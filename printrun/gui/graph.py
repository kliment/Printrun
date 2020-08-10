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
from math import log10, floor, ceil
from bisect import bisect_left

from printrun.utils import install_locale
install_locale('pronterface')

from .bufferedcanvas import BufferedCanvas

class GraphWindow(wx.Frame):
    def __init__(self, root, parent_graph = None, size = (600, 600)):
        super().__init__(None, title = _("Temperature graph"),
                                          size = size)
        self.parentg = parent_graph
        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)
        self.graph = Graph(panel, wx.ID_ANY, root, parent_graph = parent_graph)
        vbox.Add(self.graph, 1, wx.EXPAND)
        panel.SetSizer(vbox)

    def Destroy(self):
        self.graph.StopPlotting()
        if self.parentg is not None:
            self.parentg.window=None
        return super().Destroy()

    def __del__(self):
        if self.parentg is not None:
            self.parentg.window=None
        self.graph.StopPlotting()

class Graph(BufferedCanvas):
    '''A class to show a Graph with Pronterface.'''

    def __init__(self, parent, id, root, pos = wx.DefaultPosition,
                 size = wx.Size(150, 80), style = 0, parent_graph = None):
        # Forcing a no full repaint to stop flickering
        style = style | wx.NO_FULL_REPAINT_ON_RESIZE
        super().__init__(parent, id, pos, size, style)
        self.root = root

        if parent_graph is not None:
            self.extruder0temps = parent_graph.extruder0temps
            self.extruder0targettemps = parent_graph.extruder0targettemps
            self.extruder1temps = parent_graph.extruder1temps
            self.extruder1targettemps = parent_graph.extruder1targettemps
            self.bedtemps = parent_graph.bedtemps
            self.bedtargettemps = parent_graph.bedtargettemps
            self.fanpowers=parent_graph.fanpowers
        else:
            self.extruder0temps = [0]
            self.extruder0targettemps = [0]
            self.extruder1temps = [0]
            self.extruder1targettemps = [0]
            self.bedtemps = [0]
            self.bedtargettemps = [0]
            self.fanpowers= [0]

        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.updateTemperatures, self.timer)
        self.Bind(wx.EVT_WINDOW_DESTROY, self.processDestroy)

        self.minyvalue = 0
        self.maxyvalue = 260
        self.rescaley = True  # should the Y axis be rescaled dynamically?
        if self.rescaley:
            self._ybounds = Graph._YBounds(self)

        # If rescaley is set then ybars gives merely an estimate
        # Note that "bars" actually indicate the number of internal+external gridlines.
        self.ybars = 5
        self.xbars = 7  # One bar per 10 second
        self.xsteps = 60  # Covering 1 minute in the graph

        self.window = None
        self.reserved = []

    def processDestroy(self, event):
        # print('processDestroy')
        self.StopPlotting()
        self.Unbind(wx.EVT_TIMER)
        event.Skip()

    def show_graph_window(self, event = None):
        if self.window is None or not self.window:
            self.window = GraphWindow(self.root, self)
            self.window.Show()
            if self.timer.IsRunning():
                self.window.graph.StartPlotting(self.timer.Interval)
        else:
            self.window.Raise()

    def __del__(self):
        if self.window: self.window.Close()

    def updateTemperatures(self, event):
        # print('updateTemperatures')
        self.AddBedTemperature(self.bedtemps[-1])
        self.AddBedTargetTemperature(self.bedtargettemps[-1])
        self.AddExtruder0Temperature(self.extruder0temps[-1])
        self.AddExtruder0TargetTemperature(self.extruder0targettemps[-1])
        self.AddExtruder1Temperature(self.extruder1temps[-1])
        self.AddExtruder1TargetTemperature(self.extruder1targettemps[-1])
        self.AddFanPower(self.fanpowers[-1])
        if self.rescaley:
            self._ybounds.update()
        self.Refresh()

    def drawgrid(self, dc, gc):
        # cold, medium, hot = wx.Colour(0, 167, 223),\
        #                     wx.Colour(239, 233, 119),\
        #                     wx.Colour(210, 50.100)
        # col1 = wx.Colour(255, 0, 0, 255)
        # col2 = wx.Colour(255, 255, 255, 128)

        # b = gc.CreateLinearGradientBrush(0, 0, w, h, col1, col2)

        gc.SetPen(wx.Pen(wx.Colour(255, 0, 0, 0), 1))

        # gc.SetBrush(wx.Brush(wx.Colour(245, 245, 255, 52)))

        # gc.SetBrush(gc.CreateBrush(wx.Brush(wx.Colour(0, 0, 0, 255))))
        gc.SetPen(wx.Pen(wx.Colour(255, 0, 0, 255), 1))

        # gc.DrawLines(wx.Point(0, 0), wx.Point(50, 10))

        font = wx.Font(10, wx.DEFAULT, wx.NORMAL, wx.BOLD)
        gc.SetFont(font, wx.Colour(23, 44, 44))

        # draw vertical bars
        dc.SetPen(wx.Pen(wx.Colour(225, 225, 225), 1))
        xscale = float(self.width - 1) / (self.xbars - 1)
        for x in range(self.xbars + 1):
            x = x * xscale
            dc.DrawLine(x, 0, x, self.height)

        # draw horizontal bars
        spacing = self._calculate_spacing()  # spacing between bars, in degrees
        yspan = self.maxyvalue - self.minyvalue
        ybars = int(yspan / spacing)  # Should be close to self.ybars
        firstbar = int(ceil(self.minyvalue / spacing))  # in degrees
        dc.SetPen(wx.Pen(wx.Colour(225, 225, 225), 1))
        for y in range(firstbar, firstbar + ybars + 1):
            # y_pos = y*(float(self.height)/self.ybars)
            degrees = y * spacing
            y_pos = self._y_pos(degrees)
            dc.DrawLine(0, y_pos, self.width, y_pos)
            label = str(y * spacing)
            label_y = y_pos - font.GetPointSize() / 2
            self.layoutText(label, 1, label_y, gc)
            gc.DrawText(label, 1, label_y)

        if not self.timer.IsRunning():
            font = wx.Font(14, wx.DEFAULT, wx.NORMAL, wx.BOLD)
            gc.SetFont(font, wx.Colour(3, 4, 4))
            gc.DrawText("Graph offline",
                        self.width / 2 - font.GetPointSize() * 3,
                        self.height / 2 - font.GetPointSize() * 1)

        # dc.DrawCircle(50, 50, 1)

        # gc.SetPen(wx.Pen(wx.Colour(255, 0, 0, 0), 1))
        # gc.DrawLines([[20, 30], [10, 53]])
        # dc.SetPen(wx.Pen(wx.Colour(255, 0, 0, 0), 1))

    def _y_pos(self, temperature):
        """Converts a temperature, in degrees, to a pixel position"""
        # fraction of the screen from the bottom
        frac = (float(temperature - self.minyvalue)
                / (self.maxyvalue - self.minyvalue))
        return int((1.0 - frac) * (self.height - 1))

    def _calculate_spacing(self):
        # Allow grids of spacings 1,2.5,5,10,25,50,100,etc

        yspan = float(self.maxyvalue - self.minyvalue)
        log_yspan = log10(yspan / self.ybars)
        exponent = int(floor(log_yspan))

        # calculate boundary points between allowed spacings
        log1_25 = log10(2) + log10(1) + log10(2.5) - log10(1 + 2.5)
        log25_5 = log10(2) + log10(2.5) + log10(5) - log10(2.5 + 5)
        log5_10 = log10(2) + log10(5) + log10(10) - log10(5 + 10)

        if log_yspan - exponent < log1_25:
            return 10 ** exponent
        elif log1_25 <= log_yspan - exponent < log25_5:
            return 25 * 10 ** (exponent - 1)
        elif log25_5 <= log_yspan - exponent < log5_10:
            return 5 * 10 ** exponent
        else:
            return 10 ** (exponent + 1)

    def drawtemperature(self, dc, gc, temperature_list,
                        text, text_xoffset, r, g, b, a):
        color = self.timer.IsRunning() and (r, g, b, a) or [128] * 4
        dc.SetPen(wx.Pen(color, 1))

        x_add = float(self.width) / self.xsteps
        x_pos = 0.0
        lastxvalue = 0.0
        lastyvalue = temperature_list[-1]

        for temperature in temperature_list:
            y_pos = self._y_pos(temperature)
            if x_pos > 0:  # One need 2 points to draw a line.
                dc.DrawLine(lastxvalue, lastyvalue, x_pos, y_pos)

            lastxvalue = x_pos
            x_pos += x_add
            lastyvalue = y_pos

        if text:
            font = wx.Font(8, wx.DEFAULT, wx.NORMAL, wx.BOLD)
            # font = wx.Font(8, wx.DEFAULT, wx.NORMAL, wx.NORMAL)
            gc.SetFont(font, color[:3])

            text_size = len(text) * text_xoffset + 1
            pos = self.layoutText(text, lastxvalue, lastyvalue, gc)
            gc.DrawText(text, pos.x, pos.y)

    def layoutRect(self, rc):
        res = LtRect(rc)
        reserved = sorted((rs for rs in self.reserved
            if not (rc.bottom < rs.top or rc.top > rs.bottom)),
            key=wx.Rect.GetLeft)
        self.boundRect(res)
        # search to the left for gaps large enough to accomodate res
        rci = bisect_left(reserved, res)

        for i in range(rci, len(reserved)-1):
            res.x = reserved[i].right + 1
            if res.right < reserved[i+1].left:
                #found good res
                break
        else:
            # did not find gap to the right
            if reserved:
                #try to respect rc.x at the cost of a gap (50...Bed)
                if res.left < reserved[-1].right:
                    res.x = reserved[-1].right + 1
                    if res.right >= self.width:
                        #goes beyond window bounds
                        # try to the left
                        for i in range(min(rci, len(reserved)-1), 0, -1):
                            res.x = reserved[i].left - rc.width
                            if reserved[i-1].right < res.left:
                                break
                        else:
                            res = LtRect(self.layoutRectY(rc))

        self.reserved.append(res)
        return res

    def boundRect(self, rc):
        rc.x = min(rc.x, self.width - rc.width)
        return rc

    def layoutRectY(self, rc):
        top = self.height
        bottom = 0
        collision = False
        res = LtRect(rc)
        res.x = max(self.gridLabelsRight+1, min(rc.x, self.width-rc.width))
        for rs in self.reserved:
            if not (res.right < rs.left or res.left > rs.right):
                collision = True
                top = min(top, rs.Top)
                bottom = max(bottom, rs.bottom)
        if collision:
            res.y = top - rc.height
            if res.y < 0:
                res.y = bottom+1
                if res.bottom >= self.height:
                    res.y = rc.y
        return res

    def layoutText(self, text, x, y, gc):
        ext = gc.GetTextExtent(text)
        rc = self.layoutRect(wx.Rect(x, y, *ext))
        # print('layoutText', text, rc.TopLeft)
        return rc

    def drawfanpower(self, dc, gc):
        self.drawtemperature(dc, gc, self.fanpowers,
                             "Fan", 1, 0, 0, 0, 128)

    def drawbedtemp(self, dc, gc):
        self.drawtemperature(dc, gc, self.bedtemps,
                             "Bed", 2, 255, 0, 0, 128)

    def drawbedtargettemp(self, dc, gc):
        self.drawtemperature(dc, gc, self.bedtargettemps,
                             "Bed Target", 2, 255, 120, 0, 128)

    def drawextruder0temp(self, dc, gc):
        self.drawtemperature(dc, gc, self.extruder0temps,
                             "Ex0", 1, 0, 155, 255, 128)

    def drawextruder0targettemp(self, dc, gc):
        self.drawtemperature(dc, gc, self.extruder0targettemps,
                             "Ex0 Target", 2, 0, 5, 255, 128)

    def drawextruder1temp(self, dc, gc):
        self.drawtemperature(dc, gc, self.extruder1temps,
                             "Ex1", 3, 55, 55, 0, 128)

    def drawextruder1targettemp(self, dc, gc):
        self.drawtemperature(dc, gc, self.extruder1targettemps,
                             "Ex1 Target", 2, 55, 55, 0, 128)

    def SetFanPower(self, value):
        self.fanpowers.pop()
        self.fanpowers.append(value)

    def AddFanPower(self, value):
        self.fanpowers.append(value)
        if float(len(self.fanpowers) - 1) / self.xsteps > 1:
            self.fanpowers.pop(0)

    def SetBedTemperature(self, value):
        self.bedtemps.pop()
        self.bedtemps.append(value)

    def AddBedTemperature(self, value):
        self.bedtemps.append(value)
        if float(len(self.bedtemps) - 1) / self.xsteps > 1:
            self.bedtemps.pop(0)

    def SetBedTargetTemperature(self, value):
        self.bedtargettemps.pop()
        self.bedtargettemps.append(value)

    def AddBedTargetTemperature(self, value):
        self.bedtargettemps.append(value)
        if float(len(self.bedtargettemps) - 1) / self.xsteps > 1:
            self.bedtargettemps.pop(0)

    def SetExtruder0Temperature(self, value):
        self.extruder0temps.pop()
        self.extruder0temps.append(value)

    def AddExtruder0Temperature(self, value):
        self.extruder0temps.append(value)
        if float(len(self.extruder0temps) - 1) / self.xsteps > 1:
            self.extruder0temps.pop(0)

    def SetExtruder0TargetTemperature(self, value):
        self.extruder0targettemps.pop()
        self.extruder0targettemps.append(value)

    def AddExtruder0TargetTemperature(self, value):
        self.extruder0targettemps.append(value)
        if float(len(self.extruder0targettemps) - 1) / self.xsteps > 1:
            self.extruder0targettemps.pop(0)

    def SetExtruder1Temperature(self, value):
        self.extruder1temps.pop()
        self.extruder1temps.append(value)

    def AddExtruder1Temperature(self, value):
        self.extruder1temps.append(value)
        if float(len(self.extruder1temps) - 1) / self.xsteps > 1:
            self.extruder1temps.pop(0)

    def SetExtruder1TargetTemperature(self, value):
        self.extruder1targettemps.pop()
        self.extruder1targettemps.append(value)

    def AddExtruder1TargetTemperature(self, value):
        self.extruder1targettemps.append(value)
        if float(len(self.extruder1targettemps) - 1) / self.xsteps > 1:
            self.extruder1targettemps.pop(0)

    def StartPlotting(self, time):
        self.Refresh()
        self.timer.Start(time)
        if self.window: self.window.graph.StartPlotting(time)

    def Destroy(self):
        # print(__class__, '.Destroy')
        self.StopPlotting()
        return super(BufferedCanvas, self).Destroy()

    def StopPlotting(self):
        self.timer.Stop()
        #self.Refresh() # do not refresh when stopping in case the underlying object has been destroyed already
        if self.window: self.window.graph.StopPlotting()

    def draw(self, dc, w, h):
        dc.SetBackground(wx.Brush(self.root.settings.graph_color_background))
        dc.Clear()
        gc = wx.GraphicsContext.Create(dc)
        self.width = w
        self.height = h

        self.reserved.clear()
        self.drawgrid(dc, gc)
        self.gridLabelsRight = self.reserved[-1].Right

        self.drawbedtargettemp(dc, gc)
        self.drawbedtemp(dc, gc)
        self.drawfanpower(dc, gc)
        self.drawextruder0targettemp(dc, gc)
        self.drawextruder0temp(dc, gc)
        if self.extruder1targettemps[-1]>0 or self.extruder1temps[-1]>5:
            self.drawextruder1targettemp(dc, gc)
            self.drawextruder1temp(dc, gc)

    class _YBounds:
        """Small helper class to claculate y bounds dynamically"""

        def __init__(self, graph, minimum_scale=5.0, buffer=0.10):
            """_YBounds(Graph,float,float)

            graph           parent object to calculate scales for
            minimum_scale   minimum range to show on the graph
            buffer          amount of padding to add above & below the
                            displayed temperatures. Given as a fraction of the
                            total range. (Eg .05 to use 90% of the range for
                            temperatures)
            """
            self.graph = graph
            self.min_scale = minimum_scale
            self.buffer = buffer

            # Frequency to rescale the graph
            self.update_freq = 10
            # number of updates since last full refresh
            self._last_update = self.update_freq

        def update(self, forceUpdate=False):
            """Updates graph.minyvalue and graph.maxyvalue based on current
            temperatures """
            self._last_update += 1
            # TODO Smart update. Only do full calculation every 10s. Otherwise,
            # just look at current graph & expand if necessary
            if forceUpdate or self._last_update >= self.update_freq:
                self.graph.minyvalue, self.graph.maxyvalue = self.getBounds()
                self._last_update = 0
            else:
                bounds = self.getBoundsQuick()
                self.graph.minyvalue, self.graph.maxyvalue = bounds

        def getBounds(self):
            """
            Calculates the bounds based on the current temperatures

            Rules:
             * Include the full extruder0 history
             * Include the current target temp (but not necessarily old
               settings)
             * Include the extruder1 and/or bed temp if
                1) The target temp is >0
                2) The history has ever been above 5
             * Include at least min_scale
             * Include at least buffer above & below the extreme temps
            """
            extruder0_min = min(self.graph.extruder0temps)
            extruder0_max = max(self.graph.extruder0temps)
            extruder0_target = self.graph.extruder0targettemps[-1]
            extruder1_min = min(self.graph.extruder1temps)
            extruder1_max = max(self.graph.extruder1temps)
            extruder1_target = self.graph.extruder1targettemps[-1]
            bed_min = min(self.graph.bedtemps)
            bed_max = max(self.graph.bedtemps)
            bed_target = self.graph.bedtargettemps[-1]

            miny = min(extruder0_min, extruder0_target)
            maxy = max(extruder0_max, extruder0_target)
            if extruder1_target > 0 or extruder1_max > 5:  # use extruder1
                miny = min(miny, extruder1_min, extruder1_target)
                maxy = max(maxy, extruder1_max, extruder1_target)
            if bed_target > 0 or bed_max > 5:  # use HBP
                miny = min(miny, bed_min, bed_target)
                maxy = max(maxy, bed_max, bed_target)
            miny = min(0, miny)
            maxy = max(260, maxy)

            padding = (maxy - miny) * self.buffer / (1.0 - 2 * self.buffer)
            miny -= padding
            maxy += padding

            if maxy - miny < self.min_scale:
                extrapadding = (self.min_scale - maxy + miny) / 2.0
                miny -= extrapadding
                maxy += extrapadding

            return (miny, maxy)

        def getBoundsQuick(self):
            # Only look at current temps
            extruder0_min = self.graph.extruder0temps[-1]
            extruder0_max = self.graph.extruder0temps[-1]
            extruder0_target = self.graph.extruder0targettemps[-1]
            extruder1_min = self.graph.extruder1temps[-1]
            extruder1_max = self.graph.extruder1temps[-1]
            extruder1_target = self.graph.extruder1targettemps[-1]
            bed_min = self.graph.bedtemps[-1]
            bed_max = self.graph.bedtemps[-1]
            bed_target = self.graph.bedtargettemps[-1]

            miny = min(extruder0_min, extruder0_target)
            maxy = max(extruder0_max, extruder0_target)
            if extruder1_target > 0 or extruder1_max > 5:  # use extruder1
                miny = min(miny, extruder1_min, extruder1_target)
                maxy = max(maxy, extruder1_max, extruder1_target)
            if bed_target > 0 or bed_max > 5:  # use HBP
                miny = min(miny, bed_min, bed_target)
                maxy = max(maxy, bed_max, bed_target)
            miny = min(0, miny)
            maxy = max(260, maxy)

            # We have to rescale, so add padding
            bufratio = self.buffer / (1.0 - self.buffer)
            if miny < self.graph.minyvalue:
                padding = (self.graph.maxyvalue - miny) * bufratio
                miny -= padding
            if maxy > self.graph.maxyvalue:
                padding = (maxy - self.graph.minyvalue) * bufratio
                maxy += padding

            return (min(miny, self.graph.minyvalue),
                    max(maxy, self.graph.maxyvalue))

class LtRect(wx.Rect):
    def __lt__(self, other):
        return self.x < other.x
