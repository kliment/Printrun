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
    SVGDocument
"""
import wx

from cStringIO import StringIO
import warnings
import math
from functools import wraps

import pathdata
import css
from svg.css.colour import colourValue
from svg.css import values
from attributes import paintValue

document = """<?xml version = "1.0" standalone = "no"?>
<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN"
  "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">
<svg width = "4cm" height = "4cm" viewBox = "0 0 400 400"
     xmlns = "http://www.w3.org/2000/svg" version = "1.1">
  <title>Example triangle01- simple example of a 'path'</title>
  <desc>A path that draws a triangle</desc>
  <rect x = "1" y = "1" width = "398" height = "398"
        fill = "none" stroke = "blue" />
  <path d = "M 100 100 L 300 100 L 200 300 z"
        fill = "red" stroke = "blue" stroke-width = "3" />
</svg>"""

makePath = lambda: wx.GraphicsRenderer_GetDefaultRenderer().CreatePath()

def attrAsFloat(node, attr, defaultValue = "0"):
    val = node.get(attr, defaultValue)
    #TODO: process stuff like "inherit" by walking back up the nodes
    #fast path optimization - if it's a valid float, don't
    #try to parse it.
    try:
        return float(val)
    except ValueError:
        return valueToPixels(val)

def valueToPixels(val, defaultUnits = "px"):
    #TODO manage default units
    from pyparsing import ParseException
    try:
        val, unit = values.length.parseString(val)
    except ParseException:
        print "***", val
        raise
    #todo: unit conversion to something other than pixels
    return val


def pathHandler(func):
    """decorator for methods which return a path operation
        Creates the path they will fill,
        and generates the path operations for the node
    """
    @wraps(func)
    def inner(self, node):
        #brush = self.getBrushFromState()
        #pen = self.getPenFromState()
        #if not (brush or pen):
        #    return None, []
        path = wx.GraphicsRenderer_GetDefaultRenderer().CreatePath()
        func(self, node, path)
        ops = self.generatePathOps(path)
        return path, ops
    return inner


class SVGDocument(object):
    lastControl = None
    brushCache = {}
    penCache = {}
    def __init__(self, element):
        """
        Create an SVG document from an ElementTree node.
        """
        self.handlers = {
            '{http://www.w3.org/2000/svg}svg':self.addGroupToDocument,
            '{http://www.w3.org/2000/svg}a':self.addGroupToDocument,
            '{http://www.w3.org/2000/svg}g':self.addGroupToDocument,
            '{http://www.w3.org/2000/svg}rect':self.addRectToDocument,
            '{http://www.w3.org/2000/svg}circle': self.addCircleToDocument,
            '{http://www.w3.org/2000/svg}ellipse': self.addEllipseToDocument,
            '{http://www.w3.org/2000/svg}line': self.addLineToDocument,
            '{http://www.w3.org/2000/svg}polyline': self.addPolyLineToDocument,
            '{http://www.w3.org/2000/svg}polygon': self.addPolygonToDocument,
            '{http://www.w3.org/2000/svg}path':self.addPathDataToDocument,
            '{http://www.w3.org/2000/svg}text':self.addTextToDocument
        }

        assert element.tag == '{http://www.w3.org/2000/svg}svg', 'Not an SVG fragment'
        self.tree = element
        self.paths = {}
        self.stateStack = [{}]
        path, ops = self.processElement(element)
        self.ops = ops

    @property
    def state(self):
        """ Retrieve the current state, without popping"""
        return self.stateStack[-1]

    def processElement(self, element):
        """ Process one element of the XML tree.
        Returns the path representing the node,
        and an operation list for drawing the node.

        Parent nodes should return a path (for hittesting), but
        no draw operations
        """
        #copy the current state
        current = dict(self.state)
        current.update(element.items())
        current.update(css.inlineStyle(element.get("style", "")))
        self.stateStack.append(current)
        handler = self.handlers.get(element.tag, lambda *any: (None, None))
        path, ops = handler(element)
        self.paths[element] = path
        self.stateStack.pop()
        return path, ops

    def createTransformOpsFromNode(self, node):
        """ Returns an oplist for transformations.
        This applies to a node, not the current state because
        the transform stack is saved in the wxGraphicsContext.

        This oplist does *not* include the push/pop state commands
        """
        ops = []
        transform = node.get('transform')
        #todo: replace this with a mapping list
        if transform:
            for transform, args in css.transformList.parseString(transform):
                if transform == 'scale':
                    if len(args) == 1:
                        x = y = args[0]
                    else:
                        x, y = args
                    ops.append(
                        (wx.GraphicsContext.Scale, (x, y))
                    )
                if transform == 'translate':
                    if len(args) == 1:
                        x = args[0]
                        y = 0
                    else:
                        x, y = args
                    ops.append(
                        (wx.GraphicsContext.Translate, (x, y))
                    )
                if transform == 'rotate':
                    if len(args) == 3:
                        angle, cx, cy = args
                        angle = math.radians(angle)
                        ops.extend([
                            (wx.GraphicsContext.Translate, (cx, cy)),
                            (wx.GraphicsContext.Rotate, (angle,)),
                            (wx.GraphicsContext.Translate, (-cx, -cy)),
                        ])
                    else:
                        angle = args[0]
                        angle = math.radians(angle)
                        ops.append(
                            (wx.GraphicsContext.Rotate, (angle,))
                        )
                if transform == 'matrix':
                    matrix = wx.GraphicsRenderer_GetDefaultRenderer().CreateMatrix(
                        *args
                    )
                    ops.append(
                        (wx.GraphicsContext.ConcatTransform, (matrix,))
                    )
                if transform == 'skewX':
                    matrix = wx.GraphicsRenderer_GetDefaultRenderer().CreateMatrix(
                        1, 0, math.tan(math.radians(args[0])), 1, 0, 0
                    )
                    ops.append(
                        (wx.GraphicsContext.ConcatTransform, (matrix,))
                    )
                if transform == 'skewY':
                    matrix = wx.GraphicsRenderer_GetDefaultRenderer().CreateMatrix(
                        1, math.tan(math.radians(args[0])), 0, 1, 0, 0
                    )
                    ops.append(
                        (wx.GraphicsContext.ConcatTransform, (matrix,))
                    )
        return ops


    def addGroupToDocument(self, node):
        """ For parent elements: push on a state,
        then process all child elements
        """
        ops = [
            (wx.GraphicsContext.PushState, ())
        ]

        path = makePath()
        ops.extend(self.createTransformOpsFromNode(node))
        for child in node.getchildren():
            cpath, cops = self.processElement(child)
            if cpath:
                path.AddPath(cpath)
            if cops:
                ops.extend(cops)
        ops.append(
            (wx.GraphicsContext.PopState, ())
        )
        return path, ops

    def getFontFromState(self):
        font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
        family = self.state.get("font-family")
        if False:#family:
            #print "setting font", family
            font.SetFaceName(family)
        size = self.state.get("font-size")
        #I'm not sure if this is right or not
        if size:
            val, unit = values.length.parseString(size)
            if '__WXMSW__' in wx.PlatformInfo:
                i = int(val)
                font.SetPixelSize((i, i))
            else:
                font.SetPointSize(int(val))
        return font

    def addTextToDocument(self, node):
        x, y = [attrAsFloat(node, attr) for attr in ('x', 'y')]

        def DoDrawText(context, text, x, y, brush = wx.NullGraphicsBrush):
            #SVG spec appears to originate text from the bottom
            #rather than the top as with our API. This function
            #will measure and then re-orient the text as needed.
            w, h = context.GetTextExtent(text)
            y -= h
            context.DrawText(text, x, y, brush)
        font = self.getFontFromState()
        brush = self.getBrushFromState()
        if not (brush and brush.IsOk()):
            brush = wx.BLACK_BRUSH
        #normalize whitespace
        #TODO: SVG probably has rules for this
        text = ' '.join(node.text.split() if node.text else "")
        if text is None:
            return None, []
        ops = [
            (wx.GraphicsContext.SetFont, (font, brush.Colour)),
            (DoDrawText, (text, x, y))
        ]
        return None, ops

    @pathHandler
    def addRectToDocument(self, node, path):
        x, y, w, h = (attrAsFloat(node, attr) for attr in ['x', 'y', 'width', 'height'])
        rx = node.get('rx')
        ry = node.get('ry')
        if not (w and h):
            path.MoveToPoint(x, y) #keep the current point correct
            return
        if rx or ry:
            if rx and ry:
                rx, ry = float(rx), float(ry)
            elif rx:
                rx = ry = float(rx)
            elif ry:
                rx = ry = float(ry)
            #value clamping as per spec section 9.2
            rx = min(rx, w/2)
            ry = min(ry, h/2)

            #origin
            path.MoveToPoint(x+rx, y)
            path.AddLineToPoint(x+w-rx, y)
            #top right
            cx = rx * 2
            cy = ry * 2
            path.AddEllipticalArc(
                x+w-cx, y,
                cx, cy,
                math.radians(270), math.radians(0),
                True
            )
            path.AddLineToPoint(x+w, y+h-ry)
            #bottom right
            path.AddEllipticalArc(
                x+w-cx, y+h-cy,
                cx, cy,
                math.radians(0), math.radians(90),
                True
            )
            path.AddLineToPoint(x+rx, y+h)
            #bottom left
            path.AddEllipticalArc(
                x, y+h-cy,
                cx, cy,
                math.radians(90),
                math.radians(180),
                True
            )
            path.AddLineToPoint(x, y+ry)
            #bottom right
            path.AddEllipticalArc(
                x, y,
                cx, cy,
                math.radians(180),
                math.radians(270),
                True
            )
            path.CloseSubpath()
        else:
            path.AddRectangle(
                x, y, w, h
            )

    @pathHandler
    def addCircleToDocument(self, node, path):
        cx, cy, r = [attrAsFloat(node, attr) for attr in ('cx', 'cy', 'r')]
        path.AddCircle(cx, cy, r)

    @pathHandler
    def addEllipseToDocument(self, node, path):
        cx, cy, rx, ry = [float(node.get(attr, 0)) for attr in ('cx', 'cy', 'rx', 'ry')]
        #cx, cy are centerpoint.
        #rx, ry are radius.
        #wxGC coords are the rect of the ellipse bounding box.
        if rx <= 0 or ry <= 0:
            return
        x = cx - rx
        y = cy - ry
        path.AddEllipse(x, y, rx*2, ry*2)

    @pathHandler
    def addLineToDocument(self, node, path):
        x1, y1, x2, y2 = [attrAsFloat(node, attr) for attr in ('x1', 'y1', 'x2', 'y2')]
        path.MoveToPoint(x1, y1)
        path.AddLineToPoint(x2, y2)

    @pathHandler
    def addPolyLineToDocument(self, node, path):
        #translate to pathdata and render that
        data = "M " + node.get("points")
        self.addPathDataToPath(data, path)

    @pathHandler
    def addPolygonToDocument(self, node, path):
        #translate to pathdata and render that
        data = "M " + node.get("points") + " Z"
        self.addPathDataToPath(data, path)

    @pathHandler
    def addPathDataToDocument(self, node, path):
        self.addPathDataToPath(node.get('d', ''), path)

    def addPathDataToPath(self, data, path):
        self.lastControl = None
        self.lastControlQ = None
        self.firstPoints = []
        def normalizeStrokes(parseResults):
            """ The data comes from the parser in the
            form of (command, [list of arguments]).
            We translate that to [(command, args[0]), (command, args[1])]
            via a generator.

            M is special cased because its subsequent arguments
            become linetos.
            """
            for command, arguments in parseResults:
                if not arguments:
                    yield (command, ())
                else:
                    arguments = iter(arguments)
                    if command ==  'm':
                        yield (command, arguments.next())
                        command = "l"
                    elif command == "M":
                        yield (command, arguments.next())
                        command = "L"
                    for arg in arguments:
                        yield (command, arg)
        #print "data length", len(data)
        import time
        t = time.time()
        parsed = pathdata.svg.parseString(data)
        #print "parsed in", time.time()-t
        for stroke in normalizeStrokes(parsed):
            self.addStrokeToPath(path, stroke)


    def generatePathOps(self, path):
        """ Look at the current state and generate the
        draw operations (fill, stroke, neither) for the path"""
        ops = []
        brush = self.getBrushFromState(path)
        fillRule = self.state.get('fill-rule', 'nonzero')
        frMap = {'nonzero':wx.WINDING_RULE, 'evenodd': wx.ODDEVEN_RULE}
        fr = frMap.get(fillRule, wx.ODDEVEN_RULE)
        if brush:
            ops.append(
                (wx.GraphicsContext.SetBrush, (brush,))
            )
            ops.append(
                (wx.GraphicsContext.FillPath, (path, fr))
            )
        pen = self.getPenFromState()
        if pen:
            ops.append(
                    (wx.GraphicsContext.SetPen, (pen,))
                )
            ops.append(
                (wx.GraphicsContext.StrokePath, (path,))
            )
        return ops

    def getPenFromState(self):
        pencolour = self.state.get('stroke', 'none')
        if pencolour == 'currentColor':
            pencolour = self.state.get('color', 'none')
        if pencolour == 'transparent':
            return wx.TRANSPARENT_PEN
        if pencolour == 'none':
            return wx.NullPen
        type, value = colourValue.parseString(pencolour)
        if type == 'URL':
            warnings.warn("Color servers for stroking not implemented")
            return wx.NullPen
        else:
            if value[:3] == (-1, -1, -1):
                return wx.NullPen
            pen = wx.Pen(wx.Colour(*value))
        width = self.state.get('stroke-width')
        if width:
            width, units = values.length.parseString(width)
            pen.SetWidth(width)
        capmap = {
            'butt':wx.CAP_BUTT,
            'round':wx.CAP_ROUND,
            'square':wx.CAP_PROJECTING
        }
        joinmap = {
            'miter':wx.JOIN_MITER,
            'round':wx.JOIN_ROUND,
            'bevel':wx.JOIN_BEVEL
        }
        pen.SetCap(capmap.get(self.state.get('stroke-linecap', None), wx.CAP_BUTT))
        pen.SetJoin(joinmap.get(self.state.get('stroke-linejoin', None), wx.JOIN_MITER))
        return wx.GraphicsRenderer_GetDefaultRenderer().CreatePen(pen)

    def getBrushFromState(self, path = None):
        brushcolour = self.state.get('fill', 'black').strip()
        type, details = paintValue.parseString(brushcolour)
        if type == "URL":
            url, fallback = details
            element = self.resolveURL(url)
            if not element:
                if fallback:
                    type, details = fallback
                else:
                    r, g, b, = 0, 0, 0
            else:
                if element.tag == '{http://www.w3.org/2000/svg}linearGradient':
                    box = path.GetBox()
                    x, y, w, h = box.Get()
                    return wx.GraphicsRenderer.GetDefaultRenderer().CreateLinearGradientBrush(
                        x, y, x+w, y+h, wx.Colour(0, 0, 255, 128), wx.RED
                    )
                elif element.tag == '{http://www.w3.org/2000/svg}radialGradient':
                    box = path.GetBox()
                    x, y, w, h = box.Get()
                    #print w
                    mx = wx.GraphicsRenderer.GetDefaultRenderer().CreateMatrix(x, y, w, h)
                    cx, cy = mx.TransformPoint(0.5, 0.5)
                    fx, fy = cx, cy
                    return wx.GraphicsRenderer.GetDefaultRenderer().CreateRadialGradientBrush(
                        cx, cy,
                        fx, fy,
                        (max(w, h))/2,
                        wx.Colour(0, 0, 255, 128), wx.RED
                    )
                else:
                    #invlid gradient specified
                    return wx.NullBrush
            r, g, b  = 0, 0, 0
        if type == 'CURRENTCOLOR':
            type, details = paintValue.parseString(self.state.get('color', 'none'))
        if type == 'RGB':
            r, g, b = details
        elif type == "NONE":
            return wx.NullBrush
        opacity = self.state.get('fill-opacity', self.state.get('opacity', '1'))
        opacity = float(opacity)
        opacity = min(max(opacity, 0.0), 1.0)
        a = 255 * opacity
        #using try/except block instead of
        #just setdefault because the wxBrush and wxColour would
        #be created every time anyway in order to pass them,
        #defeating the purpose of the cache
        try:
            return SVGDocument.brushCache[(r, g, b, a)]
        except KeyError:
            return SVGDocument.brushCache.setdefault((r, g, b, a), wx.Brush(wx.Colour(r, g, b, a)))


    def resolveURL(self, urlData):
        """
            Resolve a URL and return an elementTree Element from it.

            Return None if unresolvable

        """
        scheme, netloc, path, query, fragment = urlData
        if scheme == netloc == path == '':
            #horrible. There's got to be a better way?
            if self.tree.get("id") == fragment:
                return self.tree
            else:
                for child in self.tree.getiterator():
                    #print child.get("id")
                    if child.get("id") == fragment:
                        return child
            return None
        else:
            return self.resolveRemoteURL(urlData)

    def resolveRemoteURL(self, url):
        return None

    def addStrokeToPath(self, path, stroke):
        """ Given a stroke from a path command
        (in the form (command, arguments)) create the path
        commands that represent it.

        TODO: break out into (yet another) class/module,
        especially so we can get O(1) dispatch on type?
        """
        type, arg = stroke
        relative = False
        if type == type.lower():
            relative = True
            ox, oy = path.GetCurrentPoint().Get()
        else:
            ox = oy = 0
        def normalizePoint(arg):
            x, y = arg
            return x+ox, y+oy
        def reflectPoint(point, relativeTo):
            x, y = point
            a, b = relativeTo
            return ((a*2)-x), ((b*2)-y)
        type = type.upper()
        if type == 'M':
            pt = normalizePoint(arg)
            self.firstPoints.append(pt)
            path.MoveToPoint(pt)
        elif type == 'L':
            path.AddLineToPoint(normalizePoint(arg))
        elif type == 'C':
            #control1, control2, endpoint = arg
            control1, control2, endpoint = map(
                normalizePoint, arg
            )
            self.lastControl = control2
            path.AddCurveToPoint(
                control1,
                control2,
                endpoint
            )
            #~ cp = path.GetCurrentPoint()
            #~ path.AddCircle(c1x, c1y, 5)
            #~ path.AddCircle(c2x, c2y, 3)
            #~ path.AddCircle(x, y, 7)
            #~ path.MoveToPoint(cp)
            #~ print "C", control1, control2, endpoint

        elif type == 'S':
            #control2, endpoint = arg
            control2, endpoint = map(
                normalizePoint, arg
            )
            if self.lastControl:
                control1 = reflectPoint(self.lastControl, path.GetCurrentPoint())
            else:
                control1 = path.GetCurrentPoint()
            #~ print "S", self.lastControl, ":", control1, control2, endpoint
            self.lastControl = control2
            path.AddCurveToPoint(
                control1,
                control2,
                endpoint
            )
        elif type == "Q":
            (cx, cy), (x, y) = map(normalizePoint, arg)
            self.lastControlQ = (cx, cy)
            path.AddQuadCurveToPoint(cx, cy, x, y)
        elif type == "T":
            x, y, = normalizePoint(arg)
            if self.lastControlQ:
                cx, cy = reflectPoint(self.lastControlQ, path.GetCurrentPoint())
            else:
                cx, cy = path.GetCurrentPoint()
            self.lastControlQ = (cx, cy)
            path.AddQuadCurveToPoint(cx, cy, x, y)

        elif type == "V":
            _, y = normalizePoint((0, arg))
            x, _ = path.GetCurrentPoint()
            path.AddLineToPoint(x, y)

        elif type == "H":
            x, _ = normalizePoint((arg, 0))
            _, y = path.GetCurrentPoint()
            path.AddLineToPoint(x, y)

        elif type == "A":
            #wxGC currently only supports circular arcs,
            #not eliptical ones

            (
            (rx, ry), #radii of ellipse
            angle, #angle of rotation on the ellipse in degrees
            (fa, fs), #arc and stroke angle flags
            (x, y) #endpoint on the arc
            ) = arg

            x, y = normalizePoint((x, y))
            cx, cy = path.GetCurrentPoint()
            if (cx, cy) == (x, y):
                return #noop

            if (rx == 0 or ry == 0):
                #no radius is effectively a line
                path.AddLineToPoint(x, y)
                return

            #find the center point for the ellipse
            #translation via the angle
            angle = angle % 360
            angle = math.radians(angle)

            #translated endpoint
            xPrime = math.cos(angle) * ((cx-x)/2)
            xPrime += math.sin(angle) * ((cx-x)/2)
            yPrime = -(math.sin(angle)) * ((cy-y)/2)
            yPrime += (math.cos(angle)) * ((cy-y)/2)


            temp = ((rx**2) * (ry**2)) - ((rx**2) * (yPrime**2)) - ((ry**2) * (xPrime**2))
            temp /= ((rx**2) * (yPrime**2)) + ((ry**2)*(xPrime**2))
            temp = abs(temp)
            try:
                temp = math.sqrt(temp)
            except ValueError:
                import pdb
                pdb.set_trace()
            cxPrime = temp * ((rx * yPrime) / ry)
            cyPrime = temp * -((ry * xPrime) / rx)
            if fa == fs:
                cxPrime, cyPrime = -cxPrime, -cyPrime

            #reflect backwards now for the origin
            cnx = math.cos(angle) * cxPrime
            cnx += math.sin(angle) * cxPrime
            cny = -(math.sin(angle)) * cyPrime
            cny += (math.cos(angle)) * cyPrime
            cnx += ((cx+x)/2.0)
            cny += ((cy+y)/2.0)

            #calculate the angle between the two endpoints
            lastArc = wx.Point2D(x-cnx, y-cny).GetVectorAngle()
            firstArc = wx.Point2D(cx-cnx, cy-cny).GetVectorAngle()
            lastArc = math.radians(lastArc)
            firstArc = math.radians(firstArc)


            #aargh buggines.
            #AddArc draws a straight line between
            #the endpoints of the arc.
            #putting it in a subpath makes the strokes come out
            #correctly, but it still only fills the slice
            #taking out the MoveToPoint fills correctly.
            path.AddEllipse(cnx-rx, cny-ry, rx*2, ry*2)
            path.MoveToPoint(x, y)
            #~ npath = makePath()
            #~ npath.AddEllipticalArc(cnx-rx, cny-ry, rx*2, ry*2, firstArc, lastArc, False)
            #~ npath.MoveToPoint(x, y)
            #~ path.AddPath(npath)

        elif type == 'Z':
            #~ Bugginess:
            #~ CloseSubpath() doesn't change the
            #~ current point, as SVG spec requires.
            #~ However, manually moving to the endpoint afterward opens a new subpath
            #~ and (apparently) messes with stroked but not filled paths.
            #~ This is possibly a bug in GDI+?
            #~ Manually closing the path via AddLineTo gives incorrect line join
            #~ results
            #~ Manually closing the path *and* calling CloseSubpath() appears
            #~ to give correct results on win32

            pt = self.firstPoints.pop()
            path.AddLineToPoint(pt)
            path.CloseSubpath()

    def render(self, context):
        if not hasattr(self, "ops"):
            return
        for op, args in self.ops:
            op(context, *args)

if __name__ == '__main__':
    from tests.test_document import *
    unittest.main()
