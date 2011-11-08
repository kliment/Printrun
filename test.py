import wx, os, math
from bufferedcanvas import *

from xybuttons import XYButtons
from zbuttons import ZButtons

class MyFrame(wx.Frame):
    def __init__(self, parent, id, title):
        wx.Frame.__init__(self, parent, id, title, wx.DefaultPosition, wx.Size(600, 400))
        sizer = wx.BoxSizer()
        self.xy = XYButtons(self, moveCallback=self.moveXY)
        sizer.Add(self.xy, flag=wx.ALIGN_CENTER)
        self.z = ZButtons(self, moveCallback=self.moveZ)
        sizer.Add(self.z, flag=wx.ALIGN_CENTER)

        self.SetSizer(sizer)
        self.SetBackgroundColour("white")
    
    def moveXY(self, x, y):
        print "got x", x, 'y', y
    
    def moveZ(self, z):
        print "got z", z


class MyApp(wx.App):
    def OnInit(self):
        frame = MyFrame(None, -1, 'test.py')
        frame.Show(True)
        frame.Centre()
        return True

app = MyApp(0)
app.MainLoop()