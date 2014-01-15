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

import cmd
import glob
import os
import time
import sys
import subprocess
import codecs
import argparse
import locale
import logging
import traceback

from . import printcore
from printrun.printrun_utils import install_locale, run_command, \
    format_time, format_duration, RemainingTimeEstimator, \
    get_home_pos, parse_build_dimensions
install_locale('pronterface')
from printrun import gcoder

from functools import wraps

if os.name == "nt":
    try:
        import _winreg
    except:
        pass
READLINE = True
try:
    import readline
    try:
        readline.rl.mode.show_all_if_ambiguous = "on"  # config pyreadline on windows
    except:
        pass
except:
    READLINE = False  # neither readline module is available

def dosify(name):
    return os.path.split(name)[1].split(".")[0][:8] + ".g"

def setting_add_tooltip(func):
    @wraps(func)
    def decorator(self, *args, **kwargs):
        widget = func(self, *args, **kwargs)
        helptxt = self.help or ""
        sep, deftxt = "", ""
        if len(helptxt):
            sep = "\n"
            if helptxt.find("\n") >= 0:
                sep = "\n\n"
        if self.default is not "":
            deftxt = _("Default: ")
            resethelp = _("(Control-doubleclick to reset to default value)")
            if len(repr(self.default)) > 10:
                deftxt += "\n    " + repr(self.default).strip("'") + "\n" + resethelp
            else:
                deftxt += repr(self.default) + "  " + resethelp
        helptxt += sep + deftxt
        if len(helptxt):
            widget.SetToolTipString(helptxt)
        return widget
    return decorator

class Setting(object):

    DEFAULT_GROUP = "Printer"

    hidden = False

    def __init__(self, name, default, label = None, help = None, group = None):
        self.name = name
        self.default = default
        self._value = default
        self.label = label
        self.help = help
        self.group = group if group else Setting.DEFAULT_GROUP

    def _get_value(self):
        return self._value

    def _set_value(self, value):
        raise NotImplementedError
    value = property(_get_value, _set_value)

    def set_default(self, e):
        import wx
        if e.CmdDown() and e.ButtonDClick() and self.default is not "":
            confirmation = wx.MessageDialog(None, _("Are you sure you want to reset the setting to the default value: {0!r} ?").format(self.default), _("Confirm set default"), wx.ICON_EXCLAMATION | wx.YES_NO | wx.NO_DEFAULT)
            if confirmation.ShowModal() == wx.ID_YES:
                self._set_value(self.default)
        else:
            e.Skip()

    @setting_add_tooltip
    def get_label(self, parent):
        import wx
        widget = wx.StaticText(parent, -1, self.label or self.name)
        widget.set_default = self.set_default
        return widget

    @setting_add_tooltip
    def get_widget(self, parent):
        return self.get_specific_widget(parent)

    def get_specific_widget(self, parent):
        raise NotImplementedError

    def update(self):
        raise NotImplementedError

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name

class HiddenSetting(Setting):

    hidden = True

    def _set_value(self, value):
        self._value = value
    value = property(Setting._get_value, _set_value)

class wxSetting(Setting):

    widget = None

    def _set_value(self, value):
        self._value = value
        if self.widget:
            self.widget.SetValue(value)
    value = property(Setting._get_value, _set_value)

    def update(self):
        self.value = self.widget.GetValue()

class StringSetting(wxSetting):

    def get_specific_widget(self, parent):
        import wx
        self.widget = wx.TextCtrl(parent, -1, str(self.value))
        return self.widget

class ComboSetting(wxSetting):

    def __init__(self, name, default, choices, label = None, help = None, group = None):
        super(ComboSetting, self).__init__(name, default, label, help, group)
        self.choices = choices

    def get_specific_widget(self, parent):
        import wx
        self.widget = wx.ComboBox(parent, -1, str(self.value), choices = self.choices, style = wx.CB_DROPDOWN)
        return self.widget

class SpinSetting(wxSetting):

    def __init__(self, name, default, min, max, label = None, help = None, group = None):
        super(SpinSetting, self).__init__(name, default, label, help, group)
        self.min = min
        self.max = max

    def get_specific_widget(self, parent):
        import wx
        self.widget = wx.SpinCtrl(parent, -1, min = self.min, max = self.max)
        self.widget.SetValue(self.value)
        return self.widget

class FloatSpinSetting(SpinSetting):

    def get_specific_widget(self, parent):
        from wx.lib.agw.floatspin import FloatSpin
        self.widget = FloatSpin(parent, -1, value = self.value, min_val = self.min, max_val = self.max, digits = 2)
        return self.widget

class BooleanSetting(wxSetting):

    def _get_value(self):
        return bool(self._value)

    def _set_value(self, value):
        self._value = value
        if self.widget:
            self.widget.SetValue(bool(value))

    value = property(_get_value, _set_value)

    def get_specific_widget(self, parent):
        import wx
        self.widget = wx.CheckBox(parent, -1)
        self.widget.SetValue(bool(self.value))
        return self.widget

class StaticTextSetting(wxSetting):

    def __init__(self, name, label = " ", text = "", help = None, group = None):
        super(StaticTextSetting, self).__init__(name, "", label, help, group)
        self.text = text

    def update(self):
        pass

    def _get_value(self):
        return ""

    def _set_value(self, value):
        pass

    def get_specific_widget(self, parent):
        import wx
        self.widget = wx.StaticText(parent, -1, self.text)
        return self.widget

class BuildDimensionsSetting(wxSetting):

    widgets = None

    def _set_value(self, value):
        self._value = value
        if self.widgets:
            self._set_widgets_values(value)
    value = property(wxSetting._get_value, _set_value)

    def _set_widgets_values(self, value):
        build_dimensions_list = parse_build_dimensions(value)
        for i in range(len(self.widgets)):
            self.widgets[i].SetValue(build_dimensions_list[i])

    def get_widget(self, parent):
        from wx.lib.agw.floatspin import FloatSpin
        import wx
        build_dimensions = parse_build_dimensions(self.value)
        self.widgets = []
        w = lambda val, m, M: self.widgets.append(FloatSpin(parent, -1, value = val, min_val = m, max_val = M, digits = 2))
        addlabel = lambda name, pos: self.widget.Add(wx.StaticText(parent, -1, name), pos = pos, flag = wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, border = 5)
        addwidget = lambda *pos: self.widget.Add(self.widgets[-1], pos = pos, flag = wx.RIGHT, border = 5)
        self.widget = wx.GridBagSizer()
        addlabel(_("Width"), (0, 0))
        w(build_dimensions[0], 0, 2000)
        addwidget(0, 1)
        addlabel(_("Depth"), (0, 2))
        w(build_dimensions[1], 0, 2000)
        addwidget(0, 3)
        addlabel(_("Height"), (0, 4))
        w(build_dimensions[2], 0, 2000)
        addwidget(0, 5)
        addlabel(_("X offset"), (1, 0))
        w(build_dimensions[3], -2000, 2000)
        addwidget(1, 1)
        addlabel(_("Y offset"), (1, 2))
        w(build_dimensions[4], -2000, 2000)
        addwidget(1, 3)
        addlabel(_("Z offset"), (1, 4))
        w(build_dimensions[5], -2000, 2000)
        addwidget(1, 5)
        addlabel(_("X home pos."), (2, 0))
        w(build_dimensions[6], -2000, 2000)
        self.widget.Add(self.widgets[-1], pos = (2, 1))
        addlabel(_("Y home pos."), (2, 2))
        w(build_dimensions[7], -2000, 2000)
        self.widget.Add(self.widgets[-1], pos = (2, 3))
        addlabel(_("Z home pos."), (2, 4))
        w(build_dimensions[8], -2000, 2000)
        self.widget.Add(self.widgets[-1], pos = (2, 5))
        return self.widget

    def update(self):
        values = [float(w.GetValue()) for w in self.widgets]
        self.value = "%.02fx%.02fx%.02f%+.02f%+.02f%+.02f%+.02f%+.02f%+.02f" % tuple(values)

class Settings(object):
    #def _temperature_alias(self): return {"pla":210, "abs":230, "off":0}
    #def _temperature_validate(self, v):
    #    if v < 0: raise ValueError("You cannot set negative temperatures. To turn the hotend off entirely, set its temperature to 0.")
    #def _bedtemperature_alias(self): return {"pla":60, "abs":110, "off":0}
    def _baudrate_list(self): return ["2400", "9600", "19200", "38400", "57600", "115200", "250000"]

    def __init__(self):
        # defaults here.
        # the initial value determines the type
        self._add(StringSetting("port", "", _("Serial port"), _("Port used to communicate with printer")))
        self._add(ComboSetting("baudrate", 115200, self._baudrate_list(), _("Baud rate"), _("Communications Speed")))
        self._add(SpinSetting("bedtemp_abs", 110, 0, 400, _("Bed temperature for ABS"), _("Heated Build Platform temp for ABS (deg C)"), "Printer"))
        self._add(SpinSetting("bedtemp_pla", 60, 0, 400, _("Bed temperature for PLA"), _("Heated Build Platform temp for PLA (deg C)"), "Printer"))
        self._add(SpinSetting("temperature_abs", 230, 0, 400, _("Extruder temperature for ABS"), _("Extruder temp for ABS (deg C)"), "Printer"))
        self._add(SpinSetting("temperature_pla", 185, 0, 400, _("Extruder temperature for PLA"), _("Extruder temp for PLA (deg C)"), "Printer"))
        self._add(SpinSetting("xy_feedrate", 3000, 0, 50000, _("X && Y manual feedrate"), _("Feedrate for Control Panel Moves in X and Y (mm/min)"), "Printer"))
        self._add(SpinSetting("z_feedrate", 200, 0, 50000, _("Z manual feedrate"), _("Feedrate for Control Panel Moves in Z (mm/min)"), "Printer"))
        self._add(SpinSetting("e_feedrate", 100, 0, 1000, _("E manual feedrate"), _("Feedrate for Control Panel Moves in Extrusions (mm/min)"), "Printer"))
        self._add(StringSetting("slicecommand", "python skeinforge/skeinforge_application/skeinforge_utilities/skeinforge_craft.py $s", _("Slice command"), _("Slice command"), "External"))
        self._add(StringSetting("sliceoptscommand", "python skeinforge/skeinforge_application/skeinforge.py", _("Slicer options command"), _("Slice settings command"), "External"))
        self._add(StringSetting("final_command", "", _("Final command"), _("Executable to run when the print is finished"), "External"))
        self._add(StringSetting("error_command", "", _("Error command"), _("Executable to run when an error occurs"), "External"))

        self._add(HiddenSetting("project_offset_x", 0.0))
        self._add(HiddenSetting("project_offset_y", 0.0))
        self._add(HiddenSetting("project_interval", 2.0))
        self._add(HiddenSetting("project_pause", 2.5))
        self._add(HiddenSetting("project_scale", 1.0))
        self._add(HiddenSetting("project_x", 1024))
        self._add(HiddenSetting("project_y", 768))
        self._add(HiddenSetting("project_projected_x", 150.0))
        self._add(HiddenSetting("project_direction", "Top Down"))
        self._add(HiddenSetting("project_overshoot", 3.0))
        self._add(HiddenSetting("project_z_axis_rate", 200))
        self._add(HiddenSetting("project_layer", 0.1))
        self._add(HiddenSetting("project_prelift_gcode", ""))
        self._add(HiddenSetting("project_postlift_gcode", ""))
        self._add(HiddenSetting("pause_between_prints", True))
        self._add(HiddenSetting("default_extrusion", 5.0))
        self._add(HiddenSetting("last_extrusion", 5.0))

    _settings = []

    def __setattr__(self, name, value):
        if name.startswith("_"):
            return object.__setattr__(self, name, value)
        if isinstance(value, Setting):
            if not value.hidden:
                self._settings.append(value)
            object.__setattr__(self, "_" + name, value)
        elif hasattr(self, "_" + name):
            getattr(self, "_" + name).value = value
        else:
            setattr(self, name, StringSetting(name = name, default = value))

    def __getattr__(self, name):
        if name.startswith("_"):
            return object.__getattribute__(self, name)
        return getattr(self, "_" + name).value

    def _add(self, setting, callback = None):
        setattr(self, setting.name, setting)
        if callback:
            setattr(self, "_" + setting.name + "_cb", callback)

    def _set(self, key, value):
        try:
            value = getattr(self, "_%s_alias" % key)()[value]
        except KeyError:
            pass
        except AttributeError:
            pass
        try:
            getattr(self, "_%s_validate" % key)(value)
        except AttributeError:
            pass
        t = type(getattr(self, key))
        if t == bool and value == "False": setattr(self, key, False)
        else: setattr(self, key, t(value))
        try:
            cb = None
            try:
                cb = getattr(self, "_%s_cb" % key)
            except AttributeError:
                pass
            if cb is not None: cb(key, value)
        except:
            logging.warning((_("Failed to run callback after setting \"%s\":") % key) +
                            "\n" + traceback.format_exc())
        return value

    def _tabcomplete(self, key):
        try:
            return getattr(self, "_%s_list" % key)()
        except AttributeError:
            pass
        try:
            return getattr(self, "_%s_alias" % key)().keys()
        except AttributeError:
            pass
        return []

    def _all_settings(self):
        return self._settings

class Status:

    def __init__(self):
        self.extruder_temp = 0
        self.extruder_temp_target = 0
        self.bed_temp = 0
        self.bed_temp_target = 0
        self.print_job = None
        self.print_job_progress = 1.0

    def update_tempreading(self, tempstr):
            r = tempstr.split()
            # eg. r = ["ok", "T:20.5", "/0.0", "B:0.0", "/0.0", "@:0"]
            if len(r) == 6:
                self.extruder_temp = float(r[1][2:])
                self.extruder_temp_target = float(r[2][1:])
                self.bed_temp = float(r[3][2:])
                self.bed_temp_target = float(r[4][1:])

    @property
    def bed_enabled(self):
        return self.bed_temp != 0

    @property
    def extruder_enabled(self):
        return self.extruder_temp != 0


class pronsole(cmd.Cmd):
    def __init__(self):
        cmd.Cmd.__init__(self)
        if not READLINE:
            self.completekey = None
        self.status = Status()
        self.dynamic_temp = False
        self.compute_eta = None
        self.p = printcore.printcore()
        self.p.recvcb = self.recvcb
        self.p.startcb = self.startcb
        self.p.endcb = self.endcb
        self.p.layerchangecb = self.layer_change_cb
        self.recvlisteners = []
        self.in_macro = False
        self.p.onlinecb = self.online
        self.p.errorcb = self.logError
        self.fgcode = None
        self.listing = 0
        self.sdfiles = []
        self.paused = False
        self.sdprinting = 0
        self.temps = {"pla": "185", "abs": "230", "off": "0"}
        self.bedtemps = {"pla": "60", "abs": "110", "off": "0"}
        self.percentdone = 0
        self.tempreadings = ""
        self.macros = {}
        self.rc_loaded = False
        self.processing_rc = False
        self.processing_args = False
        self.settings = Settings()
        self.settings._add(BuildDimensionsSetting("build_dimensions", "200x200x100+0+0+0+0+0+0", _("Build dimensions"), _("Dimensions of Build Platform\n & optional offset of origin\n & optional switch position\n\nExamples:\n   XXXxYYY\n   XXX,YYY,ZZZ\n   XXXxYYYxZZZ+OffX+OffY+OffZ\nXXXxYYYxZZZ+OffX+OffY+OffZ+HomeX+HomeY+HomeZ"), "Printer"), self.update_build_dimensions)
        self.settings._port_list = self.scanserial
        self.settings._temperature_abs_cb = self.set_temp_preset
        self.settings._temperature_pla_cb = self.set_temp_preset
        self.settings._bedtemp_abs_cb = self.set_temp_preset
        self.settings._bedtemp_pla_cb = self.set_temp_preset
        self.update_build_dimensions(None, self.settings.build_dimensions)
        self.monitoring = 0
        self.starttime = 0
        self.extra_print_time = 0
        self.silent = False
        self.commandprefixes = 'MGT$'
        self.promptstrs = {"offline": "%(bold)suninitialized>%(normal)s ",
                           "fallback": "%(bold)sPC>%(normal)s ",
                           "macro": "%(bold)s..>%(normal)s ",
                           "online": "%(bold)sT:%(extruder_temp_fancy)s %(progress_fancy)s >%(normal)s "}

    def confirm(self):
        y_or_n = raw_input("y/n: ")
        if y_or_n == "y":
            return True
        elif y_or_n != "n":
            return self.confirm()
        return False

    def log(self, *msg):
        print u"".join(unicode(i) for i in msg)

    def logError(self, *msg):
        msg = u"".join(unicode(i) for i in msg)
        logging.error(msg)
        if not self.settings.error_command:
            return
        run_command(self.settings.error_command,
                    {"$m": msg},
                    stderr = subprocess.STDOUT, stdout = subprocess.PIPE,
                    blocking = False)

    def promptf(self):
        """A function to generate prompts so that we can do dynamic prompts. """
        if self.in_macro:
            promptstr = self.promptstrs["macro"]
        elif not self.p.online:
            promptstr = self.promptstrs["offline"]
        elif self.status.extruder_enabled:
            promptstr = self.promptstrs["online"]
        else:
            promptstr = self.promptstrs["fallback"]
        if not "%" in promptstr:
            return promptstr
        else:
            specials = {}
            specials["extruder_temp"] = str(int(self.status.extruder_temp))
            specials["extruder_temp_target"] = str(int(self.status.extruder_temp_target))
            if self.status.extruder_temp_target == 0:
                specials["extruder_temp_fancy"] = str(int(self.status.extruder_temp))
            else:
                specials["extruder_temp_fancy"] = "%s/%s" % (str(int(self.status.extruder_temp)), str(int(self.status.extruder_temp_target)))
            if self.p.printing:
                progress = int(1000 * float(self.p.queueindex) / len(self.p.mainqueue)) / 10
            elif self.sdprinting:
                progress = self.percentdone
            else:
                progress = 0.0
            specials["progress"] = str(progress)
            if self.p.printing or self.sdprinting:
                specials["progress_fancy"] = str(progress) + "%"
            else:
                specials["progress_fancy"] = "?%"
            specials["bold"] = "\033[01m"
            specials["normal"] = "\033[00m"
            return promptstr % specials

    def postcmd(self, stop, line):
        """ A hook we override to generate prompts after
            each command is executed, for the next prompt.
            We also use it to send M105 commands so that
            temp info gets updated for the prompt."""
        if self.p.online and self.dynamic_temp:
            self.p.send_now("M105")
        self.prompt = self.promptf()
        return stop

    def set_temp_preset(self, key, value):
        if not key.startswith("bed"):
            self.temps["pla"] = str(self.settings.temperature_pla)
            self.temps["abs"] = str(self.settings.temperature_abs)
            self.log("Hotend temperature presets updated, pla:%s, abs:%s" % (self.temps["pla"], self.temps["abs"]))
        else:
            self.bedtemps["pla"] = str(self.settings.bedtemp_pla)
            self.bedtemps["abs"] = str(self.settings.bedtemp_abs)
            self.log("Bed temperature presets updated, pla:%s, abs:%s" % (self.bedtemps["pla"], self.bedtemps["abs"]))

    def scanserial(self):
        """scan for available ports. return a list of device names."""
        baselist = []
        if os.name == "nt":
            try:
                key = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE, "HARDWARE\\DEVICEMAP\\SERIALCOMM")
                i = 0
                while(1):
                    baselist += [_winreg.EnumValue(key, i)[1]]
                    i += 1
            except:
                pass

        for g in ['/dev/ttyUSB*', '/dev/ttyACM*', "/dev/tty.*", "/dev/cu.*", "/dev/rfcomm*"]:
            baselist += glob.glob(g)
        return filter(self._bluetoothSerialFilter, baselist)

    def _bluetoothSerialFilter(self, serial):
        return not ("Bluetooth" in serial or "FireFly" in serial)

    def online(self):
        self.log("\rPrinter is now online")
        self.write_prompt()

    def write_prompt(self):
        sys.stdout.write(self.promptf())
        sys.stdout.flush()

    def help_help(self, l = ""):
        self.do_help("")

    def do_gcodes(self, l = ""):
        self.help_gcodes()

    def help_gcodes(self):
        self.log("Gcodes are passed through to the printer as they are")

    def complete_macro(self, text, line, begidx, endidx):
        if (len(line.split()) == 2 and line[-1] != " ") or (len(line.split()) == 1 and line[-1] == " "):
            return [i for i in self.macros.keys() if i.startswith(text)]
        elif(len(line.split()) == 3 or (len(line.split()) == 2 and line[-1] == " ")):
            return [i for i in ["/D", "/S"] + self.completenames(text) if i.startswith(text)]
        else:
            return []

    def hook_macro(self, l):
        l = l.rstrip()
        ls = l.lstrip()
        ws = l[:len(l) - len(ls)]  # just leading whitespace
        if len(ws) == 0:
            self.end_macro()
            # pass the unprocessed line to regular command processor to not require empty line in .pronsolerc
            return self.onecmd(l)
        self.cur_macro_def += l + "\n"

    def end_macro(self):
        if "onecmd" in self.__dict__: del self.onecmd  # remove override
        self.in_macro = False
        self.prompt = self.promptf()
        if self.cur_macro_def != "":
            self.macros[self.cur_macro_name] = self.cur_macro_def
            macro = self.compile_macro(self.cur_macro_name, self.cur_macro_def)
            setattr(self.__class__, "do_" + self.cur_macro_name, lambda self, largs, macro = macro: macro(self, *largs.split()))
            setattr(self.__class__, "help_" + self.cur_macro_name, lambda self, macro_name = self.cur_macro_name: self.subhelp_macro(macro_name))
            if not self.processing_rc:
                self.log("Macro '" + self.cur_macro_name + "' defined")
                # save it
                if not self.processing_args:
                    macro_key = "macro " + self.cur_macro_name
                    macro_def = macro_key
                    if "\n" in self.cur_macro_def:
                        macro_def += "\n"
                    else:
                        macro_def += " "
                    macro_def += self.cur_macro_def
                    self.save_in_rc(macro_key, macro_def)
        else:
            self.logError("Empty macro - cancelled")
        del self.cur_macro_name, self.cur_macro_def

    def parseusercmd(self, line):
        pass

    def compile_macro_line(self, line):
        line = line.rstrip()
        ls = line.lstrip()
        ws = line[:len(line) - len(ls)]  # just leading whitespace
        if ls == "" or ls.startswith('#'): return ""  # no code
        if ls.startswith('!'):
            return ws + ls[1:] + "\n"  # python mode
        else:
            ls = ls.replace('"', '\\"')  # need to escape double quotes
            ret = ws + 'self.parseusercmd("' + ls + '".format(*arg))\n'  # parametric command mode
            return ret + ws + 'self.onecmd("' + ls + '".format(*arg))\n'

    def compile_macro(self, macro_name, macro_def):
        if macro_def.strip() == "":
            self.logError("Empty macro - cancelled")
            return
        macro = None
        pycode = "def macro(self,*arg):\n"
        if "\n" not in macro_def.strip():
            pycode += self.compile_macro_line("  " + macro_def.strip())
        else:
            lines = macro_def.split("\n")
            for l in lines:
                pycode += self.compile_macro_line(l)
        exec pycode
        return macro

    def start_macro(self, macro_name, prev_definition = "", suppress_instructions = False):
        if not self.processing_rc and not suppress_instructions:
            self.logError("Enter macro using indented lines, end with empty line")
        self.cur_macro_name = macro_name
        self.cur_macro_def = ""
        self.onecmd = self.hook_macro  # override onecmd temporarily
        self.in_macro = False
        self.prompt = self.promptf()

    def delete_macro(self, macro_name):
        if macro_name in self.macros.keys():
            delattr(self.__class__, "do_" + macro_name)
            del self.macros[macro_name]
            self.log("Macro '" + macro_name + "' removed")
            if not self.processing_rc and not self.processing_args:
                self.save_in_rc("macro " + macro_name, "")
        else:
            self.logError("Macro '" + macro_name + "' is not defined")

    def do_macro(self, args):
        if args.strip() == "":
            self.print_topics("User-defined macros", map(str, self.macros.keys()), 15, 80)
            return
        arglist = args.split(None, 1)
        macro_name = arglist[0]
        if macro_name not in self.macros and hasattr(self.__class__, "do_" + macro_name):
            self.logError("Name '" + macro_name + "' is being used by built-in command")
            return
        if len(arglist) == 2:
            macro_def = arglist[1]
            if macro_def.lower() == "/d":
                self.delete_macro(macro_name)
                return
            if macro_def.lower() == "/s":
                self.subhelp_macro(macro_name)
                return
            self.cur_macro_def = macro_def
            self.cur_macro_name = macro_name
            self.end_macro()
            return
        if macro_name in self.macros:
            self.start_macro(macro_name, self.macros[macro_name])
        else:
            self.start_macro(macro_name)

    def help_macro(self):
        self.log("Define single-line macro: macro <name> <definition>")
        self.log("Define multi-line macro:  macro <name>")
        self.log("Enter macro definition in indented lines. Use {0} .. {N} to substitute macro arguments")
        self.log("Enter python code, prefixed with !  Use arg[0] .. arg[N] to substitute macro arguments")
        self.log("Delete macro:             macro <name> /d")
        self.log("Show macro definition:    macro <name> /s")
        self.log("'macro' without arguments displays list of defined macros")

    def subhelp_macro(self, macro_name):
        if macro_name in self.macros.keys():
            macro_def = self.macros[macro_name]
            if "\n" in macro_def:
                self.log("Macro '" + macro_name + "' defined as:")
                self.log(self.macros[macro_name] + "----------------")
            else:
                self.log("Macro '" + macro_name + "' defined as: '" + macro_def + "'")
        else:
            self.logError("Macro '" + macro_name + "' is not defined")

    def set(self, var, str):
        try:
            t = type(getattr(self.settings, var))
            value = self.settings._set(var, str)
            if not self.processing_rc and not self.processing_args:
                self.save_in_rc("set " + var, "set %s %s" % (var, value))
        except AttributeError:
            logging.warning("Unknown variable '%s'" % var)
        except ValueError, ve:
            self.logError("Bad value for variable '%s', expecting %s (%s)" % (var, repr(t)[1:-1], ve.args[0]))

    def do_set(self, argl):
        args = argl.split(None, 1)
        if len(args) < 1:
            for k in [kk for kk in dir(self.settings) if not kk.startswith("_")]:
                self.log("%s = %s" % (k, str(getattr(self.settings, k))))
            return
        if len(args) < 2:
            try:
                self.log("%s = %s" % (args[0], getattr(self.settings, args[0])))
            except AttributeError:
                logging.warning("Unknown variable '%s'" % args[0])
            return
        self.set(args[0], args[1])

    def help_set(self):
        self.log("Set variable:   set <variable> <value>")
        self.log("Show variable:  set <variable>")
        self.log("'set' without arguments displays all variables")

    def complete_set(self, text, line, begidx, endidx):
        if (len(line.split()) == 2 and line[-1] != " ") or (len(line.split()) == 1 and line[-1] == " "):
            return [i for i in dir(self.settings) if not i.startswith("_") and i.startswith(text)]
        elif(len(line.split()) == 3 or (len(line.split()) == 2 and line[-1] == " ")):
            return [i for i in self.settings._tabcomplete(line.split()[1]) if i.startswith(text)]
        else:
            return []

    def postloop(self):
        self.p.disconnect()
        cmd.Cmd.postloop(self)

    def load_rc(self, rc_filename):
        self.processing_rc = True
        try:
            rc = codecs.open(rc_filename, "r", "utf-8")
            self.rc_filename = os.path.abspath(rc_filename)
            for rc_cmd in rc:
                if not rc_cmd.lstrip().startswith("#"):
                    self.onecmd(rc_cmd)
            rc.close()
            if hasattr(self, "cur_macro_def"):
                self.end_macro()
            self.rc_loaded = True
        finally:
            self.processing_rc = False

    def load_default_rc(self, rc_filename = ".pronsolerc"):
        if rc_filename == ".pronsolerc" and hasattr(sys, "frozen") and sys.frozen in ["windows_exe", "console_exe"]:
            rc_filename = "printrunconf.ini"
        try:
            try:
                self.load_rc(os.path.join(os.path.expanduser("~"), rc_filename))
            except IOError:
                self.load_rc(rc_filename)
        except IOError:
            # make sure the filename is initialized
            self.rc_filename = os.path.abspath(os.path.join(os.path.expanduser("~"), rc_filename))

    def save_in_rc(self, key, definition):
        """
        Saves or updates macro or other definitions in .pronsolerc
        key is prefix that determines what is being defined/updated (e.g. 'macro foo')
        definition is the full definition (that is written to file). (e.g. 'macro foo move x 10')
        Set key as empty string to just add (and not overwrite)
        Set definition as empty string to remove it from .pronsolerc
        To delete line from .pronsolerc, set key as the line contents, and definition as empty string
        Only first definition with given key is overwritten.
        Updates are made in the same file position.
        Additions are made to the end of the file.
        """
        rci, rco = None, None
        if definition != "" and not definition.endswith("\n"):
            definition += "\n"
        try:
            written = False
            if os.path.exists(self.rc_filename):
                import shutil
                shutil.copy(self.rc_filename, self.rc_filename + "~bak")
                rci = codecs.open(self.rc_filename + "~bak", "r", "utf-8")
            rco = codecs.open(self.rc_filename, "w", "utf-8")
            if rci is not None:
                overwriting = False
                for rc_cmd in rci:
                    l = rc_cmd.rstrip()
                    ls = l.lstrip()
                    ws = l[:len(l) - len(ls)]  # just leading whitespace
                    if overwriting and len(ws) == 0:
                        overwriting = False
                    if not written and key != "" and rc_cmd.startswith(key) and (rc_cmd + "\n")[len(key)].isspace():
                        overwriting = True
                        written = True
                        rco.write(definition)
                    if not overwriting:
                        rco.write(rc_cmd)
                        if not rc_cmd.endswith("\n"): rco.write("\n")
            if not written:
                rco.write(definition)
            if rci is not None:
                rci.close()
            rco.close()
            #if definition != "":
            #    self.log("Saved '"+key+"' to '"+self.rc_filename+"'")
            #else:
            #    self.log("Removed '"+key+"' from '"+self.rc_filename+"'")
        except Exception, e:
            self.logError("Saving failed for ", key + ":", str(e))
        finally:
            del rci, rco

    def preloop(self):
        self.log("Welcome to the printer console! Type \"help\" for a list of available commands.")
        self.prompt = self.promptf()
        cmd.Cmd.preloop(self)

    def do_connect(self, l):
        a = l.split()
        p = self.scanserial()
        port = self.settings.port
        if (port == "" or port not in p) and len(p) > 0:
            port = p[0]
        baud = self.settings.baudrate or 115200
        if len(a) > 0:
            port = a[0]
        if len(a) > 1:
            try:
                baud = int(a[1])
            except:
                self.log("Bad baud value '" + a[1] + "' ignored")
        if len(p) == 0 and not port:
            self.log("No serial ports detected - please specify a port")
            return
        if len(a) == 0:
            self.log("No port specified - connecting to %s at %dbps" % (port, baud))
        if port != self.settings.port:
            self.settings.port = port
            self.save_in_rc("set port", "set port %s" % port)
        if baud != self.settings.baudrate:
            self.settings.baudrate = baud
            self.save_in_rc("set baudrate", "set baudrate %d" % baud)
        self.p.connect(port, baud)

    def help_connect(self):
        self.log("Connect to printer")
        self.log("connect <port> <baudrate>")
        self.log("If port and baudrate are not specified, connects to first detected port at 115200bps")
        ports = self.scanserial()
        if(len(ports)):
            self.log("Available ports: ", " ".join(ports))
        else:
            self.log("No serial ports were automatically found.")

    def complete_connect(self, text, line, begidx, endidx):
        if (len(line.split()) == 2 and line[-1] != " ") or (len(line.split()) == 1 and line[-1] == " "):
            return [i for i in self.scanserial() if i.startswith(text)]
        elif(len(line.split()) == 3 or (len(line.split()) == 2 and line[-1] == " ")):
            return [i for i in ["2400", "9600", "19200", "38400", "57600", "115200"] if i.startswith(text)]
        else:
            return []

    def do_disconnect(self, l):
        self.p.disconnect()

    def help_disconnect(self):
        self.log("Disconnects from the printer")

    def do_load(self, filename):
        self._do_load(filename)

    def _do_load(self, filename):
        if not filename:
            self.logError("No file name given.")
            return
        self.logError("Loading file: " + filename)
        if not os.path.exists(filename):
            self.logError("File not found!")
            return
        self.load_gcode(filename)
        self.log(_("Loaded %s, %d lines.") % (filename, len(self.fgcode)))
        self.log(_("Estimated duration: %s") % self.fgcode.estimate_duration())

    def load_gcode(self, filename):
        self.fgcode = gcoder.GCode(open(filename, "rU"),
                                   get_home_pos(self.build_dimensions_list))
        self.fgcode.estimate_duration()
        self.filename = filename

    def complete_load(self, text, line, begidx, endidx):
        s = line.split()
        if len(s) > 2:
            return []
        if (len(s) == 1 and line[-1] == " ") or (len(s) == 2 and line[-1] != " "):
            if len(s) > 1:
                return [i[len(s[1]) - len(text):] for i in glob.glob(s[1] + "*/") + glob.glob(s[1] + "*.g*")]
            else:
                return glob.glob("*/") + glob.glob("*.g*")

    def help_load(self):
        self.log("Loads a gcode file (with tab-completion)")

    def do_upload(self, l):
        names = l.split()
        if len(names) == 2:
            filename = names[0]
            targetname = names[1]
        else:
            self.logError(_("Please enter target name in 8.3 format."))
            return
        if not self.p.online:
            self.logError(_("Not connected to printer."))
            return
        self._do_load(filename)
        self.log(_("Uploading as %s") % targetname)
        self.log(_("Uploading %s") % self.filename)
        self.p.send_now("M28 " + targetname)
        self.log(_("Press Ctrl-C to interrupt upload."))
        self.p.startprint(self.fgcode)
        try:
            sys.stdout.write(_("Progress: ") + "00.0%")
            sys.stdout.flush()
            time.sleep(1)
            while self.p.printing:
                time.sleep(1)
                sys.stdout.write("\b\b\b\b\b%04.1f%%" % (100 * float(self.p.queueindex) / len(self.p.mainqueue),))
                sys.stdout.flush()
            self.p.send_now("M29 " + targetname)
            self.sleep(0.2)
            self.p.clear = 1
            self._do_ls(False)
            self.log("\b\b\b\b\b100%.")
            self.log(_("Upload completed. %s should now be on the card.") % targetname)
            return
        except:
            self.logError(_("...interrupted!"))
            self.p.pause()
            self.p.send_now("M29 " + targetname)
            time.sleep(0.2)
            self.p.clear = 1
            self.p.startprint(None)
            self.logError(_("A partial file named %s may have been written to the sd card.") % targetname)

    def complete_upload(self, text, line, begidx, endidx):
        s = line.split()
        if len(s) > 2:
            return []
        if (len(s) == 1 and line[-1] == " ") or (len(s) == 2 and line[-1] != " "):
            if len(s) > 1:
                return [i[len(s[1]) - len(text):] for i in glob.glob(s[1] + "*/") + glob.glob(s[1] + "*.g*")]
            else:
                return glob.glob("*/") + glob.glob("*.g*")

    def help_upload(self):
        self.log("Uploads a gcode file to the sd card")

    def help_print(self):
        if not self.fgcode:
            self.log(_("Send a loaded gcode file to the printer. Load a file with the load command first."))
        else:
            self.log(_("Send a loaded gcode file to the printer. You have %s loaded right now.") % self.filename)

    def do_print(self, l):
        if not self.fgcode:
            self.logError(_("No file loaded. Please use load first."))
            return
        if not self.p.online:
            self.logError(_("Not connected to printer."))
            return
        self.log(_("Printing %s") % self.filename)
        self.log(_("You can monitor the print with the monitor command."))
        self.p.startprint(self.fgcode)

    def do_pause(self, l):
        if self.sdprinting:
            self.p.send_now("M25")
        else:
            if not self.p.printing:
                self.logError(_("Not printing, cannot pause."))
                return
            self.p.pause()
        self.paused = True

    def help_pause(self):
        self.log(_("Pauses a running print"))

    def pause(self, event):
        return self.do_pause(None)

    def do_resume(self, l):
        if not self.paused:
            self.logError(_("Not paused, unable to resume. Start a print first."))
            return
        self.paused = False
        if self.sdprinting:
            self.p.send_now("M24")
            return
        else:
            self.p.resume()

    def help_resume(self):
        self.log(_("Resumes a paused print."))

    def emptyline(self):
        pass

    def do_shell(self, l):
        exec(l)

    def listfiles(self, line, echo = False):
        if "Begin file list" in line:
            self.listing = 1
        elif "End file list" in line:
            self.listing = 0
            self.recvlisteners.remove(self.listfiles)
            if echo:
                self.log(_("Files on SD card:"))
                self.log("\n".join(self.sdfiles))
        elif self.listing:
            self.sdfiles.append(line.strip().lower())

    def _do_ls(self, echo):
        # FIXME: this was 2, but I think it should rather be 0 as in do_upload
        self.listing = 0
        self.sdfiles = []
        self.recvlisteners.append(lambda l: self.listfiles(l, echo))
        self.p.send_now("M20")

    def do_ls(self, l):
        if not self.p.online:
            self.logError(_("Printer is not online. Please connect to it first."))
            return
        self._do_ls(True)

    def help_ls(self):
        self.log(_("Lists files on the SD card"))

    def waitforsdresponse(self, l):
        if "file.open failed" in l:
            self.logError(_("Opening file failed."))
            self.recvlisteners.remove(self.waitforsdresponse)
            return
        if "File opened" in l:
            self.log(l)
        if "File selected" in l:
            self.log(_("Starting print"))
            self.p.send_now("M24")
            self.sdprinting = 1
            #self.recvlisteners.remove(self.waitforsdresponse)
            return
        if "Done printing file" in l:
            self.log(l)
            self.sdprinting = 0
            self.recvlisteners.remove(self.waitforsdresponse)
            return
        if "SD printing byte" in l:
            #M27 handler
            try:
                resp = l.split()
                vals = resp[-1].split("/")
                self.percentdone = 100.0 * int(vals[0]) / int(vals[1])
            except:
                pass

    def do_reset(self, l):
        self.p.reset()

    def help_reset(self):
        self.log(_("Resets the printer."))

    def do_sdprint(self, l):
        if not self.p.online:
            self.log(_("Printer is not online. Please connect to it first."))
            return
        self._do_ls(False)
        while self.listfiles in self.recvlisteners:
            time.sleep(0.1)
        if l.lower() not in self.sdfiles:
            self.log(_("File is not present on card. Please upload it first."))
            return
        self.recvlisteners.append(self.waitforsdresponse)
        self.p.send_now("M23 " + l.lower())
        self.log(_("Printing file: %s from SD card.") % l.lower())
        self.log(_("Requesting SD print..."))
        time.sleep(1)

    def help_sdprint(self):
        self.log(_("Print a file from the SD card. Tab completes with available file names."))
        self.log(_("sdprint filename.g"))

    def complete_sdprint(self, text, line, begidx, endidx):
        if not self.sdfiles and self.p.online:
            self._do_ls(False)
            while self.listfiles in self.recvlisteners:
                time.sleep(0.1)
        if (len(line.split()) == 2 and line[-1] != " ") or (len(line.split()) == 1 and line[-1] == " "):
            return [i for i in self.sdfiles if i.startswith(text)]

    def recvcb(self, l):
        if "T:" in l:
            self.tempreadings = l
            self.status.update_tempreading(l)
        tstring = l.rstrip()
        if tstring != "ok" and not self.listing and not self.monitoring:
            if tstring[:5] == "echo:":
                tstring = tstring[5:].lstrip()
            if self.silent is False: print "\r" + tstring.ljust(15)
            sys.stdout.write(self.promptf())
            sys.stdout.flush()
        for i in self.recvlisteners:
            i(l)

    def startcb(self, resuming = False):
        self.starttime = time.time()
        if resuming:
            print _("Print resumed at: %s") % format_time(self.starttime)
        else:
            print _("Print started at: %s") % format_time(self.starttime)
            self.compute_eta = RemainingTimeEstimator(self.fgcode)

    def endcb(self):
        if self.p.queueindex == 0:
            print_duration = int(time.time() - self.starttime + self.extra_print_time)
            print _("Print ended at: %(end_time)s and took %(duration)s") % {"end_time": format_time(time.time()),
                                                                             "duration": format_duration(print_duration)}

            self.p.runSmallScript(self.endScript)

            if not self.settings.final_command:
                return
            run_command(self.settings.final_command,
                        {"$s": str(self.filename),
                         "$t": format_duration(print_duration)},
                        stderr = subprocess.STDOUT, stdout = subprocess.PIPE,
                        blocking = False)

    def layer_change_cb(self, newlayer):
        if self.compute_eta:
            secondselapsed = int(time.time() - self.starttime + self.extra_print_time)
            self.compute_eta.update_layer(newlayer, secondselapsed)

    def do_eta(self, l):
        if not self.p.printing:
            self.logError(_("Printer is not currently printing. No ETA available."))
        else:
            secondselapsed = int(time.time() - self.starttime + self.extra_print_time)
            secondsremain, secondsestimate = self.compute_eta(self.p.queueindex, secondselapsed)
            eta = _("Est: %s of %s remaining") % (format_duration(secondsremain),
                                                  format_duration(secondsestimate))
            self.log(eta.strip())

    def help_eta(self):
        self.log(_("Displays estimated remaining print time."))

    def help_shell(self):
        self.log("Executes a python command. Example:")
        self.log("! os.listdir('.')")

    def default(self, l):
        if l[0] in self.commandprefixes.upper():
            if self.p and self.p.online:
                if not self.p.loud:
                    self.log("SENDING:" + l)
                self.p.send_now(l)
            else:
                self.logError(_("Printer is not online."))
            return
        elif l[0] in self.commandprefixes.lower():
            if self.p and self.p.online:
                if not self.p.loud:
                    self.log("SENDING:" + l.upper())
                self.p.send_now(l.upper())
            else:
                self.logError(_("Printer is not online."))
            return
        elif l[0] == "@":
            if self.p and self.p.online:
                if not self.p.loud:
                    self.log("SENDING:" + l[1:])
                self.p.send_now(l[1:])
            else:
                self.logError(_("Printer is not online."))
            return
        else:
            cmd.Cmd.default(self, l)

    def tempcb(self, l):
        if "T:" in l:
            self.log(l.strip().replace("T", "Hotend").replace("B", "Bed").replace("ok ", ""))

    def do_gettemp(self, l):
        if "dynamic" in l:
            self.dynamic_temp = True
        if self.p.online:
            self.p.send_now("M105")
            time.sleep(0.75)
            if not self.status.bed_enabled:
                print "Hotend: %s/%s" % (self.status.extruder_temp, self.status.extruder_temp_target)
            else:
                print "Hotend: %s/%s" % (self.status.extruder_temp, self.status.extruder_temp_target)
                print "Bed:    %s/%s" % (self.status.bed_temp, self.status.bed_temp_target)

    def help_gettemp(self):
        self.log(_("Read the extruder and bed temperature."))

    def do_settemp(self, l):
        l = l.lower().replace(", ", ".")
        for i in self.temps.keys():
            l = l.replace(i, self.temps[i])
        try:
            f = float(l)
        except:
            self.logError(_("You must enter a temperature."))
            return

        if f >= 0:
            if f > 250:
                print _("%s is a high temperature to set your extruder to. Are you sure you want to do that?") % f
                if not self.confirm():
                    return
            if self.p.online:
                self.p.send_now("M104 S" + l)
                self.log(_("Setting hotend temperature to %s degrees Celsius.") % f)
            else:
                self.logError(_("Printer is not online."))
        else:
            self.logError(_("You cannot set negative temperatures. To turn the hotend off entirely, set its temperature to 0."))

    def help_settemp(self):
        self.log(_("Sets the hotend temperature to the value entered."))
        self.log(_("Enter either a temperature in celsius or one of the following keywords"))
        self.log(", ".join([i + "(" + self.temps[i] + ")" for i in self.temps.keys()]))

    def complete_settemp(self, text, line, begidx, endidx):
        if (len(line.split()) == 2 and line[-1] != " ") or (len(line.split()) == 1 and line[-1] == " "):
            return [i for i in self.temps.keys() if i.startswith(text)]

    def do_bedtemp(self, l):
        f = None
        try:
            l = l.lower().replace(", ", ".")
            for i in self.bedtemps.keys():
                l = l.replace(i, self.bedtemps[i])
            f = float(l)
        except:
            self.logError(_("You must enter a temperature."))
        if f is not None and f >= 0:
            if self.p.online:
                self.p.send_now("M140 S" + l)
                self.log(_("Setting bed temperature to %s degrees Celsius.") % f)
            else:
                self.logError(_("Printer is not online."))
        else:
            self.logError(_("You cannot set negative temperatures. To turn the bed off entirely, set its temperature to 0."))

    def help_bedtemp(self):
        self.log(_("Sets the bed temperature to the value entered."))
        self.log(_("Enter either a temperature in celsius or one of the following keywords"))
        self.log(", ".join([i + "(" + self.bedtemps[i] + ")" for i in self.bedtemps.keys()]))

    def complete_bedtemp(self, text, line, begidx, endidx):
        if (len(line.split()) == 2 and line[-1] != " ") or (len(line.split()) == 1 and line[-1] == " "):
            return [i for i in self.bedtemps.keys() if i.startswith(text)]

    def do_tool(self, l):
        tool = None
        try:
            tool = int(l.lower().strip())
        except:
            self.logError(_("You must specify the tool index as an integer."))
        if tool is not None and tool >= 0:
            if self.p.online:
                self.p.send_now("T%d" % tool)
                self.log(_("Using tool %d.") % tool)
            else:
                self.logError(_("Printer is not online."))
        else:
            self.logError(_("You cannot set negative tool numbers."))

    def help_tool(self):
        self.log(_("Switches to the specified tool (e.g. doing tool 1 will emit a T1 G-Code)."))

    def do_move(self, l):
        if(len(l.split()) < 2):
            self.logError(_("No move specified."))
            return
        if self.p.printing:
            self.logError(_("Printer is currently printing. Please pause the print before you issue manual commands."))
            return
        if not self.p.online:
            self.logError(_("Printer is not online. Unable to move."))
            return
        l = l.split()
        if(l[0].lower() == "x"):
            feed = self.settings.xy_feedrate
            axis = "X"
        elif(l[0].lower() == "y"):
            feed = self.settings.xy_feedrate
            axis = "Y"
        elif(l[0].lower() == "z"):
            feed = self.settings.z_feedrate
            axis = "Z"
        elif(l[0].lower() == "e"):
            feed = self.settings.e_feedrate
            axis = "E"
        else:
            self.logError(_("Unknown axis."))
            return
        try:
            float(l[1])  # check if distance can be a float
        except:
            self.logError(_("Invalid distance"))
            return
        try:
            feed = int(l[2])
        except:
            pass
        self.p.send_now("G91")
        self.p.send_now("G1 " + axis + str(l[1]) + " F" + str(feed))
        self.p.send_now("G90")

    def help_move(self):
        self.log(_("Move an axis. Specify the name of the axis and the amount. "))
        self.log(_("move X 10 will move the X axis forward by 10mm at %s mm/min (default XY speed)") % self.settings.xy_feedrate)
        self.log(_("move Y 10 5000 will move the Y axis forward by 10mm at 5000mm/min"))
        self.log(_("move Z -1 will move the Z axis down by 1mm at %s mm/min (default Z speed)") % self.settings.z_feedrate)
        self.log(_("Common amounts are in the tabcomplete list."))

    def complete_move(self, text, line, begidx, endidx):
        if (len(line.split()) == 2 and line[-1] != " ") or (len(line.split()) == 1 and line[-1] == " "):
            return [i for i in ["X ", "Y ", "Z ", "E "] if i.lower().startswith(text)]
        elif(len(line.split()) == 3 or (len(line.split()) == 2 and line[-1] == " ")):
            base = line.split()[-1]
            rlen = 0
            if base.startswith("-"):
                rlen = 1
            if line[-1] == " ":
                base = ""
            return [i[rlen:] for i in ["-100", "-10", "-1", "-0.1", "100", "10", "1", "0.1", "-50", "-5", "-0.5", "50", "5", "0.5", "-200", "-20", "-2", "-0.2", "200", "20", "2", "0.2"] if i.startswith(base)]
        else:
            return []

    def do_extrude(self, l, override = None, overridefeed = 300):
        length = self.settings.default_extrusion  # default extrusion length
        feed = self.settings.e_feedrate  # default speed
        if not self.p.online:
            self.logError("Printer is not online. Unable to extrude.")
            return
        if self.p.printing:
            self.logError(_("Printer is currently printing. Please pause the print before you issue manual commands."))
            return
        ls = l.split()
        if len(ls):
            try:
                length = float(ls[0])
            except:
                self.logError(_("Invalid length given."))
        if len(ls) > 1:
            try:
                feed = int(ls[1])
            except:
                self.logError(_("Invalid speed given."))
        if override is not None:
            length = override
            feed = overridefeed
        self.do_extrude_final(length, feed)

    def do_extrude_final(self, length, feed):
        if length > 0:
            self.log(_("Extruding %fmm of filament.") % (length,))
        elif length < 0:
            self.log(_("Reversing %fmm of filament.") % (-length,))
        else:
            self.log(_("Length is 0, not doing anything."))
        self.p.send_now("G91")
        self.p.send_now("G1 E" + str(length) + " F" + str(feed))
        self.p.send_now("G90")

    def help_extrude(self):
        self.log(_("Extrudes a length of filament, 5mm by default, or the number of mm given as a parameter"))
        self.log(_("extrude - extrudes 5mm of filament at 300mm/min (5mm/s)"))
        self.log(_("extrude 20 - extrudes 20mm of filament at 300mm/min (5mm/s)"))
        self.log(_("extrude -5 - REVERSES 5mm of filament at 300mm/min (5mm/s)"))
        self.log(_("extrude 10 210 - extrudes 10mm of filament at 210mm/min (3.5mm/s)"))

    def do_reverse(self, l):
        length = self.settings.default_extrusion  # default extrusion length
        feed = self.settings.e_feedrate  # default speed
        if not self.p.online:
            self.logError(_("Printer is not online. Unable to reverse."))
            return
        if self.p.printing:
            self.logError(_("Printer is currently printing. Please pause the print before you issue manual commands."))
            return
        ls = l.split()
        if len(ls):
            try:
                length = float(ls[0])
            except:
                self.logError(_("Invalid length given."))
        if len(ls) > 1:
            try:
                feed = int(ls[1])
            except:
                self.logError(_("Invalid speed given."))
        self.do_extrude("", -length, feed)

    def help_reverse(self):
        self.log(_("Reverses the extruder, 5mm by default, or the number of mm given as a parameter"))
        self.log(_("reverse - reverses 5mm of filament at 300mm/min (5mm/s)"))
        self.log(_("reverse 20 - reverses 20mm of filament at 300mm/min (5mm/s)"))
        self.log(_("reverse 10 210 - extrudes 10mm of filament at 210mm/min (3.5mm/s)"))
        self.log(_("reverse -5 - EXTRUDES 5mm of filament at 300mm/min (5mm/s)"))

    def do_exit(self, l):
        if self.status.extruder_temp_target != 0:
            print "Setting extruder temp to 0"
        self.p.send_now("M104 S0.0")
        if self.status.bed_enabled:
            if self.status.bed_temp_taret != 0:
                print "Setting bed temp to 0"
            self.p.send_now("M140 S0.0")
        self.log("Disconnecting from printer...")
        if self.p.printing:
            print "Are you sure you want to exit while printing?"
            print "(this will terminate the print)."
            if not self.confirm():
                return
        self.log(_("Exiting program. Goodbye!"))
        self.p.disconnect()
        sys.exit()

    def help_exit(self):
        self.log(_("Disconnects from the printer and exits the program."))

    def do_monitor(self, l):
        interval = 5
        if not self.p.online:
            self.logError(_("Printer is not online. Please connect to it first."))
            return
        if not (self.p.printing or self.sdprinting):
            self.logError(_("Printer is not printing. Please print something before monitoring."))
            return
        self.log(_("Monitoring printer, use ^C to interrupt."))
        if len(l):
            try:
                interval = float(l)
            except:
                self.logError(_("Invalid period given."))
        self.log(_("Updating values every %f seconds.") % (interval,))
        self.monitoring = 1
        prev_msg_len = 0
        try:
            while True:
                self.p.send_now("M105")
                if self.sdprinting:
                    self.p.send_now("M27")
                time.sleep(interval)
                #print (self.tempreadings.replace("\r", "").replace("T", "Hotend").replace("B", "Bed").replace("\n", "").replace("ok ", ""))
                if self.p.printing:
                    preface = _("Print progress: ")
                    progress = 100 * float(self.p.queueindex) / len(self.p.mainqueue)
                elif self.sdprinting:
                    preface = _("Print progress: ")
                    progress = self.percentdone
                prev_msg = preface + "%.1f%%" % progress
                if self.silent is False:
                    sys.stdout.write("\r" + prev_msg.ljust(prev_msg_len))
                    sys.stdout.flush()
                prev_msg_len = len(prev_msg)
        except KeyboardInterrupt:
            if self.silent is False: print _("Done monitoring.")
        self.monitoring = 0

    def help_monitor(self):
        self.log(_("Monitor a machine's temperatures and an SD print's status."))
        self.log(_("monitor - Reports temperature and SD print status (if SD printing) every 5 seconds"))
        self.log(_("monitor 2 - Reports temperature and SD print status (if SD printing) every 2 seconds"))

    def expandcommand(self, c):
        return c.replace("$python", sys.executable)

    def do_skein(self, l):
        l = l.split()
        if len(l) == 0:
            self.logError(_("No file name given."))
            return
        settings = 0
        if l[0] == "set":
            settings = 1
        else:
            self.log(_("Skeining file: %s") % l[0])
            if not(os.path.exists(l[0])):
                self.logError(_("File not found!"))
                return
        try:
            if settings:
                command = self.settings.sliceoptscommand
                self.log(_("Entering slicer settings: %s") % command)
                run_command(command, blocking = True)
            else:
                command = self.settings.slicecommand
                self.log(_("Slicing: ") % command)
                stl_name = l[0]
                gcode_name = stl_name.replace(".stl", "_export.gcode").replace(".STL", "_export.gcode")
                run_command(command,
                            {"$s": stl_name,
                             "$o": gcode_name},
                            blocking = True)
                self.log(_("Loading sliced file."))
                self.do_load(l[0].replace(".stl", "_export.gcode"))
        except Exception, e:
            self.logError(_("Slicing failed: %s") % e)

    def complete_skein(self, text, line, begidx, endidx):
        s = line.split()
        if len(s) > 2:
            return []
        if (len(s) == 1 and line[-1] == " ") or (len(s) == 2 and line[-1] != " "):
            if len(s) > 1:
                return [i[len(s[1]) - len(text):] for i in glob.glob(s[1] + "*/") + glob.glob(s[1] + "*.stl")]
            else:
                return glob.glob("*/") + glob.glob("*.stl")

    def help_skein(self):
        self.log(_("Creates a gcode file from an stl model using the slicer (with tab-completion)"))
        self.log(_("skein filename.stl - create gcode file"))
        self.log(_("skein filename.stl view - create gcode file and view using skeiniso"))
        self.log(_("skein set - adjust slicer settings"))

    def do_home(self, l):
        if not self.p.online:
            self.logError(_("Printer is not online. Unable to move."))
            return
        if self.p.printing:
            self.logError(_("Printer is currently printing. Please pause the print before you issue manual commands."))
            return
        if "x" in l.lower():
            self.p.send_now("G28 X0")
        if "y" in l.lower():
            self.p.send_now("G28 Y0")
        if "z" in l.lower():
            self.p.send_now("G28 Z0")
        if "e" in l.lower():
            self.p.send_now("G92 E0")
        if not len(l):
            self.p.send_now("G28")
            self.p.send_now("G92 E0")

    def help_home(self):
        self.log(_("Homes the printer"))
        self.log(_("home - homes all axes and zeroes the extruder(Using G28 and G92)"))
        self.log(_("home xy - homes x and y axes (Using G28)"))
        self.log(_("home z - homes z axis only (Using G28)"))
        self.log(_("home e - set extruder position to zero (Using G92)"))
        self.log(_("home xyze - homes all axes and zeroes the extruder (Using G28 and G92)"))

    def do_off(self, l):
        self.off()

    def off(self, ignore = None):
        if self.p.online:
            if self.p.printing: self.pause(None)
            self.log(_("; Motors off"))
            self.onecmd("M84")
            self.log(_("; Extruder off"))
            self.onecmd("M104 S0")
            self.log(_("; Heatbed off"))
            self.onecmd("M140 S0")
            self.log(_("; Fan off"))
            self.onecmd("M107")
            self.log(_("; Power supply off"))
            self.onecmd("M81")
        else:
            self.logError(_("Printer is not online. Unable to turn it off."))

    def help_off(self):
        self.log(_("Turns off everything on the printer"))

    def add_cmdline_arguments(self, parser):
        parser.add_argument('-c', '--conf', '--config', help = _("load this file on startup instead of .pronsolerc ; you may chain config files, if so settings auto-save will use the last specified file"), action = "append", default = [])
        parser.add_argument('-e', '--execute', help = _("executes command after configuration/.pronsolerc is loaded ; macros/settings from these commands are not autosaved"), action = "append", default = [])
        parser.add_argument('filename', nargs='?', help = _("file to load"))

    def process_cmdline_arguments(self, args):
        for config in args.conf:
            self.load_rc(config)
        if not self.rc_loaded:
            self.load_default_rc()
        self.processing_args = True
        for command in args.execute:
            self.onecmd(command)
        self.processing_args = False
        if args.filename:
            filename = args.filename.decode(locale.getpreferredencoding())
            self.cmdline_filename_callback(filename)

    def cmdline_filename_callback(self, filename):
        self.do_load(filename)

    def parse_cmdline(self, args):
        parser = argparse.ArgumentParser(description = 'Printrun 3D printer interface')
        self.add_cmdline_arguments(parser)
        args = [arg for arg in args if not arg.startswith("-psn")]
        args = parser.parse_args(args = args)
        self.process_cmdline_arguments(args)

    def update_build_dimensions(self, param, value):
        self.build_dimensions_list = parse_build_dimensions(value)
        self.p.analyzer.home_pos = get_home_pos(self.build_dimensions_list)

    # We replace this function, defined in cmd.py .
    # It's default behavior with reagrds to Ctr-C
    # and Ctr-D doesn't make much sense...

    def cmdloop(self, intro=None):
        """Repeatedly issue a prompt, accept input, parse an initial prefix
        off the received input, and dispatch to action methods, passing them
        the remainder of the line as argument.

        """

        self.preloop()
        if self.use_rawinput and self.completekey:
            try:
                import readline
                self.old_completer = readline.get_completer()
                readline.set_completer(self.complete)
                readline.parse_and_bind(self.completekey + ": complete")
            except ImportError:
                pass
        try:
            if intro is not None:
                self.intro = intro
            if self.intro:
                self.stdout.write(str(self.intro) + "\n")
            stop = None
            while not stop:
                if self.cmdqueue:
                    line = self.cmdqueue.pop(0)
                else:
                    if self.use_rawinput:
                        try:
                            line = raw_input(self.prompt)
                        except EOFError:
                            print ""
                            self.do_exit("")
                        except KeyboardInterrupt:
                            print ""
                            line = ""
                    else:
                        self.stdout.write(self.prompt)
                        self.stdout.flush()
                        line = self.stdin.readline()
                        if not len(line):
                            line = ""
                        else:
                            line = line.rstrip('\r\n')
                line = self.precmd(line)
                stop = self.onecmd(line)
                stop = self.postcmd(stop, line)
            self.postloop()
        finally:
            if self.use_rawinput and self.completekey:
                try:
                    import readline
                    readline.set_completer(self.old_completer)
                except ImportError:
                    pass
