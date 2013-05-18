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
import wx, time
from printrun import gcoder

from printrun_utils import imagefile

ID_ABOUT = 101
ID_EXIT = 110
class window(wx.Frame):
    def __init__(self, f, size = (600, 600), build_dimensions = [200, 200, 100, 0, 0, 0], grid = (10, 50), extrusion_width = 0.5):
        wx.Frame.__init__(self, None, title = "Gcode view, shift to move view, mousewheel to set layer", size = size)

        self.CreateStatusBar(1);
        self.SetStatusText("Layer number and Z position show here when you scroll");

        panel = wx.Panel(self, -1)
        self.p = gviz(panel, size = size, build_dimensions = build_dimensions, grid = grid, extrusion_width = extrusion_width, realparent = self)

        vbox = wx.BoxSizer(wx.VERTICAL)
        toolbar = wx.ToolBar(panel, -1, style = wx.TB_HORIZONTAL | wx.NO_BORDER)
        toolbar.AddSimpleTool(1, wx.Image(imagefile('zoom_in.png'), wx.BITMAP_TYPE_PNG).ConvertToBitmap(), 'Zoom In [+]', '')
        toolbar.AddSimpleTool(2, wx.Image(imagefile('zoom_out.png'), wx.BITMAP_TYPE_PNG).ConvertToBitmap(), 'Zoom Out [-]', '')
        toolbar.AddSeparator()
        toolbar.AddSimpleTool(3, wx.Image(imagefile('arrow_up.png'), wx.BITMAP_TYPE_PNG).ConvertToBitmap(), 'Move Up a Layer [U]', '')
        toolbar.AddSimpleTool(4, wx.Image(imagefile('arrow_down.png'), wx.BITMAP_TYPE_PNG).ConvertToBitmap(), 'Move Down a Layer [D]', '')
        toolbar.AddSimpleTool(5, wx.Image(imagefile('reset.png'), wx.BITMAP_TYPE_PNG).ConvertToBitmap(), 'Reset view', '')
        toolbar.AddSeparator()
        #toolbar.AddSimpleTool(6, wx.Image(imagefile('inject.png'), wx.BITMAP_TYPE_PNG).ConvertToBitmap(), 'Insert Code at start of this layer', '')
        toolbar.Realize()
        vbox.Add(toolbar, 0, border = 5)
        vbox.Add(self.p, 1, wx.EXPAND)
        panel.SetSizer(vbox)
        self.SetMinSize(self.ClientToWindowSize(vbox.GetMinSize()))
        self.Bind(wx.EVT_TOOL, lambda x:self.p.zoom(-1, -1, 1.2), id = 1)
        self.Bind(wx.EVT_TOOL, lambda x:self.p.zoom(-1, -1, 1/1.2), id = 2)
        self.Bind(wx.EVT_TOOL, lambda x:self.p.layerup(), id = 3)
        self.Bind(wx.EVT_TOOL, lambda x:self.p.layerdown(), id = 4)
        self.Bind(wx.EVT_TOOL, self.resetview, id = 5)
        #self.Bind(wx.EVT_TOOL, lambda x:self.p.inject(), id = 6)

        self.initpos = [0, 0]
        self.p.Bind(wx.EVT_KEY_DOWN, self.key)
        self.Bind(wx.EVT_KEY_DOWN, self.key)
        self.p.Bind(wx.EVT_MOUSEWHEEL, self.zoom)
        self.Bind(wx.EVT_MOUSEWHEEL, self.zoom)
        self.p.Bind(wx.EVT_MOUSE_EVENTS, self.mouse)
        self.Bind(wx.EVT_MOUSE_EVENTS, self.mouse)

        if f:
            gcode = gcoder.GCode(f)
            self.p.addfile(gcode)

    def resetview(self, event):
        self.p.translate = [0.0, 0.0]
        self.p.scale = self.p.basescale
        self.p.zoom(0, 0, 1.0)

    def mouse(self, event):
        if event.ButtonUp(wx.MOUSE_BTN_LEFT):
            if self.initpos is not None:
                self.initpos = None
        elif event.Dragging():
            e = event.GetPositionTuple()
            if self.initpos is None or not hasattr(self, "basetrans"):
                self.initpos = e
                self.basetrans = self.p.translate
            self.p.translate = [self.basetrans[0] + (e[0] - self.initpos[0]),
                                self.basetrans[1] + (e[1] - self.initpos[1])]
            self.p.dirty = 1
            wx.CallAfter(self.p.Refresh)
        else:
            event.Skip()

    def key(self, event):
        #  Keycode definitions
        kup = [85, 315]               # Up keys
        kdo = [68, 317]               # Down Keys
        kzi = [388, 316, 61]        # Zoom In Keys
        kzo = [390, 314, 45]       # Zoom Out Keys
        x = event.GetKeyCode()
        cx, cy = self.p.translate
        if x in kup:
            self.p.layerup()
        if x in kdo:
            self.p.layerdown()
        if x in kzi:
            self.p.zoom(cx, cy, 1.2)
        if x in kzo:
            self.p.zoom(cx, cy, 1/1.2)

    def zoom(self, event):
        z = event.GetWheelRotation()
        if event.ShiftDown():
            if z > 0:   self.p.layerdown()
            elif z < 0: self.p.layerup()
        else:
            if z > 0:   self.p.zoom(event.GetX(), event.GetY(), 1.2)
            elif z < 0: self.p.zoom(event.GetX(), event.GetY(), 1/1.2)

class gviz(wx.Panel):

    # Mark canvas as dirty when setting showall
    _showall = 0
    def _get_showall(self):
        return self._showall
    def _set_showall(self, showall):
        if showall != self._showall:
            self.dirty = 1
            self._showall = showall
    showall = property(_get_showall, _set_showall)

    def __init__(self, parent, size = (200, 200), build_dimensions = [200, 200, 100, 0, 0, 0], grid = (10, 50), extrusion_width = 0.5, realparent = None):
        wx.Panel.__init__(self, parent, -1, size = size)
        self.SetMinSize((150, 150))
        self.parent = realparent if realparent else parent
        self.size = size
        self.build_dimensions = build_dimensions
        self.grid = grid
        self.lastpos = [0, 0, 0, 0, 0, 0, 0]
        self.hilightpos = self.lastpos[:]
        self.Bind(wx.EVT_PAINT, self.paint)
        self.Bind(wx.EVT_SIZE, self.resize)
        self.lines = {}
        self.pens = {}
        self.arcs = {}
        self.arcpens = {}
        self.layers = []
        self.layerindex = 0
        self.filament_width = extrusion_width # set it to 0 to disable scaling lines with zoom
        self.update_basescale()
        self.scale = self.basescale
        penwidth = max(1.0, self.filament_width*((self.scale[0]+self.scale[1])/2.0))
        self.translate = [0.0, 0.0]
        self.mainpen = wx.Pen(wx.Colour(0, 0, 0), penwidth)
        self.arcpen = wx.Pen(wx.Colour(255, 0, 0), penwidth)
        self.travelpen = wx.Pen(wx.Colour(10, 80, 80), penwidth)
        self.hlpen = wx.Pen(wx.Colour(200, 50, 50), penwidth)
        self.fades = [wx.Pen(wx.Colour(250-0.6**i*100, 250-0.6**i*100, 200-0.4**i*50), penwidth) for i in xrange(6)]
        self.penslist = [self.mainpen, self.travelpen, self.hlpen]+self.fades
        self.showall = 0
        self.hilight = []
        self.hilightarcs = []
        self.dirty = 1
        self.blitmap = wx.EmptyBitmap(self.GetClientSize()[0], self.GetClientSize()[1],-1)

    def inject(self):
        #import pdb; pdb.set_trace()
        print"Inject code here..."
        print  "Layer "+str(self.layerindex +1)+" - Z = "+str(self.layers[self.layerindex])+" mm"

    def clear(self):
        self.lastpos = [0, 0, 0, 0, 0, 0, 0]
        self.lines = {}
        self.pens = {}
        self.arcs = {}
        self.arcpens = {}
        self.layers = []
        self.hilight = []
        self.hilightarcs = []
        self.layerindex = 0
        self.showall = 0
        self.dirty = 1
        wx.CallAfter(self.Refresh)

    def layerup(self):
        if(self.layerindex+1<len(self.layers)):
            self.layerindex+=1
            # Display layer info on statusbar (Jezmy)
            self.parent.SetStatusText("Layer "+str(self.layerindex +1)+" - Going Up - Z = "+str(self.layers[self.layerindex])+" mm", 0)
            self.dirty = 1
            wx.CallAfter(self.Refresh)

    def layerdown(self):
        if(self.layerindex>0):
            self.layerindex-=1
            # Display layer info on statusbar (Jezmy)
            self.parent.SetStatusText("Layer "+str(self.layerindex + 1)+" - Going Down - Z = "+str(self.layers[self.layerindex])+ " mm", 0)
            self.dirty = 1
            wx.CallAfter(self.Refresh)

    def setlayer(self, layer):
        try:
            self.layerindex = self.layers.index(layer)
            self.dirty = 1
            wx.CallAfter(self.Refresh)
            self.showall = 0
        except:
            pass

    def update_basescale(self):
        self.basescale = 2*[min(float(self.size[0] - 1)/self.build_dimensions[0],
                                float(self.size[1] - 1)/self.build_dimensions[1])]

    def resize(self, event):
        oldside = max(1.0, min(self.size))
        self.size = self.GetClientSizeTuple()
        self.update_basescale()
        newside = max(1.0, min(self.size))
        zoomratio = float(newside) / oldside
        wx.CallAfter(self.zoom, 0, 0, zoomratio)

    def zoom(self, x, y, factor):
        if x == -1 and y == -1:
            side = min(self.size)
            x = y = side / 2
        self.scale = [s * factor for s in self.scale]

        self.translate = [ x - (x-self.translate[0]) * factor,
                            y - (y-self.translate[1]) * factor]
        penwidth = max(1.0, self.filament_width*((self.scale[0]+self.scale[1])/2.0))
        for pen in self.penslist:
            pen.SetWidth(penwidth)
        self.dirty = 1
        wx.CallAfter(self.Refresh)
    
    def _line_scaler(self, x):
        return (self.scale[0]*x[0]+self.translate[0],
                self.scale[1]*x[1]+self.translate[1],
                self.scale[0]*x[2]+self.translate[0],
                self.scale[1]*x[3]+self.translate[1],)
    
    def _arc_scaler(self, x):
        return (self.scale[0]*x[0]+self.translate[0],
                self.scale[1]*x[1]+self.translate[1],
                self.scale[0]*x[2]+self.translate[0],
                self.scale[1]*x[3]+self.translate[1],
                self.scale[0]*x[4]+self.translate[0],
                self.scale[1]*x[5]+self.translate[1],)

    def repaint(self):
        self.blitmap = wx.EmptyBitmap(self.GetClientSize()[0], self.GetClientSize()[1],-1)
        dc = wx.MemoryDC()
        dc.SelectObject(self.blitmap)
        dc.SetBackground(wx.Brush((250, 250, 200)))
        dc.Clear()
        dc.SetPen(wx.Pen(wx.Colour(180, 180, 150)))
        for grid_unit in self.grid:
            if grid_unit > 0:
                for x in xrange(int(self.build_dimensions[0]/grid_unit)+1):
                    dc.DrawLine(self.translate[0]+x*self.scale[0]*grid_unit, self.translate[1], self.translate[0]+x*self.scale[0]*grid_unit, self.translate[1]+self.scale[1]*self.build_dimensions[1])
                for y in xrange(int(self.build_dimensions[1]/grid_unit)+1):
                    dc.DrawLine(self.translate[0], self.translate[1]+y*self.scale[1]*grid_unit, self.translate[0]+self.scale[0]*self.build_dimensions[0], self.translate[1]+y*self.scale[1]*grid_unit)
            dc.SetPen(wx.Pen(wx.Colour(0, 0, 0)))

        if not self.showall:
            dc.SetBrush(wx.Brush((43, 144, 255)))
            dc.DrawRectangle(self.size[0]-15, 0, 15, self.size[1])
            dc.SetBrush(wx.Brush((0, 255, 0)))
            if len(self.layers):
                dc.DrawRectangle(self.size[0]-14, (1.0-(1.0*(self.layerindex+1))/len(self.layers))*self.size[1], 13, self.size[1]-1)

        def _drawlines(lines, pens):
            scaled_lines = map(self._line_scaler, lines)
            dc.DrawLineList(scaled_lines, pens)

        def _drawarcs(arcs, pens):
            scaled_arcs = map(self._arc_scaler, arcs)
            dc.SetBrush(wx.TRANSPARENT_BRUSH)
            for i in range(len(scaled_arcs)):
                dc.SetPen(pens[i] if type(pens) == list else pens)
                dc.DrawArc(*scaled_arcs[i])

        if self.showall:
            l = []
            for i in self.layers:
                dc.DrawLineList(l, self.fades[0])
                _drawlines(self.lines[i], self.pens[i])
                _drawarcs(self.arcs[i], self.arcpens[i])
            return

        if self.layerindex<len(self.layers) and self.layers[self.layerindex] in self.lines.keys():
            for layer_i in xrange(max(0, self.layerindex-6), self.layerindex):
                #print i, self.layerindex, self.layerindex-i
                _drawlines(self.lines[self.layers[layer_i]], self.fades[self.layerindex-layer_i-1])
                _drawarcs(self.arcs[self.layers[layer_i]], self.fades[self.layerindex-layer_i-1])
            _drawlines(self.lines[self.layers[self.layerindex]], self.pens[self.layers[self.layerindex]])
            _drawarcs(self.arcs[self.layers[self.layerindex]], self.arcpens[self.layers[self.layerindex]])

        _drawlines(self.hilight, self.hlpen)
        _drawarcs(self.hilightarcs, self.hlpen)

        dc.SelectObject(wx.NullBitmap)

    def paint(self, event):
        dc = wx.PaintDC(self)
        if self.dirty:
            self.dirty = 0
            self.repaint()
        dc.DrawBitmap(self.blitmap, 0, 0)

    def addfile(self, gcode):
        self.clear()
        self.add_parsed_gcodes(gcode.lines)

    # FIXME : there's code duplication going on there, we should factor it (but
    # the reason addgcode is not factored as a add_parsed_gcodes([gline]) is
    # because when loading a file there's no hilight, so it simply lets us not
    # do the if hilight: all the time for nothing when loading a lot of lines
    def add_parsed_gcodes(self, lines):
        def _y(y):
            return self.build_dimensions[1] - (y - self.build_dimensions[4])
        def _x(x):
            return x - self.build_dimensions[3]

        for gline in lines:
            if gline.command not in ["G0", "G1", "G2", "G3"]:
                continue
            
            target = self.lastpos[:]
            target[5] = 0.0
            target[6] = 0.0
            if gline.relative:
                if gline.x != None: target[0] += gline.x
                if gline.y != None: target[1] += gline.y
                if gline.z != None: target[2] += gline.z
            else:
                if gline.x != None: target[0] = gline.x
                if gline.y != None: target[1] = gline.y
                if gline.z != None: target[2] = gline.z
            if gline.e != None:
                if gline.relative_e:
                    target[3] += gline.e
                else:
                    target[3] = gline.e
            if gline.f != None: target[4] = gline.f
            if gline.i != None: target[5] = gline.i
            if gline.j != None: target[6] = gline.j
            z = target[2]
            if z not in self.layers:
                self.lines[z] = []
                self.pens[z] = []
                self.arcs[z] = []
                self.arcpens[z] = []
                self.layers.append(z)
            
            start_pos = self.lastpos[:]

            if gline.command in ["G0", "G1"]:
                self.lines[z].append((_x(start_pos[0]), _y(start_pos[1]), _x(target[0]), _y(target[1])))
                self.pens[z].append(self.mainpen if target[3] != self.lastpos[3] else self.travelpen)
            elif gline.command in ["G2", "G3"]:
                # startpos, endpos, arc center
                arc = [_x(start_pos[0]), _y(start_pos[1]),
                       _x(target[0]), _y(target[1]),
                       _x(start_pos[0] + target[5]), _y(start_pos[1] + target[6])]
                # FIXME : verify this works : why not reverse endpoints 4, 5
                if gline.command == "G2":  # clockwise, reverse endpoints
                    arc[0], arc[1], arc[2], arc[3] = arc[2], arc[3], arc[0], arc[1]

                self.arcs[z].append(arc)
                self.arcpens[z].append(self.arcpen)

            self.lastpos = target
        self.dirty = 1
        self.Refresh()

    def addgcode(self, gcode = "M105", hilight = 0):
        gcode = gcode.split("*")[0]
        gcode = gcode.split(";")[0]
        gcode = gcode.lower().strip()
        if not gcode:
            return
        gline = gcoder.Line(gcode)
        gline.parse_coordinates(False)

        def _y(y):
            return self.build_dimensions[1] - (y - self.build_dimensions[4])
        def _x(x):
            return x - self.build_dimensions[3]

        start_pos = self.hilightpos[:] if hilight else self.lastpos[:]

        if gline.command not in ["G0", "G1", "G2", "G3"]:
            return
        
        target = self.hilightpos[:] if hilight else self.lastpos[:]
        target[5] = 0.0
        target[6] = 0.0
        if gline.x != None: target[0] = gline.x
        if gline.y != None: target[1] = gline.y
        if gline.z != None: target[2] = gline.z
        if gline.e != None: target[3] = gline.e
        if gline.f != None: target[4] = gline.f
        if gline.i != None: target[5] = gline.i
        if gline.j != None: target[6] = gline.j

        z = target[2]
        if not hilight and z not in self.layers:
            self.lines[z] = []
            self.pens[z] = []
            self.arcs[z] = []
            self.arcpens[z] = []
            self.layers.append(z)

        if gline.command in ["G0", "G1"]:
            line = [_x(start_pos[0]), _y(start_pos[1]), _x(target[0]), _y(target[1])]
            if not hilight:
                self.lines[z].append((_x(start_pos[0]), _y(start_pos[1]), _x(target[0]), _y(target[1])))
                self.pens[z].append(self.mainpen if target[3] != self.lastpos[3] else self.travelpen)
            else:
                self.hilight.append(line)
        elif gline.command in ["G2", "G3"]:
            # startpos, endpos, arc center
            arc = [_x(start_pos[0]), _y(start_pos[1]),
                   _x(target[0]), _y(target[1]),
                   _x(start_pos[0] + target[5]), _y(start_pos[1] + target[6])]
            if gline.command == "G2":  # clockwise, reverse endpoints
                arc[0], arc[1], arc[2], arc[3] = arc[2], arc[3], arc[0], arc[1]

                self.arcs[z].append(arc)
                self.arcpens[z].append(self.arcpen)
            else:
                self.hilightarcs.append(arc)

        if not hilight:
            self.lastpos = target
        else:
            self.hilightpos = target
        self.dirty = 1
        self.Refresh()

if __name__ == '__main__':
    import sys
    app = wx.App(False)
    main = window(open(sys.argv[1]))
    main.Show()
    app.MainLoop()
