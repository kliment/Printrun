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
import platform
import queue
import sys
import time
import threading
import traceback
import io as StringIO
import subprocess
import glob
import logging
import re

try: import simplejson as json
except ImportError: import json

from . import pronsole
from . import printcore
from printrun.spoolmanager import spoolmanager_gui

from .utils import install_locale, setup_logging, dosify, \
    iconfile, configfile, format_time, format_duration, \
    hexcolor_to_float, parse_temperature_report, \
    prepare_command, check_rgb_color, check_rgba_color, compile_file, \
    write_history_to, read_history_from
install_locale('pronterface')

try:
    import wx
    import wx.adv
    if wx.VERSION < (4,):
        raise ImportError()
except:
    logging.error(_("WX >= 4 is not installed. This program requires WX >= 4 to run."))
    raise

from .gui.widgets import SpecialButton, MacroEditor, PronterOptions, ButtonEdit

winsize = (800, 500)
layerindex = 0
if os.name == "nt":
    winsize = (800, 530)

pronterface_quitting = False

class PronterfaceQuitException(Exception):
    pass

from .gui import MainWindow
from .settings import wxSetting, HiddenSetting, StringSetting, SpinSetting, \
    FloatSpinSetting, BooleanSetting, StaticTextSetting, ColorSetting, ComboSetting
from printrun import gcoder
from .pronsole import REPORT_NONE, REPORT_POS, REPORT_TEMP, REPORT_MANUAL

def format_length(mm, fractional=2):
    if mm <= 10:
        units = mm
        suffix = 'mm'
    elif mm < 1000:
        units = mm / 10
        suffix = 'cm'
    else:
        units = mm / 1000
        suffix = 'm'
    return '%%.%df' % fractional % units + suffix

class ConsoleOutputHandler:
    """Handle console output. All messages go through the logging submodule. We setup a logging handler to get logged messages and write them to both stdout (unless a log file path is specified, in which case we add another logging handler to write to this file) and the log panel.
    We also redirect stdout and stderr to ourself to catch print messages and al."""

    def __init__(self, target, log_path):
        self.stdout = sys.stdout
        self.stderr = sys.stderr
        sys.stdout = self
        sys.stderr = self
        self.print_on_stdout = not log_path
        if log_path:
            setup_logging(self, log_path, reset_handlers = True)
        else:
            setup_logging(sys.stdout, reset_handlers = True)
        self.target = target

    def __del__(self):
        sys.stdout = self.stdout
        sys.stderr = self.stderr

    def write(self, data):
        try:
            self.target(data)
        except:
            pass
        if self.print_on_stdout:
            self.stdout.write(data)

    def flush(self):
        if self.stdout:
            self.stdout.flush()

class PronterWindow(MainWindow, pronsole.pronsole):

    _fgcode = None
    printer_progress_time = time.time()

    def _get_fgcode(self):
        return self._fgcode

    def _set_fgcode(self, value):
        self._fgcode = value
        self.excluder = None
        self.excluder_e = None
        self.excluder_z_abs = None
        self.excluder_z_rel = None
    fgcode = property(_get_fgcode, _set_fgcode)

    def _get_display_graph(self):
        return self.settings.tempgraph
    display_graph = property(_get_display_graph)

    def _get_display_gauges(self):
        return self.settings.tempgauges
    display_gauges = property(_get_display_gauges)

    def __init__(self, app, filename = None, size = winsize):
        pronsole.pronsole.__init__(self)
        self.app = app
        self.window_ready = False
        self.ui_ready = False
        self._add_settings(size)

        self.pauseScript = None #"pause.gcode"
        self.endScript = None #"end.gcode"

        self.filename = filename

        self.capture_skip = {}
        self.capture_skip_newline = False
        self.fgcode = None
        self.excluder = None
        self.slicep = None
        self.current_pos = [0, 0, 0]
        self.paused = False
        self.uploading = False
        self.sentglines = queue.Queue(0)
        self.cpbuttons = {
            "motorsoff": SpecialButton(_("Motors off"), ("M84"), (250, 250, 250), _("Switch all motors off")),
            "extrude": SpecialButton(_("Extrude"), ("pront_extrude"), (225, 200, 200), _("Advance extruder by set length")),
            "reverse": SpecialButton(_("Reverse"), ("pront_reverse"), (225, 200, 200), _("Reverse extruder by set length")),
        }
        self.custombuttons = []
        self.btndict = {}
        self.filehistory = None
        self.autoconnect = False
        self.autoscrolldisable = False

        self.parse_cmdline(sys.argv[1:])
        for field in dir(self.settings):
            if field.startswith("_gcview_color_"):
                cleanname = field[1:]
                color = hexcolor_to_float(getattr(self.settings, cleanname), 4)
                setattr(self, cleanname, list(color))

        # FIXME: We need to initialize the main window after loading the
        # configs to restore the size, but this might have some unforeseen
        # consequences.
        # -- Okai, it seems it breaks things like update_gviz_params ><
        os.putenv("UBUNTU_MENUPROXY", "0")
        size = (self.settings.last_window_width, self.settings.last_window_height)
        MainWindow.__init__(self, None, title = _("Pronterface"), size = size)
        if self.settings.last_window_maximized:
            self.Maximize()
        self.SetIcon(wx.Icon(iconfile("pronterface.png"), wx.BITMAP_TYPE_PNG))
        self.Bind(wx.EVT_SIZE, self.on_resize)
        self.Bind(wx.EVT_MAXIMIZE, self.on_maximize)
        self.window_ready = True
        self.Bind(wx.EVT_CLOSE, self.closewin)
        self.Bind(wx.EVT_CHAR_HOOK, self.on_key)
        # set feedrates in printcore for pause/resume
        self.p.xy_feedrate = self.settings.xy_feedrate
        self.p.z_feedrate = self.settings.z_feedrate

        self.panel.SetBackgroundColour(self.bgcolor)
        customdict = {}
        try:
            exec(compile_file(configfile("custombtn.txt")), customdict)
            if len(customdict["btns"]):
                if not len(self.custombuttons):
                    try:
                        self.custombuttons = customdict["btns"]
                        for n in range(len(self.custombuttons)):
                            self.cbutton_save(n, self.custombuttons[n])
                        os.rename("custombtn.txt", "custombtn.old")
                        rco = open("custombtn.txt", "w")
                        rco.write(_("# I moved all your custom buttons into .pronsolerc.\n# Please don't add them here any more.\n# Backup of your old buttons is in custombtn.old\n"))
                        rco.close()
                    except IOError as x:
                        logging.error(str(x))
                else:
                    logging.warning(_("Note!!! You have specified custom buttons in both custombtn.txt and .pronsolerc"))
                    logging.warning(_("Ignoring custombtn.txt. Remove all current buttons to revert to custombtn.txt"))

        except:
            pass
        self.menustrip = wx.MenuBar()
        self.reload_ui()
        # disable all printer controls until we connect to a printer
        self.gui_set_disconnected()
        self.statusbar = self.CreateStatusBar()
        self.statusbar.SetStatusText(_("Not connected to printer."))

        self.t = ConsoleOutputHandler(self.catchprint, self.settings.log_path)
        self.stdout = sys.stdout
        self.slicing = False
        self.loading_gcode = False
        self.loading_gcode_message = ""
        self.mini = False
        self.p.sendcb = self.sentcb
        self.p.preprintsendcb = self.preprintsendcb
        self.p.printsendcb = self.printsentcb
        self.p.startcb = self.startcb
        self.p.endcb = self.endcb
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
            self.update_monitor()

    #  --------------------------------------------------------------
    #  Main interface handling
    #  --------------------------------------------------------------

    def reset_ui(self):
        MainWindow.reset_ui(self)
        self.custombuttons_widgets = []

    def reload_ui(self, *args):
        if not self.window_ready: return
        temp_monitor = self.settings.monitor
        self.settings.monitor = False
        self.update_monitor()
        self.Freeze()

        # If UI is being recreated, delete current one
        if self.ui_ready:
            # Store log console content
            logcontent = self.logbox.GetValue()
            self.menustrip.SetMenus([])
            if len(self.commandbox.history):
                #save current command box history
                if not os.path.exists(self.history_file):
                    if not os.path.exists(self.cache_dir):
                        os.makedirs(self.cache_dir)
                write_history_to(self.history_file, self.commandbox.history)
            # Create a temporary panel to reparent widgets with state we want
            # to retain across UI changes
            temppanel = wx.Panel(self)
            # TODO: add viz widgets to statefulControls
            for control in self.statefulControls:
                control.GetContainingSizer().Detach(control)
                control.Reparent(temppanel)
            self.panel.DestroyChildren()
            self.gwindow.Destroy()
            self.reset_ui()

        # Create UI
        self.create_menu()
        self.update_recent_files("recentfiles", self.settings.recentfiles)
        self.splitterwindow = None
        if self.settings.uimode in (_("Tabbed"), _("Tabbed with platers")):
            self.createTabbedGui()
        else:
            self.createGui(self.settings.uimode == _("Compact"),
                           self.settings.controlsmode == "Mini")

        if self.splitterwindow:
            self.splitterwindow.SetSashPosition(self.settings.last_sash_position)

            def splitter_resize(event):
                self.splitterwindow.UpdateSize()
            self.splitterwindow.Bind(wx.EVT_SIZE, splitter_resize)

            def sash_position_changed(event):
                self.set("last_sash_position", self.splitterwindow.GetSashPosition())
            self.splitterwindow.Bind(wx.EVT_SPLITTER_SASH_POS_CHANGED, sash_position_changed)

        # Set gcview parameters here as they don't get set when viewers are
        # created
        self.update_gcview_params()

        # Finalize
        if self.p.online:
            self.gui_set_connected()
        if self.ui_ready:
            self.logbox.SetValue(logcontent)
            temppanel.Destroy()
            self.panel.Layout()
            if self.fgcode:
                self.start_viz_thread()
        self.ui_ready = True
        self.settings.monitor = temp_monitor
        self.commandbox.history = read_history_from(self.history_file)
        self.commandbox.histindex = len(self.commandbox.history)
        self.Thaw()
        if self.settings.monitor:
            self.update_monitor()

    def on_resize(self, event):
        wx.CallAfter(self.on_resize_real)
        event.Skip()

    def on_resize_real(self):
        maximized = self.IsMaximized()
        self.set("last_window_maximized", maximized)
        if not maximized and not self.IsIconized():
            size = self.GetSize()
            self.set("last_window_width", size[0])
            self.set("last_window_height", size[1])

    def on_maximize(self, event):
        self.set("last_window_maximized", self.IsMaximized())
        event.Skip()

    def on_exit(self, event):
        self.Close()

    def on_settings_change(self, changed_settings):
        if self.gviz:
            self.gviz.on_settings_change(changed_settings)

    def on_key(self, event):
        if not isinstance(event.EventObject, (wx.TextCtrl, wx.ComboBox)) \
            or event.HasModifiers():
            ch = chr(event.KeyCode)
            keys = {'B': self.btemp, 'H': self.htemp, 'J': self.xyb, 'S': self.commandbox,
                'V': self.gviz}
            widget = keys.get(ch)
            #ignore Alt+(S, H), so it can open Settings, Help menu
            if widget and (ch not in 'SH' or not event.AltDown()) \
                and not (event.ControlDown() and ch == 'V'
                        and event.EventObject is self.commandbox):
                widget.SetFocus()
                return
            # On MSWindows button mnemonics are processed only if the
            # focus is in the parent panel
            if event.AltDown() and ch < 'Z':
                in_toolbar = self.toolbarsizer.GetItem(event.EventObject)
                candidates = (self.connectbtn, self.connectbtn_cb_var), \
                            (self.pausebtn, self.pause), \
                            (self.printbtn, self.printfile)
                for ctl, cb in candidates:
                    match = ('&' + ch) in ctl.Label.upper()
                    handled = in_toolbar and match
                    if handled:
                        break
                    # react to 'P' even for 'Restart', 'Resume'
                    # print('match', match, 'handled', handled, ctl.Label, ctl.Enabled)
                    if (match or ch == 'P' and ctl != self.connectbtn) and ctl.Enabled:
                        # print('call', ch, cb)
                        cb()
                        # react to only 1 of 'P' buttons, prefer Resume
                        return

        event.Skip()

    def closewin(self, e):
        e.StopPropagation()
        self.do_exit("force")

    def kill(self, e=None):
        if len(self.commandbox.history):
                #save current command box history
                history = (self.history_file)
                if not os.path.exists(history):
                    if not os.path.exists(self.cache_dir):
                        os.makedirs(self.cache_dir)
                write_history_to(history,self.commandbox.history)
        if self.p.printing or self.p.paused:
            dlg = wx.MessageDialog(self, _("Print in progress ! Are you really sure you want to quit ?"), _("Exit"), wx.YES_NO | wx.ICON_WARNING)
            if dlg.ShowModal() == wx.ID_NO:
                return
        pronsole.pronsole.kill(self)
        global pronterface_quitting
        pronterface_quitting = True
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

    @property
    def bgcolor(self):
        return (wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOWFRAME)
                if self.settings.bgcolor == 'auto'
                else self.settings.bgcolor)

    #  --------------------------------------------------------------
    #  Main interface actions
    #  --------------------------------------------------------------

    def do_monitor(self, l = ""):
        if l.strip() == "":
            self.set("monitor", not self.settings.monitor)
        elif l.strip() == "off":
            self.set("monitor", False)
        else:
            try:
                self.monitor_interval = float(l)
                self.set("monitor", self.monitor_interval > 0)
            except:
                self.log(_("Invalid period given."))
        if self.settings.monitor:
            self.log(_("Monitoring printer."))
        else:
            self.log(_("Done monitoring."))

    def do_pront_extrude(self, l = ""):
        if self.p.printing and not self.paused:
            self.log(_("Please pause or stop print before extruding."))
            return
        feed = self.settings.e_feedrate
        self.do_extrude_final(self.edist.GetValue(), feed)

    def do_pront_reverse(self, l = ""):
        if self.p.printing and not self.paused:
            self.log(_("Please pause or stop print before reversing."))
            return
        feed = self.settings.e_feedrate
        self.do_extrude_final(- self.edist.GetValue(), feed)

    def do_settemp(self, l = ""):
        try:
            if not isinstance(l, str) or not len(l):
                l = str(self.htemp.GetValue().split()[0])
            l = l.lower().replace(", ", ".")
            for i in self.temps.keys():
                l = l.replace(i, self.temps[i])
            f = float(l)
            if f >= 0:
                if self.p.online:
                    self.p.send_now("M104 S" + l)
                    self.log(_("Setting hotend temperature to %g degrees Celsius.") % f)
                    self.sethotendgui(f)
                else:
                    self.logError(_("Printer is not online."))
            else:
                self.logError(_("You cannot set negative temperatures. To turn the hotend off entirely, set its temperature to 0."))
        except Exception as x:
            self.logError(_("You must enter a temperature. (%s)") % (repr(x),))

    def do_bedtemp(self, l = ""):
        try:
            if not isinstance(l, str) or not len(l):
                l = str(self.btemp.GetValue().split()[0])
            l = l.lower().replace(", ", ".")
            for i in self.bedtemps.keys():
                l = l.replace(i, self.bedtemps[i])
            f = float(l)
            if f >= 0:
                if self.p.online:
                    self.p.send_now("M140 S" + l)
                    self.log(_("Setting bed temperature to %g degrees Celsius.") % f)
                    self.setbedgui(f)
                else:
                    self.logError(_("Printer is not online."))
            else:
                self.logError(_("You cannot set negative temperatures. To turn the bed off entirely, set its temperature to 0."))
        except Exception as x:
            self.logError(_("You must enter a temperature. (%s)") % (repr(x),))

    def do_setspeed(self, l = ""):
        try:
            if not isinstance(l, str) or not len(l):
                l = str(self.speed_slider.GetValue())
            else:
                l = l.lower()
            speed = int(l)
            if self.p.online:
                self.p.send_now("M220 S" + l)
                self.log(_("Setting print speed factor to %d%%.") % speed)
            else:
                self.logError(_("Printer is not online."))
        except Exception as x:
            self.logError(_("You must enter a speed. (%s)") % (repr(x),))

    def do_setflow(self, l = ""):
        try:
            if not isinstance(l, str) or not len(l):
                l = str(self.flow_slider.GetValue())
            else:
                l = l.lower()
            flow = int(l)
            if self.p.online:
                self.p.send_now("M221 S" + l)
                self.log(_("Setting print flow factor to %d%%.") % flow)
            else:
                self.logError(_("Printer is not online."))
        except Exception as x:
            self.logError(_("You must enter a flow. (%s)") % (repr(x),))

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

    def appendCommandHistory(self):
        cmd = self.commandbox.Value
        hist = self.commandbox.history
        append = cmd and (not hist or hist[-1] != cmd)
        if append:
            self.commandbox.history.append(cmd)
        return append

    def cbkey(self, e):
        dir = {wx.WXK_UP: -1, wx.WXK_DOWN: 1}.get(e.KeyCode)
        if dir:
            if self.commandbox.histindex == len(self.commandbox.history):
                if dir == 1:
                    # do not cycle top => bottom
                    return
                #save unsent command before going back
                self.appendCommandHistory()
            self.commandbox.histindex = max(0, min(self.commandbox.histindex + dir, len(self.commandbox.history)))
            self.commandbox.Value = (self.commandbox.history[self.commandbox.histindex]
                if self.commandbox.histindex < len(self.commandbox.history)
                else '')
            self.commandbox.SetInsertionPointEnd()
        else:
            e.Skip()

    def plate(self, e):
        from . import stlplater as plater
        self.log(_("Plate function activated"))
        plater.StlPlater(size = (800, 580), callback = self.platecb,
                         parent = self,
                         build_dimensions = self.build_dimensions_list,
                         circular_platform = self.settings.circular_bed,
                         simarrange_path = self.settings.simarrange_path,
                         antialias_samples = int(self.settings.antialias3dsamples)).Show()

    def plate_gcode(self, e):
        from . import gcodeplater as plater
        self.log(_("G-Code plate function activated"))
        plater.GcodePlater(size = (800, 580), callback = self.platecb,
                           parent = self,
                           build_dimensions = self.build_dimensions_list,
                           circular_platform = self.settings.circular_bed,
                           antialias_samples = int(self.settings.antialias3dsamples)).Show()

    def platecb(self, name):
        self.log(_("Plated %s") % name)
        self.loadfile(None, name)
        if self.settings.uimode in (_("Tabbed"), _("Tabbed with platers")):
            # Switch to page 1 (Status tab)
            self.notebook.SetSelection(1)

    def do_editgcode(self, e = None):
        if self.filename is not None:
            MacroEditor(self.filename, [line.raw for line in self.fgcode], self.doneediting, True)

    def doneediting(self, gcode):
        open(self.filename, "w").write("\n".join(gcode))
        wx.CallAfter(self.loadfile, None, self.filename)

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

    def show_viz_window(self, event):
        if self.fgcode:
            self.gwindow.Show(True)
            self.gwindow.SetToolTip(wx.ToolTip("Mousewheel zooms the display\nShift / Mousewheel scrolls layers"))
            self.gwindow.Raise()

    def setfeeds(self, e):
        self.feedrates_changed = True
        try:
            if self.efeedc is not None:
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

    def homeButtonClicked(self, axis):
        # When user clicks on the XY control, the Z control no longer gets spacebar/repeat signals
        self.zb.clearRepeat()
        if axis == "x":
            self.onecmd('home X')
        elif axis == "y":  # upper-right
            self.onecmd('home Y')
        elif axis == "z":
            self.onecmd('home Z')
        elif axis == "all":
            self.onecmd('home')
        elif axis == "center":
            center_x = self.build_dimensions_list[0] / 2 + self.build_dimensions_list[3]
            center_y = self.build_dimensions_list[1] / 2 + self.build_dimensions_list[4]
            feed = self.settings.xy_feedrate
            self.onecmd('G0 X%s Y%s F%s' % (center_x, center_y, feed))
        else:
            return
        self.p.send_now('M114')

    def clamped_move_message(self):
        self.log(_("Manual move outside of the build volume prevented (see the \"Clamp manual moves\" option)."))

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

    #  --------------------------------------------------------------
    #  Console handling
    #  --------------------------------------------------------------

    def catchprint(self, l):
        """Called by the Tee operator to write to the log box"""
        if not self.IsFrozen():
            wx.CallAfter(self.addtexttolog, l)

    def addtexttolog(self, text):
        try:
            max_length = 20000
            current_length = self.logbox.GetLastPosition()
            if current_length > max_length:
                self.logbox.Remove(0, current_length / 10)
            currentCaretPosition = self.logbox.GetInsertionPoint()
            currentLengthOfText = self.logbox.GetLastPosition()
            if self.autoscrolldisable:
                self.logbox.Freeze()
                currentSelectionStart, currentSelectionEnd = self.logbox.GetSelection()
                self.logbox.SetInsertionPointEnd()
                self.logbox.AppendText(text)
                self.logbox.SetInsertionPoint(currentCaretPosition)
                self.logbox.SetSelection(currentSelectionStart, currentSelectionEnd)
                self.logbox.Thaw()
            else:
                self.logbox.SetInsertionPointEnd()
                self.logbox.AppendText(text)

        except:
            self.log(_("Attempted to write invalid text to console, which could be due to an invalid baudrate"))

    def clear_log(self, e):
        self.logbox.Clear()

    def set_verbose_communications(self, e):
        self.p.loud = e.IsChecked()

    def set_autoscrolldisable(self,e):
        self.autoscrolldisable = e.IsChecked()

    def sendline(self, e):
        command = self.commandbox.Value
        if not len(command):
            return
        logging.info(">>> " + command)
        line = self.precmd(str(command))
        self.onecmd(line)
        self.appendCommandHistory()
        self.commandbox.histindex = len(self.commandbox.history)
        self.commandbox.Value = ''

    #  --------------------------------------------------------------
    #  Main menu handling & actions
    #  --------------------------------------------------------------

    def create_menu(self):
        """Create main menu"""

        # File menu
        m = wx.Menu()
        self.Bind(wx.EVT_MENU, self.loadfile, m.Append(-1, _("&Open...\tCtrl+O"), _(" Open file")))
        self.savebtn = m.Append(-1, _("&Save..."), _(" Save file"))
        self.savebtn.Enable(False)
        self.Bind(wx.EVT_MENU, self.savefile, self.savebtn)

        self.filehistory = wx.FileHistory(maxFiles = 8, idBase = wx.ID_FILE1)
        recent = wx.Menu()
        self.filehistory.UseMenu(recent)
        self.Bind(wx.EVT_MENU_RANGE, self.load_recent_file,
                  id = wx.ID_FILE1, id2 = wx.ID_FILE9)
        m.Append(wx.ID_ANY, _("&Recent Files"), recent)
        self.Bind(wx.EVT_MENU, self.clear_log, m.Append(-1, _("Clear console\tCtrl+L"), _(" Clear output console")))
        self.Bind(wx.EVT_MENU, self.on_exit, m.Append(wx.ID_EXIT, _("E&xit"), _(" Closes the Window")))
        self.menustrip.Append(m, _("&File"))

        # Tools Menu
        m = wx.Menu()
        self.Bind(wx.EVT_MENU, self.do_editgcode, m.Append(-1, _("&Edit..."), _(" Edit open file")))
        self.Bind(wx.EVT_MENU, self.plate, m.Append(-1, _("Plater"), _(" Compose 3D models into a single plate")))
        self.Bind(wx.EVT_MENU, self.plate_gcode, m.Append(-1, _("G-Code Plater"), _(" Compose G-Codes into a single plate")))
        self.Bind(wx.EVT_MENU, self.exclude, m.Append(-1, _("Excluder"), _(" Exclude parts of the bed from being printed")))
        self.Bind(wx.EVT_MENU, self.project, m.Append(-1, _("Projector"), _(" Project slices")))
        self.Bind(wx.EVT_MENU,
                  self.show_spool_manager,
                  m.Append(-1, _("Spool Manager"),
                           _(" Manage different spools of filament")))
        self.menustrip.Append(m, _("&Tools"))

        # Advanced Menu
        m = wx.Menu()
        self.recoverbtn = m.Append(-1, _("Recover"), _(" Recover previous print after a disconnect (homes X, Y, restores Z and E status)"))
        self.recoverbtn.Disable = lambda *a: self.recoverbtn.Enable(False)
        self.Bind(wx.EVT_MENU, self.recover, self.recoverbtn)
        self.menustrip.Append(m, _("&Advanced"))

        if self.settings.slic3rintegration:
            m = wx.Menu()
            print_menu = wx.Menu()
            filament_menu = wx.Menu()
            printer_menu = wx.Menu()
            m.AppendSubMenu(print_menu, _("Print &settings"))
            m.AppendSubMenu(filament_menu, _("&Filament"))
            m.AppendSubMenu(printer_menu, _("&Printer"))
            menus = {"print": print_menu,
                     "filament": filament_menu,
                     "printer": printer_menu}
            try:
                self.load_slic3r_configs(menus)
                self.menustrip.Append(m, _("&Slic3r"))
            except IOError:
                self.logError(_("Failed to load Slic3r configuration:") +
                              "\n" + traceback.format_exc())

        # Settings menu
        m = wx.Menu()
        self.macros_menu = wx.Menu()
        m.AppendSubMenu(self.macros_menu, _("&Macros"))
        self.Bind(wx.EVT_MENU, self.new_macro, self.macros_menu.Append(-1, _("<&New...>")))
        self.Bind(wx.EVT_MENU, lambda *e: PronterOptions(self), m.Append(-1, _("&Options"), _(" Options dialog")))

        self.Bind(wx.EVT_MENU, lambda x: threading.Thread(target = lambda: self.do_slice("set")).start(), m.Append(-1, _("Slicing settings"), _(" Adjust slicing settings")))

        mItem = m.AppendCheckItem(-1, _("Debug communications"),
                                  _("Print all G-code sent to and received from the printer."))
        m.Check(mItem.GetId(), self.p.loud)
        self.Bind(wx.EVT_MENU, self.set_verbose_communications, mItem)

        mItem = m.AppendCheckItem(-1, _("Don't autoscroll"),
                                  _("Disables automatic scrolling of the console when new text is added"))
        m.Check(mItem.GetId(), self.autoscrolldisable)
        self.Bind(wx.EVT_MENU, self.set_autoscrolldisable, mItem)

        self.menustrip.Append(m, _("&Settings"))
        self.update_macros_menu()
        self.SetMenuBar(self.menustrip)

        m = wx.Menu()
        self.Bind(wx.EVT_MENU, self.about,
                  m.Append(-1, _("&About Printrun"), _("Show about dialog")))
        self.menustrip.Append(m, _("&Help"))

    def project(self, event):
        """Start Projector tool"""
        from printrun import projectlayer
        projectlayer.SettingsFrame(self, self.p).Show()

    def exclude(self, event):
        """Start part excluder tool"""
        if not self.fgcode:
            wx.CallAfter(self.statusbar.SetStatusText, _("No file loaded. Please use load first."))
            return
        if not self.excluder:
            from .excluder import Excluder
            self.excluder = Excluder()
        self.excluder.pop_window(self.fgcode, bgcolor = self.bgcolor,
                                 build_dimensions = self.build_dimensions_list)

    def show_spool_manager(self, event):
        """Show Spool Manager Window"""
        spoolmanager_gui.SpoolManagerMainWindow(self, self.spool_manager).Show()

    def about(self, event):
        """Show about dialog"""

        info = wx.adv.AboutDialogInfo()

        info.SetIcon(wx.Icon(iconfile("pronterface.png"), wx.BITMAP_TYPE_PNG))
        info.SetName('Printrun')
        info.SetVersion(printcore.__version__)

        description = _("Printrun is a pure Python 3D printing"
                        " (and other types of CNC) host software.")

        description += "\n\n" + \
                       _("%.02fmm of filament have been extruded during prints") \
                       % self.settings.total_filament_used

        info.SetDescription(description)
        info.SetCopyright('(C) 2011 - 2020')
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
        info.AddDeveloper('Kliment Yanev @kliment (code)')
        info.AddDeveloper('Guillaume Seguin @iXce (code)')
        info.AddDeveloper('@DivingDuck (code)')
        info.AddDeveloper('@volconst (code)')
        info.AddDeveloper('Rock Storm @rockstorm101 (code, packaging)')
        info.AddDeveloper('Miro Hrončok @hroncok (code, packaging)')
        info.AddDeveloper('Rob Gilson @D1plo1d (code)')
        info.AddDeveloper('Gary Hodgson @garyhodgson (code)')
        info.AddDeveloper('Duane Johnson (code,graphics)')
        info.AddDeveloper('Alessandro Ranellucci @alranel (code)')
        info.AddDeveloper('Travis Howse @tjhowse (code)')
        info.AddDeveloper('edef (code)')
        info.AddDeveloper('Steven Devijver (code)')
        info.AddDeveloper('Christopher Keller (code)')
        info.AddDeveloper('Igor Yeremin (code)')
        info.AddDeveloper('Jeremy Hammett @jezmy (code)')
        info.AddDeveloper('Spencer Bliven (code)')
        info.AddDeveloper('Václav \'ax\' Hůla  @AxTheB (code)')
        info.AddDeveloper('Félix Sipma (code)')
        info.AddDeveloper('Maja M. @SparkyCola (code)')
        info.AddDeveloper('Francesco Santini @fsantini (code)')
        info.AddDeveloper('Cristopher Olah @colah (code)')
        
        info.AddDeveloper('Jeremy Kajikawa (code)')
        info.AddDeveloper('Markus Hitter (code)')
        info.AddDeveloper('SkateBoss (code)')
        info.AddDeveloper('Kaz Walker (code)')
        info.AddDeveloper('Brendan Erwin (documentation)')
        info.AddDeveloper('Elias (code)')
        info.AddDeveloper('Jordan Miller (code)')
        info.AddDeveloper('Mikko Sivulainen (code)')
        info.AddDeveloper('Clarence Risher (code)')
        info.AddDeveloper('Guillaume Revaillot (code)')
        info.AddDeveloper('John Tapsell (code)')
        info.AddDeveloper('Youness Alaoui (code)')
        info.AddDeveloper('@eldir (code)')
        info.AddDeveloper('@hg42 (code)')
        info.AddDeveloper('@jglauche (code, documentation)')
        info.AddDeveloper('Ahmet Cem TURAN @ahmetcemturan (icons, code)')
        info.AddDeveloper('Andrew Dalgleish (code)')
        info.AddDeveloper('Benny (documentation)')
        info.AddDeveloper('Chillance (code)')
        info.AddDeveloper('Ilya Novoselov (code)')
        info.AddDeveloper('Joeri Hendriks (code)')
        info.AddDeveloper('Kevin Cole (code)')
        info.AddDeveloper('pinaise (code)')
        info.AddDeveloper('Dratone (code)')
        info.AddDeveloper('ERoth3 (code)')
        info.AddDeveloper('Erik Zalm (code)')
        info.AddDeveloper('Felipe Corrêa da Silva Sanches (code)')
        info.AddDeveloper('Geordie Bilkey (code)')
        info.AddDeveloper('Ken Aaker (code)')
        info.AddDeveloper('Lawrence (documentation)')
        info.AddDeveloper('Loxgen (code)')
        info.AddDeveloper('Matthias Urlichs (code)')
        info.AddDeveloper('N Oliver (code)')
        info.AddDeveloper('@nexus511 (code)')
        info.AddDeveloper('Sergey Shepelev (code)')
        info.AddDeveloper('Simon Maillard (code)')
        info.AddDeveloper('Vanessa Dannenberg (code)')
        info.AddDeveloper('@beardface (code)')
        info.AddDeveloper('@hurzl (code)')
        info.AddDeveloper('Justin Hawkins @beardface (code)')
        info.AddDeveloper('siorai (documentation)')
        info.AddDeveloper('tobbelobb (code)')
        info.AddDeveloper('5ilver (packaging)')
        info.AddDeveloper('Alexander Hiam (code)')
        info.AddDeveloper('Alexander Zangerl (code)')
        info.AddDeveloper('Cameron Currie (code)')
        info.AddDeveloper('Chris DeLuca (documentation)')
        info.AddDeveloper('Colin Gilgenbach (code)')
        info.AddDeveloper('DanLipsitt (code)')
        info.AddDeveloper('Daniel Holth (code)')
        info.AddDeveloper('Denis B (code)')
        info.AddDeveloper('Erik Jonsson (code)')
        info.AddDeveloper('Felipe Acebes (code)')
        info.AddDeveloper('Florian Gilcher (code)')
        info.AddDeveloper('Henrik Brix Andersen (code)')
        info.AddDeveloper('Jan Wildeboer (documentation)')
        info.AddDeveloper('Javier Rios (code)')
        info.AddDeveloper('Jay Proulx (code)')
        info.AddDeveloper('Jim Morris (code)')
        info.AddDeveloper('Kyle Evans (code)')
        info.AddDeveloper('Lenbok (code)')
        info.AddDeveloper('Lukas Erlacher (code)')
        info.AddDeveloper('Michael Andresen @blddk (code)')
        info.AddDeveloper('NeoTheFox (code)')
        info.AddDeveloper('Nicolas Dandrimont (documentation)')
        info.AddDeveloper('OhmEye (code)')
        info.AddDeveloper('OliverEngineer (code)')
        info.AddDeveloper('Paul Telfort (code)')
        info.AddDeveloper('Sebastian \'Swift Geek\' Grzywna (code)')
        info.AddDeveloper('Senthil (documentation)')
        info.AddDeveloper('Sigma-One (code)')
        info.AddDeveloper('Spacexula (documentation)')
        info.AddDeveloper('Stefan Glatzel (code)')
        info.AddDeveloper('Stefanowicz (code)')
        info.AddDeveloper('Steven (code)')
        info.AddDeveloper('Tyler Hovanec (documentation)')
        info.AddDeveloper('Xabi Xab (code)')
        info.AddDeveloper('Xoan Sampaiño (code)')
        info.AddDeveloper('Yuri D\'Elia (code)')
        info.AddDeveloper('drf5n (code)')
        info.AddDeveloper('evilB (documentation)')
        info.AddDeveloper('fieldOfView (code)')
        info.AddDeveloper('jbh (code)')
        info.AddDeveloper('kludgineer (code)')
        info.AddDeveloper('l4nce0 (code)')
        info.AddDeveloper('palob (code)')
        info.AddDeveloper('russ (code)')
        
        info.AddArtist('Ahmet Cem TURAN @ahmetcemturan (icons, code)')
        info.AddArtist('Duane Johnson (code,graphics)')
        
        info.AddTranslator('freddii (German translation)')
        info.AddTranslator('Christian Metzen @metzench (German translation)')
        info.AddTranslator('Cyril Laguilhon-Debat (French translation)')
        info.AddTranslator('@AvagSayan (Armenian translation)')
        info.AddTranslator('Jonathan Marsden (French translation)')
        info.AddTranslator('Ruben Lubbes (NL translation)')
        info.AddTranslator('aboobed (Arabic translation)')
        info.AddTranslator('Alessandro Ranellucci @alranel (Italian translation)')
        
        wx.adv.AboutBox(info)

    #  --------------------------------------------------------------
    #  Settings & command line handling (including update callbacks)
    #  --------------------------------------------------------------

    def _add_settings(self, size):
        self.settings._add(BooleanSetting("monitor", True, _("Monitor printer status"), _("Regularly monitor printer temperatures (required to have functional temperature graph or gauges)"), "Printer"), self.update_monitor)
        self.settings._add(StringSetting("simarrange_path", "", _("Simarrange command"), _("Path to the simarrange binary to use in the STL plater"), "External"))
        self.settings._add(BooleanSetting("circular_bed", False, _("Circular build platform"), _("Draw a circular (or oval) build platform instead of a rectangular one"), "Printer"), self.update_bed_viz)
        self.settings._add(SpinSetting("extruders", 0, 1, 5, _("Extruders count"), _("Number of extruders"), "Printer"))
        self.settings._add(BooleanSetting("clamp_jogging", False, _("Clamp manual moves"), _("Prevent manual moves from leaving the specified build dimensions"), "Printer"))
        self.settings._add(BooleanSetting("display_progress_on_printer", False, _("Display progress on printer"), _("Show progress on printers display (sent via M117, might not be supported by all printers)"), "Printer"))
        self.settings._add(SpinSetting("printer_progress_update_interval", 10., 0, 120, _("Printer progress update interval"), _("Interval in which pronterface sends the progress to the printer if enabled, in seconds"), "Printer"))
        self.settings._add(BooleanSetting("cutting_as_extrusion", True, _("Display cutting moves"), _("Show moves where spindle is active as printing moves"), "Printer"))
        self.settings._add(ComboSetting("uimode", _("Standard"), [_("Standard"), _("Compact"), ], _("Interface mode"), _("Standard interface is a one-page, three columns layout with controls/visualization/log\nCompact mode is a one-page, two columns layout with controls + log/visualization"), "UI"), self.reload_ui)
        #self.settings._add(ComboSetting("uimode", _("Standard"), [_("Standard"), _("Compact"), _("Tabbed"), _("Tabbed with platers")], _("Interface mode"), _("Standard interface is a one-page, three columns layout with controls/visualization/log\nCompact mode is a one-page, two columns layout with controls + log/visualization"), "UI"), self.reload_ui)
        self.settings._add(ComboSetting("controlsmode", "Standard", ("Standard", "Mini"), _("Controls mode"), _("Standard controls include all controls needed for printer setup and calibration, while Mini controls are limited to the ones needed for daily printing"), "UI"), self.reload_ui)
        self.settings._add(BooleanSetting("slic3rintegration", False, _("Enable Slic3r integration"), _("Add a menu to select Slic3r profiles directly from Pronterface"), "UI"), self.reload_ui)
        self.settings._add(BooleanSetting("slic3rupdate", False, _("Update Slic3r default presets"), _("When selecting a profile in Slic3r integration menu, also save it as the default Slic3r preset"), "UI"))
        self.settings._add(ComboSetting("mainviz", "3D", ("2D", "3D", "None"), _("Main visualization"), _("Select visualization for main window."), "Viewer"), self.reload_ui)
        self.settings._add(BooleanSetting("viz3d", False, _("Use 3D in GCode viewer window"), _("Use 3D mode instead of 2D layered mode in the visualization window"), "Viewer"), self.reload_ui)
        self.settings._add(StaticTextSetting("separator_3d_viewer", _("3D viewer options"), "", group = "Viewer"))
        self.settings._add(BooleanSetting("light3d", False, _("Use a lighter 3D visualization"), _("Use a lighter visualization with simple lines instead of extruded paths for 3D viewer"), "Viewer"), self.reload_ui)
        self.settings._add(BooleanSetting("perspective", False, _("Use a perspective view instead of orthographic"), _("A perspective view looks more realistic, but is a bit more confusing to navigate"), "Viewer"), self.reload_ui)
        self.settings._add(ComboSetting("antialias3dsamples", "0", ["0", "2", "4", "8"], _("Number of anti-aliasing samples"), _("Amount of anti-aliasing samples used in the 3D viewer"), "Viewer"), self.reload_ui)
        self.settings._add(BooleanSetting("trackcurrentlayer3d", False, _("Track current layer in main 3D view"), _("Track the currently printing layer in the main 3D visualization"), "Viewer"))
        self.settings._add(FloatSpinSetting("gcview_path_width", 0.4, 0.01, 2, _("Extrusion width for 3D viewer"), _("Width of printed path in 3D viewer"), "Viewer", increment = 0.05), self.update_gcview_params)
        self.settings._add(FloatSpinSetting("gcview_path_height", 0.3, 0.01, 2, _("Layer height for 3D viewer"), _("Height of printed path in 3D viewer"), "Viewer", increment = 0.05), self.update_gcview_params)
        self.settings._add(BooleanSetting("tempgraph", True, _("Display temperature graph"), _("Display time-lapse temperature graph"), "UI"), self.reload_ui)
        self.settings._add(BooleanSetting("tempgauges", False, _("Display temperature gauges"), _("Display graphical gauges for temperatures visualization"), "UI"), self.reload_ui)
        self.settings._add(BooleanSetting("lockbox", False, _("Display interface lock checkbox"), _("Display a checkbox that, when check, locks most of Pronterface"), "UI"), self.reload_ui)
        self.settings._add(BooleanSetting("lockonstart", False, _("Lock interface upon print start"), _("If lock checkbox is enabled, lock the interface when starting a print"), "UI"))
        self.settings._add(BooleanSetting("refreshwhenloading", True, _("Update UI during G-Code load"), _("Regularly update visualization during the load of a G-Code file"), "UI"))
        self.settings._add(HiddenSetting("last_window_width", size[0]))
        self.settings._add(HiddenSetting("last_window_height", size[1]))
        self.settings._add(HiddenSetting("last_window_maximized", False))
        self.settings._add(HiddenSetting("last_sash_position", -1))
        self.settings._add(HiddenSetting("last_bed_temperature", 0.0))
        self.settings._add(HiddenSetting("last_file_path", ""))
        self.settings._add(HiddenSetting("last_file_filter", 0))
        self.settings._add(HiddenSetting("last_temperature", 0.0))
        self.settings._add(StaticTextSetting("separator_2d_viewer", _("2D viewer options"), "", group = "Viewer"))
        self.settings._add(FloatSpinSetting("preview_extrusion_width", 0.5, 0, 10, _("Preview extrusion width"), _("Width of Extrusion in Preview"), "Viewer", increment = 0.1), self.update_gviz_params)
        self.settings._add(SpinSetting("preview_grid_step1", 10., 0, 200, _("Fine grid spacing"), _("Fine Grid Spacing"), "Viewer"), self.update_gviz_params)
        self.settings._add(SpinSetting("preview_grid_step2", 50., 0, 200, _("Coarse grid spacing"), _("Coarse Grid Spacing"), "Viewer"), self.update_gviz_params)
        self.settings._add(ColorSetting("bgcolor", self._preferred_bgcolour_hex(), _("Background color"), _("Pronterface background color"), "Colors", isRGBA=False), self.reload_ui)
        self.settings._add(ColorSetting("graph_color_background", "#FAFAC7", _("Graph background color"), _("Color of the temperature graph background"), "Colors", isRGBA=False), self.reload_ui)
        self.settings._add(ColorSetting("graph_color_text", "#172C2C", _("Graph text color"), _("Color of the temperature graph text"), "Colors", isRGBA=False), self.reload_ui)
        self.settings._add(ColorSetting("graph_color_grid", "#5A5A5A", _("Graph grid color"), _("Color of the temperature graph grid"), "Colors", isRGBA=False), self.reload_ui)
        self.settings._add(ColorSetting("graph_color_fan", "#00000080", _("Graph fan line color"), _("Color of the temperature graph fan speed line"), "Colors"), self.reload_ui)
        self.settings._add(ColorSetting("graph_color_bedtemp", "#FF000080", _("Graph bed line color"), _("Color of the temperature graph bed temperature line"), "Colors"), self.reload_ui)
        self.settings._add(ColorSetting("graph_color_bedtarget", "#FF780080", _("Graph bed target line color"), _("Color of the temperature graph bed temperature target line"), "Colors"), self.reload_ui)
        self.settings._add(ColorSetting("graph_color_ex0temp", "#009BFF80", _("Graph ex0 line color"), _("Color of the temperature graph extruder 0 temperature line"), "Colors"), self.reload_ui)
        self.settings._add(ColorSetting("graph_color_ex0target", "#0005FF80", _("Graph ex0 target line color"), _("Color of the temperature graph extruder 0 target temperature line"), "Colors"), self.reload_ui)
        self.settings._add(ColorSetting("graph_color_ex1temp", "#37370080", _("Graph ex1 line color color"), _("Color of the temperature graph extruder 1 temperature line"), "Colors"), self.reload_ui)
        self.settings._add(ColorSetting("graph_color_ex1target", "#37370080", _("Graph ex1 target line color"), _("Color of the temperature graph extruder 1 temperature target line"), "Colors"), self.reload_ui)
        self.settings._add(ColorSetting("gcview_color_background", "#FAFAC7FF", _("3D view background color"), _("Color of the 3D view background"), "Colors"), self.update_gcview_colors)
        self.settings._add(ColorSetting("gcview_color_travel", "#99999999", _("3D view travel moves color"), _("Color of travel moves in 3D view"), "Colors"), self.update_gcview_colors)
        self.settings._add(ColorSetting("gcview_color_tool0", "#FF000099", _("3D view print moves color"), _("Color of print moves with tool 0 in 3D view"), "Colors"), self.update_gcview_colors)
        self.settings._add(ColorSetting("gcview_color_tool1", "#AC0DFF99", _("3D view tool 1 moves color"), _("Color of print moves with tool 1 in 3D view"), "Colors"), self.update_gcview_colors)
        self.settings._add(ColorSetting("gcview_color_tool2", "#FFCE0099", _("3D view tool 2 moves color"), _("Color of print moves with tool 2 in 3D view"), "Colors"), self.update_gcview_colors)
        self.settings._add(ColorSetting("gcview_color_tool3", "#FF009F99", _("3D view tool 3 moves color"), _("Color of print moves with tool 3 in 3D view"), "Colors"), self.update_gcview_colors)
        self.settings._add(ColorSetting("gcview_color_tool4", "#00FF8F99", _("3D view tool 4 moves color"), _("Color of print moves with tool 4 in 3D view"), "Colors"), self.update_gcview_colors)
        self.settings._add(ColorSetting("gcview_color_printed", "#33BF0099", _("3D view printed moves color"), _("Color of printed moves in 3D view"), "Colors"), self.update_gcview_colors)
        self.settings._add(ColorSetting("gcview_color_current", "#00E5FFCC", _("3D view current layer moves color"), _("Color of moves in current layer in 3D view"), "Colors"), self.update_gcview_colors)
        self.settings._add(ColorSetting("gcview_color_current_printed", "#196600CC", _("3D view printed current layer moves color"), _("Color of already printed moves from current layer in 3D view"), "Colors"), self.update_gcview_colors)
        self.settings._add(StaticTextSetting("note1", _("Note:"), _("Changing some of these settings might require a restart to get effect"), group = "UI"))
        recentfilessetting = StringSetting("recentfiles", "[]")
        recentfilessetting.hidden = True
        self.settings._add(recentfilessetting, self.update_recent_files)

    def _preferred_bgcolour_hex(self):
        id = wx.SYS_COLOUR_WINDOW \
            if platform.system() == 'Windows' \
            else wx.SYS_COLOUR_BACKGROUND
        sys_bgcolour = wx.SystemSettings.GetColour(id)
        return sys_bgcolour.GetAsString(flags=wx.C2S_HTML_SYNTAX)

    def add_cmdline_arguments(self, parser):
        pronsole.pronsole.add_cmdline_arguments(self, parser)
        parser.add_argument('-a', '--autoconnect', help = _("automatically try to connect to printer on startup"), action = "store_true")

    def process_cmdline_arguments(self, args):
        pronsole.pronsole.process_cmdline_arguments(self, args)
        self.autoconnect = args.autoconnect

    def update_recent_files(self, param, value):
        if self.filehistory is None:
            return
        recent_files = []
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
        if not hasattr(self, "gviz"):
            # GUI hasn't been loaded yet, ignore this setting
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
                self.logError(traceback.format_exc())
        if hasattr(self.gviz, trueparam):
            self.apply_gviz_params(self.gviz, trueparam, value)
        if hasattr(self.gwindow, "p") and hasattr(self.gwindow.p, trueparam):
            self.apply_gviz_params(self.gwindow.p, trueparam, value)

    def apply_gviz_params(self, widget, param, value):
        setattr(widget, param, value)
        widget.dirty = 1
        wx.CallAfter(widget.Refresh)

    def update_gcview_colors(self, param, value):
        if not self.window_ready:
            return
        color = hexcolor_to_float(value, 4)
        # This is sort of a hack: we copy the color values into the preexisting
        # color tuple so that we don't need to update the tuple used by gcview
        target_color = getattr(self, param)
        for i, v in enumerate(color):
            target_color[i] = v
        wx.CallAfter(self.Refresh)

    def update_build_dimensions(self, param, value):
        pronsole.pronsole.update_build_dimensions(self, param, value)
        self.update_bed_viz()

    def update_bed_viz(self, *args):
        """Update bed visualization when size/type changed"""
        if hasattr(self, "gviz") and hasattr(self.gviz, "recreate_platform"):
            self.gviz.recreate_platform(self.build_dimensions_list, self.settings.circular_bed,
                grid = (self.settings.preview_grid_step1, self.settings.preview_grid_step2))
        if hasattr(self, "gwindow") and hasattr(self.gwindow, "recreate_platform"):
            self.gwindow.recreate_platform(self.build_dimensions_list, self.settings.circular_bed,
                grid = (self.settings.preview_grid_step1, self.settings.preview_grid_step2))

    def update_gcview_params(self, *args):
        need_reload = False
        if hasattr(self, "gviz") and hasattr(self.gviz, "set_gcview_params"):
            need_reload |= self.gviz.set_gcview_params(self.settings.gcview_path_width, self.settings.gcview_path_height)
        if hasattr(self, "gwindow") and hasattr(self.gwindow, "set_gcview_params"):
            need_reload |= self.gwindow.set_gcview_params(self.settings.gcview_path_width, self.settings.gcview_path_height)
        if need_reload:
            self.start_viz_thread()

    def update_monitor(self, *args):
        if hasattr(self, "graph") and self.display_graph:
            if self.settings.monitor:
                wx.CallAfter(self.graph.StartPlotting, 1000)
            else:
                wx.CallAfter(self.graph.StopPlotting)

    #  --------------------------------------------------------------
    #  Statusbar handling
    #  --------------------------------------------------------------

    def statuschecker_inner(self):
        status_string = ""
        if self.sdprinting or self.uploading or self.p.printing:
            secondsremain, secondsestimate, progress = self.get_eta()
            if self.sdprinting or self.uploading:
                if self.uploading:
                    status_string += _("SD upload: %04.2f%% |") % (100 * progress,)
                    status_string += _(" Line# %d of %d lines |") % (self.p.queueindex, len(self.p.mainqueue))
                else:
                    status_string += _("SD printing: %04.2f%% |") % (self.percentdone,)
            elif self.p.printing:
                status_string += _("Printing: %04.2f%% |") % (100 * float(self.p.queueindex) / len(self.p.mainqueue),)
                status_string += _(" Line# %d of %d lines |") % (self.p.queueindex, len(self.p.mainqueue))
            if progress > 0:
                status_string += _(" Est: %s of %s remaining | ") % (format_duration(secondsremain),
                                                                     format_duration(secondsestimate))
                status_string += _(" Z: %.3f mm") % self.curlayer
                if self.settings.display_progress_on_printer and time.time() - self.printer_progress_time >= self.settings.printer_progress_update_interval:
                    self.printer_progress_time = time.time()
                    printer_progress_string = "M117 " + str(round(100 * float(self.p.queueindex) / len(self.p.mainqueue), 2)) + "% Est " + format_duration(secondsremain)
                    #":" seems to be some kind of separator for G-CODE"
                    self.p.send_now(printer_progress_string.replace(":", "."))
                    if len(printer_progress_string) > 25:
                        logging.info("Warning: The print progress message might be too long to be displayed properly")
                    #13 chars for up to 99h est.
        elif self.loading_gcode:
            status_string = self.loading_gcode_message
        wx.CallAfter(self.statusbar.SetStatusText, status_string)
        wx.CallAfter(self.gviz.Refresh)
        # Call pronsole's statuschecker inner loop function to handle
        # temperature monitoring and status loop sleep
        pronsole.pronsole.statuschecker_inner(self, self.settings.monitor)
        try:
            while not self.sentglines.empty():
                gc = self.sentglines.get_nowait()
                wx.CallAfter(self.gviz.addgcodehighlight, gc)
                self.sentglines.task_done()
        except queue.Empty:
            pass

    def statuschecker(self):
        pronsole.pronsole.statuschecker(self)
        wx.CallAfter(self.statusbar.SetStatusText, _("Not connected to printer."))

    #  --------------------------------------------------------------
    #  Interface lock handling
    #  --------------------------------------------------------------

    def lock(self, event = None, force = None):
        if force is not None:
            self.locker.SetValue(force)
        if self.locker.GetValue():
            self.log(_("Locking interface."))
            for panel in self.panels:
                panel.Disable()
        else:
            self.log(_("Unlocking interface."))
            for panel in self.panels:
                panel.Enable()

    #  --------------------------------------------------------------
    #  Printer connection handling
    #  --------------------------------------------------------------

    def connectbtn_cb(self, event):
        # Implement toggle behavior with a single Bind
        # and switched variable, so we have reference to
        # the actual callback to use in on_key
        self.connectbtn_cb_var()

    def connect(self, event = None):
        self.log(_("Connecting..."))
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
            self.logError(_("Could not parse baud rate: ")
                          + "\n" + traceback.format_exc())
        if self.paused:
            self.p.paused = 0
            self.p.printing = 0
            wx.CallAfter(self.pausebtn.SetLabel, _("&Pause"))
            wx.CallAfter(self.printbtn.SetLabel, _("&Print"))
            wx.CallAfter(self.toolbarsizer.Layout)
            self.paused = 0
            if self.sdprinting:
                self.p.send_now("M26 S0")
        if not self.connect_to_printer(port, baud, self.settings.dtr):
            return
        if port != self.settings.port:
            self.set("port", port)
        if baud != self.settings.baudrate:
            self.set("baudrate", str(baud))
        if self.predisconnect_mainqueue:
            self.recoverbtn.Enable()

    def store_predisconnect_state(self):
        self.predisconnect_mainqueue = self.p.mainqueue
        self.predisconnect_queueindex = self.p.queueindex
        self.predisconnect_layer = self.curlayer

    def disconnect(self, event = None):
        self.log(_("Disconnected."))
        if self.p.printing or self.p.paused or self.paused:
            self.store_predisconnect_state()
        self.p.disconnect()
        self.statuscheck = False
        if self.status_thread:
            self.status_thread.join()
            self.status_thread = None

        def toggle():
            self.connectbtn.SetLabel(_("&Connect"))
            self.connectbtn.SetToolTip(wx.ToolTip(_("Connect to the printer")))
            self.connectbtn_cb_var = self.connect
            self.gui_set_disconnected()
        wx.CallAfter(toggle)

        if self.paused:
            self.p.paused = 0
            self.p.printing = 0
            wx.CallAfter(self.pausebtn.SetLabel, _("&Pause"))
            wx.CallAfter(self.printbtn.SetLabel, _("&Print"))
            self.paused = 0
            if self.sdprinting:
                self.p.send_now("M26 S0")

        # Relayout the toolbar to handle new buttons size
        wx.CallAfter(self.toolbarsizer.Layout)

    def reset(self, event):
        self.log(_("Reset."))
        dlg = wx.MessageDialog(self, _("Are you sure you want to reset the printer?"), _("Reset?"), wx.YES | wx.NO)
        if dlg.ShowModal() == wx.ID_YES:
            self.p.reset()
            self.sethotendgui(0)
            self.setbedgui(0)
            self.p.printing = 0
            wx.CallAfter(self.printbtn.SetLabel, _("&Print"))
            if self.paused:
                self.p.paused = 0
                wx.CallAfter(self.pausebtn.SetLabel, _("&Pause"))
                self.paused = 0
            wx.CallAfter(self.toolbarsizer.Layout)
        dlg.Destroy()

    #  --------------------------------------------------------------
    #  Print/upload handling
    #  --------------------------------------------------------------

    def on_startprint(self):
        wx.CallAfter(self.pausebtn.SetLabel, _("&Pause"))
        wx.CallAfter(self.pausebtn.Enable)
        wx.CallAfter(self.printbtn.SetLabel, _("Restart"))
        wx.CallAfter(self.toolbarsizer.Layout)

    def printfile(self, event=None):
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
        self.sdprinting = False
        self.on_startprint()
        self.p.startprint(self.fgcode)

    def sdprintfile(self, event):
        self.extra_print_time = 0
        self.on_startprint()
        threading.Thread(target = self.getfiles).start()

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

    def uploadtrigger(self, l):
        if "Writing to file" in l:
            self.uploading = True
            self.p.startprint(self.fgcode)
            self.p.endcb = self.endupload
            self.recvlisteners.remove(self.uploadtrigger)
        elif "open failed, File" in l:
            self.recvlisteners.remove(self.uploadtrigger)

    def endupload(self):
        self.p.send_now("M29 ")
        wx.CallAfter(self.statusbar.SetStatusText, _("File upload complete"))
        time.sleep(0.5)
        self.p.clear = True
        self.uploading = False

    def pause(self, event = None):
        if not self.paused:
            self.log(_("Print paused at: %s") % format_time(time.time()))
            if self.settings.display_progress_on_printer:
                printer_progress_string = "M117 PausedInPronterface"
                self.p.send_now(printer_progress_string)
            if self.sdprinting:
                self.p.send_now("M25")
            else:
                if not self.p.printing:
                    return
                self.p.pause()
                self.p.runSmallScript(self.pauseScript)
            self.paused = True
            # self.p.runSmallScript(self.pauseScript)
            self.extra_print_time += int(time.time() - self.starttime)
            wx.CallAfter(self.pausebtn.SetLabel, _("Resume"))
            wx.CallAfter(self.toolbarsizer.Layout)
        else:
            self.log(_("Resuming."))
            if self.settings.display_progress_on_printer:
                printer_progress_string = "M117 Resuming"
                self.p.send_now(printer_progress_string)
            self.paused = False
            if self.sdprinting:
                self.p.send_now("M24")
            else:
                self.p.resume()
            wx.CallAfter(self.pausebtn.SetLabel, _("&Pause"))
            wx.CallAfter(self.toolbarsizer.Layout)

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

    #  --------------------------------------------------------------
    #  File loading handling
    #  --------------------------------------------------------------

    def filesloaded(self):
        dlg = wx.SingleChoiceDialog(self, _("Select the file to print"), _("Pick SD file"), self.sdfiles)
        if dlg.ShowModal() == wx.ID_OK:
            target = dlg.GetStringSelection()
            if len(target):
                self.recvlisteners.append(self.waitforsdresponse)
                self.p.send_now("M23 " + target.lower())
        dlg.Destroy()

    def getfiles(self):
        if not self.p.online:
            self.sdfiles = []
            return
        self.sdlisting = 0
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

    def slice_func(self):
        try:
            output_filename = self.model_to_gcode_filename(self.filename)
            pararray = prepare_command(self.settings.slicecommandpath+self.settings.slicecommand,
                                       {"$s": self.filename, "$o": output_filename})
            if self.settings.slic3rintegration:
                for cat, config in self.slic3r_configs.items():
                    if config:
                        fpath = os.path.join(self.slic3r_configpath, cat, config)
                        pararray += ["--load", fpath]
            self.log(_("Running ") + " ".join(pararray))
            self.slicep = subprocess.Popen(pararray, stdin=subprocess.DEVNULL, stderr = subprocess.STDOUT, stdout = subprocess.PIPE, universal_newlines = True)
            while True:
                o = self.slicep.stdout.read(1)
                if o == '' and self.slicep.poll() is not None: break
                sys.stdout.write(o)
            self.slicep.wait()
            self.stopsf = 1
        except:
            self.logError(_("Failed to execute slicing software: ")
                          + "\n" + traceback.format_exc())
            self.stopsf = 1

    def slice_monitor(self):
        while not self.stopsf:
            try:
                wx.CallAfter(self.statusbar.SetStatusText, _("Slicing..."))  # +self.cout.getvalue().split("\n")[-1])
            except:
                pass
            time.sleep(0.1)
        fn = self.filename
        try:
            self.load_gcode_async(self.model_to_gcode_filename(self.filename))
        except:
            self.filename = fn
        self.slicing = False
        self.slicep = None
        self.loadbtn.SetLabel, _("Load file")

    def slice(self, filename):
        wx.CallAfter(self.loadbtn.SetLabel, _("Cancel"))
        wx.CallAfter(self.toolbarsizer.Layout)
        self.log(_("Slicing ") + filename)
        self.cout = StringIO.StringIO()
        self.filename = filename
        self.stopsf = 0
        self.slicing = True
        threading.Thread(target = self.slice_func).start()
        threading.Thread(target = self.slice_monitor).start()

    def cmdline_filename_callback(self, filename):
        # Do nothing when processing a filename from command line, as we'll
        # handle it when everything has been prepared
        self.filename = filename

    def do_load(self, l):
        if hasattr(self, 'slicing'):
            self.loadfile(None, l)
        else:
            self._do_load(l)

    def load_recent_file(self, event):
        fileid = event.GetId() - wx.ID_FILE1
        path = self.filehistory.GetHistoryFile(fileid)
        self.loadfile(None, filename = path)

    def loadfile(self, event, filename = None):
        if self.slicing and self.slicep is not None:
            self.slicep.terminate()
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
            dlg.SetWildcard(_("OBJ, STL, and GCODE files (*.gcode;*.gco;*.g;*.stl;*.STL;*.obj;*.OBJ)|*.gcode;*.gco;*.g;*.stl;*.STL;*.obj;*.OBJ|GCODE files (*.gcode;*.gco;*.g)|*.gcode;*.gco;*.g|OBJ, STL files (*.stl;*.STL;*.obj;*.OBJ)|*.stl;*.STL;*.obj;*.OBJ|All Files (*.*)|*.*"))
            try:
              dlg.SetFilterIndex(self.settings.last_file_filter)
            except:
              pass
        if filename or dlg.ShowModal() == wx.ID_OK:
            if filename:
                name = filename
            else:
                name = dlg.GetPath()
                self.set("last_file_filter", dlg.GetFilterIndex())
                dlg.Destroy()
            if not os.path.exists(name):
                self.statusbar.SetStatusText(_("File not found!"))
                return
            path = os.path.split(name)[0]
            if path != self.settings.last_file_path:
                self.set("last_file_path", path)
            try:
                abspath = os.path.abspath(name)
                recent_files = []
                try:
                    recent_files = json.loads(self.settings.recentfiles)
                except:
                    self.logError(_("Failed to load recent files list:") +
                                  "\n" + traceback.format_exc())
                if abspath in recent_files:
                    recent_files.remove(abspath)
                recent_files.insert(0, abspath)
                if len(recent_files) > 5:
                    recent_files = recent_files[:5]
                self.set("recentfiles", json.dumps(recent_files))
            except:
                self.logError(_("Could not update recent files list:") +
                              "\n" + traceback.format_exc())
            if name.lower().endswith(".stl") or name.lower().endswith(".obj"):
                self.slice(name)
            else:
                self.load_gcode_async(name)
        else:
            dlg.Destroy()

    def load_gcode_async(self, filename):
        self.filename = filename
        gcode = self.pre_gcode_load()
        self.log(_("Loading file: %s") % filename)
        threading.Thread(target = self.load_gcode_async_thread, args = (gcode,)).start()

    def load_gcode_async_thread(self, gcode):
        try:
            self.load_gcode(self.filename,
                            layer_callback = self.layer_ready_cb,
                            gcode = gcode)
        except PronterfaceQuitException:
            return
        except Exception as e:
            self.log(str(e))
            wx.CallAfter(self.post_gcode_load,False,True)
            return
        wx.CallAfter(self.post_gcode_load)

    def layer_ready_cb(self, gcode, layer):
        global pronterface_quitting
        if pronterface_quitting:
            raise PronterfaceQuitException
        if not self.settings.refreshwhenloading:
            return
        self.viz_last_layer = layer
        if time.time() - self.viz_last_yield > 1.0:
            time.sleep(0.2)
            self.loading_gcode_message = _("Loading %s: %d layers loaded (%d lines)") % (self.filename, layer + 1, len(gcode))
            self.viz_last_yield = time.time()
            wx.CallAfter(self.statusbar.SetStatusText, self.loading_gcode_message)

    def start_viz_thread(self, gcode = None):
        threading.Thread(target = self.loadviz, args = (gcode,)).start()

    def pre_gcode_load(self):
        self.loading_gcode = True
        self.loading_gcode_message = _("Loading %s...") % self.filename
        if self.settings.mainviz == "None":
            gcode = gcoder.LightGCode(deferred = True)
        else:
            gcode = gcoder.GCode(deferred = True, cutting_as_extrusion = self.settings.cutting_as_extrusion)
        self.viz_last_yield = 0
        self.viz_last_layer = -1
        self.start_viz_thread(gcode)
        return gcode

    def post_gcode_load(self, print_stats = True, failed=False):
        # Must be called in wx.CallAfter for safety
        self.loading_gcode = False
        if not failed:
            self.SetTitle(_("Pronterface - %s") % self.filename)
            message = _("Loaded %s, %d lines") % (self.filename, len(self.fgcode),)
            self.log(message)
            self.statusbar.SetStatusText(message)
            self.savebtn.Enable(True)
        self.loadbtn.SetLabel(_("Load File"))
        self.printbtn.SetLabel(_("&Print"))
        self.pausebtn.SetLabel(_("&Pause"))
        self.pausebtn.Disable()
        self.recoverbtn.Disable()
        if not failed and self.p.online:
            self.printbtn.Enable()
        self.toolbarsizer.Layout()
        self.viz_last_layer = None
        if print_stats:
            self.output_gcode_stats()

    def calculate_remaining_filament(self, length, extruder = 0):
        """
        float calculate_remaining_filament( float length, int extruder )

        Calculate the remaining length of filament for the given extruder if
        the given length were to be extruded.
        """

        remainder = self.spool_manager.getRemainingFilament(extruder) - length
        minimum_warning_length = 1000.0
        if remainder < minimum_warning_length:
            self.log(_("\nWARNING: Currently loaded spool for extruder " +
            "%d will likely run out of filament during the print.\n" %
            extruder))
        return remainder

    def output_gcode_stats(self):
        gcode = self.fgcode
        self.spool_manager.refresh()

        self.log(_("%s of filament used in this print") % format_length(gcode.filament_length))

        if len(gcode.filament_length_multi) > 1:
            for i in enumerate(gcode.filament_length_multi):
                if self.spool_manager.getSpoolName(i[0]) == None:
                    logging.info("- Extruder %d: %0.02fmm" % (i[0], i[1]))
                else:
                    logging.info(("- Extruder %d: %0.02fmm" % (i[0], i[1]) +
                        " from spool '%s' (%.2fmm will remain)" %
                        (self.spool_manager.getSpoolName(i[0]),
                        self.calculate_remaining_filament(i[1], i[0]))))
        elif self.spool_manager.getSpoolName(0) != None:
                self.log(
                    _("Using spool '%s' (%s of filament will remain)") %
                    (self.spool_manager.getSpoolName(0),
                    format_length(self.calculate_remaining_filament(
                        gcode.filament_length, 0))))

        self.log(_("The print goes:"))
        self.log(_("- from %.2f mm to %.2f mm in X and is %.2f mm wide") % (gcode.xmin, gcode.xmax, gcode.width))
        self.log(_("- from %.2f mm to %.2f mm in Y and is %.2f mm deep") % (gcode.ymin, gcode.ymax, gcode.depth))
        self.log(_("- from %.2f mm to %.2f mm in Z and is %.2f mm high") % (gcode.zmin, gcode.zmax, gcode.height))
        self.log(_("Estimated duration: %d layers, %s") % gcode.estimate_duration())

    def loadviz(self, gcode = None):
        try:
            self.gviz.clear()
            self.gwindow.p.clear()
            if gcode is not None:
                generator = self.gviz.addfile_perlayer(gcode, True)
                next_layer = 0
                # Progressive loading of visualization
                # We load layers up to the last one which has been processed in GCoder
                # (self.viz_last_layer)
                # Once the GCode has been entirely loaded, this variable becomes None,
                # indicating that we can do the last generator call to finish the
                # loading of the visualization, which will itself return None.
                # During preloading we verify that the layer we added is the one we
                # expected through the assert call.
                while True:
                    global pronterface_quitting
                    if pronterface_quitting:
                        return
                    max_layer = self.viz_last_layer
                    if max_layer is None:
                        break
                    start_layer = next_layer
                    while next_layer <= max_layer:
                        assert next(generator) == next_layer
                        next_layer += 1
                    if next_layer != start_layer:
                        wx.CallAfter(self.gviz.Refresh)
                    time.sleep(0.1)
                generator_output = next(generator)
                while generator_output is not None:
                    assert generator_output == next_layer
                    next_layer += 1
                    generator_output = next(generator)
            else:
                # If GCode is not being loaded asynchronously, it is already
                # loaded, so let's make visualization sequentially
                gcode = self.fgcode
                self.gviz.addfile(gcode)
            wx.CallAfter(self.gviz.Refresh)
            # Load external window sequentially now that everything is ready.
            # We can't really do any better as the 3D viewer might clone the
            # finalized model from the main visualization
            self.gwindow.p.addfile(gcode)
        except:
            logging.error(traceback.format_exc())
            wx.CallAfter(self.gviz.Refresh)

    #  --------------------------------------------------------------
    #  File saving handling
    #  --------------------------------------------------------------

    def savefile(self, event):
        basedir = self.settings.last_file_path
        if not os.path.exists(basedir):
            basedir = "."
            try:
                basedir = os.path.split(self.filename)[0]
            except:
                pass
        dlg = wx.FileDialog(self, _("Save as"), basedir, style = wx.FD_SAVE)
        dlg.SetWildcard(_("GCODE files (*.gcode;*.gco;*.g)|*.gcode;*.gco;*.g|All Files (*.*)|*.*"))
        if dlg.ShowModal() == wx.ID_OK:
            name = dlg.GetPath()
            open(name, "w").write("\n".join((line.raw for line in self.fgcode)))
            self.log(_("G-Code successfully saved to %s") % name)
        dlg.Destroy()

    #  --------------------------------------------------------------
    #  Printcore callbacks
    #  --------------------------------------------------------------

    def process_host_command(self, command):
        """Override host command handling"""
        command = command.lstrip()
        if command.startswith(";@pause"):
            self.pause(None)
        else:
            pronsole.pronsole.process_host_command(self, command)

    def startcb(self, resuming = False):
        """Callback on print start"""
        pronsole.pronsole.startcb(self, resuming)
        if self.settings.lockbox and self.settings.lockonstart:
            wx.CallAfter(self.lock, force = True)

    def endcb(self):
        """Callback on print end/pause"""
        pronsole.pronsole.endcb(self)
        if self.p.queueindex == 0:
            self.p.runSmallScript(self.endScript)
            if self.settings.display_progress_on_printer:
                printer_progress_string = "M117 Finished Print"
                self.p.send_now(printer_progress_string)
            wx.CallAfter(self.pausebtn.Disable)
            wx.CallAfter(self.printbtn.SetLabel, _("&Print"))
            wx.CallAfter(self.toolbarsizer.Layout)

    def online(self):
        """Callback when printer goes online"""
        self.log(_("Printer is now online."))
        wx.CallAfter(self.online_gui)

    def online_gui(self):
        """Callback when printer goes online (graphical bits)"""
        self.connectbtn.SetLabel(_("Dis&connect"))
        self.connectbtn.SetToolTip(wx.ToolTip("Disconnect from the printer"))
        self.connectbtn_cb_var = self.disconnect

        if hasattr(self, "extrudersel"):
            self.do_tool(self.extrudersel.GetValue())

        self.gui_set_connected()

        if self.filename:
            self.printbtn.Enable()

        wx.CallAfter(self.toolbarsizer.Layout)

    def sentcb(self, line, gline):
        """Callback when a printer gcode has been sent"""
        if not gline:
            pass
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
        elif gline.command in ["M106"]:
            gline_s=gcoder.S(gline)
            fanpow=255
            if gline_s is not None:
                fanpow=gline_s
            if self.display_graph: wx.CallAfter(self.graph.SetFanPower, fanpow)
        elif gline.command in ["M107"]:
            if self.display_graph: wx.CallAfter(self.graph.SetFanPower, 0)
        elif gline.command.startswith("T"):
            tool = gline.command[1:]
            if hasattr(self, "extrudersel"): wx.CallAfter(self.extrudersel.SetValue, tool)
        if gline.is_move:
            self.sentglines.put_nowait(gline)

    def is_excluded_move(self, gline):
        """Check whether the given moves ends at a position specified as
        excluded in the part excluder"""
        if not gline.is_move or not self.excluder or not self.excluder.rectangles:
            return False
        for (x0, y0, x1, y1) in self.excluder.rectangles:
            if x0 <= gline.current_x <= x1 and y0 <= gline.current_y <= y1:
                return True
        return False

    def preprintsendcb(self, gline, next_gline):
        """Callback when a printer gcode is about to be sent. We use it to
        exclude moves defined by the part excluder tool"""
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
        """Callback when a print gcode has been sent"""
        if gline.is_move:
            if hasattr(self.gwindow, "set_current_gline"):
                wx.CallAfter(self.gwindow.set_current_gline, gline)
            if hasattr(self.gviz, "set_current_gline"):
                wx.CallAfter(self.gviz.set_current_gline, gline)

    def layer_change_cb(self, newlayer):
        """Callback when the printed layer changed"""
        pronsole.pronsole.layer_change_cb(self, newlayer)
        if self.settings.mainviz != "3D" or self.settings.trackcurrentlayer3d:
            wx.CallAfter(self.gviz.setlayer, newlayer)

    def update_tempdisplay(self):
        try:
            temps = parse_temperature_report(self.tempreadings)

            for name in 'T', 'T0', 'T1', 'B':
                if name not in temps:
                    continue
                current = float(temps[name][0])
                target = float(temps[name][1]) if temps[name][1] else None
                if name == 'T':
                    name = 'T0'
                if self.display_graph:
                    prefix = 'Set' + name.replace('T', 'Extruder').replace('B', 'Bed')
                    wx.CallAfter(getattr(self.graph, prefix + 'Temperature'), current)
                    if target is not None:
                        wx.CallAfter(getattr(self.graph, prefix + 'TargetTemperature'), target)
                if self.display_gauges:
                    if name[0] == 'T':
                        if name[1] == str(self.current_tool):
                            def update(c, t):
                                self.hottgauge.SetValue(c)
                                self.hottgauge.SetTarget(t or 0)
                                self.hottgauge.title = _('Heater%s:') % (str(self.current_tool) if self.settings.extruders > 1 else '')
                            wx.CallAfter(update, current, target)
                    else:
                        wx.CallAfter(self.bedtgauge.SetValue, current)
                        if target is not None:
                            wx.CallAfter(self.bedtgauge.SetTarget, target)
        except:
            self.logError(traceback.format_exc())

    def update_pos(self):
        bits = gcoder.m114_exp.findall(self.posreport)
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

    def recvcb_actions(self, l):
        if l.startswith("!!"):
            if not self.paused:
                wx.CallAfter(self.pause)
            msg = l.split(" ", 1)
            if len(msg) > 1 and not self.p.loud:
                self.log(msg[1] + "\n")
            return True
        elif l.startswith("//"):
            command = l.split(" ", 1)
            if len(command) > 1:
                command = command[1]
                command = command.split(":")
                if len(command) == 2 and command[0] == "action":
                    command = command[1]
                    self.log(_("Received command %s") % command)
                    if command == "pause":
                        if not self.paused:
                            wx.CallAfter(self.pause)
                        return True
                    elif command == "resume":
                        if self.paused:
                            wx.CallAfter(self.pause)
                        return True
                    elif command == "disconnect":
                        wx.CallAfter(self.disconnect)
                        return True
        return False

    def recvcb(self, l):
        l = l.rstrip()
        if not self.recvcb_actions(l):
            report_type = self.recvcb_report(l)
            isreport = report_type != REPORT_NONE
            if report_type & REPORT_POS:
                self.update_pos()
            elif report_type & REPORT_TEMP:
                wx.CallAfter(self.tempdisp.SetLabel, self.tempreadings.strip().replace("ok ", ""))
                self.update_tempdisplay()
            if not self.lineignorepattern.match(l) and not self.p.loud and (l not in ["ok", "wait"] and (not isreport or report_type & REPORT_MANUAL)):
                self.log(l)
        for listener in self.recvlisteners:
            listener(l)

    def listfiles(self, line, ignored = False):
        if "Begin file list" in line:
            self.sdlisting = True
        elif "End file list" in line:
            self.sdlisting = False
            self.recvlisteners.remove(self.listfiles)
            wx.CallAfter(self.filesloaded)
        elif self.sdlisting:
            self.sdfiles.append(re.sub(" \d+$","",line.strip().lower()))

    def waitforsdresponse(self, l):
        if "file.open failed" in l:
            wx.CallAfter(self.statusbar.SetStatusText, _("Opening file failed."))
            self.recvlisteners.remove(self.waitforsdresponse)
            return
        if "File opened" in l:
            wx.CallAfter(self.statusbar.SetStatusText, l)
        if "File selected" in l:
            wx.CallAfter(self.statusbar.SetStatusText, _("Starting print"))
            self.sdprinting = True
            self.p.send_now("M24")
            self.startcb()
            return
        if "Done printing file" in l:
            wx.CallAfter(self.statusbar.SetStatusText, l)
            self.sdprinting = False
            self.recvlisteners.remove(self.waitforsdresponse)
            self.endcb()
            return
        if "SD printing byte" in l:
            # M27 handler
            try:
                resp = l.split()
                vals = resp[-1].split("/")
                self.percentdone = 100.0 * int(vals[0]) / int(vals[1])
            except:
                pass

    #  --------------------------------------------------------------
    #  Custom buttons handling
    #  --------------------------------------------------------------

    def cbuttons_reload(self):
        allcbs = getattr(self, "custombuttons_widgets", [])
        for button in allcbs:
            self.cbuttonssizer.Detach(button)
            button.Destroy()
        self.custombuttons_widgets = []
        custombuttons = self.custombuttons[:] + [None]
        for i, btndef in enumerate(custombuttons):
            if btndef is None:
                if i == len(custombuttons) - 1:
                    self.newbuttonbutton = b = wx.Button(self.centerpanel, -1, "+", size = (35, 18), style = wx.BU_EXACTFIT)
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
                    rr, gg, bb, aa = b.GetBackgroundColour().Get() #last item is alpha
                    if 0.3 * rr + 0.59 * gg + 0.11 * bb < 60:
                        b.SetForegroundColour("#ffffff")
                b.custombutton = i
                b.properties = btndef
            if btndef is not None:
                b.Bind(wx.EVT_BUTTON, self.process_button)
                b.Bind(wx.EVT_MOUSE_EVENTS, self.editbutton)
            self.custombuttons_widgets.append(b)
            if isinstance(self.cbuttonssizer, wx.GridBagSizer):
                self.cbuttonssizer.Add(b, pos = (i // 4, i % 4), flag = wx.EXPAND)
            else:
                self.cbuttonssizer.Add(b, flag = wx.EXPAND)
        self.centerpanel.Layout()
        self.centerpanel.GetContainingSizer().Layout()

    def help_button(self):
        self.log(_('Defines custom button. Usage: button <num> "title" [/c "colour"] command'))

    def do_button(self, argstr):
        def nextarg(rest):
            rest = rest.lstrip()
            if rest.startswith('"'):
                return rest[1:].split('"', 1)
            else:
                return rest.split(None, 1)
        # try:
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
            self.log(_("Custom button number should be between 0 and 63"))
            return
        while num >= len(self.custombuttons):
            self.custombuttons.append(None)
        self.custombuttons[num] = SpecialButton(title, command)
        if colour is not None:
            self.custombuttons[num].background = colour
        if not self.processing_rc:
            self.cbuttons_reload()

    def cbutton_save(self, n, bdef, new_n = None):
        if new_n is None: new_n = n
        if bdef is None or bdef == "":
            self.save_in_rc(("button %d" % n), '')
        elif bdef.background:
            colour = bdef.background
            if not isinstance(colour, str):
                if isinstance(colour, tuple) and tuple(map(type, colour)) == (int, int, int):
                    colour = (x % 256 for x in colour)
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
                if not isinstance(colour, str):
                    if isinstance(colour, tuple) and tuple(map(type, colour)) == (int, int, int):
                        colour = (x % 256 for x in colour)
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
        elif e.Dragging() and e.LeftIsDown():
            obj = e.GetEventObject()
            scrpos = obj.ClientToScreen(e.GetPosition())
            if not hasattr(self, "dragpos"):
                self.dragpos = scrpos
                e.Skip()
                return
            else:
                dx, dy = self.dragpos[0] - scrpos[0], self.dragpos[1] - scrpos[1]
                if dx * dx + dy * dy < 30 * 30:  # threshold to detect dragging for jittery mice
                    e.Skip()
                    return
            if not hasattr(self, "dragging"):
                # init dragging of the custom button
                if hasattr(obj, "custombutton") and (not hasattr(obj,"properties") or obj.properties is not None):
                    for b in self.custombuttons_widgets:
                        if not hasattr(b,"properties") or b.properties is None:
                            b.Enable()
                            b.SetLabel("")
                            b.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
                            b.SetForegroundColour("black")
                            b.SetSize(obj.GetSize())
                            if self.toolbarsizer.GetItem(b) is not None:
                                self.toolbarsizer.SetItemMinSize(b, obj.GetSize())
                                self.mainsizer.Layout()
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
                for b in self.custombuttons_widgets:
                    if b.GetScreenRect().Contains(scrpos):
                        dst = b
                        break
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
        elif hasattr(self, "dragging") and not e.LeftIsDown():
            # dragging finished
            obj = e.GetEventObject()
            scrpos = obj.ClientToScreen(e.GetPosition())
            dst = None
            src = self.dragging.sourcebutton
            drg = self.dragging
            for b in self.custombuttons_widgets:
                if b.GetScreenRect().Contains(scrpos):
                    dst = b
                    break
            if dst is not None and hasattr(dst,"custombutton"):
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

    def process_button(self, e):
        try:
            if hasattr(e.GetEventObject(), "custombutton"):
                if wx.GetKeyState(wx.WXK_CONTROL) or wx.GetKeyState(wx.WXK_ALT):
                    return self.editbutton(e)
                self.cur_button = e.GetEventObject().custombutton
            command = e.GetEventObject().properties.command
            command = self.precmd(command)
            self.onecmd(command)
            self.cur_button = None
        except:
            self.log(_("Failed to handle button"))
            self.cur_button = None
            raise

    #  --------------------------------------------------------------
    #  Macros handling
    #  --------------------------------------------------------------

    def start_macro(self, macro_name, old_macro_definition = ""):
        if not self.processing_rc:
            def cb(definition):
                if len(definition.strip()) == 0:
                    if old_macro_definition != "":
                        dialog = wx.MessageDialog(self, _("Do you want to erase the macro?"), style = wx.YES_NO | wx.YES_DEFAULT | wx.ICON_QUESTION)
                        if dialog.ShowModal() == wx.ID_YES:
                            self.delete_macro(macro_name)
                            return
                    self.log(_("Cancelled."))
                    return
                self.cur_macro_name = macro_name
                self.cur_macro_def = definition
                self.end_macro()
            MacroEditor(macro_name, old_macro_definition, cb)
        else:
            pronsole.pronsole.start_macro(self, macro_name, old_macro_definition)

    def end_macro(self):
        pronsole.pronsole.end_macro(self)
        self.update_macros_menu()

    def delete_macro(self, macro_name):
        pronsole.pronsole.delete_macro(self, macro_name)
        self.update_macros_menu()

    def new_macro(self, e = None):
        dialog = wx.Dialog(self, -1, _("Enter macro name"))
        text = wx.StaticText(dialog, -1, _("Macro name:"))
        namectrl = wx.TextCtrl(dialog, -1, style = wx.TE_PROCESS_ENTER)
        okb = wx.Button(dialog, wx.ID_OK, _("Ok"))
        dialog.Bind(wx.EVT_TEXT_ENTER,
            lambda e: dialog.EndModal(wx.ID_OK), namectrl)
        cancel_button = wx.Button(dialog, wx.ID_CANCEL, _("Cancel"))

        # Layout
        ## Group the buttons horizontally
        buttons_sizer = wx.BoxSizer(wx.HORIZONTAL)
        buttons_sizer.Add(okb, 0)
        buttons_sizer.Add(cancel_button, 0)
        ## Set a minimum size for the name control box
        min_size = namectrl.GetTextExtent('Default Long Macro Name')
        namectrl.SetMinSize(wx.Size(min_size.width, -1))
        ## Group the text and the name control box horizontally
        name_sizer = wx.BoxSizer(wx.HORIZONTAL)
        name_sizer.Add(text, 0, flag = wx.ALIGN_CENTER)
        name_sizer.AddSpacer(10)
        name_sizer.Add(namectrl, 1, wx.EXPAND)
        ## Group everything vertically
        dialog_sizer = wx.BoxSizer(wx.VERTICAL)
        dialog_sizer.Add(name_sizer, 0, border = 10,
            flag = wx.LEFT | wx.TOP | wx.RIGHT)
        dialog_sizer.Add(buttons_sizer, 0, border = 10,
            flag = wx.ALIGN_CENTER | wx.ALL)
        dialog.SetSizerAndFit(dialog_sizer)
        dialog.Centre()

        macro = ""
        if dialog.ShowModal() == wx.ID_OK:
            macro = namectrl.GetValue()
            if macro != "":
                wx.CallAfter(self.edit_macro, macro)
        dialog.Destroy()
        return macro

    def edit_macro(self, macro):
        if macro == "": return self.new_macro()
        if macro in self.macros:
            old_def = self.macros[macro]
        elif len([chr(c) for c in macro.encode("ascii", "replace") if not chr(c).isalnum() and chr(c) != "_"]):
            self.log(_("Macro name may contain only ASCII alphanumeric symbols and underscores"))
            return
        elif hasattr(self.__class__, "do_" + macro):
            self.log(_("Name '%s' is being used by built-in command") % macro)
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
                self.macros_menu.DestroyItem(item)
        except:
            pass
        for macro in self.macros.keys():
            self.Bind(wx.EVT_MENU, lambda x, m = macro: self.start_macro(m, self.macros[m]), self.macros_menu.Append(-1, macro))

    #  --------------------------------------------------------------
    #  Slic3r integration
    #  --------------------------------------------------------------

    def load_slic3r_configs(self, menus):
        """List Slic3r configurations and create menu"""
        # Hack to get correct path for Slic3r config
        orig_appname = self.app.GetAppName()
        self.app.SetAppName("Slic3r")
        configpath = wx.StandardPaths.Get().GetUserDataDir()
        self.slic3r_configpath = configpath
        configfile = os.path.join(configpath, "slic3r.ini")
        if not os.path.exists(configfile):
            self.app.SetAppName("Slic3rPE")
            configpath = wx.StandardPaths.Get().GetUserDataDir()
            self.slic3r_configpath = configpath
            configfile = os.path.join(configpath, "slic3r.ini")
        if not os.path.exists(configfile):
            self.settings.slic3rintegration=False;
            return
        self.app.SetAppName(orig_appname)
        config = self.read_slic3r_config(configfile)
        version = config.get("dummy", "version") # Slic3r version
        self.slic3r_configs = {}
        for cat in menus:
            menu = menus[cat]
            pattern = os.path.join(configpath, cat, "*.ini")
            files = sorted(glob.glob(pattern))
            try:
                preset = config.get("presets", cat)
                # Starting from Slic3r 1.3.0, preset names have no extension
                if version.split(".") >= ["1","3","0"]: preset += ".ini"
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
        """Helper to read a Slic3r configuration file"""
        import configparser
        parser = configparser.RawConfigParser()

        class add_header:
            def __init__(self, f):
                self.f = f
                self.header = '[dummy]'

            def readline(self):
                if self.header:
                    try: return self.header
                    finally: self.header = None
                else:
                    return self.f.readline()

            def __iter__(self):
                import itertools
                return itertools.chain([self.header], iter(self.f))

        parser.readfp(add_header(open(configfile)), configfile)
        return parser

    def set_slic3r_config(self, configfile, cat, file):
        """Set new preset for a given category"""
        self.slic3r_configs[cat] = file
        if self.settings.slic3rupdate:
            config = self.read_slic3r_config(configfile)
            version = config.get("dummy", "version") # Slic3r version
            preset = os.path.basename(file)
            # Starting from Slic3r 1.3.0, preset names have no extension
            if version.split(".") >= ["1","3","0"]:
                preset = os.path.splitext(preset)[0]
            config.set("presets", cat, preset)
            f = StringIO.StringIO()
            config.write(f)
            data = f.getvalue()
            f.close()
            data = data.replace("[dummy]\n", "")
            with open(configfile, "w") as f:
                f.write(data)

class PronterApp(wx.App):

    mainwindow = None

    def __init__(self, *args, **kwargs):
        super(PronterApp, self).__init__(*args, **kwargs)
        self.SetAppName("Pronterface")
        self.locale = wx.Locale(wx.Locale.GetSystemLanguage())
        self.mainwindow = PronterWindow(self)
        self.mainwindow.Show()
