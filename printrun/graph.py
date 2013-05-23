#!/usr/bin/python

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

import wx, random
from math import log10,floor

from bufferedcanvas import *

class Graph(BufferedCanvas):
    '''A class to show a Graph with Pronterface.'''

    def __init__(self, parent, id, root, pos = wx.DefaultPosition,
                 size = wx.Size(150, 80), style = 0):
        # Forcing a no full repaint to stop flickering
        style = style | wx.NO_FULL_REPAINT_ON_RESIZE
        super(Graph, self).__init__(parent, id, pos, size, style)
        self.root = root

        self.extruder0temps       = [0]
        self.extruder0targettemps = [0]
        self.extruder1temps       = [0]
        self.extruder1targettemps = [0]
        self.bedtemps             = [0]
        self.bedtargettemps       = [0]

        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.updateTemperatures, self.timer)

        self.minyvalue  = 0
        self.maxyvalue  = 250
        self.ybars      = 5
        self.xbars      = 6 # One bar per 10 second
        self.xsteps     = 60 # Covering 1 minute in the graph

        self.y_offset   = 1 # This is to show the line even when value is 0 and maxyvalue

        self._lastyvalue = 0

    def OnPaint(self, evt):
        dc = wx.PaintDC(self)
        gc = wx.GraphicsContext.Create(dc)

    def updateTemperatures(self, event):
        self.AddBedTemperature(self.bedtemps[-1])
        self.AddBedTargetTemperature(self.bedtargettemps[-1])
        self.AddExtruder0Temperature(self.extruder0temps[-1])
        self.AddExtruder0TargetTemperature(self.extruder0targettemps[-1])
        #self.AddExtruder1Temperature(self.extruder1temps[-1])
        #self.AddExtruder1TargetTemperature(self.extruder1targettemps[-1])
        self.updateYBounds()
        self.Refresh()

    def updateYBounds(self):
        self.minyvalue = 0
        self.maxyvalue = 250

    def drawgrid(self, dc, gc):
        #cold, medium, hot = wx.Colour(0, 167, 223), wx.Colour(239, 233, 119), wx.Colour(210, 50.100)
        #col1 = wx.Colour(255, 0, 0, 255)
        #col2 = wx.Colour(255, 255, 255, 128)

        #b = gc.CreateLinearGradientBrush(0, 0, w, h, col1, col2)

        gc.SetPen(wx.Pen(wx.Colour(255, 0, 0, 0), 4))

        #gc.SetBrush(wx.Brush(wx.Colour(245, 245, 255, 52)))

        #gc.SetBrush(gc.CreateBrush(wx.Brush(wx.Colour(0, 0, 0, 255))))
        #gc.SetPen(wx.Pen(wx.Colour(255, 0, 0, 0), 4))

        #gc.DrawLines(wx.Point(0, 0), wx.Point(50, 10))

        #path = gc.CreatePath()
        #path.MoveToPoint(0.0, 0.0)
        #path.AddLineToPoint(0.0, 100.0)
        #path.AddLineToPoint(100.0, 0.0)
        #path.AddCircle( 50.0, 50.0, 50.0 )
        #path.CloseSubpath()
        #gc.DrawPath(path)
        #gc.StrokePath(path)

        font = wx.Font(10, wx.DEFAULT, wx.NORMAL, wx.BOLD)
        gc.SetFont(font, wx.Colour(23, 44, 44))

        # draw vertical bars
        dc.SetPen(wx.Pen(wx.Colour(225, 225, 225), 1))
        for x in range(self.xbars):
            dc.DrawLine(x*(float(self.width)/self.xbars), 0, x*(float(self.width)/self.xbars), self.height)

        # draw horizontal bars
        spacing = self.calculate_spacing()
        yspan = self.maxyvalue-self.minyvalue
        bars = int(yspan/spacing)

        dc.SetPen(wx.Pen(wx.Colour(225, 225, 225), 1))
        for y in xrange(bars):
            y_pos = y*(float(self.height)/self.ybars)
            dc.DrawLine(0, y_pos, self.width, y_pos)
            gc.DrawText(unicode(y*spacing), 1, y_pos - (font.GetPointSize() / 2))

        if self.timer.IsRunning() == False:
            font = wx.Font(14, wx.DEFAULT, wx.NORMAL, wx.BOLD)
            gc.SetFont(font, wx.Colour(3, 4, 4))
            gc.DrawText("Graph offline", self.width/2 - (font.GetPointSize() * 3), self.height/2 - (font.GetPointSize() * 1))

        #dc.DrawCircle(50, 50, 1)

        #gc.SetPen(wx.Pen(wx.Colour(255, 0, 0, 0), 1))
        #gc.DrawLines([[20, 30], [10, 53]])
        #dc.SetPen(wx.Pen(wx.Colour(255, 0, 0, 0), 1))

    def calculate_spacing(self):
        # Allow grids of spacings 1,2.5,5,10,25,50,100,etc

        yspan = float(self.maxyvalue-self.minyvalue)
        print "yspan=%f"%yspan
        log_yspan = log10( yspan/self.ybars )
        print "log_yspan=%f"%log_yspan
        exponent = int( floor(log_yspan) )
        print "exponent=%f"%exponent

        #calculate boundary points between allowed spacings
        log1_25 = log10(2)+log10(1)+log10(2.5)-log10(1+2.5)
        log25_5 = log10(2)+log10(2.5)+log10(5)-log10(2.5+5)
        log5_10 = log10(2)+log10(5)+log10(10)-log10(5+10)

        if log_yspan-exponent < log1_25:
            return 10**exponent
        elif log1_25 <= log_yspan-exponent < log25_5:
            return 25*10**(exponent-1)
        elif log25_5 <= log_yspan-exponent < log5_10:
            return 5*10**exponent
        else:
            return 10**(exponent+1)

    def drawtemperature(self, dc, gc, temperature_list, text, text_xoffset, r, g, b, a):
        if self.timer.IsRunning() == False:
            dc.SetPen(wx.Pen(wx.Colour(128, 128, 128, 128), 1))
        else:
            dc.SetPen(wx.Pen(wx.Colour(r, g, b, a), 1))

        x_add = float(self.width)/self.xsteps
        x_pos = float(0.0)
        lastxvalue = float(0.0)

        for temperature in (temperature_list):
            y_pos = int((float(self.height-self.y_offset)/self.maxyvalue)*temperature) + self.y_offset
            if (x_pos > 0.0): # One need 2 points to draw a line.
                dc.DrawLine(lastxvalue, self.height-self._lastyvalue, x_pos, self.height-y_pos)

            lastxvalue = x_pos
            x_pos = float(x_pos) + x_add
            self._lastyvalue = y_pos

        if len(text) > 0:
            font = wx.Font(8, wx.DEFAULT, wx.NORMAL, wx.BOLD)
            #font = wx.Font(8, wx.DEFAULT, wx.NORMAL, wx.NORMAL)
            if self.timer.IsRunning() == False:
                gc.SetFont(font, wx.Colour(128, 128, 128))
            else:
                gc.SetFont(font, wx.Colour(r, g, b))

            #gc.DrawText(text, self.width - (font.GetPointSize() * ((len(text) * text_xoffset + 1))), self.height - self._lastyvalue - (font.GetPointSize() / 2))
            gc.DrawText(text, x_pos - x_add - (font.GetPointSize() * ((len(text) * text_xoffset + 1))), self.height - self._lastyvalue - (font.GetPointSize() / 2))
            #gc.DrawText(text, self.width - (font.GetPixelSize().GetWidth() * ((len(text) * text_xoffset + 1) + 1)), self.height - self._lastyvalue - (font.GetPointSize() / 2))


    def drawbedtemp(self, dc, gc):
        self.drawtemperature(dc, gc, self.bedtemps, "Bed", 2, 255, 0, 0, 128)

    def drawbedtargettemp(self, dc, gc):
        self.drawtemperature(dc, gc, self.bedtargettemps, "Bed Target", 2, 255, 120, 0, 128)


    def drawextruder0temp(self, dc, gc):
        self.drawtemperature(dc, gc, self.extruder0temps, "Ex0", 1, 0, 155, 255, 128)

    def drawextruder0targettemp(self, dc, gc):
        self.drawtemperature(dc, gc, self.extruder0targettemps, "Ex0 Target", 2, 0, 5, 255, 128)


    def drawextruder1temp(self, dc, gc):
        self.drawtemperature(dc, gc, self.extruder1temps, "Ex1", 3, 55, 55, 0, 128)

    def drawextruder1targettemp(self, dc, gc):
        self.drawtemperature(dc, gc, self.extruder1targettemps, "Ex1 Target", 2, 55, 55, 0, 128)


    def SetBedTemperature(self, value):
        self.bedtemps.pop()
        self.bedtemps.append(value)

    def AddBedTemperature(self, value):
        self.bedtemps.append(value)
        if (len(self.bedtemps)-1) * float(self.width)/self.xsteps > self.width:
            self.bedtemps.pop(0)

    def SetBedTargetTemperature(self, value):
        self.bedtargettemps.pop()
        self.bedtargettemps.append(value)

    def AddBedTargetTemperature(self, value):
        self.bedtargettemps.append(value)
        if (len(self.bedtargettemps)-1) * float(self.width)/self.xsteps > self.width:
            self.bedtargettemps.pop(0)

    def SetExtruder0Temperature(self, value):
        self.extruder0temps.pop()
        self.extruder0temps.append(value)

    def AddExtruder0Temperature(self, value):
        self.extruder0temps.append(value)
        if (len(self.extruder0temps)-1) * float(self.width)/self.xsteps > self.width:
            self.extruder0temps.pop(0)

    def SetExtruder0TargetTemperature(self, value):
        self.extruder0targettemps.pop()
        self.extruder0targettemps.append(value)

    def AddExtruder0TargetTemperature(self, value):
        self.extruder0targettemps.append(value)
        if (len(self.extruder0targettemps)-1) * float(self.width)/self.xsteps > self.width:
            self.extruder0targettemps.pop(0)

    def SetExtruder1Temperature(self, value):
        self.extruder1temps.pop()
        self.extruder1temps.append(value)

    def AddExtruder1Temperature(self, value):
        self.extruder1temps.append(value)
        if (len(self.extruder1temps)-1) * float(self.width)/self.xsteps > self.width:
            self.extruder1temps.pop(0)

    def SetExtruder1TargetTemperature(self, value):
        self.extruder1targettemps.pop()
        self.extruder1targettemps.append(value)

    def AddExtruder1TargetTemperature(self, value):
        self.extruder1targettemps.append(value)
        if (len(self.extruder1targettemps)-1) * float(self.width)/self.xsteps > self.width:
            self.extruder1targettemps.pop(0)

    def StartPlotting(self, time):
        self.Refresh()
        self.timer.Start(time)

    def StopPlotting(self):
        self.timer.Stop()
        self.Refresh()

    def draw(self, dc, w, h):
        dc.SetBackground(wx.Brush(self.root.settings.bgcolor))
        dc.Clear()
        gc = wx.GraphicsContext.Create(dc)
        self.width = w
        self.height = h
        self.drawgrid(dc, gc)
        self.drawbedtargettemp(dc, gc)
        self.drawbedtemp(dc, gc)
        self.drawextruder0targettemp(dc, gc)
        self.drawextruder0temp(dc, gc)
        self.drawextruder1targettemp(dc, gc)
        self.drawextruder1temp(dc, gc)
