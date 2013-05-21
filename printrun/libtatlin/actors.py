# -*- coding: utf-8 -*-
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


from __future__ import division

import math
import numpy
import logging
import time

from OpenGL.GL import *
from OpenGL.GLE import *
from OpenGL.arrays.vbo import VBO

import vector
from gcodeparser import Movement


def compile_display_list(func, *options):
    display_list = glGenLists(1)
    glNewList(display_list, GL_COMPILE)
    func(*options)
    glEndList()
    return display_list

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

    def __init__(self, width, depth):
        self.width = width
        self.depth = depth

        self.color_grads_minor  = (0xaf / 255, 0xdf / 255, 0x5f / 255, 0.1)
        self.color_grads_interm = (0xaf / 255, 0xdf / 255, 0x5f / 255, 0.2)
        self.color_grads_major  = (0xaf / 255, 0xdf / 255, 0x5f / 255, 0.33)
        self.color_fill         = (0xaf / 255, 0xdf / 255, 0x5f / 255, 0.05)

        self.initialized = False

    def init(self):
        self.display_list = compile_display_list(self.draw)
        self.initialized = True

    def draw(self):
        glPushMatrix()

        glTranslate(-self.width / 2, -self.depth / 2, 0)

        def color(i):
            if i % self.graduations_major == 0:
                glColor(*self.color_grads_major)
            elif i % (self.graduations_major / 2) == 0:
                glColor(*self.color_grads_interm)
            else:
                glColor(*self.color_grads_minor)

        # draw the grid
        glBegin(GL_LINES)
        for i in range(0, self.width + 1):
            color(i)
            glVertex3f(float(i), 0.0,        0.0)
            glVertex3f(float(i), self.depth, 0.0)

        for i in range(0, self.depth + 1):
            color(i)
            glVertex3f(0,          float(i), 0.0)
            glVertex3f(self.width, float(i), 0.0)
        glEnd()

        # draw fill
        glColor(*self.color_fill)
        glRectf(0.0, 0.0, float(self.width), float(self.depth))

        glPopMatrix()

    def display(self, mode_2d=False):
        glCallList(self.display_list)


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


class GcodeModel(Model):
    """
    Model for displaying Gcode data.
    """
    # vertices for arrow to display the direction of movement
    arrow = numpy.require([
        [0.0, 0.0, 0.0],
        [0.4, -0.1, 0.0],
        [0.4, 0.1, 0.0],
    ], 'f')

    def load_data(self, model_data, callback=None):
        t_start = time.time()

        vertex_list      = []
        color_list       = []
        self.layer_stops = [0]
        arrow_list       = []
        num_layers       = len(model_data)

        for layer_idx, layer in enumerate(model_data):
            for movement in layer:
                vertex_list.append(movement.src)
                vertex_list.append(movement.dst)

                arrow = self.arrow
                # position the arrow with respect to movement
                arrow = vector.rotate(arrow, movement.angle(), 0.0, 0.0, 1.0)
                arrow_list.extend(arrow)

                vertex_color = self.movement_color(movement)
                color_list.append(vertex_color)

            self.layer_stops.append(len(vertex_list))

            if callback:
                callback(layer_idx + 1, num_layers)

        self.vertices = numpy.array(vertex_list, 'f')
        self.colors   = numpy.array(color_list,  'f')
        self.arrows   = numpy.array(arrow_list,  'f')

        # by translating the arrow vertices outside of the loop, we achieve a
        # significant performance gain thanks to numpy. it would be really nice
        # if we could rotate in a similar fashion...
        self.arrows = self.arrows + self.vertices[1::2].repeat(3, 0)

        # for every pair of vertices of the model, there are 3 vertices for the arrow
        assert len(self.arrows) == ((len(self.vertices) // 2) * 3), \
            'The 2:3 ratio of model vertices to arrow vertices does not hold.'

        self.max_layers         = len(self.layer_stops) - 1
        self.num_layers_to_draw = self.max_layers
        self.arrows_enabled     = True
        self.initialized        = False

        t_end = time.time()

        logging.info('Initialized Gcode model in %.2f seconds' % (t_end - t_start))
        logging.info('Vertex count: %d' % len(self.vertices))

    def movement_color(self, move):
        """
        Return the color to use for particular type of movement.
        """
        # default movement color is gray
        color = [0.6, 0.6, 0.6, 0.6]

        extruder_on = (move.flags & Movement.FLAG_EXTRUDER_ON or
                       move.delta_e > 0)
        outer_perimeter = (move.flags & Movement.FLAG_PERIMETER and
                           move.flags & Movement.FLAG_PERIMETER_OUTER)

        if extruder_on and outer_perimeter:
            color = [0.0, 0.875, 0.875, 0.6] # cyan
        elif extruder_on and move.flags & Movement.FLAG_PERIMETER:
            color = [0.0, 1.0, 0.0, 0.6] # green
        elif extruder_on and move.flags & Movement.FLAG_LOOP:
            color = [1.0, 0.875, 0.0, 0.6] # yellow
        elif extruder_on:
            color = [1.0, 0.0, 0.0, 0.6] # red

        return color

    # ------------------------------------------------------------------------
    # DRAWING
    # ------------------------------------------------------------------------

    def init(self):
        self.vertex_buffer       = VBO(self.vertices, 'GL_STATIC_DRAW')
        self.vertex_color_buffer = VBO(self.colors.repeat(2, 0), 'GL_STATIC_DRAW') # each pair of vertices shares the color

        if self.arrows_enabled:
            self.arrow_buffer       = VBO(self.arrows, 'GL_STATIC_DRAW')
            self.arrow_color_buffer = VBO(self.colors.repeat(3, 0), 'GL_STATIC_DRAW') # each triplet of vertices shares the color

        self.initialized = True

    def display(self, mode_2d=False):
        glPushMatrix()
        glTranslate(self.offset_x, self.offset_y, 0)
        glEnableClientState(GL_VERTEX_ARRAY)
        glEnableClientState(GL_COLOR_ARRAY)

        self._display_movements(mode_2d)

        if self.arrows_enabled:
            self._display_arrows()

        glDisableClientState(GL_COLOR_ARRAY)
        glDisableClientState(GL_VERTEX_ARRAY)
        glPopMatrix()

    def _display_movements(self, mode_2d=False):
        self.vertex_buffer.bind()
        glVertexPointer(3, GL_FLOAT, 0, None)

        self.vertex_color_buffer.bind()
        glColorPointer(4, GL_FLOAT, 0, None)

        if mode_2d:
            glScale(1.0, 1.0, 0.0) # discard z coordinates
            start = self.layer_stops[self.num_layers_to_draw - 1]
            end   = self.layer_stops[self.num_layers_to_draw] - start
        else: # 3d
            start = 0
            end   = self.layer_stops[self.num_layers_to_draw]

        glDrawArrays(GL_LINES, start, end)

        self.vertex_buffer.unbind()
        self.vertex_color_buffer.unbind()

    def _display_arrows(self):
        self.arrow_buffer.bind()
        glVertexPointer(3, GL_FLOAT, 0, None)

        self.arrow_color_buffer.bind()
        glColorPointer(4, GL_FLOAT, 0, None)

        start = (self.layer_stops[self.num_layers_to_draw - 1] // 2) * 3
        end   = (self.layer_stops[self.num_layers_to_draw] // 2) * 3

        glDrawArrays(GL_TRIANGLES, start, end - start)

        self.arrow_buffer.unbind()
        self.arrow_color_buffer.unbind()


class StlModel(Model):
    """
    Model for displaying and manipulating STL data.
    """
    def load_data(self, model_data, callback=None):
        t_start = time.time()

        vertices, normals = model_data
        # convert python lists to numpy arrays for constructing vbos
        self.vertices = numpy.require(vertices, 'f')
        self.normals  = numpy.require(normals, 'f')

        self.scaling_factor = 1.0
        self.rotation_angle = {
            self.AXIS_X: 0.0,
            self.AXIS_Y: 0.0,
            self.AXIS_Z: 0.0,
        }

        self.mat_specular   = (1.0, 1.0, 1.0, 1.0)
        self.mat_shininess  = 50.0
        self.light_position = (20.0, 20.0, 20.0)

        self.initialized = False

        t_end = time.time()

        logging.info('Initialized STL model in %.2f seconds' % (t_end - t_start))
        logging.info('Vertex count: %d' % len(self.vertices))

    def normal_data_empty(self):
        """
        Return true if the model has no normal data.
        """
        empty = (self.normals.max() == 0 and self.normals.min() == 0)
        return empty

    def calculate_normals(self):
        """
        Calculate surface normals for model vertices.
        """
        a = self.vertices[0::3] - self.vertices[1::3]
        b = self.vertices[1::3] - self.vertices[2::3]
        cross = numpy.cross(a, b)

        # normalize the cross product
        magnitudes = numpy.apply_along_axis(numpy.linalg.norm, 1, cross).reshape(-1, 1)
        normals = cross / magnitudes

        # each of 3 facet vertices shares the same normal
        normals = normals.repeat(3, 0)
        return normals

    # ------------------------------------------------------------------------
    # DRAWING
    # ------------------------------------------------------------------------

    def init(self):
        """
        Create vertex buffer objects (VBOs).
        """
        self.vertex_buffer = VBO(self.vertices, 'GL_STATIC_DRAW')

        if self.normal_data_empty():
            logging.info('STL model has no normal data')
            self.normals = self.calculate_normals()

        self.normal_buffer = VBO(self.normals, 'GL_STATIC_DRAW')
        self.initialized = True

    def draw_facets(self):
        glPushMatrix()

        glEnable(GL_LIGHT0)
        glEnable(GL_LIGHT1)
        glShadeModel(GL_SMOOTH)

        # material properties (white plastic)
        glMaterial(GL_FRONT, GL_AMBIENT, (0.0, 0.0, 0.0, 1.0))
        glMaterial(GL_FRONT, GL_DIFFUSE, (0.55, 0.55, 0.55, 1.0))
        glMaterial(GL_FRONT, GL_SPECULAR, (0.7, 0.7, 0.7, 1.0))
        glMaterial(GL_FRONT, GL_SHININESS, 32.0)

        # lights properties
        glLight(GL_LIGHT0, GL_AMBIENT, (0.3, 0.3, 0.3, 1.0))
        glLight(GL_LIGHT0, GL_DIFFUSE, (0.3, 0.3, 0.3, 1.0))
        glLight(GL_LIGHT1, GL_DIFFUSE, (0.3, 0.3, 0.3, 1.0))

        # lights position
        glLightfv(GL_LIGHT0, GL_POSITION, self.light_position)
        glLightfv(GL_LIGHT1, GL_POSITION, (-20.0, -20.0, 20.0))

        glColor(1.0, 1.0, 1.0)

        ### VBO stuff

        self.vertex_buffer.bind()
        glVertexPointer(3, GL_FLOAT, 0, None)
        self.normal_buffer.bind()
        glNormalPointer(GL_FLOAT, 0, None)

        glEnableClientState(GL_VERTEX_ARRAY)
        glEnableClientState(GL_NORMAL_ARRAY)

        glDrawArrays(GL_TRIANGLES, 0, len(self.vertices))

        glDisableClientState(GL_NORMAL_ARRAY)
        glDisableClientState(GL_VERTEX_ARRAY)
        self.normal_buffer.unbind()
        self.vertex_buffer.unbind()

        ### end VBO stuff

        glDisable(GL_LIGHT1)
        glDisable(GL_LIGHT0)

        glPopMatrix()

    def display(self, mode_2d=False):
        glEnable(GL_LIGHTING)
        self.draw_facets()
        glDisable(GL_LIGHTING)

    # ------------------------------------------------------------------------
    # TRANSFORMATIONS
    # ------------------------------------------------------------------------

    def scale(self, factor):
        if factor != self.scaling_factor:
            logging.info('actually scaling vertices')
            self.vertices *= (factor / self.scaling_factor)
            self.scaling_factor = factor
            self.invalidate_bounding_box()
            self.modified = True

    def translate(self, x, y, z):
        self.vertices = vector.translate(self.vertices, x, y, z)
        self.invalidate_bounding_box()
        self.modified = True

    def rotate_rel(self, angle, axis):
        logging.info('rotating vertices by a relative angle of '
                     '%.2f degrees along the %s axis' %
                     (angle, self.axis_letter_map[axis]))

        angle = angle % 360
        self.vertices = vector.rotate(self.vertices, angle, *axis)
        self.rotation_angle[axis] += angle
        self.invalidate_bounding_box()
        self.modified = True

    def rotate_abs(self, angle, axis):
        angle = angle % 360
        if self.rotation_angle[axis] == angle:
            return

        logging.info('rotating vertices by an absolute angle of '
                     '%.2f degrees along the %s axis' %
                     (angle, self.axis_letter_map[axis]))
        final_matrix = vector.identity_matrix()

        # modify matrix to rotate to initial position
        for v in [self.AXIS_Z, self.AXIS_Y, self.AXIS_X]:
            matrix = vector.rotation_matrix(-self.rotation_angle[v], *v)
            final_matrix = final_matrix.dot(matrix)

        # change the angle
        self.rotation_angle[axis] = angle

        # modify matrix to rotate to new position
        for v in [self.AXIS_X, self.AXIS_Y, self.AXIS_Z]:
            matrix = vector.rotation_matrix(self.rotation_angle[v], *v)
            final_matrix = final_matrix.dot(matrix)

        self.vertices = self.vertices.dot(final_matrix)
        self.invalidate_bounding_box()
        self.modified = True

