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

from pyglet.gl import glPushMatrix, glPopMatrix

from .gl.panel import wxGLPanel
from .gl import actors


class StlViewPanel(wxGLPanel):

    gcode_lights = False

    def __init__(self, parent, size,
                 build_dimensions = None, circular = False,
                 antialias_samples = 0,
                 grid = (1, 10), perspective=False):
        if perspective:
            self.orthographic=False
        super().__init__(parent, wx.DefaultPosition, size, 0,
                         antialias_samples = antialias_samples)

        self.meshmodels = []
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
        self.gl_cursor = actors.MouseCursor()
        self.cutting_plane = actors.CuttingPlane(self.build_dimensions)
        self.dist = max(self.build_dimensions[0], self.build_dimensions[1])
        wx.CallAfter(self.forceresize) #why needed

    def Destroy(self):
        # Clean up vertex lists
        for model in self.meshmodels:
            model.delete()
        super().Destroy()

    # ==========================================================================
    # GLFrame OpenGL Event Handlers
    # ==========================================================================
    def OnInitGL(self, *args, call_reshape = True, **kwargs):
        '''Initialize OpenGL for use in the window.'''
        super().OnInitGL(*args, call_reshape, **kwargs)

        if hasattr(self.parent, "filenames") and self.parent.filenames:
            for filename in self.parent.filenames:
                self.parent.load_file(filename)
            self.parent.autoplate()
            if hasattr(self.parent, "loadcb"):
                self.parent.loadcb()
            self.parent.filenames = None

    def OnReshape(self):
        self.mview_initialized = False
        super().OnReshape()

    def forceresize(self):
        #print('forceresize')
        x, y = self.GetClientSize()
        #TODO: probably not needed
        self.SetClientSize((x, y+1))
        self.SetClientSize((x, y))
        self.initialized = False

    def handle_wheel_shift(self, event, wheel_delta):
        '''This runs when Mousewheel + Shift is used'''
        pass

    def keypress(self, event):
        """gets keypress events and moves/rotates active shape"""
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
        self.initialized = True
        #TODO: this probably creates constant redraw
        # create_objects is called during OnDraw, remove
        wx.CallAfter(self.Refresh)

    def prepare_model(self, m, scale):
        mesh = actors.MeshModel(m)
        self.meshmodels.append(mesh)
        # m.animoffset = 300
        # threading.Thread(target = self.anim, args = (m, )).start()
        wx.CallAfter(self.Refresh)

    def update_object_resize(self):
        '''called when the window receives only if opengl is initialized'''
        pass

    def draw_objects(self):
        '''called in the middle of ondraw after the buffer has been cleared'''
        # Since GL display lists are not used,
        # we don't need this any more.
        # self.create_objects()

        glPushMatrix()
        self.set_origin(self.platform)
        # Draw platform
        self.platform.draw()

        # Draw mouse
        inter = self.mouse_to_plane(self.mousepos[0], self.mousepos[1],
                                    plane_normal = (0, 0, 1), plane_offset = 0,
                                    local_transform = False)
        if inter is not None:
            self.gl_cursor.position = inter
            self.gl_cursor.draw()

        # Draw objects

        # Why would we disable face culling here?
        #glDisable(GL_CULL_FACE)
        glPushMatrix()
        for i in self.parent.models:
            model = self.parent.models[i]
            # Apply transformations and draw the models
            self.transform_and_draw(model, model.batch.draw)
        glPopMatrix()
        #glEnable(GL_CULL_FACE)

        # Draw cutting plane
        if self.parent.cutting:
            axis = self.parent.cutting_axis
            fixed_dist = self.parent.cutting_dist
            dist = self.get_cutting_dist(axis, fixed_dist)

            if dist is not None:
                direction = self.parent.cutting_direction
                self.cutting_plane.update(axis, direction, dist)
                self.cutting_plane.draw()

        glPopMatrix()

    # ==========================================================================
    # Utils
    # ==========================================================================
    def get_cutting_dist(self, cutting_axis, fixed_dist, local_transform = False):
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
        return dist

def main():
    app = wx.App(redirect = False)
    frame = wx.Frame(None, -1, "GL Window", size = (400, 400))
    StlViewPanel(frame)
    frame.Show(True)
    app.MainLoop()
    app.Destroy()

if __name__ == "__main__":
    main()
