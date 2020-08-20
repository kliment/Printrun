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

import wx
import time

import numpy
import pyglet
pyglet.options['debug_gl'] = True

from pyglet.gl import GL_AMBIENT_AND_DIFFUSE, glBegin, glClearColor, \
    glColor3f, GL_CULL_FACE, GL_DEPTH_TEST, GL_DIFFUSE, GL_EMISSION, \
    glEnable, glEnd, GL_FILL, GLfloat, GL_FRONT_AND_BACK, GL_LIGHT0, \
    GL_LIGHT1, glLightfv, GL_LIGHTING, GL_LINE, glMaterialf, glMaterialfv, \
    glMultMatrixd, glNormal3f, glPolygonMode, glPopMatrix, GL_POSITION, \
    glPushMatrix, glRotatef, glScalef, glShadeModel, GL_SHININESS, \
    GL_SMOOTH, GL_SPECULAR, glTranslatef, GL_TRIANGLES, glVertex3f, \
    glGetDoublev, GL_MODELVIEW_MATRIX, GLdouble, glClearDepth, glDepthFunc, \
    GL_LEQUAL, GL_BLEND, glBlendFunc, GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA, \
    GL_LINE_LOOP, glGetFloatv, GL_LINE_WIDTH, glLineWidth, glDisable, \
    GL_LINE_SMOOTH
from pyglet import gl

from .gl.panel import wxGLPanel
from .gl.trackball import build_rotmatrix
from .gl.libtatlin import actors

def vec(*args):
    return (GLfloat * len(args))(*args)

class stlview:
    def __init__(self, facets, batch):
        # Create the vertex and normal arrays.
        vertices = []
        normals = []

        for i in facets:
            for j in i[1]:
                vertices.extend(j)
                normals.extend(i[0])

        # Create a list of triangle indices.
        indices = list(range(3 * len(facets)))  # [[3*i, 3*i+1, 3*i+2] for i in xrange(len(facets))]
        self.vertex_list = batch.add_indexed(len(vertices) // 3,
                                             GL_TRIANGLES,
                                             None,  # group,
                                             indices,
                                             ('v3f/static', vertices),
                                             ('n3f/static', normals))

    def delete(self):
        self.vertex_list.delete()

class StlViewPanel(wxGLPanel):

    do_lights = False

    def __init__(self, parent, size,
                 build_dimensions = None, circular = False,
                 antialias_samples = 0,
                 grid = (1, 10)):
        super().__init__(parent, wx.DefaultPosition, size, 0,
                                           antialias_samples = antialias_samples)
        self.batches = []
        self.rot = 0
        self.canvas.Bind(wx.EVT_MOUSE_EVENTS, self.move)
        self.canvas.Bind(wx.EVT_MOUSEWHEEL, self.wheel)
        self.canvas.Bind(wx.EVT_LEFT_DCLICK, self.double_click)
        self.initialized = True
        self.parent = parent
        self.initpos = None
        if build_dimensions:
            self.build_dimensions = build_dimensions
        else:
            self.build_dimensions = [200, 200, 100, 0, 0, 0]
        self.platform = actors.Platform(self.build_dimensions,
                                        circular = circular,
                                        grid = grid)
        self.dist = max(self.build_dimensions[0], self.build_dimensions[1])
        self.basequat = [0, 0, 0, 1]
        wx.CallAfter(self.forceresize) #why needed
        self.mousepos = (0, 0)

    def OnReshape(self):
        self.mview_initialized = False
        super(StlViewPanel, self).OnReshape()

    # ==========================================================================
    # GLFrame OpenGL Event Handlers
    # ==========================================================================
    def OnInitGL(self, call_reshape = True):
        '''Initialize OpenGL for use in the window.'''
        if self.GLinitialized:
            return
        self.GLinitialized = True
        # create a pyglet context for this panel
        self.pygletcontext = gl.Context(gl.current_context)
        self.pygletcontext.canvas = self
        self.pygletcontext.set_current()
        # normal gl init
        glClearColor(0, 0, 0, 1)
        glColor3f(1, 0, 0)
        glEnable(GL_DEPTH_TEST)
        glClearDepth(1.0)
        glDepthFunc(GL_LEQUAL)
        glEnable(GL_CULL_FACE)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        # Uncomment this line for a wireframe view
        # glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)

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
        glShadeModel(GL_SMOOTH)

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

    def double_click(self, event):
        if hasattr(self.parent, "clickcb") and self.parent.clickcb:
            self.parent.clickcb(event)

    def forceresize(self):
        #print('forceresize')
        x, y = self.GetClientSize()
        #TODO: probably not needed
        self.SetClientSize((x, y+1))
        self.SetClientSize((x, y))
        self.initialized = False

    def move(self, event):
        """react to mouse actions:
        no mouse: show red mousedrop
        LMB: move active object,
            with shift rotate viewport
        RMB: nothing
            with shift move viewport
        """
        self.mousepos = event.GetPosition()
        if event.Dragging():
            if event.LeftIsDown():
                self.handle_rotation(event)
            elif event.RightIsDown():
                self.handle_translation(event)
            self.Refresh(False)
        elif event.ButtonUp(wx.MOUSE_BTN_LEFT) or \
            event.ButtonUp(wx.MOUSE_BTN_RIGHT):
            self.initpos = None
        event.Skip()

    def handle_wheel(self, event):
        delta = event.GetWheelRotation()
        factor = 1.05
        x, y = event.GetPosition()
        x, y, _ = self.mouse_to_3d(x, y, local_transform = True)
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
        step = 5
        angle = 18
        if event.ControlDown():
            step = 1
            angle = 1
        # h
        if keycode == 72:
            self.parent.move_shape((-step, 0))
        # l
        if keycode == 76:
            self.parent.move_shape((step, 0))
        # j
        if keycode == 75:
            self.parent.move_shape((0, step))
        # k
        if keycode == 74:
            self.parent.move_shape((0, -step))
        # [
        if keycode == 91:
            self.parent.rotate_shape(-angle)
        # ]
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
            if obj.offsets[2] < 0:
                obj.scale[2] *= 1 - 3 * dt
        # return
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
        #TODO: this probably creates constant redraw
        # create_objects is called during OnDraw, remove
        wx.CallAfter(self.Refresh)

    def prepare_model(self, m, scale):
        batch = pyglet.graphics.Batch()
        stlview(m.facets, batch = batch)
        m.batch = batch
        # m.animoffset = 300
        # threading.Thread(target = self.anim, args = (m, )).start()
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
        glDisable(GL_LIGHTING)
        self.platform.draw()
        glEnable(GL_LIGHTING)
        # Draw mouse
        glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
        inter = self.mouse_to_plane(self.mousepos[0], self.mousepos[1],
                                    plane_normal = (0, 0, 1), plane_offset = 0,
                                    local_transform = False)
        if inter is not None:
            glPushMatrix()
            glTranslatef(inter[0], inter[1], inter[2])
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
            glPopMatrix()

        # Draw objects
        glDisable(GL_CULL_FACE)
        glPushMatrix()
        glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE, vec(0.3, 0.7, 0.5, 1))
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
        glEnable(GL_CULL_FACE)

        # Draw cutting plane
        if self.parent.cutting:
            # FIXME: make this a proper Actor
            axis = self.parent.cutting_axis
            fixed_dist = self.parent.cutting_dist
            dist, plane_width, plane_height = self.get_cutting_plane(axis, fixed_dist)
            if dist is not None:
                glPushMatrix()
                if axis == "x":
                    glRotatef(90, 0, 1, 0)
                    glRotatef(90, 0, 0, 1)
                    glTranslatef(0, 0, dist)
                elif axis == "y":
                    glRotatef(90, 1, 0, 0)
                    glTranslatef(0, 0, -dist)
                elif axis == "z":
                    glTranslatef(0, 0, dist)
                glDisable(GL_CULL_FACE)
                glBegin(GL_TRIANGLES)
                glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE, vec(0, 0.9, 0.15, 0.3))
                glNormal3f(0, 0, self.parent.cutting_direction)
                glVertex3f(plane_width, plane_height, 0)
                glVertex3f(0, plane_height, 0)
                glVertex3f(0, 0, 0)
                glVertex3f(plane_width, 0, 0)
                glVertex3f(plane_width, plane_height, 0)
                glVertex3f(0, 0, 0)
                glEnd()
                glEnable(GL_CULL_FACE)
                glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
                glEnable(GL_LINE_SMOOTH)
                orig_linewidth = (GLfloat)()
                glGetFloatv(GL_LINE_WIDTH, orig_linewidth)
                glLineWidth(4.0)
                glBegin(GL_LINE_LOOP)
                glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE, vec(0, 0.8, 0.15, 1))
                glVertex3f(0, 0, 0)
                glVertex3f(0, plane_height, 0)
                glVertex3f(plane_width, plane_height, 0)
                glVertex3f(plane_width, 0, 0)
                glEnd()
                glLineWidth(orig_linewidth)
                glDisable(GL_LINE_SMOOTH)
                glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
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
            glTranslatef(0, 0, -self.dist)
            glMultMatrixd(build_rotmatrix(self.basequat))  # Rotate according to trackball
            glTranslatef(- self.build_dimensions[3] - self.platform.width / 2,
                         - self.build_dimensions[4] - self.platform.depth / 2, 0)  # Move origin to bottom left of platform
            glGetDoublev(GL_MODELVIEW_MATRIX, mvmat)
            glPopMatrix()
        else:
            glGetDoublev(GL_MODELVIEW_MATRIX, mvmat)
        return mvmat

    def get_cutting_plane(self, cutting_axis, fixed_dist, local_transform = False):
        cutting_plane_sizes = {"x": (self.platform.depth, self.platform.height),
                               "y": (self.platform.width, self.platform.height),
                               "z": (self.platform.width, self.platform.depth)}
        plane_width, plane_height = cutting_plane_sizes[cutting_axis]
        if fixed_dist is not None:
            return fixed_dist, plane_width, plane_height
        ref_sizes = {"x": self.platform.width,
                     "y": self.platform.depth,
                     "z": self.platform.height,
                     }
        ref_planes = {"x": (0, 0, 1),
                      "y": (0, 0, 1),
                      "z": (0, 1, 0)
                      }
        ref_offsets = {"x": 0,
                       "y": 0,
                       "z": - self.platform.depth / 2
                       }
        translate_axis = {"x": 0,
                          "y": 1,
                          "z": 2
                          }
        fallback_ref_planes = {"x": (0, 1, 0),
                               "y": (1, 0, 0),
                               "z": (1, 0, 0)
                               }
        fallback_ref_offsets = {"x": - self.platform.height / 2,
                                "y": - self.platform.width / 2,
                                "z": - self.platform.width / 2,
                                }
        ref_size = ref_sizes[cutting_axis]
        ref_plane = ref_planes[cutting_axis]
        ref_offset = ref_offsets[cutting_axis]
        inter = self.mouse_to_plane(self.mousepos[0], self.mousepos[1],
                                    plane_normal = ref_plane,
                                    plane_offset = ref_offset,
                                    local_transform = local_transform)
        max_size = max((self.platform.width,
                        self.platform.depth,
                        self.platform.height))
        dist = None
        if inter is not None and numpy.fabs(inter).max() + max_size / 2 < 2 * max_size:
            dist = inter[translate_axis[cutting_axis]]
        if dist is None or dist < -0.5 * ref_size or dist > 1.5 * ref_size:
            ref_plane = fallback_ref_planes[cutting_axis]
            ref_offset = fallback_ref_offsets[cutting_axis]
            inter = self.mouse_to_plane(self.mousepos[0], self.mousepos[1],
                                        plane_normal = ref_plane,
                                        plane_offset = ref_offset,
                                        local_transform = False)
            if inter is not None and numpy.fabs(inter).max() + max_size / 2 < 2 * max_size:
                dist = inter[translate_axis[cutting_axis]]
        if dist is not None:
            dist = min(1.5 * ref_size, max(-0.5 * ref_size, dist))
        return dist, plane_width, plane_height

def main():
    app = wx.App(redirect = False)
    frame = wx.Frame(None, -1, "GL Window", size = (400, 400))
    StlViewPanel(frame)
    frame.Show(True)
    app.MainLoop()
    app.Destroy()

if __name__ == "__main__":
    main()
