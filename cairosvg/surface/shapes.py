# -*- coding: utf-8 -*-
# This file is part of CairoSVG
# Copyright © 2010-2012 Kozea
#
# This library is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with CairoSVG.  If not, see <http://www.gnu.org/licenses/>.

"""
Shapes drawers.

"""

from math import pi

from .helpers import normalize, point, size


def circle(surface, node):
    """Draw a circle ``node`` on ``surface``."""
    r = size(surface, node.get("r"))
    if not r:
        return
    surface.context.new_sub_path()
    surface.context.arc(
        size(surface, node.get("x"), "x") + size(surface, node.get("cx"), "x"),
        size(surface, node.get("y"), "y") + size(surface, node.get("cy"), "y"),
        r, 0, 2 * pi)


def ellipse(surface, node):
    """Draw an ellipse ``node`` on ``surface``."""
    rx = size(surface, node.get("rx"), "x")
    ry = size(surface, node.get("ry"), "y")
    if not rx or not ry:
        return
    ratio = ry / rx
    surface.context.new_sub_path()
    surface.context.save()
    surface.context.scale(1, ratio)
    surface.context.arc(
        size(surface, node.get("x"), "x") + size(surface, node.get("cx"), "x"),
        (size(surface, node.get("y"), "y") +
         size(surface, node.get("cy"), "y")) / ratio,
        size(surface, node.get("rx"), "x"), 0, 2 * pi)
    surface.context.restore()


def line(surface, node):
    """Draw a line ``node``."""
    x1, y1, x2, y2 = tuple(
        size(surface, node.get(position), position[0])
        for position in ("x1", "y1", "x2", "y2"))
    surface.context.move_to(x1, y1)
    surface.context.line_to(x2, y2)


def polygon(surface, node):
    """Draw a polygon ``node`` on ``surface``."""
    polyline(surface, node)
    surface.context.close_path()


def polyline(surface, node):
    """Draw a polyline ``node``."""
    points = normalize(node.get("points"))
    if points:
        x, y, points = point(surface, points)
        surface.context.move_to(x, y)
        while points:
            x, y, points = point(surface, points)
            surface.context.line_to(x, y)


def rect(surface, node):
    """Draw a rect ``node`` on ``surface``."""
    # TODO: handle ry
    x, y = size(surface, node.get("x"), "x"), size(surface, node.get("y"), "y")
    width = size(surface, node.get("width"), "x")
    height = size(surface, node.get("height"), "y")
    if size(surface, node.get("rx"), "x") == 0:
        surface.context.rectangle(x, y, width, height)
    else:
        r = size(surface, node.get("rx"), "x")
        a, b, c, d = x, width + x, y, height + y
        if r > width - r:
            r = width / 2
        surface.context.move_to(x, y + height / 2)
        surface.context.arc(a + r, c + r, r, 2 * pi / 2, 3 * pi / 2)
        surface.context.arc(b - r, c + r, r, 3 * pi / 2, 0 * pi / 2)
        surface.context.arc(b - r, d - r, r, 0 * pi / 2, 1 * pi / 2)
        surface.context.arc(a + r, d - r, r, 1 * pi / 2, 2 * pi / 2)
        surface.context.close_path()
