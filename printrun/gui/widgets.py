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

import wx
import re
import platform

def get_space(a):
    '''
    Takes key (str), returns spacing value (int).
    Provides correct spacing in pixel for borders and sizers.
    '''
    match a:
        case 'major':  # e.g. outer border of dialog boxes
            return 12
        case 'minor':  # e.g. border of inner elements
            return 8
        case 'mini':
            return 4
        case 'stddlg':
            # Differentiation is necessary because wxPython behaves slightly differently on different systems.
            platformname = platform.system()
            if platformname == 'Windows':
                return 8
            if platformname == 'Darwin':
                return 4
            return 4  # Linux systems
        case 'stddlg-frame':
            # Border for std dialog buttons when used with frames.
            platformname = platform.system()
            if platformname == 'Windows':
                return 8
            if platformname == 'Darwin':
                return 12
            return 8  # Linux systems
        case 'staticbox':
            # Border between StaticBoxSizers and the elements inside.
            platformname = platform.system()
            if platformname == 'Windows':
                return 4
            if platformname == 'Darwin':
                return 0
            return 0  # Linux systems
        case 'none':
            return 0

class MacroEditor(wx.Dialog):
    """Really simple editor to edit macro definitions"""

    def __init__(self, macro_name, definition, callback, gcode = False):
        self.indent_chars = "  "
        title = "  Macro %s"
        if gcode:
            title = "  %s"
        self.gcode = gcode
        wx.Dialog.__init__(self, None, title = title % macro_name,
                           style = wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.callback = callback
        panel = wx.Panel(self)
        panelsizer = wx.BoxSizer(wx.VERTICAL)
        titlesizer = wx.BoxSizer(wx.HORIZONTAL)
        self.titletext = wx.StaticText(panel, -1, "              _")  # title%macro_name)
        titlesizer.Add(self.titletext, 1, wx.ALIGN_CENTER_VERTICAL)
        self.findbtn = wx.Button(panel, -1, _(" Find "), style = wx.BU_EXACTFIT)  # New button for "Find" (Jezmy)
        self.findbtn.Bind(wx.EVT_BUTTON, self.on_find)
        self.Bind(wx.EVT_FIND, self.on_find_find)
        self.Bind(wx.EVT_FIND_NEXT, self.on_find_find)
        self.Bind(wx.EVT_FIND_CLOSE, self.on_find_cancel)
        self.Bind(wx.EVT_CLOSE, self.close)
        titlesizer.Add(self.findbtn, 0, wx.ALIGN_CENTER_VERTICAL)
        panelsizer.Add(titlesizer, 0, wx.EXPAND | wx.ALL, get_space('minor'))
        self.e = wx.TextCtrl(panel, style = wx.HSCROLL | wx.TE_MULTILINE | wx.TE_RICH2, size = (400, 400))
        if not self.gcode:
            self.e.SetValue(self.unindent(definition))
        else:
            self.e.SetValue("\n".join(definition))
        panelsizer.Add(self.e, 1, wx.EXPAND)
        panel.SetSizer(panelsizer)
        topsizer = wx.BoxSizer(wx.VERTICAL)
        topsizer.Add(panel, 1, wx.EXPAND | wx.ALL, get_space('none'))
        # No StaticLine in this case bc the TextCtrl acts as a divider
        btnsizer = wx.StdDialogButtonSizer()
        self.savebtn = wx.Button(self, wx.ID_SAVE)
        self.savebtn.SetDefault()
        self.savebtn.Bind(wx.EVT_BUTTON, self.save)
        self.cancelbtn = wx.Button(self, wx.ID_CANCEL)
        self.cancelbtn.Bind(wx.EVT_BUTTON, self.close)
        btnsizer.AddButton(self.savebtn)
        btnsizer.AddButton(self.cancelbtn)
        btnsizer.Realize()
        topsizer.Add(btnsizer, 0, wx.ALIGN_RIGHT | wx.ALL, get_space('stddlg'))
        self.SetSizer(topsizer)
        self.SetMinClientSize((230, 150))  # TODO: Check if self.FromDIP() is needed
        topsizer.Fit(self)
        self.CentreOnParent()
        self.Show()
        self.e.SetFocus()

    def on_find(self, ev):
        # Ask user what to look for, find it and point at it ...  (Jezmy)
        self.findbtn.Disable()
        self.finddata = wx.FindReplaceData(wx.FR_DOWN)   # initializes and holds search parameters
        selection = self.e.GetStringSelection()
        if selection:
            self.finddata.SetFindString(selection)
        self.finddialog = wx.FindReplaceDialog(self.e, self.finddata, _("Find..."), wx.FR_NOWHOLEWORD)  # wx.FR_REPLACEDIALOG
        # TODO: Setup ReplaceDialog, Setup WholeWord Search, deactivated for now...
        self.finddialog.Show()

    def on_find_cancel(self, ev):
        self.findbtn.Enable()
        self.titletext.SetLabel("              _")
        self.finddialog.Destroy()

    def on_find_find(self, ev):
        findstring = self.finddata.GetFindString()
        macrocode = self.e.GetValue()

        if self.e.GetStringSelection().lower() == findstring.lower():
            # If the desired string is already selected, change the position to jump to the next one.
            if self.finddata.GetFlags() % 2 == 1:
                self.e.SetInsertionPoint(self.e.GetInsertionPoint() + len(findstring))
            else:
                self.e.SetInsertionPoint(self.e.GetInsertionPoint() - len(findstring))

        if int(self.finddata.GetFlags() / 4) != 1:
            # When search is not case-sensitve, convert the whole string to lowercase
            findstring = findstring.casefold()
            macrocode = macrocode.casefold()

        # The user can choose to search upwards or downwards
        if self.finddata.GetFlags() % 2 == 1:
            stringpos = macrocode.find(findstring, self.e.GetInsertionPoint())
        else:
            stringpos = macrocode.rfind(findstring, 0, self.e.GetInsertionPoint())

        if stringpos == -1 and self.finddata.GetFlags() % 2 == 1:
            self.titletext.SetLabel(_("End of macro, jumped to first line"))
            stringpos = 0  # jump to the beginning
            self.e.SetInsertionPoint(stringpos)
            self.e.ShowPosition(stringpos)
        elif stringpos == -1 and self.finddata.GetFlags() % 2 == 0:
            self.titletext.SetLabel(_("Begin of macro, jumped to last line"))
            stringpos = self.e.GetLastPosition()  # jump to the end
            self.e.SetInsertionPoint(stringpos)
            self.e.ShowPosition(stringpos)
        else:
            # TODO: Implement a Not Found state when no single match was found
            self.titletext.SetLabel(_("Found!"))
            self.e.SetSelection(stringpos, stringpos + len(findstring))
            self.e.ShowPosition(stringpos)

    def ShowMessage(self, ev, message):
        dlg = wx.MessageDialog(self, message,
                               "Info!", wx.OK | wx.ICON_INFORMATION)
        dlg.ShowModal()
        dlg.Destroy()

    def save(self, ev):
        self.Destroy()
        if not self.gcode:
            self.callback(self.reindent(self.e.GetValue()))
        else:
            self.callback(self.e.GetValue().split("\n"))

    def close(self, ev):
        self.Destroy()

    def unindent(self, text):
        self.indent_chars = text[:len(text) - len(text.lstrip())]
        if len(self.indent_chars) == 0:
            self.indent_chars = "  "
        unindented = ""
        lines = re.split(r"(?:\r\n?|\n)", text)
        if len(lines) <= 1:
            return text
        for line in lines:
            if line.startswith(self.indent_chars):
                unindented += line[len(self.indent_chars):] + "\n"
            else:
                unindented += line + "\n"
        return unindented

    def reindent(self, text):
        lines = re.split(r"(?:\r\n?|\n)", text)
        if len(lines) <= 1:
            return text
        reindented = ""
        for line in lines:
            if line.strip() != "":
                reindented += self.indent_chars + line + "\n"
        return reindented


SETTINGS_GROUPS = {"Printer": _("Printer settings"),
                   "UI": _("User interface"),
                   "Viewer": _("Viewer"),
                   "Colors": _("Colors"),
                   "External": _("External commands")}

class PronterOptionsDialog(wx.Dialog):
    """Options editor"""
    def __init__(self, pronterface):
        wx.Dialog.__init__(self, parent = None, title = _("Edit settings"),
                           size = wx.DefaultSize, style = wx.DEFAULT_DIALOG_STYLE)
        self.notebook = notebook = wx.Notebook(self)
        all_settings = pronterface.settings._all_settings()
        group_list = []
        groups = {}
        for group in ["Printer", "UI", "Viewer", "Colors", "External"]:
            group_list.append(group)
            groups[group] = []
        for setting in all_settings:
            if setting.group not in group_list:
                group_list.append(setting.group)
                groups[setting.group] = []
            groups[setting.group].append(setting)
        for group in group_list:
            grouppanel = wx.ScrolledWindow(notebook, -1, style = wx.VSCROLL)
            # Setting the scrollrate based on the systemfont
            fontsize = wx.SystemSettings.GetFont(wx.SYS_SYSTEM_FONT).GetPixelSize()
            grouppanel.SetScrollRate(fontsize.x, fontsize.y)
            notebook.AddPage(grouppanel, SETTINGS_GROUPS[group])
            settings = groups[group]
            grid = wx.GridBagSizer(hgap = get_space('minor'), vgap = get_space('mini'))
            current_row = 0
            # This gives the first entry on the page a tiny bit of extra space to the top
            grid.Add((12, get_space('mini')), pos = (current_row, 0), span = (1, 2))
            current_row += 1
            for setting in settings:
                if setting.name.startswith("separator_"):
                    sep = wx.StaticLine(grouppanel, size = (-1, 5), style = wx.LI_HORIZONTAL)
                    grid.Add(sep, pos = (current_row, 0), span = (1, 2),
                             border = get_space('mini'), flag = wx.ALIGN_CENTER | wx.ALL | wx.EXPAND)
                    current_row += 1
                label, widget = setting.get_label(grouppanel), setting.get_widget(grouppanel)
                if setting.name.startswith("separator_"):
                    font = label.GetFont()
                    font.SetWeight(wx.BOLD)
                    label.SetFont(font)
                grid.Add(label, pos = (current_row, 0), border = get_space('minor'),
                         flag = wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT | wx.LEFT)
                expand = 0 if isinstance(widget, (wx.SpinCtrlDouble, wx.Choice, wx.ComboBox)) else wx.EXPAND
                grid.Add(widget, pos = (current_row, 1), border = get_space('minor'),
                         flag = wx.ALIGN_CENTER_VERTICAL | wx.RIGHT | expand)
                if hasattr(label, "set_default"):
                    label.Bind(wx.EVT_MOUSE_EVENTS, label.set_default)
                    if hasattr(widget, "Bind"):
                        widget.Bind(wx.EVT_MOUSE_EVENTS, label.set_default)
                current_row += 1
            grid.AddGrowableCol(1)
            grouppanel.SetSizer(grid)
            # The size of the options dialog is determined by the first panel 'Printer settings'
            if group == group_list[0]:
                grouppanel.SetMinSize(grid.ComputeFittingWindowSize(grouppanel))
        topsizer = wx.BoxSizer(wx.VERTICAL)
        topsizer.Add(notebook, 1, wx.EXPAND | wx.ALL, get_space('minor'))
        topsizer.Add(wx.StaticLine(self, -1, style = wx.LI_HORIZONTAL), 0, wx.EXPAND)
        topsizer.Add(self.CreateButtonSizer(wx.OK | wx.CANCEL), 0, wx.ALIGN_RIGHT | wx.ALL, get_space('stddlg'))
        self.SetSizer(topsizer)
        self.Fit()
        self.CentreOnParent()


notebookSelection = 0
def PronterOptions(pronterface):
    dialog = PronterOptionsDialog(pronterface)
    global notebookSelection
    dialog.notebook.Selection = notebookSelection
    if dialog.ShowModal() == wx.ID_OK:
        changed_settings = []
        for setting in pronterface.settings._all_settings():
            old_value = setting.value
            setting.update()
            if setting.value != old_value:
                pronterface.set(setting.name, setting.value)
                changed_settings.append(setting)
        pronterface.on_settings_change(changed_settings)
    notebookSelection = dialog.notebook.Selection
    dialog.Destroy()

class ButtonEdit(wx.Dialog):
    """Custom button edit dialog"""
    def __init__(self, pronterface):
        wx.Dialog.__init__(self, None, title = _("Custom button"),
                           style = wx.DEFAULT_DIALOG_STYLE)
        self.pronterface = pronterface
        panel = wx.Panel(self)
        grid = wx.FlexGridSizer(rows = 0, cols = 2, hgap = get_space('minor'), vgap = get_space('minor'))
        grid.AddGrowableCol(1, 1)
        ## Title of the button
        grid.Add(wx.StaticText(panel, -1, _("Button title:")), 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        self.name = wx.TextCtrl(panel, -1, "")
        dlg_size = 260
        self.name.SetMinSize(wx.Size(dlg_size, -1))
        grid.Add(self.name, 1, wx.EXPAND)
        ## Colour of the button
        grid.Add(wx.StaticText(panel, -1, _("Colour:")), 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        coloursizer = wx.BoxSizer(wx.HORIZONTAL)
        self.use_colour = wx.CheckBox(panel, -1)
        self.color = wx.ColourPickerCtrl(panel, colour=(255, 255, 255), style=wx.CLRP_USE_TEXTCTRL)
        self.color.Disable()
        self.use_colour.Bind(wx.EVT_CHECKBOX, self.onColourCheckbox)
        coloursizer.Add(self.use_colour, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, get_space('minor'))
        coloursizer.Add(self.color, 1, wx.EXPAND)
        grid.Add(coloursizer, 1, wx.EXPAND)
        ## Enter commands or choose a macro
        macrotooltip = _("Type short commands directly, enter a name for a new macro or select an existing macro from the list.")
        commandfield = wx.StaticText(panel, -1, _("Command:"))
        commandfield.SetToolTip(wx.ToolTip(macrotooltip))
        grid.Add(commandfield, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        macrochoices = list(self.pronterface.macros.keys())  # add the available macros to the dropdown
        macrochoices.insert(0, "")  # add an empty field, so that a new macro name can be entered
        self.command = wx.ComboBox(panel, -1, "", choices = macrochoices, style = wx.CB_DROPDOWN)
        self.command.SetToolTip(wx.ToolTip(macrotooltip))
        commandsizer = wx.BoxSizer(wx.HORIZONTAL)
        commandsizer.Add(self.command, 1, wx.EXPAND)
        self.command.Bind(wx.EVT_TEXT, self.macrob_enabler)
        self.macrobtn = wx.Button(panel, -1, "...", style = wx.BU_EXACTFIT)
        self.macrobtn.SetMinSize((self.macrobtn.GetTextExtent('AAA').width, -1))
        self.macrobtn.SetToolTip(wx.ToolTip(_("Create a new macro or edit an existing one.")))
        self.macrobtn.Bind(wx.EVT_BUTTON, self.macrob_handler)
        commandsizer.Add(self.macrobtn, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, get_space('minor'))
        grid.Add(commandsizer, 1, wx.EXPAND)
        panel.SetSizer(grid)
        topsizer = wx.BoxSizer(wx.VERTICAL)
        topsizer.Add(panel, 0, wx.EXPAND | wx.ALL, get_space('major'))
        topsizer.Add(wx.StaticLine(self, -1, style = wx.LI_HORIZONTAL), 0, wx.EXPAND)
        topsizer.Add(self.CreateButtonSizer(wx.OK | wx.CANCEL), 0, wx.ALIGN_RIGHT | wx.ALL, get_space('stddlg'))
        self.SetSizer(topsizer)
        topsizer.Fit(self)
        self.CentreOnParent()
        self.name.SetFocus()

    def macrob_enabler(self, e):
        macro = self.command.GetValue()
        valid = False
        try:
            if macro == "":
                valid = True
            elif macro in self.pronterface.macros:
                valid = True
            elif hasattr(self.pronterface.__class__, "do_" + macro):
                valid = False
            elif len([c for c in macro if not c.isalnum() and c != "_"]):
                valid = False
            else:
                valid = True
        except:
            if macro == "":
                valid = True
            elif macro in self.pronterface.macros:
                valid = True
            elif len([c for c in macro if not c.isalnum() and c != "_"]):
                valid = False
            else:
                valid = True
        self.macrobtn.Enable(valid)

    def macrob_handler(self, e):
        macro = self.command.GetValue()
        macro = self.pronterface.edit_macro(macro)
        self.command.SetValue(macro)
        if self.name.GetValue() == "":
            self.name.SetValue(macro)

    def onColourCheckbox(self, e):
        status = self.use_colour.GetValue()
        if status:
            self.color.Enable()
        else:
            self.color.Disable()

class TempGauge(wx.Panel):

    def __init__(self, parent, size = (200, 22), title = "",
                 maxval = 240, gaugeColour = None, bgcolor = "#FFFFFF"):
        wx.Panel.__init__(self, parent, -1, size = size)
        self.Bind(wx.EVT_PAINT, self.paint)
        self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)
        self.bgcolor = wx.Colour()
        self.bgcolor.Set(bgcolor)
        self.width, self.height = size
        self.title = title
        self.max = maxval
        self.gaugeColour = gaugeColour
        self.value = 0
        self.setpoint = 0
        self.recalc()

    def recalc(self):
        mmax = max(int(self.setpoint * 1.05), self.max)
        self.scale = float(self.width - 2) / float(mmax)
        self.ypt = max(16, int(self.scale * max(self.setpoint, self.max / 6)))

    def SetValue(self, value):
        self.value = value
        wx.CallAfter(self.Refresh)

    def SetTarget(self, value):
        self.setpoint = value
        wx.CallAfter(self.Refresh)

    def interpolatedColour(self, val, vmin, vmid, vmax, cmin, cmid, cmax):
        if val < vmin:
            return cmin
        if val > vmax:
            return cmax
        if val <= vmid:
            lo, hi, val, valhi = cmin, cmid, val - vmin, vmid - vmin
        else:
            lo, hi, val, valhi = cmid, cmax, val - vmid, vmax - vmid
        vv = float(val) / valhi
        rgb = lo.Red() + (hi.Red() - lo.Red()) * vv, lo.Green() + (hi.Green() - lo.Green()) * vv, lo.Blue() + (hi.Blue() - lo.Blue()) * vv
        rgb = (int(x * 0.8) for x in rgb)
        return wx.Colour(*rgb)

    def paint(self, ev):
        self.width, self.height = self.GetClientSize()
        self.recalc()
        x0, y0, x1, y1, xE, yE = 1, 1, self.ypt + 1, 1, self.width + 1 - 2, 20
        dc = wx.PaintDC(self)
        dc.SetBackground(wx.Brush(self.bgcolor))
        dc.Clear()
        cold, medium, hot = wx.Colour(0, 167, 223), wx.Colour(239, 233, 119), wx.Colour(210, 50, 0)
        # gauge1, gauge2 = wx.Colour(255, 255, 210), (self.gaugeColour or wx.Colour(234, 82, 0))
        gauge1 = wx.Colour(255, 255, 210)
        shadow1, shadow2 = wx.Colour(110, 110, 110), self.bgcolor
        gc = wx.GraphicsContext.Create(dc)
        # draw shadow first
        # corners
        gc.SetBrush(gc.CreateRadialGradientBrush(xE - 7, 9, xE - 7, 9, 8, shadow1, shadow2))
        gc.DrawRectangle(xE - 7, 1, 8, 8)
        gc.SetBrush(gc.CreateRadialGradientBrush(xE - 7, 17, xE - 7, 17, 8, shadow1, shadow2))
        gc.DrawRectangle(xE - 7, 17, 8, 8)
        gc.SetBrush(gc.CreateRadialGradientBrush(x0 + 6, 17, x0 + 6, 17, 8, shadow1, shadow2))
        gc.DrawRectangle(0, 17, x0 + 6, 8)
        # edges
        gc.SetBrush(gc.CreateLinearGradientBrush(xE - 6, 0, xE + 1, 0, shadow1, shadow2))
        gc.DrawRectangle(xE - 7, 9, 8, 8)
        gc.SetBrush(gc.CreateLinearGradientBrush(x0, yE - 2, x0, yE + 5, shadow1, shadow2))
        gc.DrawRectangle(x0 + 6, yE - 2, xE - 12, 7)
        # draw gauge background
        gc.SetBrush(gc.CreateLinearGradientBrush(x0, y0, x1 + 1, y1, cold, medium))
        gc.DrawRoundedRectangle(x0, y0, x1 + 4, yE, 6)
        gc.SetBrush(gc.CreateLinearGradientBrush(x1 - 2, y1, xE, y1, medium, hot))
        gc.DrawRoundedRectangle(x1 - 2, y1, xE - x1, yE, 6)
        # draw gauge
        width = 12
        w1 = y0 + 9 - width / 2
        w2 = w1 + width
        value = x0 + max(10, min(self.width + 1 - 2, int(self.value * self.scale)))
        # gc.SetBrush(gc.CreateLinearGradientBrush(x0, y0 + 3, x0, y0 + 15, gauge1, gauge2))
        # gc.SetBrush(gc.CreateLinearGradientBrush(0, 3, 0, 15, wx.Colour(255, 255, 255), wx.Colour(255, 90, 32)))
        gc.SetBrush(gc.CreateLinearGradientBrush(x0, y0 + 3, x0, y0 + 15, gauge1, self.interpolatedColour(value, x0, x1, xE, cold, medium, hot)))
        val_path = gc.CreatePath()
        val_path.MoveToPoint(x0, w1)
        val_path.AddLineToPoint(value, w1)
        val_path.AddLineToPoint(value + 2, w1 + width / 4)
        val_path.AddLineToPoint(value + 2, w2 - width / 4)
        val_path.AddLineToPoint(value, w2)
        # val_path.AddLineToPoint(value-4, 10)
        val_path.AddLineToPoint(x0, w2)
        gc.DrawPath(val_path)
        # draw setpoint markers
        setpoint = x0 + max(10, int(self.setpoint * self.scale))
        gc.SetBrush(gc.CreateBrush(wx.Brush(wx.Colour(0, 0, 0))))
        setp_path = gc.CreatePath()
        setp_path.MoveToPoint(setpoint - 4, y0)
        setp_path.AddLineToPoint(setpoint + 4, y0)
        setp_path.AddLineToPoint(setpoint, y0 + 5)
        setp_path.MoveToPoint(setpoint - 4, yE)
        setp_path.AddLineToPoint(setpoint + 4, yE)
        setp_path.AddLineToPoint(setpoint, yE - 5)
        gc.DrawPath(setp_path)
        # draw readout
        text = "T\u00B0 %u/%u" % (self.value, self.setpoint)
        # gc.SetFont(gc.CreateFont(wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD), wx.WHITE))
        # gc.DrawText(text, 29,-2)
        gc.SetFont(gc.CreateFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD), wx.WHITE))
        gc.DrawText(self.title, x0 + 19, y0 + 4)
        gc.DrawText(text, x0 + 119, y0 + 4)
        gc.SetFont(gc.CreateFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)))
        gc.DrawText(self.title, x0 + 18, y0 + 3)
        gc.DrawText(text, x0 + 118, y0 + 3)

class SpecialButton:

    label = None
    command = None
    background = None
    tooltip = None
    custom = None

    def __init__(self, label, command, background = None,
                 tooltip = None, custom = False):
        self.label = label
        self.command = command
        self.background = background
        self.tooltip = tooltip
        self.custom = custom
