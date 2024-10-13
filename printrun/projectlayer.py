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

import xml.etree.ElementTree as ET
import wx
import wx.svg
import os
import time
import zipfile
import tempfile
import puremagic
import copy
import re
from collections import OrderedDict
import math
from printrun.gui.widgets import get_space
from .utils import install_locale

# Set up Internationalization using gettext
install_locale('pronterface')


class DisplayFrame(wx.Frame):
    def __init__(self, parent, statusbar, title, res = (1024, 768), printer = None, scale = 1.0, offset = (0, 0)):
        super().__init__(parent = parent, title = title, size = res)

        self.printer = printer
        self.control_frame = parent
        self.slicer = 'Bitmap'
        self.dpi = 96
        self.status = statusbar
        self.scale = scale
        self.index = 0
        self.offset = offset
        self.running = False
        self.layer_red = False
        self.startime = 0

        # Closing the DisplayFrame calls the close method of Settingsframe
        self.Bind(wx.EVT_CLOSE, self.control_frame.on_close)

        x_res = self.control_frame.X.GetValue()
        y_res = self.control_frame.Y.GetValue()
        self.size = (x_res, y_res)
        self.bitmap = wx.Bitmap(*self.size)
        dc = wx.MemoryDC(self.bitmap)
        dc.SetBackground(wx.BLACK_BRUSH)
        dc.Clear()
        dc.SelectObject(wx.NullBitmap)

        panel = wx.Panel(self)
        panel.SetBackgroundColour(wx.BLACK)
        self.bitmap_widget = wx.GenericStaticBitmap(panel, -1, self.bitmap)
        self.bitmap_widget.SetScaleMode(0)
        self.bitmap_widget.Hide()
        sizer = wx.BoxSizer()
        sizer.Add(self.bitmap_widget, wx.ALIGN_LEFT | wx.ALIGN_TOP)
        panel.SetSizer(sizer)

        self.SetDoubleBuffered(True)
        self.CentreOnParent()

    def clear_layer(self):
        dc = wx.MemoryDC(self.bitmap)
        dc.SetBackground(wx.BLACK_BRUSH)
        dc.Clear()
        dc.SelectObject(wx.NullBitmap)
        self.bitmap_widget.SetBitmap(self.bitmap)
        self.bitmap_widget.Show()
        self.Refresh()

    def resize(self, res = (1024, 768)):
        self.bitmap = wx.Bitmap(*res)
        dc = wx.MemoryDC(self.bitmap)
        dc.SetBackground(wx.BLACK_BRUSH)
        dc.Clear()
        dc.SelectObject(wx.NullBitmap)
        self.Refresh()

    def convert_mm_to_px(self, mm_value) -> float:
        resolution_x_px = self.control_frame.X.GetValue()
        projected_x_mm = self.control_frame.projected_X_mm.GetValue()
        return resolution_x_px / projected_x_mm * mm_value

    def draw_layer(self, image = None):
        dc = wx.MemoryDC(self.bitmap)
        dc.SetBackground(wx.BLACK_BRUSH)
        dc.Clear()
        gc = wx.GraphicsContext.Create(dc)

        if self.slicer in ['Slic3r', 'Skeinforge']:

            if self.layer_red:
                image.set('style', 'background-color: black; fill: red;')
                for element in image.findall('{http://www.w3.org/2000/svg}g')[0]:
                    if element.get('fill') == 'white':
                        element.set('fill', 'red')
                    if element.get('style') == 'fill: white':
                        element.set('style', 'fill: red')

            svg_image = wx.svg.SVGimage.CreateFromBytes(ET.tostring(image), units = 'px', dpi = self.dpi)

            self.status(f"Scaled width: {svg_image.width / self.dpi * 25.4 * self.scale:.2f} mm @ {round(svg_image.width * self.scale)} px")

            gc.Translate(self.convert_mm_to_px(self.offset[0]), self.convert_mm_to_px(self.offset[1]))
            gc.Scale(self.scale, self.scale)
            svg_image.RenderToGC(gc)

        elif self.slicer in ('Bitmap', 'PrusaSlicer'):
            if isinstance(image, str):
                image = wx.Image(image)
            if self.layer_red:
                image = image.AdjustChannels(1, 0, 0, 1)
            width, height = image.GetSize()
            if width < height:
                image = image.Rotate90(clockwise = False)
            real_width = max(width, height)
            bitmap = gc.CreateBitmapFromImage(image)

            self.status(f"Scaled width: {real_width / self.dpi * 25.4 * self.scale:.2f} mm @ {round(real_width * self.scale)} px")

            gc.Translate(self.convert_mm_to_px(self.offset[0]), self.convert_mm_to_px(self.offset[1]))
            gc.Scale(self.scale, self.scale)
            gc.DrawBitmap(bitmap, 0, 0, image.Width, image.Height)

        elif 'Calibrate' in self.slicer:
            #gc.Translate(self.convert_mm_to_px(self.offset[0]), self.convert_mm_to_px(self.offset[1]))
            #gc.Scale(self.scale, self.scale)
            self.draw_grid(gc)

        else:
            self.status(_("No valid file loaded."))
            return

        dc.SelectObject(wx.NullBitmap)
        self.bitmap_widget.SetBitmap(self.bitmap)
        self.bitmap_widget.Show()
        self.Refresh()

    def draw_grid(self, graphics_context):
        gc = graphics_context

        x_res_px = self.control_frame.X.GetValue()
        y_res_px = self.control_frame.Y.GetValue()

        # Draw outline
        path = gc.CreatePath()
        path.AddRectangle(0, 0, x_res_px, y_res_px)
        path.AddCircle(0, 0, 5.0)
        path.AddCircle(0, 0, 14.0)

        solid_pen = gc.CreatePen(wx.GraphicsPenInfo(wx.RED).Width(5.0).Style(wx.PENSTYLE_SOLID))
        gc.SetPen(solid_pen)
        gc.StrokePath(path)

        # Calculate gridlines
        aspectRatio = x_res_px / y_res_px

        projected_x_mm = self.control_frame.projected_X_mm.GetValue()
        projected_y_mm = round(projected_x_mm / aspectRatio, 2)

        px_per_mm = x_res_px / projected_x_mm

        grid_count_x = int(projected_x_mm / 10)
        grid_count_y = int(projected_y_mm / 10)

        # Draw gridlines
        path = gc.CreatePath()
        for y in range(1, grid_count_y + 1):
            for x in range(1, grid_count_x + 1):
                # horizontal line
                path.MoveToPoint(0, int(y * (px_per_mm * 10)))
                path.AddLineToPoint(x_res_px, int(y * (px_per_mm * 10)))
                # vertical line
                path.MoveToPoint(int(x * (px_per_mm * 10)), 0)
                path.AddLineToPoint(int(x * (px_per_mm * 10)), y_res_px)

        thin_pen = gc.CreatePen(wx.GraphicsPenInfo(wx.RED).Width(2.0).Style(wx.PENSTYLE_DOT))
        gc.SetPen(thin_pen)
        gc.StrokePath(path)

    def show_img_delay(self, image):
        self.status(_("Showing, Runtime {:.3f} s").format(time.perf_counter() - self.startime))
        self.control_frame.set_current_layer(self.index)
        self.draw_layer(image)
        # AGe 2022-07-31 Python 3.10 and CallLater expects delay in milliseconds as
        # integer value instead of float. Convert float value to int
        timer = wx.CallLater(int(1000 * self.interval), self.hide_pic_and_rise)
        self.control_frame.timers['delay'] = timer

    def rise(self):
        if self.direction == 0:  # 0: Top Down
            self.status(_("Lowering, Runtime {:.3f} s").format(time.perf_counter() - self.startime))
        else:  # self.direction == 1, 1: Bottom Up
            self.status(_("Rising, Runtime {:.3f} s").format(time.perf_counter() - self.startime))

        if self.printer is not None and self.printer.online:
            self.printer.send_now('G91')

            if self.prelift_gcode:
                for line in self.prelift_gcode.split('\n'):
                    if line:
                        self.printer.send_now(line)

            if self.direction == 0:  # 0: Top Down
                self.printer.send_now(f"G1 Z-{self.overshoot:.3f} F{self.z_axis_rate}")
                self.printer.send_now(f"G1 Z{self.overshoot - self.thickness:.3f} F{self.z_axis_rate}")
            else:  # self.direction == 1, 1: Bottom Up
                self.printer.send_now(f"G1 Z{self.overshoot:.3f} F{self.z_axis_rate}")
                self.printer.send_now(f"G1 Z-{self.overshoot - self.thickness:.3f} F{self.z_axis_rate}")

            if self.postlift_gcode:
                for line in self.postlift_gcode.split('\n'):
                    if line:
                        self.printer.send_now(line)

            self.printer.send_now('G90')
        else:
            time.sleep(self.pause)

        # AGe 2022-07-31 Python 3.10 expects delay in milliseconds as
        # integer value instead of float. Convert float value to int
        timer = wx.CallLater(int(1000 * self.pause), self.next_img)
        self.control_frame.timers['rise'] = timer

    def hide_pic(self):
        self.status(_("Hiding, Runtime {:.3f} s").format(time.perf_counter() - self.startime))
        self.bitmap_widget.Hide()

    def hide_pic_and_rise(self):
        wx.CallAfter(self.hide_pic)
        timer = wx.CallLater(500, self.rise)
        self.control_frame.timers['hide'] = timer


    def next_img(self):
        if not self.running:
            return
        if self.index < len(self.layers):
            self.status(str(self.index))
            wx.CallAfter(self.show_img_delay, self.layers[self.index])
            self.index += 1
        else:
            self.control_frame.stop_present(wx.wxEVT_NULL)
            self.status(_("End"))
            wx.CallAfter(self.bitmap_widget.Hide)
            wx.CallAfter(self.Refresh)

    def present(self,
                layers,
                interval = 0.5,
                pause = 0.2,
                overshoot = 0.0,
                z_axis_rate = 200,
                prelift_gcode = "",
                postlift_gcode = "",
                direction = 0,  # 0: Top Down
                thickness = 0.4,
                scale = 1,
                size = (1024, 768),
                offset = (0, 0),
                layer_red = False):
        wx.CallAfter(self.bitmap_widget.Hide)
        wx.CallAfter(self.Refresh)
        self.layers = layers
        self.scale = scale
        self.thickness = thickness
        self.size = size
        self.interval = interval
        self.pause = pause
        self.overshoot = overshoot
        self.z_axis_rate = z_axis_rate
        self.prelift_gcode = prelift_gcode
        self.postlift_gcode = postlift_gcode
        self.direction = direction
        self.layer_red = layer_red
        self.offset = offset
        self.index = 0
        self.running = True

        self.next_img()


class SettingsFrame(wx.Dialog):

    def _set_setting(self, name, value):
        if self.pronterface:
            self.pronterface.set(name, value)

    def _get_setting(self, name, val):
        if self.pronterface:
            try:
                return getattr(self.pronterface.settings, name)
            except AttributeError:
                return val
        else:
            return val

    def __init__(self, parent, printer = None):
        super().__init__(parent, title = _("Layer Projector Control"),
                         style = wx.DEFAULT_DIALOG_STYLE | wx.DIALOG_NO_PARENT)
        self.pronterface = parent
        self.image_dir = ''
        self.current_filename = ''
        self.slicer = ''
        self.timers = {}

        # In wxPython 4.1.0 gtk3 (phoenix) wxWidgets 3.1.4
        # Layout() breaks before Show(), invoke once after Show()
        def fit(ev):
            self.Fit()
            self.Unbind(wx.EVT_ACTIVATE, handler=fit)
        self.Bind(wx.EVT_ACTIVATE, fit)

        self.panel = wx.Panel(self)

        buttonGroup = wx.StaticBox(self.panel, label = _("Controls"))
        buttonbox = wx.StaticBoxSizer(buttonGroup, wx.HORIZONTAL)

        self.load_button = wx.Button(buttonGroup, -1, _("Load"))
        self.load_button.Bind(wx.EVT_BUTTON, self.load_file)
        self.load_button.SetToolTip(_("Choose a SVG file created from Slic3r or Skeinforge, a PrusaSlicer SL1-file "
                                      "or a zip file of bitmap images (.3dlp.zip)."))
        buttonbox.Add(self.load_button, 1,
                      flag = wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, border = get_space('mini'))

        self.present_button = wx.Button(buttonGroup, -1, _("Start"))
        self.present_button.Bind(wx.EVT_BUTTON, self.start_present)
        self.present_button.SetToolTip(_("Starts the presentation of the slices."))
        buttonbox.Add(self.present_button, 1,
                      flag = wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, border = get_space('mini'))
        self.present_button.Disable()

        self.pause_button = wx.Button(buttonGroup, -1, self.get_btn_label('pause'))
        self.pause_button.Bind(wx.EVT_BUTTON, self.pause_present)
        self.pause_button.SetToolTip(_("Pauses the presentation. Can be resumed afterwards by "
                                       "clicking this button, or restarted by clicking start again."))
        buttonbox.Add(self.pause_button, 1,
                      flag = wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, border = get_space('mini'))
        self.pause_button.Disable()

        self.stop_button = wx.Button(buttonGroup, -1, _("Stop"))
        self.stop_button.Bind(wx.EVT_BUTTON, self.stop_present)
        self.stop_button.SetToolTip(_("Stops presenting the slices."))
        buttonbox.Add(self.stop_button, 1,
                      flag = wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, border = get_space('mini'))
        self.stop_button.Disable()

        settingsGroup = wx.StaticBox(self.panel, label = _("Settings"))
        fieldboxsizer = wx.StaticBoxSizer(settingsGroup, wx.VERTICAL)
        fieldsizer = wx.GridBagSizer(vgap = get_space('minor'), hgap = get_space('minor'))

        # Left Column
        fieldsizer.Add(wx.StaticText(settingsGroup, -1, _("Layerheight (mm):")), pos = (0, 0),
                       flag = wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        self.thickness = wx.SpinCtrlDouble(settingsGroup, -1, initial = self._get_setting("project_layer", 0.1),
                                           inc = 0.01, size = (125, -1))
        self.thickness.SetDigits(3)
        self.thickness.Bind(wx.EVT_SPINCTRLDOUBLE, self.update_thickness)
        self.thickness.SetToolTip(_("The thickness of each slice. Should match the value used to slice the model. "
                                    "SVG files update this value automatically, 3dlp.zip files have to be manually entered."))
        fieldsizer.Add(self.thickness, pos = (0, 1))

        fieldsizer.Add(wx.StaticText(settingsGroup, -1, _("Exposure (s):")), pos = (1, 0),
                       flag = wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        self.interval = wx.SpinCtrlDouble(settingsGroup, -1, initial = self._get_setting("project_interval", 0.5),
                                          inc = 0.1, size = (125, -1))
        self.interval.SetDigits(2)
        self.interval.Bind(wx.EVT_SPINCTRLDOUBLE, self.update_interval)
        self.interval.SetToolTip(_("How long each slice should be displayed."))
        fieldsizer.Add(self.interval, pos = (1, 1))

        fieldsizer.Add(wx.StaticText(settingsGroup, -1, _("Blank (s):")), pos = (2, 0),
                       flag = wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        self.pause = wx.SpinCtrlDouble(settingsGroup, -1, initial = self._get_setting("project_pause", 0.5),
                                       inc = 0.1, size = (125, -1))
        self.pause.SetDigits(2)
        self.pause.Bind(wx.EVT_SPINCTRLDOUBLE, self.update_pause)
        self.pause.SetToolTip(_("The pause length between slices. This should take into account any movement of the Z axis, "
                                "plus time to prepare the resin surface (sliding, tilting, sweeping, etc)."))
        fieldsizer.Add(self.pause, pos = (2, 1))

        fieldsizer.Add(wx.StaticText(settingsGroup, -1, _("Scale:")), pos = (3, 0),
                       flag = wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        self.scale = wx.SpinCtrlDouble(settingsGroup, -1, initial = self._get_setting('project_scale', 1.0),
                                       inc = 0.1, min = 0.05, size = (125, -1))
        self.scale.SetDigits(3)
        self.scale.Bind(wx.EVT_SPINCTRLDOUBLE, self.update_scale)
        self.scale.SetToolTip(_("The additional scaling of each slice."))
        fieldsizer.Add(self.scale, pos = (3, 1))

        fieldsizer.Add(wx.StaticText(settingsGroup, -1, _("Direction:")), pos = (4, 0),
                       flag = wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        self.direction = wx.Choice(settingsGroup, -1, choices = [_('Top Down'), _('Bottom Up')], size = (125, -1))

        saved_direction = self._get_setting('project_direction', 0)
        try:  # This setting used to be a string, older values need to be replaced with an index
            int(saved_direction)
        except ValueError:
            saved_direction = 1 if saved_direction == "Bottom Up" else 0
            self._set_setting('project_direction', saved_direction)

        self.direction.SetSelection(int(saved_direction))
        self.direction.Bind(wx.EVT_CHOICE, self.update_direction)
        self.direction.SetToolTip(_("The direction the Z axis should move. Top Down is where the projector is above "
                                    "the model, Bottom up is where the projector is below the model."))
        fieldsizer.Add(self.direction, pos = (4, 1), flag = wx.ALIGN_CENTER_VERTICAL)

        fieldsizer.Add(wx.StaticText(settingsGroup, -1, _("Overshoot (mm):")), pos = (5, 0),
                       flag = wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        self.overshoot = wx.SpinCtrlDouble(settingsGroup, -1, initial = self._get_setting('project_overshoot', 3.0),
                                           inc = 0.1, min = 0, size = (125, -1))
        self.overshoot.SetDigits(1)
        self.overshoot.Bind(wx.EVT_SPINCTRLDOUBLE, self.update_overshoot)
        self.overshoot.SetToolTip(_("How far the axis should move beyond the next slice position for each slice. "
                                    "For Top Down printers this would dunk the model under the resi and then return. "
                                    "For Bottom Up printers this would raise the base away from the vat and then return."))
        fieldsizer.Add(self.overshoot, pos = (5, 1))

        fieldsizer.Add(wx.StaticText(settingsGroup, -1, _("Pre-lift Gcode:")), pos = (6, 0),
                       flag = wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        self.prelift_gcode = wx.TextCtrl(settingsGroup, -1, str(self._get_setting("project_prelift_gcode", "").replace("\\n", '\n')),
                                         size = (-1, 35), style = wx.TE_MULTILINE)
        self.prelift_gcode.SetToolTip(_("Additional gcode to run before raising the Z-axis. "
                                        "Be sure to take into account any additional time needed "
                                        "in the pause value, and be careful what gcode is added!"))
        self.prelift_gcode.Bind(wx.EVT_TEXT, self.update_prelift_gcode)
        fieldsizer.Add(self.prelift_gcode, pos = (6, 1), span = (2, 1), flag = wx.EXPAND)

        fieldsizer.Add(wx.StaticText(settingsGroup, -1, _("Post-lift Gcode:")), pos = (6, 2),
                       flag = wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        self.postlift_gcode = wx.TextCtrl(settingsGroup, -1, str(self._get_setting("project_postlift_gcode", "").replace("\\n", '\n')),
                                          size = (-1, 35), style = wx.TE_MULTILINE)
        self.postlift_gcode.SetToolTip(_("Additional gcode to run after raising the Z-axis. Be sure to take "
                                         "into account any additional time needed in the pause value, "
                                         "and be careful what gcode is added!"))
        self.postlift_gcode.Bind(wx.EVT_TEXT, self.update_postlift_gcode)
        fieldsizer.Add(self.postlift_gcode, pos = (6, 3), span = (2, 1), flag = wx.EXPAND)

        # Right Column
        fieldsizer.Add(wx.StaticText(settingsGroup, -1, _("X Resolution (px):")), pos = (0, 2), flag = wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        projectX = int(math.floor(float(self._get_setting("project_x", 1920))))
        self.X = wx.SpinCtrl(settingsGroup, -1, str(projectX), max = 999999, size = (125, -1))
        self.X.Bind(wx.EVT_SPINCTRL, self.update_resolution)
        self.X.SetToolTip(_("The projector resolution in the X axis."))
        fieldsizer.Add(self.X, pos = (0, 3))

        fieldsizer.Add(wx.StaticText(settingsGroup, -1, _("Y Resolution (px):")), pos = (1, 2), flag = wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        projectY = int(math.floor(float(self._get_setting("project_y", 1200))))
        self.Y = wx.SpinCtrl(settingsGroup, -1, str(projectY), max = 999999, size = (125, -1))
        self.Y.Bind(wx.EVT_SPINCTRL, self.update_resolution)
        self.Y.SetToolTip(_("The projector resolution in the Y axis."))
        fieldsizer.Add(self.Y, pos = (1, 3))

        fieldsizer.Add(wx.StaticText(settingsGroup, -1, _("Offset in X (mm):")), pos = (2, 2),
                       flag = wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        self.offset_X = wx.SpinCtrlDouble(settingsGroup, -1, initial = self._get_setting("project_offset_x", 0.0),
                                          inc = 1, size = (125, -1))
        self.offset_X.SetDigits(1)
        self.offset_X.Bind(wx.EVT_SPINCTRLDOUBLE, self.update_offset)
        self.offset_X.SetToolTip(_("How far the slice should be offset from the edge in the X axis."))
        fieldsizer.Add(self.offset_X, pos = (2, 3))

        fieldsizer.Add(wx.StaticText(settingsGroup, -1, _("Offset in Y (mm):")), pos = (3, 2),
                       flag = wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        self.offset_Y = wx.SpinCtrlDouble(settingsGroup, -1, initial = self._get_setting("project_offset_y", 0.0),
                                          inc = 1, size = (125, -1))
        self.offset_Y.SetDigits(1)
        self.offset_Y.Bind(wx.EVT_SPINCTRLDOUBLE, self.update_offset)
        self.offset_Y.SetToolTip(_("How far the slice should be offset from the edge in the Y axis."))
        fieldsizer.Add(self.offset_Y, pos = (3, 3))

        fieldsizer.Add(wx.StaticText(settingsGroup, -1, _("Projected X (mm):")), pos = (4, 2),
                       flag = wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        self.projected_X_mm = wx.SpinCtrlDouble(settingsGroup, -1, initial = self._get_setting("project_projected_x", 100.0),
                                                inc = 0.5, size = (125, -1), min = 1.0, max = 999.9, style = wx.SP_ARROW_KEYS)
        self.projected_X_mm.SetDigits(2)
        self.projected_X_mm.Bind(wx.EVT_SPINCTRLDOUBLE, self.update_projected_Xmm)
        self.projected_X_mm.SetToolTip(_("The actual width of the entire projected image. Use the Calibrate "
                                         "grid to show the full size of the projected image, and measure "
                                         "the width at the same level where the slice will be projected onto the resin."))
        fieldsizer.Add(self.projected_X_mm, pos = (4, 3))

        fieldsizer.Add(wx.StaticText(settingsGroup, -1, _("Z-Axis Speed (mm/min):")), pos = (5, 2),
                       flag = wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        self.z_axis_rate = wx.SpinCtrl(settingsGroup, -1, str(self._get_setting("project_z_axis_rate", 200)),
                                       max = 9999, size = (125, -1))
        self.z_axis_rate.Bind(wx.EVT_SPINCTRL, self.update_z_axis_rate)
        self.z_axis_rate.SetToolTip(_("Speed of the Z axis in mm/minute. Take into account that "
                                      "slower rates may require a longer pause value."))
        fieldsizer.Add(self.z_axis_rate, pos = (5, 3))

        fieldboxsizer.Add(fieldsizer)

        # Display
        displayGroup = wx.StaticBox(self.panel, -1, _("Display"))
        displayboxsizer = wx.StaticBoxSizer(displayGroup)
        displaysizer = wx.BoxSizer(wx.HORIZONTAL)

        self.fullscreen = wx.CheckBox(displayGroup, -1, _("Fullscreen"))
        self.fullscreen.Bind(wx.EVT_CHECKBOX, self.update_fullscreen)
        self.fullscreen.SetToolTip(_("Toggles the project screen to full size."))
        displaysizer.Add(self.fullscreen, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, get_space('staticbox'))
        displaysizer.AddStretchSpacer(1)

        self.calibrate = wx.CheckBox(displayGroup, -1, _("Calibrate"))
        self.calibrate.Bind(wx.EVT_CHECKBOX, self.show_calibrate)
        self.calibrate.SetToolTip(_("Toggles the calibration grid. Each grid should be 10 mm x 10 mm in size.") +
                                  _(" Use the grid to ensure the projected size is correct. "
                                    "See also the help for the ProjectedX field."))
        displaysizer.Add(self.calibrate, 0, wx.ALIGN_CENTER_VERTICAL)
        displaysizer.AddStretchSpacer(1)

        first_layer_boxer = wx.BoxSizer(wx.HORIZONTAL)
        self.first_layer = wx.CheckBox(displayGroup, -1, _("1st Layer"))
        self.first_layer.Bind(wx.EVT_CHECKBOX, self.show_first_layer)
        self.first_layer.SetToolTip(_("Displays the first layer of the model. Use this to project "
                                      "the first layer for longer so it holds to the base. Note: "
                                      "this value does not affect the first layer when the 'Start' "
                                      "run is started, it should be used manually."))

        first_layer_boxer.Add(self.first_layer, flag = wx.ALIGN_CENTER_VERTICAL)

        first_layer_boxer.Add(wx.StaticText(displayGroup, -1, "(s):"), flag = wx.ALIGN_CENTER_VERTICAL)
        self.show_first_layer_timer = wx.SpinCtrlDouble(displayGroup, -1, initial = -1, min = -1, inc = 1, size = (125, -1))
        self.show_first_layer_timer.SetDigits(1)
        self.show_first_layer_timer.SetToolTip(_("How long to display the first layer for. -1 = unlimited."))
        first_layer_boxer.Add(self.show_first_layer_timer, flag = wx.ALIGN_CENTER_VERTICAL | wx.LEFT, border = get_space('mini'))
        displaysizer.Add(first_layer_boxer, 0, wx.ALIGN_CENTER_VERTICAL)
        displaysizer.AddStretchSpacer(1)

        self.layer_red = wx.CheckBox(displayGroup, -1, _("Red"))
        self.layer_red.Bind(wx.EVT_CHECKBOX, self.show_layer_red)
        self.layer_red.SetToolTip(_("Toggles whether the image should be red. Useful for positioning "
                                    "whilst resin is in the printer as it should not cause a reaction."))
        displaysizer.Add(self.layer_red, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, get_space('staticbox'))

        displayboxsizer.Add(displaysizer, 1, wx.EXPAND)

        # Info
        infoGroup = wx.StaticBox(self.panel, label = _("Info"))
        infosizer = wx.StaticBoxSizer(infoGroup, wx.VERTICAL)

        infofieldsizer = wx.GridBagSizer(vgap = get_space('minor'), hgap = get_space('minor'))

        filelabel = wx.StaticText(infoGroup, -1, _("File:"))
        filelabel.SetToolTip(_("The name of the model currently loaded."))
        infofieldsizer.Add(filelabel, pos = (0, 0), flag = wx.ALIGN_RIGHT)
        self.filename = wx.StaticText(infoGroup, -1, "")
        infofieldsizer.Add(self.filename, pos = (0, 1), flag = wx.EXPAND)

        totallayerslabel = wx.StaticText(infoGroup, -1, _("Total Layers:"))
        totallayerslabel.SetToolTip(_("The total number of layers found in the model."))
        infofieldsizer.Add(totallayerslabel, pos = (1, 0), flag = wx.ALIGN_RIGHT)
        self.total_layers = wx.StaticText(infoGroup, -1)
        infofieldsizer.Add(self.total_layers, pos = (1, 1), flag = wx.EXPAND)

        currentlayerlabel = wx.StaticText(infoGroup, -1, _("Current Layer:"))
        currentlayerlabel.SetToolTip(_("The current layer being displayed."))
        infofieldsizer.Add(currentlayerlabel, pos = (2, 0), flag = wx.ALIGN_RIGHT)
        self.current_layer = wx.StaticText(infoGroup, -1, "0")
        infofieldsizer.Add(self.current_layer, pos = (2, 1), flag = wx.EXPAND)

        estimatedtimelabel = wx.StaticText(infoGroup, -1, _("Estimated Time:"))
        estimatedtimelabel.SetToolTip(_("An estimate of the remaining time until print completion."))
        infofieldsizer.Add(estimatedtimelabel, pos = (3, 0), flag = wx.ALIGN_RIGHT)
        self.estimated_time = wx.StaticText(infoGroup, -1, "")
        infofieldsizer.Add(self.estimated_time, pos = (3, 1), flag = wx.EXPAND)

        statuslabel = wx.StaticText(infoGroup, -1, _("Status:"))
        statuslabel.SetToolTip(_("Latest activity, information and error messages."))
        infofieldsizer.Add(statuslabel, pos=(4, 0), flag = wx.ALIGN_RIGHT)
        self.statusbar = wx.StaticText(infoGroup, -1, "", style = wx.ELLIPSIZE_END)
        infofieldsizer.Add(self.statusbar, pos = (4, 1), flag = wx.EXPAND)

        infofieldsizer.AddGrowableCol(1)
        infosizer.Add(infofieldsizer, 1, wx.EXPAND)

        # Layout
        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(buttonbox, flag = wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP | wx.BOTTOM, border = get_space('minor'))
        vbox.Add(fieldboxsizer, flag = wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, border = get_space('minor'))
        vbox.Add(displayboxsizer, flag = wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, border = get_space('minor'))
        vbox.Add(infosizer, flag = wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, border = get_space('minor'))
        self.panel.SetSizerAndFit(vbox)

        reset_button = wx.Button(self, -1, label=_("Reset"))
        close_button = wx.Button(self, wx.ID_CLOSE)
        bottom_button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        bottom_button_sizer.Add(reset_button, 0)
        bottom_button_sizer.AddStretchSpacer(1)
        bottom_button_sizer.Add(close_button, 0)

        topsizer = wx.BoxSizer(wx.VERTICAL)
        topsizer.Add(self.panel, wx.EXPAND | wx.BOTTOM, get_space('mini'))
        topsizer.Add(wx.StaticLine(self, -1, style = wx.LI_HORIZONTAL), 0, wx.EXPAND)
        topsizer.Add(bottom_button_sizer, 0, wx.EXPAND | wx.ALL, get_space('stddlg-frame'))

        self.Bind(wx.EVT_BUTTON, self.on_close, id=wx.ID_CLOSE)
        self.Bind(wx.EVT_CLOSE, self.on_close)
        reset_button.Bind(wx.EVT_BUTTON, self.reset_all)

        self.SetSizerAndFit(topsizer)
        self.Fit()
        self.CentreOnParent()

        # res = (self.X.GetValue(), self.Y.GetValue())
        self.display_frame = DisplayFrame(self, statusbar = self.status,
                                          title = _("Layer Projector Display"),
                                          res = (1024, 768),
                                          printer = printer)
        self.display_frame.Centre()
        self.Raise()
        self.display_frame.Show()
        self.Show()

    def __del__(self):
        self.cleanup_temp()
        if self.display_frame:
            self.display_frame.Destroy()

    def status(self, message: str) -> None:
        return self.statusbar.SetLabel(message)

    def cleanup_temp(self):
        if isinstance(self.image_dir, tempfile.TemporaryDirectory):
            self.image_dir.cleanup()

    def set_total_layers(self, total):
        self.total_layers.SetLabel(str(total))
        self.set_estimated_time()

    def set_current_layer(self, index):
        self.current_layer.SetLabel(str(index))
        self.set_estimated_time()

    def display_filename(self, name):
        self.filename.SetLabel(name)

    def set_estimated_time(self):
        if not hasattr(self, 'layers'):
            return

        current_layer = int(self.current_layer.GetLabel())
        remaining_layers = len(self.layers[0]) - current_layer
        # 0.5 for delay between hide and rise
        estimated_time = remaining_layers * (self.interval.GetValue() + self.pause.GetValue() + 0.5)
        self.estimated_time.SetLabel(time.strftime("%H:%M:%S", time.gmtime(estimated_time)))

    def parse_svg(self, name):
        et = ET.ElementTree(file = name)
        namespaces = dict(node for (_, node) in ET.iterparse(name, events=['start-ns']))

        slicer = 'Slic3r' if 'slic3r' in namespaces.keys() else \
                 'Skeinforge' if et.getroot().find('{http://www.w3.org/2000/svg}metadata') else 'None'
        zlast = 0
        zdiff = 0
        ol = []
        if slicer == 'Slic3r':
            ET.register_namespace("", "http://www.w3.org/2000/svg")
            height = et.getroot().get('height').replace('m', '')
            width = et.getroot().get('width').replace('m', '')

            self.projected_X_mm.SetValue(float(width))
            self.update_projected_Xmm(wx.wxEVT_NULL)

            for i in et.findall("{http://www.w3.org/2000/svg}g"):
                z = float(i.get('{http://slic3r.org/namespaces/slic3r}z'))
                zdiff = z - zlast
                zlast = z

                svgSnippet = ET.Element('{http://www.w3.org/2000/svg}svg')
                svgSnippet.set('height', height + 'mm')
                svgSnippet.set('width', width + 'mm')

                svgSnippet.set('viewBox', '0 0 ' + width + ' ' + height)
                svgSnippet.set('style', 'background-color:black;fill:white;')
                svgSnippet.append(i)

                ol += [svgSnippet]

        elif slicer == 'Skeinforge':
            slice_layers = et.findall("{http://www.w3.org/2000/svg}metadata")[0].findall("{http://www.reprap.org/slice}layers")[0]
            minX = slice_layers.get('minX')
            maxX = slice_layers.get('maxX')
            minY = slice_layers.get('minY')
            maxY = slice_layers.get('maxY')

            height = str(abs(float(minY)) + abs(float(maxY)))
            width = str(abs(float(minX)) + abs(float(maxX)))

            self.projected_X_mm.SetValue(float(width))
            self.update_projected_Xmm(wx.wxEVT_NULL)

            for g in et.findall("{http://www.w3.org/2000/svg}g")[0].findall("{http://www.w3.org/2000/svg}g"):

                g.set('transform', '')

                text_element = g.findall("{http://www.w3.org/2000/svg}text")[0]
                g.remove(text_element)

                path_elements = g.findall("{http://www.w3.org/2000/svg}path")
                for p in path_elements:
                    p.set('transform', 'translate(' + maxX + ',' + maxY + ')')
                    p.set('fill', 'white')

                z = float(g.get('id').split("z:")[-1])
                zdiff = z - zlast
                zlast = z

                svgSnippet = ET.Element('{http://www.w3.org/2000/svg}svg')
                svgSnippet.set('height', height + 'mm')
                svgSnippet.set('width', width + 'mm')

                svgSnippet.set('viewBox', '0 0 ' + width + ' ' + height)
                svgSnippet.set('style', 'background-color:black;fill:white;')
                svgSnippet.append(g)

                ol += [svgSnippet]
        return ol, zdiff, slicer

    def parse_3DLP_zip(self, name):
        if not zipfile.is_zipfile(name):
            self.status(_("{} is not a zip file.").format(os.path.split(name)[1]))
            return -1, -1, "None"

        accepted_image_types = ['gif', 'tiff', 'jpg', 'jpeg', 'bmp', 'png']
        with zipfile.ZipFile(name, 'r') as zipFile:
            # Make sure to clean up an exisiting temp dir before creating a new one
            if isinstance(self.image_dir, tempfile.TemporaryDirectory):
                self.image_dir.cleanup()
            self.image_dir = tempfile.TemporaryDirectory()
            zipFile.extractall(self.image_dir.name)
        ol = []

        # Note: the following funky code extracts any numbers from the filenames, matches
        # them with the original then sorts them. It allows for filenames of the
        # format: abc_1.png, which would be followed by abc_10.png alphabetically.
        os.chdir(self.image_dir.name)
        vals = [f for f in os.listdir('.') if os.path.isfile(f)]
        keys = (int(re.search(r'\d+', p).group()) for p in vals)
        imagefilesDict = dict(zip(keys, vals))
        imagefilesOrderedDict = OrderedDict(sorted(imagefilesDict.items(), key = lambda t: t[0]))

        for f in imagefilesOrderedDict.values():
            path = os.path.join(self.image_dir.name, f)
            if os.path.isfile(path) and puremagic.what(path) in accepted_image_types:
                ol.append(path)

        return ol, -1, 'Bitmap'

    def parse_sl1(self, name):
        if not zipfile.is_zipfile(name):
            self.status(_("{} is not a zip file.").format(os.path.split(name)[1]))
            return -1, -1, 'None'

        accepted_image_types = ('gif', 'tiff', 'jpg', 'jpeg', 'bmp', 'png')

        with zipfile.ZipFile(name, 'r') as zippy:
            settings = self.load_sl1_config(zippy)
            # Make sure to clean up an exisiting temp dir before creating a new one
            if isinstance(self.image_dir, tempfile.TemporaryDirectory):
                self.image_dir.cleanup()
            self.image_dir = tempfile.TemporaryDirectory()
            for f in zippy.namelist():
                if f.lower().endswith(accepted_image_types) and 'thumbnail' not in f:
                    zippy.extract(f, self.image_dir.name)
        ol = []
        for f in sorted(os.listdir(self.image_dir.name)):
            path = os.path.join(self.image_dir.name, f)
            if os.path.isfile(path) and puremagic.what(path) in accepted_image_types:
                ol.append(path)

        return ol, -1, 'PrusaSlicer', settings

    def load_sl1_config(self, zip_object: zipfile.ZipFile):

        files = zip_object.namelist()
        settings = {}
        if 'prusaslicer.ini' in files:
            relevant_keys = ['display_height', 'display_width', 'display_orientation',
                             'display_pixels_x', 'display_pixels_y',
                             'display_mirror_x', 'display_mirror_y',
                             'exposure_time', 'initial_exposure_time',
                             'layer_height', 'printer_model', 'printer_technology',
                             'material_colour']
            with zip_object.open('prusaslicer.ini', 'r') as lines:
                for line in lines:
                    element = line.decode('UTF-8').rstrip().split(' = ')
                    if element[0] in relevant_keys:
                        element[1] = self.cast_type(element[1])
                        settings[element[0]] = element[1]
            return settings

        if 'config.ini' in files:
            relevant_keys = ['expTime', 'expTimeFirst', 'layerHeight', 'printerModel']
            key_names = ['exposure_time', 'initial_exposure_time', 'layer_height', 'printer_model']
            with zip_object.open('config.ini', 'r') as lines:
                for line in lines:
                    element = line.decode('UTF-8').rstrip().split(' = ')
                    if element[0] in relevant_keys:
                        index = relevant_keys.index(element[0])
                        element[1] = self.cast_type(element[1])
                        settings[key_names[index]] = element[1]
        return settings

    def cast_type(self, var):
        '''Automaticly cast int or float from str'''
        for caster in (int, float):
            try:
                return caster(var)
            except ValueError:
                pass
        return var

    def apply_sl1_settings(self, layers: list):
        thickness = layers[3].get('layer_height')
        if thickness is not None:
            self.thickness.SetValue(thickness)
            self.update_thickness(wx.wxEVT_NULL)
        else:
            self.status(_("Could not load .sl1 config."))
            return False
        interval = layers[3].get('exposure_time')
        if interval is not None:
            self.interval.SetValue(interval)
            self.update_interval(wx.wxEVT_NULL)
        init_exp = layers[3].get('initial_exposure_time')
        if init_exp is not None:
            self.show_first_layer_timer.SetValue(init_exp)
        x_res = layers[3].get('display_pixels_x')
        if x_res is not None:
            self.X.SetValue(x_res)
            self.update_resolution(wx.wxEVT_NULL)
        y_res = layers[3].get('display_pixels_y')
        if y_res is not None:
            self.Y.SetValue(y_res)
            self.update_resolution(wx.wxEVT_NULL)
        real_width = layers[3].get('display_width')
        if real_width:
            self.projected_X_mm.SetValue(real_width)
            self.update_projected_Xmm(wx.wxEVT_NULL)
        return True

    def load_file(self, event):
        self.reset_loaded_file()
        dlg = wx.FileDialog(self, _("Open file to print"), style = wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
        # On macOS, the wildcard for *.3dlp.zip is not recognised, so it is just *.zip.
        dlg.SetWildcard(_("All supported files") +
                        " (*.svg; *.3dlp.zip; *.sl1; *.sl1s)|*.svg;*.zip;*.sl1;*.sl1s|" +
                        _("Slic3r or Skeinforge SVG files") + " (*.svg)|*.svg|" +
                        _("3DLP Zip files") + " (*.3dlp.zip)|*.zip|" +
                        _("Prusa SL1 files") + " (*.sl1; *.sl1s)|*.sl1;*.sl1s")

        if dlg.ShowModal() == wx.ID_OK:
            name = dlg.GetPath()
            if not os.path.exists(name):
                self.status(_("File not found!"))
                return

            if name.lower().endswith('.svg'):
                layers = self.parse_svg(name)
            elif name.lower().endswith(('.sl1', '.sl1s')):
                layers = self.parse_sl1(name)
            elif name.lower().endswith('.3dlp.zip'):
                layers = self.parse_3DLP_zip(name)
            else:
                self.status(_("{} is not a sliced svg- or zip-file.").format(os.path.split(name)[1]))
                return

            if layers[2] in ('Slic3r', 'Skeinforge'):
                layer_height = round(layers[1], 3)
                self.thickness.SetValue(layer_height)
            elif layers[2] == 'PrusaSlicer':
                if self.apply_sl1_settings(layers):
                    layer_height = float(layers[3]['layer_height'])
                else:
                    layer_height = self.thickness.GetValue()
            elif layers[2] == 'Bitmap':
                layer_height = self.thickness.GetValue()
            else:
                self.status(_("{} is not a sliced svg-file or zip-file.").format(os.path.split(name)[1]))
                return

            self.status(_("{} layers found, total height {:.2f} mm").format(len(layers[0]),
                                                                              layer_height * len(layers[0])))
            self.layers = layers
            self.set_total_layers(len(layers[0]))
            self.set_current_layer(0)
            self.current_filename = os.path.basename(name)
            self.display_filename(self.current_filename)
            self.slicer = layers[2]
            self.display_frame.slicer = self.slicer
            self.present_button.Enable()

        dlg.Destroy()

        self.display_frame.Raise()
        self.Raise()

    def reset_loaded_file(self):
        if hasattr(self, 'layers'):
            delattr(self, 'layers')
        self.display_filename("")
        self.set_total_layers("")
        self.set_current_layer(0)
        self.estimated_time.SetLabel("")

    def show_calibrate(self, event):
        if self.calibrate.IsChecked():
            self.present_calibrate(event)
        else:
            if hasattr(self, 'layers'):
                self.display_frame.slicer = self.layers[2]
            self.display_frame.scale = self.scale.GetValue()
            self.display_frame.clear_layer()

    def show_first_layer(self, event):
        if self.first_layer.IsChecked():
            self.present_first_layer(event)
        else:
            if hasattr(self, 'layers'):
                self.display_frame.slicer = self.layers[2]
            self.display_frame.scale = self.scale.GetValue()
            self.display_frame.clear_layer()

    def show_layer_red(self, event):
        self.display_frame.layer_red = self.layer_red.IsChecked()

    def present_calibrate(self, event):
        if self.calibrate.IsChecked():
            self.first_layer.SetValue(False)

            previous_slicer = self.display_frame.slicer
            self.display_frame.slicer = 'Calibrate'
            self.display_frame.draw_layer()
            self.display_frame.slicer = previous_slicer

            self.display_frame.Raise()
        self.Raise()

    def present_first_layer(self, event):
        if self.first_layer.GetValue():
            if not hasattr(self, "layers"):
                self.status(_("No model loaded!"))
                self.first_layer.SetValue(False)
                return
            self.display_frame.offset = (self.offset_X.GetValue(), self.offset_Y.GetValue())
            self.display_frame.scale = self.scale.GetValue()

            self.display_frame.slicer = self.layers[2]
            self.display_frame.dpi = self.get_dpi()
            self.display_frame.draw_layer(copy.deepcopy(self.layers[0][0]))
            self.calibrate.SetValue(False)
            self.display_frame.Refresh()
            sfl_timer = self.show_first_layer_timer.GetValue()
            if sfl_timer > 0:
                def unpresent_first_layer():
                    self.display_frame.clear_layer()
                    self.first_layer.SetValue(False)
                # AGE2023-04-19 Python 3.10 expects delay in milliseconds as
                # integer value instead of float. Convert float value to int
                if 'first' in self.timers and self.timers['first'].IsRunning():
                    self.timers['first'].Stop()
                timer = wx.CallLater(int(sfl_timer * 1000), unpresent_first_layer)
                self.timers['first'] = timer

    def update_offset(self, event):
        offset_x = self.offset_X.GetValue()
        offset_y = self.offset_Y.GetValue()
        self.display_frame.offset = (offset_x, offset_y)

        self._set_setting('project_offset_x', offset_x)
        self._set_setting('project_offset_y', offset_y)

        self.refresh_display(event)

    def refresh_display(self, event):
        self.present_calibrate(event)
        self.present_first_layer(event)

    def update_thickness(self, event):
        self._set_setting('project_layer', self.thickness.GetValue())
        self.refresh_display(event)

    def update_projected_Xmm(self, event):
        self._set_setting('project_projected_x', self.projected_X_mm.GetValue())
        self.refresh_display(event)

    def update_scale(self, event):
        scale = self.scale.GetValue()
        self.display_frame.scale = scale
        self._set_setting('project_scale', scale)
        self.refresh_display(event)

    def update_interval(self, event):
        interval = self.interval.GetValue()
        self.display_frame.interval = interval
        self._set_setting('project_interval', interval)
        self.set_estimated_time()
        self.refresh_display(event)

    def update_pause(self, event):
        pause = self.pause.GetValue()
        self.display_frame.pause = pause
        self._set_setting('project_pause', pause)
        self.set_estimated_time()
        self.refresh_display(event)

    def update_overshoot(self, event):
        overshoot = self.overshoot.GetValue()
        self.display_frame.overshoot = overshoot
        self._set_setting('project_overshoot', overshoot)
        self.refresh_display(event)

    def update_prelift_gcode(self, event):
        prelift_gcode = self.prelift_gcode.GetValue().replace('\n', "\\n")
        self.display_frame.prelift_gcode = prelift_gcode
        self._set_setting('project_prelift_gcode', prelift_gcode)

    def update_postlift_gcode(self, event):
        postlift_gcode = self.postlift_gcode.GetValue().replace('\n', "\\n")
        self.display_frame.postlift_gcode = postlift_gcode
        self._set_setting('project_postlift_gcode', postlift_gcode)

    def update_z_axis_rate(self, event):
        z_axis_rate = self.z_axis_rate.GetValue()
        self.display_frame.z_axis_rate = z_axis_rate
        self._set_setting('project_z_axis_rate', z_axis_rate)

    def update_direction(self, event):
        direction = self.direction.GetSelection()
        self.display_frame.direction = direction
        self._set_setting('project_direction', direction)

    def update_fullscreen(self, event):
        if self.fullscreen.GetValue() and not self.display_frame.IsFullScreen():
            self.display_frame.ShowFullScreen(True, wx.FULLSCREEN_ALL)
        else:
            self.display_frame.ShowFullScreen(False)
        self.refresh_display(event)
        self.Raise()

    def update_resolution(self, event):
        x = self.X.GetValue()
        y = self.Y.GetValue()
        self.display_frame.resize((x, y))
        self._set_setting('project_x', x)
        self._set_setting('project_y', y)
        self.refresh_display(event)

    def get_dpi(self):
        '''Cacluate dots per inch from resolution and projection'''
        resolution_x_pixels = self.X.GetValue()
        projected_x_mm = self.projected_X_mm.GetValue()
        projected_x_inches = projected_x_mm / 25.4

        return resolution_x_pixels / projected_x_inches

    def start_present(self, event):
        if not hasattr(self, "layers"):
            self.status(_("No model loaded!"))
            return
        self.status(_("Starting..."))
        self.pause_button.SetLabel(self.get_btn_label('pause'))
        self.pause_button.Enable()
        self.stop_button.Enable()
        self.set_current_layer(0)
        self.display_frame.Raise()
        if self.fullscreen.GetValue() and not self.display_frame.IsFullScreen():
            self.display_frame.ShowFullScreen(True, wx.FULLSCREEN_ALL)
        self.display_frame.slicer = self.layers[2]
        self.display_frame.dpi = self.get_dpi()
        self.display_frame.startime = time.perf_counter()
        self.display_frame.present(self.layers[0][:],
                                   thickness = self.thickness.GetValue(),
                                   interval = self.interval.GetValue(),
                                   scale = self.scale.GetValue(),
                                   pause = self.pause.GetValue(),
                                   overshoot = self.overshoot.GetValue(),
                                   z_axis_rate = self.z_axis_rate.GetValue(),
                                   prelift_gcode = self.prelift_gcode.GetValue(),
                                   postlift_gcode = self.postlift_gcode.GetValue(),
                                   direction = self.direction.GetSelection(),
                                   size = (self.X.GetValue(), self.Y.GetValue()),
                                   offset = (self.offset_X.GetValue(), self.offset_Y.GetValue()),
                                   layer_red = self.layer_red.IsChecked())
        self.present_button.Disable()
        self.load_button.Disable()
        self.calibrate.SetValue(False)
        self.calibrate.Disable()
        self.Raise()

    def stop_present(self, event):
        self.status(_("Stopping..."))
        self.display_frame.running = False
        self.pause_button.SetLabel(self.get_btn_label('pause'))
        self.set_current_layer(0)
        self.present_button.Enable()
        self.load_button.Enable()
        self.calibrate.Enable()
        self.pause_button.Disable()
        self.stop_button.Disable()
        self.status(_("Stop"))

    def pause_present(self, event):
        if self.pause_button.GetLabel() == self.get_btn_label('pause'):
            self.status(self.get_btn_label('pause'))
            self.pause_button.SetLabel(self.get_btn_label('continue'))
            self.calibrate.Enable()
            self.display_frame.running = False
        else:
            self.status(self.get_btn_label('continue'))
            self.pause_button.SetLabel(self.get_btn_label('pause'))
            self.calibrate.SetValue(False)
            self.calibrate.Disable()
            self.display_frame.running = True
            self.display_frame.next_img()

    def on_close(self, event):
        self.stop_present(event)
        # Make sure that all running timers are
        # stopped before we destroy the frames
        for timer in self.timers.values():
            if timer.IsRunning():
                timer.Stop()
        self.cleanup_temp()
        if self.display_frame:
            self.display_frame.DestroyLater()
        self.DestroyLater()

    def get_btn_label(self, value):
        # This method simplifies translation of the button label
        if value == 'pause':
            return _("Pause")

        if value == 'continue':
            return _("Continue")

        return ValueError(f"No button label for '{value}'")

    def reset_all(self, event):
        # Ask confirmation for deleting
        reset_dialog = wx.MessageDialog(
            self,
            message = _("Are you sure you want to reset all the settings "
                        "to the defaults?\nBe aware that the defaults are "
                        "not guaranteed to work well with your machine."),
            caption = _("Reset Layer Projector Settings"),
            style = wx.YES_NO | wx.ICON_EXCLAMATION)

        if reset_dialog.ShowModal() == wx.ID_YES:
            # Reset all settings
            std_settings = [
                [self.thickness, 0.1, self.update_thickness],
                [self.interval, 2.0, self.update_interval],
                [self.pause, 2.5, self.update_pause],
                [self.scale, 1.0, self.update_scale],
                [self.direction, 0, self.update_direction],
                [self.overshoot, 3.0, self.update_overshoot],
                [self.prelift_gcode, "", self.update_prelift_gcode],

                [self.X, 1024, self.update_resolution],
                [self.Y, 768, self.update_resolution],
                [self.offset_X, 0, self.update_offset],
                [self.offset_Y, 0, self.update_offset],
                [self.projected_X_mm, 100.0, self.update_projected_Xmm],
                [self.z_axis_rate, 200, self.update_z_axis_rate],
                [self.postlift_gcode, "", self.update_postlift_gcode],

                [self.fullscreen, False, self.update_fullscreen],
                [self.calibrate, False, self.show_calibrate],
                [self.first_layer, False, self.show_first_layer],
                [self.show_first_layer_timer, -1.0, self.show_first_layer],
                [self.layer_red, False, self.show_layer_red]
            ]

            for setting in std_settings:
                self.reset_setting(event, setting[0], setting[1], setting[2])

            self.reset_loaded_file()
            self.status(_("Layer Projector settings reset"))

    def reset_setting(self, event, name, value, update_function):
        try:
            # First check if the user actually changed the setting
            if not value == name.GetValue():
                # If so, set it back and invoke the update_function to save the value
                name.SetValue(value)
                update_function(event)

        except AttributeError:
            if not value == name.GetSelection():
                name.SetSelection(value)
                update_function(event)


if __name__ == "__main__":
    a = wx.App()
    SettingsFrame(None)
    a.MainLoop()
