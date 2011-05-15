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
            wx.Frame.__init__(self, None, title="Weaver")

            self.menustrip = wx.MenuBar()
            m = wx.Menu()
            self.Bind(wx.EVT_MENU, self.OnLoadOpts, m.Append(wx.ID_ANY,"&Load Options"," Load Configuration Settings"))
            self.Bind(wx.EVT_MENU, self.OnSaveOpts, m.Append(wx.ID_ANY,"&Save Options"," Save Configuration Settings"))
            m.AppendSeparator()
            self.Bind(wx.EVT_MENU, self.OnExit, m.Append(wx.ID_EXIT,"Close"," Closes the Window"))
            self.menustrip.Append(m,"&Print")
            m = wx.Menu()
            self.Bind(wx.EVT_MENU, self.OnPass, m.Append(wx.ID_ANY," "," "))
            self.menustrip.Append(m,"&Object")
            m = wx.Menu()
            self.Bind(wx.EVT_MENU, self.OnWiki, m.Append(wx.ID_ANY,"&Wiki"," Http://www.reprap.org/wiki/Weaver"))
            m.AppendSeparator()
            self.Bind(wx.EVT_MENU, self.OnAbout, m.Append(wx.ID_ABOUT, "&About"," Information about this program"))
            self.menustrip.Append(m,"&Help")
            self.SetMenuBar(self.menustrip)

            self.vlayout = wx.BoxSizer(wx.VERTICAL)
            hbox = wx.BoxSizer(wx.HORIZONTAL)
            hbox.Add(wx.StaticText(self, -1, "Device :", style=wx.ALIGN_CENTRE), 0, wx.ALL, 1)
            self.SerialPort = wx.ComboBox(self, -1,
                choices=["/dev/ttyUSB0", "serial.device/0", "COM1"],
                style=wx.CB_SIMPLE|wx.CB_DROPDOWN|wx.CB_SORT)
            hbox.Add(self.SerialPort, 0, wx.ALL, 1)
            hbox.Add(wx.StaticText(self, -1, "Speed :", style=wx.ALIGN_CENTRE), 0, wx.ALL, 1)
            self.SerialSpeed = wx.ComboBox(self, -1,
                choices=["2400", "9600", "19200", "38400", "57600", "115200"],
                style=wx.CB_SIMPLE|wx.CB_DROPDOWN|wx.CB_READONLY|wx.CB_SORT)
            hbox.Add(self.SerialSpeed, 0, wx.ALL, 1)
            self.vlayout.Add(hbox, 0, wx.ALL|wx.EXPAND|wx.ALIGN_CENTER_HORIZONTAL, 1)
            self.hlayout = wx.BoxSizer(wx.HORIZONTAL)
            vbox = wx.BoxSizer(wx.VERTICAL)
            # GCode Shell
            self.ShellHistory = []
            # Tweak This for improved Response Display
            self.ShellView = wx.TextCtrl(self, size=(200, 80))
            vbox.Add(self.ShellView, 0, wx.ALL, 0)
            # Using a ComboBox selection for History
            self.ShellProc = wx.ComboBox(self, -1,
                choices = self.ShellHistory,
                style=wx.CB_SIMPLE|wx.CB_DROPDOWN|wx.CB_SORT)
            vbox.Add(self.ShellProc, 0, wx.ALL, 1)
            # Clear or Send Command String
            hbox = wx.BoxSizer(wx.HORIZONTAL)
            self.ShellClear = wx.Button(self, wx.ID_ANY, 'Clear')
            hbox.Add(self.ShellClear, 0, wx.ALL, 1)
            self.ShellSend = wx.Button(self, wx.ID_ANY, 'Send')
            hbox.Add(self.ShellSend, 0, wx.ALL, 1)
            vbox.Add(hbox, 1, wx.ALL, 1)
            self.hlayout.Add(vbox, 1, wx.ALL, 1)
            #
            vbox = wx.BoxSizer(wx.VERTICAL)
            # Workflow
            hbox = wx.BoxSizer(wx.HORIZONTAL)
            self.LoadSTL = wx.Button(self, wx.ID_ANY, 'Load STL')
            hbox.Add(self.LoadSTL, 0, wx.ALL, 0)
            self.LoadGCode = wx.Button(self, wx.ID_ANY, 'Load GCode')
            hbox.Add(self.LoadGCode, 0, wx.ALL, 0)
            vbox.Add(hbox, 0, wx.ALL, 1)
            hbox = wx.BoxSizer(wx.HORIZONTAL)
            self.PrintCancel = wx.ToggleButton(self, wx.ID_ANY, 'Print')
            hbox.Add(self.PrintCancel, 0, wx.ALL, 0)
            self.PauseResume = wx.ToggleButton(self, wx.ID_ANY, 'Pause')
            hbox.Add(self.PauseResume, 0, wx.ALL, 0)
            vbox.Add(hbox, 0, wx.ALL, 1)
            hbox = wx.BoxSizer(wx.HORIZONTAL)
            vbox.Add(hbox, 0, wx.ALL, 1)
            self.hlayout.Add(vbox, 1, wx.ALL, 1)

            #
            vbox = wx.BoxSizer(wx.VERTICAL)
            # Wxyz
            self.hlayout.Add(vbox, 1, wx.ALL, 1)

            self.vlayout.Add(self.hlayout, 1, wx.ALL|wx.EXPAND|wx.ALIGN_CENTER_HORIZONTAL, 1)
            self.CreateStatusBar()

            self.SetSizer(self.vlayout)
            self.vlayout.Fit(self)
            self.Layout()

            self.EventBinding()

            self.Centre()
            self.Show(True)

        def EventBinding(self):
            pass

        def OnAbout(self,event):
            dlg = wx.MessageDialog( self, "Prusa - Mendel - RAMPS - Sprinter", "About Weaver", wx.OK)
            dlg.ShowModal()
            dlg.Destroy()

        def OnLoadOpts(self,event):
            pass

        def OnSaveOpts(self,event):
            pass

        def OnWiki(self,event):
            pass

        def OnPass(self,event):
            pass

        def OnExit(self,event):
            self.Close(True)

        def OnShellProc(self,event):
            pass

        def OnShellClear(self,event):
            pass

        def OnShellSend(self,event):
            pass

except:
    print("Library Failure -- Please install the wxPython Libraries")
    quit()

if __name__ == '__main__':
    app = wx.App(False)
    main = AppWindow()
    app.MainLoop()

