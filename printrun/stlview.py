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
import sys
from . import stltool

import numpy

from .gl.panel import wxGLPanel
from .gl import actors

# for type hints
from typing import Tuple, Union
from printrun.stltool import stl
Build_Dims = Tuple[int, int, int, int, int, int]


class StlViewPanel(wxGLPanel):

    gcode_lights = False

    def __init__(self, parent, size: wx.Size,
                 build_dimensions: Build_Dims = (200, 200, 100, 0, 0, 0),
                 circular: bool = False,
                 antialias_samples: int = 0,
                 grid: Tuple[int, int] = (1, 10),
                 perspective: bool = False) -> None:

        super().__init__(parent, wx.DefaultPosition, size, 0,
                         antialias_samples = antialias_samples,
                         build_dimensions = build_dimensions)

        # Set projection of camera
        if perspective:
            self.camera.is_orthographic = False

        self.meshmodels = []
        self.rot = 0.0
        self.canvas.Bind(wx.EVT_MOUSE_EVENTS, self.move)
        self.canvas.Bind(wx.EVT_MOUSEWHEEL, self.wheel)
        self.canvas.Bind(wx.EVT_LEFT_DCLICK, self.double_click)

        self.initialized = False
        self.parent = parent

        self.platform = actors.Platform(self.build_dimensions,
                                        circular = circular,
                                        grid = grid)
        self.gl_cursor = actors.MouseCursor()
        self.cutting_plane = actors.CuttingPlane(self.build_dimensions)

    def Destroy(self) -> None:
        # Clean up vertex lists
        for model in self.meshmodels:
            model.delete()
        super().Destroy()

    # ==========================================================================
    # GLFrame OpenGL Event Handlers
    # ==========================================================================
    def OnInitGL(self, *args, call_reshape: bool = True, **kwargs) -> None:
        '''Initialize OpenGL for use in the window.'''
        super().OnInitGL(call_reshape, *args, **kwargs)

        if hasattr(self.parent, "filenames") and self.parent.filenames:
            for filename in self.parent.filenames:
                self.parent.load_file(filename)
            self.parent.autoplate()
            if hasattr(self.parent, "loadcb"):
                self.parent.loadcb()
            self.parent.filenames = None

    def OnReshape(self) -> None:
        self.camera.view_matrix_initialized = False
        super().OnReshape()

    def forceresize(self) -> None:
        #print('forceresize')
        x, y = self.GetClientSize()
        #TODO: probably not needed
        self.SetClientSize((x, y + 1))
        self.SetClientSize((x, y))
        self.initialized = False

    def handle_wheel_shift(self, event: wx.MouseEvent, wheel_delta: int) -> None:
        '''This runs when Mousewheel + Shift is used'''
        pass

    def anim(self, obj: stl) -> None:
        g = 50 * 9.81
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

    def create_objects(self) -> None:
        '''create opengl objects when opengl is initialized'''
        if not self.platform.initialized:
            self.platform.init()
        self.initialized = True
        #TODO: this probably creates constant redraw
        # create_objects is called during OnDraw, remove
        wx.CallAfter(self.Refresh)

    def prepare_model(self, m: stl, scale: float) -> None:
        mesh = actors.MeshModel(m)
        self.meshmodels.append(mesh)
        # m.animoffset = 300
        # threading.Thread(target = self.anim, args = (m, )).start()
        wx.CallAfter(self.Refresh)

    def update_object_resize(self) -> None:
        '''called when the window receives only if opengl is initialized'''
        pass

    def draw_objects(self) -> None:
        '''called in the middle of ondraw after the buffer has been cleared'''
        # Since GL display lists are not used,
        # we don't need this line anymore.
        # self.create_objects()

        # Draw platform
        self.platform.draw()

        # Draw mouse
        intersection = self.mouse_to_plane(self.mousepos[0], self.mousepos[1],
                                    plane_normal = (0, 0, 1), plane_offset = 0)

        if intersection is not None:
            self.gl_cursor.position = intersection
            self.gl_cursor.draw()

        # Draw objects
        for i in self.parent.models:
            model = self.parent.models[i]
            # Apply transformations and draw the models
            self.transform_and_draw(model, model.batch.draw)

        # Draw cutting plane
        if self.parent.cutting:
            axis = self.parent.cutting_axis
            fixed_dist = self.parent.cutting_dist
            dist = self.get_cutting_dist(axis, fixed_dist)

            if dist is not None:
                direction = self.parent.cutting_direction
                self.cutting_plane.update(axis, direction, dist)
                self.cutting_plane.draw()

    # ==========================================================================
    # Utils
    # ==========================================================================
    def get_cutting_dist(self, cutting_axis: str,
                         fixed_dist: Union[float, None]
                         ) -> Union[float, None]:

        if fixed_dist is not None:
            return fixed_dist

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
                                    plane_offset = ref_offset)

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
                                        plane_offset = ref_offset)

            if inter is not None and numpy.fabs(inter).max() + max_size / 2 < 2 * max_size:
                dist = inter[translate_axis[cutting_axis]]

        if dist is not None:
            dist = min(1.5 * ref_size, max(-0.5 * ref_size, dist))

        return dist


class TestFrame(wx.Frame):

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.models = {}

        # Mock a cutting plane to test rendering
        self.cutting = True
        self.cutting_axis = 'x'
        self.cutting_direction = 1.0
        self.cutting_dist = 29.0


def main() -> None:
    app = wx.App(redirect = False)
    size = wx.Size(600, 450)
    frame = TestFrame(None, -1, "Mesh GL Window", size = size)
    frame.SetMinClientSize((200, 200))

    stl_panel = StlViewPanel(frame, size,
                             circular = False,
                             antialias_samples = 4,
                             perspective = False)

    stl_panel.set_current_context()

    # Load a stl model via cmd line argument
    modeldata = stltool.stl(sys.argv[1])
    modeldata.offsets = [65.0, 75.0, 0.0]
    modeldata.rot = 0.0
    modeldata.centeroffset = [-(modeldata.dims[1] + modeldata.dims[0]) / 2,
                              -(modeldata.dims[3] + modeldata.dims[2]) / 2,
                              0.0]
    modeldata.scale = [1.0, 1.0, 1.0]

    frame.models = {'example': modeldata}
    actors.MeshModel(modeldata)

    frame.Show(True)
    app.MainLoop()
    app.Destroy()

if __name__ == "__main__":
    main()

