# This file is part of the Printrun suite.
#
# Copyright 2013 Francesco Santini francesco.santini@gmail.com
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
#
# This code is imported from RepetierHost - Original copyright and license:
# Copyright 2011 repetier repetierdev@gmail.com
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import gcoder

class GCodeAnalyzer():
    def __init__(self):
        self.gcoder = gcoder.GCode([])
        self.x = 0
        self.y = 0
        self.z = 0
        self.e = 0
        self.emax = 0
        self.f = 1000
        self.lastX = 0
        self.lastY = 0
        self.lastZ = 0
        self.lastE = 0
        self.xOffset = 0
        self.yOffset = 0
        self.zOffset = 0
        self.eOffset = 0
        self.lastZPrint = 0
        self.layerZ = 0
        self.homeX = 0
        self.homeY = 0
        self.homeZ = 0
        self.hasHomeX = False
        self.hasHomeY = False
        self.hasHomeZ = False

    def Analyze(self, gcode):
        gline = self.gcoder.append(gcode, store = False)
        if gline.command.startswith(";@"): return  # code is a host command
        try:
            code_g = int(gline.command[1:]) if gline.command.startswith("G") else None
            code_m = int(gline.command[1:]) if gline.command.startswith("M") else None
        except ValueError:
            # If we fail to parse the code number, this is probably not a
            # standard G-Code but rather a host command, so return immediately
            return

        #get movement codes
        if gline.is_move:
            self.lastX = self.x
            self.lastY = self.y
            self.lastZ = self.z
            self.lastE = self.e
            if gline.f is not None:
                self.f = gline.f

            if self.gcoder.relative:
                if gline.x is not None: self.x += gline.x
                if gline.y is not None: self.y += gline.y
                if gline.z is not None: self.z += gline.z
                if gline.e is not None:
                    if gline.e != 0:
                        self.e += gline.e
            else:
                # absolute coordinates
                if gline.x is not None: self.x = self.xOffset + gline.x
                if gline.y is not None: self.y = self.yOffset + gline.y
                if gline.z is not None: self.z = self.zOffset + gline.z
                if gline.e is not None:
                    if self.gcoder.relative_e:
                        if gline.e != 0:
                            self.e += gline.e
                    else:
                    # e is absolute. Is it changed?
                        if self.e != self.eOffset + gline.e:
                            self.e = self.eOffset + gline.e
        elif code_g == 28 or code_g == 161:
            self.lastX = self.x
            self.lastY = self.y
            self.lastZ = self.z
            self.lastE = self.e
            homeAll = False
            if gline.x is None and gline.y is None and gline.z is None: homeAll = True
            if gline.x is not None or homeAll:
                self.hasHomeX = True
                self.xOffset = 0
                self.x = self.homeX
            if gline.y is not None or homeAll:
                self.hasHomeY = True
                self.yOffset = 0
                self.y = self.homeY
            if gline.z is not None or homeAll:
                self.hasHomeZ = True
                self.zOffset = 0
                self.z = self.homeZ
            if gline.e is not None:
                self.eOffset = 0
                self.e = 0
        elif code_g == 92:
            if gline.x is not None:
                self.xOffset = self.x - float(gline.x)
                self.x = self.xOffset
            if gline.y is not None:
                self.yOffset = self.y - float(gline.y)
                self.y = self.yOffset
            if gline.z is not None:
                self.zOffset = self.z - float(gline.z)
                self.z = self.zOffset
            if gline.e is not None:
                self.eOffset = self.e - float(gline.e)
                self.e = self.eOffset

    def print_status(self):
        attrs = vars(self)
        print '\n'.join("%s: %s" % item for item in attrs.items())
