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
Images manager.

"""

import base64
import gzip
from io import BytesIO
try:
    from urllib import urlopen, unquote
    import urlparse
    unquote_to_bytes = lambda data: unquote(
        data.encode('ascii') if isinstance(data, unicode) else data)
except ImportError:
    from urllib.request import urlopen
    from urllib import parse as urlparse  # Python 3
    from urllib.parse import unquote_to_bytes

from . import cairo
from .helpers import node_format, size, preserve_ratio
from ..parser import Tree


def open_data_url(url):
    """Decode URLs with the 'data' scheme. urllib can handle them
    in Python 2, but that is broken in Python 3.

    Inspired from Python 2.7.2’s urllib.py.

    """
    # syntax of data URLs:
    # dataurl   := "data:" [ mediatype ] [ ";base64" ] "," data
    # mediatype := [ type "/" subtype ] *( ";" parameter )
    # data      := *urlchar
    # parameter := attribute "=" value
    try:
        header, data = url.split(",", 1)
    except ValueError:
        raise IOError("bad data URL")
    header = header[5:]  # len("data:") == 5
    if header:
        semi = header.rfind(";")
        if semi >= 0 and "=" not in header[semi:]:
            encoding = header[semi+1:]
        else:
            encoding = ""
    else:
        encoding = ""

    data = unquote_to_bytes(data)
    if encoding == "base64":
        missing_padding = 4 - len(data) % 4
        if missing_padding:
            data += b"=" * missing_padding
        return base64.decodestring(data)
    return data


def image(surface, node):
    """Draw an image ``node``."""
    url = node.get("{http://www.w3.org/1999/xlink}href")
    if not url:
        return
    if url.startswith("data:"):
        image_bytes = open_data_url(url)
    else:
        base_url = node.get("{http://www.w3.org/XML/1998/namespace}base")
        if base_url:
            url = urlparse.urljoin(base_url, url)
        if node.url:
            url = urlparse.urljoin(node.url, url)
        if urlparse.urlparse(url).scheme:
            input_ = urlopen(url)
        else:
            input_ = open(url, 'rb')  # filename
        image_bytes = input_.read()

    if len(image_bytes) < 5:
        return

    x, y = size(surface, node.get("x"), "x"), size(surface, node.get("y"), "y")
    width = size(surface, node.get("width"), "x")
    height = size(surface, node.get("height"), "y")
    surface.context.rectangle(x, y, width, height)
    surface.context.clip()

    if image_bytes[:4] == b"\x89PNG":
        png_file = BytesIO(image_bytes)
    elif (image_bytes[:5] in (b"<svg ", b"<?xml", b"<!DOC") or
            image_bytes[:2] == b"\x1f\x8b"):
        if image_bytes[:2] == b"\x1f\x8b":
            image_bytes = gzip.GzipFile(fileobj=BytesIO(image_bytes)).read()
        surface.context.save()
        surface.context.translate(x, y)
        if "x" in node:
            del node["x"]
        if "y" in node:
            del node["y"]
        if "viewBox" in node:
            del node["viewBox"]
        tree = Tree(
            url=url, bytestring=image_bytes, tree_cache=surface.tree_cache)
        tree_width, tree_height, viewbox = node_format(surface, tree)
        if not tree_width or not tree_height:
            tree_width = tree["width"] = width
            tree_height = tree["height"] = height
        node.image_width = tree_width or width
        node.image_height = tree_height or height
        scale_x, scale_y, translate_x, translate_y = \
            preserve_ratio(surface, node)
        surface.set_context_size(*node_format(surface, tree))
        surface.context.translate(*surface.context.get_current_point())
        surface.context.scale(scale_x, scale_y)
        surface.context.translate(translate_x, translate_y)
        surface.draw(tree)
        surface.context.restore()
        # Restore twice, because draw does not restore at the end of svg tags
        surface.context.restore()
        return
    else:
        try:
            from PIL import Image
            png_file = BytesIO()
            Image.open(BytesIO(image_bytes)).save(png_file, 'PNG')
            png_file.seek(0)
        except:
            # No way to handle the image
            return

    image_surface = cairo.ImageSurface.create_from_png(png_file)

    node.image_width = image_surface.get_width()
    node.image_height = image_surface.get_height()
    scale_x, scale_y, translate_x, translate_y = preserve_ratio(surface, node)

    surface.context.rectangle(x, y, width, height)
    pattern_pattern = cairo.SurfacePattern(image_surface)
    surface.context.save()
    surface.context.translate(*surface.context.get_current_point())
    surface.context.scale(scale_x, scale_y)
    surface.context.translate(translate_x, translate_y)
    surface.context.set_source(pattern_pattern)
    surface.context.fill()
    surface.context.restore()
