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

from .gui.widgets import MacroEditor

from .utils import install_locale
install_locale('pronterface')

def injector(gcode, viz_layer, layer_idx):
    cb = lambda toadd: inject(gcode, viz_layer, layer_idx, toadd)
    z = gcode.all_layers[layer_idx].z
    z = z if z is not None else 0
    MacroEditor(_("Inject G-Code at layer %d (Z = %.03f)") % (viz_layer, z), "", cb, True)

def injector_edit(gcode, viz_layer, layer_idx):
    cb = lambda toadd: rewritelayer(gcode, viz_layer, layer_idx, toadd)
    layer = gcode.all_layers[layer_idx]
    z = layer.z
    z = z if z is not None else 0
    lines = [line.raw for line in layer]
    MacroEditor(_("Edit G-Code of layer %d (Z = %.03f)") % (viz_layer, z), lines, cb, True)

def inject(gcode, viz_layer, layer_idx, toadd):
    # TODO: save modified gcode after injection ?
    nlines = len(gcode.prepend_to_layer(toadd, layer_idx))
    logging.info(_("Successfully injected %d lines at beginning of layer %d") % (nlines, viz_layer))

def rewritelayer(gcode, viz_layer, layer_idx, toadd):
    # TODO: save modified gcode after edit ?
    nlines = len(gcode.rewrite_layer(toadd, layer_idx))
    logging.info(_("Successfully edited layer %d (which now contains %d lines)") % (viz_layer, nlines))
