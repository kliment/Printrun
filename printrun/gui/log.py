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

from .utils import make_button

class LogPane(wx.BoxSizer):

    def __init__(self, root, parentpanel = None):
        super(LogPane, self).__init__(wx.VERTICAL)
        if not parentpanel: parentpanel = root.panel
        root.logbox = wx.TextCtrl(parentpanel, style = wx.TE_MULTILINE, size = (350, -1))
        root.logbox.SetMinSize((100, -1))
        root.logbox.SetEditable(0)
        self.Add(root.logbox, 1, wx.EXPAND)
        bottom_panel = root.newPanel(parentpanel)
        lbrs = wx.BoxSizer(wx.HORIZONTAL)
        root.commandbox = wx.TextCtrl(bottom_panel, style = wx.TE_PROCESS_ENTER)
        root.commandbox.SetToolTip(wx.ToolTip(_("Send commands to printer\n(Type 'help' for simple\nhelp function)")))
        root.commandbox.Bind(wx.EVT_TEXT_ENTER, root.sendline)
        root.commandbox.Bind(wx.EVT_CHAR, root.cbkey)
        root.commandbox.history = [u""]
        root.commandbox.histindex = 1
        lbrs.Add(root.commandbox, 1)
        root.sendbtn = make_button(bottom_panel, _("Send"), root.sendline, _("Send Command to Printer"), style = wx.BU_EXACTFIT, container = lbrs)
        bottom_panel.SetSizer(lbrs)
        self.Add(bottom_panel, 0, wx.EXPAND)
