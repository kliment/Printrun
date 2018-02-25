#!/usr/bin/env python3

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
import getopt

from printrun.printcore import printcore
from printrun.utils import setup_logging
from printrun import gcoder

if __name__ == '__main__':
    setup_logging(sys.stderr)
    baud = 115200
    loud = False
    statusreport = False

    from printrun.printcore import __version__ as printcore_version

    usage = "Usage:\n"+\
            "  printcore [OPTIONS] PORT FILE\n\n"+\
            "Options:\n"+\
            "  -b, --baud=BAUD_RATE"+\
                        "\t\tSet baud rate value. Default value is 115200\n"+\
            "  -s, --statusreport\t\tPrint progress as percentage\n"+\
            "  -v, --verbose\t\t\tPrint additional progress information\n"+\
            "  -V, --version\t\t\tPrint program's version number and exit\n"+\
            "  -h, --help\t\t\tPrint this help message and exit\n"

    try:
        opts, args = getopt.getopt(sys.argv[1:], "b:svVh",
                        ["baud=", "statusreport", "verbose", "version", "help"])
    except getopt.GetoptError as err:
        print(str(err))
        print(usage)
        sys.exit(2)
    for o, a in opts:
        if o in ('-h', '--help'):
            print(usage)
            sys.exit(0)
        elif o in ('-V','--version'):
            print("printrun "+printcore_version)
            sys.exit(0)
        elif o in ('-b','--baud'):
            try:
                baud = int(a)
            except ValueError:
                print("ValueError:")
                print("\tInvalid BAUD_RATE value '%s'" % a)
                print("\tBAUD_RATE must be an integer\n")
                # FIXME: This should output a more apropiate error message when
                #        not a good baud rate is passed as an argument
                #        i.e: when baud <= 1000 or > 225000
                print(usage)
                sys.exit(2)
        elif o in ('-v', '--verbose'):
            loud = True
        elif o in ('-s', '--statusreport'):
            statusreport = True

    if len(args) <= 1:
        print("Error: Port or gcode file were not specified.\n")
        print(usage)
        sys.exit(2)
    elif len(args) > 1:
        port = args[-2]
        filename = args[-1]
        print("Printing: %s on %s with baudrate %d" % (filename, port, baud))

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
