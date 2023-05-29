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

import logging
import os
import types
import wx
from .gui.widgets import get_space

from .utils import install_locale, iconfile
install_locale('pronterface')

def patch_method(obj, method, replacement):
    orig_handler = getattr(obj, method)

    def wrapped(*a, **kwargs):
        kwargs['orig_handler'] = orig_handler
        return replacement(*a, **kwargs)
    setattr(obj, method, types.MethodType(wrapped, obj))

class PlaterPanel(wx.Panel):
    def __init__(self, **kwargs):
        self.destroy_on_done = False
        parent = kwargs.get("parent", None)
        super().__init__(parent = parent)
        self.prepare_ui(**kwargs)

    def prepare_ui(self, filenames = [], callback = None, parent = None, build_dimensions = None, cutting_tool = True):
        self.filenames = filenames
        self.cut_axis_buttons = []

        menu_sizer = self.menu_sizer = wx.BoxSizer(wx.VERTICAL)
        list_sizer = wx.StaticBoxSizer(wx.VERTICAL, self, label = "Models")
        # Load button
        loadbutton = wx.Button(self, label = _("+ Add Model"))
        loadbutton.Bind(wx.EVT_BUTTON, self.load)
        list_sizer.Add(loadbutton, 0, wx.EXPAND | wx.BOTTOM, get_space('mini'))
        # Model list
        self.l = wx.ListBox(self)
        list_sizer.Add(self.l, 1, wx.EXPAND | wx.BOTTOM, get_space('mini'))
        # Auto arrange button
        autobutton = wx.Button(self, label = _("Auto Arrange"))
        autobutton.Bind(wx.EVT_BUTTON, self.autoplate)
        list_sizer.Add(autobutton, 0, wx.EXPAND | wx.BOTTOM, get_space('mini'))
        h_sizer = wx.BoxSizer(wx.HORIZONTAL)
        # Clear button
        clearbutton = wx.Button(self, label = _("Clear All"))
        clearbutton.Bind(wx.EVT_BUTTON, self.clear)
        h_sizer.Add(clearbutton, 1, wx.EXPAND | wx.RIGHT, get_space('mini'))
        # Export button
        exportbutton = wx.Button(self, label = _("Export"))
        exportbutton.Bind(wx.EVT_BUTTON, self.export)
        h_sizer.Add(exportbutton, 1, wx.EXPAND)
        list_sizer.Add(h_sizer, 0, wx.EXPAND)

        selection_sizer = wx.StaticBoxSizer(wx.VERTICAL, self, label = "Selection")
        # Snap to Z = 0 button
        snapbutton = wx.Button(self, label = _("Snap to Zero"))
        snapbutton.Bind(wx.EVT_BUTTON, self.snap)
        h2_sizer = wx.BoxSizer(wx.HORIZONTAL)
        h2_sizer.Add(snapbutton, 1, wx.EXPAND | wx.RIGHT, get_space('mini'))
        # Put at center button
        centerbutton = wx.Button(self, label = _("Put at Center"))
        centerbutton.Bind(wx.EVT_BUTTON, self.center)
        h2_sizer.Add(centerbutton, 1, wx.EXPAND)
        selection_sizer.Add(h2_sizer, 0, wx.EXPAND | wx.BOTTOM, get_space('mini'))
        # Delete button
        deletebutton = wx.Button(self, label = _("Delete"))
        deletebutton.Bind(wx.EVT_BUTTON, self.delete)
        selection_sizer.Add(deletebutton, 0, wx.EXPAND | wx.ALL, get_space('none'))

        menu_sizer.Add(list_sizer, 1, wx.EXPAND | wx.ALL, get_space('minor'))
        menu_sizer.Add(selection_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, get_space('minor'))
        self.menu_buttons = [autobutton, clearbutton, exportbutton, snapbutton, centerbutton, deletebutton]

        if cutting_tool:
            # Insert Cutting tool (only for STL Plater)
            cut_sizer = wx.StaticBoxSizer(wx.VERTICAL, self, label = _("Cutting Tool"))
            # Prepare buttons for all cut axis
            axis_sizer = self.axis_sizer = wx.BoxSizer(wx.HORIZONTAL)
            cutxplusbutton = wx.ToggleButton(self, label = _("+X"), style = wx.BU_EXACTFIT)
            cutxplusbutton.Bind(wx.EVT_TOGGLEBUTTON, lambda event: self.start_cutting_tool(event, "x", 1))
            axis_sizer.Add(cutxplusbutton, 1, wx.EXPAND | wx.RIGHT, get_space('mini'))
            cutyplusbutton = wx.ToggleButton(self, label = _("+Y"), style = wx.BU_EXACTFIT)
            cutyplusbutton.Bind(wx.EVT_TOGGLEBUTTON, lambda event: self.start_cutting_tool(event, "y", 1))
            axis_sizer.Add(cutyplusbutton, 1, wx.EXPAND | wx.RIGHT, get_space('mini'))
            cutzplusbutton = wx.ToggleButton(self, label = _("+Z"), style = wx.BU_EXACTFIT)
            cutzplusbutton.Bind(wx.EVT_TOGGLEBUTTON, lambda event: self.start_cutting_tool(event, "z", 1))
            axis_sizer.Add(cutzplusbutton, 1, wx.EXPAND | wx.RIGHT, get_space('mini'))
            cutxminusbutton = wx.ToggleButton(self, label = _("-X"), style = wx.BU_EXACTFIT)
            cutxminusbutton.Bind(wx.EVT_TOGGLEBUTTON, lambda event: self.start_cutting_tool(event, "x", -1))
            axis_sizer.Add(cutxminusbutton, 1, wx.EXPAND | wx.RIGHT, get_space('mini'))
            cutyminusbutton = wx.ToggleButton(self, label = _("-Y"), style = wx.BU_EXACTFIT)
            cutyminusbutton.Bind(wx.EVT_TOGGLEBUTTON, lambda event: self.start_cutting_tool(event, "y", -1))
            axis_sizer.Add(cutyminusbutton, 1, wx.EXPAND | wx.RIGHT, get_space('mini'))
            cutzminusbutton = wx.ToggleButton(self, label = _("-Z"), style = wx.BU_EXACTFIT)
            cutzminusbutton.Bind(wx.EVT_TOGGLEBUTTON, lambda event: self.start_cutting_tool(event, "z", -1))
            axis_sizer.Add(cutzminusbutton, 1, flag = wx.EXPAND)
            self.cut_axis_buttons = [cutxplusbutton, cutyplusbutton, cutzplusbutton,
                                     cutxminusbutton, cutyminusbutton, cutzminusbutton]

            cut_sizer.Add(wx.StaticText(self, -1, _("Choose axis to cut along:")), 0, wx.BOTTOM, get_space('mini'))
            cut_sizer.Add(axis_sizer, 0, wx.EXPAND, wx.BOTTOM, get_space('minor'))
            cut_sizer.Add(wx.StaticText(self, -1, _("Doubleclick to set the cutting plane.")), 0, wx.TOP | wx.BOTTOM, get_space('mini'))
            # Process cut button
            self.cut_processbutton = wx.Button(self, label = _("Process Cut"))
            self.cut_processbutton.Bind(wx.EVT_BUTTON, lambda event: self.cut_confirm(event))
            cut_sizer.Add(self.cut_processbutton, 0, flag = wx.EXPAND)
            menu_sizer.Add(cut_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, get_space('minor'))
            self.enable_cut_button(False)

        self.enable_buttons(False)  # While no file is loaded all buttons are disabled
        self.basedir = "."
        self.models = {}
        self.topsizer = wx.GridBagSizer(vgap = 0, hgap = 0)
        self.topsizer.Add(menu_sizer, pos = (0, 0), span = (1, 1), flag = wx.EXPAND)
        self.topsizer.Add(wx.StaticLine(self, -1, style = wx.LI_HORIZONTAL), pos = (1, 0), span = (1, 2), flag = wx.EXPAND)

        if callback is not None:
            self.topsizer.Add(self.CreateButtonSizer(wx.OK | wx.CANCEL), pos = (2, 0), span = (1, 2),
                              flag = wx.ALIGN_RIGHT | wx.ALL, border = get_space('stddlg'))
            self.Bind(wx.EVT_BUTTON, lambda e: self.done(e, callback), id=wx.ID_OK)
            self.Bind(wx.EVT_BUTTON, lambda e: self.Destroy(), id=wx.ID_CANCEL)

        self.topsizer.AddGrowableRow(0)
        self.topsizer.AddGrowableCol(1)
        self.SetSizer(self.topsizer)
        self.build_dimensions = build_dimensions or [200, 200, 100, 0, 0, 0]

    def set_viewer(self, viewer):
        # Patch handle_rotation on the fly
        if hasattr(viewer, "handle_rotation"):
            def handle_rotation(self, event, orig_handler):
                if self.initpos is None:
                    self.initpos = event.GetPosition()
                else:
                    if event.ShiftDown():
                        p1 = self.initpos
                        p2 = event.GetPosition()
                        x1, y1, _ = self.mouse_to_3d(p1[0], p1[1])
                        x2, y2, _ = self.mouse_to_3d(p2[0], p2[1])
                        self.parent.move_shape((x2 - x1, y2 - y1))
                        self.initpos = p2
                    else:
                        orig_handler(event)
            patch_method(viewer, "handle_rotation", handle_rotation)
        # Patch handle_wheel on the fly
        if hasattr(viewer, "handle_wheel"):
            def handle_wheel(self, event, orig_handler):
                if event.ShiftDown():
                    angle = 10
                    if event.GetWheelRotation() < 0:
                        angle = -angle
                    self.parent.rotate_shape(angle / 2)
                else:
                    orig_handler(event)
            patch_method(viewer, "handle_wheel", handle_wheel)
        self.s = viewer
        self.s.SetMinSize((150, 150))
        self.topsizer.Add(self.s, pos = (0, 1), span = (1, 1), flag = wx.EXPAND)

    def move_shape(self, delta):
        """moves shape (selected in l, which is list ListBox of shapes)
        by an offset specified in tuple delta.
        Positive numbers move to (rigt, down)"""
        name = self.l.GetSelection()
        if name == wx.NOT_FOUND:
            return False

        name = self.l.GetString(name)

        model = self.models[name]
        model.offsets = [model.offsets[0] + delta[0],
                         model.offsets[1] + delta[1],
                         model.offsets[2]
                         ]
        return True

    def rotate_shape(self, angle):
        """rotates active shape
        positive angle is clockwise
        """
        name = self.l.GetSelection()
        if name == wx.NOT_FOUND:
            return False
        name = self.l.GetString(name)
        model = self.models[name]
        model.rot += angle
        return True

    def autoplate(self, event = None):
        logging.info(_("Autoplating"))
        separation = 2
        try:
            from printrun import packer
            p = packer.Packer()
            for i, model in self.models.items():
                width = abs(model.dims[0] - model.dims[1])
                height = abs(model.dims[2] - model.dims[3])
                p.add_rect(width, height, data = i)
            centerx = self.build_dimensions[0] / 2 + self.build_dimensions[3]
            centery = self.build_dimensions[1] / 2 + self.build_dimensions[4]
            rects = p.pack(padding = separation,
                           center = packer.Vector2(centerx, centery))
            for rect in rects:
                i = rect.data
                position = rect.center()
                self.models[i].offsets[0] = position.x
                self.models[i].offsets[1] = position.y
        except ImportError:
            bedsize = self.build_dimensions[0:3]
            cursor = [0, 0, 0]
            newrow = 0
            max = [0, 0]
            for i, model in self.models.items():
                model.offsets[2] = -1.0 * model.dims[4]
                x = abs(model.dims[0] - model.dims[1])
                y = abs(model.dims[2] - model.dims[3])
                centre = [x / 2, y / 2]
                centreoffset = [model.dims[0] + centre[0],
                                model.dims[2] + centre[1]]
                if (cursor[0] + x + separation) >= bedsize[0]:
                    cursor[0] = 0
                    cursor[1] += newrow + separation
                    newrow = 0
                if (newrow == 0) or (newrow < y):
                    newrow = y
                # To the person who works out why the offsets are applied
                # differently here:
                #    Good job, it confused the hell out of me.
                model.offsets[0] = cursor[0] + centre[0] - centreoffset[0]
                model.offsets[1] = cursor[1] + centre[1] - centreoffset[1]
                if (max[0] == 0) or (max[0] < (cursor[0] + x)):
                    max[0] = cursor[0] + x
                if (max[1] == 0) or (max[1] < (cursor[1] + x)):
                    max[1] = cursor[1] + x
                cursor[0] += x + separation
                if (cursor[1] + y) >= bedsize[1]:
                    logging.info(_("Bed full, sorry sir :("))
                    self.Refresh()
                    return
            centerx = self.build_dimensions[0] / 2 + self.build_dimensions[3]
            centery = self.build_dimensions[1] / 2 + self.build_dimensions[4]
            centreoffset = [centerx - max[0] / 2, centery - max[1] / 2]
            for i, model in self.models.items():
                model.offsets[0] += centreoffset[0]
                model.offsets[1] += centreoffset[1]
        self.Refresh()

    def clear(self, event):
        result = wx.MessageBox(_('Are you sure you want to clear the grid? All unsaved changes will be lost.'),
                               _('Clear the grid?'),
                               wx.YES_NO | wx.ICON_QUESTION)
        if result == 2:
            self.models = {}
            self.l.Clear()
            self.enable_buttons(False)
            if self.cut_axis_buttons:
                self.enable_cut_button(False)
            self.Refresh()

    def enable_buttons(self, value):
        # A helper method to give the user a cue which tools are available
        for button in self.menu_buttons:
            button.Enable(value)

        if self.cut_axis_buttons:  # Only STL Plater has cut axis buttons
            for button in self.cut_axis_buttons:
                button.SetValue(False)
                button.Enable(value)

        self.Refresh()

    def enable_cut_button(self, value):
        self.cut_processbutton.Enable(value)
        self.Refresh()

    def center(self, event):
        i = self.l.GetSelection()
        if i != -1:
            m = self.models[self.l.GetString(i)]
            centerx = self.build_dimensions[0] / 2 + self.build_dimensions[3]
            centery = self.build_dimensions[1] / 2 + self.build_dimensions[4]
            m.offsets = [centerx, centery, m.offsets[2]]
            self.Refresh()

    def snap(self, event):
        i = self.l.GetSelection()
        if i != -1:
            m = self.models[self.l.GetString(i)]
            m.offsets[2] = -m.dims[4]
            self.Refresh()

    def delete(self, event):
        i = self.l.GetSelection()
        if i != -1:
            del self.models[self.l.GetString(i)]
            self.l.Delete(i)
            self.l.Select(self.l.GetCount() - 1)
            if self.l.GetCount() < 1:
                self.enable_buttons(False)
                if self.cut_axis_buttons:
                    self.enable_cut_button(False)
            self.Refresh()

    def add_model(self, name, model):
        newname = os.path.split(name.lower())[1]
        if not isinstance(newname, str):
            newname = str(newname, "utf-8")
        c = 1
        while newname in self.models:
            newname = os.path.split(name.lower())[1]
            newname = newname + "(%d)" % c
            c += 1
        self.models[newname] = model

        self.l.Append(newname)
        i = self.l.GetSelection()
        if i == wx.NOT_FOUND:
            self.l.Select(0)

        self.l.Select(self.l.GetCount() - 1)
        self.enable_buttons(True)

    def load(self, event):
        dlg = wx.FileDialog(self, _("Pick file to load"), self.basedir, style = wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
        dlg.SetWildcard(self.load_wildcard)
        if dlg.ShowModal() == wx.ID_OK:
            name = dlg.GetPath()
            self.enable_buttons(True)
            self.load_file(name)
        dlg.Destroy()

    def load_file(self, filename):
        raise NotImplementedError

    def export(self, event):
        dlg = wx.FileDialog(self, _("Pick file to save to"), self.basedir, style = wx.FD_SAVE)
        dlg.SetWildcard(self.save_wildcard)
        if dlg.ShowModal() == wx.ID_OK:
            name = dlg.GetPath()
            self.export_to(name)
        dlg.Destroy()

    def export_to(self, name):
        raise NotImplementedError

class Plater(wx.Dialog):
    def __init__(self, **kwargs):
        self.destroy_on_done = True
        parent = kwargs.get("parent", None)
        size = kwargs.get("size", (800, 580))
        if "size" in kwargs:
            del kwargs["size"]
        wx.Dialog.__init__(self, parent, title = _("STL Plate Builder"),
                           size = size, style = wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.SetIcon(wx.Icon(iconfile("plater.png"), wx.BITMAP_TYPE_PNG))
        self.prepare_ui(**kwargs)
        self.CenterOnParent()


def make_plater(panel_class):
    name = panel_class.__name__.replace("Panel", "")
    return type(name, (Plater, panel_class), {})
