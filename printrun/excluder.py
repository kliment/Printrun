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

import wx
from printrun import gviz

from .utils import imagefile, install_locale
install_locale('pronterface')

class ExcluderWindow(gviz.GvizWindow):

    def __init__(self, excluder, *args, **kwargs):
        super(ExcluderWindow, self).__init__(*args, **kwargs)
        self.SetTitle(_("Part excluder: draw rectangles where print instructions should be ignored"))
        self.toolbar.AddTool(128, " " + _("Reset selection"),
                             wx.Image(imagefile('reset.png'), wx.BITMAP_TYPE_PNG).ConvertToBitmap(),
                             _("Reset selection"))
        self.Bind(wx.EVT_TOOL, self.reset_selection, id = 128)
        self.parent = excluder
        self.p.paint_overlay = self.paint_selection
        self.p.layerup()

    def real_to_gcode(self, x, y):
        return (x + self.p.build_dimensions[3],
                self.p.build_dimensions[4] + self.p.build_dimensions[1] - y)

    def gcode_to_real(self, x, y):
        return (x - self.p.build_dimensions[3],
                self.p.build_dimensions[1] - (y - self.p.build_dimensions[4]))

    def mouse(self, event):
        if event.ButtonUp(wx.MOUSE_BTN_LEFT) \
           or event.ButtonUp(wx.MOUSE_BTN_RIGHT):
            self.initpos = None
        elif event.Dragging() and event.RightIsDown():
            e = event.GetPosition()
            if not self.initpos or not hasattr(self, "basetrans"):
                self.initpos = e
                self.basetrans = self.p.translate
            self.p.translate = [self.basetrans[0] + (e[0] - self.initpos[0]),
                                self.basetrans[1] + (e[1] - self.initpos[1])]
            self.p.dirty = 1
            wx.CallAfter(self.p.Refresh)
        elif event.Dragging() and event.LeftIsDown():
            x, y = event.GetPosition()
            if not self.initpos:
                self.basetrans = self.p.translate
            x = (x - self.basetrans[0]) / self.p.scale[0]
            y = (y - self.basetrans[1]) / self.p.scale[1]
            x, y = self.real_to_gcode(x, y)
            if not self.initpos:
                self.initpos = (x, y)
                self.parent.rectangles.append((0, 0, 0, 0))
            else:
                pos = (x, y)
                x0 = min(self.initpos[0], pos[0])
                y0 = min(self.initpos[1], pos[1])
                x1 = max(self.initpos[0], pos[0])
                y1 = max(self.initpos[1], pos[1])
                self.parent.rectangles[-1] = (x0, y0, x1, y1)
            wx.CallAfter(self.p.Refresh)
        else:
            event.Skip()

    def _line_scaler(self, orig):
        # Arguments:
        #   orig: coordinates of two corners of a rectangle (x0, y0, x1, y1)
        # Returns:
        #   rectangle coordinates as (x, y, width, height)
        x0, y0 = self.gcode_to_real(orig[0], orig[1])
        x0 = self.p.scale[0] * x0 + self.p.translate[0]
        y0 = self.p.scale[1] * y0 + self.p.translate[1]
        x1, y1 = self.gcode_to_real(orig[2], orig[3])
        x1 = self.p.scale[0] * x1 + self.p.translate[0]
        y1 = self.p.scale[1] * y1 + self.p.translate[1]
        width = max(x0, x1) - min(x0, x1) + 1
        height = max(y0, y1) - min(y0, y1) + 1
        rectangle = (min(x0, x1), min(y0, y1), width, height)
        return tuple(map(int, rectangle))

    def paint_selection(self, dc):
        dc = wx.GCDC(dc)
        dc.SetPen(wx.TRANSPARENT_PEN)
        dc.DrawRectangleList([self._line_scaler(rect)
                              for rect in self.parent.rectangles],
                             None, wx.Brush((200, 200, 200, 150)))

    def reset_selection(self, event):
        self.parent.rectangles = []
        wx.CallAfter(self.p.Refresh)

class Excluder:

    def __init__(self):
        self.rectangles = []
        self.window = None

    def pop_window(self, gcode, *args, **kwargs):
        if not self.window:
            self.window = ExcluderWindow(self, *args, **kwargs)
            self.window.p.addfile(gcode, True)
            self.window.Bind(wx.EVT_CLOSE, self.close_window)
            self.window.Show()
        else:
            self.window.Show()
            self.window.Raise()

    def close_window(self, event = None):
        if self.window:
            self.window.Destroy()
            self.window = None

if __name__ == '__main__':
    import sys
    from . import gcoder
    gcode = gcoder.GCode(open(sys.argv[1]))
    app = wx.App(False)
    ex = Excluder()
    ex.pop_window(gcode)
    app.MainLoop()
