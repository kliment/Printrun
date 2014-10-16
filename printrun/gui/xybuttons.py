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
import math
from .bufferedcanvas import BufferedCanvas
from printrun.utils import imagefile

def sign(n):
    if n < 0: return -1
    elif n > 0: return 1
    else: return 0

class XYButtons(BufferedCanvas):
    keypad_positions = {
        0: (106, 100),
        1: (86, 83),
        2: (68, 65),
        3: (53, 50)
    }
    corner_size = (49, 49)
    corner_inset = (7, 13)
    label_overlay_positions = {
        1: (145, 98.5, 9),
        2: (160.5, 83.5, 10.6),
        3: (178, 66, 13),
        4: (197.3, 46.3, 13.3)
    }
    concentric_circle_radii = [0, 17, 45, 69, 94, 115]
    concentric_inset = 11
    center = (124, 121)
    spacer = 7
    imagename = "control_xy.png"
    corner_to_axis = {
        -1: "center",
        0: "x",
        1: "z",
        2: "y",
        3: "all",
    }

    def __init__(self, parent, moveCallback = None, cornerCallback = None, spacebarCallback = None, bgcolor = "#FFFFFF", ID=-1, zcallback=None):
        self.bg_bmp = wx.Image(imagefile(self.imagename), wx.BITMAP_TYPE_PNG).ConvertToBitmap()
        self.keypad_bmp = wx.Image(imagefile("arrow_keys.png"), wx.BITMAP_TYPE_PNG).ConvertToBitmap()
        self.keypad_idx = -1
        self.quadrant = None
        self.concentric = None
        self.corner = None
        self.moveCallback = moveCallback
        self.cornerCallback = cornerCallback
        self.spacebarCallback = spacebarCallback
        self.zCallback = zcallback
        self.enabled = False
        # Remember the last clicked buttons, so we can repeat when spacebar pressed
        self.lastMove = None
        self.lastCorner = None

        self.bgcolor = wx.Colour()
        self.bgcolor.SetFromName(bgcolor)
        self.bgcolormask = wx.Colour(self.bgcolor.Red(), self.bgcolor.Green(), self.bgcolor.Blue(), 128)

        BufferedCanvas.__init__(self, parent, ID, size=self.bg_bmp.GetSize())

        self.bind_events()

    def bind_events(self):
        # Set up mouse and keyboard event capture
        self.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
        self.Bind(wx.EVT_LEFT_DCLICK, self.OnLeftDown)
        self.Bind(wx.EVT_MOTION, self.OnMotion)
        self.Bind(wx.EVT_LEAVE_WINDOW, self.OnLeaveWindow)
        self.Bind(wx.EVT_KEY_UP, self.OnKey)
        wx.GetTopLevelParent(self).Bind(wx.EVT_CHAR_HOOK, self.OnTopLevelKey)

    def disable(self):
        self.enabled = False
        self.update()

    def enable(self):
        self.enabled = True
        self.update()

    def repeatLast(self):
        if self.lastMove:
            self.moveCallback(*self.lastMove)
        if self.lastCorner:
            self.cornerCallback(self.corner_to_axis[self.lastCorner])

    def clearRepeat(self):
        self.lastMove = None
        self.lastCorner = None

    def distanceToLine(self, pos, x1, y1, x2, y2):
        xlen = x2 - x1
        ylen = y2 - y1
        pxlen = x1 - pos.x
        pylen = y1 - pos.y
        return abs(xlen * pylen - ylen * pxlen) / math.sqrt(xlen ** 2 + ylen ** 2)

    def distanceToPoint(self, x1, y1, x2, y2):
        return math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)

    def cycleKeypadIndex(self):
        idx = self.keypad_idx + 1
        if idx > 2: idx = 0
        return idx

    def setKeypadIndex(self, idx):
        self.keypad_idx = idx
        self.update()

    def getMovement(self):
        xdir = [1, 0, -1, 0, 0, 0][self.quadrant]
        ydir = [0, 1, 0, -1, 0, 0][self.quadrant]
        zdir = [0, 0, 0, 0, 1, -1][self.quadrant]
        magnitude = math.pow(10, self.concentric - 2)
        if not zdir == 0:
            magnitude = min(magnitude, 10)
        return (magnitude * xdir, magnitude * ydir, magnitude * zdir)

    def lookupConcentric(self, radius):
        idx = 0
        for r in self.concentric_circle_radii[1:]:
            if radius < r:
                return idx
            idx += 1
        return len(self.concentric_circle_radii)

    def getQuadrantConcentricFromPosition(self, pos):
        rel_x = pos[0] - self.center[0]
        rel_y = pos[1] - self.center[1]
        radius = math.sqrt(rel_x ** 2 + rel_y ** 2)
        if rel_x > rel_y and rel_x > -rel_y:
            quadrant = 0  # Right
        elif rel_x <= rel_y and rel_x > -rel_y:
            quadrant = 3  # Down
        elif rel_x > rel_y and rel_x < -rel_y:
            quadrant = 1  # Up
        else:
            quadrant = 2  # Left

        idx = self.lookupConcentric(radius)
        return (quadrant, idx)

    def mouseOverKeypad(self, mpos):
        for idx, kpos in self.keypad_positions.items():
            radius = self.distanceToPoint(mpos[0], mpos[1], kpos[0], kpos[1])
            if radius < 9:
                return idx
        return None

    def drawPartialPie(self, gc, center, r1, r2, angle1, angle2):
        p1 = wx.Point(center.x + r1 * math.cos(angle1), center.y + r1 * math.sin(angle1))

        path = gc.CreatePath()
        path.MoveToPoint(p1.x, p1.y)
        path.AddArc(center.x, center.y, r1, angle1, angle2, True)
        path.AddArc(center.x, center.y, r2, angle2, angle1, False)
        path.AddLineToPoint(p1.x, p1.y)
        gc.DrawPath(path)

    def highlightQuadrant(self, gc, quadrant, concentric):
        assert(quadrant >= 0 and quadrant <= 3)
        assert(concentric >= 0 and concentric <= 4)

        inner_ring_radius = self.concentric_inset
        # fudge = math.pi*0.002
        fudge = -0.02
        center = wx.Point(self.center[0], self.center[1])
        if quadrant == 0:
            a1, a2 = (-math.pi * 0.25, math.pi * 0.25)
            center.x += inner_ring_radius
        elif quadrant == 1:
            a1, a2 = (math.pi * 1.25, math.pi * 1.75)
            center.y -= inner_ring_radius
        elif quadrant == 2:
            a1, a2 = (math.pi * 0.75, math.pi * 1.25)
            center.x -= inner_ring_radius
        elif quadrant == 3:
            a1, a2 = (math.pi * 0.25, math.pi * 0.75)
            center.y += inner_ring_radius

        r1 = self.concentric_circle_radii[concentric]
        r2 = self.concentric_circle_radii[concentric + 1]

        self.drawPartialPie(gc, center, r1 - inner_ring_radius, r2 - inner_ring_radius, a1 + fudge, a2 - fudge)

    def drawCorner(self, gc, x, y, angle = 0.0):
        w, h = self.corner_size

        gc.PushState()
        gc.Translate(x, y)
        gc.Rotate(angle)
        path = gc.CreatePath()
        path.MoveToPoint(-w / 2, -h / 2)
        path.AddLineToPoint(w / 2, -h / 2)
        path.AddLineToPoint(w / 2, -h / 2 + h / 4)
        path.AddLineToPoint(w / 12, h / 12)
        path.AddLineToPoint(-w / 2 + w / 4, h / 2)
        path.AddLineToPoint(-w / 2, h / 2)
        path.AddLineToPoint(-w / 2, -h / 2)
        gc.DrawPath(path)
        gc.PopState()

    def highlightCorner(self, gc, corner = 0):
        w, h = self.corner_size
        xinset, yinset = self.corner_inset
        cx, cy = self.center
        ww, wh = self.GetSizeTuple()

        if corner == 0:
            x, y = (cx - ww / 2 + xinset + 1, cy - wh / 2 + yinset)
            self.drawCorner(gc, x + w / 2, y + h / 2, 0)
        elif corner == 1:
            x, y = (cx + ww / 2 - xinset, cy - wh / 2 + yinset)
            self.drawCorner(gc, x - w / 2, y + h / 2, math.pi / 2)
        elif corner == 2:
            x, y = (cx + ww / 2 - xinset, cy + wh / 2 - yinset - 1)
            self.drawCorner(gc, x - w / 2, y - h / 2, math.pi)
        elif corner == 3:
            x, y = (cx - ww / 2 + xinset + 1, cy + wh / 2 - yinset - 1)
            self.drawCorner(gc, x + w / 2, y - h / 2, math.pi * 3 / 2)

    def drawCenteredDisc(self, gc, radius):
        cx, cy = self.center
        gc.DrawEllipse(cx - radius, cy - radius, radius * 2, radius * 2)

    def draw(self, dc, w, h):
        dc.SetBackground(wx.Brush(self.bgcolor))
        dc.Clear()
        gc = wx.GraphicsContext.Create(dc)

        if self.bg_bmp:
            w, h = (self.bg_bmp.GetWidth(), self.bg_bmp.GetHeight())
            gc.DrawBitmap(self.bg_bmp, 0, 0, w, h)

        if self.enabled and self.IsEnabled():
            # Brush and pen for grey overlay when mouse hovers over
            gc.SetPen(wx.Pen(wx.Colour(100, 100, 100, 172), 4))
            gc.SetBrush(wx.Brush(wx.Colour(0, 0, 0, 128)))

            if self.concentric is not None:
                if self.concentric < len(self.concentric_circle_radii):
                    if self.concentric == 0:
                        self.drawCenteredDisc(gc, self.concentric_circle_radii[1])
                    elif self.quadrant is not None:
                        self.highlightQuadrant(gc, self.quadrant, self.concentric)
                elif self.corner is not None:
                    self.highlightCorner(gc, self.corner)

            if self.keypad_idx >= 0:
                padw, padh = (self.keypad_bmp.GetWidth(), self.keypad_bmp.GetHeight())
                pos = self.keypad_positions[self.keypad_idx]
                pos = (pos[0] - padw / 2 - 3, pos[1] - padh / 2 - 3)
                gc.DrawBitmap(self.keypad_bmp, pos[0], pos[1], padw, padh)

            # Draw label overlays
            gc.SetPen(wx.Pen(wx.Colour(255, 255, 255, 128), 1))
            gc.SetBrush(wx.Brush(wx.Colour(255, 255, 255, 128 + 64)))
            for idx, kpos in self.label_overlay_positions.items():
                if idx != self.concentric:
                    r = kpos[2]
                    gc.DrawEllipse(kpos[0] - r, kpos[1] - r, r * 2, r * 2)
        else:
            gc.SetPen(wx.Pen(self.bgcolor, 0))
            gc.SetBrush(wx.Brush(self.bgcolormask))
            gc.DrawRectangle(0, 0, w, h)
        # Used to check exact position of keypad dots, should we ever resize the bg image
        # for idx, kpos in self.label_overlay_positions.items():
        #    dc.DrawCircle(kpos[0], kpos[1], kpos[2])

    # ------ #
    # Events #
    # ------ #
    def OnTopLevelKey(self, evt):
        # Let user press escape on any control, and return focus here
        if evt.GetKeyCode() == wx.WXK_ESCAPE:
            self.SetFocus()
        evt.Skip()

    def OnKey(self, evt):
        if not self.enabled:
            return
        if self.keypad_idx >= 0:
            if evt.GetKeyCode() == wx.WXK_TAB:
                self.setKeypadIndex(self.cycleKeypadIndex())
            elif evt.GetKeyCode() == wx.WXK_UP:
                self.quadrant = 1
            elif evt.GetKeyCode() == wx.WXK_DOWN:
                self.quadrant = 3
            elif evt.GetKeyCode() == wx.WXK_LEFT:
                self.quadrant = 2
            elif evt.GetKeyCode() == wx.WXK_RIGHT:
                self.quadrant = 0
            elif evt.GetKeyCode() == wx.WXK_PAGEUP:
                self.quadrant = 4
            elif evt.GetKeyCode() == wx.WXK_PAGEDOWN:
                self.quadrant = 5
            else:
                evt.Skip()
                return

            self.concentric = self.keypad_idx
            x, y, z = self.getMovement()

            if x != 0 or y != 0 and self.moveCallback:
                self.moveCallback(x, y)
            if z != 0 and self.zCallback:
                self.zCallback(z)
        elif evt.GetKeyCode() == wx.WXK_SPACE:
            self.spacebarCallback()

    def OnMotion(self, event):
        if not self.enabled:
            return

        oldcorner = self.corner
        oldq, oldc = self.quadrant, self.concentric

        mpos = event.GetPosition()
        idx = self.mouseOverKeypad(mpos)
        self.quadrant = None
        self.concentric = None
        if idx is None:
            center = wx.Point(self.center[0], self.center[1])
            riseDist = self.distanceToLine(mpos, center.x - 1, center.y - 1, center.x + 1, center.y + 1)
            fallDist = self.distanceToLine(mpos, center.x - 1, center.y + 1, center.x + 1, center.y - 1)
            self.quadrant, self.concentric = self.getQuadrantConcentricFromPosition(mpos)

            # If mouse hovers in space between quadrants, don't commit to a quadrant
            if riseDist <= self.spacer or fallDist <= self.spacer:
                self.quadrant = None

        cx, cy = self.center
        if mpos.x < cx and mpos.y < cy:
            self.corner = 0
        if mpos.x >= cx and mpos.y < cy:
            self.corner = 1
        if mpos.x >= cx and mpos.y >= cy:
            self.corner = 2
        if mpos.x < cx and mpos.y >= cy:
            self.corner = 3

        if oldq != self.quadrant or oldc != self.concentric or oldcorner != self.corner:
            self.update()

    def OnLeftDown(self, event):
        if not self.enabled:
            return

        # Take focus when clicked so that arrow keys can control movement
        self.SetFocus()

        mpos = event.GetPosition()

        idx = self.mouseOverKeypad(mpos)
        if idx is None:
            self.quadrant, self.concentric = self.getQuadrantConcentricFromPosition(mpos)
            if self.concentric is not None:
                if self.concentric < len(self.concentric_circle_radii):
                    if self.concentric == 0:
                        self.lastCorner = -1
                        self.lastMove = None
                        self.cornerCallback(self.corner_to_axis[-1])
                    elif self.quadrant is not None:
                        x, y, z = self.getMovement()
                        if self.moveCallback:
                            self.lastMove = (x, y)
                            self.lastCorner = None
                            self.moveCallback(x, y)
                elif self.corner is not None:
                    if self.cornerCallback:
                        self.lastCorner = self.corner
                        self.lastMove = None
                        self.cornerCallback(self.corner_to_axis[self.corner])
        else:
            if self.keypad_idx == idx:
                self.setKeypadIndex(-1)
            else:
                self.setKeypadIndex(idx)

    def OnLeaveWindow(self, evt):
        self.quadrant = None
        self.concentric = None
        self.update()

class XYButtonsMini(XYButtons):
    imagename = "control_mini.png"
    center = (57, 56.5)
    concentric_circle_radii = [0, 30.3]
    corner_inset = (5, 5)
    corner_size = (50, 50)
    outer_radius = 31
    corner_to_axis = {
        0: "x",
        1: "z",
        2: "y",
        3: "center",
    }

    def bind_events(self):
        # Set up mouse and keyboard event capture
        self.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
        self.Bind(wx.EVT_LEFT_DCLICK, self.OnLeftDown)
        self.Bind(wx.EVT_MOTION, self.OnMotion)
        self.Bind(wx.EVT_LEAVE_WINDOW, self.OnLeaveWindow)

    def OnMotion(self, event):
        if not self.enabled:
            return

        oldcorner = self.corner
        oldq, oldc = self.quadrant, self.concentric

        mpos = event.GetPosition()

        self.quadrant, self.concentric = self.getQuadrantConcentricFromPosition(mpos)

        cx, cy = XYButtonsMini.center
        if mpos.x < cx and mpos.y < cy:
            self.corner = 0
        if mpos.x >= cx and mpos.y < cy:
            self.corner = 1
        if mpos.x >= cx and mpos.y >= cy:
            self.corner = 2
        if mpos.x < cx and mpos.y >= cy:
            self.corner = 3

        if oldq != self.quadrant or oldc != self.concentric or oldcorner != self.corner:
            self.update()

    def OnLeftDown(self, event):
        if not self.enabled:
            return

        # Take focus when clicked so that arrow keys can control movement
        self.SetFocus()

        mpos = event.GetPosition()

        self.quadrant, self.concentric = self.getQuadrantConcentricFromPosition(mpos)
        if self.concentric is not None:
            if self.concentric < len(self.concentric_circle_radii):
                self.cornerCallback("all")
            elif self.corner is not None:
                if self.cornerCallback:
                    self.lastCorner = self.corner
                    self.lastMove = None
                    self.cornerCallback(self.corner_to_axis[self.corner])

    def drawCorner(self, gc, x, y, angle = 0.0):
        w, h = self.corner_size

        gc.PushState()
        gc.Translate(x, y)
        gc.Rotate(angle)
        path = gc.CreatePath()
        path.MoveToPoint(-w / 2, -h / 2)
        path.AddLineToPoint(w / 2, -h / 2)
        path.AddLineToPoint(w / 2, -h / 2 + h / 4)
        path.AddArc(w / 2, h / 2, self.outer_radius, 3 * math.pi / 2, math.pi, False)
        path.AddLineToPoint(-w / 2, h / 2)
        path.AddLineToPoint(-w / 2, -h / 2)
        gc.DrawPath(path)
        gc.PopState()

    def draw(self, dc, w, h):
        dc.SetBackground(wx.Brush(self.bgcolor))
        dc.Clear()
        gc = wx.GraphicsContext.Create(dc)

        if self.bg_bmp:
            w, h = (self.bg_bmp.GetWidth(), self.bg_bmp.GetHeight())
            gc.DrawBitmap(self.bg_bmp, 0, 0, w, h)

        if self.enabled and self.IsEnabled():
            # Brush and pen for grey overlay when mouse hovers over
            gc.SetPen(wx.Pen(wx.Colour(100, 100, 100, 172), 4))
            gc.SetBrush(wx.Brush(wx.Colour(0, 0, 0, 128)))

            if self.concentric is not None:
                if self.concentric < len(self.concentric_circle_radii):
                    self.drawCenteredDisc(gc, self.concentric_circle_radii[-1])
                elif self.corner is not None:
                    self.highlightCorner(gc, self.corner)
        else:
            gc.SetPen(wx.Pen(self.bgcolor, 0))
            gc.SetBrush(wx.Brush(self.bgcolormask))
            gc.DrawRectangle(0, 0, w, h)
