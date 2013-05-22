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

import re
import gcoder

class GCodeAnalyzer():
    def __init__(self):
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
        self.relative = False
        self.eRelative = False
        self.homeX = 0
        self.homeY = 0
        self.homeZ = 0
        self.maxX = 150
        self.maxY = 150
        self.maxZ = 150
        self.minX = 0
        self.minY = 0
        self.minZ = 0
        self.hasHomeX = False
        self.hasHomeY = False
        self.hasHomeZ = False

    def Analyze(self, gcode):
        gline = gcoder.Line(gcode)
        if gline.command.startswith(";@"): return # code is a host command
        code_g = int(gline.command[1:]) if gline.command.startswith("G") else None
        code_m = int(gline.command[1:]) if gline.command.startswith("M") else None

        #get movement codes
        if gline.is_move:
            self.lastX = self.x
            self.lastY = self.y
            self.lastZ = self.z
            self.lastE = self.e
            eChanged = False;
            code_f = gline.f
            if code_f != None:
                self.f = code_f

            code_x = gline.x
            code_y = gline.y
            code_z = gline.z
            code_e = gline.e

            if self.relative:
                if code_x != None: self.x += code_x
                if code_y != None: self.y += code_y
                if code_z != None: self.z += code_z
                if code_e != None:
                    if code_e != 0:
                        eChanged = True
                        self.e += code_e
            else:
                #absolute coordinates
                if code_x != None: self.x = self.xOffset + code_x
                if code_y != None: self.y = self.yOffset + code_y
                if code_z != None: self.z = self.zOffset + code_z
                if code_e != None:
                    if self.eRelative:
                        if code_e != 0:
                            eChanged = True
                            self.e += code_e
                    else:
                    # e is absolute. Is it changed?
                        if self.e != self.eOffset + code_e:
                            eChanged = True
                            self.e = self.eOffset + code_e
            #limit checking
            if self.x < self.minX: self.x = self.minX
            if self.y < self.minY: self.y = self.minY
            if self.z < self.minZ: self.z = self.minZ

            if self.x > self.maxX: self.x = self.maxX
            if self.y > self.maxY: self.y = self.maxY
            if self.z > self.maxZ: self.z = self.maxZ
            #Repetier has a bunch of limit-checking code here and time calculations: we are leaving them for now
        elif code_g == 28 or code_g == 161:
            self.lastX = self.x
            self.lastY = self.y
            self.lastZ = self.z
            self.lastE = self.e
            code_x = gline.x
            code_y = gline.y
            code_z = gline.z
            code_e = gline.e
            homeAll = False
            if code_x == None and code_y == None and code_z == None: homeAll = True
            if code_x != None or homeAll:
                self.hasHomeX = True
                self.xOffset = 0
                self.x = self.homeX
            if code_y != None or homeAll:
                self.hasHomeY = True
                self.yOffset = 0
                self.y = self.homeY
            if code_z != None or homeAll:
                self.hasHomeZ = True
                self.zOffset = 0
                self.z = self.homeZ
            if code_e != None:
                self.eOffset = 0
                self.e = 0
        elif code_g == 162:
            self.lastX = self.x
            self.lastY = self.y
            self.lastZ = self.z
            self.lastE = self.e
            code_x = gline.x
            code_y = gline.y
            code_z = gline.z
            homeAll = False
            if code_x == None and code_y == None and code_z == None: homeAll = True
            if code_x != None or homeAll:
                self.hasHomeX = True
                self.xOffset = 0
                self.x = self.maxX
            if code_y != None or homeAll:
                self.hasHomeY = True
                self.yOffset = 0
                self.y = self.maxY
            if code_z != None or homeAll:
                self.hasHomeZ = True
                self.zOffset = 0
                self.z = self.maxZ
        elif code_g == 90: self.relative = False
        elif code_g == 91: self.relative = True
        elif code_g == 92:
            code_x = gline.x
            code_y = gline.y
            code_z = gline.z
            code_e = gline.e
            if code_x != None:
                self.xOffset = self.x - float(code_x)
                self.x = self.xOffset
            if code_y != None:
                self.yOffset = self.y - float(code_y)
                self.y = self.yOffset
            if code_z != None:
                self.zOffset = self.z - float(code_z)
                self.z = self.zOffset
            if code_e != None:
                self.xOffset = self.e - float(code_e)
                self.e = self.eOffset
            #End code_g != None
            if code_m != None:
                code_m = int(code_m)
                if code_m == 82: self.eRelative = False
                elif code_m == 83: self.eRelative = True

    def print_status(self):
        attrs = vars(self)
        print '\n'.join("%s: %s" % item for item in attrs.items())
