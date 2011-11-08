import wx, os, math
from bufferedcanvas import *

def imagefile(filename):
    return os.path.join(os.path.dirname(__file__), "images", filename)

def sign(n):
    if n < 0: return -1
    elif n > 0: return 1
    else: return 0

class XYButtons(BufferedCanvas):
    keypad_positions = {
        0: (126, 126),
        1: (100, 100),
        2: (80, 80),
        3: (60, 60)
    }
    concentric_circle_radii = [15, 55, 86, 117, 142]
    center = (166, 164)

    def __init__(self, parent, moveCallback=None, ID=-1):
        self.bg_bmp = wx.Image(imagefile("control_xy.png"),wx.BITMAP_TYPE_PNG).ConvertToBitmap()
        self.keypad_bmp = wx.Image(imagefile("arrow_keys.png"),wx.BITMAP_TYPE_PNG).ConvertToBitmap()
        self.keypad_idx = -1
        self.quadrant = None
        self.concentric = None
        self.moveCallback = moveCallback

        BufferedCanvas.__init__(self, parent, ID)

        self.SetSize(wx.Size(335, 328))

        # Set up mouse and keyboard event capture
        self.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
        self.Bind(wx.EVT_LEFT_DCLICK, self.OnLeftDown)
        self.Bind(wx.EVT_MOTION, self.OnMotion)
        self.Bind(wx.EVT_LEAVE_WINDOW, self.OnLeaveWindow)
        self.Bind(wx.EVT_KEY_UP, self.onKey)
        wx.GetTopLevelParent(self).Bind(wx.EVT_CHAR_HOOK, self.onTopLevelKey)
    
    def onTopLevelKey(self, evt):
        # Let user press escape on any control, and return focus here
        if evt.GetKeyCode() == wx.WXK_ESCAPE:
            self.SetFocus()            
        evt.Skip()

    def onKey(self, evt):
        if self.keypad_idx >= 0:
            if evt.GetKeyCode() == wx.WXK_TAB:
                self.setKeypadIndex(self.rotateKeypadIndex())
            elif evt.GetKeyCode() == wx.WXK_UP:
                self.quadrant = 1
            elif evt.GetKeyCode() == wx.WXK_DOWN:
                self.quadrant = 3
            elif evt.GetKeyCode() == wx.WXK_LEFT:
                self.quadrant = 2
            elif evt.GetKeyCode() == wx.WXK_RIGHT:
                self.quadrant = 0
            else:
                evt.Skip()
                return
            
            if self.moveCallback:
                self.concentric = self.keypad_idx
                x, y = self.getMovement()
                self.moveCallback(x, y)
            evt.Skip()

    
    def rotateKeypadIndex(self):
        idx = self.keypad_idx + 1
        if idx > 2: idx = 0
        return idx
    
    def setKeypadIndex(self, idx):
        self.keypad_idx = idx
        self.update()
        # self.keypad_bmp.Move(XYButtons.keypad_positions[self.keypad_idx])
    
    def getMovement(self):
        xdir = [1, 0, -1, 0][self.quadrant]
        ydir = [0, 1, 0, -1][self.quadrant]
        magnitude = math.pow(10, self.concentric-1)
        return (magnitude * xdir, magnitude * ydir)
    
    def lookupConcentric(self, radius):
        idx = -1
        for r in XYButtons.concentric_circle_radii:
            if radius < r:
                return idx
            idx += 1
        return None

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
            rect = wx.Rect(kpos[0], kpos[1], self.keypad_bmp.GetWidth(), self.keypad_bmp.GetHeight())
            if rect.Contains(mpos):
                return idx
        return None

    def OnMotion(self, event):
        oldq, oldc = self.quadrant, self.concentric

        mpos = event.GetPosition()
        idx = self.mouseOverKeypad(mpos)
        self.quadrant = None
        self.concentric = None
        if idx == None:
            center = wx.Point(XYButtons.center[0], XYButtons.center[1])
            riseDist = self.distanceToLine(mpos, center.x-1, center.y-1, center.x+1, center.y+1)
            fallDist = self.distanceToLine(mpos, center.x-1, center.y+1, center.x+1, center.y-1)
            if riseDist > 10 and fallDist > 10:
                self.quadrant, self.concentric = self.getQuadrantConcentricFromPosition(mpos)
        
        if oldq != self.quadrant or oldc != self.concentric:
            self.update()

    def OnLeftDown(self, event):
        # Take focus when clicked so that arrow keys can control movement
        self.SetFocus()

        mpos = event.GetPosition()

        idx = self.mouseOverKeypad(mpos)
        if idx == None:
            self.quadrant, self.concentric = self.getQuadrantConcentricFromPosition(mpos)
            if self.quadrant != None and self.concentric != None:
                x, y = self.getMovement()
                if self.moveCallback:
                    self.moveCallback(x, y)
        else:
            if self.keypad_idx == idx:
                self.setKeypadIndex(-1)
            else:
                self.setKeypadIndex(idx)
    
    def OnLeaveWindow(self, evt):
        self.quadrant = None
        self.concentric = None
        self.update()
    
    def drawPartialPie(self, gc, center, r1, r2, angle1, angle2):
        parts = 64
        angle_dist = angle2 - angle1
        angle_inc = angle_dist / parts

        p1 = wx.Point(center.x + r1*math.cos(angle1), center.y + r1*math.sin(angle1))
        
        path = gc.CreatePath()
        path.MoveToPoint(p1.x, p1.y)
        path.AddArc(center.x, center.y, r1, angle1, angle2, True)
        path.AddArc(center.x, center.y, r2, angle2, angle1, False)
        path.AddLineToPoint(p1.x, p1.y)
        gc.DrawPath(path)
    
    def distanceToLine(self, pos, x1, y1, x2, y2):
        xlen = x2 - x1
        ylen = y2 - y1
        pxlen = x1 - pos.x
        pylen = y1 - pos.y
        return abs(xlen*pylen-ylen*pxlen)/math.sqrt(xlen**2+ylen**2)
    
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

    def draw(self, dc, w, h):
        dc.Clear()
        gc = wx.GraphicsContext.Create(dc)

        center = wx.Point(XYButtons.center[0], XYButtons.center[1])

        gc.DrawBitmap(self.bg_bmp, 0, 0, self.bg_bmp.GetWidth(), self.bg_bmp.GetHeight())

        if self.quadrant != None and self.concentric != None:
            gc.SetPen(wx.Pen(wx.Colour(100,100,100,172), 4))
            gc.SetBrush(wx.Brush(wx.Colour(0,0,0,128)))
            self.highlightQuadrant(gc, self.quadrant, self.concentric)
        
        if self.keypad_idx >= 0:
            pos = XYButtons.keypad_positions[self.keypad_idx]
            gc.DrawBitmap(self.keypad_bmp, pos[0], pos[1], self.keypad_bmp.GetWidth(), self.keypad_bmp.GetHeight())
        
        return True
