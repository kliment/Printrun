#!/usr/bin/env python

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

from serial import Serial, SerialException
from threading import Thread
from select import error as SelectError
import time, getopt, sys
import platform, os

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

class printcore():
    def __init__(self, port = None, baud = None):
        """Initializes a printcore instance. Pass the port and baud rate to connect immediately
        """
        self.baud = None
        self.port = None
        self.printer = None #Serial instance connected to the printer, None when disconnected
        self.clear = 0 #clear to send, enabled after responses
        self.online = False #The printer has responded to the initial command and is active
        self.printing = False #is a print currently running, true if printing, false if paused
        self.mainqueue = []
        self.priqueue = []
        self.queueindex = 0
        self.lineno = 0
        self.resendfrom = -1
        self.paused = False
        self.sentlines = {}
        self.log = []
        self.sent = []
        self.tempcb = None #impl (wholeline)
        self.recvcb = None #impl (wholeline)
        self.sendcb = None #impl (wholeline)
        self.errorcb = None #impl (wholeline)
        self.startcb = None #impl ()
        self.endcb = None #impl ()
        self.onlinecb = None #impl ()
        self.loud = False #emit sent and received lines to terminal
        self.greetings = ['start','Grbl ']
        self.wait = 0 # default wait period for send(), send_now()
        self.read_thread = None
        self.stop_read_thread = False
        self.print_thread = None
        if port is not None and baud is not None:
            self.connect(port, baud)

    def disconnect(self):
        """Disconnects from printer and pauses the print
        """
        if self.printer:
            if self.read_thread:
                self.stop_read_thread = True
                self.read_thread.join()
                self.read_thread = None
            self.printer.close()
        self.printer = None
        self.online = False
        self.printing = False

    def connect(self, port = None, baud = None):
        """Set port and baudrate if given, then connect to printer
        """
        if self.printer:
            self.disconnect()
        if port is not None:
            self.port = port
        if baud is not None:
            self.baud = baud
        if self.port is not None and self.baud is not None:
            disable_hup(self.port)
            self.printer = Serial(port = self.port, baudrate = self.baud, timeout = 0.25)
            self.stop_read_thread = False
            self.read_thread = Thread(target = self._listen)
            self.read_thread.start()

    def reset(self):
        """Reset the printer
        """
        if self.printer:
            self.printer.setDTR(1)
            time.sleep(0.2)
            self.printer.setDTR(0)

    def _readline(self):
        try:
            line = self.printer.readline()
            if len(line) > 1:
                self.log.append(line)
                if self.recvcb:
                    try: self.recvcb(line)
                    except: pass
                if self.loud: print "RECV: ", line.rstrip()
            return line
        except SelectError, e:
            if 'Bad file descriptor' in e.args[1]:
                print "Can't read from printer (disconnected?)."
                return None
            else:
                raise
        except SerialException, e:
            print "Can't read from printer (disconnected?)."
            return None
        except OSError, e:
            print "Can't read from printer (disconnected?)."
            return None

    def _listen_can_continue(self):
        return not self.stop_read_thread and self.printer and self.printer.isOpen()

    def _listen_until_online(self):
        while not self.online and self._listen_can_continue():
            self._send("M105")
            empty_lines = 0
            while self._listen_can_continue():
                line = self._readline()
                if line == None: break # connection problem
                # workaround cases where M105 was sent before printer Serial
                # was online an empty line means read timeout was reached,
                # meaning no data was received thus we count those empty lines,
                # and once we have seen 5 in a row, we just break and send a
                # new M105
                if not line: empty_lines += 1
                else: empty_lines = 0
                if empty_lines == 5: break
                if line.startswith(tuple(self.greetings)) or line.startswith('ok'):
                    if self.onlinecb:
                        try: self.onlinecb()
                        except: pass
                    self.online = True
                    return
            time.sleep(0.25)

    def _listen(self):
        """This function acts on messages from the firmware
        """
        self.clear = True
        if not self.printing:
            self._listen_until_online()
        while self._listen_can_continue():
            line = self._readline()
            if line == None:
                break
            if line.startswith('DEBUG_'):
                continue
            if line.startswith(tuple(self.greetings)) or line.startswith('ok'):
                self.clear = True
            if line.startswith('ok') and "T:" in line and self.tempcb:
                    #callback for temp, status, whatever
                try: self.tempcb(line)
                except: pass
            elif line.startswith('Error'):
                if self.errorcb:
                #callback for errors
                    try: self.errorcb(line)
                    except: pass
            # Teststrings for resend parsing       # Firmware     exp. result
            # line="rs N2 Expected checksum 67"    # Teacup       2
            if line.lower().startswith("resend") or line.startswith("rs"):
                line = line.replace("N:"," ").replace("N"," ").replace(":"," ")
                linewords = line.split()
                while len(linewords) != 0:
                    try:
                        toresend = int(linewords.pop(0))
                        self.resendfrom = toresend
                        #print str(toresend)
                        break
                    except:
                        pass
                self.clear = True
        self.clear = True

    def _checksum(self, command):
        return reduce(lambda x, y:x^y, map(ord, command))

    def startprint(self, data, startindex = 0):
        """Start a print, data is an array of gcode commands.
        returns True on success, False if already printing.
        The print queue will be replaced with the contents of the data array, the next line will be set to 0 and the firmware notified.
        Printing will then start in a parallel thread.
        """
        if self.printing or not self.online or not self.printer:
            return False
        self.printing = True
        self.mainqueue = [] + data
        self.lineno = 0
        self.queueindex = startindex
        self.resendfrom = -1
        self._send("M110", -1, True)
        if len(data) == 0:
            return True
        self.clear = False
        self.print_thread = Thread(target = self._print)
        self.print_thread.start()
        return True

    def pause(self):
        """Pauses the print, saving the current position.
        """
        self.paused = True
        self.printing = False
        self.print_thread.join()
        self.print_thread = None

    def resume(self):
        """Resumes a paused print.
        """
        self.paused = False
        self.printing = True
        self.print_thread = Thread(target = self._print)
        self.print_thread.start()

    def send(self, command, wait = 0):
        """Adds a command to the checksummed main command queue if printing, or sends the command immediately if not printing
        """

        if self.online:
            if self.printing:
                self.mainqueue.append(command)
            else:
                while self.printer and self.printing and not self.clear:
                    time.sleep(0.001)
                if wait == 0 and self.wait > 0:
                    wait = self.wait
                if wait > 0:
                    self.clear = False
                self._send(command, self.lineno, True)
                self.lineno += 1
                while wait > 0 and self.printer and self.printing and not self.clear:
                    time.sleep(0.001)
                    wait -= 1
        else:
            print "Not connected to printer."

    def send_now(self, command, wait = 0):
        """Sends a command to the printer ahead of the command queue, without a checksum
        """
        if self.online or force:
            if self.printing:
                self.priqueue.append(command)
            else:
                while self.printer and self.printing and not self.clear:
                    time.sleep(0.001)
                if wait == 0 and self.wait > 0:
                    wait = self.wait
                if wait > 0:
                    self.clear = False
                self._send(command)
                while (wait > 0) and self.printer and self.printing and not self.clear:
                    time.sleep(0.001)
                    wait -= 1
        else:
            print "Not connected to printer."

    def _print(self):
        if self.startcb:
            #callback for printing started
            try: self.startcb()
            except: pass
        while self.printing and self.printer and self.online:
            self._sendnext()
        self.sentlines = {}
        self.log = []
        self.sent = []
        if self.endcb:
            #callback for printing done
            try: self.endcb()
            except: pass

    def _sendnext(self):
        if not self.printer:
            return
        while self.printer and self.printing and not self.clear:
            time.sleep(0.001)
        self.clear = False
        if not (self.printing and self.printer and self.online):
            self.clear = True
            return
        if self.resendfrom < self.lineno and self.resendfrom > -1:
            self._send(self.sentlines[self.resendfrom], self.resendfrom, False)
            self.resendfrom += 1
            return
        self.resendfrom = -1
        for i in self.priqueue[:]:
            self._send(i)
            del self.priqueue[0]
            return
        if self.printing and self.queueindex < len(self.mainqueue):
            tline = self.mainqueue[self.queueindex]
            tline = tline.split(";")[0]
            if len(tline) > 0:
                self._send(tline, self.lineno, True)
                self.lineno += 1
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
        if calcchecksum:
            prefix = "N" + str(lineno) + " " + command
            command = prefix + "*" + str(self._checksum(prefix))
            if "M110" not in command:
                self.sentlines[lineno] = command
        if self.printer:
            self.sent.append(command)
            if self.loud:
                print "SENT: ", command
            if self.sendcb:
                try: self.sendcb(command)
                except: pass
            try:
                self.printer.write(str(command+"\n"))
            except SerialException, e:
                print "Can't write to printer (disconnected?)."

if __name__ == '__main__':
    baud = 115200
    loud = False
    statusreport = False
    try:
        opts, args = getopt.getopt(sys.argv[1:], "h,b:,v,s",
                                   ["help", "baud", "verbose", "statusreport"])
    except getopt.GetoptError, err:
        print str(err)
        sys.exit(2)
    for o, a in opts:
        if o in ('-h', '--help'):
            # FIXME: Fix help
            print "Opts are: --help , -b --baud = baudrate, -v --verbose, -s --statusreport"
            sys.exit(1)
        if o in ('-b', '--baud'):
            baud = int(a)
        if o in ('-v','--verbose'):
            loud = True
        elif o in ('-s','--statusreport'):
            statusreport = True

    if len (args) > 1:
        port = args[-2]
        filename = args[-1]
        print "Printing: %s on %s with baudrate %d" % (filename, port, baud)
    else:
        print "Usage: python [-h|-b|-v|-s] printcore.py /dev/tty[USB|ACM]x filename.gcode"
        sys.exit(2)
    p = printcore(port, baud)
    p.loud = loud
    time.sleep(2)
    gcode = [i.replace("\n", "") for i in open(filename)]
    p.startprint(gcode)

    try:
        if statusreport:
            p.loud = False
            sys.stdout.write("Progress: 00.0%")
            sys.stdout.flush()
        while p.printing:
            time.sleep(1)
            if statusreport:
                sys.stdout.write("%02.1f%%\r" % (100 * float(p.queueindex) / len(p.mainqueue),) )
                sys.stdout.flush()
        p.disconnect()
        sys.exit(0)
    except:
        p.disconnect()
