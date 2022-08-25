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
import platform
import sys
import re
import gettext
import datetime
import subprocess
import shlex
import locale
import logging

DATADIR = os.path.join(sys.prefix, 'share')


def set_utf8_locale():
    """Make sure we read/write all text files in UTF-8"""
    lang, encoding = locale.getlocale()
    if encoding != 'UTF-8':
        locale.setlocale(locale.LC_CTYPE, (lang, 'UTF-8'))

# Set up Internationalization using gettext
# searching for installed locales on /usr/share; uses relative folder if not
# found (windows)
def install_locale(domain):
    shared_locale_dir = os.path.join(DATADIR, 'locale')
    translation = None
    lang = locale.getdefaultlocale()
    osPlatform = platform.system()

    if osPlatform == "Darwin":
        # improvised workaround for macOS crash with gettext.translation, see issue #1154
        if os.path.exists(shared_locale_dir): 
            gettext.install(domain, shared_locale_dir) 
        else: 
            gettext.install(domain, './locale') 
    else:
        if os.path.exists('./locale'):
            translation = gettext.translation(domain, './locale', languages=[lang[0]], fallback= True)
        else:
            translation = gettext.translation(domain, shared_locale_dir, languages=[lang[0]], fallback= True)
        translation.install()

class LogFormatter(logging.Formatter):
    def __init__(self, format_default, format_info):
        super(LogFormatter, self).__init__(format_info)
        self.format_default = format_default
        self.format_info = format_info

    def format(self, record):
        if record.levelno == logging.INFO:
            self._fmt = self.format_info
        else:
            self._fmt = self.format_default
        return super(LogFormatter, self).format(record)

def setup_logging(out, filepath = None, reset_handlers = False):
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    if reset_handlers:
        logger.handlers = []
    formatter = LogFormatter("[%(levelname)s] %(message)s", "%(message)s")
    logging_handler = logging.StreamHandler(out)
    logging_handler.setFormatter(formatter)
    logger.addHandler(logging_handler)
    if filepath:
        if os.path.isdir(filepath):
            filepath = os.path.join(filepath, "printrun.log")
        formatter = LogFormatter("%(asctime)s - [%(levelname)s] %(message)s", "%(asctime)s - %(message)s")
        logging_handler = logging.FileHandler(filepath)
        logging_handler.setFormatter(formatter)
        logger.addHandler(logging_handler)

def iconfile(filename):
    '''
    Get the full path to filename by checking in standard icon locations
    ("pixmaps" directories) or use the frozen executable if applicable
    (See the lookup_file function's documentation for behavior).
    '''
    if hasattr(sys, "frozen") and sys.frozen == "windows_exe":
        return sys.executable
    else:
        return pixmapfile(filename)

def imagefile(filename):
    '''
    Get the full path to filename by checking standard image locations,
    those being possible locations of the pronterface "images" directory
    (See the lookup_file function's documentation for behavior).
    '''
    my_local_share = os.path.join(
        os.path.dirname(os.path.dirname(sys.argv[0])),
        "share",
        "pronterface"
    )  # Used by pip install
    image_dirs = [
        os.path.join(DATADIR, 'pronterface', 'images'),
        os.path.join(os.path.dirname(sys.argv[0]), "images"),
        os.path.join(my_local_share, "images"),
        os.path.join(
            getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__))),
            "images"
        ),  # Check manually since lookup_file checks in frozen but not /images
    ]
    path = lookup_file(filename, image_dirs)
    if path == filename:
        # The file wasn't found in any known location, so use a relative
        #   path.
        path = os.path.join("images", filename)
    return path

def lookup_file(filename, prefixes):
    '''
    Get the full path to filename by checking one or more prefixes,
    or in the frozen data if applicable. If a result from this
    (or from callers such as imagefile) is used for the wx.Image
    constructor and filename isn't found, the C++ part of wx
    will raise an exception (wx._core.wxAssertionError): "invalid
    image".
    
    Sequential arguments:
    filename -- a filename without the path.
    prefixes -- a list of paths.
    
    Returns:
    The full path if found, or filename if not found.
    '''
    local_candidate = os.path.join(os.path.dirname(sys.argv[0]), filename)
    if os.path.exists(local_candidate):
        return local_candidate
    if getattr(sys,"frozen",False): prefixes+=[getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__))),]
    for prefix in prefixes:
        candidate = os.path.join(prefix, filename)
        if os.path.exists(candidate):
            return candidate
    return filename

def pixmapfile(filename):
    '''
    Get the full path to filename by checking in standard icon
    ("pixmaps") directories (See the lookup_file function's
    documentation for behavior).
    '''
    shared_pixmaps_dir = os.path.join(DATADIR, 'pixmaps')
    local_pixmaps_dir = os.path.join(
        os.path.dirname(os.path.dirname(sys.argv[0])),
        "share",
        "pixmaps"
    )  # Used by pip install
    pixmaps_dirs = [shared_pixmaps_dir, local_pixmaps_dir]
    return lookup_file(filename, pixmaps_dirs)

def sharedfile(filename):
    '''
    Get the full path to filename by checking in the shared
    directory (See the lookup_file function's documentation for behavior).
    '''
    shared_pronterface_dir = os.path.join(DATADIR, 'pronterface')
    return lookup_file(filename, [shared_pronterface_dir])

def configfile(filename):
    '''
    Get the full path to filename by checking in the
    standard configuration directory (See the lookup_file
    function's documentation for behavior).
    '''
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
    command = shlex.split(command.replace("\\", "\\\\"))
    if replaces:
        replaces["$python"] = sys.executable
        for pattern, rep in replaces.items():
            command = [bit.replace(pattern, rep) for bit in command]
    return command

def run_command(command, replaces = None, stdout = subprocess.STDOUT, stderr = subprocess.STDOUT, blocking = False, universal_newlines = False):
    command = prepare_command(command, replaces)
    if blocking:
        return subprocess.call(command, universal_newlines = universal_newlines)
    else:
        return subprocess.Popen(command, stderr = stderr, stdout = stdout, universal_newlines = universal_newlines)

def get_command_output(command, replaces):
    p = run_command(command, replaces,
                    stdout = subprocess.PIPE, stderr = subprocess.STDOUT,
                    blocking = False, universal_newlines = True)
    return p.stdout.read()

def dosify(name):
    return os.path.split(name)[1].split(".")[0][:8] + ".g"

class RemainingTimeEstimator:

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
        if idx >= len(self.gcode.layer_idxs):
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
    bdl = [b for b in bdl if b]
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
    ndigits = numel // components
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

def compile_file(filename):
    with open(filename) as f:
        return compile(f.read(), filename, 'exec')

def read_history_from(filename):
    history=[]
    if os.path.exists(filename):
        _hf=open(filename,encoding="utf-8")
        for i in _hf:
            history.append(i.rstrip())
    return history

def write_history_to(filename, hist):
    _hf=open(filename,"w",encoding="utf-8")
    for i in hist:
        _hf.write(i+"\n")
    _hf.close()
