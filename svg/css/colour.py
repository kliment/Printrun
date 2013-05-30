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
    Parsing for CSS colour values.
    Supported formats:
        hex literal short: #fff
        hex literal long: #fafafa
        rgb bytes: rgb(255,100,0)
        rgb percent: rgb(100%,100%,0%)
        named color: black
"""
import wx
import string
import urlparse
from pyparsing import nums, Literal, Optional, oneOf, Group, StringEnd, Combine, Word, alphas, hexnums
from ..pathdata import number, sign

number = number.copy()
integerConstant = Word(nums+"+-").setParseAction(lambda t:int(t[0]))

#rgb format parser
comma = Literal(",").suppress()
def clampColourByte(val):
    val = int(val)
    return min(max(0,val), 255)

def clampColourPerc(val):
    val = float(val)
    return min(max(0,val), 100)

def parseColorPerc(token):
    val = token[0]
    val = clampColourPerc(val)
    #normalize to bytes
    return int(255 * (val / 100.0))


colorByte = Optional(sign) + integerConstant.setParseAction(lambda t: clampColourByte(t[0]))
colorPerc = number.setParseAction(parseColorPerc) + Literal("%").suppress()

rgb = (
    Literal("rgb(").setParseAction(lambda t: "RGB") +

    (
    #integer constants, ie 255,255,255
    Group(colorByte + comma + colorByte + comma + colorByte) ^
    #percentage values, ie 100%, 50%
    Group(colorPerc + comma + colorPerc + comma + colorPerc)
    )
    +
    Literal(")").suppress() + StringEnd()
)

def parseShortHex(t):
    return tuple(int(x*2, 16) for x in t[0])


doubleHex = Word(hexnums, exact=2).setParseAction(lambda t: int(t[0], 16))
hexLiteral = (Literal("#").setParseAction(lambda t: "RGB") +
    (
    Group(doubleHex + doubleHex + doubleHex) |
    Word(hexnums, exact=3).setParseAction(parseShortHex)
    ) + StringEnd()
)

def parseNamedColour(t):
    try:
        return ["RGB", NamedColours[t[0].lower()]]
    except KeyError:
        return ["RGB", (0,0,0)]

namedColour = Word(alphas).setParseAction(parseNamedColour)


colourValue = rgb | hexLiteral | namedColour


##constants
NamedColours = {
    #~ #html named colours
    #~ "black":(0,0,0),
    #~ "silver": (0xc0, 0xc0, 0xc0, 255),
    #~ "gray": (0x80, 0x80, 0x80),
    #~ "white":(255,255,255),
    #~ "maroon":(0x80, 0, 0),
    #~ "red":(0xff, 0, 0),
    #~ "purple":(0x80, 0, 0x80),
    #~ "fuchsia":(0xff, 0, 0xff),
    #~ "green": (0, 0x80, 0),
    #~ "lime": (0, 0xff, 0),
    #~ "olive": (0x80, 0x80, 00),
    #~ "yellow":(0xff, 0xff, 00),
    #~ "navy": (0, 0, 0x80),
    #~ "blue": (0, 0, 0xff),
    #~ "teal": (0, 0x80, 0x80),
    #~ "aqua": (0, 0xff, 0xff),
    #expanded named colors from SVG spc
    'aliceblue' : (240, 248, 255) ,
    'antiquewhite' : (250, 235, 215) ,
    'aqua' : ( 0, 255, 255) ,
    'aquamarine' : (127, 255, 212) ,
    'azure' : (240, 255, 255) ,
    'beige' : (245, 245, 220) ,
    'bisque' : (255, 228, 196) ,
    'black' : ( 0, 0, 0) ,
    'blanchedalmond' : (255, 235, 205) ,
    'blue' : ( 0, 0, 255) ,
    'blueviolet' : (138, 43, 226) ,
    'brown' : (165, 42, 42) ,
    'burlywood' : (222, 184, 135) ,
    'cadetblue' : ( 95, 158, 160) ,
    'chartreuse' : (127, 255, 0) ,
    'chocolate' : (210, 105, 30) ,
    'coral' : (255, 127, 80) ,
    'cornflowerblue' : (100, 149, 237) ,
    'cornsilk' : (255, 248, 220) ,
    'crimson' : (220, 20, 60) ,
    'cyan' : ( 0, 255, 255) ,
    'darkblue' : ( 0, 0, 139) ,
    'darkcyan' : ( 0, 139, 139) ,
    'darkgoldenrod' : (184, 134, 11) ,
    'darkgray' : (169, 169, 169) ,
    'darkgreen' : ( 0, 100, 0) ,
    'darkgrey' : (169, 169, 169) ,
    'darkkhaki' : (189, 183, 107) ,
    'darkmagenta' : (139, 0, 139) ,
    'darkolivegreen' : ( 85, 107, 47) ,
    'darkorange' : (255, 140, 0) ,
    'darkorchid' : (153, 50, 204) ,
    'darkred' : (139, 0, 0) ,
    'darksalmon' : (233, 150, 122) ,
    'darkseagreen' : (143, 188, 143) ,
    'darkslateblue' : ( 72, 61, 139) ,
    'darkslategray' : ( 47, 79, 79) ,
    'darkslategrey' : ( 47, 79, 79) ,
    'darkturquoise' : ( 0, 206, 209) ,
    'darkviolet' : (148, 0, 211) ,
    'deeppink' : (255, 20, 147) ,
    'deepskyblue' : ( 0, 191, 255) ,
    'dimgray' : (105, 105, 105) ,
    'dimgrey' : (105, 105, 105) ,
    'dodgerblue' : ( 30, 144, 255) ,
    'firebrick' : (178, 34, 34) ,
    'floralwhite' : (255, 250, 240) ,
    'forestgreen' : ( 34, 139, 34) ,
    'fuchsia' : (255, 0, 255) ,
    'gainsboro' : (220, 220, 220) ,
    'ghostwhite' : (248, 248, 255) ,
    'gold' : (255, 215, 0) ,
    'goldenrod' : (218, 165, 32) ,
    'gray' : (128, 128, 128) ,
    'grey' : (128, 128, 128) ,
    'green' : ( 0, 128, 0) ,
    'greenyellow' : (173, 255, 47) ,
    'honeydew' : (240, 255, 240) ,
    'hotpink' : (255, 105, 180) ,
    'indianred' : (205, 92, 92) ,
    'indigo' : ( 75, 0, 130) ,
    'ivory' : (255, 255, 240) ,
    'khaki' : (240, 230, 140) ,
    'lavender' : (230, 230, 250) ,
    'lavenderblush' : (255, 240, 245) ,
    'lawngreen' : (124, 252, 0) ,
    'lemonchiffon' : (255, 250, 205) ,
    'lightblue' : (173, 216, 230) ,
    'lightcoral' : (240, 128, 128) ,
    'lightcyan' : (224, 255, 255) ,
    'lightgoldenrodyellow' : (250, 250, 210) ,
    'lightgray' : (211, 211, 211) ,
    'lightgreen' : (144, 238, 144) ,
    'lightgrey' : (211, 211, 211) ,
    'lightpink' : (255, 182, 193) ,
    'lightsalmon' : (255, 160, 122) ,
    'lightseagreen' : ( 32, 178, 170) ,
    'lightskyblue' : (135, 206, 250) ,
    'lightslategray' : (119, 136, 153) ,
    'lightslategrey' : (119, 136, 153) ,
    'lightsteelblue' : (176, 196, 222) ,
    'lightyellow' : (255, 255, 224) ,
    'lime' : ( 0, 255, 0) ,
    'limegreen' : ( 50, 205, 50) ,
    'linen' : (250, 240, 230) ,
    'magenta' : (255, 0, 255) ,
    'maroon' : (128, 0, 0) ,
    'mediumaquamarine' : (102, 205, 170) ,
    'mediumblue' : ( 0, 0, 205) ,
    'mediumorchid' : (186, 85, 211) ,
    'mediumpurple' : (147, 112, 219) ,
    'mediumseagreen' : ( 60, 179, 113) ,
    'mediumslateblue' : (123, 104, 238) ,
    'mediumspringgreen' : ( 0, 250, 154) ,
    'mediumturquoise' : ( 72, 209, 204) ,
    'mediumvioletred' : (199, 21, 133) ,
    'midnightblue' : ( 25, 25, 112) ,
    'mintcream' : (245, 255, 250) ,
    'mistyrose' : (255, 228, 225) ,
    'moccasin' : (255, 228, 181) ,
    'navajowhite' : (255, 222, 173) ,
    'navy' : ( 0, 0, 128) ,
    'oldlace' : (253, 245, 230) ,
    'olive' : (128, 128, 0) ,
    'olivedrab' : (107, 142, 35) ,
    'orange' : (255, 165, 0) ,
    'orangered' : (255, 69, 0) ,
    'orchid' : (218, 112, 214) ,
    'palegoldenrod' : (238, 232, 170) ,
    'palegreen' : (152, 251, 152) ,
    'paleturquoise' : (175, 238, 238) ,
    'palevioletred' : (219, 112, 147) ,
    'papayawhip' : (255, 239, 213) ,
    'peachpuff' : (255, 218, 185) ,
    'peru' : (205, 133, 63) ,
    'pink' : (255, 192, 203) ,
    'plum' : (221, 160, 221) ,
    'powderblue' : (176, 224, 230) ,
    'purple' : (128, 0, 128) ,
    'red' : (255, 0, 0) ,
    'rosybrown' : (188, 143, 143) ,
    'royalblue' : ( 65, 105, 225) ,
    'saddlebrown' : (139, 69, 19) ,
    'salmon' : (250, 128, 114) ,
    'sandybrown' : (244, 164, 96) ,
    'seagreen' : ( 46, 139, 87) ,
    'seashell' : (255, 245, 238) ,
    'sienna' : (160, 82, 45) ,
    'silver' : (192, 192, 192) ,
    'skyblue' : (135, 206, 235) ,
    'slateblue' : (106, 90, 205) ,
    'slategray' : (112, 128, 144) ,
    'slategrey' : (112, 128, 144) ,
    'snow' : (255, 250, 250) ,
    'springgreen' : ( 0, 255, 127) ,
    'steelblue' : ( 70, 130, 180) ,
    'tan' : (210, 180, 140) ,
    'teal' : ( 0, 128, 128) ,
    'thistle' : (216, 191, 216) ,
    'tomato' : (255, 99, 71) ,
    'turquoise' : ( 64, 224, 208) ,
    'violet' : (238, 130, 238) ,
    'wheat' : (245, 222, 179) ,
    'white' : (255, 255, 255) ,
    'whitesmoke' : (245, 245, 245) ,
    'yellow' : (255, 255, 0) ,
    'yellowgreen' : (154, 205, 50) ,
}



def fillCSS2SystemColours():
    #The system colours require a wxApp to be present to retrieve,
    #so if you wnat support for them you'll need
    #to call this function after your wxApp instance starts
    systemColors = {
        "ActiveBorder": wx.SYS_COLOUR_ACTIVEBORDER,
        "ActiveCaption": wx.SYS_COLOUR_ACTIVECAPTION,
        "AppWorkspace": wx.SYS_COLOUR_APPWORKSPACE,
        "Background": wx.SYS_COLOUR_BACKGROUND,
        "ButtonFace": wx.SYS_COLOUR_BTNFACE,
        "ButtonHighlight": wx.SYS_COLOUR_BTNHIGHLIGHT,
        "ButtonShadow": wx.SYS_COLOUR_BTNSHADOW,
        "ButtonText": wx.SYS_COLOUR_BTNTEXT,
        "CaptionText": wx.SYS_COLOUR_CAPTIONTEXT,
        "GrayText": wx.SYS_COLOUR_GRAYTEXT,
        "Highlight": wx.SYS_COLOUR_HIGHLIGHT,
        "HighlightText": wx.SYS_COLOUR_HIGHLIGHTTEXT,
        "InactiveBorder": wx.SYS_COLOUR_INACTIVEBORDER,
        "InactiveCaption": wx.SYS_COLOUR_INACTIVECAPTION,
        "InfoBackground": wx.SYS_COLOUR_INFOBK,
        "InfoText": wx.SYS_COLOUR_INFOTEXT,
        "Menu": wx.SYS_COLOUR_MENU,
        "MenuText": wx.SYS_COLOUR_MENUTEXT,
        "Scrollbar": wx.SYS_COLOUR_SCROLLBAR,
        "ThreeDDarkShadow": wx.SYS_COLOUR_3DDKSHADOW,
        "ThreeDFace": wx.SYS_COLOUR_3DFACE,
        "ThreeDHighlight": wx.SYS_COLOUR_3DHIGHLIGHT,
        "ThreeDLightShadow": wx.SYS_COLOUR_3DLIGHT,
        "ThreeDShadow": wx.SYS_COLOUR_3DSHADOW,
        "Window": wx.SYS_COLOUR_WINDOW,
        "WindowFrame": wx.SYS_COLOUR_WINDOWFRAME,
        "WindowText": wx.SYS_COLOUR_WINDOWTEXT
    }
    NamedColours.update(
        #strip the alpha from the system colors. Is this really what we want to do?
        (k.lower(), wx.SystemSettings.GetColour(v)[:3]) for (k,v) in systemColors.iteritems()
    )
