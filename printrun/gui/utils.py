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

def make_button(parent, label, callback, tooltip, container = None, size = wx.DefaultSize, style = 0):
    button = wx.Button(parent, -1, label, style = style, size = size)
    button.Bind(wx.EVT_BUTTON, callback)
    button.SetToolTip(wx.ToolTip(tooltip))
    if container:
        container.Add(button)
    return button

def make_autosize_button(*args):
    return make_button(*args, size = (-1, -1), style = wx.BU_EXACTFIT)

def make_custom_button(root, parentpanel, i, style = 0):
    btn = make_button(parentpanel, i.label, root.process_button,
                      i.tooltip, style = style)
    btn.SetBackgroundColour(i.background)
    btn.SetForegroundColour("black")
    btn.properties = i
    root.btndict[i.command] = btn
    root.printerControls.append(btn)
    return btn
