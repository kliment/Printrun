#!/usr/bin/env python3

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
from .utils import install_locale
install_locale('pronterface')

import wx
import time
import logging
import threading
import math
import sys
import re
import traceback
import subprocess
from copy import copy

from printrun import stltool
from printrun.objectplater import make_plater, PlaterPanel

glview = '--no-gl' not in sys.argv
if glview:
    try:
        from printrun import stlview
    except:
        glview = False
        logging.warning("Could not load 3D viewer for plater:"
                        + "\n" + traceback.format_exc())


def evalme(s):
    return eval(s[s.find("(") + 1:s.find(")")])

def transformation_matrix(model):
    matrix = stltool.I
    if any(model.centeroffset):
        matrix = model.translation_matrix(model.centeroffset).dot(matrix)
    if model.rot:
        matrix = model.rotation_matrix([0, 0, model.rot]).dot(matrix)
    if any(model.offsets):
        matrix = model.translation_matrix(model.offsets).dot(matrix)
    return matrix

class showstl(wx.Window):
    def __init__(self, parent, size, pos):
        super().__init__(parent, size = size, pos = pos)
        self.i = 0
        self.parent = parent
        self.previ = 0
        self.Bind(wx.EVT_MOUSEWHEEL, self.rot)
        self.Bind(wx.EVT_MOUSE_EVENTS, self.move)
        self.Bind(wx.EVT_PAINT, self.repaint)
        self.Bind(wx.EVT_KEY_DOWN, self.keypress)
        self.triggered = 0
        self.initpos = None
        self.prevsel = -1

    def prepare_model(self, m, scale):
        m.bitmap = wx.Bitmap(800, 800, 32)
        dc = wx.MemoryDC()
        dc.SelectObject(m.bitmap)
        dc.SetBackground(wx.Brush((0, 0, 0, 0)))
        dc.SetBrush(wx.Brush((0, 0, 0, 255)))
        dc.SetBrush(wx.Brush(wx.Colour(128, 255, 128)))
        dc.SetPen(wx.Pen(wx.Colour(128, 128, 128)))
        for i in m.facets:
            dc.DrawPolygon([wx.Point(400 + scale * p[0], (400 - scale * p[1])) for p in i[1]])
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
            if self.initpos is not None:
                currentpos = event.GetPosition()
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
                self.initpos = event.GetPosition()
            self.Refresh()
            dc = wx.ClientDC(self)
            p = event.GetPosition()
            dc.DrawLine(self.initpos[0], self.initpos[1], p[0], p[1])
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
        step = 5
        angle = 18
        if event.ControlDown():
            step = 1
            angle = 1
        # h
        if keycode == 72:
            self.move_shape((-step, 0))
        # l
        if keycode == 76:
            self.move_shape((step, 0))
        # j
        if keycode == 75:
            self.move_shape((0, step))
        # k
        if keycode == 74:
            self.move_shape((0, -step))
        # [
        if keycode == 91:
            self.rotate_shape(-angle)
        # ]
        if keycode == 93:
            self.rotate_shape(angle)
        event.Skip()

    def rotateafter(self):
        if self.i != self.previ:
            i = self.parent.l.GetSelection()
            if i != wx.NOT_FOUND:
                self.parent.models[self.parent.l.GetString(i)].rot -= 5 * (self.i - self.previ)
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
        self.rotate_shape(-1 if z < 0 else 1) #TEST

    def repaint(self, event):
        dc = wx.PaintDC(self)
        self.paint(dc = dc)

    def paint(self, coord1 = "x", coord2 = "y", dc = None):
        if dc is None:
            dc = wx.ClientDC(self)
        scale = 2
        dc.SetPen(wx.Pen(wx.Colour(100, 100, 100)))
        for i in range(20):
            dc.DrawLine(0, i * scale * 10, 400, i * scale * 10)
            dc.DrawLine(i * scale * 10, 0, i * scale * 10, 400)
        dc.SetPen(wx.Pen(wx.Colour(0, 0, 0)))
        for i in range(4):
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
        del dc

class StlPlaterPanel(PlaterPanel):

    load_wildcard = _("STL files (*.stl;*.STL)|*.stl;*.STL|OpenSCAD files (*.scad)|*.scad")
    save_wildcard = _("STL files (*.stl;*.STL)|*.stl;*.STL")

    def prepare_ui(self, filenames = [], callback = None,
                   parent = None, build_dimensions = None, circular_platform = False,
                   simarrange_path = None, antialias_samples = 0):
        super().prepare_ui(filenames, callback, parent, build_dimensions)
        self.cutting = False
        self.cutting_axis = None
        self.cutting_dist = None
        if glview:
            viewer = stlview.StlViewPanel(self, wx.DefaultSize,
                                          build_dimensions = self.build_dimensions,
                                          circular = circular_platform,
                                          antialias_samples = antialias_samples)
            # Cutting tool
            nrows = self.menusizer.GetRows()
            self.menusizer.Add(wx.StaticText(self.menupanel, -1, _("Cut along:")),
                               pos = (nrows, 0), span = (1, 1), flag = wx.ALIGN_CENTER)
            cutconfirmbutton = wx.Button(self.menupanel, label = _("Confirm cut"))
            cutconfirmbutton.Bind(wx.EVT_BUTTON, self.cut_confirm)
            cutconfirmbutton.Disable()
            self.cutconfirmbutton = cutconfirmbutton
            self.menusizer.Add(cutconfirmbutton, pos = (nrows, 1), span = (1, 1), flag = wx.EXPAND)
            cutpanel = wx.Panel(self.menupanel)
            cutsizer = self.cutsizer = wx.BoxSizer(wx.HORIZONTAL)
            cutpanel.SetSizer(cutsizer)
            cutxplusbutton = wx.ToggleButton(cutpanel, label = _(">X"), style = wx.BU_EXACTFIT)
            cutxplusbutton.Bind(wx.EVT_TOGGLEBUTTON, lambda event: self.start_cutting_tool(event, "x", 1))
            cutsizer.Add(cutxplusbutton, 1, flag = wx.EXPAND)
            cutzplusbutton = wx.ToggleButton(cutpanel, label = _(">Y"), style = wx.BU_EXACTFIT)
            cutzplusbutton.Bind(wx.EVT_TOGGLEBUTTON, lambda event: self.start_cutting_tool(event, "y", 1))
            cutsizer.Add(cutzplusbutton, 1, flag = wx.EXPAND)
            cutzplusbutton = wx.ToggleButton(cutpanel, label = _(">Z"), style = wx.BU_EXACTFIT)
            cutzplusbutton.Bind(wx.EVT_TOGGLEBUTTON, lambda event: self.start_cutting_tool(event, "z", 1))
            cutsizer.Add(cutzplusbutton, 1, flag = wx.EXPAND)
            cutxminusbutton = wx.ToggleButton(cutpanel, label = _("<X"), style = wx.BU_EXACTFIT)
            cutxminusbutton.Bind(wx.EVT_TOGGLEBUTTON, lambda event: self.start_cutting_tool(event, "x", -1))
            cutsizer.Add(cutxminusbutton, 1, flag = wx.EXPAND)
            cutzminusbutton = wx.ToggleButton(cutpanel, label = _("<Y"), style = wx.BU_EXACTFIT)
            cutzminusbutton.Bind(wx.EVT_TOGGLEBUTTON, lambda event: self.start_cutting_tool(event, "y", -1))
            cutsizer.Add(cutzminusbutton, 1, flag = wx.EXPAND)
            cutzminusbutton = wx.ToggleButton(cutpanel, label = _("<Z"), style = wx.BU_EXACTFIT)
            cutzminusbutton.Bind(wx.EVT_TOGGLEBUTTON, lambda event: self.start_cutting_tool(event, "z", -1))
            cutsizer.Add(cutzminusbutton, 1, flag = wx.EXPAND)
            self.menusizer.Add(cutpanel, pos = (nrows + 1, 0), span = (1, 2), flag = wx.EXPAND)
        else:
            viewer = showstl(self, (580, 580), (0, 0))
        self.simarrange_path = simarrange_path
        self.set_viewer(viewer)

    def start_cutting_tool(self, event, axis, direction):
        toggle = event.EventObject
        self.cutting = toggle.Value
        if toggle.Value:
            # Disable the other toggles
            for child in self.cutsizer.Children:
                child = child.Window
                if child != toggle:
                    child.Value = False
            self.cutting_axis = axis
            self.cutting_direction = direction
        else:
            self.cutting_axis = None
            self.cutting_direction = None
        self.cutting_dist = None

    def cut_confirm(self, event):
        name = self.l.GetSelection()
        name = self.l.GetString(name)
        model = self.models[name]
        transformation = transformation_matrix(model)
        transformed = model.transform(transformation)
        logging.info(_("Cutting %s alongside %s axis") % (name, self.cutting_axis))
        axes = ["x", "y", "z"]
        cut = transformed.cut(axes.index(self.cutting_axis),
                              self.cutting_direction,
                              self.cutting_dist)
        cut.offsets = [0, 0, 0]
        cut.rot = 0
        cut.scale = model.scale
        cut.filename = model.filename
        cut.centeroffset = [0, 0, 0]
        self.s.prepare_model(cut, 2)
        self.models[name] = cut
        self.cutconfirmbutton.Disable()
        self.cutting = False
        self.cutting_axis = None
        self.cutting_dist = None
        self.cutting_direction = None
        for child in self.cutsizer.GetChildren():
            child = child.GetWindow()
            child.SetValue(False)

    def clickcb(self, event, single = False):
        if not isinstance(self.s, stlview.StlViewPanel):
            return
        if self.cutting:
            self.clickcb_cut(event)
        else:
            self.clickcb_rebase(event)

    def clickcb_cut(self, event):
        axis = self.cutting_axis
        self.cutting_dist, _, _ = self.s.get_cutting_plane(axis, None,
                                                           local_transform = True)
        if self.cutting_dist is not None:
            self.cutconfirmbutton.Enable()

    def clickcb_rebase(self, event):
        x, y = event.GetPosition()
        ray_near, ray_far = self.s.mouse_to_ray(x, y, local_transform = True)
        best_match = None
        best_facet = None
        best_dist = float("inf")
        for key, model in self.models.items():
            transformation = transformation_matrix(model)
            transformed = model.transform(transformation)
            if not transformed.intersect_box(ray_near, ray_far):
                logging.debug("Skipping %s for rebase search" % key)
                continue
            facet, facet_dist = transformed.intersect(ray_near, ray_far)
            if facet is not None and facet_dist < best_dist:
                best_match = key
                best_facet = facet
                best_dist = facet_dist
        if best_match is not None:
            logging.info("Rebasing %s" % best_match)
            model = self.models[best_match]
            newmodel = model.rebase(best_facet)
            newmodel.offsets = list(model.offsets)
            newmodel.rot = 0
            newmodel.scale = model.scale
            newmodel.filename = model.filename
            newmodel.centeroffset = [-(newmodel.dims[1] + newmodel.dims[0]) / 2,
                                     -(newmodel.dims[3] + newmodel.dims[2]) / 2,
                                     0]
            self.s.prepare_model(newmodel, 2)
            self.models[best_match] = newmodel
            wx.CallAfter(self.Refresh)

    def done(self, event, cb):
        if not os.path.exists("tempstl"):
            os.mkdir("tempstl")
        name = "tempstl/" + str(int(time.time()) % 10000) + ".stl"
        self.export_to(name)
        if cb is not None:
            cb(name)
        if self.destroy_on_done:
            self.Destroy()

    def load_file(self, filename):
        if filename.lower().endswith(".stl"):
            try:
                self.load_stl(filename)
            except:
                dlg = wx.MessageDialog(self, _("Loading STL file failed"),
                                       _("Error:") + traceback.format_exc(),
                                       wx.OK)
                dlg.ShowModal()
                logging.error(_("Loading STL file failed:")
                              + "\n" + traceback.format_exc())
        elif filename.lower().endswith(".scad"):
            try:
                self.load_scad(filename)
            except:
                dlg = wx.MessageDialog(self, _("Loading OpenSCAD file failed"),
                                       _("Error:") + traceback.format_exc(),
                                       wx.OK)
                dlg.ShowModal()
                logging.error(_("Loading OpenSCAD file failed:")
                              + "\n" + traceback.format_exc())

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
        if not os.path.exists(name):
            logging.error(_("Couldn't load non-existing file %s") % name)
            return
        path = os.path.split(name)[0]
        self.basedir = path
        if name.lower().endswith(".stl"):
            for model in self.models.values():
                if model.filename == name:
                    newmodel = copy(model)
                    newmodel.offsets = list(model.offsets)
                    newmodel.rot = model.rot
                    newmodel.scale = list(model.scale)
                    self.add_model(name, newmodel)
                    self.s.prepare_model(newmodel, 2)
                    break
            else:
                # Filter out the path, just show the STL filename.
                self.load_stl_into_model(name, name)
        wx.CallAfter(self.Refresh)

    def load_stl_into_model(self, path, name, offset = None, rotation = 0, scale = [1.0, 1.0, 1.0]):
        model = stltool.stl(path)
        if offset is None:
            offset = [self.build_dimensions[3], self.build_dimensions[4], 0]
        model.offsets = list(offset)
        model.rot = rotation
        model.scale = list(scale)
        model.filename = name
        self.add_model(name, model)
        model.centeroffset = [-(model.dims[1] + model.dims[0]) / 2,
                              -(model.dims[3] + model.dims[2]) / 2,
                              0]
        self.s.prepare_model(model, 2)

    def export_to(self, name):
        with open(name.replace(".", "_") + ".scad", "w") as sf:
            facets = []
            for model in self.models.values():
                r = model.rot
                o = model.offsets
                co = model.centeroffset
                sf.write("translate([%s, %s, %s])"
                         "rotate([0, 0, %s])"
                         "translate([%s, %s, %s])"
                         "import(\"%s\");\n" % (o[0], o[1], o[2],
                                                r,
                                                co[0], co[1], co[2],
                                                model.filename))
                model = model.transform(transformation_matrix(model))
                facets += model.facets
            stltool.emitstl(name, facets, "plater_export")
            logging.info(_("Wrote plate to %s") % name)

    def autoplate(self, event = None):
        if self.simarrange_path:
            try:
                self.autoplate_simarrange()
            except Exception as e:
                logging.warning(_("Failed to use simarrange for plating, "
                                  "falling back to the standard method. "
                                  "The error was: ") + e)
                super(StlPlaterPanel, self).autoplate()
        else:
            super(StlPlaterPanel, self).autoplate()

    def autoplate_simarrange(self):
        logging.info(_("Autoplating using simarrange"))
        models = dict(self.models)
        files = [model.filename for model in models.values()]
        command = [self.simarrange_path, "--dryrun",
                   "-m",  # Pack around center
                   "-x", str(int(self.build_dimensions[0])),
                   "-y", str(int(self.build_dimensions[1]))] + files
        p = subprocess.Popen(command, stdout = subprocess.PIPE, universal_newlines = True)

        pos_regexp = re.compile("File: (.*) minx: ([0-9]+), miny: ([0-9]+), minrot: ([0-9]+)")
        for line in p.stdout:
            line = line.rstrip()
            if "Generating plate" in line:
                plateid = int(line.split()[-1])
                if plateid > 0:
                    logging.error(_("Plate full, please remove some objects"))
                    break
            if "File:" in line:
                bits = pos_regexp.match(line).groups()
                filename = bits[0]
                x = float(bits[1])
                y = float(bits[2])
                rot = -float(bits[3])
                for name, model in list(models.items()):
                    # FIXME: not sure this is going to work superwell with utf8
                    if model.filename == filename:
                        model.offsets[0] = x + self.build_dimensions[3]
                        model.offsets[1] = y + self.build_dimensions[4]
                        model.rot = rot
                        del models[name]
                        break
        if p.wait() != 0:
            raise RuntimeError(_("simarrange failed"))

StlPlater = make_plater(StlPlaterPanel)
