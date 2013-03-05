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
Optionally handle CSS stylesheets.

"""


from .parser import HAS_LXML

# Detect optional depedencies
# pylint: disable=W0611
try:
    import tinycss
    import cssselect
    CSS_CAPABLE = HAS_LXML
except ImportError:
    CSS_CAPABLE = False
# pylint: enable=W0611


# Python 2/3 compat
iteritems = getattr(dict, "iteritems", dict.items)  # pylint: disable=C0103


def find_stylesheets(tree):
    """Find the stylesheets included in ``tree``."""
    # TODO: support contentStyleType on <svg>
    default_type = "text/css"
    for element in tree.iter():
        # http://www.w3.org/TR/SVG/styling.html#StyleElement
        if (element.tag == "style" and
                element.get("type", default_type) == "text/css"):
            # TODO: pass href for relative URLs
            # TODO: support media types
            # TODO: what if <style> has children elements?
            yield tinycss.make_parser().parse_stylesheet(element.text)
    # TODO: support <?xml-stylesheet ... ?>


def find_style_rules(tree):
    """Find the style rules in ``tree``."""
    for stylesheet in find_stylesheets(tree):
        # TODO: warn for each stylesheet.errors
        for rule in stylesheet.rules:
            # TODO: support @import and @media
            if not rule.at_keyword:
                yield rule


def get_declarations(rule):
    """Get the declarations in ``rule``."""
    for declaration in rule.declarations:
        if declaration.name.startswith("-"):
            # Ignore properties prefixed by "-"
            continue
        # TODO: filter out invalid values
        yield (
            declaration.name,
            declaration.value.as_css(),
            bool(declaration.priority))


def match_selector(rule, tree):
    """Yield the ``(element, specificity)`` in ``tree`` matching ``rule``."""
    selector_list = cssselect.parse(rule.selector.as_css())
    translator = cssselect.GenericTranslator()
    for selector in selector_list:
        if not selector.pseudo_element:
            specificity = selector.specificity()
            for element in tree.xpath(translator.selector_to_xpath(selector)):
                yield element, specificity


def apply_stylesheets(tree):
    """Apply the stylesheet in ``tree`` to ``tree``."""
    if not CSS_CAPABLE:
        # TODO: warn?
        return
    style_by_element = {}
    for rule in find_style_rules(tree):
        declarations = list(get_declarations(rule))
        for element, specificity in match_selector(rule, tree):
            style = style_by_element.setdefault(element, {})
            for name, value, important in declarations:
                weight = important, specificity
                if name in style:
                    _old_value, old_weight = style[name]
                    if old_weight > weight:
                        continue
                style[name] = value, weight

    for element, style in iteritems(style_by_element):
        values = ["%s: %s" % (name, value)
                  for name, (value, weight) in iteritems(style)]
        values.append(element.get("style", ""))
        element.set("style", ";".join(values))
