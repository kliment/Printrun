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

import os
import sys
import wx
import getopt

from printrun.stlplater import StlPlater

if __name__ == '__main__':

    from printrun.printcore import __version__ as printcore_version

    os.environ['GDK_BACKEND'] = 'x11'

    usage = "Usage:\n"+\
            "  plater [OPTION]\n"+\
            "  plater FILES\n\n"+\
            "Options:\n"+\
            "  -V, --version\t\t\tPrint program's version number and exit\n"+\
            "  -h, --help\t\t\tPrint this help message and exit\n" \
            "  --no-gl\t\t\tUse 2D implementation, that seems unusable"

    try:
        opts, args = getopt.getopt(sys.argv[1:], "hV", ["help", "version", 'no-gl'])
    except getopt.GetoptError as err:
        print(str(err))
        print(usage)
        sys.exit(2)
    for o, a in opts:
        if o in ('-V','--version'):
            print("printrun "+printcore_version)
            sys.exit(0)
        elif o in ('-h', '--help'):
            print(usage)
            sys.exit(0)

    app = wx.App(False)
    main = StlPlater(filenames = sys.argv[1:])
    main.Show()
    app.MainLoop()
