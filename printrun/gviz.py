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

from queue import Queue
from collections import deque
import numpy
import wx
import time
from . import gcoder
from .injectgcode import injector, injector_edit

from .utils import imagefile, install_locale, get_home_pos
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
        self.toolbar.AddTool(1, '', wx.Image(imagefile('zoom_in.png'), wx.BITMAP_TYPE_PNG).ConvertToBitmap(), _("Zoom In [+]"),)
        self.toolbar.AddTool(2, '', wx.Image(imagefile('zoom_out.png'), wx.BITMAP_TYPE_PNG).ConvertToBitmap(), _("Zoom Out [-]"))
        self.toolbar.AddSeparator()
        self.toolbar.AddTool(3, '', wx.Image(imagefile('arrow_up.png'), wx.BITMAP_TYPE_PNG).ConvertToBitmap(), _("Move Up a Layer [U]"))
        self.toolbar.AddTool(4, '', wx.Image(imagefile('arrow_down.png'), wx.BITMAP_TYPE_PNG).ConvertToBitmap(), _("Move Down a Layer [D]"))
        self.toolbar.AddTool(5, " " + _("Reset view"), wx.Image(imagefile('reset.png'), wx.BITMAP_TYPE_PNG).ConvertToBitmap(), shortHelp = _("Reset view"))
        self.toolbar.AddSeparator()
        self.toolbar.AddTool(6, '', wx.Image(imagefile('inject.png'), wx.BITMAP_TYPE_PNG).ConvertToBitmap(), wx.NullBitmap, shortHelp = _("Inject G-Code"), longHelp = _("Insert code at the beginning of this layer"))
        self.toolbar.AddTool(7, '', wx.Image(imagefile('edit.png'), wx.BITMAP_TYPE_PNG).ConvertToBitmap(), wx.NullBitmap, shortHelp = _("Edit layer"), longHelp = _("Edit the G-Code of this layer"))

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

        self.toolbar.Realize()
        vbox.Add(self.p, 1, wx.EXPAND)

        self.SetMinSize(self.ClientToWindowSize(vbox.GetMinSize()))
        self.Bind(wx.EVT_TOOL, lambda x: self.p.zoom(-1, -1, 1.2), id = 1)
        self.Bind(wx.EVT_TOOL, lambda x: self.p.zoom(-1, -1, 1 / 1.2), id = 2)
        self.Bind(wx.EVT_TOOL, lambda x: self.p.layerup(), id = 3)
        self.Bind(wx.EVT_TOOL, lambda x: self.p.layerdown(), id = 4)
        self.Bind(wx.EVT_TOOL, self.resetview, id = 5)
        self.Bind(wx.EVT_TOOL, lambda x: self.p.inject(), id = 6)
        self.Bind(wx.EVT_TOOL, lambda x: self.p.editlayer(), id = 7)

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
        wx.CallAfter(self.SetStatusText, _("Layer %d - Z = %.03f mm") % (self.p.layerindex + 1, z), 0)
        self.p.dirty = True
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
            e = event.GetPosition()
            if self.initpos is None:
                self.initpos = e
                self.basetrans = self.p.translate
            self.p.translate = [self.basetrans[0] + (e[0] - self.initpos[0]),
                                self.basetrans[1] + (e[1] - self.initpos[1])]
            self.p.dirty = True
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

from printrun.gui.viz import BaseViz
class Gviz(wx.Panel, BaseViz):

    # Mark canvas as dirty when setting showall
    _showall = 0

    def _get_showall(self):
        return self._showall

    def _set_showall(self, showall):
        if showall != self._showall:
            self.dirty = True
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
        penwidth = max(1, int(self.filament_width * ((self.scale[0] + self.scale[1]) / 2.0)))
        self.translate = [0.0, 0.0]
        self.mainpen = wx.Pen(wx.Colour(0, 0, 0), penwidth)
        self.arcpen = wx.Pen(wx.Colour(255, 0, 0), penwidth)
        self.travelpen = wx.Pen(wx.Colour(10, 80, 80), penwidth)
        self.hlpen = wx.Pen(wx.Colour(200, 50, 50), penwidth)
        self.fades = [wx.Pen(wx.Colour(int(250 - 0.6 ** i * 100), int(250 - 0.6 ** i * 100), int(200 - 0.4 ** i * 50)), penwidth) for i in range(6)]
        self.penslist = [self.mainpen, self.arcpen, self.travelpen, self.hlpen] + self.fades
        self.bgcolor = wx.Colour()
        self.bgcolor.Set(bgcolor)
        self.blitmap = wx.Bitmap(self.GetClientSize()[0], self.GetClientSize()[1], -1)
        self.paint_overlay = None

    def inject(self):
        layer = self.layers[self.layerindex]
        injector(self.gcode, self.layerindex, layer)

    def editlayer(self):
        layer = self.layers[self.layerindex]
        injector_edit(self.gcode, self.layerindex, layer)

    def clearhilights(self):
        self.hilight.clear()
        self.hilightarcs.clear()
        while not self.hilightqueue.empty():
            self.hilightqueue.get_nowait()
        while not self.hilightarcsqueue.empty():
            self.hilightarcsqueue.get_nowait()

    def clear(self):
        self.gcode = None
        self.lastpos = [0, 0, 0, 0, 0, 0, 0]
        self.hilightpos = self.lastpos[:]
        self.lines = {}
        self.pens = {}
        self.arcs = {}
        self.arcpens = {}
        self.layers = {}
        self.layersz = []
        self.clearhilights()
        self.layerindex = 0
        self.showall = 0
        self.dirty = True
        self.partial = False
        self.painted_layers = set()
        wx.CallAfter(self.Refresh)

    def get_currentz(self):
        z = self.layersz[self.layerindex]
        z = 0. if z is None else z
        return z

    def layerup(self):
        if self.layerindex + 1 < len(self.layers):
            self.layerindex += 1
            z = self.get_currentz()
            wx.CallAfter(self.parent.SetStatusText, _("Layer %d - Going Up - Z = %.03f mm") % (self.layerindex + 1, z), 0)
            self.dirty = True
            self.parent.setlayercb(self.layerindex)
            wx.CallAfter(self.Refresh)

    def layerdown(self):
        if self.layerindex > 0:
            self.layerindex -= 1
            z = self.get_currentz()
            wx.CallAfter(self.parent.SetStatusText, _("Layer %d - Going Down - Z = %.03f mm") % (self.layerindex + 1, z), 0)
            self.dirty = True
            self.parent.setlayercb(self.layerindex)
            wx.CallAfter(self.Refresh)

    def setlayer(self, layer):
        if layer in self.layers:
            self.clearhilights()
            self.layerindex = self.layers[layer]
            self.dirty = True
            self.showall = 0
            wx.CallAfter(self.Refresh)

    def update_basescale(self):
        self.basescale = 2 * [min(float(self.size[0] - 1) / self.build_dimensions[0],
                                  float(self.size[1] - 1) / self.build_dimensions[1])]

    def resize(self, event):
        old_basescale = self.basescale
        width, height = self.GetClientSize()
        if width < 1 or height < 1:
            return
        self.size = (width, height)
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
        penwidth = max(1, int(self.filament_width * ((self.scale[0] + self.scale[1]) / 2.0)))
        for pen in self.penslist:
            pen.SetWidth(penwidth)
        self.dirty = True
        wx.CallAfter(self.Refresh)

    def _line_scaler(self, x):
        return (int(self.scale[0] * x[0]),
                int(self.scale[1] * x[1]),
                int(self.scale[0] * x[2]),
                int(self.scale[1] * x[3]),)

    def _arc_scaler(self, x):
        return (self.scale[0] * x[0],
                self.scale[1] * x[1],
                self.scale[0] * x[2],
                self.scale[1] * x[3],
                self.scale[0] * x[4],
                self.scale[1] * x[5],)

    def _drawlines(self, dc, lines, pens):
        scaled_lines = [self._line_scaler(l) for l in lines]
        dc.DrawLineList(scaled_lines, pens)

    def _drawarcs(self, dc, arcs, pens):
        scaled_arcs = [self._arc_scaler(a) for a in arcs]
        dc.SetBrush(wx.TRANSPARENT_BRUSH)
        for i in range(len(scaled_arcs)):
            dc.SetPen(pens[i] if isinstance(pens, numpy.ndarray) else pens)
            dc.DrawArc(*scaled_arcs[i])

    def repaint_everything(self):
        width = self.scale[0] * self.build_dimensions[0]
        height = self.scale[1] * self.build_dimensions[1]
        self.blitmap = wx.Bitmap(int(width) + 1, int(height) + 1, -1)
        dc = wx.MemoryDC()
        dc.SelectObject(self.blitmap)
        dc.SetBackground(wx.Brush((250, 250, 200)))
        dc.Clear()
        dc.SetPen(wx.Pen(wx.Colour(180, 180, 150)))
        for grid_unit in self.grid:
            if grid_unit > 0:
                for x in range(int(self.build_dimensions[0] / grid_unit) + 1):
                    draw_x = self.scale[0] * x * grid_unit
                    dc.DrawLine(int(draw_x), 0, int(draw_x), int(height))
                for y in range(int(self.build_dimensions[1] / grid_unit) + 1):
                    draw_y = self.scale[1] * (self.build_dimensions[1] - y * grid_unit)
                    dc.DrawLine(0, int(draw_y), int(width), int(draw_y))
            dc.SetPen(wx.Pen(wx.Colour(0, 0, 0)))

        if not self.showall:
            # Draw layer gauge
            dc.SetBrush(wx.Brush((43, 144, 255)))
            dc.DrawRectangle(int(width) - 15, 0, 15, int(height))
            dc.SetBrush(wx.Brush((0, 255, 0)))
            if self.layers:
                dc.DrawRectangle(int(width) - 14, int((1.0 - (1.0 * (self.layerindex + 1)) / len(self.layers)) * height), 13, int(height) - 1)

        if self.showall:
            for i in range(len(self.layersz)):
                self.painted_layers.add(i)
                self._drawlines(dc, self.lines[i], self.pens[i])
                self._drawarcs(dc, self.arcs[i], self.arcpens[i])
            dc.SelectObject(wx.NullBitmap)
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

    def repaint_partial(self):
        if self.showall:
            dc = wx.MemoryDC()
            dc.SelectObject(self.blitmap)
            for i in set(range(len(self.layersz))).difference(self.painted_layers):
                self.painted_layers.add(i)
                self._drawlines(dc, self.lines[i], self.pens[i])
                self._drawarcs(dc, self.arcs[i], self.arcpens[i])
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
        dc.SelectObject(wx.NullBitmap)

    def paint(self, event):
        if self.dirty:
            self.dirty = False
            self.partial = False
            self.repaint_everything()
        elif self.partial:
            self.partial = False
            self.repaint_partial()
        self.paint_hilights()
        dc = wx.PaintDC(self)
        dc.SetBackground(wx.Brush(self.bgcolor))
        dc.Clear()
        dc.DrawBitmap(self.blitmap, int(self.translate[0]), int(self.translate[1]))
        if self.paint_overlay:
            self.paint_overlay(dc)

    def addfile_perlayer(self, gcode, showall = False):
        self.clear()
        self.gcode = gcode
        self.showall = showall
        generator = self.add_parsed_gcodes(gcode)
        generator_output = next(generator)
        while generator_output is not None:
            yield generator_output
            generator_output = next(generator)
        max_layers = len(self.layers)
        if hasattr(self.parent, "layerslider"):
            self.parent.layerslider.SetRange(0, max_layers - 1)
            self.parent.layerslider.SetValue(0)
        yield None

    def addfile(self, gcode = None, showall = False):
        generator = self.addfile_perlayer(gcode, showall)
        while next(generator) is not None:
            continue

    def _get_movement(self, start_pos, gline):
        """Takes a start position and a gcode, and returns a 3-uple containing
        (final position, line, arc), with line and arc being None if not
        used"""
        target = start_pos[:]
        target[5] = 0.0
        target[6] = 0.0
        if gline.current_x is not None: target[0] = gline.current_x
        if gline.current_y is not None: target[1] = gline.current_y
        if gline.current_z is not None: target[2] = gline.current_z
        if gline.e is not None:
            if gline.relative_e:
                target[3] += gline.e
            else:
                target[3] = gline.e
        if gline.f is not None: target[4] = gline.f
        if gline.i is not None: target[5] = gline.i
        if gline.j is not None: target[6] = gline.j

        if gline.command in ["G0", "G1"]:
            line = [self._x(start_pos[0]),
                    self._y(start_pos[1]),
                    self._x(target[0]),
                    self._y(target[1])]
            return target, line, None
        elif gline.command in ["G2", "G3"]:
            # startpos, endpos, arc center
            arc = [self._x(start_pos[0]), self._y(start_pos[1]),
                   self._x(target[0]), self._y(target[1]),
                   self._x(start_pos[0] + target[5]), self._y(start_pos[1] + target[6])]
            if gline.command == "G2":  # clockwise, reverse endpoints
                arc[0], arc[1], arc[2], arc[3] = arc[2], arc[3], arc[0], arc[1]
            return target, None, arc

    def _y(self, y):
        return self.build_dimensions[1] - (y - self.build_dimensions[4])

    def _x(self, x):
        return x - self.build_dimensions[3]

    def add_parsed_gcodes(self, gcode):
        start_time = time.time()

        layer_idx = 0
        while layer_idx < len(gcode.all_layers):
            layer = gcode.all_layers[layer_idx]
            has_move = False
            for gline in layer:
                if gline.is_move:
                    has_move = True
                    break
            if not has_move:
                yield layer_idx
                layer_idx += 1
                continue
            viz_layer = len(self.layers)
            self.lines[viz_layer] = []
            self.pens[viz_layer] = []
            self.arcs[viz_layer] = []
            self.arcpens[viz_layer] = []
            for gline in layer:
                if not gline.is_move:
                    continue

                target, line, arc = self._get_movement(self.lastpos[:], gline)

                if line is not None:
                    self.lines[viz_layer].append(line)
                    self.pens[viz_layer].append(self.mainpen if target[3] != self.lastpos[3] or gline.extruding else self.travelpen)
                elif arc is not None:
                    self.arcs[viz_layer].append(arc)
                    self.arcpens[viz_layer].append(self.arcpen)

                self.lastpos = target
            # Transform into a numpy array for memory efficiency
            self.lines[viz_layer] = numpy.asarray(self.lines[viz_layer], dtype = numpy.float32)
            self.pens[viz_layer] = numpy.asarray(self.pens[viz_layer])
            self.arcs[viz_layer] = numpy.asarray(self.arcs[viz_layer], dtype = numpy.float32)
            self.arcpens[viz_layer] = numpy.asarray(self.arcpens[viz_layer])
            # Only add layer to self.layers now to prevent the display of an
            # unfinished layer
            self.layers[layer_idx] = viz_layer
            self.layersz.append(layer.z)

            # Refresh display if more than 0.2s have passed
            if time.time() - start_time > 0.2:
                start_time = time.time()
                self.partial = True
                wx.CallAfter(self.Refresh)

            yield layer_idx
            layer_idx += 1

        self.dirty = True
        wx.CallAfter(self.Refresh)
        yield None

    def addgcodehighlight(self, gline):
        if gline.command not in ["G0", "G1", "G2", "G3"]:
            return

        target, line, arc = self._get_movement(self.hilightpos[:], gline)

        if line is not None:
            self.hilight.append(line)
            self.hilightqueue.put_nowait(line)
        elif arc is not None:
            self.hilightarcs.append(arc)
            self.hilightarcsqueue.put_nowait(arc)

        self.hilightpos = target
        wx.CallAfter(self.Refresh)

if __name__ == '__main__':
    import sys
    app = wx.App(False)
    main = GvizWindow(open(sys.argv[1], "rU"))
    main.Show()
    app.MainLoop()
