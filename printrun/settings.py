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

import logging
import traceback
import os
import sys

from functools import wraps

from .utils import parse_build_dimensions

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
        if self.default != "":
            deftxt = _("Default: ")
            resethelp = _("(Control-doubleclick to reset to default value)")
            if len(repr(self.default)) > 10:
                deftxt += "\n    " + repr(self.default).strip("'") + "\n" + resethelp
            else:
                deftxt += repr(self.default) + "  " + resethelp
        helptxt += sep + deftxt
        if len(helptxt):
            widget.SetToolTip(helptxt)
        return widget
    return decorator

class Setting:

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

    def validate(self, value): pass

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

    def set_default(self, e):
        if e.CmdDown() and e.ButtonDClick() and self.default != "":
            self.widget.SetValue(self.default)
        else:
            e.Skip()

class StringSetting(wxSetting):

    def get_specific_widget(self, parent):
        import wx
        self.widget = wx.TextCtrl(parent, -1, str(self.value))
        return self.widget

def wxColorToStr(color, withAlpha = True):
    # including Alpha seems to be non standard in CSS
    format = '#{0.red:02X}{0.green:02X}{0.blue:02X}' \
        + ('{0.alpha:02X}' if withAlpha else '')
    return format.format(color)

class ColorSetting(wxSetting):
    def __init__(self, name, default, label = None, help = None, group = None, isRGBA=True):
        super().__init__(name, default, label, help, group)
        self.isRGBA = isRGBA

    def validate(self, value):
        from .utils import check_rgb_color, check_rgba_color
        validate = check_rgba_color if self.isRGBA else check_rgb_color
        validate(value)

    def get_specific_widget(self, parent):
        import wx
        self.widget = wx.ColourPickerCtrl(parent, colour=wx.Colour(self.value), style=wx.CLRP_USE_TEXTCTRL)
        self.widget.SetValue = self.widget.SetColour
        self.widget.LayoutDirection = wx.Layout_RightToLeft
        return self.widget
    def update(self):
        self._value = wxColorToStr(self.widget.Colour, self.isRGBA)

class ComboSetting(wxSetting):

    def __init__(self, name, default, choices, label = None, help = None, group = None):
        super(ComboSetting, self).__init__(name, default, label, help, group)
        self.choices = choices

    def get_specific_widget(self, parent):
        import wx
        readonly = isinstance(self.choices, tuple)
        if readonly:
            # wx.Choice drops its list on click, no need to click down arrow
            # which is far to the right because of wx.EXPAND
            self.widget = wx.Choice(parent, -1, choices = self.choices)
            self.widget.GetValue = lambda: self.choices[self.widget.Selection]
            self.widget.SetValue = lambda v: self.widget.SetSelection(self.choices.index(v))
            self.widget.SetValue(self.value)
        else:
            self.widget = wx.ComboBox(parent, -1, str(self.value), choices = self.choices, style = wx.CB_DROPDOWN)
        return self.widget

class SpinSetting(wxSetting):

    def __init__(self, name, default, min, max, label = None, help = None, group = None, increment = 0.1):
        super().__init__(name, default, label, help, group)
        self.min = min
        self.max = max
        self.increment = increment

    def get_specific_widget(self, parent):
        import wx
        self.widget = wx.SpinCtrlDouble(parent, -1, min = self.min, max = self.max)
        self.widget.SetDigits(0)
        self.widget.SetValue(self.value)
        orig = self.widget.GetValue
        self.widget.GetValue = lambda: int(orig())
        return self.widget

def MySpin(parent, digits, *args, **kw):
    # in GTK 3.[01], spinner is not large enough to fit text
    # Could be a class, but use function to avoid load errors if wx
    # not installed
    # If native wx.SpinCtrlDouble has problems in different platforms
    # try agw
    # from wx.lib.agw.floatspin import FloatSpin
    import wx
    sp = wx.SpinCtrlDouble(parent, *args, **kw)
    # sp = FloatSpin(parent)
    sp.SetDigits(digits)
    # sp.SetValue(kw['initial'])
    def fitValue(ev):
        text = '%%.%df'% digits % sp.Max
        # native wx.SpinCtrlDouble does not return good size
        # in GTK 3.0
        tex = sp.GetTextExtent(text)
        tsz = sp.GetSizeFromTextSize(tex.x)

        if sp.MinSize.x < tsz.x:
            # print('fitValue', getattr(sp, 'setting', None), sp.Value, sp.Digits, tsz.x)
            sp.MinSize = tsz
            # sp.Size = tsz
    # sp.Bind(wx.EVT_TEXT, fitValue)
    fitValue(None)
    return sp

class FloatSpinSetting(SpinSetting):

    def get_specific_widget(self, parent):
        self.widget = MySpin(parent, 2, initial = self.value, min = self.min, max = self.max, inc = self.increment)
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
        def w(val, m, M):
            self.widgets.append(MySpin(parent, 2, initial = val, min = m, max = M))
        def addlabel(name, pos):
            self.widget.Add(wx.StaticText(parent, -1, name), pos = pos, flag = wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, border = 5)
        def addwidget(*pos):
            self.widget.Add(self.widgets[-1], pos = pos, flag = wx.RIGHT | wx.EXPAND, border = 5)
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
        addwidget(2, 1)
        addlabel(_("Y home pos."), (2, 2))
        w(build_dimensions[7], -2000, 2000)
        addwidget(2, 3)
        addlabel(_("Z home pos."), (2, 4))
        w(build_dimensions[8], -2000, 2000)
        addwidget(2, 5)
        return self.widget

    def update(self):
        values = [float(w.GetValue()) for w in self.widgets]
        self.value = "%.02fx%.02fx%.02f%+.02f%+.02f%+.02f%+.02f%+.02f%+.02f" % tuple(values)

class Settings:
    def __baudrate_list(self): return ["2400", "9600", "19200", "38400", "57600", "115200", "250000"]

    def __init__(self, root):
        # defaults here.
        # the initial value determines the type
        self._add(StringSetting("port", "", _("Serial port"), _("Port used to communicate with printer")))
        self._add(ComboSetting("baudrate", 115200, self.__baudrate_list(), _("Baud rate"), _("Communications Speed")))
        self._add(BooleanSetting("tcp_streaming_mode", False, _("TCP streaming mode"), _("When using a TCP connection to the printer, the streaming mode will not wait for acks from the printer to send new commands. This will break things such as ETA prediction, but can result in smoother prints.")), root.update_tcp_streaming_mode)
        self._add(BooleanSetting("rpc_server", True, _("RPC server"), _("Enable RPC server to allow remotely querying print status")), root.update_rpc_server)
        self._add(BooleanSetting("dtr", True, _("DTR"), _("Disabling DTR would prevent Arduino (RAMPS) from resetting upon connection"), "Printer"))
        if sys.platform != "win32":
            self._add(StringSetting("devicepath", "", _("Device name pattern"), _("Custom device pattern: for example /dev/3DP_* "), "Printer"))
        self._add(SpinSetting("bedtemp_abs", 110, 0, 400, _("Bed temperature for ABS"), _("Heated Build Platform temp for ABS (deg C)"), "Printer"), root.set_temp_preset)
        self._add(SpinSetting("bedtemp_pla", 60, 0, 400, _("Bed temperature for PLA"), _("Heated Build Platform temp for PLA (deg C)"), "Printer"), root.set_temp_preset)
        self._add(SpinSetting("temperature_abs", 230, 0, 400, _("Extruder temperature for ABS"), _("Extruder temp for ABS (deg C)"), "Printer"), root.set_temp_preset)
        self._add(SpinSetting("temperature_pla", 185, 0, 400, _("Extruder temperature for PLA"), _("Extruder temp for PLA (deg C)"), "Printer"), root.set_temp_preset)
        self._add(SpinSetting("xy_feedrate", 3000, 0, 50000, _("X && Y manual feedrate"), _("Feedrate for Control Panel Moves in X and Y (mm/min)"), "Printer"))
        self._add(SpinSetting("z_feedrate", 100, 0, 50000, _("Z manual feedrate"), _("Feedrate for Control Panel Moves in Z (mm/min)"), "Printer"))
        self._add(SpinSetting("e_feedrate", 100, 0, 1000, _("E manual feedrate"), _("Feedrate for Control Panel Moves in Extrusions (mm/min)"), "Printer"))
        defaultslicerpath = ""
        if getattr(sys, 'frozen', False):
            if sys.platform == "darwin":
                defaultslicerpath = "/Applications/Slic3r.app/Contents/MacOS/"
            elif sys.platform == "win32":
                defaultslicerpath = ".\\slic3r\\"
        self._add(StringSetting("slicecommandpath", defaultslicerpath, _("Path to slicer"), _("Path to slicer"), "External"))
        slicer = 'slic3r-console' if sys.platform == 'win32' else 'slic3r'
        self._add(StringSetting("slicecommand", slicer + ' $s --output $o', _("Slice command"), _("Slice command"), "External"))
        self._add(StringSetting("sliceoptscommand", "slic3r", _("Slicer options command"), _("Slice settings command"), "External"))
        self._add(StringSetting("start_command", "", _("Start command"), _("Executable to run when the print is started"), "External"))
        self._add(StringSetting("final_command", "", _("Final command"), _("Executable to run when the print is finished"), "External"))
        self._add(StringSetting("error_command", "", _("Error command"), _("Executable to run when an error occurs"), "External"))
        self._add(StringSetting("log_path", "", _("Log path"), _("Path to the log file. An empty path will log to the console."), "UI"))

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
        self._add(HiddenSetting("total_filament_used", 0.0))
        self._add(HiddenSetting("spool_list", ""))

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

    def _add(self, setting, callback = None,
             alias = None, autocomplete_list = None):
        setattr(self, setting.name, setting)
        if callback:
            setattr(self, "__" + setting.name + "_cb", callback)
        if alias:
            setattr(self, "__" + setting.name + "_alias", alias)
        if autocomplete_list:
            setattr(self, "__" + setting.name + "_list", autocomplete_list)

    def _set(self, key, value):
        try:
            value = getattr(self, "__%s_alias" % key)()[value]
        except KeyError:
            pass
        except AttributeError:
            pass
        setting = getattr(self, '_'+key)
        setting.validate(value)
        t = type(getattr(self, key))
        if t == bool and value == "False":
            value = False
        setattr(self, key, t(value))
        try:
            cb = getattr(self, "__%s_cb" % key, None)
            if cb is not None:
                cb(key, value)
        except:
            logging.warning((_("Failed to run callback after setting \"%s\":") % key) +
                            "\n" + traceback.format_exc())
        return value

    def _tabcomplete(self, key):
        try:
            return getattr(self, "__%s_list" % key)()
        except AttributeError:
            pass
        try:
            return list(getattr(self, "__%s_alias" % key)().keys())
        except AttributeError:
            pass
        return []

    def _all_settings(self):
        return self._settings
