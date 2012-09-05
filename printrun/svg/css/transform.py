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
