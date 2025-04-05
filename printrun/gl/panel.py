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

import wx
from wx import glcanvas
import numpy as np

import pyglet
pyglet.options['debug_gl'] = True
pyglet.options['shadow_window'] = False

from pyglet.gl import GLint, GLdouble, glEnable,glBlendFunc,glViewport, \
    glClear, glClearColor, glClearDepth, glDepthFunc, glGetDoublev, \
    glGetIntegerv, glPolygonMode, \
    GL_LEQUAL, GL_ONE_MINUS_SRC_ALPHA,GL_DEPTH_BUFFER_BIT, \
    GL_SRC_ALPHA, GL_BLEND, GL_COLOR_BUFFER_BIT, GL_CULL_FACE, \
    GL_VIEWPORT, GL_FRONT_AND_BACK,GL_DEPTH_TEST, GL_FILL

# those are legacy calls which need to be replaced
from pyglet.gl import GL_LIGHTING, GL_LIGHT0, GL_LIGHT1, GL_POSITION, \
    GL_DIFFUSE, GL_AMBIENT, GL_SPECULAR, GL_COLOR_MATERIAL, GL_SMOOTH, \
    GL_NORMALIZE, GL_PROJECTION_MATRIX, GL_AMBIENT_AND_DIFFUSE, \
    GL_SHININESS, GL_EMISSION, GL_MODELVIEW, \
    glMaterialf, glColorMaterial, glMaterialfv, glLightfv, glShadeModel, \
    glPushMatrix, glPopMatrix, glMultMatrixd, glMatrixMode

from pyglet import gl

from .mathutils import vec, np_unproject, np_to_gl_mat, \
                       mat4_translation, mat4_rotation, mat4_scaling
from . import actors
from . import camera
from . import keyboardinput as kbi

# for type hints
from typing import TYPE_CHECKING, Any, Tuple, Union, Callable, Optional
from printrun import stltool
from printrun import gcoder
Build_Dims = Tuple[int, int, int, int, int, int]
Gcode_Dims = Tuple[Tuple[float , float, float],
                   Tuple[float , float, float],
                   Tuple[float , float, float]]
if TYPE_CHECKING:
    from printrun.gcview import GCObject

def gcode_dims(g: gcoder.GCode) -> Gcode_Dims:
    return ((g.xmin, g.xmax, g.width),
            (g.ymin, g.ymax, g.depth),
            (g.zmin, g.zmax, g.height))

# When Subclassing wx.Window in Windows the focus goes to the wx.Window
# instead of GLCanvas and it does not draw the focus rectangle and
# does not consume used keystrokes
# BASE_CLASS = wx.Window
# Subclassing Panel solves problem In Windows
# BASE_CLASS = wx.Panel
# BASE_CLASS = wx.ScrolledWindow
BASE_CLASS = glcanvas.GLCanvas

class wxGLPanel(BASE_CLASS):
    '''A simple class for using OpenGL with wxPython.'''

    color_background = (200 / 255, 225 / 255, 250 / 255, 1.0)  # Light Blue

    wheelTimestamp = None
    show_frametime = False

    def __init__(self, parent, pos: wx.Point = wx.DefaultPosition,
                 size: wx.Size = wx.DefaultSize, style = 0,
                 antialias_samples: int = 0,
                 build_dimensions: Build_Dims = (200, 200, 100, 0, 0, 0),
                 circular: bool = False,
                 grid: Tuple[int, int] = (1, 10),
                 perspective: bool = False
                 ) -> None:
        # Full repaint should not be a performance problem
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
            self.canvas: glcanvas.GLCanvas = self  # type: ignore
        else:
            super().__init__(parent, wx.ID_ANY, pos, size, style)
            self.canvas = glcanvas.GLCanvas(self, attribList, wx.ID_ANY, pos, size, style)

        self.width = 1.0
        self.height = 1.0

        self.camera = camera.Camera(self, build_dimensions, ortho = not perspective)
        self.focus = actors.Focus(self.camera)
        self.platform = actors.Platform(build_dimensions, circular = circular, grid = grid)
        self.keyinput = kbi.KeyboardInput(self.canvas, self.zoom_to_center,
                                      self.fit, self.resetview)

        if self.show_frametime:
            self.init_frametime()

        ctx_attrs = glcanvas.GLContextAttrs()
        # FIXME: Pronterface supports only OpenGL 2.1 and compability mode at the moment
        # ctx_attrs.PlatformDefaults().CoreProfile().MajorVersion(3).MinorVersion(3).EndList()
        ctx_attrs.PlatformDefaults().EndList()
        self.context = glcanvas.GLContext(self.canvas, ctxAttrs = ctx_attrs)
        # initialised with pyglet during glinit
        self.pygletcontext: Optional[gl.Context] = None

        self.mousepos = (0, 0)
        self.parent = parent
        self.build_dimensions = build_dimensions

        self.gl_broken = False

        # bind events
        self.canvas.Bind(wx.EVT_SIZE, self.processSizeEvent)
        if self.canvas is not self:
            self.Bind(wx.EVT_SIZE, self.OnScrollSize)
            # do not focus parent (panel like) but its canvas
            self.SetCanFocus(False)

        self.canvas.Bind(wx.EVT_ERASE_BACKGROUND, self.processEraseBackgroundEvent)
        self.canvas.Bind(wx.EVT_PAINT, self.processPaintEvent)
        self.canvas.Bind(wx.EVT_SET_FOCUS, self.processFocus)
        self.canvas.Bind(wx.EVT_KILL_FOCUS, self.processKillFocus)

    def set_current_context(self) -> None:
        '''Set the GL context of this panel as current'''
        if not self.gl_broken:
            self.canvas.SetCurrent(self.context)

    def processFocus(self, event: wx.FocusEvent) -> None:
        # print('processFocus')
        self.Refresh(False)
        event.Skip()

    def processKillFocus(self, event: wx.FocusEvent) -> None:
        # print('processKillFocus')
        self.Refresh(False)
        event.Skip()

    # def processIdle(self, event):
    #     print('processIdle')
    #     event.Skip()

    def Layout(self) -> Any:
        return super().Layout()

    def Refresh(self, eraseback: bool = True) -> Any:
        # print('Refresh')
        return super().Refresh(eraseback)

    def OnScrollSize(self, event: wx.SizeEvent) -> None:
        self.canvas.SetSize(event.Size)

    def processEraseBackgroundEvent(self, event: wx.EraseEvent) -> None:
        '''Process the erase background event.'''
        pass  # Do nothing, to avoid flashing on MSWin

    def processSizeEvent(self, event: wx.SizeEvent) -> None:
        '''Process the resize event.'''

        # print('processSizeEvent frozen', self.IsFrozen(), event.Size.x, self.ClientSize.x)
        if not self.IsFrozen() and self.canvas.IsShownOnScreen():
            # Make sure the frame is shown before calling SetCurrent.
            self.set_current_context()
            self.OnReshape()

            # self.Refresh(False)
            # print('Refresh')
        event.Skip()

    def processPaintEvent(self, event: wx.PaintEvent) -> None:
        '''Process the drawing event.'''
        # print('wxGLPanel.processPaintEvent', self.ClientSize.Width)
        self.set_current_context()

        if not self.gl_broken:
            try:
                self.OnInitGL()
                self.DrawCanvas()
            except pyglet.gl.GLException:
                self.gl_broken = True
                logging.error("OpenGL failed, disabling it:"
                              + "\n" + traceback.format_exc())
        event.Skip()

    def Destroy(self) -> None:
        # clean up the pyglet OpenGL context
        assert self.pygletcontext is not None
        self.pygletcontext.destroy()
        # call the super method
        super().Destroy()

    def init_frametime(self) -> None:
        self.frametime = FrameTime()
        self.frametime_counter = wx.StaticText(self, -1, '')
        font = wx.Font(12, family = wx.FONTFAMILY_MODERN, style = 0, weight = 90,
                       encoding = wx.FONTENCODING_DEFAULT)
        self.frametime_counter.SetFont(font)
        self.frametime_counter.SetForegroundColour(wx.WHITE)
        self.frametime_counter.SetBackgroundColour(wx.Colour('DIM GREY'))
        sizer = wx.BoxSizer()
        sizer.Add(self.frametime_counter, 0, wx.ALIGN_BOTTOM | wx.ALL, 4)
        self.SetSizer(sizer)

    # ==========================================================================
    # GLFrame OpenGL Event Handlers
    # ==========================================================================
    def OnInitGL(self, call_reshape: bool = True) -> None:
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
        self._setup_material()

        if call_reshape:
            self.OnReshape()

    def OnReshape(self) -> None:
        """Reshape the OpenGL viewport based on the size of the window"""
        self.set_current_context()
        old_width, old_height = self.width, self.height

        new_size = self.GetClientSize() * self.GetContentScaleFactor()
        width, height = new_size.width, new_size.height

        if width < 1 or height < 1:
            return

        self.camera.update_size(width, height, self.GetContentScaleFactor())
        self.focus.update_size()
        self.OnInitGL(call_reshape = False)
        # print('glViewport: ', width, height)
        glViewport(0, 0, width, height)
        self.camera.create_projection_matrix()

        self.width = max(float(width), 1.0)
        self.height = max(float(height), 1.0)

        if not self.camera.view_matrix_initialized:
            self.camera.reset_view_matrix()

        elif old_width is not None and old_height is not None:
            wratio = self.width / old_width
            hratio = self.height / old_height

            if wratio < 1.0 and hratio < 1.0:
                factor = min(wratio, hratio)
            elif hratio == 1.0:
                factor = wratio
            elif wratio == 1.0:
                factor = hratio
            elif wratio > 1.0 and hratio > 1.0:
                factor = max(wratio, hratio)
            else:
                factor = 1.0

            self.camera.zoom(factor)

    def _setup_lights(self) -> None:
        '''Sets the lightscene for gcode and stl models'''
        glEnable(GL_LIGHTING)

        glEnable(GL_LIGHT0)
        glLightfv(GL_LIGHT0, GL_AMBIENT, vec(0.0, 0.0, 0.0, 1.0))
        glLightfv(GL_LIGHT0, GL_SPECULAR, vec(0.6, 0.6, 0.6, 1.0))
        glLightfv(GL_LIGHT0, GL_DIFFUSE, vec(0.7, 0.7, 0.7, 1.0))
        glLightfv(GL_LIGHT0, GL_POSITION, vec(0.9, 2.8, 1.7, 0.0))

        glEnable(GL_LIGHT1)
        glLightfv(GL_LIGHT1, GL_AMBIENT, vec(0.0, 0.0, 0.0, 1.0))
        glLightfv(GL_LIGHT1, GL_SPECULAR, vec(0.6, 0.6, 0.6, 1.0))
        glLightfv(GL_LIGHT1, GL_DIFFUSE, vec(0.7, 0.7, 0.7, 1.0))
        glLightfv(GL_LIGHT1, GL_POSITION, vec(-1.2, -1.0, 2.2, 0.0))

        glEnable(GL_NORMALIZE)
        glShadeModel(GL_SMOOTH)

    def _setup_material(self) -> None:
        '''Sets the material attributes for all objects'''

        # Switch this two lines to show models as wireframe
        glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
        # glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)

        # Material specs are set here once and only the
        # the material colour is changed later
        glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE, vec(0.5, 0.1, 0.3, 1.0))
        glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, vec(0.35, 0.35, 0.35, 1.0))
        glMaterialf(GL_FRONT_AND_BACK, GL_SHININESS, 80.0)
        glMaterialfv(GL_FRONT_AND_BACK, GL_EMISSION, vec(0.0, 0.0, 0.0, 1.0))

        # This enables tracking of the material colour,
        # now it can be changed only by calling glColor
        glEnable(GL_COLOR_MATERIAL)
        glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)

    def resetview(self) -> None:
        self.set_current_context()
        self.camera.reset_view_matrix()
        wx.CallAfter(self.Refresh)

    def recreate_platform(self, build_dimensions: Build_Dims,
                          circular: bool, grid: Tuple[int, int],
                          colour: Tuple[float, float, float]) -> None:

        self.platform = actors.Platform(build_dimensions,
                                 circular = circular,
                                 grid = grid)
        self.platform.update_colour(colour)
        self.camera.update_build_dims(build_dimensions)
        wx.CallAfter(self.Refresh)

    def DrawCanvas(self) -> None:
        """Draw the window."""
        self.set_current_context()

        if self.show_frametime:
            self.frametime.start_frame()

        glClearColor(*self.color_background)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        self.platform.draw()
        self.draw_objects()

        if self.canvas.HasFocus():
            self.focus.draw()

        self.canvas.SwapBuffers()

        if self.show_frametime:
            self.frametime.end_frame()
            self.frametime_counter.SetLabel(self.frametime.get())

    def transform_and_draw(self, model: Union['GCObject', stltool.stl],
                           draw_function: Callable[[], None]) -> None:
        '''Apply transformations to the model and then
        draw it with the given draw function'''
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        self._load_model_matrix(model)
        # Draw the models
        draw_function()
        glPopMatrix()

    def _load_model_matrix(self, model: Union['GCObject', stltool.stl]) -> None:
        tm = mat4_translation(*model.offsets)
        rm = mat4_rotation(0.0, 0.0, 1.0, model.rot)
        tc = mat4_translation(*model.centeroffset)
        sm = mat4_scaling(*model.scale)
        mat = sm @ tc @ rm @ tm

        glMultMatrixd(np_to_gl_mat(mat))

    # ==========================================================================
    # To be implemented by a sub class
    # ==========================================================================
    def create_objects(self) -> None:
        '''create opengl objects when opengl is initialized'''
        pass

    def draw_objects(self) -> None:
        '''called in the middle of ondraw after the buffer has been cleared'''
        pass

    # ==========================================================================
    # Mouse and Utilities
    # ==========================================================================
    def mouse_to_3d(self, x: float, y: float, z = 1.0
                    ) -> Tuple[float, float, float]:
        x = float(x)
        y = self.height - float(y)

        pmat = (GLdouble * 16)()
        mvmat = self.camera.get_view_matrix()
        viewport = (GLint * 4)()
        px = (GLdouble)()
        py = (GLdouble)()
        pz = (GLdouble)()
        glGetIntegerv(GL_VIEWPORT, viewport)
        glGetDoublev(GL_PROJECTION_MATRIX, pmat)

        np_unproject(x, y, z, mvmat, pmat, viewport, px, py, pz)

        return px.value, py.value, pz.value

    def mouse_to_ray(self, x: float, y: float,
                     ) -> Tuple[Tuple[float, float, float], Tuple[float, float, float]]:
        # Ray from z-depth 1.0 to 0.0
        x = float(x)
        y = self.height - float(y)
        pmat = (GLdouble * 16)()
        mvmat = (GLdouble * 16)()
        viewport = (GLint * 4)()
        px = (GLdouble)()
        py = (GLdouble)()
        pz = (GLdouble)()
        # FIXME: This can be replaced with self.width, self.height
        glGetIntegerv(GL_VIEWPORT, viewport)
        glGetDoublev(GL_PROJECTION_MATRIX, pmat)
        mvmat = self.camera.get_view_matrix()
        np_unproject(x, y, 1.0, mvmat, pmat, viewport, px, py, pz)
        ray_far = (px.value, py.value, pz.value)
        np_unproject(x, y, 0.0, mvmat, pmat, viewport, px, py, pz)
        ray_near = (px.value, py.value, pz.value)
        return ray_near, ray_far

    def mouse_to_plane(self, x: float, y: float,
                       plane_normal: Tuple[float, float, float],
                       plane_offset: float
                       ) -> Union[Tuple[float, float, float], None]:
        # Ray/plane intersection
        ray_near, ray_far = self.mouse_to_ray(x, y)
        ray_near = np.array(ray_near)
        ray_far = np.array(ray_far)
        ray_dir = ray_far - ray_near
        ray_dir = ray_dir / np.linalg.norm(ray_dir)
        plane_normal_np = np.array(plane_normal)
        q = ray_dir.dot(plane_normal_np)
        if q == 0:
            return None
        t = - (ray_near.dot(plane_normal_np) + plane_offset) / q
        if t < 0:
            return None
        return ray_near + t * ray_dir

    def double_click(self, event: wx.MouseEvent) -> None:
        if hasattr(self.parent, "clickcb") and self.parent.clickcb:
            self.parent.clickcb(event)

    def move(self, event: wx.MouseEvent) -> None:
        """React to mouse actions:
        no mouse: show red mousedrop
        LMB: rotate viewport
        LMB + Shift: move active object
        RMB: move viewport
        RMB: + Shift: None
        """

        if event.Entering():
            # This makes sure we only set focus on a panel that is
            # in the currently active window and not any other window
            current_focus = self.FindFocus()
            if current_focus:
                if self.TopLevelParent == current_focus.TopLevelParent:
                    self.canvas.SetFocus()
            event.Skip()
            return

        self.set_current_context()
        self.mousepos = event.GetPosition() * self.GetContentScaleFactor()

        if event.Dragging():
            if event.LeftIsDown():
                self.camera.handle_rotation(event)
            elif event.RightIsDown():
                self.camera.handle_translation(event)
            self.Refresh(False)

        elif event.LeftUp() or event.RightUp():
            self.camera.init_rot_pos = None
            self.camera.init_trans_pos = None


        wx.CallAfter(self.Refresh)
        event.Skip()

    def zoom_to_center(self, factor: float) -> None:
        self.set_current_context()
        self.camera.zoom(factor)
        wx.CallAfter(self.Refresh)

    def handle_wheel_shift(self, event: wx.MouseEvent, wheel_delta: int) -> None:
        '''This runs when Mousewheel + Shift is used'''
        pass

    def handle_wheel(self, event: wx.MouseEvent) -> None:
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
        factor = 1.02 if event.ControlDown() else 1.05
        if delta > 0:
            self.camera.zoom(factor, (x, y))
        else:
            self.camera.zoom(1 / factor, (x, y))

    def wheel(self, event: wx.MouseEvent) -> None:
        """React to mouse wheel actions:
            without shift: zoom viewport
            with shift: run handle_wheel_shift
        """
        self.set_current_context()
        self.handle_wheel(event)
        wx.CallAfter(self.Refresh)

    def fit(self) -> None:
        '''Zoom to fit models to screen'''
        #FIXME: The models in the Platers are organised differently than in
        # the in the main view. So fit() is currently not implemented here.
        if hasattr(self.parent, 'l'):
            # Parent is of class objectplater
            self.resetview()
            return

        if self.parent.model and self.parent.model.loaded:
            model = self.parent.model

        else:
            self.resetview()
            return

        self.set_current_context()
        dims = gcode_dims(model.gcode)
        self.camera.reset_view_matrix()

        center_x = (dims[0][0] + dims[0][1]) / 2
        center_y = (dims[1][0] + dims[1][1]) / 2
        center_x = self.build_dimensions[0] / 2 - center_x
        center_y = self.build_dimensions[1] / 2 - center_y

        if self.camera.is_orthographic:
            ratio = float(self.camera.dist) / max(dims[0][2], dims[1][2])
            self.camera.zoom(ratio, rebuild_mat=False)

        self.camera.move_rel(-center_x, -center_y, 0.0)

        wx.CallAfter(self.Refresh)


class FrameTime:

    FRAME_MIDDLE = 20

    def __init__(self) -> None:
        self.t_frame_start = 0.0
        self.framecount = 0
        self.timesum = 0.0
        self.avg_frametime = 0.0
        self.avg_fps = 0

    def start_frame(self) -> None:
        self.t_frame_start = time.perf_counter()

    def end_frame(self) -> None:
        self.framecount += 1
        self.timesum += time.perf_counter() - self.t_frame_start

        if self.framecount >= self.FRAME_MIDDLE:
            self.avg_frametime = self.timesum / self.framecount
            self.avg_fps = int(self.framecount / self.timesum)

            self.framecount = 0
            self.timesum = 0.0

    def get(self) -> str:
        return f" avg. {self.avg_frametime * 1000:4.2f} ms ({self.avg_fps:4d} FPS) "

