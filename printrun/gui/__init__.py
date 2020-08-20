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

try:
    import wx
    if wx.VERSION < (4,):
        raise ImportError()
except:
    logging.error(_("WX >= 4 is not installed. This program requires WX >= 4 to run."))
    raise

from printrun.utils import install_locale
install_locale('pronterface')

from .controls import ControlsSizer, add_extra_controls
from .viz import VizPane
from .log import LogPane
from .toolbar import MainToolbar

class ToggleablePane(wx.BoxSizer):

    def __init__(self, root, label, parentpanel, parentsizers):
        super(ToggleablePane, self).__init__(wx.HORIZONTAL)
        if not parentpanel:
            parentpanel = root.panel
        self.root = root
        self.visible = True
        self.parentpanel = parentpanel
        self.parentsizers = parentsizers
        self.panepanel = root.newPanel(parentpanel)
        self.button = wx.Button(parentpanel, -1, label, size = (35, 18), style = wx.BU_EXACTFIT)
        self.button.Bind(wx.EVT_BUTTON, self.toggle)

    def toggle(self, event):
        if self.visible:
            self.Hide(self.panepanel)
            self.on_hide()
        else:
            self.Show(self.panepanel)
            self.on_show()
        self.visible = not self.visible
        self.button.SetLabel(">" if self.button.GetLabel() == "<" else "<")

class LeftPaneToggleable(ToggleablePane):
    def __init__(self, root, parentpanel, parentsizers):
        super().__init__(root, "<", parentpanel, parentsizers)
        self.Add(self.panepanel, 0, wx.EXPAND)
        self.Add(self.button, 0)

    def set_sizer(self, sizer):
        self.panepanel.SetSizer(sizer)

    def on_show(self):
        for sizer in self.parentsizers:
            sizer.Layout()

    def on_hide(self):
        for sizer in self.parentsizers:
            # Expand right splitterwindow
            if isinstance(sizer, wx.SplitterWindow):
                if sizer.shrinked:
                    button_width = self.button.GetSize()[0]
                    sizer.SetSashPosition(sizer.GetSize()[0] - button_width)
            else:
                sizer.Layout()

class LogPaneToggleable(ToggleablePane):
    def __init__(self, root, parentpanel, parentsizers):
        super(LogPaneToggleable, self).__init__(root, ">", parentpanel, parentsizers)
        self.Add(self.button, 0)
        pane = LogPane(root, self.panepanel)
        self.panepanel.SetSizer(pane)
        self.Add(self.panepanel, 1, wx.EXPAND)
        self.splitter = self.parentpanel.GetParent()

    def on_show(self):
        self.splitter.shrinked = False
        self.splitter.SetSashPosition(self.splitter.GetSize()[0] - self.orig_width)
        self.splitter.SetMinimumPaneSize(self.orig_min_size)
        self.splitter.SetSashGravity(self.orig_gravity)
        if getattr(self.splitter, 'SetSashSize', False):
            self.splitter.SetSashSize(self.orig_sash_size)
        getattr(self.splitter, 'SetSashInvisible', bool)(False)
        for sizer in self.parentsizers:
            sizer.Layout()

    def on_hide(self):
        self.splitter.shrinked = True
        self.orig_width = self.splitter.GetSize()[0] - self.splitter.GetSashPosition()
        button_width = self.button.GetSize()[0]
        self.orig_min_size = self.splitter.GetMinimumPaneSize()
        self.orig_gravity = self.splitter.GetSashGravity()
        self.splitter.SetMinimumPaneSize(button_width)
        self.splitter.SetSashGravity(1)
        self.splitter.SetSashPosition(self.splitter.GetSize()[0] - button_width)
        if getattr(self.splitter, 'SetSashSize', False):
            self.orig_sash_size = self.splitter.GetSashSize()
            self.splitter.SetSashSize(0)
        getattr(self.splitter, 'SetSashInvisible', bool)(True)
        for sizer in self.parentsizers:
            sizer.Layout()

class MainWindow(wx.Frame):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # this list will contain all controls that should be only enabled
        # when we're connected to a printer
        self.panel = wx.Panel(self)
        self.reset_ui()
        self.statefulControls = []

    def reset_ui(self):
        self.panels = []
        self.printerControls = []

    def newPanel(self, parent, add_to_list = True):
        panel = wx.Panel(parent)
        self.registerPanel(panel, add_to_list)
        return panel

    def registerPanel(self, panel, add_to_list = True):
        panel.SetBackgroundColour(self.bgcolor)
        if add_to_list:
            self.panels.append(panel)

    def createTabbedGui(self):
        self.notesizer = wx.BoxSizer(wx.VERTICAL)
        self.notebook = wx.Notebook(self.panel)
        self.notebook.SetBackgroundColour(self.bgcolor)
        page1panel = self.newPanel(self.notebook)
        page2panel = self.newPanel(self.notebook)
        self.mainsizer_page1 = wx.BoxSizer(wx.VERTICAL)
        page1panel1 = self.newPanel(page1panel)
        page1panel2 = self.newPanel(page1panel)
        self.toolbarsizer = MainToolbar(self, page1panel1, use_wrapsizer = True)
        page1panel1.SetSizer(self.toolbarsizer)
        self.mainsizer_page1.Add(page1panel1, 0, wx.EXPAND)
        self.lowersizer = wx.BoxSizer(wx.HORIZONTAL)
        page1panel2.SetSizer(self.lowersizer)
        leftsizer = wx.BoxSizer(wx.VERTICAL)
        controls_sizer = ControlsSizer(self, page1panel2, True)
        leftsizer.Add(controls_sizer, 1, wx.ALIGN_CENTER)
        rightsizer = wx.BoxSizer(wx.VERTICAL)
        extracontrols = wx.GridBagSizer()
        add_extra_controls(extracontrols, self, page1panel2, controls_sizer.extra_buttons)
        rightsizer.AddStretchSpacer()
        rightsizer.Add(extracontrols, 0, wx.ALIGN_CENTER)
        self.lowersizer.Add(leftsizer, 0, wx.ALIGN_CENTER | wx.RIGHT, border = 10)
        self.lowersizer.Add(rightsizer, 1, wx.ALIGN_CENTER)
        self.mainsizer_page1.Add(page1panel2, 1)
        self.mainsizer = wx.BoxSizer(wx.HORIZONTAL)
        self.splitterwindow = wx.SplitterWindow(page2panel, style = wx.SP_3D)
        page2sizer1 = wx.BoxSizer(wx.HORIZONTAL)
        page2panel1 = self.newPanel(self.splitterwindow)
        page2sizer2 = wx.BoxSizer(wx.HORIZONTAL)
        page2panel2 = self.newPanel(self.splitterwindow)
        vizpane = VizPane(self, page2panel1)
        page2sizer1.Add(vizpane, 1, wx.EXPAND)
        page2sizer2.Add(LogPane(self, page2panel2), 1, wx.EXPAND)
        page2panel1.SetSizer(page2sizer1)
        page2panel2.SetSizer(page2sizer2)
        self.splitterwindow.SetMinimumPaneSize(1)
        self.splitterwindow.SetSashGravity(0.5)
        self.splitterwindow.SplitVertically(page2panel1, page2panel2,
                                            self.settings.last_sash_position)
        self.mainsizer.Add(self.splitterwindow, 1, wx.EXPAND)
        page1panel.SetSizer(self.mainsizer_page1)
        page2panel.SetSizer(self.mainsizer)
        self.notesizer.Add(self.notebook, 1, wx.EXPAND)
        self.notebook.AddPage(page1panel, _("Commands"))
        self.notebook.AddPage(page2panel, _("Status"))
        if self.settings.uimode == _("Tabbed with platers"):
            from printrun.stlplater import StlPlaterPanel
            from printrun.gcodeplater import GcodePlaterPanel
            page3panel = StlPlaterPanel(parent = self.notebook,
                                        callback = self.platecb,
                                        build_dimensions = self.build_dimensions_list,
                                        circular_platform = self.settings.circular_bed,
                                        simarrange_path = self.settings.simarrange_path,
                                        antialias_samples = int(self.settings.antialias3dsamples))
            page4panel = GcodePlaterPanel(parent = self.notebook,
                                          callback = self.platecb,
                                          build_dimensions = self.build_dimensions_list,
                                          circular_platform = self.settings.circular_bed,
                                          antialias_samples = int(self.settings.antialias3dsamples))
            self.registerPanel(page3panel)
            self.registerPanel(page4panel)
            self.notebook.AddPage(page3panel, _("Plater"))
            self.notebook.AddPage(page4panel, _("G-Code Plater"))
        self.panel.SetSizer(self.notesizer)
        self.panel.Bind(wx.EVT_MOUSE_EVENTS, self.editbutton)

        # Custom buttons
        self.cbuttonssizer = wx.WrapSizer(wx.HORIZONTAL)
        self.centerpanel = self.newPanel(page1panel2)
        self.centerpanel.SetSizer(self.cbuttonssizer)
        rightsizer.Add(self.centerpanel, 0, wx.ALIGN_CENTER)
        rightsizer.AddStretchSpacer()

        self.panel.SetSizerAndFit(self.notesizer)

        self.cbuttons_reload()
        minsize = self.lowersizer.GetMinSize()  # lower pane
        minsize[1] = self.notebook.GetSize()[1]
        self.SetMinSize(self.ClientToWindowSize(minsize))  # client to window
        self.Fit()

    def createGui(self, compact = False, mini = False):
        self.mainsizer = wx.BoxSizer(wx.VERTICAL)
        self.lowersizer = wx.BoxSizer(wx.HORIZONTAL)
        upperpanel = self.newPanel(self.panel, False)
        self.toolbarsizer = MainToolbar(self, upperpanel)
        lowerpanel = self.newPanel(self.panel)
        upperpanel.SetSizer(self.toolbarsizer)
        lowerpanel.SetSizer(self.lowersizer)
        leftpanel = self.newPanel(lowerpanel)
        left_pane = LeftPaneToggleable(self, leftpanel, [self.lowersizer])
        leftpanel.SetSizer(left_pane)
        left_real_panel = left_pane.panepanel
        controls_panel = self.newPanel(left_real_panel)
        controls_sizer = ControlsSizer(self, controls_panel, mini_mode = mini)
        controls_panel.SetSizer(controls_sizer)
        left_sizer = wx.BoxSizer(wx.VERTICAL)
        left_sizer.Add(controls_panel, 1, wx.EXPAND)
        left_pane.set_sizer(left_sizer)
        self.lowersizer.Add(leftpanel, 0, wx.EXPAND)
        if compact:
            vizpanel = self.newPanel(lowerpanel)
            logpanel = self.newPanel(left_real_panel)
        else:
            # Use a splitterwindow to group viz and log
            rightpanel = self.newPanel(lowerpanel)
            rightsizer = wx.BoxSizer(wx.VERTICAL)
            rightpanel.SetSizer(rightsizer)
            self.splitterwindow = wx.SplitterWindow(rightpanel, style = wx.SP_3D | wx.SP_LIVE_UPDATE)
            self.splitterwindow.SetMinimumPaneSize(150)
            self.splitterwindow.SetSashGravity(0.8)
            rightsizer.Add(self.splitterwindow, 1, wx.EXPAND)
            vizpanel = self.newPanel(self.splitterwindow)
            logpanel = self.newPanel(self.splitterwindow)
            self.splitterwindow.SplitVertically(vizpanel, logpanel,
                                                self.settings.last_sash_position)
            self.splitterwindow.shrinked = False
        viz_pane = VizPane(self, vizpanel)
        # Custom buttons
        self.cbuttonssizer = wx.WrapSizer(wx.HORIZONTAL)
        self.centerpanel = self.newPanel(vizpanel)
        self.centerpanel.SetSizer(self.cbuttonssizer)
        viz_pane.Add(self.centerpanel, 0, flag = wx.ALIGN_CENTER)
        vizpanel.SetSizer(viz_pane)
        if compact:
            log_pane = LogPane(self, logpanel)
        else:
            log_pane = LogPaneToggleable(self, logpanel, [self.lowersizer])
            left_pane.parentsizers.append(self.splitterwindow)
        logpanel.SetSizer(log_pane)
        if compact:
            left_sizer.Add(logpanel, 1, wx.EXPAND)
            self.lowersizer.Add(vizpanel, 1, wx.EXPAND)
        else:
            self.lowersizer.Add(rightpanel, 1, wx.EXPAND)
        self.mainsizer.Add(upperpanel, 0, wx.EXPAND)
        self.mainsizer.Add(lowerpanel, 1, wx.EXPAND)
        self.panel.SetSizer(self.mainsizer)
        self.panel.Bind(wx.EVT_MOUSE_EVENTS, self.editbutton)

        self.mainsizer.Layout()
        # This prevents resizing below a reasonnable value
        # We sum the lowersizer (left pane / viz / log) min size
        # the toolbar height and the statusbar/menubar sizes
        minsize = [0, 0]
        minsize[0] = self.lowersizer.GetMinSize()[0]  # lower pane
        minsize[1] = max(viz_pane.GetMinSize()[1], controls_sizer.GetMinSize()[1])
        minsize[1] += self.toolbarsizer.GetMinSize()[1]  # toolbar height
        displaysize = wx.DisplaySize()
        minsize[0] = min(minsize[0], displaysize[0])
        minsize[1] = min(minsize[1], displaysize[1])
        self.SetMinSize(self.ClientToWindowSize(minsize))  # client to window

        self.cbuttons_reload()

    def gui_set_connected(self):
        self.xyb.enable()
        self.zb.enable()
        for control in self.printerControls:
            control.Enable()

    def gui_set_disconnected(self):
        self.printbtn.Disable()
        self.pausebtn.Disable()
        self.recoverbtn.Disable()
        for control in self.printerControls:
            control.Disable()
        self.xyb.disable()
        self.zb.disable()
