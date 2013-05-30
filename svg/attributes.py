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
    Parsers for specific attributes
"""
import urlparse
from pyparsing import (Literal,
    Optional, oneOf, Group, StringEnd, Combine, Word, alphas, hexnums,
    CaselessLiteral, SkipTo
)
from css.colour import colourValue
import string

##Paint values
none = CaselessLiteral("none").setParseAction(lambda t: ["NONE", ()])
currentColor = CaselessLiteral("currentColor").setParseAction(lambda t: ["CURRENTCOLOR", ()])

def parsePossibleURL(t):
    possibleURL, fallback = t[0]
    return [urlparse.urlsplit(possibleURL), fallback]

#Normal color declaration
colorDeclaration = none | currentColor | colourValue

urlEnd = (
    Literal(")").suppress() +
    Optional(Group(colorDeclaration), default = ()) +
    StringEnd()
)

url = (
    CaselessLiteral("URL")
    +
    Literal("(").suppress()+
    Group(SkipTo(urlEnd, include = True).setParseAction(parsePossibleURL))
)

#paint value will parse into a (type, details) tuple.
#For none and currentColor, the details tuple will be the empty tuple
#for CSS color declarations, it will be (type, (R, G, B))
#for URLs, it will be ("URL", ((url tuple), fallback))
#The url tuple will be as returned by urlparse.urlsplit, and can be
#an empty tuple if the parser has an error
#The fallback will be another (type, details) tuple as a parsed
#colorDeclaration, but may be the empty tuple if it is not present
paintValue = url | colorDeclaration
