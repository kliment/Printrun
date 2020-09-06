# This file is part of the Printrun suite.
#
# Printrun is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Printrun is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Printrun.  If not, see <http://www.gnu.org/licenses/>.

__version__ = "2.0.0rc7"

import sys
if sys.version_info.major < 3:
    print("You need to run this on Python 3")
    sys.exit(-1)

from serial import Serial, SerialException, PARITY_ODD, PARITY_NONE
from select import error as SelectError
import threading
from queue import Queue, Empty as QueueEmpty
import time
import platform
import os
import logging
import traceback
import errno
import socket
import re
import selectors
from functools import wraps, reduce
from collections import deque
from printrun import gcoder
from .utils import set_utf8_locale, install_locale, decode_utf8
try:
    set_utf8_locale()
except:
    pass
install_locale('pronterface')
from printrun.plugins import PRINTCORE_HANDLER

def locked(f):
    @wraps(f)
    def inner(*args, **kw):
        with inner.lock:
            return f(*args, **kw)
    inner.lock = threading.Lock()
    return inner

def control_ttyhup(port, disable_hup):
    """Controls the HUPCL"""
    if platform.system() == "Linux":
        if disable_hup:
            os.system("stty -F %s -hup" % port)
        else:
            os.system("stty -F %s hup" % port)

def enable_hup(port):
    control_ttyhup(port, False)

def disable_hup(port):
    control_ttyhup(port, True)

PR_EOF = None  #printrun's marker for EOF
PR_AGAIN = b'' #printrun's marker for timeout/no data
SYS_EOF = b''  #python's marker for EOF
SYS_AGAIN = None #python's marker for timeout/no data

class printcore():
    def __init__(self, port = None, baud = None, dtr=None):
        """Initializes a printcore instance. Pass the port and baud rate to
           connect immediately"""
        self.baud = None
        self.dtr = None
        self.port = None
        self.analyzer = gcoder.GCode()
        # Serial instance connected to the printer, should be None when
        # disconnected
        self.printer = None
        # clear to send, enabled after responses
        # FIXME: should probably be changed to a sliding window approach
        self.clear = 0
        # The printer has responded to the initial command and is active
        self.online = False
        # is a print currently running, true if printing, false if paused
        self.printing = False
        self.mainqueue = None
        self.priqueue = Queue(0)
        self.queueindex = 0
        self.lineno = 0
        self.resendfrom = -1
        self.paused = False
        self.sentlines = {}
        self.log = deque(maxlen = 10000)
        self.sent = []
        self.writefailures = 0
        self.tempcb = None  # impl (wholeline)
        self.recvcb = None  # impl (wholeline)
        self.sendcb = None  # impl (wholeline)
        self.preprintsendcb = None  # impl (wholeline)
        self.printsendcb = None  # impl (wholeline)
        self.layerchangecb = None  # impl (wholeline)
        self.errorcb = None  # impl (wholeline)
        self.startcb = None  # impl ()
        self.endcb = None  # impl ()
        self.onlinecb = None  # impl ()
        self.loud = False  # emit sent and received lines to terminal
        self.tcp_streaming_mode = False
        self.greetings = ['start', 'Grbl ']
        self.wait = 0  # default wait period for send(), send_now()
        self.read_thread = None
        self.stop_read_thread = False
        self.send_thread = None
        self.stop_send_thread = False
        self.print_thread = None
        self.readline_buf = []
        self.selector = None
        self.event_handler = PRINTCORE_HANDLER
        # Not all platforms need to do this parity workaround, and some drivers
        # don't support it.  Limit it to platforms that actually require it
        # here to avoid doing redundant work elsewhere and potentially breaking
        # things.
        self.needs_parity_workaround = platform.system() == "linux" and os.path.exists("/etc/debian")
        for handler in self.event_handler:
            try: handler.on_init()
            except: logging.error(traceback.format_exc())
        if port is not None and baud is not None:
            self.connect(port, baud)
        self.xy_feedrate = None
        self.z_feedrate = None

    def addEventHandler(self, handler):
        '''
        Adds an event handler.
        
        @param handler: The handler to be added.
        '''
        self.event_handler.append(handler)

    def logError(self, error):
        for handler in self.event_handler:
            try: handler.on_error(error)
            except: logging.error(traceback.format_exc())
        if self.errorcb:
            try: self.errorcb(error)
            except: logging.error(traceback.format_exc())
        else:
            logging.error(error)

    @locked
    def disconnect(self):
        """Disconnects from printer and pauses the print
        """
        if self.printer:
            if self.read_thread:
                self.stop_read_thread = True
                if threading.current_thread() != self.read_thread:
                    self.read_thread.join()
                self.read_thread = None
            if self.print_thread:
                self.printing = False
                self.print_thread.join()
            self._stop_sender()
            try:
                if self.selector is not None:
                    self.selector.unregister(self.printer_tcp)
                    self.selector.close()
                    self.selector = None
                if self.printer_tcp is not None:
                    self.printer_tcp.close()
                    self.printer_tcp = None
                self.printer.close()
            except socket.error:
                logger.error(traceback.format_exc())
                pass
            except OSError:
                logger.error(traceback.format_exc())
                pass
        for handler in self.event_handler:
            try: handler.on_disconnect()
            except: logging.error(traceback.format_exc())
        self.printer = None
        self.online = False
        self.printing = False

    @locked
    def connect(self, port = None, baud = None, dtr=None):
        """Set port and baudrate if given, then connect to printer
        """
        if self.printer:
            self.disconnect()
        if port is not None:
            self.port = port
        if baud is not None:
            self.baud = baud
        if dtr is not None:
            self.dtr = dtr
        if self.port is not None and self.baud is not None:
            # Connect to socket if "port" is an IP, device if not
            host_regexp = re.compile("^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])$|^(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9])\.)*([A-Za-z0-9]|[A-Za-z0-9][A-Za-z0-9\-]*[A-Za-z0-9])$")
            is_serial = True
            if ":" in self.port:
                bits = self.port.split(":")
                if len(bits) == 2:
                    hostname = bits[0]
                    try:
                        port_number = int(bits[1])
                        if host_regexp.match(hostname) and 1 <= port_number <= 65535:
                            is_serial = False
                    except:
                        pass
            self.writefailures = 0
            if not is_serial:
                self.printer_tcp = socket.socket(socket.AF_INET,
                                                 socket.SOCK_STREAM)
                self.printer_tcp.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                self.timeout = 0.25
                self.printer_tcp.settimeout(1.0)
                try:
                    self.printer_tcp.connect((hostname, port_number))
                    #a single read timeout raises OSError for all later reads
                    #probably since python 3.5
                    #use non blocking instead
                    self.printer_tcp.settimeout(0)
                    self.printer = self.printer_tcp.makefile('rwb', buffering=0)
                    self.selector = selectors.DefaultSelector()
                    self.selector.register(self.printer_tcp, selectors.EVENT_READ)
                except socket.error as e:
                    if(e.strerror is None): e.strerror=""
                    self.logError(_("Could not connect to %s:%s:") % (hostname, port_number) +
                                  "\n" + _("Socket error %s:") % e.errno +
                                  "\n" + e.strerror)
                    self.printer = None
                    self.printer_tcp = None
                    return
            else:
                disable_hup(self.port)
                self.printer_tcp = None
                try:
                    if self.needs_parity_workaround:
                        self.printer = Serial(port = self.port,
                                              baudrate = self.baud,
                                              timeout = 0.25,
                                              parity = PARITY_ODD)
                        self.printer.close()
                        self.printer.parity = PARITY_NONE
                    else:
                        self.printer = Serial(baudrate = self.baud,
                                              timeout = 0.25,
                                              parity = PARITY_NONE)
                        self.printer.port = self.port
                    try:  #this appears not to work on many platforms, so we're going to call it but not care if it fails
                        self.printer.dtr = dtr
                    except:
                        #self.logError(_("Could not set DTR on this platform")) #not sure whether to output an error message
                        pass
                    self.printer.open()
                except SerialException as e:
                    self.logError(_("Could not connect to %s at baudrate %s:") % (self.port, self.baud) +
                                  "\n" + _("Serial error: %s") % e)
                    self.printer = None
                    return
                except IOError as e:
                    self.logError(_("Could not connect to %s at baudrate %s:") % (self.port, self.baud) +
                                  "\n" + _("IO error: %s") % e)
                    self.printer = None
                    return
            for handler in self.event_handler:
                try: handler.on_connect()
                except: logging.error(traceback.format_exc())
            self.stop_read_thread = False
            self.read_thread = threading.Thread(target = self._listen,
                                                name='read thread')
            self.read_thread.start()
            self._start_sender()

    def reset(self):
        """Reset the printer
        """
        if self.printer and not self.printer_tcp:
            self.printer.dtr = 1
            time.sleep(0.2)
            self.printer.dtr = 0

    def _readline_buf(self):
        "Try to readline from buffer"
        if len(self.readline_buf):
            chunk = self.readline_buf[-1]
            eol = chunk.find(b'\n')
            if eol >= 0:
                line = b''.join(self.readline_buf[:-1]) + chunk[:(eol+1)]
                self.readline_buf = []
                if eol + 1 < len(chunk):
                    self.readline_buf.append(chunk[(eol+1):])
                return line
        return PR_AGAIN

    def _readline_nb(self):
        "Non blocking readline. Socket based files do not support non blocking or timeouting readline"
        if self.printer_tcp:
            line = self._readline_buf()
            if line:
                return line
            chunk_size = 256
            while True:
                chunk = self.printer.read(chunk_size)
                if chunk is SYS_AGAIN and self.selector.select(self.timeout):
                    chunk = self.printer.read(chunk_size)
                #print('_readline_nb chunk', chunk, type(chunk))
                if chunk:
                    self.readline_buf.append(chunk)
                    line = self._readline_buf()
                    if line:
                        return line
                elif chunk is SYS_AGAIN:
                    return PR_AGAIN
                else:
                    #chunk == b'' means EOF
                    line = b''.join(self.readline_buf)
                    self.readline_buf = []
                    self.stop_read_thread = True
                    return line if line else PR_EOF
        else: # serial port
            return self.printer.readline()

    def _readline(self):
        try:
            line_bytes = self._readline_nb()
            if line_bytes is PR_EOF:
                self.logError(_("Can't read from printer (disconnected?). line_bytes is None"))
                return PR_EOF
            line = line_bytes.decode('utf-8')

            if len(line) > 1:
                self.log.append(line)
                for handler in self.event_handler:
                    try: handler.on_recv(line)
                    except: logging.error(traceback.format_exc())
                if self.recvcb:
                    try: self.recvcb(line)
                    except: self.logError(traceback.format_exc())
                if self.loud: logging.info("RECV: %s" % line.rstrip())
            return line
        except UnicodeDecodeError:
            self.logError(_("Got rubbish reply from %s at baudrate %s:") % (self.port, self.baud) +
                              "\n" + _("Maybe a bad baudrate?"))
            return None
        except SelectError as e:
            if 'Bad file descriptor' in e.args[1]:
                self.logError(_("Can't read from printer (disconnected?) (SelectError {0}): {1}").format(e.errno, decode_utf8(e.strerror)))
                return None
            else:
                self.logError(_("SelectError ({0}): {1}").format(e.errno, decode_utf8(e.strerror)))
                raise
        except SerialException as e:
            self.logError(_("Can't read from printer (disconnected?) (SerialException): {0}").format(decode_utf8(str(e))))
            return None
        except socket.error as e:
            self.logError(_("Can't read from printer (disconnected?) (Socket error {0}): {1}").format(e.errno, decode_utf8(e.strerror)))
            return None
        except OSError as e:
            if e.errno == errno.EAGAIN:  # Not a real error, no data was available
                return ""
            self.logError(_("Can't read from printer (disconnected?) (OS Error {0}): {1}").format(e.errno, e.strerror))
            return None

    def _listen_can_continue(self):
        if self.printer_tcp:
            return not self.stop_read_thread and self.printer
        return (not self.stop_read_thread
                and self.printer
                and self.printer.is_open)

    def _listen_until_online(self):
        while not self.online and self._listen_can_continue():
            self._send("M105")
            if self.writefailures >= 4:
                logging.error(_("Aborting connection attempt after 4 failed writes."))
                return
            empty_lines = 0
            while self._listen_can_continue():
                line = self._readline()
                if line is None: break  # connection problem
                # workaround cases where M105 was sent before printer Serial
                # was online an empty line means read timeout was reached,
                # meaning no data was received thus we count those empty lines,
                # and once we have seen 15 in a row, we just break and send a
                # new M105
                # 15 was chosen based on the fact that it gives enough time for
                # Gen7 bootloader to time out, and that the non received M105
                # issues should be quite rare so we can wait for a long time
                # before resending
                if not line:
                    empty_lines += 1
                    if empty_lines == 15: break
                else: empty_lines = 0
                if line.startswith(tuple(self.greetings)) \
                   or line.startswith('ok') or "T:" in line:
                    self.online = True
                    for handler in self.event_handler:
                        try: handler.on_online()
                        except: logging.error(traceback.format_exc())
                    if self.onlinecb:
                        try: self.onlinecb()
                        except: self.logError(traceback.format_exc())
                    return

    def _listen(self):
        """This function acts on messages from the firmware
        """
        self.clear = True
        if not self.printing:
            self._listen_until_online()
        while self._listen_can_continue():
            line = self._readline()
            if line is None:
                logging.debug('_readline() is None, exiting _listen()')
                break
            if line.startswith('DEBUG_'):
                continue
            if line.startswith(tuple(self.greetings)) or line.startswith('ok'):
                self.clear = True
            if line.startswith('ok') and "T:" in line:
                for handler in self.event_handler:
                    try: handler.on_temp(line)
                    except: logging.error(traceback.format_exc())
                if self.tempcb:
                    # callback for temp, status, whatever
                    try: self.tempcb(line)
                    except: self.logError(traceback.format_exc())
            elif line.startswith('Error'):
                self.logError(line)
            # Teststrings for resend parsing       # Firmware     exp. result
            # line="rs N2 Expected checksum 67"    # Teacup       2
            if line.lower().startswith("resend") or line.startswith("rs"):
                for haystack in ["N:", "N", ":"]:
                    line = line.replace(haystack, " ")
                linewords = line.split()
                while len(linewords) != 0:
                    try:
                        toresend = int(linewords.pop(0))
                        self.resendfrom = toresend
                        break
                    except:
                        pass
                self.clear = True
        self.clear = True
        logging.debug('Exiting read thread')

    def _start_sender(self):
        self.stop_send_thread = False
        self.send_thread = threading.Thread(target = self._sender,
                                            name = 'send thread')
        self.send_thread.start()

    def _stop_sender(self):
        if self.send_thread:
            self.stop_send_thread = True
            self.send_thread.join()
            self.send_thread = None

    def _sender(self):
        while not self.stop_send_thread:
            try:
                command = self.priqueue.get(True, 0.1)
            except QueueEmpty:
                continue
            while self.printer and self.printing and not self.clear:
                time.sleep(0.001)
            self._send(command)
            while self.printer and self.printing and not self.clear:
                time.sleep(0.001)

    def _checksum(self, command):
        return reduce(lambda x, y: x ^ y, map(ord, command))

    def startprint(self, gcode, startindex = 0):
        """Start a print, gcode is an array of gcode commands.
        returns True on success, False if already printing.
        The print queue will be replaced with the contents of the data array,
        the next line will be set to 0 and the firmware notified. Printing
        will then start in a parallel thread.
        """
        if self.printing or not self.online or not self.printer:
            return False
        self.queueindex = startindex
        self.mainqueue = gcode
        self.printing = True
        self.lineno = 0
        self.resendfrom = -1
        self._send("M110", -1, True)
        if not gcode or not gcode.lines:
            return True
        self.clear = False
        resuming = (startindex != 0)
        self.print_thread = threading.Thread(target = self._print,
                                             name = 'print thread',
                                             kwargs = {"resuming": resuming})
        self.print_thread.start()
        return True

    def cancelprint(self):
        self.pause()
        self.paused = False
        self.mainqueue = None
        self.clear = True

    # run a simple script if it exists, no multithreading
    def runSmallScript(self, filename):
        if filename is None: return
        f = None
        try:
            with open(filename) as f:
                for i in f:
                    l = i.replace("\n", "")
                    l = l[:l.find(";")]  # remove comments
                    self.send_now(l)
        except:
            pass

    def pause(self):
        """Pauses the print, saving the current position.
        """
        if not self.printing: return False
        self.paused = True
        self.printing = False

        # try joining the print thread: enclose it in try/except because we
        # might be calling it from the thread itself
        try:
            self.print_thread.join()
        except RuntimeError as e:
            if e.message == "cannot join current thread":
                pass
            else:
                self.logError(traceback.format_exc())
        except:
            self.logError(traceback.format_exc())

        self.print_thread = None

        # saves the status
        self.pauseX = self.analyzer.abs_x
        self.pauseY = self.analyzer.abs_y
        self.pauseZ = self.analyzer.abs_z
        self.pauseE = self.analyzer.abs_e
        self.pauseF = self.analyzer.current_f
        self.pauseRelative = self.analyzer.relative

    def resume(self):
        """Resumes a paused print.
        """
        if not self.paused: return False
        if self.paused:
            # restores the status
            self.send_now("G90")  # go to absolute coordinates

            xyFeedString = ""
            zFeedString = ""
            if self.xy_feedrate is not None:
                xyFeedString = " F" + str(self.xy_feedrate)
            if self.z_feedrate is not None:
                zFeedString = " F" + str(self.z_feedrate)

            self.send_now("G1 X%s Y%s%s" % (self.pauseX, self.pauseY,
                                            xyFeedString))
            self.send_now("G1 Z" + str(self.pauseZ) + zFeedString)
            self.send_now("G92 E" + str(self.pauseE))

            # go back to relative if needed
            if self.pauseRelative: self.send_now("G91")
            # reset old feed rate
            self.send_now("G1 F" + str(self.pauseF))

        self.paused = False
        self.printing = True
        self.print_thread = threading.Thread(target = self._print,
                                             name = 'print thread',
                                             kwargs = {"resuming": True})
        self.print_thread.start()

    def send(self, command, wait = 0):
        """Adds a command to the checksummed main command queue if printing, or
        sends the command immediately if not printing"""

        if self.online:
            if self.printing:
                self.mainqueue.append(command)
            else:
                self.priqueue.put_nowait(command)
        else:
            self.logError(_("Not connected to printer."))

    def send_now(self, command, wait = 0):
        """Sends a command to the printer ahead of the command queue, without a
        checksum"""
        if self.online:
            self.priqueue.put_nowait(command)
        else:
            self.logError(_("Not connected to printer."))

    def _print(self, resuming = False):
        self._stop_sender()
        try:
            for handler in self.event_handler:
                try: handler.on_start(resuming)
                except: logging.error(traceback.format_exc())
            if self.startcb:
                # callback for printing started
                try: self.startcb(resuming)
                except:
                    self.logError(_("Print start callback failed with:") +
                                  "\n" + traceback.format_exc())
            while self.printing and self.printer and self.online:
                self._sendnext()
            self.sentlines = {}
            self.log.clear()
            self.sent = []
            for handler in self.event_handler:
                try: handler.on_end()
                except: logging.error(traceback.format_exc())
            if self.endcb:
                # callback for printing done
                try: self.endcb()
                except:
                    self.logError(_("Print end callback failed with:") +
                                  "\n" + traceback.format_exc())
        except:
            self.logError(_("Print thread died due to the following error:") +
                          "\n" + traceback.format_exc())
        finally:
            self.print_thread = None
            self._start_sender()

    def process_host_command(self, command):
        """only ;@pause command is implemented as a host command in printcore, but hosts are free to reimplement this method"""
        command = command.lstrip()
        if command.startswith(";@pause"):
            self.pause()

    def _sendnext(self):
        if not self.printer:
            return
        while self.printer and self.printing and not self.clear:
            time.sleep(0.001)
        # Only wait for oks when using serial connections or when not using tcp
        # in streaming mode
        if not self.printer_tcp or not self.tcp_streaming_mode:
            self.clear = False
        if not (self.printing and self.printer and self.online):
            self.clear = True
            return
        if self.resendfrom < self.lineno and self.resendfrom > -1:
            self._send(self.sentlines[self.resendfrom], self.resendfrom, False)
            self.resendfrom += 1
            return
        self.resendfrom = -1
        if not self.priqueue.empty():
            self._send(self.priqueue.get_nowait())
            self.priqueue.task_done()
            return
        if self.printing and self.mainqueue.has_index(self.queueindex):
            (layer, line) = self.mainqueue.idxs(self.queueindex)
            gline = self.mainqueue.all_layers[layer][line]
            if self.queueindex > 0:
                (prev_layer, prev_line) = self.mainqueue.idxs(self.queueindex - 1)
                if prev_layer != layer:
                    for handler in self.event_handler:
                        try: handler.on_layerchange(layer)
                        except: logging.error(traceback.format_exc())
            if self.layerchangecb and self.queueindex > 0:
                (prev_layer, prev_line) = self.mainqueue.idxs(self.queueindex - 1)
                if prev_layer != layer:
                    try: self.layerchangecb(layer)
                    except: self.logError(traceback.format_exc())
            for handler in self.event_handler:
                try: handler.on_preprintsend(gline, self.queueindex, self.mainqueue)
                except: logging.error(traceback.format_exc())
            if self.preprintsendcb:
                if self.mainqueue.has_index(self.queueindex + 1):
                    (next_layer, next_line) = self.mainqueue.idxs(self.queueindex + 1)
                    next_gline = self.mainqueue.all_layers[next_layer][next_line]
                else:
                    next_gline = None
                gline = self.preprintsendcb(gline, next_gline)
            if gline is None:
                self.queueindex += 1
                self.clear = True
                return
            tline = gline.raw
            if tline.lstrip().startswith(";@"):  # check for host command
                self.process_host_command(tline)
                self.queueindex += 1
                self.clear = True
                return

            # Strip comments
            tline = gcoder.gcode_strip_comment_exp.sub("", tline).strip()
            if tline:
                self._send(tline, self.lineno, True)
                self.lineno += 1
                for handler in self.event_handler:
                    try: handler.on_printsend(gline)
                    except: logging.error(traceback.format_exc())
                if self.printsendcb:
                    try: self.printsendcb(gline)
                    except: self.logError(traceback.format_exc())
            else:
                self.clear = True
            self.queueindex += 1
        else:
            self.printing = False
            self.clear = True
            if not self.paused:
                self.queueindex = 0
                self.lineno = 0
                self._send("M110", -1, True)

    def _send(self, command, lineno = 0, calcchecksum = False):
        # Only add checksums if over serial (tcp does the flow control itself)
        if calcchecksum and not self.printer_tcp:
            prefix = "N" + str(lineno) + " " + command
            command = prefix + "*" + str(self._checksum(prefix))
            if "M110" not in command:
                self.sentlines[lineno] = command
        if self.printer:
            self.sent.append(command)
            # run the command through the analyzer
            gline = None
            try:
                gline = self.analyzer.append(command, store = False)
            except:
                logging.warning(_("Could not analyze command %s:") % command +
                                "\n" + traceback.format_exc())
            if self.loud:
                logging.info("SENT: %s" % command)

            for handler in self.event_handler:
                try: handler.on_send(command, gline)
                except: logging.error(traceback.format_exc())
            if self.sendcb:
                try: self.sendcb(command, gline)
                except: self.logError(traceback.format_exc())
            try:
                self.printer.write((command + "\n").encode('ascii'))
                if self.printer_tcp:
                    try:
                        self.printer.flush()
                    except socket.timeout:
                        pass
                self.writefailures = 0
            except socket.error as e:
                if e.errno is None:
                    self.logError(_("Can't write to printer (disconnected ?):") +
                                  "\n" + traceback.format_exc())
                else:
                    self.logError(_("Can't write to printer (disconnected?) (Socket error {0}): {1}").format(e.errno, decode_utf8(e.strerror)))
                self.writefailures += 1
            except SerialException as e:
                self.logError(_("Can't write to printer (disconnected?) (SerialException): {0}").format(decode_utf8(str(e))))
                self.writefailures += 1
            except RuntimeError as e:
                self.logError(_("Socket connection broken, disconnected. ({0}): {1}").format(e.errno, decode_utf8(e.strerror)))
                self.writefailures += 1
