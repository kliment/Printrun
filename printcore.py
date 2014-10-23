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

import time
import getopt
import sys

from printrun.printcore import printcore
from printrun.utils import setup_logging
from printrun import gcoder

if __name__ == '__main__':
    setup_logging(sys.stderr)
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
            print ("Opts are: --help, -b --baud = baudrate, -v --verbose, "
                   "-s --statusreport")
            sys.exit(1)
        if o in ('-b', '--baud'):
            baud = int(a)
        if o in ('-v', '--verbose'):
            loud = True
        elif o in ('-s', '--statusreport'):
            statusreport = True

    if len(args) > 1:
        port = args[-2]
        filename = args[-1]
        print "Printing: %s on %s with baudrate %d" % (filename, port, baud)
    else:
        print "Usage: python [-h|-b|-v|-s] printcore.py /dev/tty[USB|ACM]x filename.gcode"
        sys.exit(2)
    p = printcore(port, baud)
    p.loud = loud
    time.sleep(2)
    gcode = [i.strip() for i in open(filename)]
    gcode = gcoder.LightGCode(gcode)
    p.startprint(gcode)

    try:
        if statusreport:
            p.loud = False
            sys.stdout.write("Progress: 00.0%\r")
            sys.stdout.flush()
        while p.printing:
            time.sleep(1)
            if statusreport:
                progress = 100 * float(p.queueindex) / len(p.mainqueue)
                sys.stdout.write("Progress: %02.1f%%\r" % progress)
                sys.stdout.flush()
        p.disconnect()
        sys.exit(0)
    except:
        p.disconnect()
