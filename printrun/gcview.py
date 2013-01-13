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
import time
import threading

import pyglet
pyglet.options['shadow_window'] = False
pyglet.options['debug_gl'] = False
from pyglet.gl import *

import stltool

import threading


class GLPanel(wx.Panel):
    '''A simple class for using OpenGL with wxPython.'''

    def __init__(self, parent, id, pos = wx.DefaultPosition,
                 size = wx.DefaultSize, style = 0):
        # Forcing a no full repaint to stop flickering
        style = style | wx.NO_FULL_REPAINT_ON_RESIZE
        #call super function
        super(GLPanel, self).__init__(parent, id, pos, size, style)

        #init gl canvas data
        self.GLinitialized = False
        attribList = (glcanvas.WX_GL_RGBA,  # RGBA
                      glcanvas.WX_GL_DOUBLEBUFFER,  # Double Buffered
                      glcanvas.WX_GL_DEPTH_SIZE, 24)  # 24 bit
        # Create the canvas
        self.sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.canvas = glcanvas.GLCanvas(self, attribList = attribList)
        self.sizer.Add(self.canvas, 1, wx.EXPAND)
        self.SetSizer(self.sizer)
        #self.sizer.Fit(self)
        self.Layout()

        # bind events
        self.canvas.Bind(wx.EVT_ERASE_BACKGROUND, self.processEraseBackgroundEvent)
        self.canvas.Bind(wx.EVT_SIZE, self.processSizeEvent)
        self.canvas.Bind(wx.EVT_PAINT, self.processPaintEvent)

    #==========================================================================
    # Canvas Proxy Methods
    #==========================================================================
    def GetGLExtents(self):
        '''Get the extents of the OpenGL canvas.'''
        return self.canvas.GetClientSize()

    def SwapBuffers(self):
        '''Swap the OpenGL buffers.'''
        self.canvas.SwapBuffers()

    #==========================================================================
    # wxPython Window Handlers
    #==========================================================================
    def processEraseBackgroundEvent(self, event):
        '''Process the erase background event.'''
        pass  # Do nothing, to avoid flashing on MSWin

    def processSizeEvent(self, event):
        '''Process the resize event.'''
        if self.canvas.GetContext():
            # Make sure the frame is shown before calling SetCurrent.
            self.Show()
            self.canvas.SetCurrent()
            size = self.GetGLExtents()
            self.winsize = (size.width, size.height)
            self.width, self.height = size.width, size.height
            self.OnReshape(size.width, size.height)
            self.canvas.Refresh(False)
        event.Skip()

    def processPaintEvent(self, event):
        '''Process the drawing event.'''
        self.canvas.SetCurrent()

        # This is a 'perfect' time to initialize OpenGL ... only if we need to
        if not self.GLinitialized:
            self.OnInitGL()
            self.GLinitialized = True

        self.OnDraw()
        event.Skip()

    def Destroy(self):
        #clean up the pyglet OpenGL context
        #self.pygletcontext.destroy()
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
        self.pygletcontext = Context(current_context)
        self.pygletcontext.set_current()
        self.dist = 1000
        self.vpmat = None
        #normal gl init
        glClearColor(0, 0, 0, 1)
        glColor3f(1, 0, 0)
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_CULL_FACE)
        # Uncomment this line for a wireframe view
        #glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)

        # Simple light setup.  On Windows GL_LIGHT0 is enabled by default,
        # but this is not the case on Linux or Mac, so remember to always
        # include it.
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glEnable(GL_LIGHT1)

        # Define a simple function to create ctypes arrays of floats:
        def vec(*args):
            return (GLfloat * len(args))(*args)

        glLightfv(GL_LIGHT0, GL_POSITION, vec(.5, .5, 1, 0))
        glLightfv(GL_LIGHT0, GL_SPECULAR, vec(.5, .5, 1, 1))
        glLightfv(GL_LIGHT0, GL_DIFFUSE, vec(1, 1, 1, 1))
        glLightfv(GL_LIGHT1, GL_POSITION, vec(1, 0, .5, 0))
        glLightfv(GL_LIGHT1, GL_DIFFUSE, vec(.5, .5, .5, 1))
        glLightfv(GL_LIGHT1, GL_SPECULAR, vec(1, 1, 1, 1))

        glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE, vec(0.5, 0, 0.3, 1))
        glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, vec(1, 1, 1, 1))
        glMaterialf(GL_FRONT_AND_BACK, GL_SHININESS, 50)
        glMaterialfv(GL_FRONT_AND_BACK, GL_EMISSION, vec(0, 0.1, 0, 0.9))
        #create objects to draw
        #self.create_objects()

    def OnReshape(self, width, height):
        '''Reshape the OpenGL viewport based on the dimensions of the window.'''

        if not self.GLinitialized:
            self.OnInitGL()
            self.GLinitialized = True
        self.pmat = (GLdouble * 16)()
        self.mvmat = (GLdouble * 16)()
        glViewport(0, 0, width, height)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(60., width / float(height), .1, 1000.)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        #pyglet stuff
        self.vpmat = (GLint * 4)(0, 0, *list(self.GetClientSize()))
        glGetDoublev(GL_PROJECTION_MATRIX, self.pmat)
        glGetDoublev(GL_MODELVIEW_MATRIX, self.mvmat)
        #glMatrixMode(GL_PROJECTION)

        # Wrap text to the width of the window
        if self.GLinitialized:
            self.pygletcontext.set_current()
            self.update_object_resize()

    def OnDraw(self, *args, **kwargs):
        """Draw the window."""
        #clear the context
        self.canvas.SetCurrent()
        self.pygletcontext.set_current()
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        #draw objects
        self.draw_objects()
        #update screen
        self.SwapBuffers()

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


def _dist(dist):
    """return axis length, or 0 if None"""
    if dist is None:
        return 0
    else:
        return float(dist)

class gcpoint(object):
    """gcode point
    stub for first line"""
    def __init__(self, x = 0, y = 0, z = 0, e = 0):
        self.x = x
        self.y = y
        self.z = z
        self.e = e
        self.length = 0


class gcline(object):
    """gcode move line
    Once initialised, it knows its position, length and extrusion ratio
    Returns lines into gcview batch()
    """
    def __init__(self, x = None, y = None, z = None, e = None, f = None, prev_gcline = None, orgline = False):
        if prev_gcline is None:
            self.prev_gcline = gcpoint()
        else:
            self.prev_gcline = prev_gcline
        if x is None:
            self.x = self.prev_gcline.x
        else:
            self.x = float(x)
        if y is None:
            self.y = self.prev_gcline.y
        else:
            self.y = float(y)
        if z is None:
            self.z = self.prev_gcline.z
        else:
            self.z = float(z)
        if e is None:
            self.e = self.prev_gcline.e
        else:
            self.e = float(e)

        self.f = f

        self.orgline = orgline

        self.calc_delta()
        self.calc_len()

    def __str__(self):
        return u"line from %s,%s,%s to %s,%s,%s with extrusion ratio %s and feedrate %s\n%s" % (
                self.prev_gcline.x,
                self.prev_gcline.y,
                self.prev_gcline.z,
                self.x,
                self.y,
                self.z,
                self.extrusion_ratio,
                self.f,
                self.orgline,
            )

    def calc_delta(self, prev_gcline = None):
        if prev_gcline is None:
            prev_gcline = self.prev_gcline
        if self.prev_gcline is not None:
            self.dx = self.x - prev_gcline.x
            self.dy = self.y - prev_gcline.y
            self.dz = self.z - prev_gcline.z
            self.de = self.e - prev_gcline.e
        else:
            self.dx = self.x
            self.dy = self.y
            self.dz = self.z
            self.de = self.e

    def calc_len(self):
        if self.dz != 0:
            self.length = math.sqrt(self.dx**2 + self.dy**2 + self.dz**2)
        else:
            self.length = math.sqrt(self.dx**2 + self.dy**2)
        if self.de:
            self.extrusion_ratio = self.length / self.de
        else:
            self.extrusion_ratio = 0

    def glline(self):
        return [
                self.prev_gcline.x,
                self.prev_gcline.y,
                self.prev_gcline.z,
                self.x,
                self.y,
                self.z,
            ]
    def glcolor(self, upper_limit = None, lower_limit = 0, max_feedrate = 0):
        if self.extrusion_ratio == 0:
            return [255, 255, 255, 0, 0, 0]
        else:
            blue_color = 0
            green_color = 0
            if upper_limit is not None:
                if self.extrusion_ratio <= lower_limit:
                    blue_color = 0
                else:
                    blue_color = int ((self.extrusion_ratio - lower_limit) / (upper_limit - lower_limit) * 255)
            else:
                blue_color = 0
            if max_feedrate > 0 and self.f > 0:
                green_color = int((self.f/max_feedrate) * 255)

            if green_color > 255:
                green_color = 255
            if green_color < 0:
                green_color = 0
            if blue_color > 255:
                blue_color = 255
            if blue_color < 0:
                blue_color = 0
            return[255, green_color, blue_color, 128, green_color, blue_color/4]


def float_from_line(axe, line):
    return float(line.split(axe)[1].split(" ")[0])

class gcThreadRenderer(threading.Thread):
    def __init__(self, gcview, lines):
        threading.Thread.__init__(self)
        self.gcview = gcview
        self.lines = lines
        print "q init"

    def run(self):
        for line in self.lines:
            layer_name = line.z
            if line.z not in self.gcview.layers:
                self.gcview.layers[line.z] = pyglet.graphics.Batch()
                self.gcview.layerlist = self.gcview.layers.keys()
                self.gcview.layerlist.sort()
            self.gcview.layers[line.z].add(2, GL_LINES, None, ("v3f", line.glline()), ("c3B", line.glcolor(self.gcview.upper_limit, self.gcview.lower_limit, self.gcview.max_feedrate)))
        self.gcview.t2 = time.time()
        print "Rendered lines in %fs" % (self.gcview.t2-self.gcview.t1)

class gcview(object):
    """gcode visualiser
    Holds opengl objects for all layers
    """
    def __init__(self, lines, batch, w = 0.5, h = 0.5):
        if len(lines) == 0:
            return
        print "Loading %s lines" % (len(lines))
        #End pos of previous mode
        self.prev = gcpoint()
        # Correction for G92 moves
        self.delta = [0, 0, 0, 0]
        self.layers = {}
        self.t0 = time.time()
        self.lastf = 0
        lines = [self.transform(i) for i in lines]
        lines = [i for i in lines if i is not None]
        self.t1 = time.time()
        print "transformed %s lines in %fs" % (len(lines), self.t1- self.t0)
        self.upper_limit = 0
        self.lower_limit = None
        self.max_feedrate = 0
        for line in lines:
            if line.extrusion_ratio and line.length > 0.005:  #lines shorter than 0.003 can have large extrusion ratio
                if line.extrusion_ratio > self.upper_limit:
                    self.upper_limit = line.extrusion_ratio
                if self.lower_limit is None or line.extrusion_ratio < self.lower_limit:
                    self.lower_limit = line.extrusion_ratio
            if line.f > self.max_feedrate:
                self.max_feedrate = line.f
        #print upper_limit, lower_limit
        #self.render_gl(lines)
        q = gcThreadRenderer(self, lines)
        q.setDaemon(True)
        q.start()




    def transform(self, line):
        """transforms line of gcode into gcline object (or None if its not move)
        Tracks coordinates across resets in self.delta
        """
        orgline = line
        line = line.split(";")[0]
        cur = [None, None, None, None, None]
        if len(line) > 0:
            if "G92" in line:
                #Recalculate delta on G92 (reset)
                if("X" in line):
                    try:
                        self.delta[0] = float_from_line("X", line) + self.prev.x
                    except:
                        self.delta[0] = 0
                if("Y" in line):
                    try:
                        self.delta[1] = float_from_line("Y", line) + self.prev.y
                    except:
                        self.delta[1] = 0
                if("Z" in line):
                    try:
                        self.delta[2] = float_from_line("Z", line) + self.prev.z
                    except:
                        self.delta[2] = 0
                if("E" in line):
                    try:
                        self.delta[3] = float_from_line("E", line) + self.prev.e
                    except:
                        self.delta[3] = 0
                return None

            if "G1" in line or "G0" in line:
                #Create new gcline
                if("X" in line):
                    cur[0] = float_from_line("X", line) + self.delta[0]
                if("Y" in line):
                    cur[1] = float_from_line("Y", line) + self.delta[1]
                if("Z" in line):
                    cur[2] = float_from_line("Z", line) + self.delta[2]
                if("E" in line):
                    cur[3] = float_from_line("E", line) + self.delta[3]
                if "F" in line:
                    cur[4] = float_from_line("F", line)


                if cur == [None, None, None, None, None]:
                    return None
                else:
                    #print cur
                    if cur[4] is None:
                        cur[4] = self.lastf
                    else:
                        self.lastf = cur[4]

                    r = gcline(x = cur[0], y = cur[1], z = cur[2], e = cur[3], f = cur[4], prev_gcline = self.prev, orgline = orgline)
                    self.prev = r
                    return r
            return None

    def delete(self):
        #for i in self.vlists:
        #    i.delete()
        #self.vlists = []
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


class TestGlPanel(GLPanel):

    def __init__(self, parent, size, id = wx.ID_ANY):
        super(TestGlPanel, self).__init__(parent, id, wx.DefaultPosition, size, 0)
        self.batches = []
        self.rot = 0
        self.canvas.Bind(wx.EVT_MOUSE_EVENTS, self.move)
        self.canvas.Bind(wx.EVT_LEFT_DCLICK, self.double)
        self.initialized = 1
        self.canvas.Bind(wx.EVT_MOUSEWHEEL, self.wheel)
        self.parent = parent
        self.initpos = None
        self.dist = 200
        self.bedsize = [200, 200]
        self.transv = [0, 0, -self.dist]
        self.basequat = [0, 0, 0, 1]
        wx.CallAfter(self.forceresize)
        self.mousepos = [0, 0]

    def double(self, event):
        p = event.GetPositionTuple()
        sz = self.GetClientSize()
        v = map(lambda m, w, b: b * m / w, p, sz, self.bedsize)
        v[1] = self.bedsize[1] - v[1]
        v += [300]
        print v
        self.add_file("../prusa/metric-prusa/x-end-idler.stl", v)

    def forceresize(self):
        self.SetClientSize((self.GetClientSize()[0], self.GetClientSize()[1] + 1))
        self.SetClientSize((self.GetClientSize()[0], self.GetClientSize()[1] - 1))
        threading.Thread(target = self.update).start()
        self.initialized = 0

    def move_shape(self, delta):
        """moves shape (selected in l, which is list ListBox of shapes)
        by an offset specified in tuple delta.
        Positive numbers move to (rigt, down)"""
        name = self.parent.l.GetSelection()
        if name == wx.NOT_FOUND:
            return False

        name = self.parent.l.GetString(name)

        model = self.parent.models[name]
        model.offsets = [
                model.offsets[0] + delta[0],
                model.offsets[1] + delta[1],
                model.offsets[2]
            ]
        self.Refresh()
        return True

    def move(self, event):
        """react to mouse actions:
        no mouse: show red mousedrop
        LMB: move active object,
            with shift rotate viewport
        RMB: nothing
            with shift move viewport
        """
        if event.Dragging() and event.LeftIsDown():
            if self.initpos == None:
                self.initpos = event.GetPositionTuple()
            else:
                if not event.ShiftDown():
                    currentpos = event.GetPositionTuple()
                    delta = (
                            (currentpos[0] - self.initpos[0]),
                            -(currentpos[1] - self.initpos[1])
                        )
                    self.move_shape(delta)
                    self.initpos = None
                    return
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

        elif event.Dragging() and event.RightIsDown() and event.ShiftDown():
            if self.initpos is None:
                self.initpos = event.GetPositionTuple()
            else:
                p1 = self.initpos
                p2 = event.GetPositionTuple()
                sz = self.GetClientSize()
                p1 = list(p1)
                p2 = list(p2)
                p1[1] *= -1
                p2[1] *= -1

                self.transv = map(lambda x, y, z, c: c - self.dist * (x - y) / z,  list(p1) + [0],  list(p2) + [0],  list(sz) + [1],  self.transv)

                glLoadIdentity()
                glTranslatef(self.transv[0], self.transv[1], 0)
                glTranslatef(0, 0, self.transv[2])
                if(self.rot):
                    glMultMatrixd(build_rotmatrix(self.basequat))
                glGetDoublev(GL_MODELVIEW_MATRIX, self.mvmat)
                self.rot = 1
                self.initpos = None
        else:
            #mouse is moving without a button press
            p = event.GetPositionTuple()
            sz = self.GetClientSize()
            v = map(lambda m, w, b: b * m / w, p, sz, self.bedsize)
            v[1] = self.bedsize[1] - v[1]
            self.mousepos = v

    def rotate_shape(self, angle):
        """rotates acive shape
        positive angle is clockwise
        """
        name = self.parent.l.GetSelection()
        if name == wx.NOT_FOUND:
            return False
        name = self.parent.l.GetString(name)
        model = self.parent.models[name]
        model.rot += angle

    def wheel(self, event):
        """react to mouse wheel actions:
        rotate object
            with shift zoom viewport
        """
        z = event.GetWheelRotation()
        angle = 10
        if not event.ShiftDown():
            i = self.parent.l.GetSelection()

            if i < 0:
                try:
                    self.parent.setlayerindex(z)
                except:
                    pass
                return

            if z > 0:
                self.rotate_shape(angle / 2)
            else:
                self.rotate_shape(-angle / 2)
            return
        if z > 0:
            self.transv[2] += angle
        else:
            self.transv[2] -= angle

        glLoadIdentity()
        glTranslatef(*self.transv)
        if(self.rot):
            glMultMatrixd(build_rotmatrix(self.basequat))
        glGetDoublev(GL_MODELVIEW_MATRIX, self.mvmat)
        self.rot = 1

    def keypress(self, event):
        """gets keypress events and moves/rotates acive shape"""
        keycode = event.GetKeyCode()
        print keycode
        step = 5
        angle = 18
        if event.ControlDown():
            step = 1
            angle = 1
        #h
        if keycode == 72:
            self.move_shape((-step, 0))
        #l
        if keycode == 76:
            self.move_shape((step, 0))
        #j
        if keycode == 75:
            self.move_shape((0, step))
        #k
        if keycode == 74:
            self.move_shape((0, -step))
        #[
        if keycode == 91:
            self.rotate_shape(-angle)
        #]
        if keycode == 93:
            self.rotate_shape(angle)
        event.Skip()

    def update(self):
        while(1):
            dt = 0.05
            time.sleep(0.05)
            try:
                wx.CallAfter(self.Refresh)
            except:
                return

    def anim(self, obj):
        g = 50 * 9.8
        v = 20
        dt = 0.05
        basepos = obj.offsets[2]
        obj.offsets[2] += obj.animoffset
        while obj.offsets[2] > -1:
            time.sleep(dt)
            obj.offsets[2] -= v * dt
            v += g * dt
            if(obj.offsets[2] < 0):
                obj.scale[2] *= 1 - 3 * dt
        #return
        v = v / 4
        while obj.offsets[2] < basepos:
            time.sleep(dt)
            obj.offsets[2] += v * dt
            v -= g * dt
            obj.scale[2] *= 1 + 5 * dt
        obj.scale[2] = 1.0

    def create_objects(self):
        '''create opengl objects when opengl is initialized'''
        self.initialized = 1
        wx.CallAfter(self.Refresh)

    def drawmodel(self, m, n):
        batch = pyglet.graphics.Batch()
        stl = stlview(m.facets, batch = batch)
        m.batch = batch
        m.animoffset = 300
        #print m
        #threading.Thread(target = self.anim, args = (m, )).start()
        wx.CallAfter(self.Refresh)

    def update_object_resize(self):
        '''called when the window recieves only if opengl is initialized'''
        pass

    def draw_objects(self):
        '''called in the middle of ondraw after the buffer has been cleared'''
        if self.vpmat is None:
            return
        if not self.initialized:
            self.create_objects()

        #glLoadIdentity()
        #print list(self.pmat)
        if self.rot == 1:
            glLoadIdentity()
            glMultMatrixd(self.mvmat)
        else:
            glLoadIdentity()
            glTranslatef(*self.transv)
        glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE, vec(0.2, 0.2, 0.2, 1))
        glBegin(GL_LINES)
        glNormal3f(0, 0, 1)
        rows = 10
        cols = 10
        zheight = 50
        for i in xrange(-rows, rows + 1):
            if i % 5 == 0:
                glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE, vec(0.6, 0.6, 0.6, 1))
            else:
                glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE, vec(0.2, 0.2, 0.2, 1))
            glVertex3f(10 * -cols, 10 * i, 0)
            glVertex3f(10 * cols, 10 * i, 0)
        for i in xrange(-cols, cols + 1):
            if i % 5 == 0:
                glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE, vec(0.6, 0.6, 0.6, 1))
            else:
                glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE, vec(0.2, 0.2, 0.2, 1))
            glVertex3f(10 * i, 10 * -rows, 0)
            glVertex3f(10 * i, 10 * rows, 0)
        glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE, vec(0.6, 0.6, 0.6, 1))
        glVertex3f(10 * -cols, 10 * -rows, 0)
        glVertex3f(10 * -cols, 10 * -rows, zheight)
        glVertex3f(10 * cols, 10 * rows, 0)
        glVertex3f(10 * cols, 10 * rows, zheight)
        glVertex3f(10 * cols, 10 * -rows, 0)
        glVertex3f(10 * cols, 10 * -rows, zheight)
        glVertex3f(10 * -cols, 10 * rows, 0)
        glVertex3f(10 * -cols, 10 * rows, zheight)

        glVertex3f(10 * -cols, 10 * rows, zheight)
        glVertex3f(10 * cols, 10 * rows, zheight)
        glVertex3f(10 * cols, 10 * rows, zheight)
        glVertex3f(10 * cols, 10 * -rows, zheight)
        glVertex3f(10 * cols, 10 * -rows, zheight)
        glVertex3f(10 * -cols, 10 * -rows, zheight)
        glVertex3f(10 * -cols, 10 * -rows, zheight)
        glVertex3f(10 * -cols, 10 * rows, zheight)

        glEnd()
        glPushMatrix()
        glTranslatef(self.mousepos[0] - self.bedsize[0] / 2, self.mousepos[1] - self.bedsize[1] / 2, 0)
        glBegin(GL_TRIANGLES)
        glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE, vec(1, 0, 0, 1))
        glNormal3f(0, 0, 1)
        glVertex3f(2, 2, 0)
        glVertex3f(-2, 2, 0)
        glVertex3f(-2, -2, 0)
        glVertex3f(2, -2, 0)
        glVertex3f(2, 2, 0)
        glVertex3f(-2, -2, 0)
        glEnd()
        glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE, vec(0.3, 0.7, 0.5, 1))
        #glTranslatef(0, 40, 0)
        glPopMatrix()
        glPushMatrix()
        glTranslatef(-100, -100, 0)
        glEnable(GL_LINE_SMOOTH)
        glEnable(GL_BLEND)
        glBlendFunc (GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glHint (GL_LINE_SMOOTH_HINT, GL_NICEST)
        glLineWidth (1.5)

        for i in self.parent.models.values():
            glPushMatrix()
            glTranslatef(*(i.offsets))
            glRotatef(i.rot, 0.0, 0.0, 1.0)
            glScalef(*i.scale)
            #glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE, vec(0.93, 0.37, 0.25, 1))
            glEnable(GL_COLOR_MATERIAL)

            if i.curlayer == -1:
                # curlayer == -1 means we are over the top.
                glLineWidth (0.8)
                [i.gc.layers[j].draw() for j in i.gc.layerlist]
            else:
                glLineWidth (0.6)

                tmpindex = i.gc.layerlist.index(i.curlayer)
                if tmpindex >= 5:
                    thin_layer = i.gc.layerlist[tmpindex - 5]
                    [i.gc.layers[j].draw() for j in i.gc.layerlist if j <= thin_layer]

                if tmpindex > 4:
                    glLineWidth (0.9)
                    i.gc.layers[i.gc.layerlist[tmpindex - 4]].draw()

                if tmpindex > 3:
                    glLineWidth (1.1)
                    i.gc.layers[i.gc.layerlist[tmpindex - 3]].draw()

                if tmpindex > 2:
                    glLineWidth (1.3)
                    i.gc.layers[i.gc.layerlist[tmpindex - 2]].draw()

                if tmpindex > 1:
                    glLineWidth (2.2)
                    i.gc.layers[i.gc.layerlist[tmpindex - 1]].draw()

                glLineWidth (3.5)
                i.gc.layers[i.curlayer].draw()
            glLineWidth (1.5)

            glDisable(GL_COLOR_MATERIAL)

            glPopMatrix()
        glPopMatrix()
        #print "drawn batch"


class GCFrame(wx.Frame):
    '''A simple class for using OpenGL with wxPython.'''

    def __init__(self, parent, ID, title, pos = wx.DefaultPosition,
            size = wx.DefaultSize, style = wx.DEFAULT_FRAME_STYLE):
        super(GCFrame, self).__init__(parent, ID, title, pos, (size[0] + 150, size[1]), style)

        class d:
            def GetSelection(self):
                return wx.NOT_FOUND
        self.p = self
        m = d()
        m.offsets = [0, 0, 0]
        m.rot = 0
        m.curlayer = -1
        m.scale = [1.0, 1.0, 1.0]
        m.batch = pyglet.graphics.Batch()
        m.gc = gcview([], batch = m.batch)
        self.models = {"GCODE": m}
        self.l = d()
        self.modelindex = 0
        self.GLPanel1 = TestGlPanel(self, size)

    def addfile(self, gcode = []):
        self.models["GCODE"].gc.delete()
        self.models["GCODE"].gc = gcview(gcode, batch = self.models["GCODE"].batch)
        self.setlayerindex(None)

    def clear(self):
        self.models["GCODE"].gc.delete()
        self.models["GCODE"].gc = gcview([], batch = self.models["GCODE"].batch)

    def Show(self, arg = True):
        wx.Frame.Show(self, arg)
        self.SetClientSize((self.GetClientSize()[0], self.GetClientSize()[1] + 1))
        self.SetClientSize((self.GetClientSize()[0], self.GetClientSize()[1] - 1))
        self.Refresh()
        wx.FutureCall(500, self.GLPanel1.forceresize)
        #threading.Thread(target = self.update).start()
        #self.initialized = 0

    def setlayerindex(self, z):
        m = self.models["GCODE"]
        try:
            mlk = m.gc.layerlist
        except:
            mlk = []
        if z is None:
            self.modelindex = -1
        elif z > 0:
            if self.modelindex < len(mlk) - 1:
                if self.modelindex > -1:
                    self.modelindex += 1
            else:
                self.modelindex = -1
        elif z < 0:
            if self.modelindex > 0:
                self.modelindex -= 1
            elif self.modelindex == -1:
                self.modelindex = len(mlk)

        if self.modelindex >= 0:
            m.curlayer = mlk[self.modelindex]
            wx.CallAfter(self.SetTitle, "Gcode view, shift to move. Layer %d/%d, Z = %f" % (self.modelindex, len(mlk), m.curlayer))
        else:
            m.curlayer = -1
            wx.CallAfter(self.SetTitle, "Gcode view, shift to move view, mousewheel to set layer")



def main():
    app = wx.App(redirect = False)
    frame = GCFrame(None, wx.ID_ANY, 'Gcode view, shift to move view, mousewheel to set layer', size = (400, 400))
    import sys
    for filename in sys.argv:
        if ".gcode" in filename:
            frame.addfile(list(open(filename)))
        elif ".stl" in filename:
            #TODO: add stl here
            pass

    #frame = wx.Frame(None, -1, "GL Window", size = (400, 400))
    #panel = TestGlPanel(frame, size = (300, 300))
    frame.Show(True)
    app.MainLoop()
    app.Destroy()

if __name__ == "__main__":
    #import cProfile
    #print cProfile.run("main()")
    main()
