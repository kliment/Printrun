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

"""MeatPack G-code compression, the sending side.

Each byte on the wire carries two characters from a 15 character alphabet,
the first in the low nibble and the second in the high nibble. The nibble
value 0xF means the character doesn't fit the alphabet and is sent as a whole
byte after the packed byte.

Commands are 0xFF, 0xFF and a command byte. They can be sent at any time
between lines, in either mode.
"""

import re

_COMMAND = b"\xff\xff"
ENABLE_PACKING = _COMMAND + b"\xfb"
DISABLE_PACKING = _COMMAND + b"\xfa"
RESET_ALL = _COMMAND + b"\xf9"
QUERY_CONFIG = _COMMAND + b"\xf8"
ENABLE_NO_SPACES = _COMMAND + b"\xf7"
DISABLE_NO_SPACES = _COMMAND + b"\xf6"

# In no-spaces mode the firmware decodes the space entry as 'E'.
_ALPHABET = b"0123456789.E\nGX"
_LITERAL = 0xF
_NIBBLES = tuple(_ALPHABET.find(i) if i in _ALPHABET else _LITERAL
                 for i in range(256))
_NEWLINE = _ALPHABET.index(b"\n")

_MOVE_EXP = re.compile(r"\s*G[0-3](?![0-9])")
_EMERGENCY_EXP = re.compile(r"\s*(N\d+\s*)?M(108|112|410|876)(?![0-9])")


def strip_spaces(command):
    """Remove the spaces from a move, where they serve no purpose.

    Other commands are returned unchanged, since they may carry text.
    """
    if _MOVE_EXP.match(command):
        return command.replace(" ", "")
    return command


def is_emergency(command):
    """Tell if a command is one the firmware's emergency parser looks for.

    That parser reads the serial data before it is unpacked.
    """
    return _EMERGENCY_EXP.match(command) is not None


def pack(line):
    """Pack the bytes of one line, ending in a newline, for no-spaces mode.
    """
    out = bytearray()
    nibbles = _NIBBLES
    i = 0
    while i < len(line):
        first = line[i]
        nibble = nibbles[first]
        if nibble == _NEWLINE:
            # The firmware doesn't read a second character after a newline
            out.append(_NEWLINE)
            i += 1
            continue
        second = line[i + 1]
        second_nibble = nibbles[second]
        out.append(nibble | second_nibble << 4)
        if nibble == _LITERAL:
            out.append(first)
        if second_nibble == _LITERAL:
            out.append(second)
        i += 2
    return bytes(out)
