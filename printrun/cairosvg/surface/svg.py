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
Root tag drawer.

"""

from .helpers import preserve_ratio, node_format
from .units import size


def svg(surface, node):
    """Draw a svg ``node``."""
    width, height, viewbox = node_format(surface, node)
    if viewbox:
        rect_x, rect_y = viewbox[0:2]
        node.image_width = viewbox[2]
        node.image_height = viewbox[3]
    else:
        rect_x, rect_y = 0, 0
        node.image_width = size(surface, node.get("width"), "x")
        node.image_height = size(surface, node.get("height"), "y")

    if node.parent is None:
        return

    if node.get("preserveAspectRatio", "none") != "none":
        scale_x, scale_y, translate_x, translate_y = \
            preserve_ratio(surface, node)
        rect_width, rect_height = width, height
    else:
        scale_x, scale_y, translate_x, translate_y = (1, 1, 0, 0)
        rect_width, rect_height = node.image_width, node.image_height
    surface.context.translate(*surface.context.get_current_point())
    surface.context.rectangle(rect_x, rect_y, rect_width, rect_height)
    surface.context.clip()
    surface.context.scale(scale_x, scale_y)
    surface.context.translate(translate_x, translate_y)
