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

import traceback
import logging

import wx

class BaseViz:
    def clear(self, *a):
        pass

    def addfile_perlayer(self, gcode, showall = False):
        layer_idx = 0
        while layer_idx < len(gcode.all_layers):
            yield layer_idx
            layer_idx += 1
        yield None

    def addfile(self, *a, **kw):
        pass

    def addgcodehighlight(self, *a, **kw):
        pass

    def setlayer(self, *a):
        pass

    def on_settings_change(self, changed_settings):
        pass

class NoViz(BaseViz):
    showall = False
    def Refresh(self, *a):
        pass

class NoVizWindow:

    def __init__(self):
        self.p = NoViz()

    def Destroy(self):
        pass

class VizPane(wx.BoxSizer):

    def __init__(self, root, parentpanel = None):
        super(VizPane, self).__init__(wx.VERTICAL)
        if not parentpanel: parentpanel = root.panel
        if root.settings.mainviz == "None":
            root.gviz = NoViz()
            root.gwindow = NoVizWindow()
            return
        use2dview = root.settings.mainviz == "2D"
        if root.settings.mainviz == "3D":
            try:
                import printrun.gcview
                root.gviz = printrun.gcview.GcodeViewMainWrapper(
                    parentpanel,
                    root.build_dimensions_list,
                    root = root,
                    circular = root.settings.circular_bed,
                    antialias_samples = int(root.settings.antialias3dsamples),
                    grid = (root.settings.preview_grid_step1, root.settings.preview_grid_step2),
                    perspective = root.settings.perspective)
                root.gviz.clickcb = root.show_viz_window
            except:
                use2dview = True
                logging.error("3D view mode requested, but we failed to initialize it.\n"
                              + "Falling back to 2D view, and here is the backtrace:\n"
                              + traceback.format_exc())
        if use2dview:
            from printrun import gviz
            root.gviz = gviz.Gviz(parentpanel, (300, 300),
                                  build_dimensions = root.build_dimensions_list,
                                  grid = (root.settings.preview_grid_step1, root.settings.preview_grid_step2),
                                  extrusion_width = root.settings.preview_extrusion_width,
                                  bgcolor = root.bgcolor)
            root.gviz.SetToolTip(wx.ToolTip(_("Click to examine / edit\n  layers of loaded file")))
            root.gviz.showall = 1
            root.gviz.Bind(wx.EVT_LEFT_DOWN, root.show_viz_window)
        use3dview = root.settings.viz3d
        if use3dview:
            try:
                import printrun.gcview
                objects = None
                if isinstance(root.gviz, printrun.gcview.GcodeViewMainWrapper):
                    objects = root.gviz.objects
                root.gwindow = printrun.gcview.GcodeViewFrame(None, wx.ID_ANY, 'Gcode view, shift to move view, mousewheel to set layer',
                    size = (600, 600),
                    build_dimensions = root.build_dimensions_list,
                    objects = objects,
                    root = root,
                    circular = root.settings.circular_bed,
                    antialias_samples = int(root.settings.antialias3dsamples),
                    grid = (root.settings.preview_grid_step1, root.settings.preview_grid_step2),
                    perspective=root.settings.perspective)
            except:
                use3dview = False
                logging.error("3D view mode requested, but we failed to initialize it.\n"
                              + "Falling back to 2D view, and here is the backtrace:\n"
                              + traceback.format_exc())
        if not use3dview:
            from printrun import gviz
            root.gwindow = gviz.GvizWindow(build_dimensions = root.build_dimensions_list,
                                           grid = (root.settings.preview_grid_step1, root.settings.preview_grid_step2),
                                           extrusion_width = root.settings.preview_extrusion_width,
                                           bgcolor = root.bgcolor)
        root.gwindow.Bind(wx.EVT_CLOSE, lambda x: root.gwindow.Hide())
        if not isinstance(root.gviz, NoViz):
            self.Add(root.gviz.widget, 1, flag = wx.EXPAND)
