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

from math import cos, sin, radians

# Python 2/3 management
# pylint: disable=E0611
# pylint: enable=E0611

from . import cairo
from .helpers import distance, normalize, point_angle, zip_letters
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

    font_size = size(surface, node.get("font-size", "12pt"))
    font_family = (
        (node.get("font-family") or "sans-serif")
        .split(",")[0].strip("\"' "))
    font_style = getattr(
        cairo, ("font_slant_%s" % node.get("font-style")).upper(),
        cairo.FONT_SLANT_NORMAL)
    font_weight = getattr(
        cairo, ("font_weight_%s" % node.get("font-weight")).upper(),
        cairo.FONT_WEIGHT_NORMAL)
    surface.context.select_font_face(font_family, font_style, font_weight)
    surface.context.set_font_size(font_size)
    ascent, descent, _, max_x_advance, max_y_advance = (
        surface.context.font_extents())

    text_path_href = (
        node.get("{http://www.w3.org/1999/xlink}href", "") or
        node.parent.get("{http://www.w3.org/1999/xlink}href", ""))
    text_path = surface.paths.get(text_path_href.lstrip("#"))
    letter_spacing = size(surface, node.get("letter-spacing"))
    x_bearing, y_bearing, width, height = (
        surface.context.text_extents(node.text)[:4])

    x, y, dx, dy, rotate = [], [], [], [], [0]
    if "x" in node:
        x = [size(surface, i, "x")
             for i in normalize(node["x"]).strip().split(" ")]
    if "y" in node:
        y = [size(surface, i, "y")
             for i in normalize(node["y"]).strip().split(" ")]
    if "dx" in node:
        dx = [size(surface, i, "x")
              for i in normalize(node["dx"]).strip().split(" ")]
    if "dy" in node:
        dy = [size(surface, i, "y")
              for i in normalize(node["dy"]).strip().split(" ")]
    if "rotate" in node:
        rotate = [radians(float(i)) if i else 0
                  for i in normalize(node["rotate"]).strip().split(" ")]
    last_r = rotate[-1]
    letters_positions = zip_letters(x, y, dx, dy, rotate, node.text)

    text_anchor = node.get("text-anchor")
    if text_anchor == "middle":
        x_align = width / 2. + x_bearing
    elif text_anchor == "end":
        x_align = width + x_bearing
    else:
        x_align = 0

    # XXX This is a hack. The rest of the baseline alignment
    # tags of the SVG 1.1 spec (section 10.9.2) are
    # not supported. We only try to align things
    # that look like Western horizontal fonts.
    # Finally, we add a "display-anchor" attribute
    # for aligning the specific text rather than the
    # font baseline.
    # Nonetheless, there are times when one needs to align
    # text vertically, and this will at least make that
    # possible.
    if max_x_advance > 0 and max_y_advance == 0:
        display_anchor = node.get("display-anchor")
        alignment_baseline = node.get("alignment-baseline")
        if display_anchor == "middle":
            y_align = -height / 2.0 - y_bearing
        elif display_anchor == "top":
            y_align = -y_bearing
        elif display_anchor == "bottom":
            y_align = -height - y_bearing
        elif (alignment_baseline == "central" or
              alignment_baseline == "middle"):
            # XXX This is wrong--Cairo gives no reasonable access
            # to x-height information, so we use font top-to-bottom
            y_align = (ascent + descent) / 2.0 - descent
        elif (alignment_baseline == "text-before-edge" or
              alignment_baseline == "before_edge" or
              alignment_baseline == "top" or
              alignment_baseline == "text-top"):
            y_align = ascent
        elif (alignment_baseline == "text-after-edge" or
              alignment_baseline == "after_edge" or
              alignment_baseline == "bottom" or
              alignment_baseline == "text-bottom"):
            y_align = -descent
        else:
            y_align = 0

    if text_path:
        surface.stroke_and_fill = False
        surface.draw(text_path)
        surface.stroke_and_fill = True
        cairo_path = surface.context.copy_path_flat()
        surface.context.new_path()
        start_offset = size(
            surface, node.get("startOffset", 0), path_length(cairo_path))
        surface.text_path_width += start_offset
        x1, y1 = point_following_path(cairo_path, surface.text_path_width)

    if node.text:
        for [x, y, dx, dy, r], letter in letters_positions:
            if x:
                surface.cursor_d_position[0] = 0
            if y:
                surface.cursor_d_position[1] = 0
            surface.cursor_d_position[0] += dx or 0
            surface.cursor_d_position[1] += dy or 0
            extents = surface.context.text_extents(letter)[4]
            surface.context.save()
            if text_path:
                surface.text_path_width += extents + letter_spacing
                point_on_path = point_following_path(
                    cairo_path,
                    surface.text_path_width + surface.cursor_d_position[0])
                if point_on_path:
                    x2, y2 = point_on_path
                else:
                    continue
                surface.context.translate(x1, y1)
                surface.context.rotate(point_angle(x1, y1, x2, y2))
                surface.context.translate(0, surface.cursor_d_position[1])
                surface.context.move_to(0, 0)
                x1, y1 = x2, y2
            else:
                x = surface.cursor_position[0] if x is None else x
                y = surface.cursor_position[1] if y is None else y
                surface.context.move_to(x + letter_spacing, y)
                cursor_position = x + letter_spacing + extents, y
                surface.context.rel_move_to(*surface.cursor_d_position)
                surface.context.rel_move_to(-x_align, y_align)
                surface.context.rotate(last_r if r is None else r)

            surface.context.text_path(letter)
            surface.context.restore()
            if not text_path:
                surface.cursor_position = cursor_position
    else:
        x = x[0] if x else surface.cursor_position[0]
        y = y[0] if y else surface.cursor_position[1]
        dx = dx[0] if dx else 0
        dy = dy[0] if dy else 0
        surface.cursor_position = (x + dx, y + dy)
