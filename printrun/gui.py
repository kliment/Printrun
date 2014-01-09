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

import traceback

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
from printrun.pronterface_widgets import TempGauge

from printrun.printrun_utils import install_locale
install_locale('pronterface')

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

def make_custom_button(root, parentpanel, i, style = 0):
    btn = make_button(parentpanel, i.label, root.procbutton,
                      i.tooltip, style = style)
    btn.SetBackgroundColour(i.background)
    btn.SetForegroundColour("black")
    btn.properties = i
    root.btndict[i.command] = btn
    root.printerControls.append(btn)
    return btn

class XYZControlsSizer(wx.GridBagSizer):

    def __init__(self, root, parentpanel = None):
        super(XYZControlsSizer, self).__init__()
        if not parentpanel: parentpanel = root.panel
        root.xyb = XYButtons(parentpanel, root.moveXY, root.homeButtonClicked, root.spacebarAction, root.settings.bgcolor, zcallback=root.moveZ)
        self.Add(root.xyb, pos = (0, 1), flag = wx.ALIGN_CENTER)
        root.zb = ZButtons(parentpanel, root.moveZ, root.settings.bgcolor)
        self.Add(root.zb, pos = (0, 2), flag = wx.ALIGN_CENTER)
        wx.CallAfter(root.xyb.SetFocus)

def add_extra_controls(self, root, parentpanel, extra_buttons = None):
    standalone_mode = extra_buttons is not None
    base_line = 1 if standalone_mode else 2
    root.monitorbox = wx.CheckBox(parentpanel, -1, _("Watch"))
    root.monitorbox.SetValue(bool(root.settings.monitor))
    root.monitorbox.SetToolTip(wx.ToolTip(_("Monitor Temperatures in Graph")))
    if standalone_mode:
        self.Add(root.monitorbox, pos = (0, 3), span = (1, 3))
    else:
        self.Add(root.monitorbox, pos = (base_line + 1, 5))
    root.monitorbox.Bind(wx.EVT_CHECKBOX, root.setmonitor)

    self.Add(wx.StaticText(parentpanel, -1, _("Heat:")), pos = (base_line + 0, 0), span = (1, 2), flag = wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
    htemp_choices = [root.temps[i] + " (" + i + ")" for i in sorted(root.temps.keys(), key = lambda x:root.temps[x])]

    root.settoff = make_button(parentpanel, _("Off"), lambda e: root.do_settemp("off"), _("Switch Hotend Off"), size = (38, -1), style = wx.BU_EXACTFIT)
    root.printerControls.append(root.settoff)
    self.Add(root.settoff, pos = (base_line + 0, 2), span = (1, 1))

    if root.settings.last_temperature not in map(float, root.temps.values()):
        htemp_choices = [str(root.settings.last_temperature)] + htemp_choices
    root.htemp = wx.ComboBox(parentpanel, -1, choices = htemp_choices,
                             style = wx.CB_DROPDOWN, size = (80, -1))
    root.htemp.SetToolTip(wx.ToolTip(_("Select Temperature for Hotend")))
    root.htemp.Bind(wx.EVT_COMBOBOX, root.htemp_change)

    self.Add(root.htemp, pos = (base_line + 0, 3), span = (1, 1))
    root.settbtn = make_button(parentpanel, _("Set"), root.do_settemp, _("Switch Hotend On"), size = (38, -1), style = wx.BU_EXACTFIT)
    root.printerControls.append(root.settbtn)
    self.Add(root.settbtn, pos = (base_line + 0, 4), span = (1, 1))

    self.Add(wx.StaticText(parentpanel, -1, _("Bed:")), pos = (base_line + 1, 0), span = (1, 2), flag = wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
    btemp_choices = [root.bedtemps[i] + " (" + i + ")" for i in sorted(root.bedtemps.keys(), key = lambda x:root.temps[x])]

    root.setboff = make_button(parentpanel, _("Off"), lambda e: root.do_bedtemp("off"), _("Switch Heated Bed Off"), size = (38, -1), style = wx.BU_EXACTFIT)
    root.printerControls.append(root.setboff)
    self.Add(root.setboff, pos = (base_line + 1, 2), span = (1, 1))

    if root.settings.last_bed_temperature not in map(float, root.bedtemps.values()):
        btemp_choices = [str(root.settings.last_bed_temperature)] + btemp_choices
    root.btemp = wx.ComboBox(parentpanel, -1, choices = btemp_choices,
                             style = wx.CB_DROPDOWN, size = (80, -1))
    root.btemp.SetToolTip(wx.ToolTip(_("Select Temperature for Heated Bed")))
    root.btemp.Bind(wx.EVT_COMBOBOX, root.btemp_change)
    self.Add(root.btemp, pos = (base_line + 1, 3), span = (1, 1))

    root.setbbtn = make_button(parentpanel, _("Set"), root.do_bedtemp, _("Switch Heated Bed On"), size = (38, -1), style = wx.BU_EXACTFIT)
    root.printerControls.append(root.setbbtn)
    self.Add(root.setbbtn, pos = (base_line + 1, 4), span = (1, 1))

    root.btemp.SetValue(str(root.settings.last_bed_temperature))
    root.htemp.SetValue(str(root.settings.last_temperature))

    ## added for an error where only the bed would get (pla) or (abs).
    #This ensures, if last temp is a default pla or abs, it will be marked so.
    # if it is not, then a (user) remark is added. This denotes a manual entry

    for i in btemp_choices:
        if i.split()[0] == str(root.settings.last_bed_temperature).split('.')[0] or i.split()[0] == str(root.settings.last_bed_temperature):
            root.btemp.SetValue(i)
    for i in htemp_choices:
        if i.split()[0] == str(root.settings.last_temperature).split('.')[0] or i.split()[0] == str(root.settings.last_temperature):
            root.htemp.SetValue(i)

    if '(' not in root.btemp.Value:
        root.btemp.SetValue(root.btemp.Value + ' (user)')
    if '(' not in root.htemp.Value:
        root.htemp.SetValue(root.htemp.Value + ' (user)')

    root.tempdisp = wx.StaticText(parentpanel, -1, "")

    if not extra_buttons:
        ebuttonspanel = root.newPanel(parentpanel)
        ebuttonssizer = wx.BoxSizer(wx.HORIZONTAL)
        if root.settings.extruders > 1:
            ebuttonssizer.Add(wx.StaticText(ebuttonspanel, -1, _("Tool:")), flag = wx.ALIGN_CENTER)
            if root.settings.extruders == 2:
                root.extrudersel = wx.Button(ebuttonspanel, -1, "0", style = wx.BU_EXACTFIT)
                root.extrudersel.SetToolTip(wx.ToolTip(_("Click to switch current extruder")))

                def extrudersel_cb(event):
                    if root.extrudersel.GetLabel() == "1":
                        new = "0"
                    else:
                        new = "1"
                    root.extrudersel.SetLabel(new)
                    root.tool_change(event)
                root.extrudersel.Bind(wx.EVT_BUTTON, extrudersel_cb)
                root.extrudersel.GetValue = root.extrudersel.GetLabel
                root.extrudersel.SetValue = root.extrudersel.SetLabel
            else:
                choices = [str(i) for i in range(0, root.settings.extruders)]
                root.extrudersel = wx.ComboBox(ebuttonspanel, -1, choices = choices,
                                               style = wx.CB_DROPDOWN | wx.CB_READONLY,
                                               size = (50, -1))
                root.extrudersel.SetToolTip(wx.ToolTip(_("Select current extruder")))
                root.extrudersel.SetValue(choices[0])
                root.extrudersel.Bind(wx.EVT_COMBOBOX, root.tool_change)
            root.printerControls.append(root.extrudersel)
            ebuttonssizer.Add(root.extrudersel)
        ebuttonspanel.SetSizer(ebuttonssizer)
        self.Add(ebuttonspanel, pos = (base_line + 2, 0), span = (1, 5), flag = wx.EXPAND)

    esettingspanel = root.newPanel(parentpanel)
    esettingssizer = wx.BoxSizer(wx.HORIZONTAL)
    root.edist = wx.SpinCtrl(esettingspanel, -1, str(root.settings.last_extrusion), min = 0, max = 1000, size = (70, -1))
    root.edist.SetBackgroundColour((225, 200, 200))
    root.edist.SetForegroundColour("black")
    root.edist.Bind(wx.EVT_SPINCTRL, root.setfeeds)
    root.edist.Bind(wx.EVT_TEXT, root.setfeeds)
    esettingssizer.Add(root.edist, flag = wx.ALIGN_CENTER | wx.RIGHT, border = 5)
    esettingssizer.Add(wx.StaticText(esettingspanel, -1, _("mm @")), flag = wx.ALIGN_CENTER | wx.RIGHT, border = 5)
    root.edist.SetToolTip(wx.ToolTip(_("Amount to Extrude or Retract (mm)")))
    root.efeedc = wx.SpinCtrl(esettingspanel, -1, str(root.settings.e_feedrate), min = 0, max = 50000, size = (70, -1))
    root.efeedc.SetToolTip(wx.ToolTip(_("Extrude / Retract speed (mm/min)")))
    root.efeedc.SetBackgroundColour((225, 200, 200))
    root.efeedc.SetForegroundColour("black")
    root.efeedc.Bind(wx.EVT_SPINCTRL, root.setfeeds)
    root.efeedc.Bind(wx.EVT_TEXT, root.setfeeds)
    esettingssizer.Add(root.efeedc, flag = wx.ALIGN_CENTER | wx.RIGHT, border = 5)
    esettingssizer.Add(wx.StaticText(esettingspanel, -1, _("mm/\nmin")), flag = wx.ALIGN_CENTER)
    esettingspanel.SetSizer(esettingssizer)
    self.Add(esettingspanel, pos = (base_line + 3, 0), span = (1, 5))

    gauges_base_line = base_line + 8 if standalone_mode else base_line + 5
    if root.display_gauges:
        root.hottgauge = TempGauge(parentpanel, size = (-1, 24), title = _("Heater:"), maxval = 300)
        self.Add(root.hottgauge, pos = (gauges_base_line + 0, 0), span = (1, 6), flag = wx.EXPAND)
        root.bedtgauge = TempGauge(parentpanel, size = (-1, 24), title = _("Bed:"), maxval = 150)
        self.Add(root.bedtgauge, pos = (gauges_base_line + 1, 0), span = (1, 6), flag = wx.EXPAND)

        def hotendgauge_scroll_setpoint(e):
            rot = e.GetWheelRotation()
            if rot > 0:
                root.do_settemp(str(root.hsetpoint + 1))
            elif rot < 0:
                root.do_settemp(str(max(0, root.hsetpoint - 1)))

        def bedgauge_scroll_setpoint(e):
            rot = e.GetWheelRotation()
            if rot > 0:
                root.do_settemp(str(root.bsetpoint + 1))
            elif rot < 0:
                root.do_settemp(str(max(0, root.bsetpoint - 1)))
        root.hottgauge.Bind(wx.EVT_MOUSEWHEEL, hotendgauge_scroll_setpoint)
        root.bedtgauge.Bind(wx.EVT_MOUSEWHEEL, bedgauge_scroll_setpoint)
        self.Add(root.tempdisp, pos = (gauges_base_line + 2, 0), span = (1, 6))
    else:
        self.Add(root.tempdisp, pos = (gauges_base_line + 0, 0), span = (1, 6))

    if root.display_graph:
        root.graph = Graph(parentpanel, wx.ID_ANY, root)
        if standalone_mode:
            self.Add(root.graph, pos = (base_line + 5, 0), span = (3, 6))
        else:
            self.Add(root.graph, pos = (base_line + 2, 5), span = (3, 1))
        root.graph.Bind(wx.EVT_LEFT_DOWN, root.graph.showwin)

    if extra_buttons:
        pos_mapping = {(2, 5): (0, 0),
                       (4, 0): (3, 0),
                       (4, 2): (3, 2),
                       }
        span_mapping = {(2, 5): (1, 3),
                        (4, 0): (1, 2),
                        (4, 2): (1, 3),
                        }
        for i in extra_buttons:
            btn = extra_buttons[i]
            self.Add(btn, pos = pos_mapping[i.pos], span = span_mapping[i.pos], flag = wx.EXPAND)
    else:
        for i in root.cpbuttons:
            if not i.pos or i.pos[0] != 4:
                continue
            btn = make_custom_button(root, ebuttonspanel, i,
                                     style = wx.BU_EXACTFIT)
            ebuttonssizer.Add(btn, 1, flag = wx.EXPAND)

class LeftPane(wx.GridBagSizer):

    def __init__(self, root, parentpanel = None, standalone_mode = False):
        super(LeftPane, self).__init__()
        if not parentpanel: parentpanel = root.panel
        llts = wx.BoxSizer(wx.HORIZONTAL)
        self.Add(llts, pos = (0, 0), span = (1, 6))
        self.xyzsizer = XYZControlsSizer(root, parentpanel)
        self.Add(self.xyzsizer, pos = (1, 0), span = (1, 6), flag = wx.ALIGN_CENTER)

        self.extra_buttons = {}
        for i in root.cpbuttons:
            if not standalone_mode and i.pos and i.pos[0] == 4:
                continue
            btn = make_custom_button(root, parentpanel, i)
            if i.pos is None:
                if i.span == 0:
                    llts.Add(btn)
            elif not standalone_mode:
                self.Add(btn, pos = i.pos, span = i.span, flag = wx.EXPAND)
            else:
                self.extra_buttons[i] = btn

        root.xyfeedc = wx.SpinCtrl(parentpanel, -1, str(root.settings.xy_feedrate), min = 0, max = 50000, size = (70, -1))
        root.xyfeedc.SetToolTip(wx.ToolTip(_("Set Maximum Speed for X & Y axes (mm/min)")))
        llts.Add(wx.StaticText(parentpanel, -1, _("XY:")), flag = wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        llts.Add(root.xyfeedc)
        llts.Add(wx.StaticText(parentpanel, -1, _("mm/min Z:")), flag = wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        root.zfeedc = wx.SpinCtrl(parentpanel, -1, str(root.settings.z_feedrate), min = 0, max = 50000, size = (70, -1))
        root.zfeedc.SetToolTip(wx.ToolTip(_("Set Maximum Speed for Z axis (mm/min)")))
        llts.Add(root.zfeedc,)

        root.xyfeedc.Bind(wx.EVT_SPINCTRL, root.setfeeds)
        root.zfeedc.Bind(wx.EVT_SPINCTRL, root.setfeeds)
        root.xyfeedc.Bind(wx.EVT_TEXT, root.setfeeds)
        root.zfeedc.Bind(wx.EVT_TEXT, root.setfeeds)
        root.zfeedc.SetBackgroundColour((180, 255, 180))
        root.zfeedc.SetForegroundColour("black")

        if not standalone_mode:
            add_extra_controls(self, root, parentpanel, None)

class NoViz(object):

    showall = False

    def clear(self, *a):
        pass

    def addfile(self, *a, **kw):
        pass

    def addgcode(self, *a, **kw):
        pass

    def Refresh(self, *a):
        pass

    def setlayer(self, *a):
        pass

class VizPane(wx.BoxSizer):

    def __init__(self, root, parentpanel = None):
        super(VizPane, self).__init__(wx.VERTICAL)
        if not parentpanel: parentpanel = root.panel
        if root.settings.mainviz == "None":
            root.gviz = NoViz()
        use2dview = root.settings.mainviz == "2D"
        if root.settings.mainviz == "3D":
            try:
                import printrun.gcview
                root.gviz = printrun.gcview.GcodeViewMainWrapper(parentpanel, root.build_dimensions_list, root = root)
                root.gviz.clickcb = root.showwin
            except:
                use2dview = True
                print "3D view mode requested, but we failed to initialize it."
                print "Falling back to 2D view, and here is the backtrace:"
                traceback.print_exc()
        if use2dview:
            root.gviz = gviz.Gviz(parentpanel, (300, 300),
                                  build_dimensions = root.build_dimensions_list,
                                  grid = (root.settings.preview_grid_step1, root.settings.preview_grid_step2),
                                  extrusion_width = root.settings.preview_extrusion_width,
                                  bgcolor = root.settings.bgcolor)
            root.gviz.SetToolTip(wx.ToolTip(_("Click to examine / edit\n  layers of loaded file")))
            root.gviz.showall = 1
            root.gviz.Bind(wx.EVT_LEFT_DOWN, root.showwin)
        use3dview = root.settings.viz3d
        if use3dview:
            try:
                import printrun.gcview
                objects = None
                if isinstance(root.gviz, printrun.gcview.GcodeViewMainWrapper):
                    objects = root.gviz.objects
                root.gwindow = printrun.gcview.GcodeViewFrame(None, wx.ID_ANY, 'Gcode view, shift to move view, mousewheel to set layer', size = (600, 600), build_dimensions = root.build_dimensions_list, objects = objects, root = root)
            except:
                use3dview = False
                print "3D view mode requested, but we failed to initialize it."
                print "Falling back to 2D view, and here is the backtrace:"
                traceback.print_exc()
        if not use3dview:
            root.gwindow = gviz.GvizWindow(build_dimensions = root.build_dimensions_list,
                                           grid = (root.settings.preview_grid_step1, root.settings.preview_grid_step2),
                                           extrusion_width = root.settings.preview_extrusion_width,
                                           bgcolor = root.settings.bgcolor)
        root.gwindow.Bind(wx.EVT_CLOSE, lambda x: root.gwindow.Hide())
        if not isinstance(root.gviz, NoViz):
            self.Add(root.gviz.widget, 1, flag = wx.SHAPED | wx.ALIGN_CENTER_HORIZONTAL)

class LogPane(wx.BoxSizer):

    def __init__(self, root, parentpanel = None):
        super(LogPane, self).__init__(wx.VERTICAL)
        if not parentpanel: parentpanel = root.panel
        root.logbox = wx.TextCtrl(parentpanel, style = wx.TE_MULTILINE, size = (350, -1))
        root.logbox.SetMinSize((100, -1))
        root.logbox.SetEditable(0)
        self.Add(root.logbox, 1, wx.EXPAND)
        lbrs = wx.BoxSizer(wx.HORIZONTAL)
        root.commandbox = wx.TextCtrl(parentpanel, style = wx.TE_PROCESS_ENTER)
        root.commandbox.SetToolTip(wx.ToolTip(_("Send commands to printer\n(Type 'help' for simple\nhelp function)")))
        root.commandbox.Bind(wx.EVT_TEXT_ENTER, root.sendline)
        root.commandbox.Bind(wx.EVT_CHAR, root.cbkey)
        root.commandbox.history = [u""]
        root.commandbox.histindex = 1
        #root.printerControls.append(root.commandbox)
        lbrs.Add(root.commandbox, 1)
        root.sendbtn = make_button(parentpanel, _("Send"), root.sendline, _("Send Command to Printer"), style = wx.BU_EXACTFIT, container = lbrs)
        #root.printerControls.append(root.sendbtn)
        self.Add(lbrs, 0, wx.EXPAND)


def MainToolbar(root, parentpanel = None, use_wrapsizer = False):
    if not parentpanel: parentpanel = root.panel
    if root.settings.lockbox:
        root.locker = wx.CheckBox(parentpanel, label = _("Lock") + "  ")
        root.locker.Bind(wx.EVT_CHECKBOX, root.lock)
        root.locker.SetToolTip(wx.ToolTip(_("Lock graphical interface")))
        glob = wx.BoxSizer(wx.HORIZONTAL)
        parentpanel = root.newPanel(parentpanel)
        glob.Add(parentpanel, 1, flag = wx.EXPAND)
        glob.Add(root.locker, 0)
    ToolbarSizer = wx.WrapSizer if use_wrapsizer and wx.VERSION > (2, 9) else wx.BoxSizer
    self = ToolbarSizer(wx.HORIZONTAL)
    root.rescanbtn = make_autosize_button(parentpanel, _("Port"), root.rescanports, _("Communication Settings\nClick to rescan ports"))
    self.Add(root.rescanbtn, 0, wx.TOP | wx.LEFT, 0)

    root.serialport = wx.ComboBox(parentpanel, -1, choices = root.scanserial(),
                                  style = wx.CB_DROPDOWN, size = (-1, 25))
    root.serialport.SetToolTip(wx.ToolTip(_("Select Port Printer is connected to")))
    root.rescanports()
    self.Add(root.serialport)

    self.Add(wx.StaticText(parentpanel, -1, "@"), 0, wx.RIGHT | wx.ALIGN_CENTER, 0)
    root.baud = wx.ComboBox(parentpanel, -1,
                            choices = ["2400", "9600", "19200", "38400",
                                       "57600", "115200", "250000"],
                            style = wx.CB_DROPDOWN, size = (100, 25))
    root.baud.SetToolTip(wx.ToolTip(_("Select Baud rate for printer communication")))
    try:
        root.baud.SetValue("115200")
        root.baud.SetValue(str(root.settings.baudrate))
    except:
        pass
    self.Add(root.baud)
    root.connectbtn = make_autosize_button(parentpanel, _("Connect"), root.connect, _("Connect to the printer"), self)

    root.resetbtn = make_autosize_button(parentpanel, _("Reset"), root.reset, _("Reset the printer"), self)
    root.loadbtn = make_autosize_button(parentpanel, _("Load file"), root.loadfile, _("Load a 3D model file"), self)
    root.sdbtn = make_autosize_button(parentpanel, _("SD"), root.sdmenu, _("SD Card Printing"), self)
    root.printerControls.append(root.sdbtn)
    root.printbtn = make_autosize_button(parentpanel, _("Print"), root.printfile, _("Start Printing Loaded File"), self)
    root.printbtn.Disable()
    root.pausebtn = make_autosize_button(parentpanel, _("Pause"), root.pause, _("Pause Current Print"), self)
    root.offbtn = make_autosize_button(parentpanel, _("Off"), root.off, _("Turn printer off"), self)
    root.printerControls.append(root.offbtn)
    if root.settings.lockbox:
        parentpanel.SetSizer(self)
        return glob
    else:
        return self

class MainWindow(wx.Frame):

    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        # this list will contain all controls that should be only enabled
        # when we're connected to a printer
        self.printerControls = []
        self.panel = wx.Panel(self, -1, size = kwargs["size"])
        self.panels = []

    def newPanel(self, parent, add_to_list = True):
        panel = wx.Panel(parent)
        panel.SetBackgroundColour(self.settings.bgcolor)
        if add_to_list: self.panels.append(panel)
        return panel

    def createTabbedGui(self):
        self.notesizer = wx.BoxSizer(wx.VERTICAL)
        self.notebook = wx.Notebook(self.panel)
        self.notebook.SetBackgroundColour(self.settings.bgcolor)
        page1panel = self.newPanel(self.notebook)
        page2panel = self.newPanel(self.notebook)
        self.mainsizer_page1 = wx.BoxSizer(wx.VERTICAL)
        page1panel1 = self.newPanel(page1panel)
        page1panel2 = self.newPanel(page1panel)
        self.uppersizer = MainToolbar(self, page1panel1, use_wrapsizer = True)
        page1panel1.SetSizer(self.uppersizer)
        self.mainsizer_page1.Add(page1panel1, 0, wx.EXPAND)
        self.lowersizer = wx.BoxSizer(wx.HORIZONTAL)
        page1panel2.SetSizer(self.lowersizer)
        leftsizer = wx.BoxSizer(wx.VERTICAL)
        left_pane = LeftPane(self, page1panel2, True)
        leftsizer.Add(left_pane, 1, wx.ALIGN_CENTER)
        rightsizer = wx.BoxSizer(wx.VERTICAL)
        extracontrols = wx.GridBagSizer()
        add_extra_controls(extracontrols, self, page1panel2, left_pane.extra_buttons)
        rightsizer.AddStretchSpacer()
        rightsizer.Add(extracontrols, 0, wx.ALIGN_CENTER)
        self.lowersizer.Add(leftsizer, 0, wx.ALIGN_CENTER | wx.RIGHT, border = 10)
        self.lowersizer.Add(rightsizer, 1, wx.ALIGN_CENTER)
        self.mainsizer_page1.Add(page1panel2, 1)
        self.mainsizer = wx.BoxSizer(wx.HORIZONTAL)
        self.splitterwindow = wx.SplitterWindow(page2panel, style = wx.SP_3D)
        page2sizer1 = wx.BoxSizer(wx.HORIZONTAL)
        page2panel1 = self.newPanel(self.splitterwindow)
        page2sizer2 = wx.BoxSizer(wx.HORIZONTAL)
        page2panel2 = self.newPanel(self.splitterwindow)
        vizpane = VizPane(self, page2panel1)
        page2sizer1.Add(vizpane, 1, wx.EXPAND)
        page2sizer2.Add(LogPane(self, page2panel2), 1, wx.EXPAND)
        page2panel1.SetSizer(page2sizer1)
        page2panel2.SetSizer(page2sizer2)
        self.splitterwindow.SetMinimumPaneSize(1)
        self.splitterwindow.SetSashGravity(0.5)
        self.splitterwindow.SplitVertically(page2panel1, page2panel2, 0)
        self.mainsizer.Add(self.splitterwindow, 1, wx.EXPAND)
        page1panel.SetSizer(self.mainsizer_page1)
        page2panel.SetSizer(self.mainsizer)
        self.notesizer.Add(self.notebook, 1, wx.EXPAND)
        self.notebook.AddPage(page1panel, _("Commands"))
        self.notebook.AddPage(page2panel, _("Status"))
        self.panel.SetSizer(self.notesizer)
        self.statusbar = self.CreateStatusBar()
        self.statusbar.SetStatusText(_("Not connected to printer."))
        self.panel.Bind(wx.EVT_MOUSE_EVENTS, self.editbutton)
        self.Bind(wx.EVT_CLOSE, self.kill)

        # Custom buttons
        if wx.VERSION > (2, 9): self.centersizer = wx.WrapSizer(wx.HORIZONTAL)
        else: self.centersizer = wx.GridBagSizer()
        self.centersizer = wx.GridBagSizer()
        self.centerpanel = self.newPanel(page1panel2)
        self.centerpanel.SetSizer(self.centersizer)
        rightsizer.Add(self.centerpanel, 0, wx.ALIGN_CENTER)
        rightsizer.AddStretchSpacer()

        self.panel.SetSizerAndFit(self.notesizer)

        # disable all printer controls until we connect to a printer
        self.pausebtn.Disable()
        self.recoverbtn.Disable()
        for i in self.printerControls:
            i.Disable()

        self.cbuttons_reload()
        minsize = self.lowersizer.GetMinSize()  # lower pane
        minsize[1] = self.notebook.GetSize()[1]
        self.SetMinSize(self.ClientToWindowSize(minsize))  # client to window
        self.Fit()

    def createGui(self, compact = False):
        self.mainsizer = wx.BoxSizer(wx.VERTICAL)
        self.lowersizer = wx.BoxSizer(wx.HORIZONTAL)
        upperpanel = self.newPanel(self.panel, False)
        self.uppersizer = MainToolbar(self, upperpanel)
        lowerpanel = self.newPanel(self.panel)
        upperpanel.SetSizer(self.uppersizer)
        lowerpanel.SetSizer(self.lowersizer)
        left_pane = LeftPane(self, lowerpanel)
        left_pane.Layout()  # required to get correct rows/cols counts
        left_sizer = wx.BoxSizer(wx.VERTICAL)
        left_sizer.Add(left_pane, 0)
        self.lowersizer.Add(left_sizer, 0, wx.EXPAND)
        if not compact:  # Use a splitterwindow to group viz and log
            rightpanel = self.newPanel(lowerpanel)
            rightsizer = wx.BoxSizer(wx.VERTICAL)
            rightpanel.SetSizer(rightsizer)
            self.splitterwindow = wx.SplitterWindow(rightpanel, style = wx.SP_3D)
            self.splitterwindow.SetMinimumPaneSize(150)
            self.splitterwindow.SetSashGravity(0.8)
            rightsizer.Add(self.splitterwindow, 1, wx.EXPAND)
            vizpanel = self.newPanel(self.splitterwindow)
            logpanel = self.newPanel(self.splitterwindow)
            self.splitterwindow.SplitVertically(vizpanel, logpanel, 0)
        else:
            vizpanel = self.newPanel(lowerpanel)
            logpanel = self.newPanel(lowerpanel)
        viz_pane = VizPane(self, vizpanel)
        # Custom buttons
        if wx.VERSION > (2, 9): self.centersizer = wx.WrapSizer(wx.HORIZONTAL)
        else: self.centersizer = wx.GridBagSizer()
        self.centerpanel = self.newPanel(vizpanel)
        self.centerpanel.SetSizer(self.centersizer)
        viz_pane.Add(self.centerpanel, 0, flag = wx.ALIGN_CENTER)
        vizpanel.SetSizer(viz_pane)
        log_pane = LogPane(self, logpanel)
        logpanel.SetSizer(log_pane)
        if not compact:
            self.lowersizer.Add(rightpanel, 1, wx.EXPAND)
        else:
            left_sizer.Add(logpanel, 1, wx.EXPAND)
        self.mainsizer.Add(upperpanel, 0)
        self.mainsizer.Add(lowerpanel, 1, wx.EXPAND)
        self.panel.SetSizer(self.mainsizer)
        self.statusbar = self.CreateStatusBar()
        self.statusbar.SetStatusText(_("Not connected to printer."))
        self.panel.Bind(wx.EVT_MOUSE_EVENTS, self.editbutton)
        self.Bind(wx.EVT_CLOSE, self.kill)

        self.mainsizer.Layout()
        # This prevents resizing below a reasonnable value
        # We sum the lowersizer (left pane / viz / log) min size
        # the toolbar height and the statusbar/menubar sizes
        minsize = self.lowersizer.GetMinSize()  # lower pane
        minsize[1] += self.uppersizer.GetMinSize()[1]  # toolbar height
        self.SetMinSize(self.ClientToWindowSize(minsize))  # client to window

        # disable all printer controls until we connect to a printer
        self.pausebtn.Disable()
        self.recoverbtn.Disable()
        for i in self.printerControls:
            i.Disable()

        self.cbuttons_reload()
