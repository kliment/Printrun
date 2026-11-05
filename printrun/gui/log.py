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

import math

import wx

from .utils import make_button

class SendModeIndicator(wx.StaticBitmap):
    """A dot showing how lines are being sent to the printer"""
    SIZE = 12
    # (MeatPack packing, Advanced OK sending ahead)
    COLORS = {(False, False): (150, 150, 150),
              (True, False): (60, 130, 230),
              (False, True): (235, 160, 30),
              (True, True): (40, 190, 80)}
    TIPS = {(False, False): _("Normal: lines are plain text, one at a time"),
            (True, False): _("MeatPack: lines are packed"),
            (False, True): _("Advanced OK: lines are sent ahead of replies"),
            (True, True): _("MeatPack and Advanced OK: lines are packed and sent ahead of replies")}

    def __init__(self, parent):
        super().__init__(parent, bitmap = self.dot(self.COLORS[(False, False)]))
        self.set_state(False, False)

    @classmethod
    def dot(cls, color):
        """Make a round dot with a smooth edge"""
        middle = cls.SIZE / 2
        data = bytearray()
        for y in range(cls.SIZE):
            for x in range(cls.SIZE):
                distance = math.hypot(x + 0.5 - middle, y + 0.5 - middle)
                coverage = min(max(middle - distance, 0), 1)
                data.extend((*color, int(255 * coverage)))
        return wx.Bitmap.FromBufferRGBA(cls.SIZE, cls.SIZE, bytes(data))

    def set_state(self, packing, sending_ahead):
        state = (bool(packing), bool(sending_ahead))
        self.SetBitmap(self.dot(self.COLORS[state]))
        self.SetToolTip(wx.ToolTip(self.TIPS[state]))


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
        root.commandbox.Hint = _("Command to send")
        root.commandbox.Bind(wx.EVT_TEXT_ENTER, root.sendline)
        root.commandbox.Bind(wx.EVT_CHAR, root.cbkey)
        def deselect(ev):
            # In Ubuntu 19.10, when focused, all text is selected
            lp = root.commandbox.LastPosition
            # print(f"SetSelection({lp}, {lp})")
            wx.CallAfter(root.commandbox.SetSelection, lp, lp)
            ev.Skip()
        root.commandbox.Bind(wx.EVT_SET_FOCUS, deselect)
        root.commandbox.history = [""]
        root.commandbox.histindex = 1
        root.send_mode_indicator = SendModeIndicator(bottom_panel)
        lbrs.Add(root.send_mode_indicator, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT | wx.RIGHT, 4)
        root.update_send_mode_indicator()
        lbrs.Add(root.commandbox, 1)
        root.sendbtn = make_button(bottom_panel, _("Send"), root.sendline, _("Send Command to Printer"), style = wx.BU_EXACTFIT, container = lbrs)
        bottom_panel.SetSizer(lbrs)
        self.Add(bottom_panel, 0, wx.EXPAND)
