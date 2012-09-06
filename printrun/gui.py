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

try:
    import wx
except:
    print _("WX is not installed. This program requires WX to run.")
    raise

global buttonSize
buttonSize = (70, 25)  # Define sizes for the buttons on top rows

from printrun import gviz
from printrun.xybuttons import XYButtons
from printrun.zbuttons import ZButtons
from printrun.graph import Graph

def make_button(parent, label, callback, tooltip, container = None, size = wx.DefaultSize, style = 0):
    button = wx.Button(parent, -1, label, style = style, size = size)
    button.Bind(wx.EVT_BUTTON, callback)
    button.SetToolTip(wx.ToolTip(tooltip))
    if container:
        container.Add(button)
    return button

def make_sized_button(*args):
    return make_button(*args, size = buttonSize)

def make_autosize_button(*args):
    return make_button(*args, size = (-1, buttonSize[1]), style = wx.BU_EXACTFIT)

class XYZControlsSizer(wx.GridBagSizer):

    def __init__(self, root):
        super(XYZControlsSizer, self).__init__()
        root.xyb = XYButtons(root.panel, root.moveXY, root.homeButtonClicked, root.spacebarAction, root.settings.bgcolor)
        self.Add(root.xyb, pos = (0, 1), flag = wx.ALIGN_CENTER)
        root.zb = ZButtons(root.panel, root.moveZ, root.settings.bgcolor)
        self.Add(root.zb, pos = (0, 2), flag = wx.ALIGN_CENTER)
        wx.CallAfter(root.xyb.SetFocus)

class LeftPane(wx.GridBagSizer):

    def __init__(self, root):
        super(LeftPane, self).__init__()
        llts = wx.BoxSizer(wx.HORIZONTAL)
        self.Add(llts, pos = (0, 0), span = (1, 9))
        self.xyzsizer = XYZControlsSizer(root)
        self.Add(self.xyzsizer, pos = (1, 0), span = (1, 8), flag = wx.ALIGN_CENTER)
        
        for i in root.cpbuttons:
            btn = make_button(root.panel, i.label, root.procbutton, i.tooltip, style = wx.BU_EXACTFIT)
            btn.SetBackgroundColour(i.background)
            btn.SetForegroundColour("black")
            btn.properties = i
            root.btndict[i.command] = btn
            root.printerControls.append(btn)
            if i.pos == None:
                if i.span == 0:
                    llts.Add(btn)
            else:
                self.Add(btn, pos = i.pos, span = i.span)

        root.xyfeedc = wx.SpinCtrl(root.panel,-1, str(root.settings.xy_feedrate), min = 0, max = 50000, size = (70,-1))
        root.xyfeedc.SetToolTip(wx.ToolTip("Set Maximum Speed for X & Y axes (mm/min)"))
        llts.Add(wx.StaticText(root.panel,-1, _("XY:")), flag = wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL)
        llts.Add(root.xyfeedc)
        llts.Add(wx.StaticText(root.panel,-1, _("mm/min   Z:")), flag = wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL)
        root.zfeedc = wx.SpinCtrl(root.panel,-1, str(root.settings.z_feedrate), min = 0, max = 50000, size = (70,-1))
        root.zfeedc.SetToolTip(wx.ToolTip("Set Maximum Speed for Z axis (mm/min)"))
        llts.Add(root.zfeedc,)

        root.monitorbox = wx.CheckBox(root.panel,-1, _("Watch"))
        root.monitorbox.SetToolTip(wx.ToolTip("Monitor Temperatures in Graph"))
        self.Add(root.monitorbox, pos = (2, 6))
        root.monitorbox.Bind(wx.EVT_CHECKBOX, root.setmonitor)

        self.Add(wx.StaticText(root.panel,-1, _("Heat:")), pos = (2, 0), span = (1, 1), flag = wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT)
        htemp_choices = [root.temps[i]+" ("+i+")" for i in sorted(root.temps.keys(), key = lambda x:root.temps[x])]

        root.settoff = make_button(root.panel, _("Off"), lambda e: root.do_settemp("off"), _("Switch Hotend Off"), size = (36,-1), style = wx.BU_EXACTFIT)
        root.printerControls.append(root.settoff)
        self.Add(root.settoff, pos = (2, 1), span = (1, 1))

        if root.settings.last_temperature not in map(float, root.temps.values()):
            htemp_choices = [str(root.settings.last_temperature)] + htemp_choices
        root.htemp = wx.ComboBox(root.panel, -1,
                choices = htemp_choices, style = wx.CB_DROPDOWN, size = (70,-1))
        root.htemp.SetToolTip(wx.ToolTip("Select Temperature for Hotend"))
        root.htemp.Bind(wx.EVT_COMBOBOX, root.htemp_change)

        self.Add(root.htemp, pos = (2, 2), span = (1, 2))
        root.settbtn = make_button(root.panel, _("Set"), root.do_settemp, _("Switch Hotend On"), size = (38, -1), style = wx.BU_EXACTFIT)
        root.printerControls.append(root.settbtn)
        self.Add(root.settbtn, pos = (2, 4), span = (1, 1))

        self.Add(wx.StaticText(root.panel,-1, _("Bed:")), pos = (3, 0), span = (1, 1), flag = wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT)
        btemp_choices = [root.bedtemps[i]+" ("+i+")" for i in sorted(root.bedtemps.keys(), key = lambda x:root.temps[x])]

        root.setboff = make_button(root.panel, _("Off"), lambda e:root.do_bedtemp("off"), _("Switch Heated Bed Off"), size = (36,-1), style = wx.BU_EXACTFIT)
        root.printerControls.append(root.setboff)
        self.Add(root.setboff, pos = (3, 1), span = (1, 1))

        if root.settings.last_bed_temperature not in map(float, root.bedtemps.values()):
            btemp_choices = [str(root.settings.last_bed_temperature)] + btemp_choices
        root.btemp = wx.ComboBox(root.panel, -1,
                choices = btemp_choices, style = wx.CB_DROPDOWN, size = (70,-1))
        root.btemp.SetToolTip(wx.ToolTip("Select Temperature for Heated Bed"))
        root.btemp.Bind(wx.EVT_COMBOBOX, root.btemp_change)
        self.Add(root.btemp, pos = (3, 2), span = (1, 2))

        root.setbbtn = make_button(root.panel, _("Set"), root.do_bedtemp, ("Switch Heated Bed On"), size = (38, -1), style = wx.BU_EXACTFIT)
        root.printerControls.append(root.setbbtn)
        self.Add(root.setbbtn, pos = (3, 4), span = (1, 1))

        root.btemp.SetValue(str(root.settings.last_bed_temperature))
        root.htemp.SetValue(str(root.settings.last_temperature))

        ## added for an error where only the bed would get (pla) or (abs).
        #This ensures, if last temp is a default pla or abs, it will be marked so.
        # if it is not, then a (user) remark is added. This denotes a manual entry

        for i in btemp_choices:
            if i.split()[0] == str(root.settings.last_bed_temperature).split('.')[0] or i.split()[0] == str(root.settings.last_bed_temperature):
                root.btemp.SetValue(i)
        for i in htemp_choices:
            if i.split()[0] == str(root.settings.last_temperature).split('.')[0] or i.split()[0] == str(root.settings.last_temperature) :
                root.htemp.SetValue(i)

        if( '(' not in root.btemp.Value):
            root.btemp.SetValue(root.btemp.Value + ' (user)')
        if( '(' not in root.htemp.Value):
            root.htemp.SetValue(root.htemp.Value + ' (user)')

        root.tempdisp = wx.StaticText(root.panel,-1, "")

        root.edist = wx.SpinCtrl(root.panel,-1, "5", min = 0, max = 1000, size = (60,-1))
        root.edist.SetBackgroundColour((225, 200, 200))
        root.edist.SetForegroundColour("black")
        self.Add(root.edist, pos = (4, 2), span = (1, 2))
        self.Add(wx.StaticText(root.panel,-1, _("mm")), pos = (4, 4), span = (1, 1))
        root.edist.SetToolTip(wx.ToolTip("Amount to Extrude or Retract (mm)"))
        root.efeedc = wx.SpinCtrl(root.panel,-1, str(root.settings.e_feedrate), min = 0, max = 50000, size = (60,-1))
        root.efeedc.SetToolTip(wx.ToolTip("Extrude / Retract speed (mm/min)"))
        root.efeedc.SetBackgroundColour((225, 200, 200))
        root.efeedc.SetForegroundColour("black")
        root.efeedc.Bind(wx.EVT_SPINCTRL, root.setfeeds)
        self.Add(root.efeedc, pos = (5, 2), span = (1, 2))
        self.Add(wx.StaticText(root.panel,-1, _("mm/\nmin")), pos = (5, 4), span = (1, 1))
        root.xyfeedc.Bind(wx.EVT_SPINCTRL, root.setfeeds)
        root.zfeedc.Bind(wx.EVT_SPINCTRL, root.setfeeds)
        root.zfeedc.SetBackgroundColour((180, 255, 180))
        root.zfeedc.SetForegroundColour("black")

        root.graph = Graph(root.panel, wx.ID_ANY)
        self.Add(root.graph, pos = (3, 5), span = (3, 3))
        self.Add(root.tempdisp, pos = (6, 0), span = (1, 9))

class VizPane(wx.BoxSizer):

    def __init__(self, root):
        super(VizPane, self).__init__(wx.VERTICAL)
        root.gviz = gviz.gviz(root.panel, (300, 300),
            build_dimensions = root.build_dimensions_list,
            grid = (root.settings.preview_grid_step1, root.settings.preview_grid_step2),
            extrusion_width = root.settings.preview_extrusion_width)
        root.gviz.SetToolTip(wx.ToolTip("Click to examine / edit\n  layers of loaded file"))
        root.gviz.showall = 1
        try:
            raise ""
            import printrun.stlview
            root.gwindow = printrun.stlview.GCFrame(None, wx.ID_ANY, 'Gcode view, shift to move view, mousewheel to set layer', size = (600, 600))
        except:
            root.gwindow = gviz.window([],
            build_dimensions = root.build_dimensions_list,
            grid = (root.settings.preview_grid_step1, root.settings.preview_grid_step2),
            extrusion_width = root.settings.preview_extrusion_width)
        root.gviz.Bind(wx.EVT_LEFT_DOWN, root.showwin)
        root.gwindow.Bind(wx.EVT_CLOSE, lambda x:root.gwindow.Hide())
        self.Add(root.gviz, 1, flag = wx.SHAPED)
        cs = root.centersizer = wx.GridBagSizer()
        self.Add(cs, 0, flag = wx.EXPAND)

class LogPane(wx.BoxSizer):

    def __init__(self, root):
        super(LogPane, self).__init__(wx.VERTICAL)
        root.lowerrsizer = self
        root.logbox = wx.TextCtrl(root.panel, style = wx.TE_MULTILINE, size = (350,-1))
        root.logbox.SetEditable(0)
        self.Add(root.logbox, 1, wx.EXPAND)
        lbrs = wx.BoxSizer(wx.HORIZONTAL)
        root.commandbox = wx.TextCtrl(root.panel, style = wx.TE_PROCESS_ENTER)
        root.commandbox.SetToolTip(wx.ToolTip("Send commands to printer\n(Type 'help' for simple\nhelp function)"))
        root.commandbox.Bind(wx.EVT_TEXT_ENTER, root.sendline)
        root.commandbox.Bind(wx.EVT_CHAR, root.cbkey)
        root.commandbox.history = [u""]
        root.commandbox.histindex = 1
        #root.printerControls.append(root.commandbox)
        lbrs.Add(root.commandbox, 1)
        root.sendbtn = make_button(root.panel, _("Send"), root.sendline, _("Send Command to Printer"), style = wx.BU_EXACTFIT, container = lbrs)
        #root.printerControls.append(root.sendbtn)
        self.Add(lbrs, 0, wx.EXPAND)

class MainToolbar(wx.BoxSizer):

    def __init__(self, root):
        super(MainToolbar, self).__init__(wx.HORIZONTAL)
        root.rescanbtn = make_sized_button(root.panel, _("Port"), root.rescanports, _("Communication Settings\nClick to rescan ports"))
        self.Add(root.rescanbtn, 0, wx.TOP|wx.LEFT, 0)

        root.serialport = wx.ComboBox(root.panel, -1,
                choices = root.scanserial(),
                style = wx.CB_DROPDOWN, size = (100, 25))
        root.serialport.SetToolTip(wx.ToolTip("Select Port Printer is connected to"))
        root.rescanports()
        self.Add(root.serialport)

        self.Add(wx.StaticText(root.panel,-1, "@"), 0, wx.RIGHT|wx.ALIGN_CENTER, 0)
        root.baud = wx.ComboBox(root.panel, -1,
                choices = ["2400", "9600", "19200", "38400", "57600", "115200", "250000"],
                style = wx.CB_DROPDOWN,  size = (100, 25))
        root.baud.SetToolTip(wx.ToolTip("Select Baud rate for printer communication"))
        try:
            root.baud.SetValue("115200")
            root.baud.SetValue(str(root.settings.baudrate))
        except:
            pass
        self.Add(root.baud)
        root.connectbtn = make_sized_button(root.panel, _("Connect"), root.connect, _("Connect to the printer"), self)

        root.resetbtn = make_autosize_button(root.panel, _("Reset"), root.reset, _("Reset the printer"), self)
        root.loadbtn = make_autosize_button(root.panel, _("Load file"), root.loadfile, _("Load a 3D model file"), self)
        root.platebtn = make_autosize_button(root.panel, _("Compose"), root.plate, _("Simple Plater System"), self)
        root.sdbtn = make_autosize_button(root.panel, _("SD"), root.sdmenu, _("SD Card Printing"), self)
        root.printerControls.append(root.sdbtn)
        root.printbtn = make_sized_button(root.panel, _("Print"), root.printfile, _("Start Printing Loaded File"), self)
        root.printbtn.Disable()
        root.pausebtn = make_sized_button(root.panel, _("Pause"), root.pause, _("Pause Current Print"), self)
        root.recoverbtn = make_sized_button(root.panel, _("Recover"), root.recover, _("Recover previous Print"), self)

class MainWindow(wx.Frame):
    
    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        # this list will contain all controls that should be only enabled
        # when we're connected to a printer
        self.printerControls = []

    def createGui(self):
        self.mainsizer = wx.BoxSizer(wx.VERTICAL)
        self.uppersizer = MainToolbar(self)
        self.lowersizer = wx.BoxSizer(wx.HORIZONTAL)
        self.lowersizer.Add(LeftPane(self))
        self.lowersizer.Add(VizPane(self), 1, wx.EXPAND|wx.ALIGN_CENTER_HORIZONTAL)
        self.lowersizer.Add(LogPane(self), 0, wx.EXPAND)
        self.mainsizer.Add(self.uppersizer)
        self.mainsizer.Add(self.lowersizer, 1, wx.EXPAND)
        self.panel.SetSizer(self.mainsizer)
        self.status = self.CreateStatusBar()
        self.status.SetStatusText(_("Not connected to printer."))
        self.panel.Bind(wx.EVT_MOUSE_EVENTS, self.editbutton)
        self.Bind(wx.EVT_CLOSE, self.kill)

        self.mainsizer.Layout()
        self.mainsizer.Fit(self)

        # disable all printer controls until we connect to a printer
        self.pausebtn.Disable()
        self.recoverbtn.Disable()
        for i in self.printerControls:
            i.Disable()

        #self.panel.Fit()
        self.cbuttons_reload()
