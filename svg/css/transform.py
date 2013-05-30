# This file is part of the Printrun suite.
#
# Printrun is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Printrun is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Printrun.  If not, see <http://www.gnu.org/licenses/>.

"""
    Parsing for CSS and CSS-style values, such as transform and filter attributes.
"""

from pyparsing import (Literal, Word, CaselessLiteral,
    Optional, Combine, Forward, ZeroOrMore, nums, oneOf, Group, delimitedList)

#some shared definitions from pathdata

from ..pathdata import number, maybeComma

paren = Literal("(").suppress()
cparen = Literal(")").suppress()

def Parenthised(exp):
    return Group(paren + exp + cparen)

skewY = Literal("skewY") + Parenthised(number)

skewX = Literal("skewX") + Parenthised(number)

rotate = Literal("rotate") + Parenthised(
    number + Optional(maybeComma + number + maybeComma + number)
)


scale = Literal("scale") + Parenthised(
    number + Optional(maybeComma + number)
)

translate = Literal("translate") + Parenthised(
    number + Optional(maybeComma + number)
)

matrix = Literal("matrix") + Parenthised(
    #there's got to be a better way to write this
    number + maybeComma +
    number + maybeComma +
    number + maybeComma +
    number + maybeComma +
    number + maybeComma +
    number
)

transform = (skewY | skewX | rotate | scale | translate | matrix)

transformList = delimitedList(Group(transform), delim=maybeComma)

if __name__ == '__main__':
    from tests.test_css import *
    unittest.main()
