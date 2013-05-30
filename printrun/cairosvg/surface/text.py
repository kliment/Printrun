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
Text drawers.

"""

import cairo
from math import cos, sin

# Python 2/3 management
# pylint: disable=E0611
try:
    from itertools import zip_longest
except ImportError:
    from itertools import izip_longest as zip_longest
# pylint: enable=E0611

from .colors import color
from .helpers import distance, normalize, point_angle
from .units import size


def path_length(path):
    """Get the length of ``path``."""
    total_length = 0
    for item in path:
        if item[0] == cairo.PATH_MOVE_TO:
            old_point = item[1]
        elif item[0] == cairo.PATH_LINE_TO:
            new_point = item[1]
            length = distance(
                old_point[0], old_point[1], new_point[0], new_point[1])
            total_length += length
            old_point = new_point
    return total_length


def point_following_path(path, width):
    """Get the point at ``width`` distance on ``path``."""
    total_length = 0
    for item in path:
        if item[0] == cairo.PATH_MOVE_TO:
            old_point = item[1]
        elif item[0] == cairo.PATH_LINE_TO:
            new_point = item[1]
            length = distance(
                old_point[0], old_point[1], new_point[0], new_point[1])
            total_length += length
            if total_length < width:
                old_point = new_point
            else:
                length -= total_length - width
                angle = point_angle(
                    old_point[0], old_point[1], new_point[0], new_point[1])
                x = cos(angle) * length + old_point[0]
                y = sin(angle) * length + old_point[1]
                return x, y


def text(surface, node):
    """Draw a text ``node``."""
    # Set black as default text color
    if not node.get("fill"):
        node["fill"] = "#000000"

    # TODO: find a better way to manage white spaces in text nodes
    node.text = (node.text or "").lstrip()
    node.text = node.text.rstrip() + " "

    # TODO: manage font variant
    font_size = size(surface, node.get("font-size", "12pt"))
    font_family = (node.get("font-family") or "sans-serif").split(",")[0]
    font_style = getattr(
        cairo, ("font_slant_%s" % node.get("font-style")).upper(),
        cairo.FONT_SLANT_NORMAL)
    font_weight = getattr(
        cairo, ("font_weight_%s" % node.get("font-weight")).upper(),
        cairo.FONT_WEIGHT_NORMAL)
    surface.context.select_font_face(font_family, font_style, font_weight)
    surface.context.set_font_size(font_size)

    text_extents = surface.context.text_extents(node.text)
    x_bearing = text_extents[0]
    width = text_extents[2]
    x, y = size(surface, node.get("x"), "x"), size(surface, node.get("y"), "y")
    text_anchor = node.get("text-anchor")
    if text_anchor == "middle":
        x -= width / 2. + x_bearing
    elif text_anchor == "end":
        x -= width + x_bearing

    surface.context.move_to(x, y)
    surface.context.text_path(node.text)

    # Remember the absolute cursor position
    surface.cursor_position = surface.context.get_current_point()


def text_path(surface, node):
    """Draw text on a path."""
    surface.context.save()
    if "url(#" not in (node.get("fill") or ""):
        surface.context.set_source_rgba(*color(node.get("fill")))

    id_path = node.get("{http://www.w3.org/1999/xlink}href", "")
    if not id_path.startswith("#"):
        return
    id_path = id_path[1:]

    if id_path in surface.paths:
        path = surface.paths.get(id_path)
    else:
        return

    surface.draw(path, False)
    cairo_path = surface.context.copy_path_flat()
    surface.context.new_path()

    start_offset = size(
        surface, node.get("startOffset", 0), path_length(cairo_path))
    surface.total_width += start_offset

    x, y = point_following_path(cairo_path, surface.total_width)
    string = (node.text or "").strip(" \n")
    letter_spacing = size(surface, node.get("letter-spacing"))

    for letter in string:
        surface.total_width += (
            surface.context.text_extents(letter)[4] + letter_spacing)
        point_on_path = point_following_path(cairo_path, surface.total_width)
        if point_on_path:
            x2, y2 = point_on_path
        else:
            continue
        angle = point_angle(x, y, x2, y2)
        surface.context.save()
        surface.context.translate(x, y)
        surface.context.rotate(angle)
        surface.context.translate(0, size(surface, node.get("y"), "y"))
        surface.context.move_to(0, 0)
        surface.context.show_text(letter)
        surface.context.restore()
        x, y = x2, y2
    surface.context.restore()

    # Remember the relative cursor position
    surface.cursor_position = \
        size(surface, node.get("x"), "x"), size(surface, node.get("y"), "y")


def tspan(surface, node):
    """Draw a tspan ``node``."""
    x, y = [[i] for i in surface.cursor_position]
    if "x" in node:
        x = [size(surface, i, "x")
             for i in normalize(node["x"]).strip().split(" ")]
    if "y" in node:
        y = [size(surface, i, "y")
             for i in normalize(node["y"]).strip().split(" ")]

    string = (node.text or "").strip()
    if not string:
        return
    fill = node.get("fill")
    positions = list(zip_longest(x, y))
    letters_positions = list(zip(positions, string))
    letters_positions = letters_positions[:-1] + [
        (letters_positions[-1][0], string[len(letters_positions) - 1:])]

    for (x, y), letters in letters_positions:
        if x == None:
            x = surface.cursor_position[0]
        if y == None:
            y = surface.cursor_position[1]
        node["x"] = str(x + size(surface, node.get("dx"), "x"))
        node["y"] = str(y + size(surface, node.get("dy"), "y"))
        node["fill"] = fill
        node.text = letters
        if node.parent.tag == "text":
            text(surface, node)
        else:
            node["x"] = str(x + size(surface, node.get("dx"), "x"))
            node["y"] = str(y + size(surface, node.get("dy"), "y"))
            text_path(surface, node)
            if node.parent.children[-1] == node:
                surface.total_width = 0
