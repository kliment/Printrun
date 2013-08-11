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
Surface helpers.

"""

from math import cos, sin, tan, atan2, radians

from . import cairo
from .units import size

# Python 2/3 management
# pylint: disable=C0103
try:
    Error = cairo.Error
except AttributeError:
    Error = SystemError
# pylint: enable=C0103


class PointError(Exception):
    """Exception raised when parsing a point fails."""


def distance(x1, y1, x2, y2):
    """Get the distance between two points."""
    return ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5


def paint(value):
    """Extract from value an uri and a color.

    See http://www.w3.org/TR/SVG/painting.html#SpecifyingPaint

    """
    if not value:
        return None, None

    value = value.strip()

    if value.startswith("url"):
        source = urls(value.split(")")[0])[0][1:]
        color = value.split(")", 1)[-1].strip() or None
    else:
        source = None
        color = value.strip() or None

    return (source, color)


def node_format(surface, node):
    """Return ``(width, height, viewbox)`` of ``node``."""
    width = size(surface, node.get("width"), "x")
    height = size(surface, node.get("height"), "y")
    viewbox = node.get("viewBox")
    if viewbox:
        viewbox = tuple(float(position) for position in viewbox.split())
        width = width or viewbox[2]
        height = height or viewbox[3]
    return width, height, viewbox


def normalize(string=None):
    """Normalize a string corresponding to an array of various values."""
    string = string.replace("-", " -")
    string = string.replace(",", " ")

    while "  " in string:
        string = string.replace("  ", " ")

    string = string.replace("e -", "e-")
    string = string.replace("E -", "E-")

    values = string.split(" ")
    string = ""
    for value in values:
        if value.count(".") > 1:
            numbers = value.split(".")
            string += "%s.%s " % (numbers.pop(0), numbers.pop(0))
            string += ".%s " % " .".join(numbers)
        else:
            string += value + " "

    return string.strip()


def point(surface, string=None):
    """Return ``(x, y, trailing_text)`` from ``string``."""
    if not string:
        return (0, 0, "")

    try:
        x, y, string = (string.strip() + " ").split(" ", 2)
    except ValueError:
        raise PointError("The point cannot be found in string %s" % string)

    return size(surface, x, "x"), size(surface, y, "y"), string


def point_angle(cx, cy, px, py):
    """Return angle between x axis and point knowing given center."""
    return atan2(py - cy, px - cx)


def preserve_ratio(surface, node):
    """Manage the ratio preservation."""
    if node.tag == "marker":
        scale_x = size(surface, node.get("markerWidth", "3"), "x")
        scale_y = size(surface, node.get("markerHeight", "3"), "y")
        translate_x = -size(surface, node.get("refX"))
        translate_y = -size(surface, node.get("refY"))
    elif node.tag in ("svg", "image"):
        width, height, _ = node_format(surface, node)
        scale_x = width / node.image_width
        scale_y = height / node.image_height

        align = node.get("preserveAspectRatio", "xMidYMid").split(" ")[0]
        if align == "none":
            return scale_x, scale_y, 0, 0
        else:
            mos_properties = node.get("preserveAspectRatio", "").split()
            meet_or_slice = (
                mos_properties[1] if len(mos_properties) > 1 else None)
            if meet_or_slice == "slice":
                scale_value = max(scale_x, scale_y)
            else:
                scale_value = min(scale_x, scale_y)
            scale_x = scale_y = scale_value

            x_position = align[1:4].lower()
            y_position = align[5:].lower()

            if x_position == "min":
                translate_x = 0

            if y_position == "min":
                translate_y = 0

            if x_position == "mid":
                translate_x = (width / scale_x - node.image_width) / 2.

            if y_position == "mid":
                translate_y = (height / scale_y - node.image_height) / 2.

            if x_position == "max":
                translate_x = width / scale_x - node.image_width

            if y_position == "max":
                translate_y = height / scale_y - node.image_height

    return scale_x, scale_y, translate_x, translate_y


def quadratic_points(x1, y1, x2, y2, x3, y3):
    """Return the quadratic points to create quadratic curves."""
    xq1 = x2 * 2 / 3 + x1 / 3
    yq1 = y2 * 2 / 3 + y1 / 3
    xq2 = x2 * 2 / 3 + x3 / 3
    yq2 = y2 * 2 / 3 + y3 / 3
    return xq1, yq1, xq2, yq2, x3, y3


def rotate(x, y, angle):
    """Rotate a point of an angle around the origin point."""
    return x * cos(angle) - y * sin(angle), y * cos(angle) + x * sin(angle)


def transform(surface, string):
    """Update ``surface`` matrix according to transformation ``string``."""
    if not string:
        return

    transformations = string.split(")")
    matrix = cairo.Matrix()
    for transformation in transformations:
        for ttype in ("scale", "translate", "matrix", "rotate", "skewX",
                      "skewY"):
            if ttype in transformation:
                transformation = transformation.replace(ttype, "")
                transformation = transformation.replace("(", "")
                transformation = normalize(transformation).strip() + " "
                values = []
                while transformation:
                    value, transformation = transformation.split(" ", 1)
                    # TODO: manage the x/y sizes here
                    values.append(size(surface, value))
                if ttype == "matrix":
                    matrix = cairo.Matrix(*values).multiply(matrix)
                elif ttype == "rotate":
                    angle = radians(float(values.pop(0)))
                    x, y = values or (0, 0)
                    matrix.translate(x, y)
                    matrix.rotate(angle)
                    matrix.translate(-x, -y)
                elif ttype == "skewX":
                    tangent = tan(radians(float(values[0])))
                    matrix = \
                        cairo.Matrix(1, 0, tangent, 1, 0, 0).multiply(matrix)
                elif ttype == "skewY":
                    tangent = tan(radians(float(values[0])))
                    matrix = \
                        cairo.Matrix(1, tangent, 0, 1, 0, 0).multiply(matrix)
                elif ttype == "translate":
                    if len(values) == 1:
                        values += (0,)
                    matrix.translate(*values)
                elif ttype == "scale":
                    if len(values) == 1:
                        values = 2 * values
                    matrix.scale(*values)
    apply_matrix_transform(surface, matrix)


def apply_matrix_transform(surface, matrix):
    try:
        matrix.invert()
    except Error:
        # Matrix not invertible, clip the surface to an empty path
        active_path = surface.context.copy_path()
        surface.context.new_path()
        surface.context.clip()
        surface.context.append_path(active_path)
    else:
        matrix.invert()
        surface.context.transform(matrix)


def urls(string):
    """Parse a comma-separated list of url() strings."""
    if not string:
        return []

    string = string.strip()
    if string.startswith("url"):
        string = string[3:]
    return [
        link.strip("() ") for link in string.rsplit(")")[0].split(",")
        if link.strip("() ")]


def rect(string):
    """Parse the rect value of a clip."""
    if not string:
        return []
    string = string.strip()
    if string.startswith("rect"):
        return string[4:].strip('() ').split(',')
    else:
        return []
