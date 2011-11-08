import wx, os, math
from bufferedcanvas import *

def imagefile(filename):
    return os.path.join(os.path.dirname(__file__), "images", filename)

def sign(n):
    if n < 0: return -1
    elif n > 0: return 1
    else: return 0

class ZButtons(BufferedCanvas):
    button_ydistances = [8, 30, 56, 84, 118]
    center = (32, 146)

    def __init__(self, parent, moveCallback=None, homeCallback=None, ID=-1):
        self.bg_bmp = wx.Image(imagefile("control_z.png"),wx.BITMAP_TYPE_PNG).ConvertToBitmap()
        self.range = None
        self.direction = None
        self.orderOfMagnitudeIdx = 0 # 0 means '1', 1 means '10', 2 means '100', etc.
        self.moveCallback = moveCallback
        self.homeCallback = homeCallback

        BufferedCanvas.__init__(self, parent, ID)

        self.SetSize(wx.Size(87, 295))

        # Set up mouse and keyboard event capture
        self.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
        self.Bind(wx.EVT_LEFT_DCLICK, self.OnLeftDown)
        self.Bind(wx.EVT_MOTION, self.OnMotion)
        self.Bind(wx.EVT_LEAVE_WINDOW, self.OnLeaveWindow)

    def lookupRange(self, ydist):
        idx = -1
        for d in ZButtons.button_ydistances:
            if ydist < d:
                return idx
            idx += 1
        return None
    
    def highlight(self, dc, rng, dir):
        assert(rng >= -1 and rng <= 3)
        assert(dir >= -1 and dir <= 1)

        fudge = 11
        x = 0 + fudge
        w = 72 - fudge*2
        if rng >= 0:
            k = 1 if dir > 0 else 0
            y = ZButtons.center[1] - (dir * ZButtons.button_ydistances[rng+k])
            h = ZButtons.button_ydistances[rng+1] - ZButtons.button_ydistances[rng]
            dc.DrawRectangle(x, y, w, h)
        # self.drawPartialPie(dc, center, r1-inner_ring_radius, r2-inner_ring_radius, a1+fudge, a2-fudge)
    
    def getRangeDir(self, pos):
        ydelta = ZButtons.center[1] - pos[1]
        return (self.lookupRange(abs(ydelta)), sign(ydelta))

    def OnMotion(self, event):
        oldr, oldd = self.range, self.direction

        mpos = event.GetPosition()
        self.range, self.direction = self.getRangeDir(mpos)

        if oldr != self.range or oldd != self.direction:
            self.update()

    def OnLeftDown(self, event):
        mpos = event.GetPosition()
        r, d = self.getRangeDir(mpos)
        if r >= 0:
            value = math.pow(10, self.orderOfMagnitudeIdx) * math.pow(10, r - 1) * d
            if self.moveCallback:
                self.moveCallback(value)
        else:
            if self.homeCallback:
                self.homeCallback()

    def OnLeaveWindow(self, evt):
        self.range = None
        self.direction = None
        self.update()

    def draw(self, dc):
        dc.SetPen(wx.Pen(wx.Colour(100,100,100,172), 4))
        dc.SetBrush(wx.Brush(wx.Colour(0,0,0,128)))

        dc.DrawBitmap(self.bg_bmp, 0, 0)

        if self.range != None and self.direction != None:
            self.highlight(dc, self.range, self.direction)

        return True
