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

import re
import string  # For determining whitespaces and punctuation marks
import platform  # Used by get_space() for platform specific spacing
import logging
import wx

def get_space(key: str) -> int:
    '''
    Takes key (str), returns spacing value (int).
    Provides correct spacing in pixel for borders and sizers.
    '''

    spacing_values = {
        'major': 12,  # e.g. outer border of dialog boxes
        'minor': 8,  # e.g. border of inner elements
        'mini': 4,
        'stddlg': 4,  # Border around std dialog buttons.
        'stddlg-frame': 8,  # Border around std dialog buttons when used with frames.
        'staticbox': 0,  # Border between StaticBoxSizers and the elements inside.
        'settings': 16,  # How wide setting elements can be (multiples of this)
        'none': 0
    }

    # Platform specific overrides, Windows
    if platform.system() == 'Windows':
        spacing_values['stddlg'] = 8
        spacing_values['staticbox'] = 4

    # Platform specific overrides, macOS
    if platform.system() == 'Darwin':
        spacing_values['stddlg-frame'] = 12

    try:
        return spacing_values[key]
    except KeyError:
        logging.warning("get_space() cannot return spacing value, "
                        "will return 0 instead. No entry: %s" % key)
        return 0


class MacroEditor(wx.Dialog):
    """Really simple editor to edit macro definitions"""

    def __init__(self, macro_name, definition, callback, gcode = False):
        self.indent_chars = "  "
        title = "%s" if gcode else "Macro %s"
        self.gcode = gcode
        self.fr_settings = (False, False, True, '')
        wx.Dialog.__init__(self, None, title = title % macro_name,
                           style = wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.callback = callback
        panel = wx.Panel(self)
        panelsizer = wx.BoxSizer(wx.VERTICAL)
        titlesizer = wx.BoxSizer(wx.HORIZONTAL)
        self.status_field = wx.StaticText(panel, -1, "")
        titlesizer.Add(self.status_field, 1, wx.ALIGN_CENTER_VERTICAL)
        self.findbtn = wx.Button(panel, -1, _("Find..."))  # New button for "Find" (Jezmy)
        self.findbtn.Bind(wx.EVT_BUTTON, self.on_find)
        self.Bind(wx.EVT_CLOSE, self.on_close)

        titlesizer.Add(self.findbtn, 0, wx.ALIGN_CENTER_VERTICAL)
        panelsizer.Add(titlesizer, 0, wx.EXPAND | wx.ALL, get_space('minor'))
        self.text_box = wx.TextCtrl(panel,
                                    style = wx.HSCROLL | wx.TE_MULTILINE | wx.TE_RICH2 | wx.TE_NOHIDESEL,
                                    size = (400, 400))
        if not self.gcode:
            self.text_box.SetValue(self.unindent(definition))
        else:
            self.text_box.SetValue("\n".join(definition))
        panelsizer.Add(self.text_box, 1, wx.EXPAND)
        panel.SetSizer(panelsizer)
        topsizer = wx.BoxSizer(wx.VERTICAL)
        topsizer.Add(panel, 1, wx.EXPAND | wx.ALL, get_space('none'))
        # No StaticLine in this case bc the TextCtrl acts as a divider
        btnsizer = wx.StdDialogButtonSizer()
        self.savebtn = wx.Button(self, wx.ID_SAVE)
        self.savebtn.SetDefault()
        self.savebtn.Bind(wx.EVT_BUTTON, self.on_save)
        self.cancelbtn = wx.Button(self, wx.ID_CANCEL)
        self.cancelbtn.Bind(wx.EVT_BUTTON, self.on_close)
        btnsizer.AddButton(self.savebtn)
        btnsizer.AddButton(self.cancelbtn)
        btnsizer.Realize()
        topsizer.Add(btnsizer, 0, wx.ALIGN_RIGHT | wx.ALL, get_space('stddlg'))
        self.SetSizer(topsizer)
        self.SetMinClientSize((230, 150))  # TODO: Check if self.FromDIP() is needed
        topsizer.Fit(self)
        self.CentreOnParent()
        self.Show()
        self.text_box.SetFocus()

    def on_find(self, event):
        for window in self.GetChildren():
            if isinstance(window, wx.FindReplaceDialog):
                window.Show()
                window.Raise()
                return
        FindAndReplace(self.text_box, self.status_field, self.fr_settings, self.fr_callback)

    def fr_callback(self, val1, val2, val3, val4):
        self.fr_settings = (val1, val2, val3, val4)

    def on_save(self, event):
        self.Destroy()
        if not self.gcode:
            self.callback(self.reindent(self.text_box.GetValue()))
        else:
            self.callback(self.text_box.GetValue().split("\n"))

    def on_close(self, event):
        self.Destroy()

    def ShowMessage(self, event, message):
        dlg = wx.MessageDialog(self, message,
                               "Info!", wx.OK | wx.ICON_INFORMATION)
        dlg.ShowModal()
        dlg.Destroy()

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

class FindAndReplace():
    '''A dialogue that provides full functionality for finding
    and replacing strings in a given target string.
    '''
    def __init__(self, text_cntrl: wx.TextCtrl,
                 statusbar: wx.StaticText,
                 settings: tuple = (False, False, True, ''),
                 settings_cb = None):

        self.matchcase = settings[0]  # wx.FR_MATCHCASE
        self.wholeword = settings[1]  # wx.FR_WHOLEWORD
        self.down = settings[2]  # wx.FR_DOWN
        self.callback = settings_cb

        self.statusbar = statusbar
        self.text_cntrl = text_cntrl
        self.find_str = settings[3]
        self.replace_str = ""
        self.target = ""
        self.all_matches = 0
        self.current_match = 0

        if self.text_cntrl.IsEmpty():
            self.statusbar.SetLabel(_("No content to search."))
            return

        # Initialise and hold search parameters in fr_data
        self.fr_data = wx.FindReplaceData(self.bools_to_flags(settings))
        selection = text_cntrl.GetStringSelection()
        if selection and not len(selection) > 40 and selection not in ('\n', '\r'):
            self.find_str = selection
        self.fr_data.SetFindString(self.find_str)
        self.fr_dialog = wx.FindReplaceDialog(self.text_cntrl,
                                              self.fr_data, _("Find and Replace..."),
                                              wx.FR_REPLACEDIALOG)

        # Bind all button events
        self.fr_dialog.Bind(wx.EVT_FIND, self.on_find)
        self.fr_dialog.Bind(wx.EVT_FIND_NEXT, self.on_find_next)
        self.fr_dialog.Bind(wx.EVT_FIND_REPLACE, self.on_replace)
        self.fr_dialog.Bind(wx.EVT_FIND_REPLACE_ALL, self.on_replace_all)
        self.fr_dialog.Bind(wx.EVT_FIND_CLOSE, self.on_cancel)

        # Move the dialogue to the side of the editor where there is more space
        display_size = wx.Display(self.fr_dialog).GetClientArea()
        ed_x, ed_y, ed_width, ed_height = self.fr_dialog.GetParent().GetRect()
        fr_x, fr_y, fr_width, fr_height = self.fr_dialog.GetRect()
        if display_size[2] - ed_x - ed_width < fr_width:
            fr_x = ed_x - fr_width
        else:
            fr_x = ed_x + ed_width - 16
        self.fr_dialog.SetRect((fr_x, fr_y, fr_width, fr_height))
        self.fr_dialog.Show()

    def update_data(self):
        '''Reads the current settings of the FindReplaceDialog and updates
        all relevant strings of the search feature.
        '''
        # Update flags
        flags_binary = bin(self.fr_data.GetFlags())[2:].zfill(3)
        self.down = bool(int(flags_binary[2]))
        self.wholeword = bool(int(flags_binary[1]))
        self.matchcase = bool(int(flags_binary[0]))

        # Update search data
        self.find_str = self.fr_data.GetFindString()
        self.replace_str = self.fr_data.GetReplaceString()
        self.target = self.text_cntrl.GetRange(0, self.text_cntrl.GetLastPosition())
        if not self.find_str:
            self.statusbar.SetLabel("")

        if not self.matchcase:
            # When search is not case-sensitve, convert the whole string to lowercase
            self.find_str = self.find_str.casefold()
            self.target = self.target.casefold()

    def find_next(self):
        self.update_data()
        if not self.update_all_matches():
            return

        # If the search string is already selected, move
        # the InsertionPoint and then select the next match
        idx = self.text_cntrl.GetInsertionPoint()
        selection = self.get_selected_str()
        if selection == self.find_str:
            sel_from, sel_to = self.text_cntrl.GetSelection()
            self.text_cntrl.SelectNone()
            if self.down:
                self.text_cntrl.SetInsertionPoint(sel_to)
                idx = sel_to
            else:
                self.text_cntrl.SetInsertionPoint(sel_from)
                idx = sel_from

        self.select_next_match(idx)

    def replace_next(self):
        '''Replaces one time the next instance of the search string
        in the defined direction.
        '''
        self.update_data()
        if not self.update_all_matches():
            return

        # If the search string is already selected, replace it.
        # Otherwise find the next match an replace that one.
        # The while loop helps us with the wholeword checks
        if self.get_selected_str() == self.find_str:
            sel_from, sel_to = self.text_cntrl.GetSelection()
        else:
            sel_from = self.get_next_idx(self.text_cntrl.GetInsertionPoint())
            sel_to = sel_from + len(self.find_str)
        self.text_cntrl.SelectNone()
        self.text_cntrl.Replace(sel_from, sel_to, self.replace_str)

        # The text_cntrl object is changed directly so
        # we need to update the copy in self.target
        self.update_data()

        self.all_matches -= 1
        if not self.all_matches:
            self.statusbar.SetLabel(_('No matches'))
            return
        self.select_next_match(sel_from)

    def replace_all(self):
        '''Goes through the whole file and replaces
        every instance of the search string.
        '''
        position = self.text_cntrl.GetInsertionPoint()
        self.update_data()
        if not self.update_all_matches():
            return

        self.text_cntrl.SelectNone()
        seek_idx = 0
        for match in range(self.all_matches):
            sel_from = self.get_next_idx(seek_idx)
            sel_to = sel_from + len(self.find_str)
            self.text_cntrl.Replace(sel_from, sel_to, self.replace_str)
            seek_idx = sel_from
            self.update_data()

        self.statusbar.SetLabel(_('Replaced {} matches').format(self.all_matches))
        self.all_matches = 0
        self.text_cntrl.SetInsertionPoint(position)
        self.text_cntrl.ShowPosition(position)

    def bools_to_flags(self, bools) -> int:
        '''Converts a tuple of bool settings into an integer
        that is readable for wx.FindReplaceData'''
        matchcase = wx.FR_MATCHCASE if bools[0] else 0
        wholeword = wx.FR_WHOLEWORD if bools[1] else 0
        down = wx.FR_DOWN if bools[2] else 0
        return matchcase | wholeword | down

    def get_selected_str(self) -> str:
        '''Returns the currently selected string, accounting for matchcase.'''
        selection = self.text_cntrl.GetStringSelection()
        if not self.matchcase:
            selection = selection.casefold()
        return selection

    def get_next_idx(self, position: int) -> int:
        '''Searches for the next instance of the search string
        in the defined direction.
        Takes wholeword setting into account.
        Returns index of the first character.
        '''
        while True:
            if self.down:
                next_idx = self.target.find(self.find_str, position)
                if next_idx == -1:
                    next_idx = self.target.find(self.find_str, 0, position)
                if not self.wholeword or (self.wholeword and self.is_wholeword(next_idx)):
                    break
                position = next_idx + len(self.find_str)
            else:
                next_idx = self.target.rfind(self.find_str, 0, position)
                if next_idx == -1:
                    next_idx = self.target.rfind(self.find_str, position)
                if not self.wholeword or (self.wholeword and self.is_wholeword(next_idx)):
                    break
                position = next_idx
        return next_idx

    def update_all_matches(self) -> bool:
        '''Updates self.all_matches with the amount of search
        string instances in the target string.
        '''
        self.all_matches = 0
        if self.wholeword:
            selection = self.text_cntrl.GetSelection()
            self.text_cntrl.SetInsertionPoint(0)
            seek_idx = 0
            found_idx = 0
            while found_idx != -1:
                found_idx = self.target.find(self.find_str, seek_idx)
                if found_idx == -1:
                    break
                if self.is_wholeword(found_idx):
                    self.all_matches += 1
                seek_idx = found_idx + len(self.find_str)
            self.text_cntrl.SetSelection(selection[0], selection[1])
        else:
            self.all_matches = self.target.count(self.find_str)

        if not self.all_matches:
            self.statusbar.SetLabel(_('No matches'))
            return False
        return True

    def select_next_match(self, position: int):
        '''Selects the next match in the defined direction.'''
        idx = self.get_next_idx(position)

        self.text_cntrl.SetSelection(idx, idx + len(self.find_str))
        self.text_cntrl.ShowPosition(idx)
        self.update_current_match()

    def update_current_match(self):
        '''Updates the current match index.'''
        self.current_match = 0
        position = self.text_cntrl.GetInsertionPoint()
        if self.wholeword:
            selection = self.text_cntrl.GetSelection()
            seek_idx = position
            found_idx = 0
            while found_idx != -1:
                found_idx = self.target.rfind(self.find_str, 0, seek_idx)
                if found_idx == -1:
                    break
                if self.is_wholeword(found_idx):
                    self.current_match += 1
                seek_idx = found_idx
            self.current_match += 1  # We counted all matches before the current, therefore +1
            self.text_cntrl.SetSelection(selection[0], selection[1])
        else:
            self.current_match = self.target.count(self.find_str, 0, position) + 1

        self.statusbar.SetLabel(_('Match {} out of {}').format(self.current_match, self.all_matches))

    def is_wholeword(self, index: int) -> bool:
        '''Returns True if the search string is a whole word.
        That is, if it is enclosed in spaces, line breaks, or
        the very start or end of the target string.
        '''
        start_idx = index
        delimiter = string.whitespace + string.punctuation
        if start_idx != 0 and self.target[start_idx - 1] not in delimiter:
            return False
        end_idx = start_idx + len(self.find_str)
        if not end_idx > len(self.target) and self.target[end_idx] not in delimiter:
            return False
        return True

    def on_find_next(self, event):
        self.find_next()

    def on_find(self, event):
        self.find_next()

    def on_replace(self, event):
        self.replace_next()

    def on_replace_all(self, event):
        self.replace_all()

    def on_cancel(self, event):
        self.statusbar.SetLabel("")
        if self.callback:
            self.update_data()
            self.callback(self.matchcase, self.wholeword,
                          self.down, self.find_str)
        self.fr_dialog.Destroy()


SETTINGS_GROUPS = {"Printer": _("Printer Settings"),
                   "UI": _("User Interface"),
                   "Viewer": _("Viewer"),
                   "Colors": _("Colors"),
                   "External": _("External Commands")}

class PronterOptionsDialog(wx.Dialog):
    """Options editor"""
    def __init__(self, pronterface):
        wx.Dialog.__init__(self, parent = None, title = _("Edit Settings"),
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
        wx.Dialog.__init__(self, None, title = _("Custom Button"),
                           style = wx.DEFAULT_DIALOG_STYLE)
        self.pronterface = pronterface
        panel = wx.Panel(self)
        grid = wx.FlexGridSizer(rows = 0, cols = 2, hgap = get_space('minor'), vgap = get_space('minor'))
        grid.AddGrowableCol(1, 1)
        # Title of the button
        grid.Add(wx.StaticText(panel, -1, _("Button Title:")), 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        self.name = wx.TextCtrl(panel, -1, "")
        dlg_size = 260
        self.name.SetMinSize(wx.Size(dlg_size, -1))
        grid.Add(self.name, 1, wx.EXPAND)
        # Colour of the button
        grid.Add(wx.StaticText(panel, -1, _("Colour:")), 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        coloursizer = wx.BoxSizer(wx.HORIZONTAL)
        self.use_colour = wx.CheckBox(panel, -1)
        self.color = wx.ColourPickerCtrl(panel, colour=(255, 255, 255), style=wx.CLRP_USE_TEXTCTRL)
        self.color.Disable()
        self.use_colour.Bind(wx.EVT_CHECKBOX, self.toggle_colour)
        coloursizer.Add(self.use_colour, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, get_space('minor'))
        coloursizer.Add(self.color, 1, wx.EXPAND)
        grid.Add(coloursizer, 1, wx.EXPAND)
        # Enter commands or choose a macro
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

    def macrob_enabler(self, event):
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

    def macrob_handler(self, event):
        macro = self.command.GetValue()
        macro = self.pronterface.edit_macro(macro)
        self.command.SetValue(macro)
        if self.name.GetValue() == "":
            self.name.SetValue(macro)

    def toggle_colour(self, event):
        self.color.Enable(self.use_colour.GetValue())


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

    def paint(self, event):
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
