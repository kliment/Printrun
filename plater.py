#!/usr/bin/env python

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

import os

# Set up Internationalization using gettext
# searching for installed locales on /usr/share; uses relative folder if not found (windows)
from printrun.printrun_utils import install_locale
install_locale('plater')

import wx
import time
import threading
import math
import sys
import traceback

from printrun import stltool
from printrun.objectplater import Plater

glview = False
if "-nogl" not in sys.argv:
    try:
        from printrun import stlview
        glview = True
    except:
        print "Could not load 3D viewer for plater:"
        traceback.print_exc()


def evalme(s):
    return eval(s[s.find("(") + 1:s.find(")")])


class stlwrap:
    def __init__(self, obj, name = None):
        self.obj = obj
        self.name = name
        if name is None:
            self.name = obj.name

    def __repr__(self):
        return self.name


class showstl(wx.Window):
    def __init__(self, parent, size, pos):
        wx.Window.__init__(self, parent, size = size, pos = pos)
        #self.SetBackgroundColour((0, 0, 0))
        #wx.FutureCall(200, self.paint)
        self.i = 0
        self.parent = parent
        self.previ = 0
        self.Bind(wx.EVT_MOUSEWHEEL, self.rot)
        self.Bind(wx.EVT_MOUSE_EVENTS, self.move)
        self.Bind(wx.EVT_PAINT, self.repaint)
        self.Bind(wx.EVT_KEY_DOWN, self.keypress)
        #self.s = stltool.stl("sphere.stl").scale([2, 1, 1])
        self.triggered = 0
        self.initpos = None
        self.prevsel = -1

    def drawmodel(self, m, scale):
        m.bitmap = wx.EmptyBitmap(800, 800, 32)
        dc = wx.MemoryDC()
        dc.SelectObject(m.bitmap)
        dc.SetBackground(wx.Brush((0, 0, 0, 0)))
        dc.SetBrush(wx.Brush((0, 0, 0, 255)))
        #dc.DrawRectangle(-1, -1, 10000, 10000)
        dc.SetBrush(wx.Brush(wx.Colour(128, 255, 128)))
        dc.SetPen(wx.Pen(wx.Colour(128, 128, 128)))
        #m.offsets = [10, 10, 0]
        #print m.offsets, m.dims
        for i in m.facets:  # random.sample(m.facets, min(100000, len(m.facets))):
            dc.DrawPolygon([wx.Point(400 + scale * p[0], (400 - scale * p[1])) for p in i[1]])
            #if(time.time()-t)>5:
            #    break
        dc.SelectObject(wx.NullBitmap)
        m.bitmap.SetMask(wx.Mask(m.bitmap, wx.Colour(0, 0, 0, 255)))

    def move_shape(self, delta):
        """moves shape (selected in l, which is list ListBox of shapes)
        by an offset specified in tuple delta.
        Positive numbers move to (rigt, down)"""
        name = self.parent.l.GetSelection()
        if name == wx.NOT_FOUND:
            return False
        name = self.parent.l.GetString(name)
        model = self.parent.models[name]
        model.offsets = [model.offsets[0] + delta[0],
                         model.offsets[1] + delta[1],
                         model.offsets[2]
                         ]
        self.Refresh()
        return True

    def move(self, event):
        if event.ButtonUp(wx.MOUSE_BTN_LEFT):
            if(self.initpos is not None):
                currentpos = event.GetPositionTuple()
                delta = (0.5 * (currentpos[0] - self.initpos[0]),
                         -0.5 * (currentpos[1] - self.initpos[1])
                         )
                self.move_shape(delta)
                self.Refresh()
                self.initpos = None
        elif event.ButtonDown(wx.MOUSE_BTN_RIGHT):
            self.parent.right(event)
        elif event.Dragging():
            if self.initpos is None:
                self.initpos = event.GetPositionTuple()
            self.Refresh()
            dc = wx.ClientDC(self)
            p = event.GetPositionTuple()
            dc.DrawLine(self.initpos[0], self.initpos[1], p[0], p[1])
            #print math.sqrt((p[0]-self.initpos[0])**2+(p[1]-self.initpos[1])**2)

            del dc
        else:
            event.Skip()

    def rotate_shape(self, angle):
        """rotates acive shape
        positive angle is clockwise
        """
        self.i += angle
        if not self.triggered:
            self.triggered = 1
            threading.Thread(target = self.cr).start()

    def keypress(self, event):
        """gets keypress events and moves/rotates acive shape"""
        keycode = event.GetKeyCode()
        #print keycode
        step = 5
        angle = 18
        if event.ControlDown():
            step = 1
            angle = 1
        #h
        if keycode == 72:
            self.move_shape((-step, 0))
        #l
        if keycode == 76:
            self.move_shape((step, 0))
        #j
        if keycode == 75:
            self.move_shape((0, step))
        #k
        if keycode == 74:
            self.move_shape((0, -step))
        #[
        if keycode == 91:
            self.rotate_shape(-angle)
        #]
        if keycode == 93:
            self.rotate_shape(angle)
        event.Skip()

    def rotateafter(self):
        if self.i != self.previ:
            i = self.parent.l.GetSelection()
            if i != wx.NOT_FOUND:
                #o = self.models[self.l.GetItemText(i)].offsets
                self.parent.models[self.parent.l.GetString(i)].rot -= 5 * (self.i - self.previ)
                #self.models[self.l.GetItemText(i)].offsets = o
            self.previ = self.i
            self.Refresh()

    def cr(self):
        time.sleep(0.01)
        wx.CallAfter(self.rotateafter)
        self.triggered = 0

    def rot(self, event):
        z = event.GetWheelRotation()
        s = self.parent.l.GetSelection()
        if self.prevsel != s:
            self.i = 0
            self.prevsel = s
        if z < 0:
            self.rotate_shape(-1)
        else:
            self.rotate_shape(1)

    def repaint(self, event):
        dc = wx.PaintDC(self)
        self.paint(dc = dc)

    def paint(self, coord1 = "x", coord2 = "y", dc = None):
        if dc is None:
            dc = wx.ClientDC(self)
        scale = 2
        dc.SetPen(wx.Pen(wx.Colour(100, 100, 100)))
        for i in xrange(20):
            dc.DrawLine(0, i * scale * 10, 400, i * scale * 10)
            dc.DrawLine(i * scale * 10, 0, i * scale * 10, 400)
        dc.SetPen(wx.Pen(wx.Colour(0, 0, 0)))
        for i in xrange(4):
            dc.DrawLine(0, i * scale * 50, 400, i * scale * 50)
            dc.DrawLine(i * scale * 50, 0, i * scale * 50, 400)
        dc.SetBrush(wx.Brush(wx.Colour(128, 255, 128)))
        dc.SetPen(wx.Pen(wx.Colour(128, 128, 128)))
        dcs = wx.MemoryDC()
        for m in self.parent.models.values():
            b = m.bitmap
            im = b.ConvertToImage()
            imgc = wx.Point(im.GetWidth() / 2, im.GetHeight() / 2)
            im = im.Rotate(math.radians(m.rot), imgc, 0)
            bm = wx.BitmapFromImage(im)
            dcs.SelectObject(bm)
            bsz = bm.GetSize()
            dc.Blit(scale * m.offsets[0] - bsz[0] / 2, 400 - (scale * m.offsets[1] + bsz[1] / 2), bsz[0], bsz[1], dcs, 0, 0, useMask = 1)
            #for i in m.facets:#random.sample(m.facets, min(100000, len(m.facets))):
            #    dc.DrawPolygon([wx.Point(offset[0]+scale*m.offsets[0]+scale*p[0], 400-(offset[1]+scale*m.offsets[1]+scale*p[1])) for p in i[1]])
                #if(time.time()-t)>5:
                #    break
        del dc

class StlPlater(Plater):

    load_wildcard = _("STL files (*.stl;*.STL)|*.stl;*.STL|OpenSCAD files (*.scad)|*.scad")
    save_wildcard = _("STL files (*.stl;*.STL)|*.stl;*.STL")

    def __init__(self, filenames = [], size = (800, 580), callback = None, parent = None, build_dimensions = None):
        super(StlPlater, self).__init__(filenames, size, callback, parent, build_dimensions)
        if glview:
            viewer = stlview.StlViewPanel(self, (580, 580), build_dimensions = self.build_dimensions)
        else:
            viewer = showstl(self, (580, 580), (0, 0))
        self.set_viewer(viewer)

    def done(self, event, cb):
        try:
            os.mkdir("tempstl")
        except:
            pass
        name = "tempstl/" + str(int(time.time()) % 10000) + ".stl"
        self.export_to(name)
        if cb is not None:
            cb(name)
        self.Destroy()

    def load_file(self, filename):
        if filename.lower().endswith(".stl"):
            self.load_stl(filename)
        elif filename.lower().endswith(".scad"):
            self.load_scad(filename)

    def load_scad(self, name):
        lf = open(name)
        s = [i.replace("\n", "").replace("\r", "").replace(";", "") for i in lf if "stl" in i]
        lf.close()

        for i in s:
            parts = i.split()
            for part in parts:
                if 'translate' in part:
                    translate_list = evalme(part)
            for part in parts:
                if 'rotate' in part:
                    rotate_list = evalme(part)
            for part in parts:
                if 'import' in part:
                    stl_file = evalme(part)

            newname = os.path.split(stl_file.lower())[1]
            c = 1
            while newname in self.models:
                newname = os.path.split(stl_file.lower())[1]
                newname = newname + "(%d)" % c
                c += 1
            stl_path = os.path.join(os.path.split(name)[0:len(os.path.split(stl_file)) - 1])
            stl_full_path = os.path.join(stl_path[0], str(stl_file))
            self.load_stl_into_model(stl_full_path, stl_file, translate_list, rotate_list[2])

    def load_stl(self, name):
        if not(os.path.exists(name)):
            return
        path = os.path.split(name)[0]
        self.basedir = path
        #print name
        if name.lower().endswith(".stl"):
            #Filter out the path, just show the STL filename.
            self.load_stl_into_model(name, name)
        self.Refresh()

    def load_stl_into_model(self, path, name, offset = [0, 0, 0], rotation = 0, scale = [1.0, 1.0, 1.0]):
        model = stltool.stl(path)
        model.offsets = offset
        model.rot = rotation
        model.scale = scale
        model.filename = name
        minx, miny, minz, maxx, maxy, maxz = (10000, 10000, 10000, 0, 0, 0)
        minx = float("inf")
        miny = float("inf")
        minz = float("inf")
        maxx = float("-inf")
        maxy = float("-inf")
        maxz = float("-inf")
        for i in model.facets:
            for j in i[1]:
                if j[0] < minx:
                    minx = j[0]
                if j[1] < miny:
                    miny = j[1]
                if j[2] < minz:
                    minz = j[2]
                if j[0] > maxx:
                    maxx = j[0]
                if j[1] > maxy:
                    maxy = j[1]
                if j[2] > maxz:
                    maxz = j[2]
        model.dims = [minx, maxx, miny, maxy, minz, maxz]
        self.add_model(name, model)
        #if minx < 0:
        #    model.offsets[0] = -minx
        #if miny < 0:
        #    model.offsets[1] = -miny
        self.s.drawmodel(model, 2)

    def export_to(self, name):
        sf = open(name.replace(".", "_") + ".scad", "w")
        facets = []
        for i in self.models.values():

            r = i.rot
            o = i.offsets
            sf.write('translate([%s, %s, %s]) rotate([0, 0, %s]) import_stl("%s");\n' % (str(o[0]), str(o[1]), str(o[2]), r, os.path.split(i.filename)[1]))
            if r != 0:
                i = i.rotate([0, 0, r])
            if o != [0, 0, 0]:
                i = i.translate([o[0], o[1], o[2]])
            facets += i.facets
        sf.close()
        stltool.emitstl(name, facets, "plater_export")
        print _("wrote %s") % name


if __name__ == '__main__':
    app = wx.App(False)
    main = StlPlater(sys.argv[1:])
    main.Show()
    app.MainLoop()
