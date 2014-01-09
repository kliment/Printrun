#!/usr/bin/env python

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

import os
import Queue
import re
import sys
import time
import threading
import traceback
import cStringIO as StringIO
import subprocess
import shlex
import glob
import logging

try: import simplejson as json
except ImportError: import json

from . import pronsole
from . import printcore

from printrun.printrun_utils import install_locale, setup_logging
install_locale('pronterface')

try:
    import wx
except:
    logging.error(_("WX is not installed. This program requires WX to run."))
    raise

from printrun.pronterface_widgets import SpecialButton, MacroEditor, \
    PronterOptions, ButtonEdit
from serial import SerialException

winsize = (800, 500)
layerindex = 0
if os.name == "nt":
    winsize = (800, 530)

from printrun.printrun_utils import iconfile, configfile, format_time, format_duration
from printrun.gui import MainWindow
from printrun.excluder import Excluder
from pronsole import dosify, wxSetting, HiddenSetting, StringSetting, SpinSetting, FloatSpinSetting, BooleanSetting, StaticTextSetting
from printrun import gcoder

tempreport_exp = re.compile("([TB]\d*):([-+]?\d*\.?\d*)(?: ?\/)?([-+]?\d*\.?\d*)")

def parse_temperature_report(report):
    matches = tempreport_exp.findall(report)
    return dict((m[0], (m[1], m[2])) for m in matches)

class Tee(object):
    def __init__(self, target):
        self.stdout = sys.stdout
        sys.stdout = self
        setup_logging(sys.stdout)
        self.target = target

    def __del__(self):
        sys.stdout = self.stdout

    def write(self, data):
        try:
            self.target(data)
        except:
            pass
        try:
            data = data.encode("utf-8")
        except:
            pass
        self.stdout.write(data)

    def flush(self):
        self.stdout.flush()

class ComboSetting(wxSetting):

    def __init__(self, name, default, choices, label = None, help = None, group = None):
        super(ComboSetting, self).__init__(name, default, label, help, group)
        self.choices = choices

    def get_specific_widget(self, parent):
        import wx
        self.widget = wx.ComboBox(parent, -1, str(self.value), choices = self.choices, style = wx.CB_DROPDOWN)
        return self.widget

class PronterWindow(MainWindow, pronsole.pronsole):

    _fgcode = None

    def _get_fgcode(self):
        return self._fgcode

    def _set_fgcode(self, value):
        self._fgcode = value
        self.excluder = None
        self.excluder_e = None
        self.excluder_z_abs = None
        self.excluder_z_rel = None
    fgcode = property(_get_fgcode, _set_fgcode)

    def __init__(self, app, filename = None, size = winsize):
        pronsole.pronsole.__init__(self)
        self.app = app
        #default build dimensions are 200x200x100 with 0, 0, 0 in the corner of the bed and endstops at 0, 0 and 0
        monitorsetting = BooleanSetting("monitor", False)
        monitorsetting.hidden = True
        self.settings._add(monitorsetting)
        self.settings._add(StringSetting("simarrange_path", "", _("Simarrange command"), _("Path to the simarrange binary to use in the STL plater"), "External"))
        self.settings._add(SpinSetting("extruders", 0, 1, 5, _("Extruders count"), _("Number of extruders"), "Printer"))
        self.settings._add(BooleanSetting("clamp_jogging", False, _("Clamp manual moves"), _("Prevent manual moves from leaving the specified build dimensions"), "Printer"))
        self.settings._add(StringSetting("bgcolor", "#FFFFFF", _("Background color"), _("Pronterface background color"), "UI"))
        self.settings._add(ComboSetting("uimode", "Standard", ["Standard", "Compact", "Tabbed"], _("Interface mode"), _("Standard interface is a one-page, three columns layout with controls/visualization/log\nCompact mode is a one-page, two columns layout with controls + log/visualization\nTabbed mode is a two-pages mode, where the first page shows controls and the second one shows visualization and log."), "UI"))
        self.settings._add(BooleanSetting("slic3rintegration", False, _("Enable Slic3r integration"), _("Add a menu to select Slic3r profiles directly from Pronterface"), "UI"))
        self.settings._add(BooleanSetting("slic3rupdate", False, _("Update Slic3r default presets"), _("When selecting a profile in Slic3r integration menu, also save it as the default Slic3r preset"), "UI"))
        self.settings._add(ComboSetting("mainviz", "2D", ["2D", "3D", "None"], _("Main visualization"), _("Select visualization for main window."), "UI"))
        self.settings._add(BooleanSetting("viz3d", False, _("Use 3D in GCode viewer window"), _("Use 3D mode instead of 2D layered mode in the visualization window"), "UI"))
        self.settings._add(BooleanSetting("light3d", True, _("Use a lighter 3D visualization"), _("Use a lighter visualization with simple lines instead of extruded paths for 3D viewer"), "UI"))
        self.settings._add(BooleanSetting("tempgraph", True, _("Display temperature graph"), _("Display time-lapse temperature graph"), "UI"))
        self.settings._add(BooleanSetting("tempgauges", False, _("Display temperature gauges"), _("Display graphical gauges for temperatures visualization"), "UI"))
        self.settings._add(BooleanSetting("lockbox", False, _("Display interface lock checkbox"), _("Display a checkbox that, when check, locks most of Pronterface"), "UI"))
        self.settings._add(BooleanSetting("lockonstart", False, _("Lock interface upon print start"), _("If lock checkbox is enabled, lock the interface when starting a print"), "UI"))
        self.settings._add(HiddenSetting("last_window_width", size[0]))
        self.settings._add(HiddenSetting("last_window_height", size[1]))
        self.settings._add(HiddenSetting("last_window_maximized", False))
        self.settings._add(HiddenSetting("last_bed_temperature", 0.0))
        self.settings._add(HiddenSetting("last_file_path", u""))
        self.settings._add(HiddenSetting("last_temperature", 0.0))
        self.settings._add(HiddenSetting("last_extrusion", 5.0))
        self.settings._add(HiddenSetting("default_extrusion", 5.0))
        self.settings._add(FloatSpinSetting("preview_extrusion_width", 0.5, 0, 10, _("Preview extrusion width"), _("Width of Extrusion in Preview"), "UI"), self.update_gviz_params)
        self.settings._add(SpinSetting("preview_grid_step1", 10., 0, 200, _("Fine grid spacing"), _("Fine Grid Spacing"), "UI"), self.update_gviz_params)
        self.settings._add(SpinSetting("preview_grid_step2", 50., 0, 200, _("Coarse grid spacing"), _("Coarse Grid Spacing"), "UI"), self.update_gviz_params)
        self.settings._add(StaticTextSetting("note1", _("Note:"), _("Changing most settings here will require restart to get effect"), group = "UI"))
        recentfilessetting = StringSetting("recentfiles", "[]")
        recentfilessetting.hidden = True
        self.settings._add(recentfilessetting, self.update_recent_files)

        self.pauseScript = "pause.gcode"
        self.endScript = "end.gcode"

        self.filename = filename

        self.statuscheck = False
        self.status_thread = None
        self.capture_skip = {}
        self.capture_skip_newline = False
        self.tempreport = ""
        self.userm114 = 0
        self.userm105 = 0
        self.m105_waitcycles = 0
        self.monitor = 0
        self.fgcode = None
        self.excluder = None
        self.skeinp = None
        self.monitor_interval = 3
        self.current_pos = [0, 0, 0]
        self.paused = False
        self.uploading = False
        self.sentlines = Queue.Queue(0)
        self.cpbuttons = [
            SpecialButton(_("Motors off"), ("M84"), (250, 250, 250), None, 0, _("Switch all motors off")),
            SpecialButton(_("Check temp"), ("M105"), (225, 200, 200), (2, 5), (1, 1), _("Check current hotend temperature")),
            SpecialButton(_("Extrude"), ("pront_extrude"), (225, 200, 200), (4, 0), (1, 2), _("Advance extruder by set length")),
            SpecialButton(_("Reverse"), ("pront_reverse"), (225, 200, 200), (4, 2), (1, 3), _("Reverse extruder by set length")),
        ]
        self.custombuttons = []
        self.btndict = {}
        self.filehistory = None
        self.autoconnect = False
        self.parse_cmdline(sys.argv[1:])

        # FIXME: We need to initialize the main window after loading the
        # configs to restore the size, but this might have some unforeseen
        # consequences.
        os.putenv("UBUNTU_MENUPROXY", "0")
        size = (self.settings.last_window_width, self.settings.last_window_height)
        MainWindow.__init__(self, None, title = _("Pronterface"), size = size)
        if self.settings.last_window_maximized:
            self.Maximize()
        self.Bind(wx.EVT_SIZE, self.on_resize)
        self.Bind(wx.EVT_MAXIMIZE, self.on_maximize)
        self.SetIcon(wx.Icon(iconfile("P-face.ico"), wx.BITMAP_TYPE_ICO))

        self.display_graph = self.settings.tempgraph
        self.display_gauges = self.settings.tempgauges

        #set feedrates in printcore for pause/resume
        self.p.xy_feedrate = self.settings.xy_feedrate
        self.p.z_feedrate = self.settings.z_feedrate

        #make printcore aware of me
        self.p.pronterface = self

        self.panel.SetBackgroundColour(self.settings.bgcolor)
        customdict = {}
        try:
            execfile(configfile("custombtn.txt"), customdict)
            if len(customdict["btns"]):
                if not len(self.custombuttons):
                    try:
                        self.custombuttons = customdict["btns"]
                        for n in xrange(len(self.custombuttons)):
                            self.cbutton_save(n, self.custombuttons[n])
                        os.rename("custombtn.txt", "custombtn.old")
                        rco = open("custombtn.txt", "w")
                        rco.write(_("# I moved all your custom buttons into .pronsolerc.\n# Please don't add them here any more.\n# Backup of your old buttons is in custombtn.old\n"))
                        rco.close()
                    except IOError, x:
                        logging.error(str(x))
                else:
                    logging.warning(_("Note!!! You have specified custom buttons in both custombtn.txt and .pronsolerc"))
                    logging.warning(_("Ignoring custombtn.txt. Remove all current buttons to revert to custombtn.txt"))

        except:
            pass
        self.popmenu()
        self.update_recent_files("recentfiles", self.settings.recentfiles)
        if self.settings.uimode == "Tabbed":
            self.createTabbedGui()
        else:
            self.createGui(self.settings.uimode == "Compact")
        self.t = Tee(self.catchprint)
        self.stdout = sys.stdout
        self.skeining = 0
        self.mini = False
        self.p.sendcb = self.sentcb
        self.p.preprintsendcb = self.preprintsendcb
        self.p.printsendcb = self.printsentcb
        self.p.startcb = self.startcb
        self.p.endcb = self.endcb
        self.curlayer = 0
        self.cur_button = None
        self.predisconnect_mainqueue = None
        self.predisconnect_queueindex = None
        self.predisconnect_layer = None
        self.hsetpoint = 0.0
        self.bsetpoint = 0.0
        if self.autoconnect:
            self.connect()
        if self.filename is not None:
            self.do_load(self.filename)
        if self.settings.monitor:
            self.setmonitor(None)

    def on_resize(self, event):
        maximized = self.IsMaximized()
        self.set("last_window_maximized", maximized)
        if not maximized and not self.IsIconized():
            size = self.GetClientSize()
            self.set("last_window_width", size[0])
            self.set("last_window_height", size[1])
        self.settings.last_window_maximized = self.IsMaximized()
        event.Skip()

    def on_maximize(self, event):
        self.set("last_window_maximized", self.IsMaximized())
        event.Skip()

    def add_cmdline_arguments(self, parser):
        pronsole.pronsole.add_cmdline_arguments(self, parser)
        parser.add_argument('-a', '--autoconnect', help = _("automatically try to connect to printer on startup"), action = "store_true")

    def process_cmdline_arguments(self, args):
        pronsole.pronsole.process_cmdline_arguments(self, args)
        self.autoconnect = args.autoconnect

    def startcb(self, resuming = False):
        pronsole.pronsole.startcb(self, resuming)
        if self.settings.lockbox and self.settings.lockonstart:
            wx.CallAfter(self.lock, force = True)

    def endcb(self):
        pronsole.pronsole.endcb(self)
        if self.p.queueindex == 0:
            wx.CallAfter(self.pausebtn.Disable)
            wx.CallAfter(self.printbtn.SetLabel, _("Print"))

    def online(self):
        print _("Printer is now online.")
        wx.CallAfter(self.online_gui)

    def online_gui(self):
        self.connectbtn.SetLabel(_("Disconnect"))
        self.connectbtn.SetToolTip(wx.ToolTip("Disconnect from the printer"))
        self.connectbtn.Bind(wx.EVT_BUTTON, self.disconnect)

        if hasattr(self, "extrudersel"):
            self.do_tool(self.extrudersel.GetValue())

        for i in self.printerControls:
            i.Enable()

        # Enable XYButtons and ZButtons
        self.xyb.enable()
        self.zb.enable()

        if self.filename:
            self.printbtn.Enable()

    def sentcb(self, line, gline):
        if not gline:
            pass
        elif gline.is_move:
            if gline.z is not None:
                layer = gline.z
                if layer != self.curlayer:
                    self.curlayer = layer
                    wx.CallAfter(self.gviz.clearhilights)
                    wx.CallAfter(self.gviz.setlayer, layer)
        elif gline.command in ["M104", "M109"]:
            gline_s = gcoder.S(gline)
            if gline_s is not None:
                temp = gline_s
                if self.display_gauges: wx.CallAfter(self.hottgauge.SetTarget, temp)
                if self.display_graph: wx.CallAfter(self.graph.SetExtruder0TargetTemperature, temp)
        elif gline.command in ["M140", "M190"]:
            gline_s = gcoder.S(gline)
            if gline_s is not None:
                temp = gline_s
                if self.display_gauges: wx.CallAfter(self.bedtgauge.SetTarget, temp)
                if self.display_graph: wx.CallAfter(self.graph.SetBedTargetTemperature, temp)
        elif gline.command.startswith("T"):
            tool = gline.command[1:]
            if hasattr(self, "extrudersel"): wx.CallAfter(self.extrudersel.SetValue, tool)
        self.sentlines.put_nowait(line)

    def is_excluded_move(self, gline):
        if not gline.is_move or not self.excluder or not self.excluder.rectangles:
            return False
        for (x0, y0, x1, y1) in self.excluder.rectangles:
            if x0 <= gline.current_x <= x1 and y0 <= gline.current_y <= y1:
                return True
        return False

    def preprintsendcb(self, gline, next_gline):
        if not self.is_excluded_move(gline):
            return gline
        else:
            if gline.z is not None:
                if gline.relative:
                    if self.excluder_z_abs is not None:
                        self.excluder_z_abs += gline.z
                    elif self.excluder_z_rel is not None:
                        self.excluder_z_rel += gline.z
                    else:
                        self.excluder_z_rel = gline.z
                else:
                    self.excluder_z_rel = None
                    self.excluder_z_abs = gline.z
            if gline.e is not None and not gline.relative_e:
                self.excluder_e = gline.e
            # If next move won't be excluded, push the changes we have to do
            if next_gline is not None and not self.is_excluded_move(next_gline):
                if self.excluder_e is not None:
                    self.p.send_now("G92 E%.5f" % self.excluder_e)
                    self.excluder_e = None
                if self.excluder_z_abs is not None:
                    if gline.relative:
                        self.p.send_now("G90")
                    self.p.send_now("G1 Z%.5f" % self.excluder_z_abs)
                    self.excluder_z_abs = None
                    if gline.relative:
                        self.p.send_now("G91")
                if self.excluder_z_rel is not None:
                    if not gline.relative:
                        self.p.send_now("G91")
                    self.p.send_now("G1 Z%.5f" % self.excluder_z_rel)
                    self.excluder_z_rel = None
                    if not gline.relative:
                        self.p.send_now("G90")
                return None

    def printsentcb(self, gline):
        if gline.is_move and hasattr(self.gwindow, "set_current_gline"):
            wx.CallAfter(self.gwindow.set_current_gline, gline)
        if gline.is_move and hasattr(self.gviz, "set_current_gline"):
            wx.CallAfter(self.gviz.set_current_gline, gline)

    def do_pront_extrude(self, l = ""):
        feed = self.settings.e_feedrate
        self.do_extrude_final(self.edist.GetValue(), feed)

    def do_pront_reverse(self, l = ""):
        feed = self.settings.e_feedrate
        self.do_extrude_final(- self.edist.GetValue(), feed)

    def setbedgui(self, f):
        self.bsetpoint = f
        if self.display_gauges: self.bedtgauge.SetTarget(int(f))
        if self.display_graph: wx.CallAfter(self.graph.SetBedTargetTemperature, int(f))
        if f > 0:
            wx.CallAfter(self.btemp.SetValue, str(f))
            self.set("last_bed_temperature", str(f))
            wx.CallAfter(self.setboff.SetBackgroundColour, None)
            wx.CallAfter(self.setboff.SetForegroundColour, None)
            wx.CallAfter(self.setbbtn.SetBackgroundColour, "#FFAA66")
            wx.CallAfter(self.setbbtn.SetForegroundColour, "#660000")
            wx.CallAfter(self.btemp.SetBackgroundColour, "#FFDABB")
        else:
            wx.CallAfter(self.setboff.SetBackgroundColour, "#0044CC")
            wx.CallAfter(self.setboff.SetForegroundColour, "white")
            wx.CallAfter(self.setbbtn.SetBackgroundColour, None)
            wx.CallAfter(self.setbbtn.SetForegroundColour, None)
            wx.CallAfter(self.btemp.SetBackgroundColour, "white")
            wx.CallAfter(self.btemp.Refresh)

    def sethotendgui(self, f):
        self.hsetpoint = f
        if self.display_gauges: self.hottgauge.SetTarget(int(f))
        if self.display_graph: wx.CallAfter(self.graph.SetExtruder0TargetTemperature, int(f))
        if f > 0:
            wx.CallAfter(self.htemp.SetValue, str(f))
            self.set("last_temperature", str(f))
            wx.CallAfter(self.settoff.SetBackgroundColour, None)
            wx.CallAfter(self.settoff.SetForegroundColour, None)
            wx.CallAfter(self.settbtn.SetBackgroundColour, "#FFAA66")
            wx.CallAfter(self.settbtn.SetForegroundColour, "#660000")
            wx.CallAfter(self.htemp.SetBackgroundColour, "#FFDABB")
        else:
            wx.CallAfter(self.settoff.SetBackgroundColour, "#0044CC")
            wx.CallAfter(self.settoff.SetForegroundColour, "white")
            wx.CallAfter(self.settbtn.SetBackgroundColour, None)
            wx.CallAfter(self.settbtn.SetForegroundColour, None)
            wx.CallAfter(self.htemp.SetBackgroundColour, "white")
            wx.CallAfter(self.htemp.Refresh)

    def do_settemp(self, l = ""):
        try:
            if not l.__class__ in (str, unicode) or not len(l):
                l = str(self.htemp.GetValue().split()[0])
            l = l.lower().replace(", ", ".")
            for i in self.temps.keys():
                l = l.replace(i, self.temps[i])
            f = float(l)
            if f >= 0:
                if self.p.online:
                    self.p.send_now("M104 S" + l)
                    print _("Setting hotend temperature to %f degrees Celsius.") % f
                    self.sethotendgui(f)
                else:
                    print _("Printer is not online.")
            else:
                print _("You cannot set negative temperatures. To turn the hotend off entirely, set its temperature to 0.")
        except Exception, x:
            print _("You must enter a temperature. (%s)") % (repr(x),)

    def do_bedtemp(self, l = ""):
        try:
            if not l.__class__ in (str, unicode) or not len(l):
                l = str(self.btemp.GetValue().split()[0])
            l = l.lower().replace(", ", ".")
            for i in self.bedtemps.keys():
                l = l.replace(i, self.bedtemps[i])
            f = float(l)
            if f >= 0:
                if self.p.online:
                    self.p.send_now("M140 S" + l)
                    print _("Setting bed temperature to %f degrees Celsius.") % f
                    self.setbedgui(f)
                else:
                    print _("Printer is not online.")
            else:
                print _("You cannot set negative temperatures. To turn the bed off entirely, set its temperature to 0.")
        except Exception, x:
            print _("You must enter a temperature. (%s)") % (repr(x),)

    def end_macro(self):
        pronsole.pronsole.end_macro(self)
        self.update_macros_menu()

    def delete_macro(self, macro_name):
        pronsole.pronsole.delete_macro(self, macro_name)
        self.update_macros_menu()

    def start_macro(self, macro_name, old_macro_definition = ""):
        if not self.processing_rc:
            def cb(definition):
                if len(definition.strip()) == 0:
                    if old_macro_definition != "":
                        dialog = wx.MessageDialog(self, _("Do you want to erase the macro?"), style = wx.YES_NO | wx.YES_DEFAULT | wx.ICON_QUESTION)
                        if dialog.ShowModal() == wx.ID_YES:
                            self.delete_macro(macro_name)
                            return
                    print _("Cancelled.")
                    return
                self.cur_macro_name = macro_name
                self.cur_macro_def = definition
                self.end_macro()
            MacroEditor(macro_name, old_macro_definition, cb)
        else:
            pronsole.pronsole.start_macro(self, macro_name, old_macro_definition)

    def catchprint(self, l):
        wx.CallAfter(self.addtexttolog, l)

    def project(self, event):
        from printrun import projectlayer
        projectlayer.SettingsFrame(self, self.p).Show()

    def exclude(self, event):
        if not self.fgcode:
            wx.CallAfter(self.statusbar.SetStatusText, _("No file loaded. Please use load first."))
            return
        if not self.excluder:
            self.excluder = Excluder()
        self.excluder.pop_window(self.fgcode, bgcolor = self.settings.bgcolor)

    def popmenu(self):
        self.menustrip = wx.MenuBar()
        # File menu
        m = wx.Menu()
        self.Bind(wx.EVT_MENU, self.loadfile, m.Append(-1, _("&Open..."), _(" Opens file")))

        self.filehistory = wx.FileHistory(maxFiles = 8, idBase = wx.ID_FILE1)
        recent = wx.Menu()
        self.filehistory.UseMenu(recent)
        self.Bind(wx.EVT_MENU_RANGE, self.load_recent_file,
                  id = wx.ID_FILE1, id2 = wx.ID_FILE9)
        m.AppendMenu(wx.ID_ANY, "&Recent Files", recent)
        self.Bind(wx.EVT_MENU, self.clearOutput, m.Append(-1, _("Clear console"), _(" Clear output console")))
        self.Bind(wx.EVT_MENU, self.OnExit, m.Append(wx.ID_EXIT, _("E&xit"), _(" Closes the Window")))
        self.menustrip.Append(m, _("&File"))

        m = wx.Menu()
        self.Bind(wx.EVT_MENU, self.do_editgcode, m.Append(-1, _("&Edit..."), _(" Edit open file")))
        self.Bind(wx.EVT_MENU, self.plate, m.Append(-1, _("Plater"), _(" Compose 3D models into a single plate")))
        self.Bind(wx.EVT_MENU, self.exclude, m.Append(-1, _("Excluder"), _(" Exclude parts of the bed from being printed")))
        self.Bind(wx.EVT_MENU, self.project, m.Append(-1, _("Projector"), _(" Project slices")))
        self.menustrip.Append(m, _("&Tools"))

        m = wx.Menu()
        self.recoverbtn = m.Append(-1, _("Recover"), _(" Recover previous print after a disconnect (homes X, Y, restores Z and E status)"))
        self.recoverbtn.Disable = lambda *a: self.recoverbtn.Enable(False)
        self.Bind(wx.EVT_MENU, self.recover, self.recoverbtn)
        self.menustrip.Append(m, _("&Advanced"))

        if self.settings.slic3rintegration:
            m = wx.Menu()
            self.menustrip.Append(m, _("&Slic3r"))
            print_menu = wx.Menu()
            filament_menu = wx.Menu()
            printer_menu = wx.Menu()
            m.AppendSubMenu(print_menu, _("Print &settings"))
            m.AppendSubMenu(filament_menu, _("&Filament"))
            m.AppendSubMenu(printer_menu, _("&Printer"))
            menus = {"print": print_menu,
                     "filament": filament_menu,
                     "printer": printer_menu}
            self.load_slic3r_configs(menus)

        # Settings menu
        m = wx.Menu()
        self.macros_menu = wx.Menu()
        m.AppendSubMenu(self.macros_menu, _("&Macros"))
        self.Bind(wx.EVT_MENU, self.new_macro, self.macros_menu.Append(-1, _("<&New...>")))
        self.Bind(wx.EVT_MENU, lambda *e: PronterOptions(self), m.Append(-1, _("&Options"), _(" Options dialog")))

        self.Bind(wx.EVT_MENU, lambda x: threading.Thread(target = lambda: self.do_skein("set")).start(), m.Append(-1, _("Slicing Settings"), _(" Adjust slicing settings")))

        mItem = m.AppendCheckItem(-1, _("Debug G-code"),
                                  _("Print all G-code sent to and received from the printer."))
        m.Check(mItem.GetId(), self.p.loud)
        self.Bind(wx.EVT_MENU, self.setloud, mItem)

        #try:
        #    from SkeinforgeQuickEditDialog import SkeinforgeQuickEditDialog
        #    self.Bind(wx.EVT_MENU, lambda *e:SkeinforgeQuickEditDialog(self), m.Append(-1,_("SFACT Quick Settings"),_(" Quickly adjust SFACT settings for active profile")))
        #except:
        #    pass

        self.menustrip.Append(m, _("&Settings"))
        self.update_macros_menu()
        self.SetMenuBar(self.menustrip)

        m = wx.Menu()
        self.Bind(wx.EVT_MENU, self.about,
                  m.Append(-1, _("&About Printrun"), _("Show about dialog")))
        self.menustrip.Append(m, _("&Help"))

    def about(self, event):

        info = wx.AboutDialogInfo()

        info.SetIcon(wx.Icon(iconfile("P-face.ico"), wx.BITMAP_TYPE_ICO))
        info.SetName('Printrun')
        info.SetVersion(printcore.__version__)

        description = _("\
Printrun is a pure Python 3D printing (and other types of CNC) host software.")

        info.SetDescription(description)
        info.SetCopyright('(C) 2011 - 2013')
        info.SetWebSite('https://github.com/kliment/Printrun')

        licence = """\
Printrun is free software: you can redistribute it and/or modify it under the
terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.

Printrun is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
PARTICULAR PURPOSE.  See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with
Printrun. If not, see <http://www.gnu.org/licenses/>."""

        info.SetLicence(licence)
        info.AddDeveloper('Kliment Yanev')
        info.AddDeveloper('Guillaume Seguin')

        wx.AboutBox(info)

    def load_slic3r_configs(self, menus):
        # Hack to get correct path for Slic3r config
        orig_appname = self.app.GetAppName()
        self.app.SetAppName("Slic3r")
        configpath = wx.StandardPaths.Get().GetUserDataDir()
        self.app.SetAppName(orig_appname)
        self.slic3r_configpath = configpath
        configfile = os.path.join(configpath, "slic3r.ini")
        config = self.read_slic3r_config(configfile)
        self.slic3r_configs = {}
        for cat in menus:
            menu = menus[cat]
            pattern = os.path.join(configpath, cat, "*.ini")
            files = sorted(glob.glob(pattern))
            try:
                preset = config.get("presets", cat)
                self.slic3r_configs[cat] = preset
            except:
                preset = None
                self.slic3r_configs[cat] = None
            for f in files:
                name = os.path.splitext(os.path.basename(f))[0]
                item = menu.Append(-1, name, f, wx.ITEM_RADIO)
                item.Check(os.path.basename(f) == preset)
                self.Bind(wx.EVT_MENU,
                          lambda event, cat = cat, f = f:
                          self.set_slic3r_config(configfile, cat, f), item)

    def read_slic3r_config(self, configfile, parser = None):
        import ConfigParser
        parser = ConfigParser.RawConfigParser()

        class add_header(object):
            def __init__(self, f):
                self.f = f
                self.header = '[dummy]'

            def readline(self):
                if self.header:
                    try: return self.header
                    finally: self.header = None
                else:
                    return self.f.readline()
        parser.readfp(add_header(open(configfile)), configfile)
        return parser

    def set_slic3r_config(self, configfile, cat, file):
        self.slic3r_configs[cat] = file
        if self.settings.slic3rupdate:
            config = self.read_slic3r_config(configfile)
            config.set("presets", cat, os.path.basename(file))
            f = StringIO.StringIO()
            config.write(f)
            data = f.getvalue()
            f.close()
            data = data.replace("[dummy]\n", "")
            with open(configfile, "w") as f:
                f.write(data)

    def doneediting(self, gcode):
        open(self.filename, "w").write("\n".join(gcode))
        wx.CallAfter(self.loadfile, None, self.filename)

    def do_editgcode(self, e = None):
        if self.filename is not None:
            MacroEditor(self.filename, [line.raw for line in self.fgcode], self.doneediting, 1)

    def new_macro(self, e = None):
        dialog = wx.Dialog(self, -1, _("Enter macro name"), size = (260, 85))
        panel = wx.Panel(dialog, -1)
        vbox = wx.BoxSizer(wx.VERTICAL)
        wx.StaticText(panel, -1, _("Macro name:"), (8, 14))
        dialog.namectrl = wx.TextCtrl(panel, -1, '', (110, 8), size = (130, 24), style = wx.TE_PROCESS_ENTER)
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        okb = wx.Button(dialog, wx.ID_OK, _("Ok"), size = (60, 24))
        dialog.Bind(wx.EVT_TEXT_ENTER, lambda e: dialog.EndModal(wx.ID_OK), dialog.namectrl)
        #dialog.Bind(wx.EVT_BUTTON, lambda e:self.new_macro_named(dialog, e), okb)
        hbox.Add(okb)
        hbox.Add(wx.Button(dialog, wx.ID_CANCEL, _("Cancel"), size = (60, 24)))
        vbox.Add(panel)
        vbox.Add(hbox, 1, wx.ALIGN_CENTER | wx.TOP | wx.BOTTOM, 10)
        dialog.SetSizer(vbox)
        dialog.Centre()
        macro = ""
        if dialog.ShowModal() == wx.ID_OK:
            macro = dialog.namectrl.GetValue()
            if macro != "":
                wx.CallAfter(self.edit_macro, macro)
        dialog.Destroy()
        return macro

    def edit_macro(self, macro):
        if macro == "": return self.new_macro()
        if macro in self.macros:
            old_def = self.macros[macro]
        elif len([c for c in macro.encode("ascii", "replace") if not c.isalnum() and c != "_"]):
            print _("Macro name may contain only ASCII alphanumeric symbols and underscores")
            return
        elif hasattr(self.__class__, "do_" + macro):
            print _("Name '%s' is being used by built-in command") % macro
            return
        else:
            old_def = ""
        self.start_macro(macro, old_def)
        return macro

    def update_macros_menu(self):
        if not hasattr(self, "macros_menu"):
            return  # too early, menu not yet built
        try:
            while True:
                item = self.macros_menu.FindItemByPosition(1)
                if item is None: break
                self.macros_menu.DeleteItem(item)
        except:
            pass
        for macro in self.macros.keys():
            self.Bind(wx.EVT_MENU, lambda x, m = macro: self.start_macro(m, self.macros[m]), self.macros_menu.Append(-1, macro))

    def OnExit(self, event):
        self.Close()

    def rescanports(self, event = None):
        scanned = self.scanserial()
        portslist = list(scanned)
        if self.settings.port != "" and self.settings.port not in portslist:
            portslist.append(self.settings.port)
            self.serialport.Clear()
            self.serialport.AppendItems(portslist)
        if os.path.exists(self.settings.port) or self.settings.port in scanned:
            self.serialport.SetValue(self.settings.port)
        elif portslist:
            self.serialport.SetValue(portslist[0])

    def cbkey(self, e):
        if e.GetKeyCode() == wx.WXK_UP:
            if self.commandbox.histindex == len(self.commandbox.history):
                self.commandbox.history.append(self.commandbox.GetValue())  # save current command
            if len(self.commandbox.history):
                self.commandbox.histindex = (self.commandbox.histindex - 1) % len(self.commandbox.history)
                self.commandbox.SetValue(self.commandbox.history[self.commandbox.histindex])
                self.commandbox.SetSelection(0, len(self.commandbox.history[self.commandbox.histindex]))
        elif e.GetKeyCode() == wx.WXK_DOWN:
            if self.commandbox.histindex == len(self.commandbox.history):
                self.commandbox.history.append(self.commandbox.GetValue())  # save current command
            if len(self.commandbox.history):
                self.commandbox.histindex = (self.commandbox.histindex + 1) % len(self.commandbox.history)
                self.commandbox.SetValue(self.commandbox.history[self.commandbox.histindex])
                self.commandbox.SetSelection(0, len(self.commandbox.history[self.commandbox.histindex]))
        else:
            e.Skip()

    def plate(self, e):
        from . import plater
        print _("Plate function activated")
        plater.StlPlater(size = (800, 580), callback = self.platecb,
                         parent = self,
                         build_dimensions = self.build_dimensions_list,
                         simarrange_path = self.settings.simarrange_path).Show()

    def platecb(self, name):
        print _("Plated %s") % name
        self.loadfile(None, name)

    def sdmenu(self, e):
        obj = e.GetEventObject()
        popupmenu = wx.Menu()
        item = popupmenu.Append(-1, _("SD Upload"))
        if not self.fgcode:
            item.Enable(False)
        self.Bind(wx.EVT_MENU, self.upload, id = item.GetId())
        item = popupmenu.Append(-1, _("SD Print"))
        self.Bind(wx.EVT_MENU, self.sdprintfile, id = item.GetId())
        self.panel.PopupMenu(popupmenu, obj.GetPosition())

    def htemp_change(self, event):
        if self.hsetpoint > 0:
            self.do_settemp("")
        wx.CallAfter(self.htemp.SetInsertionPoint, 0)

    def btemp_change(self, event):
        if self.bsetpoint > 0:
            self.do_bedtemp("")
        wx.CallAfter(self.btemp.SetInsertionPoint, 0)

    def tool_change(self, event):
        self.do_tool(self.extrudersel.GetValue())

    def showwin(self, event):
        if self.fgcode:
            self.gwindow.Show(True)
            self.gwindow.SetToolTip(wx.ToolTip("Mousewheel zooms the display\nShift / Mousewheel scrolls layers"))
            self.gwindow.Raise()

    def update_recent_files(self, param, value):
        if self.filehistory is None:
            return
        try:
            recent_files = json.loads(value)
        except:
            self.logError(_("Failed to load recent files list:") +
                          "\n" + traceback.format_exc())
        # Clear history
        while self.filehistory.GetCount():
            self.filehistory.RemoveFileFromHistory(0)
        recent_files.reverse()
        for f in recent_files:
            self.filehistory.AddFileToHistory(f)

    def update_gviz_params(self, param, value):
        params_map = {"preview_extrusion_width": "extrusion_width",
                      "preview_grid_step1": "grid",
                      "preview_grid_step2": "grid"}
        if param not in params_map:
            return
        trueparam = params_map[param]
        if hasattr(self.gviz, trueparam):
            gviz = self.gviz
        elif hasattr(self.gwindow, "p") and hasattr(self.gwindow.p, trueparam):
            gviz = self.gwindow.p
        else:
            return
        if trueparam == "grid":
            try:
                item = int(param[-1])  # extract list item position
                grid = list(gviz.grid)
                grid[item - 1] = value
                value = tuple(grid)
            except:
                traceback.print_exc()
        if hasattr(self.gviz, trueparam):
            self.apply_gviz_params(self.gviz, trueparam, value)
        if hasattr(self.gwindow, "p") and hasattr(self.gwindow.p, trueparam):
            self.apply_gviz_params(self.gwindow.p, trueparam, value)

    def apply_gviz_params(self, widget, param, value):
        setattr(widget, param, value)
        widget.dirty = 1
        wx.CallAfter(widget.Refresh)

    def setfeeds(self, e):
        self.feedrates_changed = True
        try:
            self.settings._set("e_feedrate", self.efeedc.GetValue())
        except:
            pass
        try:
            self.settings._set("z_feedrate", self.zfeedc.GetValue())
        except:
            pass
        try:
            self.settings._set("xy_feedrate", self.xyfeedc.GetValue())
        except:
            pass
        try:
            self.settings._set("last_extrusion", self.edist.GetValue())
        except:
            pass

    def cbuttons_reload(self):
        allcbs = getattr(self, "custombuttonbuttons", [])
        for button in allcbs:
            self.centersizer.Detach(button)
            button.Destroy()
        self.custombuttonbuttons = []
        custombuttons = self.custombuttons[:] + [None]
        for i, btndef in enumerate(custombuttons):
            if btndef is None:
                if i == len(custombuttons) - 1:
                    self.newbuttonbutton = b = wx.Button(self.centerpanel, -1, "+", size = (19, 18), style = wx.BU_EXACTFIT)
                    #b.SetFont(wx.Font(12, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
                    b.SetForegroundColour("#4444ff")
                    b.SetToolTip(wx.ToolTip(_("click to add new custom button")))
                    b.Bind(wx.EVT_BUTTON, self.cbutton_edit)
                else:
                    b = wx.StaticText(self.panel, -1, "")
            else:
                b = wx.Button(self.centerpanel, -1, btndef.label, style = wx.BU_EXACTFIT)
                b.SetToolTip(wx.ToolTip(_("Execute command: ") + btndef.command))
                if btndef.background:
                    b.SetBackgroundColour(btndef.background)
                    rr, gg, bb = b.GetBackgroundColour().Get()
                    if 0.3 * rr + 0.59 * gg + 0.11 * bb < 60:
                        b.SetForegroundColour("#ffffff")
                b.custombutton = i
                b.properties = btndef
            if btndef is not None:
                b.Bind(wx.EVT_BUTTON, self.procbutton)
                b.Bind(wx.EVT_MOUSE_EVENTS, self.editbutton)
            self.custombuttonbuttons.append(b)
            if type(self.centersizer) == wx.GridBagSizer:
                self.centersizer.Add(b, pos = (i // 4, i % 4), flag = wx.EXPAND)
            else:
                self.centersizer.Add(b, flag = wx.EXPAND)
        self.centerpanel.Layout()

    def help_button(self):
        print _('Defines custom button. Usage: button <num> "title" [/c "colour"] command')

    def do_button(self, argstr):
        def nextarg(rest):
            rest = rest.lstrip()
            if rest.startswith('"'):
                return rest[1:].split('"', 1)
            else:
                return rest.split(None, 1)
        #try:
        num, argstr = nextarg(argstr)
        num = int(num)
        title, argstr = nextarg(argstr)
        colour = None
        try:
            c1, c2 = nextarg(argstr)
            if c1 == "/c":
                colour, argstr = nextarg(c2)
        except:
            pass
        command = argstr.strip()
        if num < 0 or num >= 64:
            print _("Custom button number should be between 0 and 63")
            return
        while num >= len(self.custombuttons):
            self.custombuttons.append(None)
        self.custombuttons[num] = SpecialButton(title, command)
        if colour is not None:
            self.custombuttons[num].background = colour
        if not self.processing_rc:
            self.cbuttons_reload()
        #except Exception, x:
        #    print "Bad syntax for button definition, see 'help button'"
        #    print x

    def cbutton_save(self, n, bdef, new_n = None):
        if new_n is None: new_n = n
        if bdef is None or bdef == "":
            self.save_in_rc(("button %d" % n), '')
        elif bdef.background:
            colour = bdef.background
            if type(colour) not in (str, unicode):
                #print type(colour), map(type, colour)
                if type(colour) == tuple and tuple(map(type, colour)) == (int, int, int):
                    colour = map(lambda x: x % 256, colour)
                    colour = wx.Colour(*colour).GetAsString(wx.C2S_NAME | wx.C2S_HTML_SYNTAX)
                else:
                    colour = wx.Colour(colour).GetAsString(wx.C2S_NAME | wx.C2S_HTML_SYNTAX)
            self.save_in_rc(("button %d" % n), 'button %d "%s" /c "%s" %s' % (new_n, bdef.label, colour, bdef.command))
        else:
            self.save_in_rc(("button %d" % n), 'button %d "%s" %s' % (new_n, bdef.label, bdef.command))

    def cbutton_edit(self, e, button = None):
        bedit = ButtonEdit(self)
        if button is not None:
            n = button.custombutton
            bedit.name.SetValue(button.properties.label)
            bedit.command.SetValue(button.properties.command)
            if button.properties.background:
                colour = button.properties.background
                if type(colour) not in (str, unicode):
                    #print type(colour)
                    if type(colour) == tuple and tuple(map(type, colour)) == (int, int, int):
                        colour = map(lambda x: x % 256, colour)
                        colour = wx.Colour(*colour).GetAsString(wx.C2S_NAME | wx.C2S_HTML_SYNTAX)
                    else:
                        colour = wx.Colour(colour).GetAsString(wx.C2S_NAME | wx.C2S_HTML_SYNTAX)
                bedit.color.SetValue(colour)
        else:
            n = len(self.custombuttons)
            while n > 0 and self.custombuttons[n - 1] is None:
                n -= 1
        if bedit.ShowModal() == wx.ID_OK:
            if n == len(self.custombuttons):
                self.custombuttons.append(None)
            self.custombuttons[n] = SpecialButton(bedit.name.GetValue().strip(), bedit.command.GetValue().strip(), custom = True)
            if bedit.color.GetValue().strip() != "":
                self.custombuttons[n].background = bedit.color.GetValue()
            self.cbutton_save(n, self.custombuttons[n])
        wx.CallAfter(bedit.Destroy)
        wx.CallAfter(self.cbuttons_reload)

    def cbutton_remove(self, e, button):
        n = button.custombutton
        self.cbutton_save(n, None)
        del self.custombuttons[n]
        for i in range(n, len(self.custombuttons)):
            self.cbutton_save(i, self.custombuttons[i])
        wx.CallAfter(self.cbuttons_reload)

    def cbutton_order(self, e, button, dir):
        n = button.custombutton
        if dir < 0:
            n = n - 1
        if n + 1 >= len(self.custombuttons):
            self.custombuttons.append(None)  # pad
        # swap
        self.custombuttons[n], self.custombuttons[n + 1] = self.custombuttons[n + 1], self.custombuttons[n]
        self.cbutton_save(n, self.custombuttons[n])
        self.cbutton_save(n + 1, self.custombuttons[n + 1])
        #if self.custombuttons[-1] is None:
        #    del self.custombuttons[-1]
        wx.CallAfter(self.cbuttons_reload)

    def editbutton(self, e):
        if e.IsCommandEvent() or e.ButtonUp(wx.MOUSE_BTN_RIGHT):
            if e.IsCommandEvent():
                pos = (0, 0)
            else:
                pos = e.GetPosition()
            popupmenu = wx.Menu()
            obj = e.GetEventObject()
            if hasattr(obj, "custombutton"):
                item = popupmenu.Append(-1, _("Edit custom button '%s'") % e.GetEventObject().GetLabelText())
                self.Bind(wx.EVT_MENU, lambda e, button = e.GetEventObject(): self.cbutton_edit(e, button), item)
                item = popupmenu.Append(-1, _("Move left <<"))
                self.Bind(wx.EVT_MENU, lambda e, button = e.GetEventObject(): self.cbutton_order(e, button, -1), item)
                if obj.custombutton == 0: item.Enable(False)
                item = popupmenu.Append(-1, _("Move right >>"))
                self.Bind(wx.EVT_MENU, lambda e, button = e.GetEventObject(): self.cbutton_order(e, button, 1), item)
                if obj.custombutton == 63: item.Enable(False)
                pos = self.panel.ScreenToClient(e.GetEventObject().ClientToScreen(pos))
                item = popupmenu.Append(-1, _("Remove custom button '%s'") % e.GetEventObject().GetLabelText())
                self.Bind(wx.EVT_MENU, lambda e, button = e.GetEventObject(): self.cbutton_remove(e, button), item)
            else:
                item = popupmenu.Append(-1, _("Add custom button"))
                self.Bind(wx.EVT_MENU, self.cbutton_edit, item)
            self.panel.PopupMenu(popupmenu, pos)
        elif e.Dragging() and e.ButtonIsDown(wx.MOUSE_BTN_LEFT):
            obj = e.GetEventObject()
            scrpos = obj.ClientToScreen(e.GetPosition())
            if not hasattr(self, "dragpos"):
                self.dragpos = scrpos
                e.Skip()
                return
            else:
                dx, dy = self.dragpos[0] - scrpos[0], self.dragpos[1] - scrpos[1]
                if dx * dx + dy * dy < 5 * 5:  # threshold to detect dragging for jittery mice
                    e.Skip()
                    return
            if not hasattr(self, "dragging"):
                # init dragging of the custom button
                if hasattr(obj, "custombutton") and obj.properties is not None:
                    #self.newbuttonbutton.SetLabel("")
                    #self.newbuttonbutton.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
                    #self.newbuttonbutton.SetForegroundColour("black")
                    #self.newbuttonbutton.SetSize(obj.GetSize())
                    #if self.uppersizer.GetItem(self.newbuttonbutton) is not None:
                    #    self.uppersizer.SetItemMinSize(self.newbuttonbutton, obj.GetSize())
                    #    self.mainsizer.Layout()
                    for b in self.custombuttonbuttons:
                        #if b.IsFrozen(): b.Thaw()
                        if b.properties is None:
                            b.Enable()
                            b.SetLabel("")
                            b.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
                            b.SetForegroundColour("black")
                            b.SetSize(obj.GetSize())
                            if self.uppersizer.GetItem(b) is not None:
                                self.uppersizer.SetItemMinSize(b, obj.GetSize())
                                self.mainsizer.Layout()
                        #    b.SetStyle(wx.ALIGN_CENTRE+wx.ST_NO_AUTORESIZE+wx.SIMPLE_BORDER)
                    self.dragging = wx.Button(self.panel, -1, obj.GetLabel(), style = wx.BU_EXACTFIT)
                    self.dragging.SetBackgroundColour(obj.GetBackgroundColour())
                    self.dragging.SetForegroundColour(obj.GetForegroundColour())
                    self.dragging.sourcebutton = obj
                    self.dragging.Raise()
                    self.dragging.Disable()
                    self.dragging.SetPosition(self.panel.ScreenToClient(scrpos))
                    self.last_drag_dest = obj
                    self.dragging.label = obj.s_label = obj.GetLabel()
                    self.dragging.bgc = obj.s_bgc = obj.GetBackgroundColour()
                    self.dragging.fgc = obj.s_fgc = obj.GetForegroundColour()
            else:
                # dragging in progress
                self.dragging.SetPosition(self.panel.ScreenToClient(scrpos))
                wx.CallAfter(self.dragging.Refresh)
                dst = None
                src = self.dragging.sourcebutton
                drg = self.dragging
                for b in self.custombuttonbuttons:
                    if b.GetScreenRect().Contains(scrpos):
                        dst = b
                        break
                #if dst is None and self.panel.GetScreenRect().Contains(scrpos):
                #    # try to check if it is after buttons at the end
                #    tspos = self.panel.ClientToScreen(self.uppersizer.GetPosition())
                #    bspos = self.panel.ClientToScreen(self.centersizer.GetPosition())
                #    tsrect = wx.Rect(*(tspos.Get()+self.uppersizer.GetSize().Get()))
                #    bsrect = wx.Rect(*(bspos.Get()+self.centersizer.GetSize().Get()))
                #    lbrect = btns[-1].GetScreenRect()
                #    p = scrpos.Get()
                #    if len(btns)<4 and tsrect.Contains(scrpos):
                #        if lbrect.GetRight() < p[0]:
                #            print "Right of last button on upper cb sizer"
                #    if bsrect.Contains(scrpos):
                #        if lbrect.GetBottom() < p[1]:
                #            print "Below last button on lower cb sizer"
                #        if lbrect.GetRight() < p[0] and lbrect.GetTop() <= p[1] and lbrect.GetBottom() >= p[1]:
                #            print "Right to last button on lower cb sizer"
                if dst is not self.last_drag_dest:
                    if self.last_drag_dest is not None:
                        self.last_drag_dest.SetBackgroundColour(self.last_drag_dest.s_bgc)
                        self.last_drag_dest.SetForegroundColour(self.last_drag_dest.s_fgc)
                        self.last_drag_dest.SetLabel(self.last_drag_dest.s_label)
                    if dst is not None and dst is not src:
                        dst.s_bgc = dst.GetBackgroundColour()
                        dst.s_fgc = dst.GetForegroundColour()
                        dst.s_label = dst.GetLabel()
                        src.SetBackgroundColour(dst.GetBackgroundColour())
                        src.SetForegroundColour(dst.GetForegroundColour())
                        src.SetLabel(dst.GetLabel())
                        dst.SetBackgroundColour(drg.bgc)
                        dst.SetForegroundColour(drg.fgc)
                        dst.SetLabel(drg.label)
                    else:
                        src.SetBackgroundColour(drg.bgc)
                        src.SetForegroundColour(drg.fgc)
                        src.SetLabel(drg.label)
                    self.last_drag_dest = dst
        elif hasattr(self, "dragging") and not e.ButtonIsDown(wx.MOUSE_BTN_LEFT):
            # dragging finished
            obj = e.GetEventObject()
            scrpos = obj.ClientToScreen(e.GetPosition())
            dst = None
            src = self.dragging.sourcebutton
            drg = self.dragging
            for b in self.custombuttonbuttons:
                if b.GetScreenRect().Contains(scrpos):
                    dst = b
                    break
            if dst is not None:
                src_i = src.custombutton
                dst_i = dst.custombutton
                self.custombuttons[src_i], self.custombuttons[dst_i] = self.custombuttons[dst_i], self.custombuttons[src_i]
                self.cbutton_save(src_i, self.custombuttons[src_i])
                self.cbutton_save(dst_i, self.custombuttons[dst_i])
                while self.custombuttons[-1] is None:
                    del self.custombuttons[-1]
            wx.CallAfter(self.dragging.Destroy)
            del self.dragging
            wx.CallAfter(self.cbuttons_reload)
            del self.last_drag_dest
            del self.dragpos
        else:
            e.Skip()

    def homeButtonClicked(self, corner):
        # When user clicks on the XY control, the Z control no longer gets spacebar/repeat signals
        self.zb.clearRepeat()
        if corner == 0:  # upper-left
            self.onecmd('home X')
        elif corner == 1:  # upper-right
            self.onecmd('home Y')
        elif corner == 2:  # lower-right
            self.onecmd('home Z')
        elif corner == 3:  # lower-left
            self.onecmd('home')
        else:
            return
        self.p.send_now('M114')

    def clamped_move_message(self):
        print _("Manual move outside of the build volume prevented (see the \"Clamp manual moves\" option).")

    def moveXY(self, x, y):
        # When user clicks on the XY control, the Z control no longer gets spacebar/repeat signals
        self.zb.clearRepeat()
        if x != 0:
            if self.settings.clamp_jogging:
                new_x = self.current_pos[0] + x
                if new_x < self.build_dimensions_list[3] or new_x > self.build_dimensions_list[0] + self.build_dimensions_list[3]:
                    self.clamped_move_message()
                    return
            self.onecmd('move X %s' % x)
        elif y != 0:
            if self.settings.clamp_jogging:
                new_y = self.current_pos[1] + y
                if new_y < self.build_dimensions_list[4] or new_y > self.build_dimensions_list[1] + self.build_dimensions_list[4]:
                    self.clamped_move_message()
                    return
            self.onecmd('move Y %s' % y)
        else:
            return
        self.p.send_now('M114')

    def moveZ(self, z):
        if z != 0:
            if self.settings.clamp_jogging:
                new_z = self.current_pos[2] + z
                if new_z < self.build_dimensions_list[5] or new_z > self.build_dimensions_list[2] + self.build_dimensions_list[5]:
                    self.clamped_move_message()
                    return
            self.onecmd('move Z %s' % z)
            self.p.send_now('M114')
        # When user clicks on the Z control, the XY control no longer gets spacebar/repeat signals
        self.xyb.clearRepeat()

    def spacebarAction(self):
        self.zb.repeatLast()
        self.xyb.repeatLast()

    def parseusercmd(self, line):
        if line.upper().startswith("M114"):
            self.userm114 += 1
        elif line.upper().startswith("M105"):
            self.userm105 += 1

    def procbutton(self, e):
        try:
            if hasattr(e.GetEventObject(), "custombutton"):
                if wx.GetKeyState(wx.WXK_CONTROL) or wx.GetKeyState(wx.WXK_ALT):
                    return self.editbutton(e)
                self.cur_button = e.GetEventObject().custombutton
            command = e.GetEventObject().properties.command
            self.parseusercmd(command)
            self.onecmd(command)
            self.cur_button = None
        except:
            print _("event object missing")
            self.cur_button = None
            raise

    def kill(self, e):
        self.statuscheck = False
        if self.status_thread:
            self.status_thread.join()
            self.status_thread = None
        self.p.recvcb = None
        self.p.disconnect()
        if hasattr(self, "feedrates_changed"):
            self.save_in_rc("set xy_feedrate", "set xy_feedrate %d" % self.settings.xy_feedrate)
            self.save_in_rc("set z_feedrate", "set z_feedrate %d" % self.settings.z_feedrate)
            self.save_in_rc("set e_feedrate", "set e_feedrate %d" % self.settings.e_feedrate)
        if self.settings.last_extrusion != self.settings.default_extrusion:
            self.save_in_rc("set last_extrusion", "set last_extrusion %d" % self.settings.last_extrusion)
        if self.excluder:
            self.excluder.close_window()
        wx.CallAfter(self.gwindow.Destroy)
        wx.CallAfter(self.Destroy)

    def do_monitor(self, l = ""):
        if l.strip() == "":
            self.monitorbox.SetValue(not self.monitorbox.GetValue())
        elif l.strip() == "off":
            wx.CallAfter(self.monitorbox.SetValue, False)
        else:
            try:
                self.monitor_interval = float(l)
                wx.CallAfter(self.monitorbox.SetValue, self.monitor_interval > 0)
            except:
                print _("Invalid period given.")
        self.setmonitor(None)
        if self.monitor:
            print _("Monitoring printer.")
        else:
            print _("Done monitoring.")

    def setmonitor(self, e):
        self.monitor = self.monitorbox.GetValue()
        self.set("monitor", self.monitor)
        if self.display_graph:
            if self.monitor:
                wx.CallAfter(self.graph.StartPlotting, 1000)
            else:
                wx.CallAfter(self.graph.StopPlotting)

    def addtexttolog(self, text):
        try:
            self.logbox.AppendText(text)
        except:
            print _("Attempted to write invalid text to console, which could be due to an invalid baudrate")

    def setloud(self, e):
        self.p.loud = e.IsChecked()

    def sendline(self, e):
        command = self.commandbox.GetValue()
        if not len(command):
            return
        wx.CallAfter(self.addtexttolog, ">>>" + command + "\n")
        self.parseusercmd(str(command))
        self.onecmd(str(command))
        self.commandbox.SetSelection(0, len(command))
        self.commandbox.history.append(command)
        self.commandbox.histindex = len(self.commandbox.history)

    def clearOutput(self, e):
        self.logbox.Clear()

    def update_tempdisplay(self):
        try:
            # FIXME : we don't use setpoints here, we should probably exploit them
            temps = parse_temperature_report(self.tempreport)
            if "T0" in temps:
                hotend_temp = float(temps["T0"][0])
            else:
                hotend_temp = float(temps["T"][0]) if "T" in temps else None
            if hotend_temp is not None:
                if self.display_graph: wx.CallAfter(self.graph.SetExtruder0Temperature, hotend_temp)
                if self.display_gauges: wx.CallAfter(self.hottgauge.SetValue, hotend_temp)
                setpoint = None
                if "T0" in temps and temps["T0"][1]: setpoint = float(temps["T0"][1])
                elif temps["T"][1]: setpoint = float(temps["T"][1])
                if setpoint is not None:
                    if self.display_graph: wx.CallAfter(self.graph.SetExtruder0TargetTemperature, setpoint)
                    if self.display_gauges: wx.CallAfter(self.hottgauge.SetTarget, setpoint)
            if "T1" in temps:
                hotend_temp = float(temps["T1"][0])
                if self.display_graph: wx.CallAfter(self.graph.SetExtruder1Temperature, hotend_temp)
                setpoint = temps["T1"][1]
                if setpoint and self.display_graph:
                    wx.CallAfter(self.graph.SetExtruder1TargetTemperature, float(setpoint))
            bed_temp = float(temps["B"][0]) if "B" in temps else None
            if bed_temp is not None:
                if self.display_graph: wx.CallAfter(self.graph.SetBedTemperature, bed_temp)
                if self.display_gauges: wx.CallAfter(self.bedtgauge.SetValue, bed_temp)
                setpoint = temps["B"][1]
                if setpoint:
                    setpoint = float(setpoint)
                    if self.display_graph: wx.CallAfter(self.graph.SetBedTargetTemperature, setpoint)
                    if self.display_gauges: wx.CallAfter(self.bedtgauge.SetTarget, setpoint)
        except:
            traceback.print_exc()

    def update_pos(self, l):
        bits = gcoder.m114_exp.findall(l)
        x = None
        y = None
        z = None
        for bit in bits:
            if not bit[0]: continue
            if x is None and bit[0] == "X":
                x = float(bit[1])
            elif y is None and bit[0] == "Y":
                y = float(bit[1])
            elif z is None and bit[0] == "Z":
                z = float(bit[1])
        if x is not None: self.current_pos[0] = x
        if y is not None: self.current_pos[1] = y
        if z is not None: self.current_pos[2] = z

    def statuschecker(self):
        while self.statuscheck:
            string = ""
            fractioncomplete = 0.0
            if self.sdprinting or self.uploading:
                if self.uploading:
                    fractioncomplete = float(self.p.queueindex) / len(self.p.mainqueue)
                    string += _("SD upload: %04.2f%% |") % (100 * fractioncomplete,)
                    string += _(" Line# %d of %d lines |") % (self.p.queueindex, len(self.p.mainqueue))
                else:
                    fractioncomplete = float(self.percentdone / 100.0)
                    string += _("SD printing: %04.2f%% |") % (self.percentdone,)
                if fractioncomplete > 0.0:
                    secondselapsed = int(time.time() - self.starttime + self.extra_print_time)
                    secondsestimate = secondselapsed / fractioncomplete
                    secondsremain = secondsestimate - secondselapsed
                    string += _(" Est: %s of %s remaining | ") % (format_duration(secondsremain),
                                                                  format_duration(secondsestimate))
                    string += _(" Z: %.3f mm") % self.curlayer
            elif self.p.printing:
                fractioncomplete = float(self.p.queueindex) / len(self.p.mainqueue)
                string += _("Printing: %04.2f%% |") % (100 * float(self.p.queueindex) / len(self.p.mainqueue),)
                string += _(" Line# %d of %d lines |") % (self.p.queueindex, len(self.p.mainqueue))
                if self.p.queueindex > 0:
                    secondselapsed = int(time.time() - self.starttime + self.extra_print_time)
                    secondsremain, secondsestimate = self.compute_eta(self.p.queueindex, secondselapsed)
                    string += _(" Est: %s of %s remaining | ") % (format_duration(secondsremain),
                                                                  format_duration(secondsestimate))
                    string += _(" Z: %.3f mm") % self.curlayer
            wx.CallAfter(self.statusbar.SetStatusText, string)
            wx.CallAfter(self.gviz.Refresh)
            if self.p.online:
                if self.p.writefailures >= 4:
                    self.logError(_("Disconnecting after 4 failed writes."))
                    self.status_thread = None
                    self.disconnect()
                    return
            if self.monitor and self.p.online:
                if self.sdprinting:
                    self.p.send_now("M27")
                if self.m105_waitcycles % 10 == 0:
                    self.p.send_now("M105")
                self.m105_waitcycles += 1
            cur_time = time.time()
            wait_time = 0
            while time.time() < cur_time + self.monitor_interval - 0.25:
                if not self.statuscheck:
                    break
                time.sleep(0.25)
                # Safeguard: if system time changes and goes back in the past,
                # we could get stuck almost forever
                wait_time += 0.25
                if wait_time > self.monitor_interval - 0.25:
                    break
            # Always sleep at least a bit, if something goes wrong with the
            # system time we'll avoid freezing the whole app this way
            time.sleep(0.25)
            try:
                while not self.sentlines.empty():
                    gc = self.sentlines.get_nowait()
                    wx.CallAfter(self.gviz.addgcode, gc, 1)
                    self.sentlines.task_done()
            except Queue.Empty:
                pass
        wx.CallAfter(self.statusbar.SetStatusText, _("Not connected to printer."))

    def recvcb(self, l):
        isreport = False
        if "ok C:" in l or "Count" in l \
           or ("X:" in l and len(gcoder.m114_exp.findall(l)) == 6):
            self.posreport = l
            self.update_pos(l)
            if self.userm114 > 0:
                self.userm114 -= 1
            else:
                isreport = True
        if "ok T:" in l or ("T:" in l and "E:" in l):
            self.tempreport = l
            wx.CallAfter(self.tempdisp.SetLabel, self.tempreport.strip().replace("ok ", ""))
            self.update_tempdisplay()
            if self.userm105 > 0:
                self.userm105 -= 1
            else:
                self.m105_waitcycles = 0
                isreport = True
        tstring = l.rstrip()
        if not self.p.loud and (tstring not in ["ok", "wait"] and not isreport):
            wx.CallAfter(self.addtexttolog, tstring + "\n")
        for listener in self.recvlisteners:
            listener(l)

    def listfiles(self, line, ignored = False):
        if "Begin file list" in line:
            self.listing = 1
        elif "End file list" in line:
            self.listing = 0
            self.recvlisteners.remove(self.listfiles)
            wx.CallAfter(self.filesloaded)
        elif self.listing:
            self.sdfiles.append(line.strip().lower())

    def waitforsdresponse(self, l):
        if "file.open failed" in l:
            wx.CallAfter(self.statusbar.SetStatusText, _("Opening file failed."))
            self.recvlisteners.remove(self.waitforsdresponse)
            return
        if "File opened" in l:
            wx.CallAfter(self.statusbar.SetStatusText, l)
        if "File selected" in l:
            wx.CallAfter(self.statusbar.SetStatusText, _("Starting print"))
            self.sdprinting = 1
            self.p.send_now("M24")
            self.startcb()
            return
        if "Done printing file" in l:
            wx.CallAfter(self.statusbar.SetStatusText, l)
            self.sdprinting = 0
            self.recvlisteners.remove(self.waitforsdresponse)
            self.endcb()
            return
        if "SD printing byte" in l:
            #M27 handler
            try:
                resp = l.split()
                vals = resp[-1].split("/")
                self.percentdone = 100.0 * int(vals[0]) / int(vals[1])
            except:
                pass

    def filesloaded(self):
        dlg = wx.SingleChoiceDialog(self, _("Select the file to print"), _("Pick SD file"), self.sdfiles)
        if(dlg.ShowModal() == wx.ID_OK):
            target = dlg.GetStringSelection()
            if len(target):
                self.recvlisteners.append(self.waitforsdresponse)
                self.p.send_now("M23 " + target.lower())
        dlg.Destroy()
        #print self.sdfiles

    def getfiles(self):
        if not self.p.online:
            self.sdfiles = []
            return
        self.listing = 0
        self.sdfiles = []
        self.recvlisteners.append(self.listfiles)
        self.p.send_now("M21")
        self.p.send_now("M20")

    def model_to_gcode_filename(self, filename):
        suffix = "_export.gcode"
        for ext in [".stl", ".obj"]:
            filename = filename.replace(ext, suffix)
            filename = filename.replace(ext.upper(), suffix)
        return filename

    def skein_func(self):
        try:
            param = self.expandcommand(self.settings.slicecommand)
            output_filename = self.model_to_gcode_filename(self.filename)
            pararray = [i.replace("$s", self.filename).replace("$o", output_filename) for i in shlex.split(param.replace("\\", "\\\\"))]
            if self.settings.slic3rintegration:
                for cat, config in self.slic3r_configs.items():
                    if config:
                        fpath = os.path.join(self.slic3r_configpath, cat, config)
                        pararray += ["--load", fpath]
            print _("Slicing ") + " ".join(pararray)
            self.skeinp = subprocess.Popen(pararray, stderr = subprocess.STDOUT, stdout = subprocess.PIPE)
            while True:
                o = self.skeinp.stdout.read(1)
                if o == '' and self.skeinp.poll() is not None: break
                sys.stdout.write(o)
            self.skeinp.wait()
            self.stopsf = 1
        except:
            logging.error(_("Failed to execute slicing software: "))
            self.stopsf = 1
            traceback.print_exc(file = sys.stdout)

    def skein_monitor(self):
        while not self.stopsf:
            try:
                wx.CallAfter(self.statusbar.SetStatusText, _("Slicing..."))  # +self.cout.getvalue().split("\n")[-1])
            except:
                pass
            time.sleep(0.1)
        fn = self.filename
        try:
            self.filename = self.model_to_gcode_filename(self.filename)
            self.load_gcode(self.filename)
            if self.p.online:
                wx.CallAfter(self.printbtn.Enable)

            wx.CallAfter(self.statusbar.SetStatusText, _("Loaded %s, %d lines") % (self.filename, len(self.fgcode),))
            print _("Loaded %s, %d lines") % (self.filename, len(self.fgcode),)
            wx.CallAfter(self.pausebtn.Disable)
            wx.CallAfter(self.printbtn.SetLabel, _("Print"))

            threading.Thread(target = self.loadviz).start()
        except:
            self.filename = fn
        wx.CallAfter(self.loadbtn.SetLabel, _("Load File"))
        self.skeining = 0
        self.skeinp = None

    def skein(self, filename):
        wx.CallAfter(self.loadbtn.SetLabel, _("Cancel"))
        print _("Slicing ") + filename
        self.cout = StringIO.StringIO()
        self.filename = filename
        self.stopsf = 0
        self.skeining = 1
        threading.Thread(target = self.skein_func).start()
        threading.Thread(target = self.skein_monitor).start()

    def cmdline_filename_callback(self, filename):
        # Do nothing when processing a filename from command line, as we'll
        # handle it when everything has been prepared
        self.filename = filename

    def do_load(self, l):
        if hasattr(self, 'skeining'):
            self.loadfile(None, l)
        else:
            self._do_load(l)

    def load_recent_file(self, event):
        fileid = event.GetId() - wx.ID_FILE1
        path = self.filehistory.GetHistoryFile(fileid)
        self.loadfile(None, filename = path)

    def loadfile(self, event, filename = None):
        if self.skeining and self.skeinp is not None:
            self.skeinp.terminate()
            return
        basedir = self.settings.last_file_path
        if not os.path.exists(basedir):
            basedir = "."
            try:
                basedir = os.path.split(self.filename)[0]
            except:
                pass
        dlg = None
        if filename is None:
            dlg = wx.FileDialog(self, _("Open file to print"), basedir, style = wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
            dlg.SetWildcard(_("OBJ, STL, and GCODE files (*.gcode;*.gco;*.g;*.stl;*.STL;*.obj;*.OBJ)|*.gcode;*.gco;*.g;*.stl;*.STL;*.obj;*.OBJ|All Files (*.*)|*.*"))
        if filename or dlg.ShowModal() == wx.ID_OK:
            if filename:
                name = filename
            else:
                name = dlg.GetPath()
                dlg.Destroy()
            if not os.path.exists(name):
                self.statusbar.SetStatusText(_("File not found!"))
                return
            path = os.path.split(name)[0]
            if path != self.settings.last_file_path:
                self.set("last_file_path", path)
            try:
                abspath = os.path.abspath(name)
                recent_files = json.loads(self.settings.recentfiles)
                if abspath in recent_files:
                    recent_files.remove(abspath)
                recent_files.insert(0, abspath)
                if len(recent_files) > 5:
                    recent_files = recent_files[:5]
                self.set("recentfiles", json.dumps(recent_files))
            except:
                self.logError(_("Could not update recent files list:") +
                              "\n" + traceback.format_exc())
            if name.lower().endswith(".stl"):
                self.skein(name)
            elif name.lower().endswith(".obj"):
                self.skein(name)
            else:
                self.filename = name
                self.load_gcode(self.filename)
                self.statusbar.SetStatusText(_("Loaded %s, %d lines") % (name, len(self.fgcode)))
                print _("Loaded %s, %d lines") % (name, len(self.fgcode))
                wx.CallAfter(self.printbtn.SetLabel, _("Print"))
                wx.CallAfter(self.pausebtn.SetLabel, _("Pause"))
                wx.CallAfter(self.pausebtn.Disable)
                wx.CallAfter(self.recoverbtn.Disable)
                if self.p.online:
                    wx.CallAfter(self.printbtn.Enable)
                threading.Thread(target = self.loadviz).start()
        else:
            dlg.Destroy()

    def loadviz(self):
        gcode = self.fgcode
        print gcode.filament_length, _("mm of filament used in this print")
        print _("The print goes:")
        print _("- from %.2f mm to %.2f mm in X and is %.2f mm wide") % (gcode.xmin, gcode.xmax, gcode.width)
        print _("- from %.2f mm to %.2f mm in Y and is %.2f mm deep") % (gcode.ymin, gcode.ymax, gcode.depth)
        print _("- from %.2f mm to %.2f mm in Z and is %.2f mm high") % (gcode.zmin, gcode.zmax, gcode.height)
        print _("Estimated duration: %s") % gcode.estimate_duration()
        self.gviz.clear()
        self.gwindow.p.clear()
        self.gviz.addfile(gcode, True)
        self.gwindow.p.addfile(gcode)
        wx.CallAfter(self.gviz.Refresh)

    def printfile(self, event):
        self.extra_print_time = 0
        if self.paused:
            self.p.paused = 0
            self.paused = 0
            if self.sdprinting:
                self.on_startprint()
                self.p.send_now("M26 S0")
                self.p.send_now("M24")
                return

        if not self.fgcode:
            wx.CallAfter(self.statusbar.SetStatusText, _("No file loaded. Please use load first."))
            return
        if not self.p.online:
            wx.CallAfter(self.statusbar.SetStatusText, _("Not connected to printer."))
            return
        self.on_startprint()
        self.p.startprint(self.fgcode)

    def on_startprint(self):
        wx.CallAfter(self.pausebtn.SetLabel, _("Pause"))
        wx.CallAfter(self.pausebtn.Enable)
        wx.CallAfter(self.printbtn.SetLabel, _("Restart"))

    def endupload(self):
        self.p.send_now("M29 ")
        wx.CallAfter(self.statusbar.SetStatusText, _("File upload complete"))
        time.sleep(0.5)
        self.p.clear = True
        self.uploading = False

    def uploadtrigger(self, l):
        if "Writing to file" in l:
            self.uploading = True
            self.p.startprint(self.fgcode)
            self.p.endcb = self.endupload
            self.recvlisteners.remove(self.uploadtrigger)
        elif "open failed, File" in l:
            self.recvlisteners.remove(self.uploadtrigger)

    def upload(self, event):
        if not self.fgcode:
            return
        if not self.p.online:
            return
        dlg = wx.TextEntryDialog(self, ("Enter a target filename in 8.3 format:"), _("Pick SD filename"), dosify(self.filename))
        if dlg.ShowModal() == wx.ID_OK:
            self.p.send_now("M21")
            self.p.send_now("M28 " + str(dlg.GetValue()))
            self.recvlisteners.append(self.uploadtrigger)
        dlg.Destroy()

    def pause(self, event):
        if not self.paused:
            print _("Print paused at: %s") % format_time(time.time())
            if self.sdprinting:
                self.p.send_now("M25")
            else:
                if(not self.p.printing):
                    #print "Not printing, cannot pause."
                    return
                self.p.pause()
                self.p.runSmallScript(self.pauseScript)
            self.paused = True
            #self.p.runSmallScript(self.pauseScript)
            self.extra_print_time += int(time.time() - self.starttime)
            wx.CallAfter(self.pausebtn.SetLabel, _("Resume"))
        else:
            print _("Resuming.")
            self.paused = False
            if self.sdprinting:
                self.p.send_now("M24")
            else:
                self.p.resume()
            wx.CallAfter(self.pausebtn.SetLabel, _("Pause"))

    def sdprintfile(self, event):
        self.on_startprint()
        threading.Thread(target = self.getfiles).start()

    def connect(self, event = None):
        print _("Connecting...")
        port = None
        if self.serialport.GetValue():
            port = str(self.serialport.GetValue())
        else:
            scanned = self.scanserial()
            if scanned:
                port = scanned[0]
        baud = 115200
        try:
            baud = int(self.baud.GetValue())
        except:
            print _("Could not parse baud rate: ")
            traceback.print_exc(file = sys.stdout)
        if self.paused:
            self.p.paused = 0
            self.p.printing = 0
            wx.CallAfter(self.pausebtn.SetLabel, _("Pause"))
            wx.CallAfter(self.printbtn.SetLabel, _("Print"))
            self.paused = 0
            if self.sdprinting:
                self.p.send_now("M26 S0")
        try:
            self.p.connect(port, baud)
        except SerialException as e:
            # Currently, there is no errno, but it should be there in the future
            if e.errno == 2:
                self.logError(_("Error: You are trying to connect to a non-existing port."))
            elif e.errno == 8:
                self.logError(_("Error: You don't have permission to open %s.") % port)
                self.logError(_("You might need to add yourself to the dialout group."))
            else:
                self.logError(traceback.format_exc())
            # Kill the scope anyway
            return
        except OSError as e:
            if e.errno == 2:
                self.logError(_("Error: You are trying to connect to a non-existing port."))
            else:
                self.logError(traceback.format_exc())
            return
        self.statuscheck = True
        if port != self.settings.port:
            self.set("port", port)
        if baud != self.settings.baudrate:
            self.set("baudrate", str(baud))
        self.status_thread = threading.Thread(target = self.statuschecker)
        self.status_thread.start()
        if self.predisconnect_mainqueue:
            self.recoverbtn.Enable()

    def recover(self, event):
        self.extra_print_time = 0
        if not self.p.online:
            wx.CallAfter(self.statusbar.SetStatusText, _("Not connected to printer."))
            return
        # Reset Z
        self.p.send_now("G92 Z%f" % self.predisconnect_layer)
        # Home X and Y
        self.p.send_now("G28 X Y")
        self.on_startprint()
        self.p.startprint(self.predisconnect_mainqueue, self.p.queueindex)

    def store_predisconnect_state(self):
        self.predisconnect_mainqueue = self.p.mainqueue
        self.predisconnect_queueindex = self.p.queueindex
        self.predisconnect_layer = self.curlayer

    def disconnect(self, event = None):
        print _("Disconnected.")
        if self.p.printing or self.p.paused or self.paused:
            self.store_predisconnect_state()
        self.p.disconnect()
        self.statuscheck = False
        if self.status_thread:
            self.status_thread.join()
            self.status_thread = None

        self.connectbtn.SetLabel(_("Connect"))
        self.connectbtn.SetToolTip(wx.ToolTip("Connect to the printer"))
        self.connectbtn.Bind(wx.EVT_BUTTON, self.connect)

        wx.CallAfter(self.printbtn.Disable)
        wx.CallAfter(self.pausebtn.Disable)
        wx.CallAfter(self.recoverbtn.Disable)
        for i in self.printerControls:
            wx.CallAfter(i.Disable)

        # Disable XYButtons and ZButtons
        wx.CallAfter(self.xyb.disable)
        wx.CallAfter(self.zb.disable)

        if self.paused:
            self.p.paused = 0
            self.p.printing = 0
            wx.CallAfter(self.pausebtn.SetLabel, _("Pause"))
            wx.CallAfter(self.printbtn.SetLabel, _("Print"))
            self.paused = 0
            if self.sdprinting:
                self.p.send_now("M26 S0")

    def reset(self, event):
        print _("Reset.")
        dlg = wx.MessageDialog(self, _("Are you sure you want to reset the printer?"), _("Reset?"), wx.YES | wx.NO)
        if dlg.ShowModal() == wx.ID_YES:
            self.p.reset()
            self.sethotendgui(0)
            self.setbedgui(0)
            self.p.printing = 0
            wx.CallAfter(self.printbtn.SetLabel, _("Print"))
            if self.paused:
                self.p.paused = 0
                wx.CallAfter(self.pausebtn.SetLabel, _("Pause"))
                self.paused = 0
        dlg.Destroy()

    def lock(self, event = None, force = None):
        if force is not None:
            self.locker.SetValue(force)
        if self.locker.GetValue():
            print _("Locking interface.")
            for panel in self.panels:
                panel.Disable()
        else:
            print _("Unlocking interface.")
            for panel in self.panels:
                panel.Enable()

class PronterApp(wx.App):

    mainwindow = None

    def __init__(self, *args, **kwargs):
        super(PronterApp, self).__init__(*args, **kwargs)
        self.SetAppName("Pronterface")
        self.mainwindow = PronterWindow(self)
        self.mainwindow.Show()
