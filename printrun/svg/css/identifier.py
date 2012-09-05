""" Parse CSS identifiers. More complicated than it sounds"""

from pyparsing import Word, Literal, Regex, Combine, Optional, White, oneOf, ZeroOrMore
import string
import re

class White(White):
    """ Customize whitespace to match the CSS spec values"""
    def __init__(self, ws=" \t\r\n\f", min=1, max=0, exact=0):
        super(White, self).__init__(ws, min, max, exact)

escaped = (
    Literal("\\").suppress() +
    #chr(20)-chr(126) + chr(128)-unichr(sys.maxunicode)
    Regex(u"[\u0020-\u007e\u0080-\uffff]", re.IGNORECASE)
)

def convertToUnicode(t):
    return unichr(int(t[0], 16))
hex_unicode = (
    Literal("\\").suppress() +
    Regex("[0-9a-f]{1,6}", re.IGNORECASE) +
    Optional(White(exact=1)).suppress()
).setParseAction(convertToUnicode)


escape = hex_unicode | escaped

#any unicode literal outside the 0-127 ascii range
nonascii = Regex(u"[^\u0000-\u007f]")

#single character for starting an identifier.
nmstart = Regex(u"[A-Z]", re.IGNORECASE) | nonascii | escape

nmchar = Regex(u"[0-9A-Z-]", re.IGNORECASE) | nonascii | escape

identifier = Combine(nmstart + ZeroOrMore(nmchar))
