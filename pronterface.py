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

import os, Queue, re

from printrun.printrun_utils import install_locale
install_locale('pronterface')

try:
    import wx
except:
    print _("WX is not installed. This program requires WX to run.")
    raise
import sys, glob, time, datetime, threading, traceback, cStringIO, subprocess

from printrun.pronterface_widgets import *
from serial import SerialException

StringIO = cStringIO

winsize = (800, 500)
layerindex = 0
if os.name == "nt":
    winsize = (800, 530)
    try:
        import _winreg
    except:
        pass

import printcore
from printrun.printrun_utils import pixmapfile, configfile
from printrun.gui import MainWindow
import pronsole

def dosify(name):
    return os.path.split(name)[1].split(".")[0][:8]+".g"

def parse_temperature_report(report, key):
    if key in report:
        return float(filter(lambda x: x.startswith(key), report.split())[0].split(":")[1].split("/")[0])
    else: 
        return -1.0

def format_time(timestamp):
    return datetime.datetime.fromtimestamp(timestamp).strftime("%H:%M:%S")

def format_duration(delta):
    return str(datetime.timedelta(seconds = int(delta)))

class Tee(object):
    def __init__(self, target):
        self.stdout = sys.stdout
        sys.stdout = self
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


class PronterWindow(MainWindow, pronsole.pronsole):
    def __init__(self, filename = None, size = winsize):
        pronsole.pronsole.__init__(self)
        self.settings.build_dimensions = '200x200x100+0+0+0' #default build dimensions are 200x200x100 with 0, 0, 0 in the corner of the bed
        self.settings.last_bed_temperature = 0.0
        self.settings.last_file_path = ""
        self.settings.last_temperature = 0.0
        self.settings.preview_extrusion_width = 0.5
        self.settings.preview_grid_step1 = 10.
        self.settings.preview_grid_step2 = 50.
        self.settings.bgcolor = "#FFFFFF"
        self.helpdict["build_dimensions"] = _("Dimensions of Build Platform\n & optional offset of origin\n\nExamples:\n   XXXxYYY\n   XXX,YYY,ZZZ\n   XXXxYYYxZZZ+OffX+OffY+OffZ")
        self.helpdict["last_bed_temperature"] = _("Last Set Temperature for the Heated Print Bed")
        self.helpdict["last_file_path"] = _("Folder of last opened file")
        self.helpdict["last_temperature"] = _("Last Temperature of the Hot End")
        self.helpdict["preview_extrusion_width"] = _("Width of Extrusion in Preview (default: 0.5)")
        self.helpdict["preview_grid_step1"] = _("Fine Grid Spacing (default: 10)")
        self.helpdict["preview_grid_step2"] = _("Coarse Grid Spacing (default: 50)")
        self.helpdict["bgcolor"] = _("Pronterface background color (default: #FFFFFF)")
        self.filename = filename
        os.putenv("UBUNTU_MENUPROXY", "0")
        MainWindow.__init__(self, None, title = _("Printer Interface"), size = size);
        self.SetIcon(wx.Icon(pixmapfile("P-face.ico"), wx.BITMAP_TYPE_ICO))
        self.panel = wx.Panel(self,-1, size = size)

        self.statuscheck = False
        self.status_thread = None
        self.capture_skip = {}
        self.capture_skip_newline = False
        self.tempreport = ""
        self.monitor = 0
        self.f = None
        self.skeinp = None
        self.monitor_interval = 3
        self.paused = False
        self.sentlines = Queue.Queue(30)
        self.cpbuttons = [
            SpecialButton(_("Motors off"), ("M84"), (250, 250, 250), None, 0, _("Switch all motors off")),
            SpecialButton(_("Check temp"), ("M105"), (225, 200, 200), (2, 5), (1, 1), _("Check current hotend temperature")),
            SpecialButton(_("Extrude"), ("extrude"), (225, 200, 200), (4, 0), (1, 2), _("Advance extruder by set length")),
            SpecialButton(_("Reverse"), ("reverse"), (225, 200, 200), (5, 0), (1, 2), _("Reverse extruder by set length")),
        ]
        self.custombuttons = []
        self.btndict = {}
        self.parse_cmdline(sys.argv[1:])
        self.build_dimensions_list = self.get_build_dimensions(self.settings.build_dimensions)
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
                        print str(x)
                else:
                    print _("Note!!! You have specified custom buttons in both custombtn.txt and .pronsolerc")
                    print _("Ignoring custombtn.txt. Remove all current buttons to revert to custombtn.txt")

        except:
            pass
        self.popmenu()
        self.createGui()
        self.t = Tee(self.catchprint)
        self.stdout = sys.stdout
        self.skeining = 0
        self.mini = False
        self.p.sendcb = self.sentcb
        self.p.startcb = self.startcb
        self.p.endcb = self.endcb
        self.starttime = 0
        self.extra_print_time = 0
        self.curlayer = 0
        self.cur_button = None
        self.predisconnect_mainqueue = None
        self.predisconnect_queueindex = None
        self.predisconnect_layer = None
        self.hsetpoint = 0.0
        self.bsetpoint = 0.0
        self.webInterface = None
        if self.webrequested:
            try :
                import cherrypy
                from printrun import webinterface
                try:
                    self.webInterface = webinterface.WebInterface(self)
                    self.webThread = threading.Thread(target = webinterface.StartWebInterfaceThread, args = (self.webInterface, ))
                    self.webThread.start()
                except:
                    print _("Failed to start web interface")
                    traceback.print_exc(file = sys.stdout)
                    self.webInterface = None
            except:
                print _("CherryPy is not installed. Web Interface Disabled.")
        if self.filename is not None:
            self.do_load(self.filename)

    def startcb(self):
        self.starttime = time.time()
        print "Print Started at: " + format_time(self.starttime)

    def endcb(self):
        if self.p.queueindex == 0:
            print "Print ended at: " + format_time(time.time())
            print_duration = int(time.time () - self.starttime + self.extra_print_time)
            print "and took: " + format_duration(print_duration)
            wx.CallAfter(self.pausebtn.Disable)
            wx.CallAfter(self.printbtn.SetLabel, _("Print"))

            param = self.settings.final_command
            if not param:
                return
            import shlex
            pararray = [i.replace("$s", str(self.filename)).replace("$t", format_duration(print_duration)).encode() for i in shlex.split(param.replace("\\", "\\\\").encode())]
            self.finalp = subprocess.Popen(pararray, stderr = subprocess.STDOUT, stdout = subprocess.PIPE)

    def online(self):
        print _("Printer is now online.")
        self.connectbtn.SetLabel(_("Disconnect"))
        self.connectbtn.SetToolTip(wx.ToolTip("Disconnect from the printer"))
        self.connectbtn.Bind(wx.EVT_BUTTON, self.disconnect)

        for i in self.printerControls:
            wx.CallAfter(i.Enable)

        # Enable XYButtons and ZButtons
        wx.CallAfter(self.xyb.enable)
        wx.CallAfter(self.zb.enable)

        if self.filename:
            wx.CallAfter(self.printbtn.Enable)

    def sentcb(self, line):
        if "G1" in line:
            if "Z" in line:
                try:
                    layer = float(line.split("Z")[1].split()[0])
                    if layer != self.curlayer:
                        self.curlayer = layer
                        self.gviz.hilight = []
                        threading.Thread(target = wx.CallAfter, args = (self.gviz.setlayer, layer)).start()
                except:
                    pass
            try:
                self.sentlines.put_nowait(line)
            except:
                pass
            #threading.Thread(target = self.gviz.addgcode, args = (line, 1)).start()
            #self.gwindow.p.addgcode(line, hilight = 1)
        if "M104" in line or "M109" in line:
            if "S" in line:
                try:
                    temp = float(line.split("S")[1].split("*")[0])
                    wx.CallAfter(self.graph.SetExtruder0TargetTemperature, temp)
                except:
                    pass
            try:
                self.sentlines.put_nowait(line)
            except:
                pass
        if "M140" in line:
            if "S" in line:
                try:
                    temp = float(line.split("S")[1].split("*")[0])
                    wx.CallAfter(self.graph.SetBedTargetTemperature, temp)
                except:
                    pass
            try:
                self.sentlines.put_nowait(line)
            except:
                pass

    def do_extrude(self, l = ""):
        try:
            if not l.__class__ in (str, unicode) or not len(l):
                l = str(self.edist.GetValue())
            pronsole.pronsole.do_extrude(self, l)
        except:
            raise

    def do_reverse(self, l = ""):
        try:
            if not l.__class__ in (str, unicode) or not len(l):
                l = str(- float(self.edist.GetValue()))
            pronsole.pronsole.do_extrude(self, l)
        except:
            pass

    def setbedgui(self, f):
        self.bsetpoint = f
        wx.CallAfter(self.graph.SetBedTargetTemperature, int(f))
        if f>0:
            wx.CallAfter(self.btemp.SetValue, str(f))
            self.set("last_bed_temperature", str(f))
            wx.CallAfter(self.setboff.SetBackgroundColour, "")
            wx.CallAfter(self.setboff.SetForegroundColour, "")
            wx.CallAfter(self.setbbtn.SetBackgroundColour, "#FFAA66")
            wx.CallAfter(self.setbbtn.SetForegroundColour, "#660000")
            wx.CallAfter(self.btemp.SetBackgroundColour, "#FFDABB")
        else:
            wx.CallAfter(self.setboff.SetBackgroundColour, "#0044CC")
            wx.CallAfter(self.setboff.SetForegroundColour, "white")
            wx.CallAfter(self.setbbtn.SetBackgroundColour, "")
            wx.CallAfter(self.setbbtn.SetForegroundColour, "")
            wx.CallAfter(self.btemp.SetBackgroundColour, "white")
            wx.CallAfter(self.btemp.Refresh)

    def sethotendgui(self, f):
        self.hsetpoint = f
        wx.CallAfter(self.graph.SetExtruder0TargetTemperature, int(f))
        if f > 0:
            wx.CallAfter(self.htemp.SetValue, str(f))
            self.set("last_temperature", str(f))
            wx.CallAfter(self.settoff.SetBackgroundColour, "")
            wx.CallAfter(self.settoff.SetForegroundColour, "")
            wx.CallAfter(self.settbtn.SetBackgroundColour, "#FFAA66")
            wx.CallAfter(self.settbtn.SetForegroundColour, "#660000")
            wx.CallAfter(self.htemp.SetBackgroundColour, "#FFDABB")
        else:
            wx.CallAfter(self.settoff.SetBackgroundColour, "#0044CC")
            wx.CallAfter(self.settoff.SetForegroundColour, "white")
            wx.CallAfter(self.settbtn.SetBackgroundColour, "")
            wx.CallAfter(self.settbtn.SetForegroundColour, "")
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
                    self.p.send_now("M104 S"+l)
                    print _("Setting hotend temperature to %f degrees Celsius.") % f
                    self.sethotendgui(f)
                else:
                    print _("Printer is not online.")
            else:
                print _("You cannot set negative temperatures. To turn the hotend off entirely, set its temperature to 0.")
        except Exception, x:
            print _("You must enter a temperature. (%s)") % (repr(x),)
            if self.webInterface:
                self.webInterface.AddLog("You must enter a temperature. (%s)" % (repr(x),))

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
                    self.p.send_now("M140 S"+l)
                    print _("Setting bed temperature to %f degrees Celsius.") % f
                    self.setbedgui(f)
                else:
                    print _("Printer is not online.")
                    if self.webInterface:
                        self.webInterface.AddLog("Printer is not online.")
            else:
                print _("You cannot set negative temperatures. To turn the bed off entirely, set its temperature to 0.")
                if self.webInterface:
                    self.webInterface.AddLog("You cannot set negative temperatures. To turn the bed off entirely, set its temperature to 0.")
        except Exception, x:
            print _("You must enter a temperature. (%s)") % (repr(x),)
            if self.webInterface:
                self.webInterface.AddLog("You must enter a temperature.")

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
                        dialog = wx.MessageDialog(self, _("Do you want to erase the macro?"), style = wx.YES_NO|wx.YES_DEFAULT|wx.ICON_QUESTION)
                        if dialog.ShowModal() == wx.ID_YES:
                            self.delete_macro(macro_name)
                            return
                    print _("Cancelled.")
                    if self.webInterface:
                        self.webInterface.AddLog("Cancelled.")
                    return
                self.cur_macro_name = macro_name
                self.cur_macro_def = definition
                self.end_macro()
            MacroEditor(macro_name, old_macro_definition, cb)
        else:
            pronsole.pronsole.start_macro(self, macro_name, old_macro_definition)

    def catchprint(self, l):
        if self.capture_skip_newline and len(l) and not len(l.strip("\n\r")):
            self.capture_skip_newline = False
            return
        for pat in self.capture_skip.keys():
            if self.capture_skip[pat] > 0 and pat.match(l):
                self.capture_skip[pat] -= 1
                self.capture_skip_newline = True
                return
        wx.CallAfter(self.addtexttolog,l);

    def scanserial(self):
        """scan for available ports. return a list of device names."""
        baselist = []
        if os.name == "nt":
            try:
                key = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE, "HARDWARE\\DEVICEMAP\\SERIALCOMM")
                i = 0
                while True:
                    baselist += [_winreg.EnumValue(key, i)[1]]
                    i += 1
            except:
                pass
        return baselist+glob.glob('/dev/ttyUSB*') + glob.glob('/dev/ttyACM*') + glob.glob("/dev/tty.*") + glob.glob("/dev/cu.*") + glob.glob("/dev/rfcomm*")

    def project(self,event):
        from printrun import projectlayer
        if self.p.online:
            projectlayer.setframe(self,self.p).Show()
        else:
            print _("Printer is not online.")
            if self.webInterface:
                self.webInterface.AddLog("Printer is not online.")

    def popmenu(self):
        self.menustrip = wx.MenuBar()
        # File menu
        m = wx.Menu()
        self.Bind(wx.EVT_MENU, self.loadfile, m.Append(-1, _("&Open..."), _(" Opens file")))
        self.Bind(wx.EVT_MENU, self.do_editgcode, m.Append(-1, _("&Edit..."), _(" Edit open file")))
        self.Bind(wx.EVT_MENU, self.clearOutput, m.Append(-1, _("Clear console"), _(" Clear output console")))
        self.Bind(wx.EVT_MENU, self.project, m.Append(-1, _("Projector"), _(" Project slices")))
        self.Bind(wx.EVT_MENU, self.OnExit, m.Append(wx.ID_EXIT, _("E&xit"), _(" Closes the Window")))
        self.menustrip.Append(m, _("&File"))

        # Settings menu
        m = wx.Menu()
        self.macros_menu = wx.Menu()
        m.AppendSubMenu(self.macros_menu, _("&Macros"))
        self.Bind(wx.EVT_MENU, self.new_macro, self.macros_menu.Append(-1, _("<&New...>")))
        self.Bind(wx.EVT_MENU, lambda *e:options(self), m.Append(-1, _("&Options"), _(" Options dialog")))

        self.Bind(wx.EVT_MENU, lambda x: threading.Thread(target = lambda:self.do_skein("set")).start(), m.Append(-1, _("Slicing Settings"), _(" Adjust slicing settings")))

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

    def doneediting(self, gcode):
        f = open(self.filename, "w")
        f.write("\n".join(gcode))
        f.close()
        wx.CallAfter(self.loadfile, None, self.filename)

    def do_editgcode(self, e = None):
        if self.filename is not None:
            MacroEditor(self.filename, self.f, self.doneediting, 1)

    def new_macro(self, e = None):
        dialog = wx.Dialog(self, -1, _("Enter macro name"), size = (260, 85))
        panel = wx.Panel(dialog, -1)
        vbox = wx.BoxSizer(wx.VERTICAL)
        wx.StaticText(panel, -1, _("Macro name:"), (8, 14))
        dialog.namectrl = wx.TextCtrl(panel, -1, '', (110, 8), size = (130, 24), style = wx.TE_PROCESS_ENTER)
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        okb = wx.Button(dialog, wx.ID_OK, _("Ok"), size = (60, 24))
        dialog.Bind(wx.EVT_TEXT_ENTER, lambda e:dialog.EndModal(wx.ID_OK), dialog.namectrl)
        #dialog.Bind(wx.EVT_BUTTON, lambda e:self.new_macro_named(dialog, e), okb)
        hbox.Add(okb)
        hbox.Add(wx.Button(dialog, wx.ID_CANCEL, _("Cancel"), size = (60, 24)))
        vbox.Add(panel)
        vbox.Add(hbox, 1, wx.ALIGN_CENTER|wx.TOP|wx.BOTTOM, 10)
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
        if self.macros.has_key(macro):
            old_def = self.macros[macro]
        elif len([c for c in macro.encode("ascii", "replace") if not c.isalnum() and c != "_"]):
            print _("Macro name may contain only ASCII alphanumeric symbols and underscores")
            if self.webInterface:
                self.webInterface.AddLog("Macro name may contain only alphanumeric symbols and underscores")
            return
        elif hasattr(self.__class__, "do_"+macro):
            print _("Name '%s' is being used by built-in command") % macro
            return
        else:
            old_def = ""
        self.start_macro(macro, old_def)
        return macro

    def update_macros_menu(self):
        if not hasattr(self, "macros_menu"):
            return # too early, menu not yet built
        try:
            while True:
                item = self.macros_menu.FindItemByPosition(1)
                if item is None: return
                self.macros_menu.DeleteItem(item)
        except:
            pass
        for macro in self.macros.keys():
            self.Bind(wx.EVT_MENU, lambda x, m = macro: self.start_macro(m, self.macros[m]), self.macros_menu.Append(-1, macro))

    def OnExit(self, event):
        self.Close()

    def rescanports(self, event = None):
        scan = self.scanserial()
        portslist = list(scan)
        if self.settings.port != "" and self.settings.port not in portslist:
            portslist += [self.settings.port]
            self.serialport.Clear()
            self.serialport.AppendItems(portslist)
        try:
            if os.path.exists(self.settings.port) or self.settings.port in scan:
                self.serialport.SetValue(self.settings.port)
            elif len(portslist) > 0:
                self.serialport.SetValue(portslist[0])
        except:
            pass

    def cbkey(self, e):
        if e.GetKeyCode() == wx.WXK_UP:
            if self.commandbox.histindex == len(self.commandbox.history):
                self.commandbox.history+=[self.commandbox.GetValue()] #save current command
            if len(self.commandbox.history):
                self.commandbox.histindex = (self.commandbox.histindex-1)%len(self.commandbox.history)
                self.commandbox.SetValue(self.commandbox.history[self.commandbox.histindex])
                self.commandbox.SetSelection(0, len(self.commandbox.history[self.commandbox.histindex]))
        elif e.GetKeyCode() == wx.WXK_DOWN:
            if self.commandbox.histindex == len(self.commandbox.history):
                self.commandbox.history+=[self.commandbox.GetValue()] #save current command
            if len(self.commandbox.history):
                self.commandbox.histindex = (self.commandbox.histindex+1)%len(self.commandbox.history)
                self.commandbox.SetValue(self.commandbox.history[self.commandbox.histindex])
                self.commandbox.SetSelection(0, len(self.commandbox.history[self.commandbox.histindex]))
        else:
            e.Skip()

    def plate(self, e):
        import plater
        print "plate function activated"
        plater.stlwin(size = (800, 580), callback = self.platecb, parent = self).Show()

    def platecb(self, name):
        print "plated: "+name
        self.loadfile(None, name)

    def sdmenu(self, e):
        obj = e.GetEventObject()
        popupmenu = wx.Menu()
        item = popupmenu.Append(-1, _("SD Upload"))
        if not self.f or not len(self.f):
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

    def showwin(self, event):
        if(self.f is not None):
            self.gwindow.Show(True)
            self.gwindow.SetToolTip(wx.ToolTip("Mousewheel zooms the display\nShift / Mousewheel scrolls layers"))
            self.gwindow.Raise()

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

    def toggleview(self, e):
        if(self.mini):
            self.mini = False
            self.mainsizer.Fit(self)

            #self.SetSize(winsize)
            wx.CallAfter(self.minibtn.SetLabel, _("Mini mode"))

        else:
            self.mini = True
            self.uppersizer.Fit(self)

            #self.SetSize(winssize)
            wx.CallAfter(self.minibtn.SetLabel, _("Full mode"))

    def cbuttons_reload(self):
        allcbs = []
        ubs = self.uppersizer
        cs = self.centersizer
        #for item in ubs.GetChildren():
        #    if hasattr(item.GetWindow(),"custombutton"):
        #        allcbs += [(ubs, item.GetWindow())]
        for item in cs.GetChildren():
            if hasattr(item.GetWindow(),"custombutton"):
                allcbs += [(cs, item.GetWindow())]
        for sizer, button in allcbs:
            #sizer.Remove(button)
            button.Destroy()
        self.custombuttonbuttons = []
        newbuttonbuttonindex = len(self.custombuttons)
        while newbuttonbuttonindex>0 and self.custombuttons[newbuttonbuttonindex-1] is None:
            newbuttonbuttonindex -= 1
        while len(self.custombuttons) < 13:
            self.custombuttons.append(None)
        for i in xrange(len(self.custombuttons)):
            btndef = self.custombuttons[i]
            try:
                b = wx.Button(self.panel, -1, btndef.label, style = wx.BU_EXACTFIT)
                b.SetToolTip(wx.ToolTip(_("Execute command: ")+btndef.command))
                if btndef.background:
                    b.SetBackgroundColour(btndef.background)
                    rr, gg, bb = b.GetBackgroundColour().Get()
                    if 0.3*rr+0.59*gg+0.11*bb < 60:
                        b.SetForegroundColour("#ffffff")
            except:
                if i == newbuttonbuttonindex:
                    self.newbuttonbutton = b = wx.Button(self.panel, -1, "+", size = (19, 18), style = wx.BU_EXACTFIT)
                    #b.SetFont(wx.Font(12, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
                    b.SetForegroundColour("#4444ff")
                    b.SetToolTip(wx.ToolTip(_("click to add new custom button")))
                    b.Bind(wx.EVT_BUTTON, self.cbutton_edit)
                else:
                    b = wx.Button(self.panel,-1, ".", size = (1, 1))
                    #b = wx.StaticText(self.panel,-1, "", size = (72, 22), style = wx.ALIGN_CENTRE+wx.ST_NO_AUTORESIZE) #+wx.SIMPLE_BORDER
                    b.Disable()
                    #continue
            b.custombutton = i
            b.properties = btndef
            if btndef is not None:
                b.Bind(wx.EVT_BUTTON, self.procbutton)
                b.Bind(wx.EVT_MOUSE_EVENTS, self.editbutton)
            #else:
            #    b.Bind(wx.EVT_BUTTON, lambda e:e.Skip())
            self.custombuttonbuttons.append(b)
            #if i<4:
            #    ubs.Add(b)
            #else:
            cs.Add(b, pos = ((i)/4, (i)%4))
        self.mainsizer.Layout()

    def help_button(self):
        print _('Defines custom button. Usage: button <num> "title" [/c "colour"] command')
        if self.webInterface:
            self.webInterface.AddLog('Defines custom button. Usage: button <num> "title" [/c "colour"] command')

    def do_button(self, argstr):
        def nextarg(rest):
            rest = rest.lstrip()
            if rest.startswith('"'):
                return rest[1:].split('"',1)
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
        if num<0 or num>=64:
            print _("Custom button number should be between 0 and 63")
            if self.webInterface:
                self.webInterface.AddLog("Custom button number should be between 0 and 63")
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
            self.save_in_rc(("button %d" % n),'')
        elif bdef.background:
            colour = bdef.background
            if type(colour) not in (str, unicode):
                #print type(colour), map(type, colour)
                if type(colour) == tuple and tuple(map(type, colour)) == (int, int, int):
                    colour = map(lambda x:x%256, colour)
                    colour = wx.Colour(*colour).GetAsString(wx.C2S_NAME|wx.C2S_HTML_SYNTAX)
                else:
                    colour = wx.Colour(colour).GetAsString(wx.C2S_NAME|wx.C2S_HTML_SYNTAX)
            self.save_in_rc(("button %d" % n),'button %d "%s" /c "%s" %s' % (new_n, bdef.label, colour, bdef.command))
        else:
            self.save_in_rc(("button %d" % n),'button %d "%s" %s' % (new_n, bdef.label, bdef.command))

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
                        colour = map(lambda x:x%256, colour)
                        colour = wx.Colour(*colour).GetAsString(wx.C2S_NAME|wx.C2S_HTML_SYNTAX)
                    else:
                        colour = wx.Colour(colour).GetAsString(wx.C2S_NAME|wx.C2S_HTML_SYNTAX)
                bedit.color.SetValue(colour)
        else:
            n = len(self.custombuttons)
            while n>0 and self.custombuttons[n-1] is None:
                n -= 1
        if bedit.ShowModal() == wx.ID_OK:
            if n == len(self.custombuttons):
                self.custombuttons+=[None]
            self.custombuttons[n]=SpecialButton(bedit.name.GetValue().strip(), bedit.command.GetValue().strip(), custom = True)
            if bedit.color.GetValue().strip()!="":
                self.custombuttons[n].background = bedit.color.GetValue()
            self.cbutton_save(n, self.custombuttons[n])
        bedit.Destroy()
        self.cbuttons_reload()

    def cbutton_remove(self, e, button):
        n = button.custombutton
        self.custombuttons[n]=None
        self.cbutton_save(n, None)
        #while len(self.custombuttons) and self.custombuttons[-1] is None:
        #    del self.custombuttons[-1]
        wx.CallAfter(self.cbuttons_reload)

    def cbutton_order(self, e, button, dir):
        n = button.custombutton
        if dir<0:
            n = n-1
        if n+1 >= len(self.custombuttons):
            self.custombuttons+=[None] # pad
        # swap
        self.custombuttons[n], self.custombuttons[n+1] = self.custombuttons[n+1], self.custombuttons[n]
        self.cbutton_save(n, self.custombuttons[n])
        self.cbutton_save(n+1, self.custombuttons[n+1])
        #if self.custombuttons[-1] is None:
        #    del self.custombuttons[-1]
        self.cbuttons_reload()

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
                self.Bind(wx.EVT_MENU, lambda e, button = e.GetEventObject():self.cbutton_edit(e, button), item)
                item = popupmenu.Append(-1, _("Move left <<"))
                self.Bind(wx.EVT_MENU, lambda e, button = e.GetEventObject():self.cbutton_order(e, button,-1), item)
                if obj.custombutton == 0: item.Enable(False)
                item = popupmenu.Append(-1, _("Move right >>"))
                self.Bind(wx.EVT_MENU, lambda e, button = e.GetEventObject():self.cbutton_order(e, button, 1), item)
                if obj.custombutton == 63: item.Enable(False)
                pos = self.panel.ScreenToClient(e.GetEventObject().ClientToScreen(pos))
                item = popupmenu.Append(-1, _("Remove custom button '%s'") % e.GetEventObject().GetLabelText())
                self.Bind(wx.EVT_MENU, lambda e, button = e.GetEventObject():self.cbutton_remove(e, button), item)
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
                dx, dy = self.dragpos[0]-scrpos[0], self.dragpos[1]-scrpos[1]
                if dx*dx+dy*dy < 5*5: # threshold to detect dragging for jittery mice
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
                    self.dragging = wx.Button(self.panel,-1, obj.GetLabel(), style = wx.BU_EXACTFIT)
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
                btns = self.custombuttonbuttons
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
        if corner == 0: # upper-left
            self.onecmd('home X')
        if corner == 1: # upper-right
            self.onecmd('home Y')
        if corner == 2: # lower-right
            self.onecmd('home Z')
        if corner == 3: # lower-left
            self.onecmd('home')
        # When user clicks on the XY control, the Z control no longer gets spacebar/repeat signals
        self.zb.clearRepeat()

    def moveXY(self, x, y):
        if x != 0:
            self.onecmd('move X %s' % x)
        if y != 0:
            self.onecmd('move Y %s' % y)
        # When user clicks on the XY control, the Z control no longer gets spacebar/repeat signals
        self.zb.clearRepeat()

    def moveZ(self, z):
        if z != 0:
            self.onecmd('move Z %s' % z)
        # When user clicks on the Z control, the XY control no longer gets spacebar/repeat signals
        self.xyb.clearRepeat()

    def spacebarAction(self):
        self.zb.repeatLast()
        self.xyb.repeatLast()

    def procbutton(self, e):
        try:
            if hasattr(e.GetEventObject(),"custombutton"):
                if wx.GetKeyState(wx.WXK_CONTROL) or wx.GetKeyState(wx.WXK_ALT):
                    return self.editbutton(e)
                self.cur_button = e.GetEventObject().custombutton
            self.onecmd(e.GetEventObject().properties.command)
            self.cur_button = None
        except:
            print _("event object missing")
            if self.webInterface:
                self.webInterface.AddLog("event object missing")
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
        try:
            self.gwindow.Destroy()
        except:
            pass
        self.Destroy()
        if self.webInterface:
            from printrun import webinterface
            webinterface.KillWebInterfaceThread()

    def do_monitor(self, l = ""):
        if l.strip()=="":
            self.monitorbox.SetValue(not self.monitorbox.GetValue())
        elif l.strip()=="off":
            wx.CallAfter(self.monitorbox.SetValue, False)
        else:
            try:
                self.monitor_interval = float(l)
                wx.CallAfter(self.monitorbox.SetValue, self.monitor_interval>0)
            except:
                print _("Invalid period given.")
                if self.webInterface:
                    self.webInterface.AddLog("Invalid period given.")
        self.setmonitor(None)
        if self.monitor:
            print _("Monitoring printer.")
            if self.webInterface:
                self.webInterface.AddLog("Monitoring printer.")
        else:
            print _("Done monitoring.")
            if self.webInterface:
                self.webInterface.AddLog("Done monitoring.")

    def setmonitor(self, e):
        self.monitor = self.monitorbox.GetValue()
        if self.monitor:
            wx.CallAfter(self.graph.StartPlotting, 1000)
        else:
            wx.CallAfter(self.graph.StopPlotting)

    def addtexttolog(self,text):
        try:
            self.logbox.AppendText(text)
        except:
            print "attempted to write invalid text to console"
            pass
        if self.webInterface:
            self.webInterface.AppendLog(text)

    def setloud(self,e):
        self.p.loud=e.IsChecked()

    def sendline(self, e):
        command = self.commandbox.GetValue()
        if not len(command):
            return
        wx.CallAfter(self.addtexttolog, ">>>" + command + "\n");
        self.onecmd(str(command))
        self.commandbox.SetSelection(0, len(command))
        self.commandbox.history+=[command]
        self.commandbox.histindex = len(self.commandbox.history)

    def clearOutput(self, e):
        self.logbox.Clear()

    def statuschecker(self):
        while self.statuscheck:
            string = ""
            wx.CallAfter(self.tempdisp.SetLabel, self.tempreport.strip().replace("ok ", ""))
            try:
                wx.CallAfter(self.graph.SetExtruder0Temperature, parse_temperature_report(self.tempreport, "T:"))
                wx.CallAfter(self.graph.SetBedTemperature, parse_temperature_report(self.tempreport, "B:"))
            except:
                pass
            fractioncomplete = 0.0
            if self.sdprinting:
                fractioncomplete = float(self.percentdone / 100.0)
                string += _(" SD printing:%04.2f %%") % (self.percentdone,)
            if self.p.printing:
                fractioncomplete = float(self.p.queueindex) / len(self.p.mainqueue)
                string += _(" Printing: %04.2f%% |") % (100*float(self.p.queueindex)/len(self.p.mainqueue),)
                string += _(" Line# %d of %d lines |" ) % (self.p.queueindex, len(self.p.mainqueue))
            if fractioncomplete > 0.0:
                secondselapsed = int(time.time() - self.starttime + self.extra_print_time)
                secondsestimate = secondselapsed / fractioncomplete
                secondsremain = secondsestimate - secondselapsed
                string += _(" Est: %s of %s remaining | ") % (format_duration(secondsremain),
                                                              format_duration(secondsestimate))
                string += _(" Z: %0.2f mm") % self.curlayer
            wx.CallAfter(self.status.SetStatusText, string)
            wx.CallAfter(self.gviz.Refresh)
            if(self.monitor and self.p.online):
                if self.sdprinting:
                    self.p.send_now("M27")
                if not hasattr(self, "auto_monitor_pattern"):
                    self.auto_monitor_pattern = re.compile(r"(ok\s+)?T:[\d\.]+(\s+B:[\d\.]+)?(\s+@:[\d\.]+)?\s*")
                self.capture_skip[self.auto_monitor_pattern] = self.capture_skip.setdefault(self.auto_monitor_pattern, 0) + 1
                self.p.send_now("M105")
            cur_time = time.time()
            while time.time() < cur_time + self.monitor_interval:
                if not self.statuscheck:
                    break
                time.sleep(0.25)
            while not self.sentlines.empty():
                try:
                    gc = self.sentlines.get_nowait()
                    wx.CallAfter(self.gviz.addgcode, gc, 1)
                except:
                    break
        wx.CallAfter(self.status.SetStatusText, _("Not connected to printer."))

    def capture(self, func, *args, **kwargs):
        stdout = sys.stdout
        cout = None
        try:
            cout = self.cout
        except:
            pass
        if cout is None:
            cout = cStringIO.StringIO()

        sys.stdout = cout
        retval = None
        try:
            retval = func(*args,**kwargs)
        except:
            traceback.print_exc()
        sys.stdout = stdout
        return retval

    def recvcb(self, l):
        if "T:" in l:
            self.tempreport = l
            wx.CallAfter(self.tempdisp.SetLabel, self.tempreport.strip().replace("ok ", ""))
            try:
                wx.CallAfter(self.graph.SetExtruder0Temperature, parse_temperature_report(self.tempreport, "T:"))
                wx.CallAfter(self.graph.SetBedTemperature, parse_temperature_report(self.tempreport, "B:"))
            except:
                traceback.print_exc()
        tstring = l.rstrip()
        #print tstring
        if (tstring!="ok") and (tstring!="wait") and ("ok T:" not in tstring) and (not self.p.loud):
           # print "*"+tstring+"*"
           # print "[" + time.strftime('%H:%M:%S',time.localtime(time.time())) + "] " + tstring
            wx.CallAfter(self.addtexttolog, tstring + "\n");
        for i in self.recvlisteners:
            i(l)

    def listfiles(self, line):
        if "Begin file list" in line:
            self.listing = 1
        elif "End file list" in line:
            self.listing = 0
            self.recvlisteners.remove(self.listfiles)
            wx.CallAfter(self.filesloaded)
        elif self.listing:
            self.sdfiles+=[line.replace("\n", "").replace("\r", "").lower()]

    def waitforsdresponse(self, l):
        if "file.open failed" in l:
            wx.CallAfter(self.status.SetStatusText, _("Opening file failed."))
            self.recvlisteners.remove(self.waitforsdresponse)
            return
        if "File opened" in l:
            wx.CallAfter(self.status.SetStatusText, l)
        if "File selected" in l:
            wx.CallAfter(self.status.SetStatusText, _("Starting print"))
            self.sdprinting = 1
            self.p.send_now("M24")
            self.startcb()
            return
        if "Done printing file" in l:
            wx.CallAfter(self.status.SetStatusText, l)
            self.sdprinting = 0
            self.recvlisteners.remove(self.waitforsdresponse)
            self.endcb()
            return
        if "SD printing byte" in l:
            #M27 handler
            try:
                resp = l.split()
                vals = resp[-1].split("/")
                self.percentdone = 100.0*int(vals[0])/int(vals[1])
            except:
                pass

    def filesloaded(self):
        dlg = wx.SingleChoiceDialog(self, _("Select the file to print"), _("Pick SD file"), self.sdfiles)
        if(dlg.ShowModal() == wx.ID_OK):
            target = dlg.GetStringSelection()
            if len(target):
                self.recvlisteners+=[self.waitforsdresponse]
                self.p.send_now("M23 "+target.lower())
        #print self.sdfiles

    def getfiles(self):
        if not self.p.online:
            self.sdfiles = []
            return
        self.listing = 0
        self.sdfiles = []
        self.recvlisteners+=[self.listfiles]
        self.p.send_now("M21")
        self.p.send_now("M20")

    def skein_func(self):
        try:
            import shlex
            param = self.expandcommand(self.settings.slicecommand).encode()
            print "Slicing: ", param
            if self.webInterface:
                self.webInterface.AddLog("Slicing: "+param)
            pararray = [i.replace("$s", self.filename).replace("$o", self.filename.replace(".stl", "_export.gcode").replace(".STL", "_export.gcode")).encode() for i in shlex.split(param.replace("\\", "\\\\").encode())]
                #print pararray
            self.skeinp = subprocess.Popen(pararray, stderr = subprocess.STDOUT, stdout = subprocess.PIPE)
            while True:
                o = self.skeinp.stdout.read(1)
                if o == '' and self.skeinp.poll() != None: break
                sys.stdout.write(o)
            self.skeinp.wait()
            self.stopsf = 1
        except:
            print _("Failed to execute slicing software: ")
            if self.webInterface:
                self.webInterface.AddLog("Failed to execute slicing software: ")
            self.stopsf = 1
            traceback.print_exc(file = sys.stdout)

    def skein_monitor(self):
        while(not self.stopsf):
            try:
                wx.CallAfter(self.status.SetStatusText, _("Slicing..."))#+self.cout.getvalue().split("\n")[-1])
            except:
                pass
            time.sleep(0.1)
        fn = self.filename
        try:
            self.filename = self.filename.replace(".stl", "_export.gcode").replace(".STL", "_export.gcode").replace(".obj", "_export.gcode").replace(".OBJ", "_export.gcode")
            of = open(self.filename)
            self.f = [i.replace("\n", "").replace("\r", "") for i in of]
            of.close()
            if self.p.online:
                wx.CallAfter(self.printbtn.Enable)

            wx.CallAfter(self.status.SetStatusText, _("Loaded ")+self.filename+_(", %d lines") % (len(self.f),))
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

    def do_load(self,l):
        if hasattr(self, 'skeining'):
            self.loadfile(None, l)
        else:
            self._do_load(l)

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
        dlg = wx.FileDialog(self, _("Open file to print"), basedir, style = wx.FD_OPEN|wx.FD_FILE_MUST_EXIST)
        dlg.SetWildcard(_("OBJ, STL, and GCODE files (*.gcode;*.gco;*.g;*.stl;*.STL;*.obj;*.OBJ)|*.gcode;*.gco;*.g;*.stl;*.STL;*.obj;*.OBJ|All Files (*.*)|*.*"))
        if(filename is not None or dlg.ShowModal() == wx.ID_OK):
            if filename is not None:
                name = filename
            else:
                name = dlg.GetPath()
            if not(os.path.exists(name)):
                self.status.SetStatusText(_("File not found!"))
                return
            path = os.path.split(name)[0]
            if path != self.settings.last_file_path:
                self.set("last_file_path", path)
            if name.lower().endswith(".stl"):
                self.skein(name)
            elif name.lower().endswith(".obj"):
                self.skein(name)
            else:
                self.filename = name
                of = open(self.filename)
                self.f = [i.replace("\n", "").replace("\r", "") for i in of]
                of.close()
                self.status.SetStatusText(_("Loaded %s, %d lines") % (name, len(self.f)))
                wx.CallAfter(self.printbtn.SetLabel, _("Print"))
                wx.CallAfter(self.pausebtn.SetLabel, _("Pause"))
                wx.CallAfter(self.pausebtn.Disable)
                wx.CallAfter(self.recoverbtn.Disable)
                if self.p.online:
                    wx.CallAfter(self.printbtn.Enable)
                threading.Thread(target = self.loadviz).start()

    def loadviz(self):
        Xtot, Ytot, Ztot, Xmin, Xmax, Ymin, Ymax, Zmin, Zmax = pronsole.measurements(self.f)
        print pronsole.totalelength(self.f), _("mm of filament used in this print\n")
        print _("the print goes from %f mm to %f mm in X\nand is %f mm wide\n") % (Xmin, Xmax, Xtot)
        if self.webInterface:
            self.webInterface.AddLog(_("the print goes from %f mm to %f mm in X\nand is %f mm wide\n") % (Xmin, Xmax, Xtot))
        print _("the print goes from %f mm to %f mm in Y\nand is %f mm wide\n") % (Ymin, Ymax, Ytot)
        print _("the print goes from %f mm to %f mm in Z\nand is %f mm high\n") % (Zmin, Zmax, Ztot)
        try:
            print _("Estimated duration (pessimistic): "), pronsole.estimate_duration(self.f)
        except:
            pass
        #import time
        #t0 = time.time()
        self.gviz.clear()
        self.gwindow.p.clear()
        self.gviz.addfile(self.f)
        #print "generated 2d view in %f s"%(time.time()-t0)
        #t0 = time.time()
        self.gwindow.p.addfile(self.f)
        #print "generated 3d view in %f s"%(time.time()-t0)
        self.gviz.showall = 1
        wx.CallAfter(self.gviz.Refresh)

    def printfile(self, event):
        self.extra_print_time = 0
        if self.paused:
            self.p.paused = 0
            self.paused = 0
            self.on_startprint()
            if self.sdprinting:
                self.p.send_now("M26 S0")
                self.p.send_now("M24")
                return

        if self.f is None or not len(self.f):
            wx.CallAfter(self.status.SetStatusText, _("No file loaded. Please use load first."))
            return
        if not self.p.online:
            wx.CallAfter(self.status.SetStatusText, _("Not connected to printer."))
            return
        self.on_startprint()
        self.p.startprint(self.f)

    def on_startprint(self):
        wx.CallAfter(self.pausebtn.SetLabel, _("Pause"))
        wx.CallAfter(self.pausebtn.Enable)
        wx.CallAfter(self.printbtn.SetLabel, _("Restart"))

    def endupload(self):
        self.p.send_now("M29 ")
        wx.CallAfter(self.status.SetStatusText, _("File upload complete"))
        time.sleep(0.5)
        self.p.clear = True
        self.uploading = False

    def uploadtrigger(self, l):
        if "Writing to file" in l:
            self.uploading = True
            self.p.startprint(self.f)
            self.p.endcb = self.endupload
            self.recvlisteners.remove(self.uploadtrigger)
        elif "open failed, File" in l:
            self.recvlisteners.remove(self.uploadtrigger)

    def upload(self, event):
        if not self.f or not len(self.f):
            return
        if not self.p.online:
            return
        dlg = wx.TextEntryDialog(self, ("Enter a target filename in 8.3 format:"), _("Pick SD filename") ,dosify(self.filename))
        if dlg.ShowModal() == wx.ID_OK:
            self.p.send_now("M21")
            self.p.send_now("M28 "+str(dlg.GetValue()))
            self.recvlisteners+=[self.uploadtrigger]

    def pause(self, event):
        print _("Paused.")
        if not self.paused:
            if self.sdprinting:
                self.p.send_now("M25")
            else:
                if(not self.p.printing):
                    #print "Not printing, cannot pause."
                    return
                self.p.pause()
            self.paused = True
            self.extra_print_time += int(time.time() - self.starttime)
            wx.CallAfter(self.pausebtn.SetLabel, _("Resume"))
        else:
            self.paused = False
            if self.sdprinting:
                self.p.send_now("M24")
            else:
                self.p.resume()
            wx.CallAfter(self.pausebtn.SetLabel, _("Pause"))

    def sdprintfile(self, event):
        self.on_startprint()
        threading.Thread(target = self.getfiles).start()

    def connect(self, event):
        print _("Connecting...")
        port = None
        try:
            port = self.scanserial()[0]
        except:
            pass
        if self.serialport.GetValue()!="":
            port = str(self.serialport.GetValue())
        baud = 115200
        try:
            baud = int(self.baud.GetValue())
        except:
            pass
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
                print _("Error: You are trying to connect to a non-exisiting port.")
            elif e.errno == 8:
                print _("Error: You don't have permission to open %s.") % port
                print _("You might need to add yourself to the dialout group.")
            else:
                print e
            # Kill the scope anyway
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
            wx.CallAfter(self.status.SetStatusText, _("Not connected to printer."))
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

    def disconnect(self, event):
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
        dlg = wx.MessageDialog(self, _("Are you sure you want to reset the printer?"), _("Reset?"), wx.YES|wx.NO)
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

    def get_build_dimensions(self, bdim):
        import re
        # a string containing up to six numbers delimited by almost anything
        # first 0-3 numbers specify the build volume, no sign, always positive
        # remaining 0-3 numbers specify the coordinates of the "southwest" corner of the build platform
        # "XXX,YYY"
        # "XXXxYYY+xxx-yyy"
        # "XXX,YYY,ZZZ+xxx+yyy-zzz"
        # etc
        bdl = re.match(
        "[^\d+-]*(\d+)?" + # X build size
        "[^\d+-]*(\d+)?" + # Y build size
        "[^\d+-]*(\d+)?" + # Z build size
        "[^\d+-]*([+-]\d+)?" + # X corner coordinate
        "[^\d+-]*([+-]\d+)?" + # Y corner coordinate
        "[^\d+-]*([+-]\d+)?"   # Z corner coordinate
        ,bdim).groups()
        defaults = [200, 200, 100, 0, 0, 0]
        bdl_float = [float(value) if value else defaults[i] for i, value in enumerate(bdl)]
        return bdl_float

if __name__ == '__main__':
    app = wx.App(False)
    main = PronterWindow()
    main.Show()
    try:
        app.MainLoop()
    except:
        pass
