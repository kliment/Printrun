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
import time

import pyglet
pyglet.options['debug_gl'] = True

from pyglet.gl import *
from pyglet import gl

from .gl.panel import wxGLPanel
from .gl.trackball import trackball, mulquat, build_rotmatrix
from .gl.libtatlin import actors

def vec(*args):
    return (GLfloat * len(args))(*args)

class stlview(object):
    def __init__(self, facets, batch):
        # Create the vertex and normal arrays.
        vertices = []
        normals = []

        for i in facets:
            for j in i[1]:
                vertices.extend(j)
                normals.extend(i[0])

        # Create a list of triangle indices.
        indices = range(3 * len(facets))  # [[3*i, 3*i+1, 3*i+2] for i in xrange(len(facets))]
        #print indices[:10]
        self.vertex_list = batch.add_indexed(len(vertices) // 3,
                                             GL_TRIANGLES,
                                             None,  # group,
                                             indices,
                                             ('v3f/static', vertices),
                                             ('n3f/static', normals))

    def delete(self):
        self.vertex_list.delete()

class StlViewPanel(wxGLPanel):

    def __init__(self, parent, size, id = wx.ID_ANY, build_dimensions = None):
        super(StlViewPanel, self).__init__(parent, id, wx.DefaultPosition, size, 0)
        self.batches = []
        self.rot = 0
        self.canvas.Bind(wx.EVT_MOUSE_EVENTS, self.move)
        self.canvas.Bind(wx.EVT_LEFT_DCLICK, self.double)
        self.initialized = 1
        self.canvas.Bind(wx.EVT_MOUSEWHEEL, self.wheel)
        self.parent = parent
        self.initpos = None
        if build_dimensions:
            self.build_dimensions = build_dimensions
        else:
            self.build_dimensions = [200, 200, 100, 0, 0, 0]
        self.platform = actors.Platform(self.build_dimensions, light = True)
        self.dist = max(self.build_dimensions[0], self.build_dimensions[1])
        self.basequat = [0, 0, 0, 1]
        wx.CallAfter(self.forceresize)
        self.mousepos = (0, 0)

    def OnReshape(self):
        self.mview_initialized = False
        super(StlViewPanel, self).OnReshape()

    #==========================================================================
    # GLFrame OpenGL Event Handlers
    #==========================================================================
    def OnInitGL(self, call_reshape = True):
        '''Initialize OpenGL for use in the window.'''
        if self.GLinitialized:
            return
        self.GLinitialized = True
        #create a pyglet context for this panel
        self.pygletcontext = gl.Context(gl.current_context)
        self.pygletcontext.canvas = self
        self.pygletcontext.set_current()
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
        if call_reshape:
            self.OnReshape()
        if hasattr(self.parent, "filenames") and self.parent.filenames:
            for filename in self.parent.filenames:
                self.parent.load_file(filename)
            self.parent.autoplate()
            if hasattr(self.parent, "loadcb"):
                self.parent.loadcb()
            self.parent.filenames = None

    def double(self, event):
        p = event.GetPositionTuple()
        sz = self.GetClientSize()
        v = map(lambda m, w, b: b * m / w, p, sz, self.build_dimensions[0:2])
        v[1] = self.build_dimensions[1] - v[1]
        v += [300]
        print "Double-click at " + str(v) + " in "
        print self

    def forceresize(self):
        self.SetClientSize((self.GetClientSize()[0], self.GetClientSize()[1] + 1))
        self.SetClientSize((self.GetClientSize()[0], self.GetClientSize()[1] - 1))
        self.initialized = 0

    def move(self, event):
        """react to mouse actions:
        no mouse: show red mousedrop
        LMB: move active object,
            with shift rotate viewport
        RMB: nothing
            with shift move viewport
        """
        self.mousepos = event.GetPositionTuple()
        if event.Dragging() and event.LeftIsDown():
            self.handle_rotation(event)
        elif event.Dragging() and event.RightIsDown():
            self.handle_translation(event)
        elif event.ButtonUp(wx.MOUSE_BTN_LEFT):
            if self.initpos is not None:
                self.initpos = None
        elif event.ButtonUp(wx.MOUSE_BTN_RIGHT):
            if self.initpos is not None:
                self.initpos = None
        else:
            event.Skip()
            return
        event.Skip()
        wx.CallAfter(self.Refresh)

    def handle_wheel(self, event):
        delta = event.GetWheelRotation()
        factor = 1.05
        x, y = event.GetPositionTuple()
        x, y, _ = self.mouse_to_3d(x, y)
        if delta > 0:
            self.zoom(factor, (x, y))
        else:
            self.zoom(1 / factor, (x, y))

    def wheel(self, event):
        """react to mouse wheel actions:
        rotate object
            with shift zoom viewport
        """
        self.handle_wheel(event)
        wx.CallAfter(self.Refresh)

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
            self.parent.move_shape((-step, 0))
        #l
        if keycode == 76:
            self.parent.move_shape((step, 0))
        #j
        if keycode == 75:
            self.parent.move_shape((0, step))
        #k
        if keycode == 74:
            self.parent.move_shape((0, -step))
        #[
        if keycode == 91:
            self.parent.rotate_shape(-angle)
        #]
        if keycode == 93:
            self.parent.rotate_shape(angle)
        event.Skip()
        wx.CallAfter(self.Refresh)

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
        if not self.platform.initialized:
            self.platform.init()
        self.initialized = 1
        wx.CallAfter(self.Refresh)

    def drawmodel(self, m, n):
        batch = pyglet.graphics.Batch()
        stlview(m.facets, batch = batch)
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
        self.create_objects()

        glPushMatrix()
        glTranslatef(0, 0, -self.dist)
        glMultMatrixd(build_rotmatrix(self.basequat))  # Rotate according to trackball
        glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE, vec(0.2, 0.2, 0.2, 1))
        glTranslatef(- self.build_dimensions[3] - self.platform.width / 2,
                     - self.build_dimensions[4] - self.platform.depth / 2, 0)  # Move origin to bottom left of platform
        # Draw platform
        glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
        self.platform.draw()
        glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
        # Draw mouse
        glPushMatrix()
        x, y, z = self.mouse_to_3d(self.mousepos[0], self.mousepos[1], 0.9)
        glTranslatef(x, y, z)
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
        glPopMatrix()
        glPushMatrix()

        # Draw objects
        for i in self.parent.models:
            model = self.parent.models[i]
            glPushMatrix()
            glTranslatef(*(model.offsets))
            glRotatef(model.rot, 0.0, 0.0, 1.0)
            glTranslatef(*(model.centeroffset))
            glScalef(*model.scale)
            model.batch.draw()
            glPopMatrix()
        glPopMatrix()
        glPopMatrix()

def main():
    app = wx.App(redirect = False)
    frame = wx.Frame(None, -1, "GL Window", size = (400, 400))
    StlViewPanel(frame)
    frame.Show(True)
    app.MainLoop()
    app.Destroy()

if __name__ == "__main__":
    main()
