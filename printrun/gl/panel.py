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
import time
import traceback
import numpy
import numpy.linalg

import wx
from wx import glcanvas

import pyglet
pyglet.options['debug_gl'] = True
pyglet.options['shadow_window'] = False

from pyglet.gl import glEnable, GL_LIGHTING, glLightfv, \
    GL_LIGHT0, GL_LIGHT1, GL_POSITION, GL_DIFFUSE, \
    GL_AMBIENT, GL_SPECULAR, GL_COLOR_MATERIAL, \
    glShadeModel, GL_SMOOTH, GL_NORMALIZE, GL_BLEND, glBlendFunc, \
    glClear, glClearColor, glClearDepth, GL_COLOR_BUFFER_BIT, GL_CULL_FACE, \
    GL_DEPTH_BUFFER_BIT, glDepthFunc, GL_DEPTH_TEST, \
    GLdouble, glGetDoublev, glGetIntegerv, GLint, \
    GL_LEQUAL, GL_MODELVIEW_MATRIX, GL_ONE_MINUS_SRC_ALPHA, \
    GL_PROJECTION_MATRIX, glScalef, GL_SRC_ALPHA, glTranslatef, \
    gluUnProject, glViewport, GL_VIEWPORT, glPushMatrix, glPopMatrix, \
    glMaterialfv, GL_FRONT_AND_BACK, glPolygonMode, \
    GL_AMBIENT_AND_DIFFUSE, glMaterialf, GL_SHININESS, GL_EMISSION, \
    GL_RESCALE_NORMAL, glColorMaterial, GL_FRONT, glRotatef, GL_FILL

from pyglet import gl
from .actors import Focus, vec
from .camera import Camera

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

    color_background = (200 / 255, 225 / 255, 250 / 255, 1.0)  # Light Blue

    # G-Code models and stl models use different lightscene
    gcode_lights = True
    wheelTimestamp = None
    show_fps = True

    def __init__(self, parent, pos = wx.DefaultPosition,
                 size = wx.DefaultSize, style = 0,
                 antialias_samples = 0):
        # Full repaint should not be a performance problem
        #TODO: test on windows, tested in Ubuntu
        style = style | wx.FULL_REPAINT_ON_RESIZE

        self.GLinitialized = False

        attribList = glcanvas.GLAttributes()
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

        self.width = 1.0
        self.height = 1.0
        self.camera = Camera(self)
        self.focus = Focus(self.camera)

        if self.show_fps:
            self.frametime = FrameTime()
            self.fps_counter = wx.StaticText(self, -1, '')
            font = wx.Font(16, family = wx.FONTFAMILY_MODERN, style = 0, weight = 90,
                           encoding = wx.FONTENCODING_DEFAULT)
            self.fps_counter.SetFont(font)

        ctx_attrs = glcanvas.GLContextAttrs()
        # FIXME: Pronterface supports only OpenGL 2.1 and compability mode at the moment
        # ctx_attrs.PlatformDefaults().CoreProfile().MajorVersion(3).MinorVersion(3).EndList()
        ctx_attrs.PlatformDefaults().EndList()
        self.context = glcanvas.GLContext(self.canvas, ctxAttrs = ctx_attrs)
        self.pygletcontext = None  # initialised with pyglet during glinit

        self.mousepos = (0, 0)
        self.parent = None
        self.buid_dimensions = (200, 200, 100, 0, 0, 0)

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

    def set_current_context(self) -> None:
        '''Set the GL context of this panel as current'''
        if not self.gl_broken:
            self.canvas.SetCurrent(self.context)

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
                logging.error("OpenGL failed, disabling it:"
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
        # Uncomment this line to see information about the created context
        # print(f"OpenGL context version: {self.pygletcontext.get_info().get_version()},\n",
        #      self.pygletcontext.get_info().get_renderer())

        # normal gl init
        glClearColor(*self.color_background)
        glClearDepth(1.0)  # set depth value to 1
        glDepthFunc(GL_LEQUAL)

        glEnable(GL_DEPTH_TEST)
        glEnable(GL_CULL_FACE)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        self._setup_lights()

        glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
        # Polygon mode is never changed, but you can uncomment
        # this line to show models as wireframe
        # glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)

        # Material specs are set here once and then we only change
        # the material colour by using glColor
        glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE, vec(0.5, 0, 0.3, 1))
        glMaterialfv(GL_FRONT, GL_SPECULAR, vec(0.85, 0.85, 0.85, 1))
        glMaterialf(GL_FRONT, GL_SHININESS, 96)
        glMaterialfv(GL_FRONT_AND_BACK, GL_EMISSION, vec(0, 0, 0, 0))

        # This enables tracking of the material colour,
        # now it can be changed only by calling glColor
        glEnable(GL_COLOR_MATERIAL)
        glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)

        if call_reshape:
            self.OnReshape()

    def OnReshape(self):
        """Reshape the OpenGL viewport based on the size of the window"""

        old_width, old_height = self.width, self.height

        new_size = self.GetClientSize() * self.GetContentScaleFactor()
        width, height = new_size.width, new_size.height

        if width < 1 or height < 1:
            return

        self.camera.update_size(width, height, self.GetContentScaleFactor())
        self.OnInitGL(call_reshape = False)
        # print('glViewport: ', width, height)
        glViewport(0, 0, width, height)
        self.camera.create_projection_matrix()

        self.width = max(float(width), 1.0)
        self.height = max(float(height), 1.0)

        if not self.camera.view_matrix_initialized:
            self.camera.reset_view_matrix(0.9)

        elif old_width is not None and old_height is not None:
            wratio = self.width / old_width
            hratio = self.height / old_height

            factor = min(wratio * self.camera.zoomed_width, hratio * self.camera.zoomed_height)
            x, y, _ = self.mouse_to_3d(self.width / 2, self.height / 2)
            self.camera.zoom(factor, (x, y))
            self.camera.zoomed_width *= wratio / factor
            self.camera.zoomed_height *= hratio / factor

        # Wrap text to the width of the window
        if self.GLinitialized:
            self.pygletcontext.set_current()
            self.update_object_resize()

    def _setup_lights(self):
        '''Sets the lightscene for gcode and stl models'''
        glEnable(GL_LIGHTING)

        glEnable(GL_LIGHT0)
        glLightfv(GL_LIGHT0, GL_AMBIENT, vec(0.0, 0.0, 0.0, 1.0))
        glLightfv(GL_LIGHT0, GL_SPECULAR, vec(0.6, 0.6, 0.6, 1.0))
        glLightfv(GL_LIGHT0, GL_DIFFUSE, vec(0.8, 0.8, 0.8, 1.0))
        glLightfv(GL_LIGHT0, GL_POSITION, vec(1.0, 2.0, 2.0, 0.0))

        glEnable(GL_LIGHT1)
        glLightfv(GL_LIGHT1, GL_AMBIENT, vec(0.0, 0.0, 0.0, 1.0))
        glLightfv(GL_LIGHT1, GL_SPECULAR, vec(0.6, 0.6, 0.6, 1.0))
        glLightfv(GL_LIGHT1, GL_DIFFUSE, vec(0.8, 0.8, 0.8, 1.0))
        glLightfv(GL_LIGHT1, GL_POSITION, vec(-1.2, -1, 2.4, 0.0))

        if self.gcode_lights:
            # Normalises the normal vectors after scaling
            glEnable(GL_NORMALIZE)
        else:
            # GL_NORMALIZE makes stl objects look too bright (?)
            glEnable(GL_RESCALE_NORMAL)

        glShadeModel(GL_SMOOTH)

    def resetview(self):
        self.canvas.SetCurrent(self.context)
        self.camera.reset_view_matrix(0.9)
        self.camera.reset_rotation()
        wx.CallAfter(self.Refresh)

    def DrawCanvas(self):
        """Draw the window."""
        self.pygletcontext.set_current()
        glClearColor(*self.color_background)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        glPushMatrix()
        self.draw_objects()
        glPopMatrix()

        if self.canvas.HasFocus():
            self.focus.draw()

        self.canvas.SwapBuffers()

        if self.show_fps:
            self.frametime.update()
            self.fps_counter.SetLabel(self.frametime.get())

    def transform_and_draw(self, actor, draw_function):
        '''Apply transformations to the model and then
        draw it with the given draw function'''
        glPushMatrix()
        self._create_model_matrix(actor)
        # Draw the models
        draw_function()
        glPopMatrix()

    def _create_model_matrix(self, model):
        glTranslatef(*model.offsets)
        glRotatef(model.rot, 0.0, 0.0, 1.0)
        glTranslatef(*model.centeroffset)
        glScalef(*model.scale)

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
    # Mouse and Utilities
    # ==========================================================================
    def mouse_to_3d(self, x, y, z = 1.0, local_transform = False):
        x = float(x)
        y = self.height - float(y)
        # The following could work if we were not initially scaling to zoom on
        # the bed
        # if self.camera.is_orthographic:
        #    return (x - self.width / 2, y - self.height / 2, 0)
        pmat = (GLdouble * 16)()
        mvmat = self.camera.get_view_matrix(local_transform, self.build_dimensions)
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
        # Ray from z-depth 1.0 to 0.0
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
        mvmat = self.camera.get_view_matrix(local_transform, self.build_dimensions)
        gluUnProject(x, y, 1.0, mvmat, pmat, viewport, px, py, pz)
        ray_far = (px.value, py.value, pz.value)
        gluUnProject(x, y, 0.0, mvmat, pmat, viewport, px, py, pz)
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
                self.camera.handle_rotation(event)
            elif event.RightIsDown():
                self.camera.handle_translation(event)
            self.Refresh(False)

        elif event.LeftUp() or event.RightUp():
            self.camera.initpos = None

        wx.CallAfter(self.Refresh)
        event.Skip()

    def zoom_to_center(self, factor):
        self.canvas.SetCurrent(self.context)
        x, y, _ = self.mouse_to_3d(self.width / 2, self.height / 2)
        self.camera.zoom(factor, (x, y))
        wx.CallAfter(self.Refresh)

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
            self.camera.zoom(factor, (x, y))
        else:
            self.camera.zoom(1 / factor, (x, y))

    def wheel(self, event):
        """React to mouse wheel actions:
            without shift: zoom viewport
            with shift: run handle_wheel_shift
        """
        self.handle_wheel(event)
        wx.CallAfter(self.Refresh)

    def fit(self):
        '''Zoom to fit models to screen'''

        # FIXME: The models in G-Code Plater are different than
        # in the main view. So fit() currently doesn't work here.
        if hasattr(self.parent, 'models'):
            return

        if not self.parent.model or not self.parent.model.loaded:
            return

        self.canvas.SetCurrent(self.context)
        dims = gcode_dims(self.parent.model.gcode)
        self.camera.reset_view_matrix(1.0)

        center_x = (dims[0][0] + dims[0][1]) / 2
        center_y = (dims[1][0] + dims[1][1]) / 2
        center_x = self.build_dimensions[0] / 2 - center_x
        center_y = self.build_dimensions[1] / 2 - center_y

        if self.camera.is_orthographic:
            ratio = float(self.camera.dist) / max(dims[0][2], dims[1][2])
            glScalef(ratio, ratio, 1)

        glTranslatef(center_x, center_y, 0)
        wx.CallAfter(self.Refresh)


class FrameTime:

    SMOOTHING_FACTOR = 0.8
    MAX_FPS = 2000

    def __init__(self) -> None:
        self.delta_time = 0
        self.last_frame = time.perf_counter()
        self.avg_fps = -1

    def update(self) -> None:
        current_frame = time.perf_counter()
        self.delta_time = current_frame - self.last_frame
        self.last_frame = current_frame
        current_fps = round(min(1 / self.delta_time, self.MAX_FPS))

        if self.avg_fps < 0:
            self.avg_fps = current_fps
        else:
            self.avg_fps = round((self.avg_fps * self.SMOOTHING_FACTOR) + (current_fps * (1 - self.SMOOTHING_FACTOR)))

    def get(self) -> str:
        return f" {self.delta_time * 1000:4.2f} ms, {self.avg_fps:3d} FPS"
