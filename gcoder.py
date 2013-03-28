#!/usr/bin/env python
# This file is copied from GCoder.
#
# GCoder is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# GCoder is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Printrun.  If not, see <http://www.gnu.org/licenses/>.

import sys
import re
import math

def deltalen(a,b):
	d = object()
	d.x = b.x - a.x
	d.y = b.y - a.y
	d.z = b.z - a.z
	
	return math.sqrt((d.x*d.x)+(d.y*d.y)+(d.z*d.z))
	


class Line(object):
	def __init__(self,l):
		self._x = None
		self._y = None
		self._z = None
		self.e = None
		self.f = 0
		
		self.regex = re.compile("[-]?\d+[.]?\d*")
		self.raw = l.upper().lstrip()
		self.imperial = False
		self.relative = False
		self.relative_e = False
		
		if ";" in self.raw:
			self.raw = self.raw.split(";")[0]
		
		self._parse_coordinates()
		
	def _to_mm(self,v):
		if v and self.imperial:
			return v*25.4
		return v
		
	def _getx(self):
		return self._to_mm(self._x)
			
	def _setx(self,v):
		self._x = v

	def _gety(self):
		return self._to_mm(self._y)

	def _sety(self,v):
		self._y = v

	def _getz(self):
		return self._to_mm(self._z)

	def _setz(self,v):
		self._z = v

	def _gete(self):
		return self._to_mm(self._e)

	def _sete(self,v):
		self._e = v

	x = property(_getx,_setx)
	y = property(_gety,_sety)
	z = property(_getz,_setz)
	e = property(_gete,_sete)
	
		
	def command(self):
		try:
			return self.raw.split(" ")[0]
		except:
			return ""
			
	def _get_float(self,which):
		try:
			return float(self.regex.findall(self.raw.split(which)[1])[0])
		except:
			return None
		
	def _parse_coordinates(self):
		try:
			if "X" in self.raw:
				self._x = self._get_float("X")
		except:
			pass

		try:
			if "Y" in self.raw:
				self._y = self._get_float("Y")
		except:
			pass
			
		try:
			if "Z" in self.raw:
				self._z = self._get_float("Z")
		except:
			pass
			
		try:
			if "E" in self.raw:
				self.e = self._get_float("E")
		except:
			pass
			
		try:
			if "F" in self.raw:
				self.f = self._get_float("F")
		except:
			pass
			
		
	def is_move(self):
		return self.command() and ("G1" in self.raw or "G0" in self.raw)
		
		
	def __str__(self):
		return self.raw
		
class Layer(object):
	def __init__(self,lines):
		self.lines = lines
		
		
	def measure(self):
		xmin = 999999999
		ymin = 999999999
		zmin = 0
		xmax = -999999999
		ymax = -999999999
		zmax = -999999999
		relative = False
		relative_e = False

		current_x = 0
		current_y = 0
		current_z = 0

		for line in self.lines:
			if line.command() == "G92":
				current_x = line.x or current_x
				current_y = line.y or current_y
				current_z = line.z or current_z	

			if line.is_move():
				x = line.x 
				y = line.y
				z = line.z

				if line.relative:
					x = current_x + (x or 0)
					y = current_y + (y or 0)
					z = current_z + (z or 0)


				if x and line.e:
					if x < xmin:
						xmin = x
					if x > xmax:
						xmax = x
				if y and line.e:
					if y < ymin:
						ymin = y
					if y > ymax:
						ymax = y
				if z:
					if z < zmin:
						zmin = z
					if z > zmax:
						zmax = z

				current_x = x or current_x
				current_y = y or current_y
				current_z = z or current_z

		return ( (xmin,xmax),(ymin,ymax),(zmin,zmax) )
	

class GCode(object):
	def __init__(self,data):
		self.lines = [Line(i) for i in data]
		self._preprocess()
		self._create_layers()

	def _preprocess(self):
		#checks for G20, G21, G90 and G91, sets imperial and relative flags
		imperial = False
		relative = False
		relative_e = False
		for line in self.lines:
			if line.command() == "G20":
				imperial = True
			elif line.command() == "G21":
				imperial = False
			elif line.command() == "G90":
				relative = False
				relative_e = False
			elif line.command() == "G91":
				relative = True
				relative_e = True
			elif line.command() == "M82":
				relative_e = False
			elif line.command() == "M83":
				relative_e = True
			elif line.is_move():
				line.imperial = imperial
				line.relative = relative
				line.relative_e = relative_e
		
	def _create_layers(self):
		self.layers = []

		prev_z = None
		cur_z = 0
		cur_lines = []
		layer_index = []
		
		temp_layers = {}
		for line in self.lines:
			if line.command() == "G92" and line.z != None:
				cur_z = line.z
			elif line.is_move():
				if line.z != None:
					if line.relative:
						cur_z += line.z
					else:
						cur_z = line.z
					
			if cur_z != prev_z:
				old_lines = temp_layers.pop(prev_z,[])
				old_lines += cur_lines
				temp_layers[prev_z] = old_lines

				if not prev_z in layer_index:
					layer_index.append(prev_z)
					
				cur_lines = []
			
			cur_lines.append(line)
			prev_z = cur_z
		
		
		old_lines = temp_layers.pop(prev_z,[])
		old_lines += cur_lines
		temp_layers[prev_z] = old_lines

		if not prev_z in layer_index:
			layer_index.append(prev_z)
			
		layer_index.sort()
		
		for idx in layer_index:
			cur_lines = temp_layers[idx]
			has_movement = False
			for l in cur_lines:
				if l.is_move() and l.e != None:
					has_movement = True
					break
			
			if has_movement:
				self.layers.append(Layer(cur_lines))
			

	def num_layers(self):
		return len(self.layers)
				

	def measure(self):
		xmin = 999999999
		ymin = 999999999
		zmin = 0
		xmax = -999999999
		ymax = -999999999
		zmax = -999999999

		for l in self.layers:
			xd,yd,zd = l.measure()
			if xd[0] < xmin:
				xmin = xd[0]
			if xd[1] > xmax:
				xmax = xd[1]

			if yd[0] < ymin:
				ymin = yd[0]
			if yd[1] > ymax:
				ymax = yd[1]

			if zd[0] < zmin:
				zmin = zd[0]
			if zd[1] > zmax:
				zmax = zd[1]

		self.xmin = xmin
		self.xmax = xmax
		self.ymin = ymin
		self.ymax = ymax
		self.zmin = zmin
		self.zmax = zmax
		self.width = xmax - xmin
		self.depth = ymax - ymin
		self.height = zmax - zmin
	
	def filament_length(self):
		total_e = 0		
		cur_e = 0
		
		for line in self.lines:
			if line.command() == "G92":
				if line.e != None:
					total_e += cur_e
					cur_e = line.e
			elif line.is_move() and line.e:
				if line.relative_e:
					cur_e += line.e
				else:
					cur_e = line.e
				
				
		return total_e


def main():
	if len(sys.argv) < 2:
		print "usage: %s filename.gcode" % sys.argv[0]
		return

#	d = [i.replace("\n","") for i in open(sys.argv[1])]
#	gcode = GCode(d)
	gcode = GCode(list(open(sys.argv[1]))) 
	
	gcode.measure()

	print "Dimensions:"
	print "\tX: %0.02f - %0.02f (%0.02f)" % (gcode.xmin,gcode.xmax,gcode.width)
	print "\tY: %0.02f - %0.02f (%0.02f)" % (gcode.ymin,gcode.ymax,gcode.depth)
	print "\tZ: %0.02f - %0.02f (%0.02f)" % (gcode.zmin,gcode.zmax,gcode.height)
	print "Filament used: %0.02fmm" % gcode.filament_length()
	print "Number of layers: %d" % gcode.num_layers()


if __name__ == '__main__':
	main()
