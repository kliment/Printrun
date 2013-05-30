#!/usr/bin/python

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

import os
import math

import wx
from wx import glcanvas

import pyglet
pyglet.options['debug_gl'] = True

from pyglet.gl import *
from pyglet import gl

from . import gcoder
from . import stltool
from .libtatlin import actors

class wxGLPanel(wx.Panel):
    '''A simple class for using OpenGL with wxPython.'''

    def __init__(self, parent, id, pos = wx.DefaultPosition,
                 size = wx.DefaultSize, style = 0):
        # Forcing a no full repaint to stop flickering
        style = style | wx.NO_FULL_REPAINT_ON_RESIZE
        super(wxGLPanel, self).__init__(parent, id, pos, size, style)

        self.GLinitialized = False
        attribList = (glcanvas.WX_GL_RGBA,  # RGBA
                      glcanvas.WX_GL_DOUBLEBUFFER,  # Double Buffered
                      glcanvas.WX_GL_DEPTH_SIZE, 24)  # 24 bit

        self.sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.canvas = glcanvas.GLCanvas(self, attribList = attribList)
        self.context = glcanvas.GLContext(self.canvas)
        self.sizer.Add(self.canvas, 1, wx.EXPAND)
        self.SetSizer(self.sizer)
        self.sizer.Fit(self)

        # bind events
        self.canvas.Bind(wx.EVT_ERASE_BACKGROUND, self.processEraseBackgroundEvent)
        self.canvas.Bind(wx.EVT_SIZE, self.processSizeEvent)
        self.canvas.Bind(wx.EVT_PAINT, self.processPaintEvent)

    def processEraseBackgroundEvent(self, event):
        '''Process the erase background event.'''
        pass  # Do nothing, to avoid flashing on MSWin

    def processSizeEvent(self, event):
        '''Process the resize event.'''
        if (wx.VERSION > (2,9) and self.canvas.IsShownOnScreen()) or self.canvas.GetContext():
            # Make sure the frame is shown before calling SetCurrent.
            size = self.GetClientSize()
            self.winsize = (size.width, size.height)
            self.width, self.height = size.width, size.height
            self.canvas.SetCurrent(self.context)
            self.OnReshape(size.width, size.height)
            self.canvas.Refresh(False)
        event.Skip()
        #wx.CallAfter(self.Refresh)

    def processPaintEvent(self, event):
        '''Process the drawing event.'''
        self.canvas.SetCurrent(self.context)
 
        if not self.GLinitialized:
            self.OnInitGL()
            self.GLinitialized = True

        self.OnDraw()
        event.Skip()

    def Destroy(self):
        #clean up the pyglet OpenGL context
        self.pygletcontext.destroy()
        #call the super method
        super(wx.Panel, self).Destroy()

    #==========================================================================
    # GLFrame OpenGL Event Handlers
    #==========================================================================
    def OnInitGL(self):
        '''Initialize OpenGL for use in the window.'''
        #create a pyglet context for this panel
        self.pmat = (GLdouble * 16)()
        self.mvmat = (GLdouble * 16)()
        self.pygletcontext = gl.Context(gl.current_context)
        self.pygletcontext.canvas = self
        self.pygletcontext.set_current()
        self.dist = 1000
        self.vpmat = None
        #normal gl init
        glClearColor(0.98, 0.98, 0.78, 1)
        glClearDepth(1.0)                # set depth value to 1
        glDepthFunc(GL_LEQUAL)
        glEnable(GL_COLOR_MATERIAL)
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_CULL_FACE)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        self.OnReshape(*self.GetClientSize())

    def OnReshape(self, width, height):
        '''Reshape the OpenGL viewport based on the dimensions of the window.'''
        if not self.GLinitialized:
            self.GLinitialized = True
            self.OnInitGL()
        glViewport(0, 0, width, height)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(60., width / float(height), .1, 1000.)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        self.vpmat = (GLint * 4)(0, 0, *list(self.GetClientSize()))
        glGetDoublev(GL_PROJECTION_MATRIX, self.pmat)

        # Wrap text to the width of the window
        if self.GLinitialized:
            self.pygletcontext.set_current()
            self.update_object_resize()

    def OnDraw(self, *args, **kwargs):
        """Draw the window."""
        self.pygletcontext.set_current()
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        self.draw_objects()
        self.canvas.SwapBuffers()

    #==========================================================================
    # To be implemented by a sub class
    #==========================================================================
    def create_objects(self):
        '''create opengl objects when opengl is initialized'''
        pass

    def update_object_resize(self):
        '''called when the window recieves only if opengl is initialized'''
        pass

    def draw_objects(self):
        '''called in the middle of ondraw after the buffer has been cleared'''
        pass

def trackball(p1x, p1y, p2x, p2y, r):
    TRACKBALLSIZE = r
#float a[3]; /* Axis of rotation */
#float phi;  /* how much to rotate about axis */
#float p1[3], p2[3], d[3];
#float t;

    if (p1x == p2x and p1y == p2y):
        return [0.0, 0.0, 0.0, 1.0]

    p1 = [p1x, p1y, project_to_sphere(TRACKBALLSIZE, p1x, p1y)]
    p2 = [p2x, p2y, project_to_sphere(TRACKBALLSIZE, p2x, p2y)]
    a = stltool.cross(p2, p1)

    d = map(lambda x, y: x - y, p1, p2)
    t = math.sqrt(sum(map(lambda x: x * x, d))) / (2.0 * TRACKBALLSIZE)

    if (t > 1.0):
        t = 1.0
    if (t < -1.0):
        t = -1.0
    phi = 2.0 * math.asin(t)

    return axis_to_quat(a, phi)


def vec(*args):
    return (GLfloat * len(args))(*args)


def axis_to_quat(a, phi):
    #print a, phi
    lena = math.sqrt(sum(map(lambda x: x * x, a)))
    q = map(lambda x: x * (1 / lena), a)
    q = map(lambda x: x * math.sin(phi / 2.0), q)
    q.append(math.cos(phi / 2.0))
    return q


def build_rotmatrix(q):
    m = (GLdouble * 16)()
    m[0] = 1.0 - 2.0 * (q[1] * q[1] + q[2] * q[2])
    m[1] = 2.0 * (q[0] * q[1] - q[2] * q[3])
    m[2] = 2.0 * (q[2] * q[0] + q[1] * q[3])
    m[3] = 0.0

    m[4] = 2.0 * (q[0] * q[1] + q[2] * q[3])
    m[5] = 1.0 - 2.0 * (q[2] * q[2] + q[0] * q[0])
    m[6] = 2.0 * (q[1] * q[2] - q[0] * q[3])
    m[7] = 0.0

    m[8] = 2.0 * (q[2] * q[0] - q[1] * q[3])
    m[9] = 2.0 * (q[1] * q[2] + q[0] * q[3])
    m[10] = 1.0 - 2.0 * (q[1] * q[1] + q[0] * q[0])
    m[11] = 0.0

    m[12] = 0.0
    m[13] = 0.0
    m[14] = 0.0
    m[15] = 1.0
    return m


def project_to_sphere(r, x, y):
    d = math.sqrt(x * x + y * y)
    if (d < r * 0.70710678118654752440):
        return math.sqrt(r * r - d * d)
    else:
        t = r / 1.41421356237309504880
        return t * t / d


def mulquat(q1, rq):
    return [q1[3] * rq[0] + q1[0] * rq[3] + q1[1] * rq[2] - q1[2] * rq[1],
                    q1[3] * rq[1] + q1[1] * rq[3] + q1[2] * rq[0] - q1[0] * rq[2],
                    q1[3] * rq[2] + q1[2] * rq[3] + q1[0] * rq[1] - q1[1] * rq[0],
                    q1[3] * rq[3] - q1[0] * rq[0] - q1[1] * rq[1] - q1[2] * rq[2]]


class GcodeViewPanel(wxGLPanel):

    def __init__(self, parent, id = wx.ID_ANY, build_dimensions = None, realparent = None):
        super(GcodeViewPanel, self).__init__(parent, id, wx.DefaultPosition, wx.DefaultSize, 0)
        self.batches = []
        self.rot = 0
        self.canvas.Bind(wx.EVT_MOUSE_EVENTS, self.move)
        self.canvas.Bind(wx.EVT_LEFT_DCLICK, self.double)
        self.canvas.Bind(wx.EVT_KEY_DOWN, self.keypress)
        self.initialized = 0
        self.canvas.Bind(wx.EVT_MOUSEWHEEL, self.wheel)
        self.parent = realparent if realparent else parent
        self.initpos = None
        if build_dimensions:
            self.dist = max(build_dimensions[0], build_dimensions[1])
        else:
            self.dist = 200
        self.transv = [0, 0, -self.dist]
        self.basequat = [0, 0, 0, 1]
        self.mousepos = [0, 0]

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
        if self.vpmat is None:
            return
        self.create_objects()

        if self.rot == 1:
            glLoadIdentity()
            glMultMatrixd(self.mvmat)
        else:
            glLoadIdentity()
            glTranslatef(*self.transv)
        
        glPushMatrix()
        glTranslatef(-self.parent.platform.width/2, -self.parent.platform.depth/2, 0)

        for obj in self.parent.objects:
            if not obj.model or not obj.model.loaded or not obj.model.initialized:
                continue
            glPushMatrix()
            glTranslatef(*(obj.offsets))
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
            if self.initpos == None:
                self.initpos = event.GetPositionTuple()
            else:
                #print self.initpos
                p1 = self.initpos
                self.initpos = None
                p2 = event.GetPositionTuple()
                sz = self.GetClientSize()
                p1x = (float(p1[0]) - sz[0] / 2) / (sz[0] / 2)
                p1y = -(float(p1[1]) - sz[1] / 2) / (sz[1] / 2)
                p2x = (float(p2[0]) - sz[0] / 2) / (sz[0] / 2)
                p2y = -(float(p2[1]) - sz[1] / 2) / (sz[1] / 2)
                #print p1x, p1y, p2x, p2y
                quat = trackball(p1x, p1y, p2x, p2y, -self.transv[2] / 250.0)
                if self.rot:
                    self.basequat = mulquat(self.basequat, quat)
                #else:
                glGetDoublev(GL_MODELVIEW_MATRIX, self.mvmat)
                #self.basequat = quatx
                mat = build_rotmatrix(self.basequat)
                glLoadIdentity()
                glTranslatef(self.transv[0], self.transv[1], 0)
                glTranslatef(0, 0, self.transv[2])
                glMultMatrixd(mat)
                glGetDoublev(GL_MODELVIEW_MATRIX, self.mvmat)
                self.rot = 1

        elif event.ButtonUp(wx.MOUSE_BTN_LEFT):
            if self.initpos is not None:
                self.initpos = None
        elif event.ButtonUp(wx.MOUSE_BTN_RIGHT):
            if self.initpos is not None:
                self.initpos = None

        elif event.Dragging() and event.RightIsDown():
            if self.initpos is None:
                self.initpos = event.GetPositionTuple()
            else:
                p1 = self.initpos
                p2 = event.GetPositionTuple()
                sz = self.GetClientSize()
                p1 = list(p1) + [0]
                p2 = list(p2) + [0]
                p1[1] *= -1
                p2[1] *= -1
                sz = list(sz) + [1]
                sz[0] *= 2
                sz[1] *= 2

                self.transv = map(lambda x, y, z, c: c - self.dist * (x - y) / z,  p1, p2,  sz,  self.transv)

                glLoadIdentity()
                glTranslatef(self.transv[0], self.transv[1], 0)
                glTranslatef(0, 0, self.transv[2])
                if self.rot:
                    glMultMatrixd(build_rotmatrix(self.basequat))
                glGetDoublev(GL_MODELVIEW_MATRIX, self.mvmat)
                self.rot = 1
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
        new_layer = min(max_layers, current_layer + 1)
        self.parent.model.num_layers_to_draw = new_layer
        wx.CallAfter(self.Refresh)

    def layerdown(self):
        if not self.parent.model:
            return
        current_layer = self.parent.model.num_layers_to_draw
        new_layer = max(1, current_layer - 1)
        self.parent.model.num_layers_to_draw = new_layer
        wx.CallAfter(self.Refresh)

    def zoom(self, dist):
        self.transv[2] += dist
        glLoadIdentity()
        glTranslatef(*self.transv)
        if self.rot:
            glMultMatrixd(build_rotmatrix(self.basequat))
        glGetDoublev(GL_MODELVIEW_MATRIX, self.mvmat)
        self.rot = 1
        wx.CallAfter(self.Refresh)

    def wheel(self, event):
        """react to mouse wheel actions:
            without shift: set max layer
            with shift: zoom viewport
        """
        z = event.GetWheelRotation()
        dist = 10
        if event.ShiftDown():
            if not self.parent.model:
                return
            if z > 0:
                self.layerup()
            else:
                self.layerdown()
            return
        if z > 0:
            self.zoom(dist)
        else:
            self.zoom(-dist)

    def keypress(self, event):
        """gets keypress events and moves/rotates acive shape"""
        keycode = event.GetKeyCode()
        step = 10
        if event.ControlDown():
            step = 3
        kup = [85, 315]               # Up keys
        kdo = [68, 317]               # Down Keys
        kzi = [wx.WXK_PAGEDOWN, 388, 316, 61]        # Zoom In Keys
        kzo = [wx.WXK_PAGEUP, 390, 314, 45]       # Zoom Out Keys
        x = event.GetKeyCode()
        if x in kup:
            self.layerup()
        if x in kdo:
            self.layerdown()
        if x in kzi:
            self.zoom(step)
        if x in kzo:
            self.zoom(-step)
        event.Skip()
        wx.CallAfter(self.Refresh)

class GCObject(object):

    def __init__(self, model):
        self.offsets = [0, 0, 0]
        self.rot = 0
        self.curlayer = 0.0
        self.scale = [1.0, 1.0, 1.0]
        self.batch = pyglet.graphics.Batch()
        self.model = model

class GcodeViewMainWrapper(object):
    
    def __init__(self, parent, build_dimensions):
        self.glpanel = GcodeViewPanel(parent, realparent = self, build_dimensions = build_dimensions)
        self.glpanel.SetMinSize((150, 150))
        self.clickcb = None
        self.widget = self.glpanel
        self.refresh_timer = wx.CallLater(100, self.Refresh)
        self.p = self # Hack for backwards compatibility with gviz API
        self.platform = actors.Platform(build_dimensions)
        self.model = None
        self.objects = [GCObject(self.platform), GCObject(None)]

    def __getattr__(self, name):
        return getattr(self.glpanel, name)

    def set_current_gline(self, gline):
        if gline.is_move and self.model and self.model.loaded:
            self.model.printed_until = gline.gcview_end_vertex
            if not self.refresh_timer.IsRunning():
                self.refresh_timer.Start()

    def addgcode(self, *a):
        pass

    def setlayer(self, *a):
        pass

    def addfile(self, gcode = None):
        self.model = actors.GcodeModel()
        if gcode:
            self.model.load_data(gcode)
        self.objects[-1].model = self.model
        wx.CallAfter(self.Refresh)

    def clear(self):
        self.model = None
        self.objects[-1].model = None
        wx.CallAfter(self.Refresh)

class GcodeViewFrame(wx.Frame):
    '''A simple class for using OpenGL with wxPython.'''

    def __init__(self, parent, ID, title, build_dimensions, objects = None,
                 pos = wx.DefaultPosition, size = wx.DefaultSize,
                 style = wx.DEFAULT_FRAME_STYLE):
        super(GcodeViewFrame, self).__init__(parent, ID, title, pos, size, style)
        self.refresh_timer = wx.CallLater(100, self.Refresh)
        self.p = self # Hack for backwards compatibility with gviz API
        self.clonefrom = objects
        self.platform = actors.Platform(build_dimensions)
        if objects:
            self.model = objects[1].model
        else:
            self.model = None
        self.objects = [GCObject(self.platform), GCObject(None)]
        self.glpanel = GcodeViewPanel(self, build_dimensions = build_dimensions)

    def set_current_gline(self, gline):
        if gline.is_move and self.model and self.model.loaded:
            self.model.printed_until = gline.gcview_end_vertex
            if not self.refresh_timer.IsRunning():
                self.refresh_timer.Start()

    def addfile(self, gcode = None):
        if self.clonefrom:
            self.model = self.clonefrom[-1].model.copy()
        else:
            self.model = actors.GcodeModel()
            if gcode:
                self.model.load_data(gcode)
        self.objects[-1].model = self.model
        wx.CallAfter(self.Refresh)

    def clear(self):
        self.model = None
        self.objects[-1].model = None
        wx.CallAfter(self.Refresh)

if __name__ == "__main__":
    import sys
    app = wx.App(redirect = False)
    build_dimensions = [200, 200, 100, 0, 0, 0]
    frame = GcodeViewFrame(None, wx.ID_ANY, 'Gcode view, shift to move view, mousewheel to set layer', size = (400, 400), build_dimensions = build_dimensions)
    gcode = gcoder.GCode(open(sys.argv[1]))
    frame.addfile(gcode)

    first_move = None
    for i in range(len(gcode.lines)):
        if gcode.lines[i].is_move:
            first_move = gcode.lines[i]
            break
    last_move = None
    for i in range(len(gcode.lines)-1,-1,-1):
        if gcode.lines[i].is_move:
            last_move = gcode.lines[i]
            break
    nsteps = 20
    steptime = 500
    lines = [first_move] + [gcode.lines[int(float(i)*(len(gcode.lines)-1)/nsteps)] for i in range(1, nsteps)] + [last_move]
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
