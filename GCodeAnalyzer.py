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
      
      
  # find a code in a gstring line   
  def findCode(self, gcode, codeStr):
      pattern = re.compile(codeStr + "s*([\d.]*)",re.I)
      m=re.match(pattern, gcode)
      if m == None:
        return None
      else
        return m.group(1)
	
  def Analyze(self, gcode):
      code_g = self.findCode(gcode, "G")
      code_m = self.findCode(gcode, "M")
      
      # we have a g_code
      if code_g != None:
        code_g = int(code_g)
	
	#get movement codes
	if code_g == 0 or code_g == 1 or code_g == 2 or code_g == 3:
	  eChanged = false;
	  code_f = self.findCode(gcode, "F")
	  if code_f != None:
	    self.f=float(code_f)
	    
	  code_x = self.findCode(gcode, "X")
	  code_y = self.findCode(gcode. "Y")
	  code_z = self.findCode(gcode, "Z")
	  code_e = self.findCode(gcode, "E")
	  
	  if self.relative:
	    if code_x != None: self.x += float(code_x)
	    if code_y != None: self.y += float(code_y)
	    if code_z != None: self.z += float(code_z)
	    if code_e != None:
	      e = float(code_e)
	      if e != 0:
		eChanged = True
		self.e += e
	  else:	    
	    #absolute coordinates
	    if code_x != None: self.x = self.xOffset + float(code_x)
	    if code_y != None: self.y = self.yOffset + float(code_y)
	    if code_z != None: self.z = self.zOffset + float(code_z)
	    if code_e != None:
	      e = float(code_e)
	      if self.eRelative:
		if e != 0:
		  eChanged = True
		  self.e += e
	      else:
		# e is absolute. Is it changed?
		if self.e != self.eOffset + e:
		  eChanged = True
		  self.e = self.eOffset + e
	    #Repetier has a bunch of limit-checking code here and time calculations: we are leaving them for now

	elif code_g == 28 or code_g == 161:
	  code_x = self.findCode(gcode, "X")
	  code_y = self.findCode(gcode, "Y")
	  code_z = self.findCode(gcode, "Z")
	  code_e = self.findCode(gcode, "E")
	  homeAll = False
	  if code_x == None and code_y == None and code_z == None: homeAll = True
	  if code_x != None or homeAll:
	    self.xOffset = 0
	    self.x = self.homeX
	  if code_y != None or homeAll:
	    self.yOffset = 0
	    self.y = self.homeY
	  if code_z != None or homeAll:
	    self.zOffset = 0
	    self.z = self.homeZ
	  if code_e != None:
	    self.eOffset = 0
	    self.e = 0
	elif code_g == 162:
	  code_x = self.findCode(gcode, "X")
	  code_y = self.findCode(gcode, "Y")
	  code_z = self.findCode(gcode, "Z")
	  homeAll = False
	  if code_x == None and code_y == None and code_z == None: homeAll = True
	  if code_x != None or homeAll:
	    self.xOffset = 0
	    self.x = self.maxX
	  if code_y != None or homeAll:
	    self.yOffset = 0
	    self.y = self.maxY
	  if code_z != None or homeAll:
	    self.zOffset = 0
	    self.z = self.maxZ
	elif code_g == 90: self.relative = False
	elif code_g == 91: self.relative = True
	elif code_g == 92:
	  code_x = self.findCode(gcode, "X")
	  code_y = self.findCode(gcode, "Y")
	  code_z = self.findCode(gcode, "Z")
	  code_e = self.findCode(gcode, "E")
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
	