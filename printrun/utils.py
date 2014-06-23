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
import re
import gettext
import datetime
import subprocess
import shlex
import logging

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

def setup_logging(out):
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.handlers = []
    logging_handler = logging.StreamHandler(out)
    logging_handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    logger.addHandler(logging_handler)

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
    local_candidate = os.path.join(os.path.dirname(sys.argv[0]), filename)
    if os.path.exists(local_candidate):
        return local_candidate
    for prefix in prefixes:
        candidate = os.path.join(prefix, filename)
        if os.path.exists(candidate):
            return candidate
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

def format_time(timestamp):
    return datetime.datetime.fromtimestamp(timestamp).strftime("%H:%M:%S")

def format_duration(delta):
    return str(datetime.timedelta(seconds = int(delta)))

def prepare_command(command, replaces = None):
    command = shlex.split(command.replace("\\", "\\\\").encode())
    if replaces:
        replaces["$python"] = sys.executable
        for pattern, rep in replaces.items():
            command = [bit.replace(pattern, rep) for bit in command]
    command = [bit.encode() for bit in command]
    return command

def run_command(command, replaces = None, stdout = subprocess.STDOUT, stderr = subprocess.STDOUT, blocking = False):
    command = prepare_command(command, replaces)
    if blocking:
        return subprocess.call(command)
    else:
        return subprocess.Popen(command, stderr = stderr, stdout = stdout)

def get_command_output(command, replaces):
    p = run_command(command, replaces,
                    stdout = subprocess.PIPE, stderr = subprocess.STDOUT,
                    blocking = False)
    return p.stdout.read()

def dosify(name):
    return os.path.split(name)[1].split(".")[0][:8] + ".g"

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
        if self.previous_layers_estimate > 1. and printtime > 1.:
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

def parse_build_dimensions(bdim):
    # a string containing up to six numbers delimited by almost anything
    # first 0-3 numbers specify the build volume, no sign, always positive
    # remaining 0-3 numbers specify the coordinates of the "southwest" corner of the build platform
    # "XXX,YYY"
    # "XXXxYYY+xxx-yyy"
    # "XXX,YYY,ZZZ+xxx+yyy-zzz"
    # etc
    bdl = re.findall("([-+]?[0-9]*\.?[0-9]*)", bdim)
    defaults = [200, 200, 100, 0, 0, 0, 0, 0, 0]
    bdl = filter(None, bdl)
    bdl_float = [float(value) if value else defaults[i] for i, value in enumerate(bdl)]
    if len(bdl_float) < len(defaults):
        bdl_float += [defaults[i] for i in range(len(bdl_float), len(defaults))]
    for i in range(3):  # Check for nonpositive dimensions for build volume
        if bdl_float[i] <= 0: bdl_float[i] = 1
    return bdl_float

def get_home_pos(build_dimensions):
    return build_dimensions[6:9] if len(build_dimensions) >= 9 else None

def hexcolor_to_float(color, components):
    color = color[1:]
    numel = len(color)
    ndigits = numel / components
    div = 16 ** ndigits - 1
    return tuple(round(float(int(color[i:i + ndigits], 16)) / div, 2)
                 for i in range(0, numel, ndigits))

def check_rgb_color(color):
    if len(color[1:]) % 3 != 0:
        ex = ValueError(_("Color must be specified as #RGB"))
        ex.from_validator = True
        raise ex

def check_rgba_color(color):
    if len(color[1:]) % 4 != 0:
        ex = ValueError(_("Color must be specified as #RGBA"))
        ex.from_validator = True
        raise ex

tempreport_exp = re.compile("([TB]\d*):([-+]?\d*\.?\d*)(?: ?\/)?([-+]?\d*\.?\d*)")
def parse_temperature_report(report):
    matches = tempreport_exp.findall(report)
    return dict((m[0], (m[1], m[2])) for m in matches)
