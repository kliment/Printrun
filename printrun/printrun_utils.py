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

import os, sys
import gettext

# Set up Internationalization using gettext
# searching for installed locales on /usr/share; uses relative folder if not found (windows)
def install_locale(domain):
    if os.path.exists('/usr/share/pronterface/locale'):
        gettext.install(domain, '/usr/share/pronterface/locale', unicode = 1)
    elif os.path.exists('/usr/local/share/pronterface/locale'):
        gettext.install(domain, '/usr/local/share/pronterface/locale', unicode = 1)
    else:
        gettext.install(domain, './locale', unicode = 1)

def imagefile(filename):
    for prefix in ['/usr/local/share/pronterface/images', '/usr/share/pronterface/images']:
        candidate = os.path.join(prefix, filename)
        if os.path.exists(candidate):
            return candidate
    local_candidate = os.path.join(os.path.dirname(sys.argv[0]), "images", filename)
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
    return lookup_file(filename, ['/usr/local/share/pixmaps', '/usr/share/pixmaps'])

def sharedfile(filename):
    return lookup_file(filename, ['/usr/local/share/pronterface', '/usr/share/pronterface'])

def configfile(filename):
    return lookup_file(filename, [os.path.expanduser("~/.printrun/"),])
