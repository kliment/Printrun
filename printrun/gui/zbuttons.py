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

import wx
from printrun.gui.xybuttons import FocusCanvas
from printrun.utils import imagefile

def sign(n):
    if n < 0: return -1
    elif n > 0: return 1
    else: return 0

class ZButtons(FocusCanvas):
    button_ydistances = [7, 30, 55, 83]  # ,112
    move_values = [0.1, 1, 10]
    center = (30, 118)
    label_overlay_positions = {
        0: (1.1, 18, 9),
        1: (1.1, 41.5, 10.6),
        2: (1.1, 68, 13),
    }
    imagename = "control_z.png"

    def __init__(self, parent, moveCallback = None, bgcolor = "#FFFFFF", ID=-1):
        self.bg_bmp = wx.Image(imagefile(self.imagename), wx.BITMAP_TYPE_PNG).ConvertToBitmap()
        self.range = None
        self.direction = None
        self.orderOfMagnitudeIdx = 0  # 0 means '1', 1 means '10', 2 means '100', etc.
        self.moveCallback = moveCallback
        self.enabled = False
        # Remember the last clicked value, so we can repeat when spacebar pressed
        self.lastValue = None

        self.bgcolor = wx.Colour()
        self.bgcolor.Set(bgcolor)
        self.bgcolormask = wx.Colour(self.bgcolor.Red(), self.bgcolor.Green(), self.bgcolor.Blue(), 128)

        # On MS Windows super(style=WANTS_CHARS) prevents tab cycling
        # pass empty style explicitly
        super().__init__(parent, ID, size=self.bg_bmp.GetSize(), style=0)

        # Set up mouse and keyboard event capture
        self.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
        self.Bind(wx.EVT_LEFT_DCLICK, self.OnLeftDown)
        self.Bind(wx.EVT_MOTION, self.OnMotion)
        self.Bind(wx.EVT_LEAVE_WINDOW, self.OnLeaveWindow)
        self.Bind(wx.EVT_SET_FOCUS, self.RefreshFocus)
        self.Bind(wx.EVT_KILL_FOCUS, self.RefreshFocus)
    
    def RefreshFocus(self, evt):
        self.Refresh()
        evt.Skip()

    def disable(self):
        self.Enabled = False # prevents focus
        self.enabled = False
        self.update()

    def enable(self):
        self.Enabled = True
        self.enabled = True
        self.update()

    def repeatLast(self):
        if self.lastValue:
            self.moveCallback(self.lastValue)

    def clearRepeat(self):
        self.lastValue = None

    def lookupRange(self, ydist):
        idx = -1
        for d in self.button_ydistances:
            if ydist < d:
                return idx
            idx += 1
        return None

    def highlight(self, gc, rng, dir):
        assert(rng >= -1 and rng <= 3)
        assert(dir >= -1 and dir <= 1)

        fudge = 11
        x = 0 + fudge
        w = 59 - fudge * 2
        if rng >= 0:
            k = 1 if dir > 0 else 0
            y = self.center[1] - (dir * self.button_ydistances[rng + k])
            h = self.button_ydistances[rng + 1] - self.button_ydistances[rng]
            gc.DrawRoundedRectangle(x, y, w, h, 4)
            # gc.DrawRectangle(x, y, w, h)
        # self.drawPartialPie(dc, center, r1-inner_ring_radius, r2-inner_ring_radius, a1+fudge, a2-fudge)

    def getRangeDir(self, pos):
        ydelta = self.center[1] - pos[1]
        return (self.lookupRange(abs(ydelta)), sign(ydelta))

    def draw(self, dc, w, h):
        dc.SetBackground(wx.Brush(self.bgcolor))
        dc.Clear()
        gc = wx.GraphicsContext.Create(dc)
        if self.bg_bmp:
            w, h = (self.bg_bmp.GetWidth(), self.bg_bmp.GetHeight())
            gc.DrawBitmap(self.bg_bmp, 0, 0, w, h)

        if self.enabled and self.IsEnabled():
            # Draw label overlays
            gc.SetPen(wx.Pen(wx.Colour(255, 255, 255, 128), 1))
            gc.SetBrush(wx.Brush(wx.Colour(255, 255, 255, 128 + 64)))
            for idx, kpos in self.label_overlay_positions.items():
                if idx != self.range:
                    r = kpos[2]
                    gc.DrawEllipse(self.center[0] - kpos[0] - r, self.center[1] - kpos[1] - r, r * 2, r * 2)

            # Top 'layer' is the mouse-over highlights
            gc.SetPen(wx.Pen(wx.Colour(100, 100, 100, 172), 4))
            gc.SetBrush(wx.Brush(wx.Colour(0, 0, 0, 128)))
            if self.range is not None and self.direction is not None:
                self.highlight(gc, self.range, self.direction)
        else:
            gc.SetPen(wx.Pen(self.bgcolor, 0))
            gc.SetBrush(wx.Brush(self.bgcolormask))
            gc.DrawRectangle(0, 0, w, h)
        self.drawFocusRect(dc)

    # ------ #
    # Events #
    # ------ #

    def OnMotion(self, event):
        if not self.enabled:
            return

        oldr, oldd = self.range, self.direction

        mpos = event.GetPosition()
        self.range, self.direction = self.getRangeDir(mpos)

        if oldr != self.range or oldd != self.direction:
            self.update()

    def OnLeftDown(self, event):
        if not self.enabled:
            return

        mpos = event.GetPosition()
        r, d = self.getRangeDir(mpos)
        if r is not None and r >= 0:
            value = d * self.move_values[r]
            if self.moveCallback:
                self.lastValue = value
                self.moveCallback(value)

    def OnLeaveWindow(self, evt):
        self.range = None
        self.direction = None
        self.update()

class ZButtonsMini(ZButtons):
    button_ydistances = [7, 30, 55]
    center = (30, 84)
    label_overlay_positions = {
        0: (1, 18, 9),
        1: (1, 42.8, 12.9),
    }
    imagename = "control_z_mini.png"
    move_values = [0.1, 10]
