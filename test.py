import wx, os, math
from bufferedcanvas import *

def imagefile(filename):
    return os.path.join(os.path.dirname(__file__), "images", filename)

class XYButtons(BufferedCanvas):
    keypad_positions = {
        0: (102, 109),
        1: (78, 86),
        2: (49, 58)
    }
    concentric_circle_radii = [19, 45, 81, 120]
    center = (146, 149)
    distance = [
        # Order of Magnitude 0 (i.e. 0.1, 1, 10)
        [
            # Quadrant 0 (Right)
            [(0.1, 0), (1, 0), (10, 0)],
            # Quadrant 1 (Up)
            [(0, -0.1), (0, -1), (0, -10)],
            # Quadrant 2 (Left)
            [(-0.1, 0), (-1, 0), (-10, 0)],
            # Quadrant 3 (Down)
            [(0, 0.1), (0, 1), (0, 10)]
        ],
        # Order of Magnitude 1 (i.e. 1, 10, 100)
        [
            # Quadrant 0 (Right)
            [(1, 0), (10, 0), (100, 0)],
            # Quadrant 1 (Up)
            [(0, -1), (0, -10), (0, -100)],
            # Quadrant 2 (Left)
            [(-1, 0), (-10, 0), (-100, 0)],
            # Quadrant 3 (Down)
            [(0, 1), (0, 10), (0, 100)]
        ]
    ]

    def __init__(self, parent, ID=-1):
        self.bg_bmp = wx.Image(imagefile("control_xy.png"),wx.BITMAP_TYPE_PNG).ConvertToBitmap()
        self.keypad_bmp = wx.Image(imagefile("arrow_keys.png"),wx.BITMAP_TYPE_PNG).ConvertToBitmap()
        self.keypad_idx = 0
        self.orderOfMagnitude = 0
        self.quadrant = None
        self.concentric = None

        BufferedCanvas.__init__(self, parent, ID)

        # Set up mouse and keyboard event capture
        self.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
        self.Bind(wx.EVT_LEFT_DCLICK, self.OnLeftDown)
        self.Bind(wx.EVT_MOTION, self.OnMotion)
        parent.Bind(wx.EVT_CHAR_HOOK, self.onKey)
    
    def onKey(self, evt):
        if evt.GetKeyCode() == wx.WXK_TAB:
            self.setKeypadIndex(self.rotateKeypadIndex())
        elif evt.GetKeyCode() == wx.WXK_UP:
            print "Up key pressed"
        elif evt.GetKeyCode() == wx.WXK_DOWN:
            print "Down key pressed"
        elif evt.GetKeyCode() == wx.WXK_LEFT:
            print "Left key pressed"
        elif evt.GetKeyCode() == wx.WXK_RIGHT:
            print "Right key pressed"
        else:
            evt.Skip()
    
    def rotateKeypadIndex(self):
        idx = self.keypad_idx + 1
        if idx > 2: idx = 0
        return idx
    
    def lookupConcentric(self, radius):
        idx = -1
        for r in XYButtons.concentric_circle_radii:
            if radius < r:
                return idx
            idx += 1
        return 2
    
    def setKeypadIndex(self, idx):
        self.keypad_idx = idx
        self.update()
        # self.keypad_bmp.Move(XYButtons.keypad_positions[self.keypad_idx])
    
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
            rect = wx.Rect(kpos[0], kpos[1], 44, 32)
            if rect.Contains(mpos):
                return idx
        return None

    def OnMotion(self, event):
        oldq, oldc = self.quadrant, self.concentric

        mpos = event.GetPosition()
        idx = self.mouseOverKeypad(mpos)
        if idx != None:
            self.quadrant = None
            self.concentric = None
        else:
            self.quadrant, self.concentric = self.getQuadrantConcentricFromPosition(mpos)
        
        if oldq != self.quadrant or oldc != self.concentric:
            self.update()

    def OnLeftDown(self, event):
        mpos = event.GetPosition()

        idx = self.mouseOverKeypad(mpos)
        if idx != None:
            self.setKeypadIndex(idx)
        
        quadrant, concentric = self.getQuadrantConcentricFromPosition(mpos)
        # print 'click:', mpos, quadrant, concentric
        if concentric == -1:
            print 'center button'
        elif quadrant != None and concentric != None:
            dist = XYButtons.distance[self.orderOfMagnitude][quadrant][concentric]
            print 'x', dist[0], 'y', dist[1]
    
    def drawPartialPie(self, dc, center, r1, r2, angle1, angle2):
        parts = 64
        angle_dist = angle2 - angle1
        angle_inc = angle_dist / parts

        p1 = wx.Point(center.x + r1*math.cos(angle1), center.y + r1*math.sin(angle1))
        p2 = wx.Point(center.x + r2*math.cos(angle1), center.y + r2*math.sin(angle1))
        p3 = wx.Point(center.x + r2*math.cos(angle2), center.y + r2*math.sin(angle2))
        p4 = wx.Point(center.x + r1*math.cos(angle2), center.y + r1*math.sin(angle2))

        points = [p1, p2]

        points.extend([wx.Point(
            center.x + r1*math.cos(angle1+i*angle_inc),
            center.y + r1*math.sin(angle1+i*angle_inc)) for i in range(0, parts)])
        
        # points.extend([p3])

        points.extend([wx.Point(
            center.x + r2*math.cos(angle1+i*angle_inc),
            center.y + r2*math.sin(angle1+i*angle_inc)) for i in range(parts, 0, -1)])
        dc.DrawPolygon(points)
    
    def highlightQuadrant(self, dc, quadrant, concentric):
        assert(quadrant >= 0 and quadrant <= 3)
        assert(concentric >= 0 and concentric <= 2)

        inner_ring_radius = XYButtons.concentric_circle_radii[0]
        # fudge = math.pi*0.002
        fudge = 0
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
        self.drawPartialPie(dc, center, r1-inner_ring_radius, r2-inner_ring_radius, a1+fudge, a2-fudge)

    def draw(self, dc):
        # print 'draw called'
        dc.Clear()
        center = wx.Point(XYButtons.center[0], XYButtons.center[1])

        start = wx.Point(50, 0)
        end = wx.Point(0, 50)
        dc.SetPen(wx.Pen(wx.Colour(100,100,100,172), 4))
        dc.SetBrush(wx.Brush(wx.Colour(0,0,0,128)))

        dc.DrawBitmap(self.bg_bmp, 0, 0)
        # dc.DrawArc(50, 0, 0, 50, XYButtons.center[0], XYButtons.center[1])
        # self.drawPartialPie(dc, center, 19, 44, -math.pi/4, math.pi/4)
        if self.concentric == -1:
            pass
        elif self.quadrant != None and self.concentric != None:
            self.highlightQuadrant(dc, self.quadrant, self.concentric)

        pos = XYButtons.keypad_positions[self.keypad_idx]
        dc.DrawBitmap(self.keypad_bmp, pos[0], pos[1])
        # dc.DrawArcPoint(start, end, center)
        return True


class MyFrame(wx.Frame):
    def __init__(self, parent, id, title):
        wx.Frame.__init__(self, parent, id, title, wx.DefaultPosition, wx.Size(800, 600))
        self.xy = XYButtons(self)


class MyApp(wx.App):
    def OnInit(self):
        frame = MyFrame(None, -1, 'test.py')
        frame.Show(True)
        frame.Centre()
        return True

app = MyApp(0)
app.MainLoop()