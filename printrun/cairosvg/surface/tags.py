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
SVG tags functions.

"""

from .defs import (
    clip_path, filter_, linear_gradient, marker, mask, pattern,
    radial_gradient, use)
from .image import image
from .path import path
from .shapes import circle, ellipse, line, polygon, polyline, rect
from .svg import svg
from .text import text

TAGS = {
    "a": text,
    "circle": circle,
    "clipPath": clip_path,
    "ellipse": ellipse,
    "filter": filter_,
    "image": image,
    "line": line,
    "linearGradient": linear_gradient,
    "marker": marker,
    "mask": mask,
    "path": path,
    "pattern": pattern,
    "polyline": polyline,
    "polygon": polygon,
    "radialGradient": radial_gradient,
    "rect": rect,
    "svg": svg,
    "text": text,
    "textPath": text,
    "tspan": text,
    "use": use}
