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


def svg(surface, node):
    """Draw a svg ``node``."""
    if node.get("preserveAspectRatio", "none") != "none":
        width, height, viewbox = node_format(surface, node)
        node.image_width, node.image_height = viewbox[2:]
        scale_x, scale_y, translate_x, translate_y = \
            preserve_ratio(surface, node)
        surface.context.rectangle(0, 0, width, height)
        surface.context.clip()
        surface.context.translate(*surface.context.get_current_point())
        surface.context.scale(scale_x, scale_y)
        surface.context.translate(translate_x, translate_y)
