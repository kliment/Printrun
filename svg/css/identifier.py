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
