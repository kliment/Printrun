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
Cairo surface creators.

"""

import io
try:
    import cairocffi as cairo
except ImportError:
    import cairo  # pycairo

from ..parser import Tree
from .colors import color
from .defs import (
    apply_filter_after, apply_filter_before, gradient_or_pattern, parse_def,
    paint_mask)
from .helpers import (
    node_format, transform, normalize, paint, urls, apply_matrix_transform,
    PointError, rect)
from .path import PATH_TAGS
from .tags import TAGS
from .units import size
from . import units


class Surface(object):
    """Abstract base class for CairoSVG surfaces.

    The ``width`` and ``height`` attributes are in device units (pixels for
    PNG, else points).

    The ``context_width`` and ``context_height`` attributes are in user units
    (i.e. in pixels), they represent the size of the active viewport.

    """

    # Subclasses must either define this or override _create_surface()
    surface_class = None

    @classmethod
    def convert(cls, bytestring=None, **kwargs):
        """Convert a SVG document to the format for this class.

        Specify the input by passing one of these:

        :param bytestring: The SVG source as a byte-string.
        :param file_obj: A file-like object.
        :param url: A filename.

        And the output with:

        :param write_to: The filename of file-like object where to write the
                         output. If None or not provided, return a byte string.

        Only ``source`` can be passed as a positional argument, other
        parameters are keyword-only.

        """
        dpi = kwargs.pop('dpi', 96)
        write_to = kwargs.pop('write_to', None)
        kwargs['bytestring'] = bytestring
        tree = Tree(**kwargs)
        if write_to is None:
            output = io.BytesIO()
        else:
            output = write_to
        cls(tree, output, dpi).finish()
        if write_to is None:
            return output.getvalue()

    def __init__(self, tree, output, dpi, parent_surface=None):
        """Create the surface from a filename or a file-like object.

        The rendered content is written to ``output`` which can be a filename,
        a file-like object, ``None`` (render in memory but do not write
        anything) or the built-in ``bytes`` as a marker.

        Call the ``.finish()`` method to make sure that the output is
        actually written.

        """
        self.cairo = None
        self.context_width, self.context_height = None, None
        self.cursor_position = 0, 0
        self.total_width = 0
        self.tree_cache = {(tree.url, tree["id"]): tree}
        if parent_surface:
            self.markers = parent_surface.markers
            self.gradients = parent_surface.gradients
            self.patterns = parent_surface.patterns
            self.masks = parent_surface.masks
            self.paths = parent_surface.paths
            self.filters = parent_surface.filters
        else:
            self.markers = {}
            self.gradients = {}
            self.patterns = {}
            self.masks = {}
            self.paths = {}
            self.filters = {}
        self.page_sizes = []
        self._old_parent_node = self.parent_node = None
        self.output = output
        self.dpi = dpi
        self.font_size = size(self, "12pt")
        width, height, viewbox = node_format(self, tree)
        # Actual surface dimensions: may be rounded on raster surfaces types
        self.cairo, self.width, self.height = self._create_surface(
            width * self.device_units_per_user_units,
            height * self.device_units_per_user_units)
        self.page_sizes.append((self.width, self.height))
        self.context = cairo.Context(self.cairo)
        # We must scale the context as the surface size is using physical units
        self.context.scale(
            self.device_units_per_user_units, self.device_units_per_user_units)
        # Initial, non-rounded dimensions
        self.set_context_size(width, height, viewbox)
        self.context.move_to(0, 0)
        self.draw_root(tree)

    @property
    def points_per_pixel(self):
        """Surface resolution."""
        return 1 / (self.dpi * units.UNITS["pt"])

    @property
    def device_units_per_user_units(self):
        """Ratio between Cairo device units and user units.

        Device units are points for everything but PNG, and pixels for
        PNG. User units are pixels.

        """
        return self.points_per_pixel

    def _create_surface(self, width, height):
        """Create and return ``(cairo_surface, width, height)``."""
        # self.surface_class should not be None when called here
        # pylint: disable=E1102
        cairo_surface = self.surface_class(self.output, width, height)
        # pylint: enable=E1102
        return cairo_surface, width, height

    def set_context_size(self, width, height, viewbox):
        """Set the Cairo context size, set the SVG viewport size."""
        if viewbox:
            x, y, x_size, y_size = viewbox
            self.context_width, self.context_height = x_size, y_size
            x_ratio, y_ratio = width / x_size, height / y_size
            matrix = cairo.Matrix()
            if x_ratio > y_ratio:
                matrix.translate((width - x_size * y_ratio) / 2, 0)
                matrix.scale(y_ratio, y_ratio)
                matrix.translate(-x, -y / y_ratio * x_ratio)
            elif x_ratio < y_ratio:
                matrix.translate(0, (height - y_size * x_ratio) / 2)
                matrix.scale(x_ratio, x_ratio)
                matrix.translate(-x / x_ratio * y_ratio, -y)
            else:
                matrix.scale(x_ratio, y_ratio)
                matrix.translate(-x, -y)
            apply_matrix_transform(self, matrix)
        else:
            self.context_width, self.context_height = width, height

    def finish(self):
        """Read the surface content."""
        self.cairo.finish()

    def draw_root(self, node):
        """Draw the root ``node``."""
        self.draw(node)

    def draw(self, node, stroke_and_fill=True):
        """Draw ``node`` and its children."""
        old_font_size = self.font_size
        self.font_size = size(self, node.get("font-size", "12pt"))

        # Do not draw defs
        if node.tag == "defs":
            for child in node.children:
                parse_def(self, child)
            return

        # Do not draw elements with width or height of 0
        if (("width" in node and size(self, node["width"]) == 0) or
           ("height" in node and size(self, node["height"]) == 0)):
            return

        node.tangents = [None]
        node.pending_markers = []

        self._old_parent_node = self.parent_node
        self.parent_node = node

        self.context.save()
        # Transform the context according to the ``transform`` attribute
        transform(self, node.get("transform"))

        masks = urls(node.get("mask"))
        mask = masks[0][1:] if masks else None
        opacity = float(node.get("opacity", 1))
        if mask or opacity < 1:
            self.context.push_group()

        self.context.move_to(
            size(self, node.get("x"), "x"),
            size(self, node.get("y"), "y"))

        if node.tag in PATH_TAGS:
            # Set 1 as default stroke-width
            if not node.get("stroke-width"):
                node["stroke-width"] = "1"

        # Set node's drawing informations if the ``node.tag`` method exists
        line_cap = node.get("stroke-linecap")
        if line_cap == "square":
            self.context.set_line_cap(cairo.LINE_CAP_SQUARE)
        if line_cap == "round":
            self.context.set_line_cap(cairo.LINE_CAP_ROUND)

        join_cap = node.get("stroke-linejoin")
        if join_cap == "round":
            self.context.set_line_join(cairo.LINE_JOIN_ROUND)
        if join_cap == "bevel":
            self.context.set_line_join(cairo.LINE_JOIN_BEVEL)

        dash_array = normalize(node.get("stroke-dasharray", "")).split()
        if dash_array:
            dashes = [size(self, dash) for dash in dash_array]
            if sum(dashes):
                offset = size(self, node.get("stroke-dashoffset"))
                self.context.set_dash(dashes, offset)

        miter_limit = float(node.get("stroke-miterlimit", 4))
        self.context.set_miter_limit(miter_limit)

        # Clip
        rect_values = rect(node.get("clip"))
        if len(rect_values) == 4:
            top = float(size(self, rect_values[0], "y"))
            right = float(size(self, rect_values[1], "x"))
            bottom = float(size(self, rect_values[2], "y"))
            left = float(size(self, rect_values[3], "x"))
            x = float(size(self, node.get("x"), "x"))
            y = float(size(self, node.get("y"), "y"))
            width = float(size(self, node.get("width"), "x"))
            height = float(size(self, node.get("height"), "y"))
            self.context.save()
            self.context.translate(x, y)
            self.context.rectangle(
                left, top, width - left - right, height - top - bottom)
            self.context.restore()
            self.context.clip()
        clip_paths = urls(node.get("clip-path"))
        if clip_paths:
            path = self.paths.get(clip_paths[0][1:])
            if path:
                self.context.save()
                if path.get("clipPathUnits") == "objectBoundingBox":
                    x = float(size(self, node.get("x"), "x"))
                    y = float(size(self, node.get("y"), "y"))
                    width = float(size(self, node.get("width"), "x"))
                    height = float(size(self, node.get("height"), "y"))
                    self.context.translate(x, y)
                    self.context.scale(width, height)
                path.tag = "g"
                self.draw(path, stroke_and_fill=False)
                self.context.restore()
                if node.get("clip-rule") == "evenodd":
                    self.context.set_fill_rule(cairo.FILL_RULE_EVEN_ODD)
                self.context.clip()
                self.context.set_fill_rule(cairo.FILL_RULE_WINDING)

        # Filter
        apply_filter_before(self, node)

        if node.tag in TAGS:
            try:
                TAGS[node.tag](self, node)
            except PointError:
                # Error in point parsing, do nothing
                pass

        # Filter
        apply_filter_after(self, node)

        # Get stroke and fill opacity
        stroke_opacity = float(node.get("stroke-opacity", 1))
        fill_opacity = float(node.get("fill-opacity", 1))

        # Manage display and visibility
        display = node.get("display", "inline") != "none"
        visible = display and (node.get("visibility", "visible") != "hidden")

        if stroke_and_fill and visible and node.tag in TAGS:
            # Fill
            self.context.save()
            paint_source, paint_color = paint(node.get("fill", "black"))
            if not gradient_or_pattern(self, node, paint_source):
                if node.get("fill-rule") == "evenodd":
                    self.context.set_fill_rule(cairo.FILL_RULE_EVEN_ODD)
                self.context.set_source_rgba(*color(paint_color, fill_opacity))
            self.context.fill_preserve()
            self.context.restore()

            # Stroke
            self.context.save()
            self.context.set_line_width(size(self, node.get("stroke-width")))
            paint_source, paint_color = paint(node.get("stroke"))
            if not gradient_or_pattern(self, node, paint_source):
                self.context.set_source_rgba(
                    *color(paint_color, stroke_opacity))
            self.context.stroke()
            self.context.restore()
        elif not visible:
            self.context.new_path()

        # Draw children
        if display and node.tag not in (
                "linearGradient", "radialGradient", "marker", "pattern",
                "mask", "clipPath", "filter"):
            for child in node.children:
                self.draw(child, stroke_and_fill)

        if mask or opacity < 1:
            self.context.pop_group_to_source()
            if mask and mask in self.masks:
                paint_mask(self, node, mask, opacity)
            else:
                self.context.paint_with_alpha(opacity)

        if not node.root:
            # Restoring context is useless if we are in the root tag, it may
            # raise an exception if we have multiple svg tags
            self.context.restore()

        self.parent_node = self._old_parent_node
        self.font_size = old_font_size


class MultipageSurface(Surface):
    """Abstract base class for surfaces that can handle multiple pages."""
    def draw_root(self, node):
        self.width = None
        self.height = None
        svg_children = [child for child in node.children if child.tag == 'svg']
        if svg_children:
            # Multi-page
            for page in svg_children:
                width, height, viewbox = node_format(self, page)
                self.context.save()
                self.set_context_size(width, height, viewbox)
                width *= self.device_units_per_user_units
                height *= self.device_units_per_user_units
                self.page_sizes.append((width, height))
                self.cairo.set_size(width, height)
                self.draw(page)
                self.context.restore()
                self.cairo.show_page()
        else:
            self.draw(node)


class PDFSurface(MultipageSurface):
    """A surface that writes in PDF format."""
    surface_class = cairo.PDFSurface


class PSSurface(MultipageSurface):
    """A surface that writes in PostScript format."""
    surface_class = cairo.PSSurface


class PNGSurface(Surface):
    """A surface that writes in PNG format."""
    device_units_per_user_units = 1

    def _create_surface(self, width, height):
        """Create and return ``(cairo_surface, width, height)``."""
        width = int(width)
        height = int(height)
        cairo_surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
        return cairo_surface, width, height

    def finish(self):
        """Read the PNG surface content."""
        if self.output is not None:
            self.cairo.write_to_png(self.output)
        return super(PNGSurface, self).finish()


class SVGSurface(Surface):
    """A surface that writes in SVG format.

    It may seem pointless to render SVG to SVG, but this can be used
    with ``output=None`` to get a vector-based single page cairo surface.

    """
    surface_class = cairo.SVGSurface
