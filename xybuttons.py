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

import wx, os, math
from bufferedcanvas import *


def imagefile(filename):
    if os.path.exists(os.path.join(os.path.dirname(__file__), "images", filename)):
        return os.path.join(os.path.dirname(__file__), "images", filename)
    else:
        return os.path.join(os.path.split(os.path.split(__file__)[0])[0], "images", filename)
    
def sign(n):
    if n < 0: return -1
    elif n > 0: return 1
    else: return 0

class XYButtons(BufferedCanvas):
    keypad_positions = {
        0: (105, 102),
        1: (86, 83),
        2: (68, 65),
        3: (53, 50)
    }
    corner_size = (49, 49)
    corner_inset = (8, 6)
    label_overlay_positions = {
        0: (142, 105, 11),
        1: (160, 85, 13),
        2: (179, 65, 15),
        3: (201, 42, 16)
    }
    concentric_circle_radii = [11, 45, 69, 94, 115]
    center = (124, 121)
    spacer = 7

    def __init__(self, parent, moveCallback=None, cornerCallback=None, ID=-1):
        self.bg_bmp = wx.Image(imagefile("control_xy.png"),wx.BITMAP_TYPE_PNG).ConvertToBitmap()
        self.keypad_bmp = wx.Image(imagefile("arrow_keys.png"),wx.BITMAP_TYPE_PNG).ConvertToBitmap()
        self.keypad_idx = -1
        self.quadrant = None
        self.concentric = None
        self.corner = None
        self.moveCallback = moveCallback
        self.cornerCallback = cornerCallback
        self.enabled = False
    
        BufferedCanvas.__init__(self, parent, ID)
        self.SetSize(self.bg_bmp.GetSize())

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
    
    def distanceToLine(self, pos, x1, y1, x2, y2):
        xlen = x2 - x1
        ylen = y2 - y1
        pxlen = x1 - pos.x
        pylen = y1 - pos.y
        return abs(xlen*pylen-ylen*pxlen)/math.sqrt(xlen**2+ylen**2)
    
    def distanceToPoint(self, x1, y1, x2, y2):
        return math.sqrt((x1-x2)**2 + (y1-y2)**2)

    def cycleKeypadIndex(self):
        idx = self.keypad_idx + 1
        if idx > 2: idx = 0
        return idx
    
    def setKeypadIndex(self, idx):
        self.keypad_idx = idx
        self.update()
    
    def getMovement(self):
        xdir = [1, 0, -1, 0][self.quadrant]
        ydir = [0, 1, 0, -1][self.quadrant]
        magnitude = math.pow(10, self.concentric-1)
        return (magnitude * xdir, magnitude * ydir)
    
    def lookupConcentric(self, radius):
        idx = 0
        for r in XYButtons.concentric_circle_radii[1:]:
            if radius < r:
                return idx
            idx += 1
        return len(XYButtons.concentric_circle_radii)

    def getQuadrantConcentricFromPosition(self, pos):
        rel_x = pos[0] - XYButtons.center[0]
        rel_y = pos[1] - XYButtons.center[1]
        radius = math.sqrt(rel_x**2 + rel_y**2)
        if rel_x > rel_y and rel_x > -rel_y:
            quadrant = 0 # Right
        elif rel_x <= rel_y and rel_x > -rel_y:
            quadrant = 3 # Down
        elif rel_x > rel_y and rel_x < -rel_y:
            quadrant = 1 # Up
        else:
            quadrant = 2 # Left
        
        idx = self.lookupConcentric(radius)
        return (quadrant, idx)
    
    def mouseOverKeypad(self, mpos):
        for idx, kpos in XYButtons.keypad_positions.items():
            radius = self.distanceToPoint(mpos[0], mpos[1], kpos[0], kpos[1])
            if radius < 9:
                return idx
        return None
    
    def drawPartialPie(self, gc, center, r1, r2, angle1, angle2):
        p1 = wx.Point(center.x + r1*math.cos(angle1), center.y + r1*math.sin(angle1))
        
        path = gc.CreatePath()
        path.MoveToPoint(p1.x, p1.y)
        path.AddArc(center.x, center.y, r1, angle1, angle2, True)
        path.AddArc(center.x, center.y, r2, angle2, angle1, False)
        path.AddLineToPoint(p1.x, p1.y)
        gc.DrawPath(path)
    
    def highlightQuadrant(self, gc, quadrant, concentric):
        assert(quadrant >= 0 and quadrant <= 3)
        assert(concentric >= 0 and concentric <= 3)

        inner_ring_radius = XYButtons.concentric_circle_radii[0]
        # fudge = math.pi*0.002
        fudge = -0.02
        center = wx.Point(XYButtons.center[0], XYButtons.center[1])
        if quadrant == 0:
            a1, a2 = (-math.pi*0.25, math.pi*0.25)
            center.x += inner_ring_radius
        elif quadrant == 1:
            a1, a2 = (math.pi*1.25, math.pi*1.75)
            center.y -= inner_ring_radius
        elif quadrant == 2:
            a1, a2 = (math.pi*0.75, math.pi*1.25)
            center.x -= inner_ring_radius
        elif quadrant == 3:
            a1, a2 = (math.pi*0.25, math.pi*0.75)
            center.y += inner_ring_radius
        
        r1 = XYButtons.concentric_circle_radii[concentric]
        r2 = XYButtons.concentric_circle_radii[concentric+1]

        self.drawPartialPie(gc, center, r1-inner_ring_radius, r2-inner_ring_radius, a1+fudge, a2-fudge)
    
    def drawCorner(self, gc, x, y, angle=0.0):
        w, h = XYButtons.corner_size

        gc.PushState()
        gc.Translate(x, y)
        gc.Rotate(angle)
        path = gc.CreatePath()
        path.MoveToPoint(-w/2, -h/2)
        path.AddLineToPoint(w/2, -h/2)
        path.AddLineToPoint(w/2, -h/2+h/3)
        path.AddLineToPoint(-w/2+w/3, h/2)
        path.AddLineToPoint(-w/2, h/2)
        path.AddLineToPoint(-w/2, -h/2)
        gc.DrawPath(path)
        gc.PopState()

    def highlightCorner(self, gc, corner=0):
        w, h = XYButtons.corner_size
        cx, cy = XYButtons.center
        ww, wh = self.GetSizeTuple()
        
        inset = 10
        if corner == 0:
            x, y = (cx - ww/2 + inset, cy - wh/2 + inset)
            self.drawCorner(gc, x+w/2, y+h/2, 0)
        elif corner == 1:
            x, y = (cx + ww/2 - inset, cy - wh/2 + inset)
            self.drawCorner(gc, x-w/2, y+h/2, math.pi/2)
        elif corner == 2:
            x, y = (cx + ww/2 - inset, cy + wh/2 - inset)
            self.drawCorner(gc, x-w/2, y-h/2, math.pi)
        elif corner == 3:
            x, y = (cx - ww/2 + inset, cy + wh/2 - inset)
            self.drawCorner(gc, x+w/2, y-h/2, math.pi*3/2)
        

    def draw(self, dc, w, h):
        dc.Clear()
        gc = wx.GraphicsContext.Create(dc)

        center = wx.Point(XYButtons.center[0], XYButtons.center[1])
        if self.bg_bmp:
            w, h = (self.bg_bmp.GetWidth(), self.bg_bmp.GetHeight())
            gc.DrawBitmap(self.bg_bmp, 0, 0, w, h)
        
        if self.enabled:
            # Brush and pen for grey overlay when mouse hovers over
            gc.SetPen(wx.Pen(wx.Colour(100,100,100,172), 4))
            gc.SetBrush(wx.Brush(wx.Colour(0,0,0,128)))

            if self.concentric != None:
                if self.concentric < len(XYButtons.concentric_circle_radii):
                    if self.quadrant != None:
                        self.highlightQuadrant(gc, self.quadrant, self.concentric)
                elif self.corner != None:
                    self.highlightCorner(gc, self.corner)
            
            if self.keypad_idx >= 0:
                padw, padh = (self.keypad_bmp.GetWidth(), self.keypad_bmp.GetHeight())
                pos = XYButtons.keypad_positions[self.keypad_idx]
                pos = (pos[0] - padw/2 - 3, pos[1] - padh/2 - 3)
                gc.DrawBitmap(self.keypad_bmp, pos[0], pos[1], padw, padh)
            
            # Draw label overlays
            gc.SetPen(wx.Pen(wx.Colour(255,255,255,128), 1))
            gc.SetBrush(wx.Brush(wx.Colour(255,255,255,128+64)))
            for idx, kpos in XYButtons.label_overlay_positions.items():
                if idx != self.concentric:
                    r = kpos[2]
                    gc.DrawEllipse(kpos[0]-r, kpos[1]-r, r*2, r*2)
        else:
            gc.SetPen(wx.Pen(wx.Colour(255,255,255,0), 4))
            gc.SetBrush(wx.Brush(wx.Colour(255,255,255,128)))
            gc.DrawRectangle(0, 0, w, h)
        

        # Used to check exact position of keypad dots, should we ever resize the bg image
        # for idx, kpos in XYButtons.label_overlay_positions.items():
        #    dc.DrawCircle(kpos[0], kpos[1], kpos[2])

    ## ------ ##
    ## Events ##
    ## ------ ##

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
            elif evt.GetKeyCode() == wx.WXK_SPACE:
                pass
            else:
                evt.Skip()
                return
            
            if self.moveCallback:
                self.concentric = self.keypad_idx
                x, y = self.getMovement()
                self.moveCallback(x, y)

    def OnMotion(self, event):
        if not self.enabled:
            return
        
        oldcorner = self.corner
        oldq, oldc = self.quadrant, self.concentric

        mpos = event.GetPosition()
        idx = self.mouseOverKeypad(mpos)
        self.quadrant = None
        self.concentric = None
        if idx == None:
            center = wx.Point(XYButtons.center[0], XYButtons.center[1])
            riseDist = self.distanceToLine(mpos, center.x-1, center.y-1, center.x+1, center.y+1)
            fallDist = self.distanceToLine(mpos, center.x-1, center.y+1, center.x+1, center.y-1)
            self.quadrant, self.concentric = self.getQuadrantConcentricFromPosition(mpos)

            # If mouse hovers in space between quadrants, don't commit to a quadrant
            if riseDist <= XYButtons.spacer or fallDist <= XYButtons.spacer:
                self.quadrant = None
        
        cx, cy = XYButtons.center
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
        if idx == None:
            self.quadrant, self.concentric = self.getQuadrantConcentricFromPosition(mpos)
            if self.concentric != None:
                if self.concentric < len(XYButtons.concentric_circle_radii):
                    if self.quadrant != None:
                        x, y = self.getMovement()
                        if self.moveCallback:
                            self.moveCallback(x, y)
                elif self.corner != None:
                    if self.cornerCallback:
                        self.cornerCallback(self.corner)
        else:
            if self.keypad_idx == idx:
                self.setKeypadIndex(-1)
            else:
                self.setKeypadIndex(idx)
    
    def OnLeaveWindow(self, evt):
        self.quadrant = None
        self.concentric = None
        self.update()
