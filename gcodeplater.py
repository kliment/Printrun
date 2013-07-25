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

    def export_to(self, name):
        raise NotImplementedError

if __name__ == '__main__':
    app = wx.App(False)
    main = GcodePlater(sys.argv[1:])
    main.Show()
    app.MainLoop()
