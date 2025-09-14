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
import logging
from pathlib import Path

import numpy as np

from . import stltool
from .gl.panel import wxGLPanel
from .gl import actors

from .utils import install_locale
install_locale("pronterface")

# for type hints
from typing import Tuple, Union
Build_Dims = Tuple[int, int, int, int, int, int]


class StlViewPanel(wxGLPanel):

    def __init__(self, parent, size: wx.Size,
                 build_dimensions: Build_Dims = (200, 200, 100, 0, 0, 0),
                 circular: bool = False,
                 antialias_samples: int = 0,
                 grid: Tuple[int, int] = (1, 10),
                 perspective: bool = False) -> None:

        super().__init__(parent, wx.DefaultPosition, size, 0,
                         antialias_samples = antialias_samples,
                         build_dimensions = build_dimensions,
                         circular = circular,
                         grid = grid,
                         perspective = perspective)

        self.parent = parent
        self.initialized = False

        self.gl_cursor = actors.MouseCursor()
        self.cutting_plane = actors.CuttingPlane(self.build_dimensions)
        self.meshmodels = []

        logging.debug(_("GL: Initialised stlview"))

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

    def handle_wheel_shift(self, event: wx.MouseEvent) -> None:
        '''This runs when Mousewheel + Shift is used'''
        pass

    def anim(self, obj: stltool.stl) -> None:
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

    def prepare_model(self, m: stltool.stl, scale: float) -> None:
        self.set_current_context()
        mesh = actors.MeshModel(m)
        self.meshmodels.append(mesh)
        # m.animoffset = 300
        # threading.Thread(target = self.anim, args = (m, )).start()
        wx.CallAfter(self.Refresh)

    def draw_objects(self) -> None:
        '''called in the middle of ondraw after the buffer has been cleared'''

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
                # TODO: Check if plane has even changed (use buttonEvent?)
                self.cutting_plane.update_plane(axis, direction)
                self.cutting_plane.update_position(dist)
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

        if inter is not None and np.fabs(inter).max() + max_size / 2 < 2 * max_size:
            dist = inter[translate_axis[cutting_axis]]

        if dist is None or dist < -0.5 * ref_size or dist > 1.5 * ref_size:
            ref_plane = fallback_ref_planes[cutting_axis]
            ref_offset = fallback_ref_offsets[cutting_axis]

            inter = self.mouse_to_plane(self.mousepos[0], self.mousepos[1],
                                        plane_normal = ref_plane,
                                        plane_offset = ref_offset)

            if inter is not None and np.fabs(inter).max() + max_size / 2 < 2 * max_size:
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
    STL_TESTMODEL = Path(__file__, "../../testfiles/testgeometry_ascii.stl").resolve()
    app = wx.App(redirect = False)
    size = wx.Size(600, 450)
    frame = TestFrame(None, -1, "Mesh GL Window", size = size)
    frame.SetMinClientSize((200, 200))
    persp = False

    if 2 < len(sys.argv):
        persp = sys.argv[2] == "perspective"

    stl_panel = StlViewPanel(frame, size,
                             circular = False,
                             antialias_samples = 4,
                             perspective = persp,
                             )

    stl_panel.show_frametime = True
    stl_panel.init_frametime()
    stl_panel.set_current_context()

    # Load a stl model via cmd line argument
    if 1 < len(sys.argv) and Path(sys.argv[1]).is_file():
        testgeometry = sys.argv[1]
    else :
        testgeometry = STL_TESTMODEL
    modeldata = stltool.stl(testgeometry)
    modeldata.offsets = [65.0, 75.0, 0.0]
    modeldata.rot = 45.0
    modeldata.centeroffset = [-(modeldata.dims[1] + modeldata.dims[0]) / 2,
                              -(modeldata.dims[3] + modeldata.dims[2]) / 2,
                              0.0]
    modeldata.scale = [1.0, 1.0, 0.6]

    frame.models = {'example': modeldata}
    actors.MeshModel(modeldata)

    frame.Show(True)
    app.MainLoop()
    app.Destroy()

if __name__ == "__main__":
    main()

