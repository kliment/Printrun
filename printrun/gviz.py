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

from Queue import Queue
from collections import deque
import wx
import time
from printrun import gcoder

from printrun_utils import imagefile, install_locale, get_home_pos
install_locale('pronterface')

class GvizBaseFrame(wx.Frame):

    def create_base_ui(self):
        self.CreateStatusBar(1)
        self.SetStatusText(_("Layer number and Z position show here when you scroll"))

        hpanel = wx.Panel(self, -1)
        hbox = wx.BoxSizer(wx.HORIZONTAL)

        panel = wx.Panel(hpanel, -1)
        vbox = wx.BoxSizer(wx.VERTICAL)

        vbox = wx.BoxSizer(wx.VERTICAL)
        self.toolbar = wx.ToolBar(panel, -1, style = wx.TB_HORIZONTAL | wx.NO_BORDER | wx.TB_HORZ_TEXT)
        self.toolbar.AddSimpleTool(1, wx.Image(imagefile('zoom_in.png'), wx.BITMAP_TYPE_PNG).ConvertToBitmap(), _("Zoom In [+]"), '')
        self.toolbar.AddSimpleTool(2, wx.Image(imagefile('zoom_out.png'), wx.BITMAP_TYPE_PNG).ConvertToBitmap(), _("Zoom Out [-]"), '')
        self.toolbar.AddSeparator()
        self.toolbar.AddSimpleTool(3, wx.Image(imagefile('arrow_up.png'), wx.BITMAP_TYPE_PNG).ConvertToBitmap(), _("Move Up a Layer [U]"), '')
        self.toolbar.AddSimpleTool(4, wx.Image(imagefile('arrow_down.png'), wx.BITMAP_TYPE_PNG).ConvertToBitmap(), _("Move Down a Layer [D]"), '')
        self.toolbar.AddLabelTool(5, " " + _("Reset view"), wx.Image(imagefile('reset.png'), wx.BITMAP_TYPE_PNG).ConvertToBitmap(), shortHelp = _("Reset view"), longHelp = '')

        vbox.Add(self.toolbar, 0, border = 5)

        panel.SetSizer(vbox)

        hbox.Add(panel, 1, flag = wx.EXPAND)
        self.layerslider = wx.Slider(hpanel, style = wx.SL_VERTICAL | wx.SL_AUTOTICKS | wx.SL_LEFT | wx.SL_INVERSE)
        self.layerslider.Bind(wx.EVT_SCROLL, self.process_slider)
        hbox.Add(self.layerslider, 0, border = 5, flag = wx.LEFT | wx.EXPAND)
        hpanel.SetSizer(hbox)

        return panel, vbox

    def setlayercb(self, layer):
        self.layerslider.SetValue(layer)

    def process_slider(self, event):
        raise NotImplementedError

ID_ABOUT = 101
ID_EXIT = 110
class GvizWindow(GvizBaseFrame):
    def __init__(self, f = None, size = (600, 600), build_dimensions = [200, 200, 100, 0, 0, 0], grid = (10, 50), extrusion_width = 0.5, bgcolor = "#000000"):
        super(GvizWindow, self).__init__(None, title = _("Gcode view, shift to move view, mousewheel to set layer"), size = size)

        panel, vbox = self.create_base_ui()

        self.p = Gviz(panel, size = size, build_dimensions = build_dimensions, grid = grid, extrusion_width = extrusion_width, bgcolor = bgcolor, realparent = self)

        self.toolbar.AddSeparator()
        #self.toolbar.AddSimpleTool(6, wx.Image(imagefile('inject.png'), wx.BITMAP_TYPE_PNG).ConvertToBitmap(), _("Insert Code at start of this layer"), '')
        self.toolbar.Realize()
        vbox.Add(self.p, 1, wx.EXPAND)

        self.SetMinSize(self.ClientToWindowSize(vbox.GetMinSize()))
        self.Bind(wx.EVT_TOOL, lambda x: self.p.zoom(-1, -1, 1.2), id = 1)
        self.Bind(wx.EVT_TOOL, lambda x: self.p.zoom(-1, -1, 1 / 1.2), id = 2)
        self.Bind(wx.EVT_TOOL, lambda x: self.p.layerup(), id = 3)
        self.Bind(wx.EVT_TOOL, lambda x: self.p.layerdown(), id = 4)
        self.Bind(wx.EVT_TOOL, self.resetview, id = 5)
        #self.Bind(wx.EVT_TOOL, lambda x:self.p.inject(), id = 6)

        self.initpos = None
        self.p.Bind(wx.EVT_KEY_DOWN, self.key)
        self.Bind(wx.EVT_KEY_DOWN, self.key)
        self.p.Bind(wx.EVT_MOUSEWHEEL, self.zoom)
        self.Bind(wx.EVT_MOUSEWHEEL, self.zoom)
        self.p.Bind(wx.EVT_MOUSE_EVENTS, self.mouse)
        self.Bind(wx.EVT_MOUSE_EVENTS, self.mouse)

        if f:
            gcode = gcoder.GCode(f, get_home_pos(self.p.build_dimensions))
            self.p.addfile(gcode)

    def set_current_gline(self, gline):
        return

    def process_slider(self, event):
        self.p.layerindex = self.layerslider.GetValue()
        z = self.p.get_currentz()
        self.SetStatusText(_("Layer %d - Going Up - Z = %.03f mm") % (self.p.layerindex + 1, z), 0)
        self.p.dirty = 1
        wx.CallAfter(self.p.Refresh)

    def resetview(self, event):
        self.p.translate = [0.0, 0.0]
        self.p.scale = self.p.basescale
        self.p.zoom(0, 0, 1.0)

    def mouse(self, event):
        if event.ButtonUp(wx.MOUSE_BTN_LEFT) or event.ButtonUp(wx.MOUSE_BTN_RIGHT):
            if self.initpos is not None:
                self.initpos = None
        elif event.Dragging():
            e = event.GetPositionTuple()
            if self.initpos is None:
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
            self.p.zoom(cx, cy, 1 / 1.2)

    def zoom(self, event):
        z = event.GetWheelRotation()
        if event.ShiftDown():
            if z > 0: self.p.layerdown()
            elif z < 0: self.p.layerup()
        else:
            if z > 0: self.p.zoom(event.GetX(), event.GetY(), 1.2)
            elif z < 0: self.p.zoom(event.GetX(), event.GetY(), 1 / 1.2)

class Gviz(wx.Panel):

    # Mark canvas as dirty when setting showall
    _showall = 0

    def _get_showall(self):
        return self._showall

    def _set_showall(self, showall):
        if showall != self._showall:
            self.dirty = 1
            self._showall = showall
    showall = property(_get_showall, _set_showall)

    def __init__(self, parent, size = (200, 200), build_dimensions = [200, 200, 100, 0, 0, 0], grid = (10, 50), extrusion_width = 0.5, bgcolor = "#000000", realparent = None):
        wx.Panel.__init__(self, parent, -1)
        self.widget = self
        size = [max(1.0, x) for x in size]
        ratio = size[0] / size[1]
        self.SetMinSize((150, 150 / ratio))
        self.parent = realparent if realparent else parent
        self.size = size
        self.build_dimensions = build_dimensions
        self.grid = grid
        self.Bind(wx.EVT_PAINT, self.paint)
        self.Bind(wx.EVT_SIZE, self.resize)
        self.hilight = deque()
        self.hilightarcs = deque()
        self.hilightqueue = Queue(0)
        self.hilightarcsqueue = Queue(0)
        self.clear()
        self.filament_width = extrusion_width  # set it to 0 to disable scaling lines with zoom
        self.update_basescale()
        self.scale = self.basescale
        penwidth = max(1.0, self.filament_width * ((self.scale[0] + self.scale[1]) / 2.0))
        self.translate = [0.0, 0.0]
        self.mainpen = wx.Pen(wx.Colour(0, 0, 0), penwidth)
        self.arcpen = wx.Pen(wx.Colour(255, 0, 0), penwidth)
        self.travelpen = wx.Pen(wx.Colour(10, 80, 80), penwidth)
        self.hlpen = wx.Pen(wx.Colour(200, 50, 50), penwidth)
        self.fades = [wx.Pen(wx.Colour(250 - 0.6 ** i * 100, 250 - 0.6 ** i * 100, 200 - 0.4 ** i * 50), penwidth) for i in xrange(6)]
        self.penslist = [self.mainpen, self.travelpen, self.hlpen] + self.fades
        self.bgcolor = wx.Colour()
        self.bgcolor.SetFromName(bgcolor)
        self.blitmap = wx.EmptyBitmap(self.GetClientSize()[0], self.GetClientSize()[1], -1)
        self.paint_overlay = None

    def inject(self):
        #import pdb; pdb.set_trace()
        print "Inject code here..."
        print "Layer " + str(self.layerindex + 1) + " - Z = " + str(self.layers[self.layerindex]) + " mm"

    def clearhilights(self):
        self.hilight.clear()
        self.hilightarcs.clear()
        while not self.hilightqueue.empty():
            self.hilightqueue.get_nowait()
        while not self.hilightarcsqueue.empty():
            self.hilightarcsqueue.get_nowait()

    def clear(self):
        self.lastpos = [0, 0, 0, 0, 0, 0, 0]
        self.hilightpos = self.lastpos[:]
        self.gcoder = gcoder.GCode([], get_home_pos(self.build_dimensions))
        self.lines = {}
        self.pens = {}
        self.arcs = {}
        self.arcpens = {}
        self.layers = []
        self.clearhilights()
        self.layerindex = 0
        self.showall = 0
        self.dirty = 1
        wx.CallAfter(self.Refresh)

    def get_currentz(self):
        z = self.layers[self.layerindex]
        z = 0. if z is None else z
        return z

    def layerup(self):
        if self.layerindex + 1 < len(self.layers):
            self.layerindex += 1
            z = self.get_currentz()
            self.parent.SetStatusText(_("Layer %d - Going Up - Z = %.03f mm") % (self.layerindex + 1, z), 0)
            self.dirty = 1
            self.parent.setlayercb(self.layerindex)
            wx.CallAfter(self.Refresh)

    def layerdown(self):
        if self.layerindex > 0:
            self.layerindex -= 1
            z = self.get_currentz()
            self.parent.SetStatusText(_("Layer %d - Going Down - Z = %.03f mm") % (self.layerindex + 1, z), 0)
            self.dirty = 1
            self.parent.setlayercb(self.layerindex)
            wx.CallAfter(self.Refresh)

    def setlayer(self, layer):
        if layer in self.layers:
            self.layerindex = self.layers.index(layer)
            self.dirty = 1
            self.showall = 0
            wx.CallAfter(self.Refresh)

    def update_basescale(self):
        self.basescale = 2 * [min(float(self.size[0] - 1) / self.build_dimensions[0],
                                  float(self.size[1] - 1) / self.build_dimensions[1])]

    def resize(self, event):
        old_basescale = self.basescale
        self.size = self.GetClientSizeTuple()
        self.update_basescale()
        zoomratio = float(self.basescale[0]) / old_basescale[0]
        wx.CallLater(200, self.zoom, 0, 0, zoomratio)

    def zoom(self, x, y, factor):
        if x == -1 and y == -1:
            side = min(self.size)
            x = y = side / 2
        self.scale = [s * factor for s in self.scale]

        self.translate = [x - (x - self.translate[0]) * factor,
                          y - (y - self.translate[1]) * factor]
        penwidth = max(1.0, self.filament_width * ((self.scale[0] + self.scale[1]) / 2.0))
        for pen in self.penslist:
            pen.SetWidth(penwidth)
        self.dirty = 1
        wx.CallAfter(self.Refresh)

    def _line_scaler(self, x):
        return (self.scale[0] * x[0],
                self.scale[1] * x[1],
                self.scale[0] * x[2],
                self.scale[1] * x[3],)

    def _arc_scaler(self, x):
        return (self.scale[0] * x[0],
                self.scale[1] * x[1],
                self.scale[0] * x[2],
                self.scale[1] * x[3],
                self.scale[0] * x[4],
                self.scale[1] * x[5],)

    def _drawlines(self, dc, lines, pens):
        scaled_lines = map(self._line_scaler, lines)
        dc.DrawLineList(scaled_lines, pens)

    def _drawarcs(self, dc, arcs, pens):
        scaled_arcs = map(self._arc_scaler, arcs)
        dc.SetBrush(wx.TRANSPARENT_BRUSH)
        for i in range(len(scaled_arcs)):
            dc.SetPen(pens[i] if type(pens) == list else pens)
            dc.DrawArc(*scaled_arcs[i])

    def repaint_everything(self):
        width = self.scale[0] * self.build_dimensions[0]
        height = self.scale[1] * self.build_dimensions[1]
        self.blitmap = wx.EmptyBitmap(width + 1, height + 1, -1)
        dc = wx.MemoryDC()
        dc.SelectObject(self.blitmap)
        dc.SetBackground(wx.Brush((250, 250, 200)))
        dc.Clear()
        dc.SetPen(wx.Pen(wx.Colour(180, 180, 150)))
        for grid_unit in self.grid:
            if grid_unit > 0:
                for x in xrange(int(self.build_dimensions[0] / grid_unit) + 1):
                    draw_x = self.scale[0] * x * grid_unit
                    dc.DrawLine(draw_x, 0, draw_x, height)
                for y in xrange(int(self.build_dimensions[1] / grid_unit) + 1):
                    draw_y = self.scale[1] * (self.build_dimensions[1] - y * grid_unit)
                    dc.DrawLine(0, draw_y, width, draw_y)
            dc.SetPen(wx.Pen(wx.Colour(0, 0, 0)))

        if not self.showall:
            # Draw layer gauge
            dc.SetBrush(wx.Brush((43, 144, 255)))
            dc.DrawRectangle(width - 15, 0, 15, height)
            dc.SetBrush(wx.Brush((0, 255, 0)))
            if self.layers:
                dc.DrawRectangle(width - 14, (1.0 - (1.0 * (self.layerindex + 1)) / len(self.layers)) * height, 13, height - 1)

        if self.showall:
            for i, _ in enumerate(self.layers):
                self._drawlines(dc, self.lines[i], self.pens[i])
                self._drawarcs(dc, self.arcs[i], self.arcpens[i])
            return

        if self.layerindex < len(self.layers) and self.layerindex in self.lines:
            for layer_i in range(max(0, self.layerindex - 6), self.layerindex):
                self._drawlines(dc, self.lines[layer_i], self.fades[self.layerindex - layer_i - 1])
                self._drawarcs(dc, self.arcs[layer_i], self.fades[self.layerindex - layer_i - 1])
            self._drawlines(dc, self.lines[self.layerindex], self.pens[self.layerindex])
            self._drawarcs(dc, self.arcs[self.layerindex], self.arcpens[self.layerindex])

        self._drawlines(dc, self.hilight, self.hlpen)
        self._drawarcs(dc, self.hilightarcs, self.hlpen)

        self.paint_hilights(dc)

        dc.SelectObject(wx.NullBitmap)

    def paint_hilights(self, dc = None):
        if self.hilightqueue.empty() and self.hilightarcsqueue.empty():
            return
        hl = []
        if not dc:
            dc = wx.MemoryDC()
            dc.SelectObject(self.blitmap)
        while not self.hilightqueue.empty():
            hl.append(self.hilightqueue.get_nowait())
        self._drawlines(dc, hl, self.hlpen)
        hlarcs = []
        while not self.hilightarcsqueue.empty():
            hlarcs.append(self.hilightarcsqueue.get_nowait())
        self._drawarcs(dc, hlarcs, self.hlpen)

    def paint(self, event):
        if self.dirty:
            self.dirty = 0
            self.repaint_everything()
        self.paint_hilights()
        dc = wx.PaintDC(self)
        dc.SetBackground(wx.Brush(self.bgcolor))
        dc.Clear()
        dc.DrawBitmap(self.blitmap, self.translate[0], self.translate[1])
        if self.paint_overlay:
            self.paint_overlay(dc)

    def addfile(self, gcode, showall = False):
        self.clear()
        self.showall = showall
        self.add_parsed_gcodes(gcode)
        max_layers = len(self.layers)
        if hasattr(self.parent, "layerslider"):
            self.parent.layerslider.SetRange(0, max_layers - 1)
            self.parent.layerslider.SetValue(0)

    # FIXME : there's code duplication going on there, we should factor it (but
    # the reason addgcode is not factored as a add_parsed_gcodes([gline]) is
    # because when loading a file there's no hilight, so it simply lets us not
    # do the if hilight: all the time for nothing when loading a lot of lines
    def add_parsed_gcodes(self, gcode):
        def _y(y):
            return self.build_dimensions[1] - (y - self.build_dimensions[4])

        def _x(x):
            return x - self.build_dimensions[3]

        start_time = time.time()

        for layer_idx, layer in enumerate(gcode.all_layers):
            has_move = False
            for gline in layer:
                if gline.is_move:
                    has_move = True
                    break
            if not has_move:
                continue
            viz_layer = len(self.layers)
            self.lines[viz_layer] = []
            self.pens[viz_layer] = []
            self.arcs[viz_layer] = []
            self.arcpens[viz_layer] = []
            for gline in layer:
                if not gline.is_move:
                    continue

                target = self.lastpos[:]
                target[0] = gline.current_x
                target[1] = gline.current_y
                target[2] = gline.current_z
                target[5] = 0.0
                target[6] = 0.0
                if gline.e is not None:
                    if gline.relative_e:
                        target[3] += gline.e
                    else:
                        target[3] = gline.e
                if gline.f is not None: target[4] = gline.f
                if gline.i is not None: target[5] = gline.i
                if gline.j is not None: target[6] = gline.j

                start_pos = self.lastpos[:]

                if gline.command in ["G0", "G1"]:
                    self.lines[viz_layer].append((_x(start_pos[0]), _y(start_pos[1]), _x(target[0]), _y(target[1])))
                    self.pens[viz_layer].append(self.mainpen if target[3] != self.lastpos[3] else self.travelpen)
                elif gline.command in ["G2", "G3"]:
                    # startpos, endpos, arc center
                    arc = [_x(start_pos[0]), _y(start_pos[1]),
                           _x(target[0]), _y(target[1]),
                           _x(start_pos[0] + target[5]), _y(start_pos[1] + target[6])]
                    if gline.command == "G2":  # clockwise, reverse endpoints
                        arc[0], arc[1], arc[2], arc[3] = arc[2], arc[3], arc[0], arc[1]

                    self.arcs[viz_layer].append(arc)
                    self.arcpens[viz_layer].append(self.arcpen)

                self.lastpos = target
            # Only add layer.z to self.layers now to prevent the display of an
            # unfinished layer
            self.layers.append(layer.z)
            # Refresh display if more than 0.2s have passed
            if time.time() - start_time > 0.2:
                start_time = time.time()
                self.dirty = 1
                wx.CallAfter(self.Refresh)
        self.dirty = 1
        wx.CallAfter(self.Refresh)

    def addgcode(self, gcode = "M105", hilight = 0):
        gcode = gcode.split("*")[0]
        gcode = gcode.split(";")[0]
        gcode = gcode.lower().strip()
        if not gcode:
            return
        gline = self.gcoder.append(gcode, store = False)

        def _y(y):
            return self.build_dimensions[1] - (y - self.build_dimensions[4])

        def _x(x):
            return x - self.build_dimensions[3]

        if gline.command not in ["G0", "G1", "G2", "G3"]:
            return

        start_pos = self.hilightpos[:] if hilight else self.lastpos[:]

        target = start_pos[:]
        target[5] = 0.0
        target[6] = 0.0
        if gline.current_x is not None: target[0] = gline.current_x
        if gline.current_y is not None: target[1] = gline.current_y
        if gline.current_z is not None: target[2] = gline.current_z
        if gline.e is not None: target[3] = gline.e
        if gline.f is not None: target[4] = gline.f
        if gline.i is not None: target[5] = gline.i
        if gline.j is not None: target[6] = gline.j

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
                self.hilightqueue.put_nowait(line)
        elif gline.command in ["G2", "G3"]:
            # startpos, endpos, arc center
            arc = [_x(start_pos[0]), _y(start_pos[1]),
                   _x(target[0]), _y(target[1]),
                   _x(start_pos[0] + target[5]), _y(start_pos[1] + target[6])]
            if gline.command == "G2":  # clockwise, reverse endpoints
                arc[0], arc[1], arc[2], arc[3] = arc[2], arc[3], arc[0], arc[1]

            if not hilight:
                self.arcs[z].append(arc)
                self.arcpens[z].append(self.arcpen)
            else:
                self.hilightarcs.append(arc)
                self.hilightarcsqueue.put_nowait(arc)

        if not hilight:
            self.lastpos = target
            self.dirty = 1
        else:
            self.hilightpos = target
        wx.CallAfter(self.Refresh)

if __name__ == '__main__':
    import sys
    app = wx.App(False)
    main = GvizWindow(open(sys.argv[1], "rU"))
    main.Show()
    app.MainLoop()
