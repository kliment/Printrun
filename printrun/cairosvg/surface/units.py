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
Units functions.

"""


UNITS = {
    "mm": 1 / 25.4,
    "cm": 1 / 2.54,
    "in": 1,
    "pt": 1 / 72.,
    "pc": 1 / 6.,
    "px": None}


def size(surface, string, reference="xy"):
    """Replace a ``string`` with units by a float value.

    If ``reference`` is a float, it is used as reference for percentages. If it
    is ``'x'``, we use the viewport width as reference. If it is ``'y'``, we
    use the viewport height as reference. If it is ``'xy'``, we use
    ``(viewport_width ** 2 + viewport_height ** 2) ** .5 / 2 ** .5`` as
    reference.

    """
    if not string:
        return 0.

    try:
        return float(string)
    except ValueError:
        # Not a float, try something else
        pass

    if "%" in string:
        if reference == "x":
            reference = surface.context_width or 0
        elif reference == "y":
            reference = surface.context_height or 0
        elif reference == "xy":
            reference = (
                (surface.context_width ** 2 + surface.context_height ** 2)
                ** .5 / 2 ** .5)
        return float(string.strip(" %")) * reference / 100
    elif "em" in string:
        return surface.font_size * float(string.strip(" em"))
    elif "ex" in string:
        # Assume that 1em == 2ex
        return surface.font_size * float(string.strip(" ex")) / 2

    for unit, coefficient in UNITS.items():
        if unit in string:
            number = float(string.strip(" " + unit))
            return number * (surface.dpi * coefficient if coefficient else 1)

    # Try to return the number at the beginning of the string
    return_string = ""
    while string and (string[0].isdigit() or string[0] in "+-."):
        return_string += string[0]
        string = string[1:]

    # Unknown size or multiple sizes
    return float(return_string or 0)
