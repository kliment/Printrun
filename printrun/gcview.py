#!/usr/bin/env python

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

from . import gcoder
from .gl.panel import wxGLPanel
from .gl.trackball import build_rotmatrix
from .gl.libtatlin import actors
from .gl.libtatlin.actors import vec

from pyglet.gl import glPushMatrix, glPopMatrix, \
    glTranslatef, glRotatef, glScalef, glMultMatrixd
from pyglet.gl import *

from .gviz import GvizBaseFrame

from printrun_utils import imagefile, install_locale, get_home_pos
install_locale('pronterface')

def create_model(light):
    if light:
        return actors.GcodeModelLight()
    else:
        return actors.GcodeModel()

class GcodeViewPanel(wxGLPanel):

    def __init__(self, parent, id = wx.ID_ANY,
                 build_dimensions = None, realparent = None):
        super(GcodeViewPanel, self).__init__(parent, id, wx.DefaultPosition,
                                             wx.DefaultSize, 0)
        self.canvas.Bind(wx.EVT_MOUSE_EVENTS, self.move)
        self.canvas.Bind(wx.EVT_LEFT_DCLICK, self.double)
        self.canvas.Bind(wx.EVT_KEY_DOWN, self.keypress)
        self.initialized = 0
        self.canvas.Bind(wx.EVT_MOUSEWHEEL, self.wheel)
        self.parent = realparent if realparent else parent
        self.initpos = None
        if build_dimensions:
            self.build_dimensions = build_dimensions
        else:
            self.build_dimensions = [200, 200, 100, 0, 0, 0]
        self.dist = max(self.build_dimensions[0], self.build_dimensions[1])
        self.basequat = [0, 0, 0, 1]
        self.mousepos = [0, 0]

    def setlayercb(self, layer):
        pass

    def OnInitGL(self, *args, **kwargs):
        super(GcodeViewPanel, self).OnInitGL(*args, **kwargs)
        if hasattr(self.parent, "filenames") and self.parent.filenames:
            for filename in self.parent.filenames:
                self.parent.load_file(filename)
            self.parent.autoplate()
            if hasattr(self.parent, "loadcb"):
                self.parent.loadcb()
            self.parent.filenames = None

    def create_objects(self):
        '''create opengl objects when opengl is initialized'''
        for obj in self.parent.objects:
            if obj.model and obj.model.loaded and not obj.model.initialized:
                obj.model.init()

    def update_object_resize(self):
        '''called when the window recieves only if opengl is initialized'''
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

        light_z = max(self.parent.platform.width, self.parent.platform.depth)
        glLightfv(GL_LIGHT0, GL_POSITION, vec(0,
                                              self.parent.platform.depth / 2,
                                              light_z, 0))
        glLightfv(GL_LIGHT1, GL_POSITION, vec(self.parent.platform.width,
                                              self.parent.platform.depth / 2,
                                              light_z, 0))

        for obj in self.parent.objects:
            if not obj.model \
               or not obj.model.loaded \
               or not obj.model.initialized:
                continue
            glPushMatrix()
            glTranslatef(*(obj.offsets))
            glTranslatef(*(obj.centeroffset))
            glRotatef(obj.rot, 0.0, 0.0, 1.0)
            glScalef(*obj.scale)

            obj.model.display()
            glPopMatrix()
        glPopMatrix()

    def double(self, event):
        if self.parent.clickcb:
            self.parent.clickcb(event)

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
        if event.Dragging() and event.LeftIsDown():
            self.handle_rotation(event)
        elif event.Dragging() and event.RightIsDown():
            self.handle_translation(event)
        elif event.LeftUp():
            self.initpos = None
        elif event.RightUp():
            self.initpos = None
        else:
            event.Skip()
            return
        event.Skip()
        wx.CallAfter(self.Refresh)

    def layerup(self):
        if not self.parent.model:
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
        if not self.parent.model:
            return
        current_layer = self.parent.model.num_layers_to_draw
        new_layer = max(1, current_layer - 1)
        self.parent.model.num_layers_to_draw = new_layer
        self.parent.setlayercb(new_layer)
        wx.CallAfter(self.Refresh)

    def handle_wheel(self, event):
        delta = event.GetWheelRotation()
        factor = 1.05
        if hasattr(self.parent, "model") and event.ShiftDown():
            if not self.parent.model:
                return
            count = 1 if not event.ControlDown() else 10
            for i in range(count):
                if delta > 0: self.layerup()
                else: self.layerdown()
            return
        x, y = event.GetPositionTuple()
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
        dims = self.parent.model.dims
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
        """gets keypress events and moves/rotates acive shape"""
        step = 1.1
        if event.ControlDown():
            step = 1.05
        kup = [85, 315]               # Up keys
        kdo = [68, 317]               # Down Keys
        kzi = [wx.WXK_PAGEDOWN, 388, 316, 61]        # Zoom In Keys
        kzo = [wx.WXK_PAGEUP, 390, 314, 45]       # Zoom Out Keys
        kfit = [70]       # Fit to print keys
        kshowcurrent = [67]       # Show only current layer keys
        kreset = [82]       # Reset keys
        key = event.GetKeyCode()
        if key in kup:
            self.layerup()
        if key in kdo:
            self.layerdown()
        x, y, _ = self.mouse_to_3d(self.width / 2, self.height / 2)
        if key in kzi:
            self.zoom_to_center(step)
        if key in kzo:
            self.zoom_to_center(1 / step)
        if key in kfit:
            self.fit()
        if key in kshowcurrent:
            if not self.parent.model or not self.parent.model.loaded:
                return
            self.parent.model.only_current = not self.parent.model.only_current
            wx.CallAfter(self.Refresh)
        if key in kreset:
            self.resetview()
        event.Skip()

    def resetview(self):
        self.canvas.SetCurrent(self.context)
        self.reset_mview(0.9)
        self.basequat = [0, 0, 0, 1]
        wx.CallAfter(self.Refresh)

class GCObject(object):

    def __init__(self, model):
        self.offsets = [0, 0, 0]
        self.centeroffset = [0, 0, 0]
        self.rot = 0
        self.curlayer = 0.0
        self.scale = [1.0, 1.0, 1.0]
        self.model = model

class GcodeViewMainWrapper(object):

    def __init__(self, parent, build_dimensions, root):
        self.root = root
        self.glpanel = GcodeViewPanel(parent, realparent = self,
                                      build_dimensions = build_dimensions)
        self.glpanel.SetMinSize((150, 150))
        self.clickcb = None
        self.widget = self.glpanel
        self.refresh_timer = wx.CallLater(100, self.Refresh)
        self.p = self  # Hack for backwards compatibility with gviz API
        self.platform = actors.Platform(build_dimensions)
        self.model = None
        self.objects = [GCObject(self.platform), GCObject(None)]

    def __getattr__(self, name):
        return getattr(self.glpanel, name)

    def set_current_gline(self, gline):
        if gline.is_move and gline.gcview_end_vertex is not None \
           and self.model and self.model.loaded:
            self.model.printed_until = gline.gcview_end_vertex
            if not self.refresh_timer.IsRunning():
                self.refresh_timer.Start()

    def addgcode(self, *a):
        pass

    def setlayer(self, *a):
        pass

    def addfile(self, gcode = None, showall = False):
        self.model = create_model(self.root.settings.light3d
                                  if self.root else False)
        if gcode:
            self.model.load_data(gcode)
        self.objects[-1].model = self.model
        wx.CallAfter(self.Refresh)

    def clear(self):
        self.model = None
        self.objects[-1].model = None
        wx.CallAfter(self.Refresh)

class GcodeViewFrame(GvizBaseFrame):
    '''A simple class for using OpenGL with wxPython.'''

    def __init__(self, parent, ID, title, build_dimensions, objects = None,
                 pos = wx.DefaultPosition, size = wx.DefaultSize,
                 style = wx.DEFAULT_FRAME_STYLE, root = None):
        super(GcodeViewFrame, self).__init__(parent, ID, title,
                                             pos, size, style)
        self.root = root

        panel, vbox = self.create_base_ui()

        self.refresh_timer = wx.CallLater(100, self.Refresh)
        self.p = self  # Hack for backwards compatibility with gviz API
        self.clonefrom = objects
        self.platform = actors.Platform(build_dimensions)
        if objects:
            self.model = objects[1].model
        else:
            self.model = None
        self.objects = [GCObject(self.platform), GCObject(None)]

        fit_image = wx.Image(imagefile('fit.png'), wx.BITMAP_TYPE_PNG).ConvertToBitmap()
        self.toolbar.AddLabelTool(6, " " + _("Fit to plate"), fit_image,
                                  shortHelp = _("Fit to plate [F]"),
                                  longHelp = '')
        self.toolbar.Realize()
        self.glpanel = GcodeViewPanel(panel,
                                      build_dimensions = build_dimensions,
                                      realparent = self)
        vbox.Add(self.glpanel, 1, flag = wx.EXPAND)

        self.Bind(wx.EVT_TOOL, lambda x: self.glpanel.zoom_to_center(1.2), id = 1)
        self.Bind(wx.EVT_TOOL, lambda x: self.glpanel.zoom_to_center(1 / 1.2), id = 2)
        self.Bind(wx.EVT_TOOL, lambda x: self.glpanel.layerup(), id = 3)
        self.Bind(wx.EVT_TOOL, lambda x: self.glpanel.layerdown(), id = 4)
        self.Bind(wx.EVT_TOOL, lambda x: self.glpanel.resetview(), id = 5)
        self.Bind(wx.EVT_TOOL, lambda x: self.glpanel.fit(), id = 6)

    def process_slider(self, event):
        new_layer = self.layerslider.GetValue()
        new_layer = min(self.model.max_layers + 1, new_layer)
        new_layer = max(1, new_layer)
        self.model.num_layers_to_draw = new_layer
        wx.CallAfter(self.Refresh)

    def set_current_gline(self, gline):
        if gline.is_move and gline.gcview_end_vertex is not None \
           and self.model and self.model.loaded:
            self.model.printed_until = gline.gcview_end_vertex
            if not self.refresh_timer.IsRunning():
                self.refresh_timer.Start()

    def addfile(self, gcode = None):
        if self.clonefrom:
            self.model = self.clonefrom[-1].model.copy()
        else:
            self.model = create_model(self.root.settings.light3d
                                      if self.root else False)
            if gcode:
                self.model.load_data(gcode)
        self.objects[-1].model = self.model
        self.layerslider.SetRange(1, self.model.max_layers + 1)
        self.layerslider.SetValue(self.model.max_layers + 1)
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
