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

# Set up Internationalization using gettext
# searching for installed locales on /usr/share; uses relative folder if not found (windows)
from printrun.printrun_utils import install_locale
install_locale('plater')

import wx
import sys

from printrun import gcview
from printrun import gcoder
from printrun.objectplater import Plater
from printrun.gl.libtatlin import actors

class GcodePlater(Plater):

    load_wildcard = _("GCODE files (*.gcode;*.GCODE;*.g)")
    save_wildcard = _("GCODE files (*.gcode;*.GCODE;*.g)")

    def __init__(self, filenames = [], size = (800, 580), callback = None, parent = None, build_dimensions = None):
        super(GcodePlater, self).__init__(filenames, size, callback, parent, build_dimensions)
        viewer = gcview.GcodeViewPanel(self, build_dimensions = self.build_dimensions)
        self.set_viewer(viewer)
        self.platform = actors.Platform(self.build_dimensions)
        self.platform_object = gcview.GCObject(self.platform)

    def get_objects(self):
        return [self.platform_object] + self.models.values()
    objects = property(get_objects)

    def load_file(self, filename):
        gcode = gcoder.GCode(open(filename))
        model = actors.GcodeModel()
        model.load_data(gcode)
        obj = gcview.GCObject(model)
        obj.gcode = gcode
        obj.dims = [gcode.xmin, gcode.xmax,
                    gcode.ymin, gcode.ymax,
                    gcode.zmin, gcode.zmax]
        obj.centeroffset = [-(obj.dims[1] + obj.dims[0]) / 2,
                            -(obj.dims[3] + obj.dims[2]) / 2,
                            0]
        self.add_model(filename, obj)
        wx.CallAfter(self.Refresh)

    # What's hard in there ?
    # 1) finding the order in which the objects are printed
    # 2) handling layers correctly
    # 3) handling E correctly
    # 4) handling position shifts: should we either reset absolute 0 using G92
    # or should we rewrite all positions ?
    # 5) handling the start & end gcode properly ?
    # Initial implementation should just print the objects sequentially,
    # but the end goal is to have a clean per-layer merge
    def export_to(self, name):
        with open(name, "w") as f:
            models = self.models.values()
            last_real_position = None
            # Sort models by Z max to print smaller objects first
            models.sort(key = lambda x: x.dims[-1])
            for model in models:
                r = model.rot  # no rotation support for now
                if r != 0:
                    print _("Warning: no rotation support for now, "
                            "object won't be correctly rotated")
                o = model.offsets
                co = model.centeroffset
                offset_pos = last_real_position if last_real_position is not None else [0, 0, 0]
                trans = (offset_pos[0] - (o[0] + co[0]),
                         offset_pos[1] - (o[1] + co[1]),
                         offset_pos[2] - (o[2] + co[2]))
                f.write("G90\n")
                f.write("G92 X%.5f Y%.5f Z%.5f E0\n" % trans)
                for l in model.gcode:
                    if l.command != "G28" and (l.command != "92" or not any([l.x, l.y, l.z])):
                        f.write(l.raw + "\n")
                # Find the current real position
                for i in xrange(len(model.gcode) - 1, -1, -1):
                    if model.gcode.lines[i].is_move:
                        gline = model.gcode.lines[i]
                        last_real_position = [trans[0] + gline.current_x,
                                              trans[1] + gline.current_y,
                                              trans[2] + gline.current_z]
                        break
        print _("Exported merged G-Codes to %s") % name

if __name__ == '__main__':
    app = wx.App(False)
    main = GcodePlater(sys.argv[1:])
    main.Show()
    app.MainLoop()
