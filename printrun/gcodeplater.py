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

# Set up Internationalization using gettext
# searching for installed locales on /usr/share; uses relative folder if not found (windows)
from .utils import install_locale, get_home_pos
install_locale('pronterface')

import wx
import sys
import os
import time
import types
import re
import math
import logging

from printrun import gcoder
from printrun.objectplater import make_plater, PlaterPanel
from printrun.gl.libtatlin import actors
import printrun.gui.viz  # NOQA
from printrun import gcview

def extrusion_only(gline):
    return gline.e is not None \
        and (gline.x, gline.y, gline.z) == (None, None, None)

# Custom method for gcoder.GCode to analyze & output gcode in a single call
def gcoder_write(self, f, line, store = False):
    f.write(line)
    self.append(line, store = store)

rewrite_exp = re.compile("(%s)" % "|".join(["X([-+]?[0-9]*\.?[0-9]*)",
                                            "Y([-+]?[0-9]*\.?[0-9]*)"]))

def rewrite_gline(centeroffset, gline, cosr, sinr):
    if gline.is_move and (gline.x is not None or gline.y is not None):
        if gline.relative:
            xc = yc = 0
            cox = coy = 0
            if gline.x is not None:
                xc = gline.x
            if gline.y is not None:
                yc = gline.y
        else:
            xc = gline.current_x + centeroffset[0]
            yc = gline.current_y + centeroffset[1]
            cox = centeroffset[0]
            coy = centeroffset[1]
        new_x = "X%.04f" % (xc * cosr - yc * sinr - cox)
        new_y = "Y%.04f" % (xc * sinr + yc * cosr - coy)
        new = {"X": new_x, "Y": new_y}
        new_line = rewrite_exp.sub(lambda ax: new[ax.group()[0]], gline.raw)
        new_line = new_line.split(";")[0]
        if gline.x is None: new_line += " " + new_x
        if gline.y is None: new_line += " " + new_y
        return new_line
    else:
        return gline.raw

class GcodePlaterPanel(PlaterPanel):

    load_wildcard = _("GCODE files (*.gcode;*.GCODE;*.g)") + "|*.gcode;*.gco;*.g"
    save_wildcard = _("GCODE files (*.gcode;*.GCODE;*.g)") + "|*.gcode;*.gco;*.g"

    def prepare_ui(self, filenames = [], callback = None,
                   parent = None, build_dimensions = None,
                   circular_platform = False,
                   antialias_samples = 0,
                   grid = (1, 10)):
        super(GcodePlaterPanel, self).prepare_ui(filenames, callback, parent, build_dimensions)
        viewer = gcview.GcodeViewPanel(self, build_dimensions = self.build_dimensions,
                                       antialias_samples = antialias_samples)
        self.set_viewer(viewer)
        self.platform = actors.Platform(self.build_dimensions,
                                        circular = circular_platform,
                                        grid = grid)
        self.platform_object = gcview.GCObject(self.platform)

    def get_objects(self):
        return [self.platform_object] + list(self.models.values())
    objects = property(get_objects)

    def load_file(self, filename):
        gcode = gcoder.GCode(open(filename, "rU"),
                             get_home_pos(self.build_dimensions))
        model = actors.GcodeModel()
        if gcode.filament_length > 0:
            model.display_travels = False
        generator = model.load_data(gcode)
        generator_output = next(generator)
        while generator_output is not None:
            generator_output = next(generator)
        obj = gcview.GCObject(model)
        obj.offsets = [self.build_dimensions[3], self.build_dimensions[4], 0]
        obj.gcode = gcode
        obj.dims = [gcode.xmin, gcode.xmax,
                    gcode.ymin, gcode.ymax,
                    gcode.zmin, gcode.zmax]
        obj.centeroffset = [-(obj.dims[1] + obj.dims[0]) / 2,
                            -(obj.dims[3] + obj.dims[2]) / 2,
                            0]
        self.add_model(filename, obj)
        wx.CallAfter(self.Refresh)

    def done(self, event, cb):
        if not os.path.exists("tempgcode"):
            os.mkdir("tempgcode")
        name = "tempgcode/" + str(int(time.time()) % 10000) + ".gcode"
        self.export_to(name)
        if cb is not None:
            cb(name)
        if self.destroy_on_done:
            self.Destroy()

    # What's hard in there ?
    # 1) [x] finding the order in which the objects are printed
    # 2) [x] handling layers correctly
    # 3) [x] handling E correctly
    # 4) [x] handling position shifts: should we either reset absolute 0 using
    #        G92 or should we rewrite all positions ? => we use G92s
    # 5) [ ] handling the start & end gcode properly ?
    # 6) [x] handling of current tool
    # 7) [x] handling of Z moves for sequential printing (don't lower Z before
    #        reaching the next object print area)
    # 8) [x] handling of absolute/relative status
    # Initial implementation should just print the objects sequentially,
    # but the end goal is to have a clean per-layer merge
    def export_to(self, name):
        return self.export_combined(name)
        return self.export_sequential(name)

    def export_combined(self, name):
        models = list(self.models.values())
        last_real_position = None
        # Sort models by Z max to print smaller objects first
        models.sort(key = lambda x: x.dims[-1])
        alllayers = []
        for (model_i, model) in enumerate(models):
            def add_offset(layer):
                return layer.z + model.offsets[2] if layer.z is not None else layer.z
            alllayers += [(add_offset(layer), model_i, layer_i)
                          for (layer_i, layer) in enumerate(model.gcode.all_layers) if add_offset(layer) is not None]
        alllayers.sort()
        laste = [0] * len(models)
        lasttool = [0] * len(models)
        lastrelative = [False] * len(models)
        with open(name, "w") as f:
            analyzer = gcoder.GCode(None, get_home_pos(self.build_dimensions))
            analyzer.write = types.MethodType(lambda self, line: gcoder_write(self, f, line), analyzer)
            for (layer_z, model_i, layer_i) in alllayers:
                model = models[model_i]
                layer = model.gcode.all_layers[layer_i]
                r = math.radians(model.rot)
                o = model.offsets
                co = model.centeroffset
                offset_pos = last_real_position if last_real_position is not None else (0, 0, 0)
                analyzer.write("; %f %f %f\n" % offset_pos)
                trans = (- (o[0] + co[0]),
                         - (o[1] + co[1]),
                         - (o[2] + co[2]))
                trans_wpos = (offset_pos[0] + trans[0],
                              offset_pos[1] + trans[1],
                              offset_pos[2] + trans[2])
                analyzer.write("; GCodePlater: Model %d Layer %d at Z = %s\n" % (model_i, layer_i, layer_z))
                if lastrelative[model_i]:
                    analyzer.write("G91\n")
                else:
                    analyzer.write("G90\n")
                if analyzer.current_tool != lasttool[model_i]:
                    analyzer.write("T%d\n" % lasttool[model_i])
                analyzer.write("G92 X%.5f Y%.5f Z%.5f\n" % trans_wpos)
                analyzer.write("G92 E%.5f\n" % laste[model_i])
                for l in layer:
                    if l.command != "G28" and (l.command != "G92" or extrusion_only(l)):
                        if r == 0:
                            analyzer.write(l.raw + "\n")
                        else:
                            analyzer.write(rewrite_gline(co, l, math.cos(r), math.sin(r)) + "\n")
                # Find the current real position & E
                last_real_position = analyzer.current_pos
                laste[model_i] = analyzer.current_e
                lastrelative[model_i] = analyzer.relative
                lasttool[model_i] = analyzer.current_tool
        logging.info(_("Exported merged G-Codes to %s") % name)

    def export_sequential(self, name):
        models = list(self.models.values())
        last_real_position = None
        # Sort models by Z max to print smaller objects first
        models.sort(key = lambda x: x.dims[-1])
        with open(name, "w") as f:
            for model_i, model in enumerate(models):
                r = math.radians(model.rot)
                o = model.offsets
                co = model.centeroffset
                offset_pos = last_real_position if last_real_position is not None else (0, 0, 0)
                trans = (- (o[0] + co[0]),
                         - (o[1] + co[1]),
                         - (o[2] + co[2]))
                trans_wpos = (offset_pos[0] + trans[0],
                              offset_pos[1] + trans[1],
                              offset_pos[2] + trans[2])
                f.write("; GCodePlater: Model %d\n" % model_i)
                f.write("G90\n")
                f.write("G92 X%.5f Y%.5f Z%.5f E0\n" % trans_wpos)
                f.write("G1 X%.5f Y%.5f" % (-co[0], -co[1]))
                for l in model.gcode:
                    if l.command != "G28" and (l.command != "G92" or extrusion_only(l)):
                        if r == 0:
                            f.write(l.raw + "\n")
                        else:
                            f.write(rewrite_gline(co, l, math.cos(r), math.sin(r)) + "\n")
                # Find the current real position
                for i in range(len(model.gcode) - 1, -1, -1):
                    gline = model.gcode.lines[i]
                    if gline.is_move:
                        last_real_position = (- trans[0] + gline.current_x,
                                              - trans[1] + gline.current_y,
                                              - trans[2] + gline.current_z)
                        break
        logging.info(_("Exported merged G-Codes to %s") % name)

GcodePlater = make_plater(GcodePlaterPanel)

if __name__ == '__main__':
    app = wx.App(False)
    main = GcodePlater(filenames = sys.argv[1:])
    for fn in main.filenames:
        main.load_file(fn)
    main.filenames = None
    main.autoplate()
    main.export_to("gcodeplate___test.gcode")
    raise SystemExit
    main.Show()
    app.MainLoop()
