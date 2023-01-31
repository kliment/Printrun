#!/usr/bin/env python3

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
import wx

from . import gcoder
from .gl.panel import wxGLPanel
from .gl.trackball import build_rotmatrix
from .gl.libtatlin import actors
from .injectgcode import injector, injector_edit

from pyglet.gl import glPushMatrix, glPopMatrix, \
    glTranslatef, glRotatef, glScalef, glMultMatrixd, \
    glGetDoublev, GL_MODELVIEW_MATRIX, GLdouble

from .gviz import GvizBaseFrame

from .utils import imagefile, install_locale, get_home_pos
install_locale('pronterface')

def create_model(light):
    if light:
        return actors.GcodeModelLight()
    else:
        return actors.GcodeModel()

def gcode_dims(g):
    return ((g.xmin, g.xmax, g.width),
            (g.ymin, g.ymax, g.depth),
            (g.zmin, g.zmax, g.height))

def set_model_colors(model, root):
    for field in dir(model):
        if field.startswith("color_"):
            root_fieldname = "gcview_" + field
            if hasattr(root, root_fieldname):
                setattr(model, field, getattr(root, root_fieldname))

def recreate_platform(self, build_dimensions, circular, grid):
    self.platform = actors.Platform(build_dimensions, circular = circular, grid = grid)
    self.objects[0].model = self.platform
    wx.CallAfter(self.Refresh)

def set_gcview_params(self, path_width, path_height):
    self.path_halfwidth = path_width / 2
    self.path_halfheight = path_height / 2
    has_changed = False
    for obj in self.objects[1:]:
        if isinstance(obj.model, actors.GcodeModel):
            obj.model.set_path_size(self.path_halfwidth, self.path_halfheight)
            has_changed = True
    return has_changed

# E selected for Up because is above D
LAYER_UP_KEYS = ord('U'), ord('E'), wx.WXK_UP
LAYER_DOWN_KEYS = ord('D'), wx.WXK_DOWN
ZOOM_IN_KEYS = wx.WXK_PAGEDOWN, 388, wx.WXK_RIGHT, ord('=')
ZOOM_OUT_KEYS = wx.WXK_PAGEUP, 390, wx.WXK_LEFT, ord('-')
FIT_KEYS = [ord('F')]
CURRENT_LAYER_KEYS = [ord('C')]
RESET_KEYS = [ord('R')]

class GcodeViewPanel(wxGLPanel):

    def __init__(self, parent,
                 build_dimensions = (200, 200, 100, 0, 0, 0),
                 realparent = None, antialias_samples = 0, perspective=False):
        if perspective:
            self.orthographic=False
        super().__init__(parent, wx.DefaultPosition,
                                             wx.DefaultSize, 0,
                                             antialias_samples = antialias_samples)
        self.canvas.Bind(wx.EVT_MOUSE_EVENTS, self.move)
        self.canvas.Bind(wx.EVT_LEFT_DCLICK, self.double)
        # self.canvas.Bind(wx.EVT_KEY_DOWN, self.keypress)
        # in Windows event inspector shows only EVT_CHAR_HOOK events
        self.canvas.Bind(wx.EVT_CHAR_HOOK, self.keypress)
        self.initialized = 0
        self.canvas.Bind(wx.EVT_MOUSEWHEEL, self.wheel)
        self.parent = realparent or parent
        self.initpos = None
        self.build_dimensions = build_dimensions
        self.dist = max(self.build_dimensions[:2])
        self.basequat = [0, 0, 0, 1]
        self.mousepos = [0, 0]

    def inject(self):
        l = self.parent.model.num_layers_to_draw
        filtered = [k for k, v in self.parent.model.layer_idxs_map.items() if v == l]
        if filtered:
            injector(self.parent.model.gcode, l, filtered[0])
        else:
            logging.error(_("Invalid layer for injection"))

    def editlayer(self):
        l = self.parent.model.num_layers_to_draw
        filtered = [k for k, v in self.parent.model.layer_idxs_map.items() if v == l]
        if filtered:
            injector_edit(self.parent.model.gcode, l, filtered[0])
        else:
            logging.error(_("Invalid layer for edition"))

    def setlayercb(self, layer):
        pass

    def OnInitGL(self, *args, **kwargs):
        super().OnInitGL(*args, **kwargs)
        filenames = getattr(self.parent, 'filenames', None)
        if filenames:
            for filename in filenames:
                self.parent.load_file(filename)
            self.parent.autoplate()
            getattr(self.parent, 'loadcb', bool)()
            self.parent.filenames = None

    def create_objects(self):
        '''create opengl objects when opengl is initialized'''
        for obj in self.parent.objects:
            if obj.model and obj.model.loaded and not obj.model.initialized:
                obj.model.init()

    def update_object_resize(self):
        '''called when the window receives only if opengl is initialized'''
        pass

    def draw_objects(self):
        '''called in the middle of ondraw after the buffer has been cleared'''
        self.create_objects()

        glPushMatrix()
        # Rotate according to trackball
        glMultMatrixd(build_rotmatrix(self.basequat))
        # Move origin to bottom left of platform
        platformx0 = -self.build_dimensions[3] - self.parent.platform.width / 2
        platformy0 = -self.build_dimensions[4] - self.parent.platform.depth / 2
        glTranslatef(platformx0, platformy0, 0)

        for obj in self.parent.objects:
            if not obj.model \
               or not obj.model.loaded:
                continue
            # Skip (comment out) initialized check, which safely causes empty 
            # model during progressive load. This can cause exceptions/garbage
            # render, but seems fine for now
            # May need to lock init() and draw_objects() together
            # if not obj.model.initialized:
            #     continue
            glPushMatrix()
            glTranslatef(*(obj.offsets))
            glRotatef(obj.rot, 0.0, 0.0, 1.0)
            glTranslatef(*(obj.centeroffset))
            glScalef(*obj.scale)

            obj.model.display()
            glPopMatrix()
        glPopMatrix()

    # ==========================================================================
    # Utils
    # ==========================================================================
    def get_modelview_mat(self, local_transform):
        mvmat = (GLdouble * 16)()
        if local_transform:
            glPushMatrix()
            # Rotate according to trackball
            glMultMatrixd(build_rotmatrix(self.basequat))
            # Move origin to bottom left of platform
            platformx0 = -self.build_dimensions[3] - self.parent.platform.width / 2
            platformy0 = -self.build_dimensions[4] - self.parent.platform.depth / 2
            glTranslatef(platformx0, platformy0, 0)
            glGetDoublev(GL_MODELVIEW_MATRIX, mvmat)
            glPopMatrix()
        else:
            glGetDoublev(GL_MODELVIEW_MATRIX, mvmat)
        return mvmat

    def double(self, event):
        getattr(self.parent, 'clickcb', bool)(event)

    def move(self, event):
        """react to mouse actions:
        no mouse: show red mousedrop
        LMB: rotate viewport
        RMB: move viewport
        """
        if event.Entering():
            self.canvas.SetFocus()
            event.Skip()
            return
        if event.Dragging():
            if event.LeftIsDown():
                self.handle_rotation(event)
            elif event.RightIsDown():
                self.handle_translation(event)
            self.Refresh(False)
        elif event.LeftUp() or event.RightUp():
            self.initpos = None
        event.Skip()

    def layerup(self):
        if not getattr(self.parent, 'model', False):
            return
        max_layers = self.parent.model.max_layers
        current_layer = self.parent.model.num_layers_to_draw
        # accept going up to max_layers + 1
        # max_layers means visualizing the last layer differently,
        # max_layers + 1 means visualizing all layers with the same color
        new_layer = min(max_layers + 1, current_layer + 1)
        self.parent.model.num_layers_to_draw = new_layer
        self.parent.setlayercb(new_layer)
        wx.CallAfter(self.Refresh)

    def layerdown(self):
        if not getattr(self.parent, 'model', False):
            return
        current_layer = self.parent.model.num_layers_to_draw
        new_layer = max(1, current_layer - 1)
        self.parent.model.num_layers_to_draw = new_layer
        self.parent.setlayercb(new_layer)
        wx.CallAfter(self.Refresh)

    wheelTimestamp = None
    def handle_wheel(self, event):
        if self.wheelTimestamp == event.Timestamp:
            # filter duplicate event delivery in Ubuntu, Debian issue #1110
            return  

        self.wheelTimestamp = event.Timestamp

        delta = event.GetWheelRotation()
        factor = 1.05
        if event.ControlDown():
            factor = 1.02
        if hasattr(self.parent, "model") and event.ShiftDown():
            if not self.parent.model:
                return
            count = 1 if not event.ControlDown() else 10
            for i in range(count):
                if delta > 0: self.layerup()
                else: self.layerdown()
            return
        x, y = event.GetPosition() * self.GetContentScaleFactor()
        x, y, _ = self.mouse_to_3d(x, y)
        if delta > 0:
            self.zoom(factor, (x, y))
        else:
            self.zoom(1 / factor, (x, y))

    def wheel(self, event):
        """react to mouse wheel actions:
            without shift: set max layer
            with shift: zoom viewport
        """
        self.handle_wheel(event)
        wx.CallAfter(self.Refresh)

    def fit(self):
        if not self.parent.model or not self.parent.model.loaded:
            return
        self.canvas.SetCurrent(self.context)
        dims = gcode_dims(self.parent.model.gcode)
        self.reset_mview(1.0)
        center_x = (dims[0][0] + dims[0][1]) / 2
        center_y = (dims[1][0] + dims[1][1]) / 2
        center_x = self.build_dimensions[0] / 2 - center_x
        center_y = self.build_dimensions[1] / 2 - center_y
        if self.orthographic:
            ratio = float(self.dist) / max(dims[0][2], dims[1][2])
            glScalef(ratio, ratio, 1)
        glTranslatef(center_x, center_y, 0)
        wx.CallAfter(self.Refresh)

    def keypress(self, event):
        """gets keypress events and moves/rotates active shape"""
        if event.HasModifiers():
            # let alt+c bubble up
            event.Skip()
            return
        step = event.ControlDown() and 1.05 or 1.1
        key = event.GetKeyCode()
        if key in LAYER_UP_KEYS:
            self.layerup()
            return  # prevent shifting focus to other controls
        elif key in LAYER_DOWN_KEYS:
            self.layerdown()
            return
        # x, y, _ = self.mouse_to_3d(self.width / 2, self.height / 2)
        elif key in ZOOM_IN_KEYS:
            self.zoom_to_center(step)
            return
        elif key in ZOOM_OUT_KEYS:
            self.zoom_to_center(1 / step)
            return
        elif key in FIT_KEYS:
            self.fit()
        elif key in CURRENT_LAYER_KEYS:
            if not self.parent.model or not self.parent.model.loaded:
                return
            self.parent.model.only_current = not self.parent.model.only_current
            wx.CallAfter(self.Refresh)
        elif key in RESET_KEYS:
            self.resetview()
        event.Skip()

    def resetview(self):
        self.canvas.SetCurrent(self.context)
        self.reset_mview(0.9)
        self.basequat = [0, 0, 0, 1]
        wx.CallAfter(self.Refresh)

class GCObject:

    def __init__(self, model):
        self.offsets = [0, 0, 0]
        self.centeroffset = [0, 0, 0]
        self.rot = 0
        self.curlayer = 0.0
        self.scale = [1.0, 1.0, 1.0]
        self.model = model

class GcodeViewLoader:

    path_halfwidth = 0.2
    path_halfheight = 0.15

    def addfile_perlayer(self, gcode = None, showall = False):
        self.model = create_model(self.root.settings.light3d
                                  if self.root else False)
        if isinstance(self.model, actors.GcodeModel):
            self.model.set_path_size(self.path_halfwidth, self.path_halfheight)
        self.objects[-1].model = self.model
        if self.root:
            set_model_colors(self.model, self.root)
        if gcode is not None:
            generator = self.model.load_data(gcode)
            generator_output = next(generator)
            while generator_output is not None:
                yield generator_output
                generator_output = next(generator)
        wx.CallAfter(self.Refresh)
        yield None

    def addfile(self, gcode = None, showall = False):
        generator = self.addfile_perlayer(gcode, showall)
        while next(generator) is not None:
            continue

    def set_gcview_params(self, path_width, path_height):
        return set_gcview_params(self, path_width, path_height)

from printrun.gviz import BaseViz
class GcodeViewMainWrapper(GcodeViewLoader, BaseViz):

    def __init__(self, parent, build_dimensions, root, circular, antialias_samples, grid, perspective=False):
        self.root = root
        self.glpanel = GcodeViewPanel(parent, realparent = self,
                                      build_dimensions = build_dimensions,
                                      antialias_samples = antialias_samples, perspective=perspective)
        self.glpanel.SetMinSize((150, 150))
        if self.root and hasattr(self.root, "gcview_color_background"):
            self.glpanel.color_background = self.root.gcview_color_background
        self.clickcb = None
        self.widget = self.glpanel
        self.refresh_timer = wx.CallLater(100, self.Refresh)
        self.p = self  # Hack for backwards compatibility with gviz API
        self.grid = grid
        self.platform = actors.Platform(build_dimensions, circular = circular, grid = grid)
        self.model = None
        self.objects = [GCObject(self.platform), GCObject(None)]

    def __getattr__(self, name):
        return getattr(self.glpanel, name)

    def on_settings_change(self, changed_settings):
        if self.model:
            for s in changed_settings:
                if s.name.startswith('gcview_color_'):
                    self.model.update_colors()
                    break

    def set_current_gline(self, gline):
        if gline.is_move and gline.gcview_end_vertex is not None \
           and self.model and self.model.loaded:
            self.model.printed_until = gline.gcview_end_vertex
            if not self.refresh_timer.IsRunning():
                self.refresh_timer.Start()

    def recreate_platform(self, build_dimensions, circular, grid):
        return recreate_platform(self, build_dimensions, circular, grid)

    def setlayer(self, layer):
        if layer in self.model.layer_idxs_map:
            viz_layer = self.model.layer_idxs_map[layer]
            self.parent.model.num_layers_to_draw = viz_layer
            wx.CallAfter(self.Refresh)

    def clear(self):
        self.model = None
        self.objects[-1].model = None
        wx.CallAfter(self.Refresh)

class GcodeViewFrame(GvizBaseFrame, GcodeViewLoader):
    '''A simple class for using OpenGL with wxPython.'''

    def __init__(self, parent, ID, title, build_dimensions, objects = None,
                 pos = wx.DefaultPosition, size = wx.DefaultSize,
                 style = wx.DEFAULT_FRAME_STYLE, root = None, circular = False,
                 antialias_samples = 0,
                 grid = (1, 10), perspective=False):
        GvizBaseFrame.__init__(self, parent, ID, title,
                               pos, size, style)
        self.root = root

        panel, vbox = self.create_base_ui()

        self.refresh_timer = wx.CallLater(100, self.Refresh)
        self.p = self  # Hack for backwards compatibility with gviz API
        self.clonefrom = objects
        self.platform = actors.Platform(build_dimensions, circular = circular, grid = grid)
        self.model = objects[1].model if objects else None
        self.objects = [GCObject(self.platform), GCObject(None)]

        fit_image = wx.Image(imagefile('fit.png'), wx.BITMAP_TYPE_PNG).ConvertToBitmap()
        self.toolbar.InsertTool(6, 8, " " + _("Fit to plate"), fit_image,
                                     shortHelp = _("Fit to plate [F]"),
                                     longHelp = '')
        self.toolbar.Realize()
        self.glpanel = GcodeViewPanel(panel,
                                      build_dimensions = build_dimensions,
                                      realparent = self,
                                      antialias_samples = antialias_samples, perspective=perspective)
        vbox.Add(self.glpanel, 1, flag = wx.EXPAND)

        self.Bind(wx.EVT_TOOL, lambda x: self.glpanel.zoom_to_center(1.2), id = 1)
        self.Bind(wx.EVT_TOOL, lambda x: self.glpanel.zoom_to_center(1 / 1.2), id = 2)
        self.Bind(wx.EVT_TOOL, lambda x: self.glpanel.layerup(), id = 3)
        self.Bind(wx.EVT_TOOL, lambda x: self.glpanel.layerdown(), id = 4)
        self.Bind(wx.EVT_TOOL, lambda x: self.glpanel.resetview(), id = 5)
        self.Bind(wx.EVT_TOOL, lambda x: self.glpanel.fit(), id = 8)
        self.Bind(wx.EVT_TOOL, lambda x: self.glpanel.inject(), id = 6)
        self.Bind(wx.EVT_TOOL, lambda x: self.glpanel.editlayer(), id = 7)

    def setlayercb(self, layer):
        self.layerslider.SetValue(layer)
        self.update_status("")

    def update_status(self, extra):
        layer = self.model.num_layers_to_draw
        filtered = [k for k, v in self.model.layer_idxs_map.items() if v == layer]
        if filtered:
            true_layer = filtered[0]
            z = self.model.gcode.all_layers[true_layer].z
            message = _("Layer %d -%s Z = %.03f mm") % (layer, extra, z)
        else:
            message = _("Entire object")
        wx.CallAfter(self.SetStatusText, message, 0)

    def process_slider(self, event):
        if self.model is not None:
            new_layer = self.layerslider.GetValue()
            new_layer = min(self.model.max_layers + 1, new_layer)
            new_layer = max(1, new_layer)
            self.model.num_layers_to_draw = new_layer
            self.update_status("")
            wx.CallAfter(self.Refresh)
        else:
            logging.info(_("G-Code view, can't process slider. Please wait until model is loaded completely."))

    def set_current_gline(self, gline):
        if gline.is_move and gline.gcview_end_vertex is not None \
           and self.model and self.model.loaded:
            self.model.printed_until = gline.gcview_end_vertex
            if not self.refresh_timer.IsRunning():
                self.refresh_timer.Start()

    def recreate_platform(self, build_dimensions, circular, grid):
        return recreate_platform(self, build_dimensions, circular, grid)

    def addfile(self, gcode = None):
        if self.clonefrom:
            self.model = self.clonefrom[-1].model.copy()
            self.objects[-1].model = self.model
        else:
            GcodeViewLoader.addfile(self, gcode)
        self.layerslider.SetRange(1, self.model.max_layers + 1)
        self.layerslider.SetValue(self.model.max_layers + 1)
        wx.CallAfter(self.SetStatusText, _("Entire object"), 0)
        wx.CallAfter(self.Refresh)

    def clear(self):
        self.model = None
        self.objects[-1].model = None
        wx.CallAfter(self.Refresh)

if __name__ == "__main__":
    import sys
    app = wx.App(redirect = False)
    build_dimensions = [200, 200, 100, 0, 0, 0]
    title = 'Gcode view, shift to move view, mousewheel to set layer'
    frame = GcodeViewFrame(None, wx.ID_ANY, title, size = (400, 400),
                           build_dimensions = build_dimensions)
    gcode = gcoder.GCode(open(sys.argv[1]), get_home_pos(build_dimensions))
    frame.addfile(gcode)

    first_move = None
    for i in range(len(gcode.lines)):
        if gcode.lines[i].is_move:
            first_move = gcode.lines[i]
            break
    last_move = None
    for i in range(len(gcode.lines) - 1, -1, -1):
        if gcode.lines[i].is_move:
            last_move = gcode.lines[i]
            break
    nsteps = 20
    steptime = 500
    lines = [first_move] + [gcode.lines[int(float(i) * (len(gcode.lines) - 1) / nsteps)] for i in range(1, nsteps)] + [last_move]
    current_line = 0

    def setLine():
        global current_line
        frame.set_current_gline(lines[current_line])
        current_line = (current_line + 1) % len(lines)
        timer.Start()
    timer = wx.CallLater(steptime, setLine)
    timer.Start()

    frame.Show(True)
    app.MainLoop()
    app.Destroy()
