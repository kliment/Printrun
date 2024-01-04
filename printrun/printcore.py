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

__version__ = "2.2.0"

import sys
if sys.version_info.major < 3:
    print("You need to run this on Python 3")
    sys.exit(-1)

import threading
from queue import Queue, Empty as QueueEmpty
import time
import logging
import traceback
from functools import wraps, reduce
from collections import deque
from printrun import gcoder
from printrun import device
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


PR_EOF = None  #printrun's marker for EOF
PR_AGAIN = b'' #printrun's marker for timeout/no data
SYS_EOF = b''  #python's marker for EOF
SYS_AGAIN = None #python's marker for timeout/no data

class printcore():
    """Core 3D printer host functionality.

    If `port` and `baud` are specified, `connect` is called immediately.

    Parameters
    ----------
    port : str, optional
        Either a device name, such as '/dev/ttyUSB0' or 'COM3', or an URL with
        port, such as '192.168.0.10:80' or 'http://www.example.com:8080'. Only
        required if it was not provided already.
    baud : int, optional
        Communication speed in bit/s, such as 9600, 115200 or 250000. Only
        required if it was not provided already.
    dtr : bool, optional
        On serial connections, enable/disable hardware DTR flow
        control. (Default is None)

    Attributes (WIP)
    ----------
    analyzer : GCode
        A `printrun.gcoder.GCode` object containing all the G-code commands
        sent to the printer.
    baud
    callback : Callback
        Object containing callback functions run at certain process stages.
        See `printrun.printcore.Callback`.
    dtr
    event_handler : list of PrinterEventHandler
        Collection of event-handling objects. The relevant method of each
        handler on this list will be triggered at the relevant process
        stage. See `printrun.eventhandler.PrinterEventHandler`.
    mainqueue : GCode
        The main command queue. A `printrun.gcoder.GCode` object containing an
        array of G-code commands. A call to `startprint` will populate this
        list and `printcore` will then gradually send the commands in this
        queue to the printer.
    online : bool
        True if the printer has responded to the initial command and is
        active.
    paused : bool
        True if there is a print currently on pause.
    port
    printing : bool
        True if there is a print currently running.
    priqueue : Queue
        The priority command queue. Commands in this queue will be gradually
        sent to the printer. If there are commands in the `mainqueue` the ones
        in `priqueue` will be sent ahead of them. See `queue.Queue`.

    """

    def __init__(self, port = None, baud = None, dtr=None):
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
        self.callback = Callback()
        # TODO[v3]: *cb attributes kept for backwards compatibility. To be
        #           removed in future releases
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
        self._callback('init')
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
                self.printer.disconnect()
            except device.DeviceError:
                self.logError(traceback.format_exc())
                pass
        self._callback('disconnect')
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
            self.writefailures = 0
            self.printer = device.Device()
            self.printer.force_dtr = self.dtr
            try:
                self.printer.connect(self.port, self.baud)
            except device.DeviceError as e:
                self.logError("Connection error: %s" % e)
                self.printer = None
                return
            self._callback('connect')
            self.stop_read_thread = False
            self.read_thread = threading.Thread(target = self._listen,
                                                name='read thread')
            self.read_thread.start()
            self._start_sender()

    def reset(self):
        """Attempt to reset the connection to the printer.

        Warnings
        --------
        Current implementation resets a serial connection by disabling
        hardware DTR flow control. It has no effect on socket connections.

        """
        self.printer.reset()

    def _readline(self):
        try:
            line_bytes = self.printer.readline()
            if line_bytes is device.READ_EOF:
                self.logError("Can't read from printer (disconnected?)." +
                              " line_bytes is None")
                self.stop_read_thread = True
                return PR_EOF
            line = line_bytes.decode('utf-8')

            if len(line) > 1:
                self.log.append(line)
                self._callback('recv', line)
                if self.loud: logging.info("RECV: %s" % line.rstrip())
            return line
        except UnicodeDecodeError:
            msg = ("Got rubbish reply from {0} at baudrate {1}:\n"
                   "Maybe a bad baudrate?").format(self.port, self.baud)
            self.logError(msg)
            return None
        except device.DeviceError as e:
            msg = ("Can't read from printer (disconnected?) {0}"
                   ).format(decode_utf8(str(e)))
            self.logError(msg)
            return None

    def _listen_can_continue(self):
        return (not self.stop_read_thread
                and self.printer
                and self.printer.is_connected)

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
                    self._callback('online')
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
                self._callback('temp', line)
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
        """Start a print.

        The `mainqueue` is populated and then commands are gradually sent to
        the printer. Printing starts in a parallel thread, this function
        launches the print and returns immediately, it does not wait/block
        until printing has finished.

        Parameters
        ----------
        gcode : GCode
            A `printrun.gcoder.GCode` object containing the array of G-code
            commands. The print queue `mainqueue` will be replaced with the
            contents of `gcode`.
        startindex : int, default: 0
            The index from the `gcode` array from which the printing will be
            started.

        Returns
        -------
        bool
            True on successful print start, False if already printing or
            offline.

        """
        if self.printing or not self.online or not self.printer:
            return False
        self.queueindex = startindex
        self.mainqueue = gcode
        self.printing = True
        self.lineno = 0
        self.resendfrom = -1
        if not gcode or not gcode.lines:
            return True

        self.clear = False
        self._send("M110 N-1", -1, True)

        resuming = (startindex != 0)
        self.print_thread = threading.Thread(target = self._print,
                                             name = 'print thread',
                                             kwargs = {"resuming": resuming})
        self.print_thread.start()
        return True

    def cancelprint(self):
        """Cancel an ongoing print."""
        self.pause()
        self.paused = False
        self.mainqueue = None
        self.clear = True

    # run a simple script if it exists, no multithreading
    def runSmallScript(self, filename):
        if not filename: return
        try:
            with open(filename) as f:
                for i in f:
                    l = i.replace("\n", "")
                    l = l.partition(';')[0]  # remove comments
                    self.send_now(l)
        except:
            pass

    def pause(self):
        """Pauses an ongoing print.

        The current position of the print is saved to be able to go back to it
        when resuming.

        Returns
        -------
        bool
            False if not printing.

        """
        if not self.printing: return False
        self.paused = True
        self.printing = False

        # ';@pause' in the gcode file calls pause from the print thread
        if not threading.current_thread() is self.print_thread:
            try:
                self.print_thread.join()
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
        self.pauseRelativeE = self.analyzer.relative_e

    def resume(self):
        """Resumes a paused print.

        `printcore` will first attempt to set the position and conditions it
        had when the print was paused and then resume the print right where it
        was.

        Returns
        -------
        bool
            False if print not paused.

        """
        if not self.paused: return False
        # restores the status
        self.send_now("G90")  # go to absolute coordinates

        xyFeed = '' if self.xy_feedrate is None else ' F' + str(self.xy_feedrate)
        zFeed = '' if self.z_feedrate is None else ' F' + str(self.z_feedrate)

        self.send_now("G1 X%s Y%s%s" % (self.pauseX, self.pauseY, xyFeed))
        self.send_now("G1 Z" + str(self.pauseZ) + zFeed)
        self.send_now("G92 E" + str(self.pauseE))

        # go back to relative if needed
        if self.pauseRelative:
            self.send_now("G91")
        if self.pauseRelativeE:
            self.send_now('M83')
        # reset old feed rate
        self.send_now("G1 F" + str(self.pauseF))

        self.paused = False
        self.printing = True
        self.print_thread = threading.Thread(target = self._print,
                                             name = 'print thread',
                                             kwargs = {"resuming": True})
        self.print_thread.start()

    def send(self, command, wait = 0):
        """Adds a command to the main queue.

        If a print is ongoing, `command` is appended at the end of
        `mainqueue`. If not printing, the command is added to the priority
        queue `priqueue`. The `command` is added to a queue and is sent on a
        parallel thread. This function is non-blocking.

        Parameters
        ----------
        command : str
            Command to be sent, e.g. "M105" or "G1 X10 Y10".
        wait
            Ignored. Do not use.

        """
        if self.online:
            if self.printing:
                self.mainqueue.append(command)
            else:
                self.priqueue.put_nowait(command)
        else:
            self.logError(_("Not connected to printer."))

    def send_now(self, command, wait = 0):
        """Adds a command to the priority queue.

        Command is appended to `priqueue`. The `command` is added to a queue
        and is sent on a parallel thread. This function is non-blocking.

        Parameters
        ----------
        command : str
            Command to be sent, e.g. "M105" or "G1 X10 Y10".
        wait
            Ignored. Do not use.

        """
        if self.online:
            self.priqueue.put_nowait(command)
        else:
            self.logError(_("Not connected to printer."))

    def _print(self, resuming = False):
        self._stop_sender()
        try:
            self._callback('start', resuming)
            while self.printing and self.printer and self.online:
                self._sendnext()
            self.sentlines = {}
            self.log.clear()
            self.sent = []
            self._callback('end')
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
        if not self.printer.has_flow_control or not self.tcp_streaming_mode:
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
                    self._callback('layerchange', layer)
            for handler in self.event_handler:
                # TODO[v3]: Unify arguments of callback and envent handler
                try: handler.on_preprintsend(gline, self.queueindex, self.mainqueue)
                except: logging.error(traceback.format_exc())
            if self.mainqueue.has_index(self.queueindex + 1):
                (next_layer, next_line) = self.mainqueue.idxs(self.queueindex + 1)
                next_gline = self.mainqueue.all_layers[next_layer][next_line]
            else:
                next_gline = None
            if self.preprintsendcb:
                # TODO[v3]: Unify arguments of callback and envent handler
                gline = self.preprintsendcb(gline, next_gline)
            else:
                gline = self.callback.preprintsend(gline, next_gline)
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
                self._callback('printsend', gline)
            else:
                self.clear = True
            self.queueindex += 1
        else:
            self.printing = False
            self.clear = True
            if not self.paused:
                self.queueindex = 0
                self.lineno = 0
                self._send("M110 N-1", -1, True)

    def _send(self, command, lineno = 0, calcchecksum = False):
        # Only add checksums if over serial (tcp does the flow control itself)
        if calcchecksum and not self.printer.has_flow_control:
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

            self._callback('send', command, gline)
            try:
                self.printer.write((command + "\n").encode('ascii'))
                self.writefailures = 0
            except device.DeviceError as e:
                self.logError("Can't write to printer (disconnected?)"
                              " {0}".format(e))
                self.writefailures += 1

    def _callback(self, name, *args):
        # Parameters:
        #   name: string with relevant callback or event name
        #   *args: Any arguments after `name` are passed directly to
        #          the callback or event function

        # Call events from each event-handler
        for handler in self.event_handler:
            try: event = getattr(handler, f"on_{name}")
            except AttributeError: continue
            try: event(*args)
            except Exception:
                logging.error(f"'on_{name}' handler failed with:\n"
                              f"{traceback.format_exc()}")

        # Invoke the relevant old callback function for backwards
        # compatibility
        # TODO[v3]: Remove this code
        try: callback = getattr(self, f"{name}cb")
        except AttributeError: pass
        else:
            if callback is not None:
                logging.warning(f"Function printcore.{name}cb is deprecated.")
                try: return callback(*args)
                except Exception: logging.error(traceback.format_exc())

        # Invoke the relevant callback function
        try: callback = getattr(self.callback, f"{name}")
        except AttributeError: return None
        try: return callback(*args)
        except Exception:
            logging.error(f"'{name}' callback failed with:\n"
                          f"{traceback.format_exc()}")


class Callback():
    """Printcore callback functions.

    The relevant callback method is invoked at the relevant process stage.

    """

    def end(self):
        """Called when printing stops.

        Called when an ongoing print is paused, canceled or finished.
        See `printrun.printcore.printcore.pause`.
        See `printrun.printcore.printcore.cancel`.

        """
        pass

    def error(self, error):
        """Called whenever an error occurs.

        Parameters:
        -----------
        error : str
            String containing the error message.

        """
        logging.error(error)

    def hostcommand(self, command):
        """Called on host-commands.

        Host-commands are those starting with ';@', e.g. ';@pause'. When a
        host-command is detected, this function is invoked and this line is
        omitted and not sent to the printer.

        Only ;@pause command is implemented by default. If overwriting this
        function, remember to rewrite the pause logic if you wish to keep that
        functionality.

        This function is only called on lines sent while a print is ongoing.
        See `printrun.printcore.printcore.startprint`.

        Parameters:
        -----------
        command : str
            Verbatim command string.

        """
        command = command.lstrip()
        if command.startswith(";@pause"):
            self.pause()

    def layerchange(self, layer):
        """Called on detected layer changes during a print.

        This event is only triggered on lines sent while a print is ongoing.
        See `printrun.printcore.printcore.startprint`.

        Parameters
        ----------
        layer : int
            Index of the new layer within printcore's `mainqueue`.
            See `printrun.printcore.printcore.mainqueue`.

        """
        pass

    def online(self):
        """Called when printer gets online."""
        pass

    def preprintsend(self, gline, next_gline):
        """Called before sending each command of a print.

        This function is called right before a line is sent and the line
        returned by this function is what it is actually sent to the
        printer. Therefore this function allows modifying/processing lines
        before they are sent to the printer.

        This function is only called on lines sent while a print is ongoing.
        See `printrun.printcore.printcore.startprint`.

        Parameters
        ----------
        gline : Line
            The `printrun.gcoder.Line` object containing the line of G-code to
            be sent.
        next_gline : Line
            The `printrun.gcoder.Line` object containing the line of G-code to
            be sent after the current `gline`.

        Returns
        -------
        Line
            The `printrun.gcoder.Line` object containing the line of G-code
            that will be actually sent to the printer. If None is returned
            then this line won't be sent to the printer.

        """
        return gline

    def printsend(self, gline):
        """Called on each line sent during a print.

        This event is only triggered on lines sent while a print is ongoing.
        See `printrun.printcore.printcore.startprint`.

        Parameters
        ----------
        gline : Line
            The `printrun.gcoder.Line` object containing the line of G-code
            sent.

        """
        pass

    def recv(self, line):
        """Called on every line read from the printer.

        Parameters:
        -----------
        line : str
            String with data read from the printer.

        """
        pass

    def send(self, command, gline):
        """Called on every command sent to the printer.

        Parameters:
        -----------
        line : str
            Command string sent to the printer.
        gline : Line
            The `printrun.gcoder.Line` object containing the line of G-code
            sent to the printer.

        """
        pass

    def start(self, resume):
        """Called when printing commences.

        Called when starting a new print or resuming a paused one.
        See `printrun.printcore.printcore.startprint`.
        See `printrun.printcore.printcore.resume`.

        Parameters
        ----------
        resume : bool
            True if the print is resumed.

        """
        pass

    def temp(self, line):
        """Called on temperature related printer replies.

        Called when an answer from the printer contains information related to
        temperature such as temperature readings or status indications.

        Parameters:
        -----------
        line : str
            String with data read from the printer.

        """
        pass
