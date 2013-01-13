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
    SVG path data parser


    Usage:
    steps = svg.parseString(pathdata)
    for command, arguments in steps:
        pass

"""

from pyparsing import (ParserElement, Literal, Word, CaselessLiteral,
    Optional, Combine, Forward, ZeroOrMore, nums, oneOf, Group, ParseException, OneOrMore)

#ParserElement.enablePackrat()

def Command(char):
    """ Case insensitive but case preserving"""
    return CaselessPreservingLiteral(char)

def Arguments(token):
    return Group(token)


class CaselessPreservingLiteral(CaselessLiteral):
    """ Like CaselessLiteral, but returns the match as found
        instead of as defined.
    """
    def __init__( self, matchString ):
        super(CaselessPreservingLiteral, self).__init__( matchString.upper() )
        self.name = "'%s'" % matchString
        self.errmsg = "Expected " + self.name
        self.myException.msg = self.errmsg

    def parseImpl( self, instring, loc, doActions = True ):
        test = instring[ loc:loc+self.matchLen ]
        if test.upper() == self.match:
            return loc+self.matchLen, test
        #~ raise ParseException( instring, loc, self.errmsg )
        exc = self.myException
        exc.loc = loc
        exc.pstr = instring
        raise exc

def Sequence(token):
    """ A sequence of the token"""
    return OneOrMore(token+maybeComma)

digit_sequence = Word(nums)

sign = oneOf("+ -")

def convertToFloat(s, loc, toks):
    try:
        return float(toks[0])
    except:
        raise ParseException(loc, "invalid float format %s"%toks[0])

exponent = CaselessLiteral("e")+Optional(sign)+Word(nums)

#note that almost all these fields are optional,
#and this can match almost anything. We rely on Pythons built-in
#float() function to clear out invalid values - loosely matching like this
#speeds up parsing quite a lot
floatingPointConstant = Combine(
    Optional(sign) +
    Optional(Word(nums)) +
    Optional(Literal(".") + Optional(Word(nums)))+
    Optional(exponent)
)

floatingPointConstant.setParseAction(convertToFloat)

number = floatingPointConstant

#same as FP constant but don't allow a - sign
nonnegativeNumber = Combine(
    Optional(Word(nums)) +
    Optional(Literal(".") + Optional(Word(nums)))+
    Optional(exponent)
)
nonnegativeNumber.setParseAction(convertToFloat)

coordinate = number

#comma or whitespace can seperate values all over the place in SVG
maybeComma = Optional(Literal(',')).suppress()

coordinateSequence = Sequence(coordinate)

coordinatePair = (coordinate + maybeComma + coordinate).setParseAction(lambda t: tuple(t))
coordinatePairSequence = Sequence(coordinatePair)

coordinatePairPair = coordinatePair + maybeComma + coordinatePair
coordinatePairPairSequence = Sequence(Group(coordinatePairPair))

coordinatePairTriple = coordinatePair + maybeComma + coordinatePair + maybeComma + coordinatePair
coordinatePairTripleSequence = Sequence(Group(coordinatePairTriple))

#commands
lineTo = Group(Command("L") + Arguments(coordinatePairSequence))

moveTo = Group(Command("M") + Arguments(coordinatePairSequence))

closePath = Group(Command("Z")).setParseAction(lambda t: ('Z', (None,)))

flag = oneOf("1 0").setParseAction(lambda t: bool(int((t[0]))))

arcRadius = (
    nonnegativeNumber + maybeComma + #rx
    nonnegativeNumber #ry
).setParseAction(lambda t: tuple(t))

arcFlags = (flag + maybeComma + flag).setParseAction(lambda t: tuple(t))

ellipticalArcArgument = Group(
    arcRadius + maybeComma + #rx, ry
    number + maybeComma +#rotation
    arcFlags + #large-arc-flag, sweep-flag
    coordinatePair #(x, y)
)


ellipticalArc = Group(Command("A") + Arguments(Sequence(ellipticalArcArgument)))

smoothQuadraticBezierCurveto = Group(Command("T") + Arguments(coordinatePairSequence))

quadraticBezierCurveto = Group(Command("Q") + Arguments(coordinatePairPairSequence))

smoothCurve = Group(Command("S") + Arguments(coordinatePairPairSequence))

curve = Group(Command("C") + Arguments(coordinatePairTripleSequence))

horizontalLine = Group(Command("H") + Arguments(coordinateSequence))
verticalLine = Group(Command("V") + Arguments(coordinateSequence))

drawToCommand = (
    lineTo | moveTo | closePath | ellipticalArc | smoothQuadraticBezierCurveto |
    quadraticBezierCurveto | smoothCurve | curve | horizontalLine | verticalLine
    )

#~ number.debug = True
moveToDrawToCommands = moveTo + ZeroOrMore(drawToCommand)

svg = ZeroOrMore(moveToDrawToCommands)
svg.keepTabs = True

def profile():
    import cProfile
    p = cProfile.Profile()
    p.enable()
    ptest()
    ptest()
    ptest()
    p.disable()
    p.print_stats()

bpath = """M204.33 139.83 C196.33 133.33 206.68 132.82 206.58 132.58 C192.33 97.08 169.35
    81.41 167.58 80.58 C162.12 78.02 159.48 78.26 160.45 76.97 C161.41 75.68 167.72 79.72 168.58
    80.33 C193.83 98.33 207.58 132.33 207.58 132.33 C207.58 132.33 209.33 133.33 209.58 132.58
    C219.58 103.08 239.58 87.58 246.33 81.33 C253.08 75.08 256.63 74.47 247.33 81.58 C218.58 103.58
    210.34 132.23 210.83 132.33 C222.33 134.83 211.33 140.33 211.83 139.83 C214.85 136.81 214.83 145.83 214.83
    145.83 C214.83 145.83 231.83 110.83 298.33 66.33 C302.43 63.59 445.83 -14.67 395.83 80.83 C393.24 85.79 375.83
    105.83 375.83 105.83 C375.83 105.83 377.33 114.33 371.33 121.33 C370.3 122.53 367.83 134.33 361.83 140.83 C360.14 142.67
    361.81 139.25 361.83 140.83 C362.33 170.83 337.76 170.17 339.33 170.33 C348.83 171.33 350.19 183.66 350.33 183.83 C355.83
    190.33 353.83 191.83 355.83 194.83 C366.63 211.02 355.24 210.05 356.83 212.83 C360.83 219.83 355.99 222.72 357.33 224.83
    C360.83 230.33 354.75 233.84 354.83 235.33 C355.33 243.83 349.67 240.73 349.83 244.33 C350.33 255.33 346.33 250.83 343.83 254.83
    C336.33 266.83 333.46 262.38 332.83 263.83 C329.83 270.83 325.81 269.15 324.33 270.83 C320.83 274.83 317.33 274.83 315.83 276.33
    C308.83 283.33 304.86 278.39 303.83 278.83 C287.83 285.83 280.33 280.17 277.83 280.33 C270.33 280.83 271.48 279.67 269.33 277.83
    C237.83 250.83 219.33 211.83 215.83 206.83 C214.4 204.79 211.35 193.12 212.33 195.83 C214.33 201.33 213.33 250.33 207.83 250.33
    C202.33 250.33 201.83 204.33 205.33 195.83 C206.43 193.16 204.4 203.72 201.79 206.83 C196.33 213.33 179.5 250.83 147.59 277.83
    C145.42 279.67 146.58 280.83 138.98 280.33 C136.46 280.17 128.85 285.83 112.65 278.83 C111.61 278.39 107.58 283.33 100.49 276.33
    C98.97 274.83 95.43 274.83 91.88 270.83 C90.39 269.15 86.31 270.83 83.27 263.83 C82.64 262.38 79.73 266.83 72.13 254.83 C69.6 250.83
    65.54 255.33 66.05 244.33 C66.22 240.73 60.48 243.83 60.99 235.33 C61.08 233.84 54.91 230.33 58.45 224.83 C59.81 222.72 54.91 219.83
    58.96 212.83 C60.57 210.05 49.04 211.02 59.97 194.83 C62 191.83 59.97 190.33 65.54 183.83 C65.69 183.66 67.06 171.33 76.69 170.33
    C78.28 170.17 53.39 170.83 53.9 140.83 C53.92 139.25 55.61 142.67 53.9 140.83 C47.82 134.33 45.32 122.53 44.27 121.33 C38.19 114.33
    39.71 105.83 39.71 105.83 C39.71 105.83 22.08 85.79 19.46 80.83 C-31.19 -14.67 114.07 63.59 118.22 66.33 C185.58 110.83 202 145.83
    202 145.83 C202 145.83 202.36 143.28 203 141.83 C203.64 140.39 204.56 140.02 204.33 139.83 z"""

def ptest():
    svg.parseString(bpath)





if __name__ == '__main__':

    #~ from tests.test_pathdata import *
    #~ unittest.main()
    profile()
