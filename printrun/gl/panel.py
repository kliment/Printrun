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

from threading import Lock
import logging
import traceback
import numpy
import numpy.linalg

import wx
from wx import glcanvas

import pyglet
pyglet.options['debug_gl'] = True
pyglet.options['shadow_window'] = False

from pyglet.gl import glEnable, glDisable, GL_LIGHTING, glLightfv, \
    GL_LIGHT0, GL_LIGHT1, GL_LIGHT2, GL_POSITION, GL_DIFFUSE, \
    GL_AMBIENT, GL_SPECULAR, GL_COLOR_MATERIAL, \
    glShadeModel, GL_SMOOTH, GL_NORMALIZE, \
    GL_BLEND, glBlendFunc, glClear, glClearColor, \
    glClearDepth, GL_COLOR_BUFFER_BIT, GL_CULL_FACE, \
    GL_DEPTH_BUFFER_BIT, glDepthFunc, GL_DEPTH_TEST, \
    GLdouble, glGetDoublev, glGetIntegerv, GLint, \
    GL_LEQUAL, glLoadIdentity, glMatrixMode, GL_MODELVIEW, \
    GL_MODELVIEW_MATRIX, GL_ONE_MINUS_SRC_ALPHA, glOrtho, \
    GL_PROJECTION, GL_PROJECTION_MATRIX, glScalef, \
    GL_SRC_ALPHA, glTranslatef, gluPerspective, gluUnProject, \
    glViewport, GL_VIEWPORT, glPushMatrix, glPopMatrix, \
    glColor3f, glColor4f, glMaterialfv, GL_FRONT_AND_BACK, \
    GL_AMBIENT_AND_DIFFUSE, glMaterialf, GL_SHININESS, GL_EMISSION, \
    GL_RESCALE_NORMAL, glColorMaterial, GL_FRONT, glRotatef, \
    glMultMatrixd, glPolygonMode, GL_FILL

from pyglet import gl
from .trackball import trackball, mulquat, axis_to_quat, build_rotmatrix
from .actors import Focus, vec

def gcode_dims(g):
    return ((g.xmin, g.xmax, g.width),
            (g.ymin, g.ymax, g.depth),
            (g.zmin, g.zmax, g.height))

# When Subclassing wx.Window in Windows the focus goes to the wx.Window
# instead of GLCanvas and it does not draw the focus rectangle and
# does not consume used keystrokes
# BASE_CLASS = wx.Window
# Subclassing Panel solves problem In Windows
BASE_CLASS = wx.Panel
# BASE_CLASS = wx.ScrolledWindow
# BASE_CLASS = glcanvas.GLCanvas
class wxGLPanel(BASE_CLASS):
    '''A simple class for using OpenGL with wxPython.'''

    orbit_control = True
    orthographic = True
    color_background = (200 / 255, 225 / 255, 250 / 255, 1.0)  # Light Blue

    # G-Code models and stl models use different lightscene
    gcode_lights = True
    wheelTimestamp = None


    def __init__(self, parent, pos = wx.DefaultPosition,
                 size = wx.DefaultSize, style = 0,
                 antialias_samples = 0):
        # Full repaint should not be a performance problem
        #TODO: test on windows, tested in Ubuntu
        style = style | wx.FULL_REPAINT_ON_RESIZE

        self.GLinitialized = False
        self.mview_initialized = False

        attribList = wx.glcanvas.GLAttributes()
        # Set a 24bit depth buffer and activate double buffering for the canvas
        attribList.PlatformDefaults().DoubleBuffer().Depth(24)

        # Enable multi-sampling support (antialiasing) if it is active in the settings
        if antialias_samples > 0 and hasattr(glcanvas, "WX_GL_SAMPLE_BUFFERS"):
            attribList.SampleBuffers(1).Samplers(antialias_samples)

        attribList.EndList()

        if BASE_CLASS is glcanvas.GLCanvas:
            super().__init__(parent, attribList, wx.ID_ANY, pos, size, style)
            self.canvas = self
        else:
            super().__init__(parent, wx.ID_ANY, pos, size, style)
            self.canvas = glcanvas.GLCanvas(self, attribList, wx.ID_ANY, pos, size, style)

        self.width = self.height = None
        self.focus = Focus()

        self.context = glcanvas.GLContext(self.canvas)
        self.pygletcontext = None  # initialised during glinit

        self.rot_lock = Lock()
        self.basequat = [0, 0, 0, 1]
        self.mousepos = (0, 0)
        self.zoom_factor = 1.0
        self.zoomed_width = 1.0
        self.zoomed_height = 1.0
        self.angle_z = 0
        self.angle_x = 0
        self.initpos = 0

        self.gl_broken = False

        # bind events
        self.canvas.Bind(wx.EVT_SIZE, self.processSizeEvent)
        if self.canvas is not self:
            self.Bind(wx.EVT_SIZE, self.OnScrollSize)
            # do not focus parent (panel like) but its canvas
            self.SetCanFocus(False)

        self.canvas.Bind(wx.EVT_ERASE_BACKGROUND, self.processEraseBackgroundEvent)
        # In wxWidgets 3.0.x there is a clipping bug during resizing
        # which could be affected by painting the container
        # self.Bind(wx.EVT_PAINT, self.processPaintEvent)
        # Upgrade to wxPython 4.1 recommended
        self.canvas.Bind(wx.EVT_PAINT, self.processPaintEvent)

        self.canvas.Bind(wx.EVT_SET_FOCUS, self.processFocus)
        self.canvas.Bind(wx.EVT_KILL_FOCUS, self.processKillFocus)

    def processFocus(self, ev):
        # print('processFocus')
        self.Refresh(False)
        ev.Skip()

    def processKillFocus(self, ev):
        # print('processKillFocus')
        self.Refresh(False)
        ev.Skip()
    # def processIdle(self, event):
    #     print('processIdle')
    #     event.Skip()

    def Layout(self):
        return super().Layout()

    def Refresh(self, eraseback=True):
        # print('Refresh')
        return super().Refresh(eraseback)

    def OnScrollSize(self, event):
        self.canvas.SetSize(event.Size)

    def processEraseBackgroundEvent(self, event):
        '''Process the erase background event.'''
        pass  # Do nothing, to avoid flashing on MSWin

    def processSizeEvent(self, event):
        '''Process the resize event.'''

        # print('processSizeEvent frozen', self.IsFrozen(), event.Size.x, self.ClientSize.x)
        if not self.IsFrozen() and self.canvas.IsShownOnScreen():
            # Make sure the frame is shown before calling SetCurrent.
            self.canvas.SetCurrent(self.context)
            self.OnReshape()

            # self.Refresh(False)
            # print('Refresh')
        event.Skip()

    def processPaintEvent(self, event):
        '''Process the drawing event.'''
        # print('wxGLPanel.processPaintEvent', self.ClientSize.Width)
        self.canvas.SetCurrent(self.context)

        if not self.gl_broken:
            try:
                self.OnInitGL()
                self.DrawCanvas()
            except pyglet.gl.lib.GLException:
                self.gl_broken = True
                logging.error(_("OpenGL failed, disabling it:")
                              + "\n" + traceback.format_exc())
        event.Skip()

    def Destroy(self):
        # clean up the pyglet OpenGL context
        self.pygletcontext.destroy()
        # call the super method
        super().Destroy()

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
        glClearColor(*self.color_background)
        glClearDepth(1.0)  # set depth value to 1
        glDepthFunc(GL_LEQUAL)

        glEnable(GL_DEPTH_TEST)
        glEnable(GL_CULL_FACE)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
        # Polygon mode is never changed, but you can uncomment
        # this line to show models as wireframe
        # glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)

        # Material specs are set here once and then we only change
        # the material colour by using glColor3f / glColor4f
        glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE, vec(0.5, 0, 0.3, 1))
        glMaterialfv(GL_FRONT, GL_SPECULAR, vec(0.85, 0.85, 0.85, 1))
        glMaterialf(GL_FRONT, GL_SHININESS, 72)
        glMaterialfv(GL_FRONT_AND_BACK, GL_EMISSION, vec(0, 0, 0, 0))

        # This enables tracking of the material colour,
        # now it can be changed only by calling glColor
        glEnable(GL_COLOR_MATERIAL)
        glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)

        if call_reshape:
            self.OnReshape()

    def OnReshape(self):
        """Reshape the OpenGL viewport based on the size of the window"""
        size = self.GetClientSize() * self.GetContentScaleFactor()
        oldwidth, oldheight = self.width, self.height
        width, height = size.width, size.height
        if width < 1 or height < 1:
            return
        self.width = max(float(width), 1.0)
        self.height = max(float(height), 1.0)
        self.focus.update_size(self.width, self.height)
        self.OnInitGL(call_reshape = False)
        # print('glViewport', width)
        glViewport(0, 0, width, height)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        if self.orthographic:
            glOrtho(-width / 2, width / 2, -height / 2, height / 2,
                    -5 * self.dist, 5 * self.dist)
        else:
            gluPerspective(60., float(width) / height, 10.0, 3 * self.dist)
            glTranslatef(0, 0, -self.dist)  # Move back
        glMatrixMode(GL_MODELVIEW)

        if not self.mview_initialized:
            self.reset_mview(0.9)
            self.mview_initialized = True
        elif oldwidth is not None and oldheight is not None:
            wratio = self.width / oldwidth
            hratio = self.height / oldheight

            factor = min(wratio * self.zoomed_width, hratio * self.zoomed_height)
            x, y, _ = self.mouse_to_3d(self.width / 2, self.height / 2)
            self.zoom(factor, (x, y))
            self.zoomed_width *= wratio / factor
            self.zoomed_height *= hratio / factor

        # Wrap text to the width of the window
        if self.GLinitialized:
            self.pygletcontext.set_current()
            self.update_object_resize()

    def set_gl_colour(self, r_val: float, g_val: float,
                      b_val: float, a_val: float = 1.0) -> None:
        if a_val == 1.0:
            glColor3f(*vec(r_val, g_val, b_val))
        else:
            glColor4f(*vec(r_val, g_val, b_val, a_val))

    def set_origin(self, platform):
        # Rotate according to trackball
        glMultMatrixd(build_rotmatrix(self.basequat))
        # Move origin to bottom left of platform
        platformx0 = -self.build_dimensions[3] - platform.width / 2
        platformy0 = -self.build_dimensions[4] - platform.depth / 2
        glTranslatef(platformx0, platformy0, 0)

    def setup_lights(self):
        '''Sets the lightscene for gcode and stl models'''
        glEnable(GL_LIGHTING)
        # TODO: Harmonise and improve lighting between gcode and stl
        if self.gcode_lights:
            glDisable(GL_LIGHT0)

            glEnable(GL_LIGHT1)
            glLightfv(GL_LIGHT1, GL_AMBIENT, vec(0, 0, 0, 1.0))
            glLightfv(GL_LIGHT1, GL_SPECULAR, vec(0.6, 0.6, 0.6, 1.0))
            glLightfv(GL_LIGHT2, GL_DIFFUSE, vec(0.8, 0.8, 0.8, 1))
            glLightfv(GL_LIGHT1, GL_POSITION, vec(1, 2, 3, 0))

            glEnable(GL_LIGHT2)
            glLightfv(GL_LIGHT2, GL_AMBIENT, vec(0, 0, 0, 1.0))
            glLightfv(GL_LIGHT2, GL_SPECULAR, vec(0.6, 0.6, 0.6, 1.0))
            glLightfv(GL_LIGHT2, GL_DIFFUSE, vec(0.8, 0.8, 0.8, 1))
            glLightfv(GL_LIGHT2, GL_POSITION, vec(-1, -1, 3, 0))

            # Normalises (0 - 1.0) the normal vectors after scaling
            glEnable(GL_NORMALIZE)
        else:
            glEnable(GL_LIGHT0)
            glLightfv(GL_LIGHT1, GL_AMBIENT, vec(0, 0, 0, 1.0))
            glLightfv(GL_LIGHT0, GL_SPECULAR, vec(0.5, 0.5, 1.0, 1.0))
            glLightfv(GL_LIGHT0, GL_DIFFUSE, vec(1.0, 1.0, 1.0, 1.0))
            glLightfv(GL_LIGHT0, GL_POSITION, vec(0.5, 0.5, 1.0, 0))

            glEnable(GL_LIGHT1)
            glLightfv(GL_LIGHT1, GL_AMBIENT, vec(0, 0, 0, 1.0))
            glLightfv(GL_LIGHT2, GL_SPECULAR, vec(0.6, 0.6, 0.6, 1.0))
            glLightfv(GL_LIGHT1, GL_DIFFUSE, vec(0.5, 0.5, 0.5, 1.0))
            glLightfv(GL_LIGHT1, GL_POSITION, vec(1.0, 0, 0.5, 0))

            glDisable(GL_LIGHT2)

            # Normalises (0 - 1.0) the normal vectors after scaling
            # GL_NORMALIZE makes the objects look too bright (?)
            glEnable(GL_RESCALE_NORMAL)
        glShadeModel(GL_SMOOTH)

    def reset_mview(self, factor):
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        self.setup_lights()

        wratio = self.width / self.dist
        hratio = self.height / self.dist
        minratio = float(min(wratio, hratio))
        self.zoom_factor = 1.0
        self.zoomed_width = wratio / minratio
        self.zoomed_height = hratio / minratio
        glScalef(factor * minratio, factor * minratio, 1)

    def resetview(self):
        self.canvas.SetCurrent(self.context)
        self.reset_mview(0.9)
        self.basequat = [0, 0, 0, 1]
        wx.CallAfter(self.Refresh)

    def DrawCanvas(self):
        """Draw the window."""
        #import time
        #start = time.perf_counter()
        #print('DrawCanvas', self.canvas.GetClientRect())
        self.pygletcontext.set_current()
        glClearColor(*self.color_background)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        self.draw_objects()

        if self.canvas.HasFocus():
            self.focus.draw()

        self.canvas.SwapBuffers()
        #print(f"Draw took {(time.perf_counter()-start) * 1000:.2f} ms,"
        #      f" {1 / (time.perf_counter()-start):.0f} FPS")

    def transform_and_draw(self, model, draw_func):
        '''Apply transformations to the model and then
        draw it with the given draw function'''
        glPushMatrix()
        glTranslatef(*(model.offsets))
        glRotatef(model.rot, 0.0, 0.0, 1.0)
        glTranslatef(*(model.centeroffset))
        glScalef(*model.scale)

        # Draw the models
        draw_func()

        glPopMatrix()

    # ==========================================================================
    # To be implemented by a sub class
    # ==========================================================================
    def create_objects(self):
        '''create opengl objects when opengl is initialized'''
        pass

    def update_object_resize(self):
        '''called when the window receives only if opengl is initialized'''
        pass

    def draw_objects(self):
        '''called in the middle of ondraw after the buffer has been cleared'''
        pass

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
            platformx0 = -self.build_dimensions[3] - self.platform.width / 2
            platformy0 = -self.build_dimensions[4] - self.platform.depth / 2
            glTranslatef(platformx0, platformy0, 0)
            glGetDoublev(GL_MODELVIEW_MATRIX, mvmat)
            glPopMatrix()
        else:
            glGetDoublev(GL_MODELVIEW_MATRIX, mvmat)
        return mvmat

    # ==========================================================================
    # Mouse and Camera
    # ==========================================================================
    def mouse_to_3d(self, x, y, z = 1.0, local_transform = False):
        x = float(x)
        y = self.height - float(y)
        # The following could work if we were not initially scaling to zoom on
        # the bed
        # if self.orthographic:
        #    return (x - self.width / 2, y - self.height / 2, 0)
        pmat = (GLdouble * 16)()
        mvmat = self.get_modelview_mat(local_transform)
        viewport = (GLint * 4)()
        px = (GLdouble)()
        py = (GLdouble)()
        pz = (GLdouble)()
        glGetIntegerv(GL_VIEWPORT, viewport)
        glGetDoublev(GL_PROJECTION_MATRIX, pmat)
        glGetDoublev(GL_MODELVIEW_MATRIX, mvmat)
        gluUnProject(x, y, z, mvmat, pmat, viewport, px, py, pz)
        return (px.value, py.value, pz.value)

    def mouse_to_ray(self, x, y, local_transform = False):
        x = float(x)
        y = self.height - float(y)
        pmat = (GLdouble * 16)()
        mvmat = (GLdouble * 16)()
        viewport = (GLint * 4)()
        px = (GLdouble)()
        py = (GLdouble)()
        pz = (GLdouble)()
        glGetIntegerv(GL_VIEWPORT, viewport)
        glGetDoublev(GL_PROJECTION_MATRIX, pmat)
        mvmat = self.get_modelview_mat(local_transform)
        gluUnProject(x, y, 1, mvmat, pmat, viewport, px, py, pz)
        ray_far = (px.value, py.value, pz.value)
        gluUnProject(x, y, 0., mvmat, pmat, viewport, px, py, pz)
        ray_near = (px.value, py.value, pz.value)
        return ray_near, ray_far

    def mouse_to_plane(self, x, y, plane_normal, plane_offset, local_transform = False):
        # Ray/plane intersection
        ray_near, ray_far = self.mouse_to_ray(x, y, local_transform)
        ray_near = numpy.array(ray_near)
        ray_far = numpy.array(ray_far)
        ray_dir = ray_far - ray_near
        ray_dir = ray_dir / numpy.linalg.norm(ray_dir)
        plane_normal = numpy.array(plane_normal)
        q = ray_dir.dot(plane_normal)
        if q == 0:
            return None
        t = - (ray_near.dot(plane_normal) + plane_offset) / q
        if t < 0:
            return None
        return ray_near + t * ray_dir

    def double_click(self, event):
        if hasattr(self.parent, "clickcb") and self.parent.clickcb:
            self.parent.clickcb(event)

    def move(self, event):
        """React to mouse actions:
        no mouse: show red mousedrop
        LMB: rotate viewport
        LMB + Shift: move active object
        RMB: move viewport
        RMB: + Shift: None
        """
        self.mousepos = event.GetPosition() * self.GetContentScaleFactor()

        if event.Entering():
            # This makes sure we only set focus on a panel that is
            # in the currently active window and not any other window
            current_focus = self.FindFocus()
            if current_focus:
                if self.TopLevelParent == current_focus.TopLevelParent:
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

        wx.CallAfter(self.Refresh)
        event.Skip()

    def zoom(self, factor, to = None):
        glMatrixMode(GL_MODELVIEW)
        if to:
            delta_x = to[0]
            delta_y = to[1]
            glTranslatef(delta_x, delta_y, 0)
        glScalef(factor, factor, 1)
        self.zoom_factor *= factor
        if to:
            glTranslatef(-delta_x, -delta_y, 0)
        # For wxPython (<4.1) and GTK:
        # when you resize (enlarge) 3d view fast towards the log pane
        # sash garbage may remain in GLCanvas
        # The following refresh clears it at the cost of
        # doubled frame draws.
        # wx.CallAfter(self.Refresh)
        self.Refresh(False)

    def zoom_to_center(self, factor):
        self.canvas.SetCurrent(self.context)
        x, y, _ = self.mouse_to_3d(self.width / 2, self.height / 2)
        self.zoom(factor, (x, y))

    def handle_wheel_shift(self, event, wheel_delta):
        '''This runs when Mousewheel + Shift is used'''
        pass

    def handle_wheel(self, event):
        '''This runs when Mousewheel is used'''
        if self.wheelTimestamp == event.Timestamp:
            # filter duplicate event delivery in Ubuntu, Debian issue #1110
            return
        self.wheelTimestamp = event.Timestamp

        delta = event.GetWheelRotation()
        if event.ShiftDown():
            self.handle_wheel_shift(event, delta)
            return
        x, y = event.GetPosition() * self.GetContentScaleFactor()
        x, y, _ = self.mouse_to_3d(x, y)
        factor = 1.02 if event.ControlDown() else 1.05
        if delta > 0:
            self.zoom(factor, (x, y))
        else:
            self.zoom(1 / factor, (x, y))

    def wheel(self, event):
        """React to mouse wheel actions:
            without shift: zoom viewport
            with shift: run handle_wheel_shift
        """
        self.handle_wheel(event)
        wx.CallAfter(self.Refresh)

    def orbit(self, p1x, p1y, p2x, p2y):
        rz = p2x - p1x
        self.angle_z -= rz
        rot_z = axis_to_quat([0.0, 0.0, 1.0], self.angle_z)

        rx = p2y - p1y
        self.angle_x += rx
        rot_a = axis_to_quat([1.0, 0.0, 0.0], self.angle_x)
        return mulquat(rot_z, rot_a)

    def fit(self):
        '''Zoom to fit models to screen'''
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

    def handle_rotation(self, event):
        content_scale_factor = self.GetContentScaleFactor()
        if self.initpos is None:
            self.initpos = event.GetPosition() * content_scale_factor
        else:
            p1 = self.initpos
            p2 = event.GetPosition() * content_scale_factor
            sz = self.GetClientSize() * content_scale_factor
            p1x = p1[0] / (sz[0] / 2) - 1
            p1y = 1 - p1[1] / (sz[1] / 2)
            p2x = p2[0] / (sz[0] / 2) - 1
            p2y = 1 - p2[1] / (sz[1] / 2)
            quat = trackball(p1x, p1y, p2x, p2y, self.dist / 250.0)
            with self.rot_lock:
                if self.orbit_control:
                    self.basequat = self.orbit(p1x, p1y, p2x, p2y)
                else:
                    self.basequat = mulquat(self.basequat, quat)
            self.initpos = p2

    def handle_translation(self, event):
        content_scale_factor = self.GetContentScaleFactor()
        if self.initpos is None:
            self.initpos = event.GetPosition() * content_scale_factor
        else:
            p1 = self.initpos
            p2 = event.GetPosition() * content_scale_factor
            if self.orthographic:
                x1, y1, _ = self.mouse_to_3d(p1[0], p1[1])
                x2, y2, _ = self.mouse_to_3d(p2[0], p2[1])
                glTranslatef(x2 - x1, y2 - y1, 0)
            else:
                glTranslatef(p2[0] - p1[0], -(p2[1] - p1[1]), 0)
            self.initpos = p2
