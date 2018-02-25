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

# Interactive RepRap e axis calibration program
# (C) Nathan Zadoks 2011

s = 300  # Extrusion speed (mm/min)
n = 100  # Default length to extrude
m = 0  # User-entered measured extrusion length
k = 300  # Default amount of steps per mm
port = '/dev/ttyUSB0'  # Default serial port to connect to printer
temp = 210  # Default extrusion temperature

tempmax = 250  # Maximum extrusion temperature

t = int(n * 60) / s  # Time to wait for extrusion

try:
    from printdummy import printcore
except ImportError:
    from printcore import printcore

import time
import getopt
import sys
import os

def float_input(prompt=''):
    f = None
    while f is None:
        s = input(prompt)
        try:
            f = float(s)
        except ValueError:
            sys.stderr.write("Not a valid floating-point number.\n")
            sys.stderr.flush()
    return f
def wait(t, m=''):
    sys.stdout.write(m + '[' + (' ' * t) + ']\r' + m + '[')
    sys.stdout.flush()
    for i in range(t):
        for s in ['|\b', '/\b', '-\b', '\\\b', '|']:
            sys.stdout.write(s)
            sys.stdout.flush()
            time.sleep(1.0 / 5)
    print()
def w(s):
    sys.stdout.write(s)
    sys.stdout.flush()


def heatup(p, temp, s = 0):
    curtemp = gettemp(p)
    p.send_now('M109 S%03d' % temp)
    p.temp = 0
    if not s: w("Heating extruder up..")
    f = False
    while curtemp <= (temp - 1):
        p.send_now('M105')
        time.sleep(0.5)
        if not f:
            time.sleep(1.5)
            f = True
        curtemp = gettemp(p)
        if curtemp: w("\rHeating extruder up.. %3d \xb0C" % curtemp)
    if s: print()
    else: print("\nReady.")

def gettemp(p):
    try: p.logl
    except: setattr(p, 'logl', 0)
    try: p.temp
    except: setattr(p, 'temp', 0)
    for n in range(p.logl, len(p.log)):
        line = p.log[n]
        if 'T:' in line:
            try:
                setattr(p, 'temp', int(line.split('T:')[1].split()[0]))
            except: print(line)
    p.logl = len(p.log)
    return p.temp
if not os.path.exists(port):
    port = 0

# Parse options
help = """
%s [ -l DISTANCE ] [ -s STEPS ] [ -t TEMP ] [ -p PORT ]
        -l      --length        Length of filament to extrude for each calibration step (default: %d mm)
        -s      --steps         Initial amount of steps to use (default: %d steps)
        -t      --temp          Extrusion temperature in degrees Celsius (default: %d \xb0C, max %d \xb0C)
        -p      --port          Serial port the printer is connected to (default: %s)
        -h      --help          This cruft.
"""[1:-1].encode('utf-8') % (sys.argv[0], n, k, temp, tempmax, port if port else 'auto')
try:
    opts, args = getopt.getopt(sys.argv[1:], "hl:s:t:p:", ["help", "length=", "steps=", "temp=", "port="])
except getopt.GetoptError as err:
    print(str(err))
    print(help)
    sys.exit(2)
for o, a in opts:
    if o in ('-h', '--help'):
        print(help)
        sys.exit()
    elif o in ('-l', '--length'):
        n = float(a)
    elif o in ('-s', '--steps'):
        k = int(a)
    elif o in ('-t', '--temp'):
        temp = int(a)
        if temp >= tempmax:
            print(('%d \xb0C? Are you insane?'.encode('utf-8') % temp) + (" That's over nine thousand!" if temp > 9000 else ''))
            sys.exit(255)
    elif o in ('-p', '--port'):
        port = a

# Show initial parameters
print("Initial parameters")
print("Steps per mm:    %3d steps" % k)
print("Length extruded: %3d mm" % n)
print()
print("Serial port:     %s" % (port if port else 'auto'))

p = None
try:
    # Connect to printer
    w("Connecting to printer..")
    try:
        p = printcore(port, 115200)
    except:
        print('Error.')
        raise
    while not p.online:
        time.sleep(1)
        w('.')
    print(" connected.")

    heatup(p, temp)

    # Calibration loop
    while n != m:
        heatup(p, temp, True)
        p.send_now("G92 E0")  # Reset e axis
        p.send_now("G1 E%d F%d" % (n, s))  # Extrude length of filament
        wait(t, 'Extruding.. ')
        m = float_input("How many millimeters of filament were extruded? ")
        if m == 0: continue
        if n != m:
            k = (n / m) * k
            p.send_now("M92 E%d" % int(round(k)))  # Set new step count
            print("Steps per mm:    %3d steps" % k)  # Tell user
    print('Calibration completed.')  # Yay!
except KeyboardInterrupt:
    pass
finally:
    if p: p.disconnect()
