import wx, os, math

def imagefile(filename):
    return os.path.join(os.path.dirname(__file__), "images", filename)


class XYButtons(wx.StaticBitmap):
    keypad_positions = {
        0: (102, 109),
        1: (78, 86),
        2: (49, 58)
    }
    concentric_circle_radii = [19, 44, 80, 125]
    center = (145, 147)
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

    def __init__(self, parent):
        self.keypad_idx = 0
        self.orderOfMagnitude = 0

        # Set up background image
        bmp = wx.Image(imagefile("control_xy.png"),wx.BITMAP_TYPE_PNG).ConvertToBitmap()
        self.bg_bmp = wx.StaticBitmap.__init__(self, parent, -1, bmp, (0, 0))

        bmp = wx.Image(imagefile("arrow_keys.png"),wx.BITMAP_TYPE_PNG).ConvertToBitmap()
        self.keypad_bmp = wx.StaticBitmap(self, -1, bmp, XYButtons.keypad_positions[self.keypad_idx])

        # Set up mouse and keyboard event capture
        self.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
        self.Bind(wx.EVT_MOTION, self.OnMotion)
        parent.Bind(wx.EVT_CHAR_HOOK, self.onKey)
        
        # Paint
        self.Bind(wx.EVT_PAINT, self.OnPaint)

    
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
        self.keypad_bmp.Move(XYButtons.keypad_positions[self.keypad_idx])
    
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
        
    def OnMotion(self, event):
        mpos = event.GetPosition()
        quadrant, concentric = self.getQuadrantConcentricFromPosition(mpos)

        # print 'motion:', mpos, quadrant, concentric

    def OnLeftDown(self, event):
        mpos = event.GetPosition()
        for idx, kpos in XYButtons.keypad_positions.items():
            rect = wx.Rect(kpos[0], kpos[1], 44, 32)
            if rect.Contains(mpos):
                self.setKeypadIndex(idx)
        
        quadrant, concentric = self.getQuadrantConcentricFromPosition(mpos)
        print 'click:', mpos, quadrant, concentric
    
    def OnPaint(self, event):
        # wx.StaticBitmap.OnPaint(self, event)
        dc = wx.PaintDC(self)
        # dc.Clear()
        center = wx.Point(XYButtons.center[0], XYButtons.center[1])
        start = wx.Point(50, 0)
        end = wx.Point(0, 50)
        dc.SetPen(wx.Pen(wx.Colour(0,0,0), 4))
        dc.SetBrush(wx.Brush(wx.Colour(255,0,0)))
        dc.DrawArcPoint(start, end, center)
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

# def main():
#     app = wx.App()

#     frame = wx.Frame(None, title='Icon', pos=(350,300))
#     # frame.SetIcon(wx.Icon('tipi.ico', wx.BITMAP_TYPE_ICO))
#     frame.Center()
#     frame.Show()
    
#     panel = wx.Panel(self, -1)
#     button = wx.Button(panel, -1, "Button1", (0,0))
#     # wx.Image('stock_exit-16.png',wx.BITMAP_TYPE_PNG).ConvertToBitmap()

#     app.MainLoop()

app = MyApp(0)
app.MainLoop()