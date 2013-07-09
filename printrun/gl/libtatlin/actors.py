# -*- coding: utf-8 -*-
# Copyright (C) 2013 Guillaume Seguin
# Copyright (C) 2011 Denis Kobozev
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

import time
import numpy
import math
import logging

from pyglet.gl import *
from pyglet import gl
from pyglet.graphics.vertexbuffer import create_buffer, VertexBufferObject

from printrun.printrun_utils import install_locale
install_locale('pronterface')

def compile_display_list(func, *options):
    display_list = glGenLists(1)
    glNewList(display_list, GL_COMPILE)
    func(*options)
    glEndList()
    return display_list

def numpy2vbo(nparray, target = GL_ARRAY_BUFFER, usage = GL_STATIC_DRAW, use_vbos = True):
    vbo = create_buffer(nparray.nbytes, target = target, usage = usage, vbo = use_vbos)
    vbo.bind()
    vbo.set_data(nparray.ctypes.data)
    return vbo

class BoundingBox(object):
    """
    A rectangular box (cuboid) enclosing a 3D model, defined by lower and upper corners.
    """
    def __init__(self, upper_corner, lower_corner):
        self.upper_corner = upper_corner
        self.lower_corner = lower_corner

    @property
    def width(self):
        width = abs(self.upper_corner[0] - self.lower_corner[0])
        return round(width, 2)

    @property
    def depth(self):
        depth = abs(self.upper_corner[1] - self.lower_corner[1])
        return round(depth, 2)

    @property
    def height(self):
        height = abs(self.upper_corner[2] - self.lower_corner[2])
        return round(height, 2)


class Platform(object):
    """
    Platform on which models are placed.
    """
    graduations_major = 10

    def __init__(self, build_dimensions, light = False):
        self.light = light
        self.width = build_dimensions[0]
        self.depth = build_dimensions[1]
        self.height = build_dimensions[2]
        self.xoffset = build_dimensions[3]
        self.yoffset = build_dimensions[4]
        self.zoffset = build_dimensions[5]

        self.color_grads_minor  = (0xaf / 255, 0xdf / 255, 0x5f / 255, 0.1)
        self.color_grads_interm = (0xaf / 255, 0xdf / 255, 0x5f / 255, 0.2)
        self.color_grads_major  = (0xaf / 255, 0xdf / 255, 0x5f / 255, 0.33)
        self.color_fill         = (0xaf / 255, 0xdf / 255, 0x5f / 255, 0.05)

        self.initialized = False
        self.loaded      = True

    def init(self):
        self.display_list = compile_display_list(self.draw)
        self.initialized = True

    def draw(self):
        glPushMatrix()

        glTranslatef(self.xoffset, self.yoffset, self.zoffset)

        def color(i):
            if i % self.graduations_major == 0:
                glColor4f(*self.color_grads_major)
            elif i % (self.graduations_major / 2) == 0:
                glColor4f(*self.color_grads_interm)
            else:
                if self.light: return False
                glColor4f(*self.color_grads_minor)
            return True

        # draw the grid
        glBegin(GL_LINES)
        for i in range(0, int(math.ceil(self.width + 1))):
            if color(i):
                glVertex3f(float(i), 0.0,        0.0)
                glVertex3f(float(i), self.depth, 0.0)

        for i in range(0, int(math.ceil(self.depth + 1))):
            if color(i):
                glVertex3f(0,          float(i), 0.0)
                glVertex3f(self.width, float(i), 0.0)
        glEnd()

        # draw fill
        glColor4f(*self.color_fill)
        glRectf(0.0, 0.0, float(self.width), float(self.depth))

        glPopMatrix()

    def display(self, mode_2d=False):
        glCallList(self.display_list)

class PrintHead(object):
    def __init__(self):
        self.color = (43. / 255, 0., 175. / 255, 1.0)
        self.scale = 5
        self.height = 5

        self.initialized = False
        self.loaded      = True

    def init(self):
        self.display_list = compile_display_list(self.draw)
        self.initialized = True

    def draw(self):
        glPushMatrix()

        glBegin(GL_LINES)
        glColor4f(*self.color)
        for di in [-1, 1]:
            for dj in [-1, 1]:
                glVertex3f(0, 0, 0)
                glVertex3f(self.scale * di, self.scale * dj, self.height)
        glEnd()

        glPopMatrix()

    def display(self, mode_2d=False):
        glEnable(GL_LINE_SMOOTH)
        orig_linewidth = (GLfloat)()
        glGetFloatv(GL_LINE_WIDTH, orig_linewidth)
        glLineWidth(3.0)
        glCallList(self.display_list)
        glLineWidth(orig_linewidth)
        glDisable(GL_LINE_SMOOTH)

class Model(object):
    """
    Parent class for models that provides common functionality.
    """
    AXIS_X = (1, 0, 0)
    AXIS_Y = (0, 1, 0)
    AXIS_Z = (0, 0, 1)

    letter_axis_map = {
        'x': AXIS_X,
        'y': AXIS_Y,
        'z': AXIS_Z,
    }

    axis_letter_map = dict([(v, k) for k, v in letter_axis_map.items()])

    def __init__(self, offset_x=0, offset_y=0):
        self.offset_x = offset_x
        self.offset_y = offset_y

        self.init_model_attributes()

    def init_model_attributes(self):
        """
        Set/reset saved properties.
        """
        self.invalidate_bounding_box()
        self.modified = False

    def invalidate_bounding_box(self):
        self._bounding_box = None

    @property
    def bounding_box(self):
        """
        Get a bounding box for the model.
        """
        if self._bounding_box is None:
            self._bounding_box = self._calculate_bounding_box()
        return self._bounding_box

    def _calculate_bounding_box(self):
        """
        Calculate an axis-aligned box enclosing the model.
        """
        # swap rows and columns in our vertex arrays so that we can do max and
        # min on axis 1
        xyz_rows = self.vertices.reshape(-1, order='F').reshape(3, -1)
        lower_corner = xyz_rows.min(1)
        upper_corner = xyz_rows.max(1)
        box = BoundingBox(upper_corner, lower_corner)
        return box

    @property
    def width(self):
        return self.bounding_box.width

    @property
    def depth(self):
        return self.bounding_box.depth

    @property
    def height(self):
        return self.bounding_box.height

def movement_angle(src, dst, precision=0):
    x = dst[0] - src[0]
    y = dst[1] - src[1]
    angle = math.degrees(math.atan2(y, -x)) # negate x for clockwise rotation angle
    return round(angle, precision)

class GcodeModel(Model):
    """
    Model for displaying Gcode data.
    """

    color_travel = (0.6, 0.6, 0.6, 0.6)
    color_tool0 = (1.0, 0.0, 0.0, 0.6)
    color_tool1 = (0.0, 0.0, 1.0, 0.6)
    color_printed = (0.2, 0.75, 0, 0.6)
    color_current = (0.6, 0.3, 0, 0.8)
    color_current_printed = (0.1, 0.4, 0, 0.8)

    use_vbos = True
    loaded = False

    def load_data(self, model_data, callback=None):
        t_start = time.time()

        self.dims = ((model_data.xmin,model_data.xmax,model_data.width),
                     (model_data.ymin,model_data.ymax,model_data.depth),
                     (model_data.zmin,model_data.zmax,model_data.height))

        vertex_list      = []
        color_list       = []
        self.layer_stops = [0]
        arrow_list       = []
        num_layers       = len(model_data.all_layers)

        prev_pos = (0, 0, 0)
        for layer_idx, layer in enumerate(model_data.all_layers):
            for gline in layer:
                if not gline.is_move:
                    continue
                vertex_list.append(prev_pos)
                current_pos = (gline.current_x, gline.current_y, gline.current_z)
                vertex_list.append(current_pos)

                vertex_color = self.movement_color(gline)
                color_list.append(vertex_color)

                prev_pos = current_pos
                gline.gcview_end_vertex = len(vertex_list)

            self.layer_stops.append(len(vertex_list))

            if callback:
                callback(layer_idx + 1, num_layers)

        self.vertices = numpy.array(vertex_list, dtype = GLfloat)
        self.colors   = numpy.array(color_list, dtype = GLfloat).repeat(2, 0)

        self.max_layers         = len(self.layer_stops) - 1
        self.num_layers_to_draw = self.max_layers
        self.printed_until      = -1
        self.only_current       = False
        self.initialized        = False
        self.loaded             = True

        t_end = time.time()

        logging.log(logging.INFO, _('Initialized 3D visualization in %.2f seconds') % (t_end - t_start))
        logging.log(logging.INFO, _('Vertex count: %d') % len(self.vertices))

    def copy(self):
        copy = GcodeModel()
        for var in ["vertices", "colors", "max_layers", "num_layers_to_draw", "printed_until", "layer_stops", "dims"]:
            setattr(copy, var, getattr(self, var))
        copy.loaded = True
        copy.initialized = False
        return copy

    def movement_color(self, move):
        """
        Return the color to use for particular type of movement.
        """
        if move.extruding:
            if move.current_tool == 0:
                return self.color_tool0
            else:
                return self.color_tool1

        return self.color_travel

    # ------------------------------------------------------------------------
    # DRAWING
    # ------------------------------------------------------------------------

    def init(self):
        self.vertex_buffer       = numpy2vbo(self.vertices, use_vbos = self.use_vbos)
        self.vertex_color_buffer = numpy2vbo(self.colors, use_vbos = self.use_vbos) # each pair of vertices shares the color
        self.initialized = True

    def display(self, mode_2d=False):
        glPushMatrix()
        glTranslatef(self.offset_x, self.offset_y, 0)
        glEnableClientState(GL_VERTEX_ARRAY)
        glEnableClientState(GL_COLOR_ARRAY)

        self._display_movements(mode_2d)

        glDisableClientState(GL_COLOR_ARRAY)
        glDisableClientState(GL_VERTEX_ARRAY)
        glPopMatrix()

    def _display_movements(self, mode_2d=False):
        self.vertex_buffer.bind()
        has_vbo = isinstance(self.vertex_buffer, VertexBufferObject)
        if has_vbo:
            glVertexPointer(3, GL_FLOAT, 0, None)
        else:
            glVertexPointer(3, GL_FLOAT, 0, self.vertex_buffer.ptr)

        self.vertex_color_buffer.bind()
        if has_vbo:
            glColorPointer(4, GL_FLOAT, 0, None)
        else:
            glColorPointer(4, GL_FLOAT, 0, self.vertex_color_buffer.ptr)

        start = 0
        if self.num_layers_to_draw <= self.max_layers:
            end_prev_layer = self.layer_stops[self.num_layers_to_draw - 1]
        else:
            end_prev_layer = -1
        end = self.layer_stops[min(self.num_layers_to_draw, self.max_layers)]
        
        glDisableClientState(GL_COLOR_ARRAY)

        glColor4f(*self.color_printed)

        # Draw printed stuff until end or end_prev_layer
        cur_end = min(self.printed_until, end)
        if not self.only_current:
            if 0 <= end_prev_layer <= cur_end:
                glDrawArrays(GL_LINES, start, end_prev_layer)
            elif cur_end >= 0:
                glDrawArrays(GL_LINES, start, cur_end)

        glEnableClientState(GL_COLOR_ARRAY)

        # Draw nonprinted stuff until end_prev_layer
        start = max(cur_end, 0)
        if end_prev_layer >= start:
            if not self.only_current:
                glDrawArrays(GL_LINES, start, end_prev_layer - start)
            cur_end = end_prev_layer

        # Draw current layer
        if end_prev_layer >= 0:
            glDisableClientState(GL_COLOR_ARRAY)
            
            # Backup & increase line width
            orig_linewidth = (GLfloat)()
            glGetFloatv(GL_LINE_WIDTH, orig_linewidth)
            glLineWidth(2.0)
        
            glColor4f(*self.color_current_printed)
        
            if cur_end > end_prev_layer:
                glDrawArrays(GL_LINES, end_prev_layer, cur_end - end_prev_layer)

            glColor4f(*self.color_current)

            if end > cur_end:
                glDrawArrays(GL_LINES, cur_end, end - cur_end)

            # Restore line width
            glLineWidth(orig_linewidth)

            glEnableClientState(GL_COLOR_ARRAY)

        # Draw non printed stuff until end (if not ending at a given layer)
        start = max(self.printed_until, 0)
        end = end - start
        if end_prev_layer < 0 and end > 0 and not self.only_current:
            glDrawArrays(GL_LINES, start, end)

        self.vertex_buffer.unbind()
        self.vertex_color_buffer.unbind()

