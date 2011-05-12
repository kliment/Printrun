#!/usr/bin/env python
# "Weaver" Graphical Client
#(C) Jeremy Kajikawa 2011
#Licensed under GPLv2 and newer
#
import os, sys
from StringIO import StringIO
try:
    import printcore
except:
    from  printrun import printcore

try:
    import wx

    class AppWindow(wx.Frame):
        def __init__(self):
            wx.Frame.__init__(self, None, title="Weaver - [UI Template]")
            self.menustrip = wx.MenuBar()
            m = wx.Menu()
            self.Bind(wx.EVT_MENU, self.OnOther, m.Append(wx.ID_ANY," "," "))
            m.AppendSeparator()
            self.Bind(wx.EVT_MENU, self.OnExit, m.Append(wx.ID_EXIT,"Close"," Closes the Window"))
            self.menustrip.Append(m,"&Print")
            m = wx.Menu()
            self.Bind(wx.EVT_MENU, self.OnOther, m.Append(wx.ID_ANY," "," "))
            self.Bind(wx.EVT_MENU, self.OnOther, m.Append(wx.ID_ANY," "," "))
            self.menustrip.Append(m,"&Object")
            m = wx.Menu()
            self.Bind(wx.EVT_MENU, self.OnOther, m.Append(wx.ID_ANY,"&Wiki"," Http://www.reprap.org/wiki/Weaver"))
            m.AppendSeparator()
            self.Bind(wx.EVT_MENU, self.OnAbout, m.Append(wx.ID_ABOUT, "&About"," Information about this program"))
            self.menustrip.Append(m,"&Help")
            self.SetMenuBar(self.menustrip)

            self.vroot = wx.BoxSizer(wx.VERTICAL)

            self.CreateStatusBar()
            self.Show(True)

        def OnAbout(self,event):
            dlg = wx.MessageDialog( self, "Prusa - Mendel - RAMPS/Sanguinololu - Sprinter", "Weaver", wx.OK)
            dlg.ShowModal()
            dlg.Destroy()

        def OnOther(self,event):
            pass

        def OnExit(self,event):
            self.Close(True)

except:
    print("Library Failure -- Please install the wxPython Libraries")
    quit()

if __name__ == '__main__':
    app = wx.App(False)
    main = AppWindow()
    app.MainLoop()

