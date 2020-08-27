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

from .utils import make_autosize_button

def MainToolbar(root, parentpanel = None, use_wrapsizer = False):
    if not parentpanel: parentpanel = root.panel
    if root.settings.lockbox:
        root.locker = wx.CheckBox(parentpanel, label = _("Lock") + "  ")
        root.locker.Bind(wx.EVT_CHECKBOX, root.lock)
        root.locker.SetToolTip(wx.ToolTip(_("Lock graphical interface")))
        glob = wx.BoxSizer(wx.HORIZONTAL)
        parentpanel = root.newPanel(parentpanel)
        glob.Add(parentpanel, 1, flag = wx.EXPAND)
        glob.Add(root.locker, 0, flag = wx.ALIGN_CENTER)
    ToolbarSizer = wx.WrapSizer if use_wrapsizer else wx.BoxSizer
    self = ToolbarSizer(wx.HORIZONTAL)
    root.rescanbtn = make_autosize_button(parentpanel, _("Port"), root.rescanports, _("Communication Settings\nClick to rescan ports"))
    self.Add(root.rescanbtn, 0, wx.TOP | wx.LEFT, 0)

    root.serialport = wx.ComboBox(parentpanel, -1, choices = root.scanserial(),
                                  style = wx.CB_DROPDOWN)
    root.serialport.SetToolTip(wx.ToolTip(_("Select Port Printer is connected to")))
    root.rescanports()
    self.Add(root.serialport)

    self.Add(wx.StaticText(parentpanel, -1, "@"), 0, wx.RIGHT | wx.ALIGN_CENTER, 0)
    root.baud = wx.ComboBox(parentpanel, -1,
                            choices = ["2400", "9600", "19200", "38400",
                                       "57600", "115200", "250000"],
                            style = wx.CB_DROPDOWN, size = (110, -1))
    root.baud.SetToolTip(wx.ToolTip(_("Select Baud rate for printer communication")))
    try:
        root.baud.SetValue("115200")
        root.baud.SetValue(str(root.settings.baudrate))
    except:
        pass
    self.Add(root.baud)

    if not hasattr(root, "connectbtn"):
        root.connectbtn_cb_var = root.connect
        root.connectbtn = make_autosize_button(parentpanel, _("&Connect"), root.connectbtn_cb, _("Connect to the printer"))
        root.statefulControls.append(root.connectbtn)
    else:
        root.connectbtn.Reparent(parentpanel)
    self.Add(root.connectbtn)
    if not hasattr(root, "resetbtn"):
        root.resetbtn = make_autosize_button(parentpanel, _("Reset"), root.reset, _("Reset the printer"))
        root.statefulControls.append(root.resetbtn)
    else:
        root.resetbtn.Reparent(parentpanel)
    self.Add(root.resetbtn)

    self.AddStretchSpacer(prop = 1)

    root.loadbtn = make_autosize_button(parentpanel, _("Load file"), root.loadfile, _("Load a 3D model file"), self)
    root.sdbtn = make_autosize_button(parentpanel, _("SD"), root.sdmenu, _("SD Card Printing"), self)
    root.sdbtn.Reparent(parentpanel)
    root.printerControls.append(root.sdbtn)
    if not hasattr(root, "printbtn"):
        root.printbtn = make_autosize_button(parentpanel, _("Print"), root.printfile, _("Start Printing Loaded File"))
        root.statefulControls.append(root.printbtn)
    else:
        root.printbtn.Reparent(parentpanel)
    self.Add(root.printbtn)
    if not hasattr(root, "pausebtn"):
        root.pausebtn = make_autosize_button(parentpanel, _("Pause"), root.pause, _("Pause Current Print"))
        root.statefulControls.append(root.pausebtn)
    else:
        root.pausebtn.Reparent(parentpanel)
    self.Add(root.pausebtn)
    root.offbtn = make_autosize_button(parentpanel, _("Off"), root.off, _("Turn printer off"), self)
    root.printerControls.append(root.offbtn)

    self.AddStretchSpacer(prop = 4)

    if root.settings.lockbox:
        parentpanel.SetSizer(self)
        return glob
    else:
        return self
