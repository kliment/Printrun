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

import sys
import os
import logging
logging.basicConfig(level=logging.INFO)

import wx

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from printrun.gcview import GcodeViewFrame
from printrun import gcoder

app = wx.App(redirect = False)
build_dimensions = [200, 200, 100, -100, -100, 0]
build_dimensions = [200, 200, 100, 0, 0, 0]
frame = GcodeViewFrame(None, wx.ID_ANY, 'Gcode view, shift to move view, mousewheel to set layer', size = (800, 800), build_dimensions = build_dimensions)
gcode = gcoder.GCode(open(sys.argv[1]))
print("Gcode loaded")
frame.addfile(gcode)

first_move = None
for i in range(len(gcode.lines)):
    if gcode.lines[i].is_move:
        first_move = gcode.lines[i]
        break
last_move = None
for i in range(len(gcode.lines) - 1, -1, -1):
    if gcode.lines[i].is_move:
        last_move = gcode.lines[i]
        break
nsteps = 20
steptime = 50
lines = [first_move] \
    + [gcode.lines[int(float(i) * (len(gcode.lines) - 1) / nsteps)]
       for i in range(1, nsteps)] + [last_move]
current_line = 0
def setLine():
    global current_line
    frame.set_current_gline(lines[current_line])
    current_line = (current_line + 1) % len(lines)
    timer.Start()

timer = wx.CallLater(steptime, setLine)
timer.Start()

frame.Show(True)
app.MainLoop()
app.Destroy()
