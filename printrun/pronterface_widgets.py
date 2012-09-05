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

class MacroEditor(wx.Dialog):
    """Really simple editor to edit macro definitions"""

    def __init__(self, macro_name, definition, callback, gcode = False):
        self.indent_chars = "  "
        title = "  macro %s"
        if gcode:
            title = "  %s"
        self.gcode = gcode
        wx.Dialog.__init__(self, None, title = title % macro_name, style = wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)
        self.callback = callback
        self.panel = wx.Panel(self,-1)
        titlesizer = wx.BoxSizer(wx.HORIZONTAL)
        titletext = wx.StaticText(self.panel,-1, "              _")  #title%macro_name)
        #title.SetFont(wx.Font(11, wx.NORMAL, wx.NORMAL, wx.BOLD))
        titlesizer.Add(titletext, 1)
        self.findb = wx.Button(self.panel,  -1, _("Find"), style = wx.BU_EXACTFIT)  #New button for "Find" (Jezmy)
        self.findb.Bind(wx.EVT_BUTTON,  self.find)
        self.okb = wx.Button(self.panel, -1, _("Save"), style = wx.BU_EXACTFIT)
        self.okb.Bind(wx.EVT_BUTTON, self.save)
        self.Bind(wx.EVT_CLOSE, self.close)
        titlesizer.Add(self.findb)
        titlesizer.Add(self.okb)
        self.cancelb = wx.Button(self.panel, -1, _("Cancel"), style = wx.BU_EXACTFIT)
        self.cancelb.Bind(wx.EVT_BUTTON, self.close)
        titlesizer.Add(self.cancelb)
        topsizer = wx.BoxSizer(wx.VERTICAL)
        topsizer.Add(titlesizer, 0, wx.EXPAND)
        self.e = wx.TextCtrl(self.panel, style = wx.HSCROLL|wx.TE_MULTILINE|wx.TE_RICH2, size = (400, 400))
        if not self.gcode:
            self.e.SetValue(self.unindent(definition))
        else:
            self.e.SetValue("\n".join(definition))
        topsizer.Add(self.e, 1, wx.ALL+wx.EXPAND)
        self.panel.SetSizer(topsizer)
        topsizer.Layout()
        topsizer.Fit(self)
        self.Show()
        self.e.SetFocus()

    def find(self, ev):
        # Ask user what to look for, find it and point at it ...  (Jezmy)
        S = self.e.GetStringSelection()
        if not S :
            S = "Z"
        FindValue = wx.GetTextFromUser('Please enter a search string:', caption = "Search", default_value = S, parent = None)
        somecode = self.e.GetValue()
        numLines = len(somecode)
        position = somecode.find(FindValue,  self.e.GetInsertionPoint())
        if position == -1 :
         #   ShowMessage(self,-1,  "Not found!")
            titletext = wx.TextCtrl(self.panel,-1, "Not Found!")
        else:
        # self.title.SetValue("Position : "+str(position))

            titletext = wx.TextCtrl(self.panel,-1, str(position))

            # ananswer = wx.MessageBox(str(numLines)+" Lines detected in file\n"+str(position), "OK")
            self.e.SetFocus()
            self.e.SetInsertionPoint(position)
            self.e.SetSelection(position,  position + len(FindValue))
            self.e.ShowPosition(position)

    def ShowMessage(self, ev , message):
        dlg = wxMessageDialog(self, message,
                              "Info!", wxOK | wxICON_INFORMATION)
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
        self.indent_chars = text[:len(text)-len(text.lstrip())]
        if len(self.indent_chars) == 0:
            self.indent_chars = "  "
        unindented = ""
        lines = re.split(r"(?:\r\n?|\n)", text)
        #print lines
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

class options(wx.Dialog):
    """Options editor"""
    def __init__(self, pronterface):
        wx.Dialog.__init__(self, None, title = _("Edit settings"), style = wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)
        topsizer = wx.BoxSizer(wx.VERTICAL)
        vbox = wx.StaticBoxSizer(wx.StaticBox(self, label = _("Defaults")) ,wx.VERTICAL)
        topsizer.Add(vbox, 1, wx.ALL+wx.EXPAND)
        grid = wx.FlexGridSizer(rows = 0, cols = 2, hgap = 8, vgap = 2)
        grid.SetFlexibleDirection( wx.BOTH )
        grid.AddGrowableCol( 1 )
        grid.SetNonFlexibleGrowMode( wx.FLEX_GROWMODE_SPECIFIED )
        vbox.Add(grid, 0, wx.EXPAND)
        ctrls = {}
        for k, v in sorted(pronterface.settings._all_settings().items()):
            ctrls[k, 0] = wx.StaticText(self,-1, k)
            ctrls[k, 1] = wx.TextCtrl(self,-1, str(v))
            if k in pronterface.helpdict:
                ctrls[k, 0].SetToolTipString(pronterface.helpdict.get(k))
                ctrls[k, 1].SetToolTipString(pronterface.helpdict.get(k))
            grid.Add(ctrls[k, 0], 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL|wx.ALIGN_RIGHT)
            grid.Add(ctrls[k, 1], 1, wx.ALIGN_CENTER_VERTICAL|wx.ALL|wx.EXPAND)
        topsizer.Add(self.CreateSeparatedButtonSizer(wx.OK+wx.CANCEL), 0, wx.EXPAND)
        self.SetSizer(topsizer)
        topsizer.Layout()
        topsizer.Fit(self)
        if self.ShowModal() == wx.ID_OK:
            for k, v in pronterface.settings._all_settings().items():
                if ctrls[k, 1].GetValue() != str(v):
                    pronterface.set(k, str(ctrls[k, 1].GetValue()))
        self.Destroy()

class ButtonEdit(wx.Dialog):
    """Custom button edit dialog"""
    def __init__(self, pronterface):
        wx.Dialog.__init__(self, None, title = _("Custom button"), style = wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)
        self.pronterface = pronterface
        topsizer = wx.BoxSizer(wx.VERTICAL)
        grid = wx.FlexGridSizer(rows = 0, cols = 2, hgap = 4, vgap = 2)
        grid.AddGrowableCol(1, 1)
        grid.Add(wx.StaticText(self,-1, _("Button title")), 0, wx.BOTTOM|wx.RIGHT)
        self.name = wx.TextCtrl(self,-1, "")
        grid.Add(self.name, 1, wx.EXPAND)
        grid.Add(wx.StaticText(self, -1, _("Command")), 0, wx.BOTTOM|wx.RIGHT)
        self.command = wx.TextCtrl(self,-1, "")
        xbox = wx.BoxSizer(wx.HORIZONTAL)
        xbox.Add(self.command, 1, wx.EXPAND)
        self.command.Bind(wx.EVT_TEXT, self.macrob_enabler)
        self.macrob = wx.Button(self,-1, "..", style = wx.BU_EXACTFIT)
        self.macrob.Bind(wx.EVT_BUTTON, self.macrob_handler)
        xbox.Add(self.macrob, 0)
        grid.Add(xbox, 1, wx.EXPAND)
        grid.Add(wx.StaticText(self,-1, _("Color")), 0, wx.BOTTOM|wx.RIGHT)
        self.color = wx.TextCtrl(self,-1, "")
        grid.Add(self.color, 1, wx.EXPAND)
        topsizer.Add(grid, 0, wx.EXPAND)
        topsizer.Add( (0, 0), 1)
        topsizer.Add(self.CreateStdDialogButtonSizer(wx.OK|wx.CANCEL), 0, wx.ALIGN_CENTER)
        self.SetSizer(topsizer)

    def macrob_enabler(self, e):
        macro = self.command.GetValue()
        valid = False
        try:
            if macro == "":
                valid = True
            elif self.pronterface.macros.has_key(macro):
                valid = True
            elif hasattr(self.pronterface.__class__, u"do_"+macro):
                valid = False
            elif len([c for c in macro if not c.isalnum() and c != "_"]):
                valid = False
            else:
                valid = True
        except:
            if macro == "":
                valid = True
            elif self.pronterface.macros.has_key(macro):
                valid = True
            elif len([c for c in macro if not c.isalnum() and c != "_"]):
                valid = False
            else:
                valid = True
        self.macrob.Enable(valid)

    def macrob_handler(self, e):
        macro = self.command.GetValue()
        macro = self.pronterface.edit_macro(macro)
        self.command.SetValue(macro)
        if self.name.GetValue()=="":
            self.name.SetValue(macro)

class SpecialButton(object):

    label = None
    command = None
    background = None
    pos = None
    span = None
    tooltip = None
    custom = None

    def __init__(self, label, command, background = None, pos = None, span = None, tooltip = None, custom = False):
        self.label = label
        self.command = command
        self.pos = pos
        self.background = background
        self.span = span
        self.tooltip = tooltip
        self.custom = custom
