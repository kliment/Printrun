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
    Optional(Group(colorDeclaration), default=()) +
    StringEnd()
)

url = (
    CaselessLiteral("URL")
    +
    Literal("(").suppress()+
    Group(SkipTo(urlEnd, include=True).setParseAction(parsePossibleURL))
)

#paint value will parse into a (type, details) tuple.
#For none and currentColor, the details tuple will be the empty tuple
#for CSS color declarations, it will be (type, (R,G,B))
#for URLs, it will be ("URL", ((url tuple), fallback))
#The url tuple will be as returned by urlparse.urlsplit, and can be
#an empty tuple if the parser has an error
#The fallback will be another (type, details) tuple as a parsed
#colorDeclaration, but may be the empty tuple if it is not present
paintValue = url | colorDeclaration
