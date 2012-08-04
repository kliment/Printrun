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
SVG Parser.

"""

# Fallbacks for Python 2/3 and lxml/ElementTree
# pylint: disable=E0611,F0401,W0611
try:
    import lxml.etree as ElementTree
    from lxml.etree import XMLSyntaxError as ParseError
    HAS_LXML = True
except ImportError:
    from xml.etree import ElementTree
    from xml.parsers import expat
    # ElementTree's API changed between 2.6 and 2.7
    # pylint: disable=C0103
    ParseError = getattr(ElementTree, 'ParseError', expat.ExpatError)
    # pylint: enable=C0103
    HAS_LXML = False

try:
    from urllib import urlopen
    import urlparse
except ImportError:
    from urllib.request import urlopen
    from urllib import parse as urlparse  # Python 3
# pylint: enable=E0611,F0401,W0611


import gzip
import os.path

from .css import apply_stylesheets


# Python 2/3 compat
# pylint: disable=C0103,W0622
try:
    basestring
except NameError:
    basestring = str
# pylint: enable=C0103,W0622


def remove_svg_namespace(tree):
    """Remove the SVG namespace from ``tree`` tags.

    ``lxml.cssselect`` does not support empty/default namespaces, so remove any
    SVG namespace.

    """
    prefix = "{http://www.w3.org/2000/svg}"
    prefix_len = len(prefix)
    iterator = (
        tree.iter() if hasattr(tree, 'iter')
        else tree.getiterator())
    for element in iterator:
        tag = element.tag
        if hasattr(tag, "startswith") and tag.startswith(prefix):
            element.tag = tag[prefix_len:]


class Node(dict):
    """SVG node with dict-like properties and children."""
    def __init__(self, node, parent=None):
        """Create the Node from ElementTree ``node``, with ``parent`` Node."""
        super(Node, self).__init__()
        self.children = ()

        self.root = False
        self.tag = node.tag
        self.text = node.text

        # Inherits from parent properties
        # TODO: drop other attributes that should not be inherited
        if parent is not None:
            items = parent.copy()
            not_inherited = (
                "transform", "opacity", "style", "viewBox", "stop-color",
                "stop-opacity")
            if self.tag in ("tspan", "pattern"):
                not_inherited += ("x", "y")
            for attribute in not_inherited:
                if attribute in items:
                    del items[attribute]

            self.update(items)
            self.url = parent.url
            self.xml_tree = parent.xml_tree
            self.parent = parent

        self.update(dict(node.attrib.items()))

        # Handle the CSS
        style = self.pop("style", "")
        for declaration in style.split(";"):
            if ":" in declaration:
                name, value = declaration.split(":", 1)
                self[name.strip()] = value.strip()

        # Replace currentColor by a real color value
        color_attributes = (
            "fill", "stroke", "stop-color", "flood-color",
            "lighting-color")
        for attribute in color_attributes:
            if self.get(attribute) == "currentColor":
                self[attribute] = self.get("color", "black")

        # Replace inherit by the parent value
        for attribute, value in dict(self).items():
            if value == "inherit":
                if parent is not None and attribute in parent:
                    self[attribute] = parent.get(attribute)
                else:
                    del self[attribute]

        # Manage text by creating children
        if self.tag == "text" or self.tag == "textPath":
            self.children = self.text_children(node)

        if not self.children:
            self.children = tuple(
                Node(child, self) for child in node
                if isinstance(child.tag, basestring))

    def text_children(self, node):
        """Create children and return them."""
        children = []

        for child in node:
            children.append(Node(child, parent=self))
            if child.tail:
                anonymous = ElementTree.Element('tspan')
                anonymous.text = child.tail
                children.append(Node(anonymous, parent=self))

        return list(children)


class Tree(Node):
    """SVG tree."""
    def __init__(self, **kwargs):
        """Create the Tree from SVG ``text``."""
        # Make the parameters keyword-only:
        bytestring = kwargs.pop('bytestring', None)
        file_obj = kwargs.pop('file_obj', None)
        url = kwargs.pop('url', None)
        parent = kwargs.pop('parent', None)

        if bytestring is not None:
            tree = ElementTree.fromstring(bytestring)
            self.url = url
        elif file_obj is not None:
            tree = ElementTree.parse(file_obj).getroot()
            if url:
                self.url = url
            else:
                self.url = getattr(file_obj, 'name', None)
        elif url is not None:
            if "#" in url:
                url, element_id = url.split("#", 1)
            else:
                element_id = None
            if parent and parent.url:
                if url:
                    url = urlparse.urljoin(parent.url, url)
                elif element_id:
                    url = parent.url
            self.url = url
            if url:
                if urlparse.urlparse(url).scheme:
                    input_ = urlopen(url)
                else:
                    input_ = url  # filename
                if os.path.splitext(url)[1].lower() == "svgz":
                    input_ = gzip.open(url)
                tree = ElementTree.parse(input_).getroot()
            else:
                tree = parent.xml_tree
            if element_id:
                iterator = (
                    tree.iter() if hasattr(tree, 'iter')
                    else tree.getiterator())
                for element in iterator:
                    if element.get("id") == element_id:
                        tree = element
                        break
                else:
                    raise TypeError(
                        'No tag with id="%s" found.' % element_id)
        else:
            raise TypeError(
                'No input. Use one of bytestring, file_obj or url.')
        remove_svg_namespace(tree)
        apply_stylesheets(tree)
        self.xml_tree = tree
        super(Tree, self).__init__(tree, parent)
        self.root = True
