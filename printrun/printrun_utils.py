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
import sys
import gettext

# Set up Internationalization using gettext
# searching for installed locales on /usr/share; uses relative folder if not
# found (windows)
def install_locale(domain):
    if os.path.exists('/usr/share/pronterface/locale'):
        gettext.install(domain, '/usr/share/pronterface/locale', unicode = 1)
    elif os.path.exists('/usr/local/share/pronterface/locale'):
        gettext.install(domain, '/usr/local/share/pronterface/locale',
                        unicode = 1)
    else:
        gettext.install(domain, './locale', unicode = 1)

def iconfile(filename):
    if hasattr(sys, "frozen") and sys.frozen == "windows_exe":
        return sys.executable
    else:
        return pixmapfile(filename)

def imagefile(filename):
    for prefix in ['/usr/local/share/pronterface/images',
                   '/usr/share/pronterface/images']:
        candidate = os.path.join(prefix, filename)
        if os.path.exists(candidate):
            return candidate
    local_candidate = os.path.join(os.path.dirname(sys.argv[0]),
                                   "images", filename)
    if os.path.exists(local_candidate):
        return local_candidate
    else:
        return os.path.join("images", filename)

def lookup_file(filename, prefixes):
    for prefix in prefixes:
        candidate = os.path.join(prefix, filename)
        if os.path.exists(candidate):
            return candidate
    local_candidate = os.path.join(os.path.dirname(sys.argv[0]), filename)
    if os.path.exists(local_candidate):
        return local_candidate
    else:
        return filename

def pixmapfile(filename):
    return lookup_file(filename, ['/usr/local/share/pixmaps',
                                  '/usr/share/pixmaps'])

def sharedfile(filename):
    return lookup_file(filename, ['/usr/local/share/pronterface',
                                  '/usr/share/pronterface'])

def configfile(filename):
    return lookup_file(filename, [os.path.expanduser("~/.printrun/"), ])

def decode_utf8(s):
    try:
        s = s.decode("utf-8")
    except:
        pass
    return s

class RemainingTimeEstimator(object):

    drift = None
    gcode = None

    def __init__(self, gcode):
        self.drift = 1
        self.previous_layers_estimate = 0
        self.current_layer_estimate = 0
        self.current_layer_lines = 0
        self.gcode = gcode
        self.remaining_layers_estimate = sum(layer.duration for layer in gcode.all_layers)
        if len(gcode) > 0:
            self.update_layer(0, 0)

    def update_layer(self, layer, printtime):
        self.previous_layers_estimate += self.current_layer_estimate
        if self.previous_layers_estimate > 0 and printtime > 0:
            self.drift = printtime / self.previous_layers_estimate
        self.current_layer_estimate = self.gcode.all_layers[layer].duration
        self.current_layer_lines = len(self.gcode.all_layers[layer])
        self.remaining_layers_estimate -= self.current_layer_estimate
        self.last_idx = -1
        self.last_estimate = None

    def __call__(self, idx, printtime):
        if not self.current_layer_lines:
            return (0, 0)
        if idx == self.last_idx:
            return self.last_estimate
        layer, line = self.gcode.idxs(idx)
        layer_progress = (1 - (float(line + 1) / self.current_layer_lines))
        remaining = layer_progress * self.current_layer_estimate + self.remaining_layers_estimate
        estimate = self.drift * remaining
        total = estimate + printtime
        self.last_idx = idx
        self.last_estimate = (estimate, total)
        return self.last_estimate
