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
import datetime
from array import array

gcode_parsed_args = ["x", "y", "e", "f", "z", "i", "j"]
gcode_parsed_nonargs = ["g", "t", "m", "n"]
to_parse = "".join(gcode_parsed_args + gcode_parsed_nonargs)
gcode_exp = re.compile("\([^\(\)]*\)|;.*|[/\*].*\n|([%s])([-+]?[0-9]*\.?[0-9]*)" % to_parse) 
m114_exp = re.compile("\([^\(\)]*\)|[/\*].*\n|([XYZ]):?([-+]?[0-9]*\.?[0-9]*)") 
specific_exp = "(?:\([^\(\)]*\))|(?:;.*)|(?:[/\*].*\n)|(%s[-+]?[0-9]*\.?[0-9]*)"
move_gcodes = ["G0", "G1", "G2", "G3"]

class PyLine(object):

    __slots__ = ('x','y','z','e','f','i','j',
                 'raw','split_raw',
                 'command','is_move',
                 'relative','relative_e',
                 'current_x', 'current_y', 'current_z', 'extruding', 'current_tool',
                 'gcview_end_vertex')

    def __init__(self, l):
        self.raw = l

    def __getattr__(self, name):
        return None

try:
    import gcoder_line
    Line = gcoder_line.GLine
except ImportError:
    Line = PyLine

def find_specific_code(line, code):
    exp = specific_exp % code
    bits = [bit for bit in re.findall(exp, line.raw) if bit]
    if not bits: return None
    else: return float(bits[0][1:])

def S(line):
    return find_specific_code(line, "S")

def P(line):
    return find_specific_code(line, "P")

def split(line):
    split_raw = gcode_exp.findall(line.raw.lower())
    command = split_raw[0] if not split_raw[0] == "n" else split_raw[1]
    line.command = command[0].upper() + command[1]
    line.is_move = line.command in move_gcodes
    return split_raw

def parse_coordinates(line, split_raw, imperial = False, force = False):
    # Not a G-line, we don't want to parse its arguments
    if not force and line.command[0] != "G":
        return
    unit_factor = 25.4 if imperial else 1
    for bit in split_raw:
        code = bit[0]
        if code not in gcode_parsed_nonargs and bit[1]:
            setattr(line, code, unit_factor*float(bit[1]))

class Layer(object):

    lines = None
    duration = None

    def __init__(self, lines):
        self.lines = lines

    def _preprocess(self, current_x, current_y, current_z):
        xmin = float("inf")
        ymin = float("inf")
        zmin = 0
        xmax = float("-inf")
        ymax = float("-inf")
        zmax = float("-inf")
        relative = False
        relative_e = False

        for line in self.lines:
            if not line.is_move and line.command != "G92":
                continue
            if line.is_move:
                x = line.x 
                y = line.y
                z = line.z

                if line.relative:
                    x = current_x + (x or 0)
                    y = current_y + (y or 0)
                    z = current_z + (z or 0)
                
                current_x = x or current_x
                current_y = y or current_y
                current_z = z or current_z

                if line.e:
                    if x:
                        xmin = min(xmin, x)
                        xmax = max(xmax, x)
                    if y:
                        ymin = min(ymin, y)
                        ymax = max(ymax, y)
                    if current_z:
                        zmin = min(zmin, current_z)
                        zmax = max(zmax, current_z)

            else:
                current_x = line.x or current_x
                current_y = line.y or current_y
                current_z = line.z or current_z    

            line.current_x = current_x
            line.current_y = current_y
            line.current_z = current_z
        return (current_x, current_y, current_z), (xmin, xmax), (ymin, ymax), (zmin, zmax)

class GCode(object):

    lines = None
    layers = None
    all_layers = None
    layer_idxs = None
    line_idxs = None
    append_layer = None
    append_layer_id = None

    imperial = False
    relative = False
    relative_e = False
    current_tool = 0

    filament_length = None
    xmin = None
    xmax = None
    ymin = None
    ymax = None
    zmin = None
    zmax = None
    width = None
    depth = None
    height = None

    def __init__(self,data):
        self.lines = [Line(l2) for l2 in
                        (l.strip() for l in data)
                      if l2]
        self._preprocess_lines()
        self.filament_length = self._preprocess_extrusion()
        self._create_layers()
        self._preprocess_layers()

    def __len__(self):
        return len(self.line_idxs)

    def __iter__(self):
        return self.lines.__iter__()

    def append(self, command):
        command = command.strip()
        if not command:
            return
        gline = Line(command)
        self.lines.append(gline)
        self._preprocess_lines([gline])
        self._preprocess_extrusion([gline])
        self.append_layer.lines.append(gline)
        self.layer_idxs.append(self.append_layer_id)
        self.line_idxs.append(len(self.append_layer.lines))
        return gline

    def _preprocess_lines(self, lines = None):
        """Checks for G20, G21, G90 and G91, sets imperial and relative flags"""
        if not lines:
            lines = self.lines
        imperial = self.imperial
        relative = self.relative
        relative_e = self.relative_e
        current_tool = self.current_tool
        for line in lines:
            split_raw = split(line)
            if not line.command:
                continue
            if line.is_move:
                line.relative = relative
                line.relative_e = relative_e
                line.current_tool = current_tool
            elif line.command == "G20":
                imperial = True
            elif line.command == "G21":
                imperial = False
            elif line.command == "G90":
                relative = False
                relative_e = False
            elif line.command == "G91":
                relative = True
                relative_e = True
            elif line.command == "M82":
                relative_e = False
            elif line.command == "M83":
                relative_e = True
            elif line.command[0] == "T":
                current_tool = int(line.command[1:])
            if line.command[0] == "G":
                parse_coordinates(line, split_raw, imperial)
        self.imperial = imperial
        self.relative = relative
        self.relative_e = relative_e
        self.current_tool = current_tool
    
    def _preprocess_extrusion(self, lines = None, cur_e = 0):
        if not lines:
            lines = self.lines

        total_e = 0
        max_e = 0
        
        for line in lines:
            if line.e == None:
                continue
            if line.is_move:
                if line.relative_e:
                    line.extruding = line.e != 0
                    total_e += line.e
                else:
                    line.extruding = line.e != cur_e
                    total_e += line.e - cur_e
                    cur_e = line.e
                max_e = max(max_e, total_e)
            elif line.command == "G92":
                cur_e = line.e

        return max_e
    
    # FIXME : looks like this needs to be tested with list Z on move
    def _create_layers(self):
        layers = {}
        all_layers = []
        layer_idxs = []
        line_idxs = []

        layer_id = 0
        layer_line = 0

        prev_z = None
        cur_z = 0
        cur_lines = []
        for line in self.lines:
            if line.command == "G92" and line.z != None:
                cur_z = line.z
            elif line.is_move:
                if line.z != None:
                    if line.relative:
                        cur_z += line.z
                    else:
                        cur_z = line.z

            if cur_z != prev_z:
                cur_lines = tuple(cur_lines)
                all_layers.append(Layer(cur_lines))
                old_lines = layers.get(prev_z, ())
                old_lines += cur_lines
                layers[prev_z] = old_lines
                cur_lines = []
                layer_id += 1
                layer_line = 0

            cur_lines.append(line)
            layer_idxs.append(layer_id)
            line_idxs.append(layer_line)
            layer_line += 1
            prev_z = cur_z

        if cur_lines:
            cur_lines = tuple(cur_lines)
            all_layers.append(Layer(tuple(cur_lines)))
            old_lines = layers.get(prev_z, ())
            old_lines += cur_lines
            layers[prev_z] = tuple(old_lines)

        for idx in layers.keys():
            cur_lines = layers[idx]
            has_movement = False
            for l in layers[idx]:
                if l.is_move and l.e != None:
                    has_movement = True
                    break
            if has_movement:
                layers[idx] = Layer(cur_lines)
            else:
                del layers[idx]

        self.append_layer_id = len(all_layers)
        self.append_layer = Layer([])
        all_layers.append(self.append_layer)
        self.all_layers = all_layers
        self.layers = layers
        self.layer_idxs = array('I', layer_idxs)
        self.line_idxs = array('I', line_idxs)

    def idxs(self, i):
        return self.layer_idxs[i], self.line_idxs[i]

    def num_layers(self):
        return len(self.layers)

    def _preprocess_layers(self):
        xmin = float("inf")
        ymin = float("inf")
        zmin = 0
        xmax = float("-inf")
        ymax = float("-inf")
        zmax = float("-inf")

        current_x = 0
        current_y = 0
        current_z = 0

        for l in self.all_layers:
            (current_x, current_y, current_z), (xm, xM), (ym, yM), (zm, zM) = l._preprocess(current_x, current_y, current_z)
            xmin = min(xm, xmin)
            xmax = max(xM, xmax)
            ymin = min(ym, ymin)
            ymax = max(yM, ymax)
            zmin = min(zm, zmin)
            zmax = max(zM, zmax)

        self.xmin = xmin if not math.isinf(xmin) else 0
        self.xmax = xmax if not math.isinf(xmax) else 0
        self.ymin = ymin if not math.isinf(ymin) else 0
        self.ymax = ymax if not math.isinf(ymax) else 0
        self.zmin = zmin if not math.isinf(zmin) else 0
        self.zmax = zmax if not math.isinf(zmax) else 0
        self.width = self.xmax - self.xmin
        self.depth = self.ymax - self.ymin
        self.height = self.zmax - self.zmin

    def estimate_duration(self):
        lastx = lasty = lastz = laste = lastf = 0.0
        x = y = z = e = f = 0.0
        currenttravel = 0.0
        totaltravel = 0.0
        moveduration = 0.0
        totalduration = 0.0
        acceleration = 1500.0 #mm/s/s  ASSUMING THE DEFAULT FROM SPRINTER !!!!
        layerduration = 0.0
        layerbeginduration = 0.0
        layercount = 0
        #TODO:
        # get device caps from firmware: max speed, acceleration/axis (including extruder)
        # calculate the maximum move duration accounting for above ;)
        for layer in self.all_layers:
            for line in layer.lines:
                if line.command not in ["G1", "G0", "G4"]:
                    continue
                if line.command == "G4":
                    moveduration = line.p
                    if not moveduration:
                        continue
                    else:
                        moveduration /= 1000.0
                else:
                    x = line.x if line.x != None else lastx
                    y = line.y if line.y != None else lasty
                    e = line.e if line.e != None else laste
                    f = line.f / 60.0 if line.f != None else lastf # mm/s vs mm/m => divide by 60
                    
                    # given last feedrate and current feedrate calculate the distance needed to achieve current feedrate.
                    # if travel is longer than req'd distance, then subtract distance to achieve full speed, and add the time it took to get there.
                    # then calculate the time taken to complete the remaining distance

                    currenttravel = math.hypot(x - lastx, y - lasty)
                    # FIXME: review this better
                    # this looks wrong : there's little chance that the feedrate we'll decelerate to is the previous feedrate
                    # shouldn't we instead look at three consecutive moves ?
                    distance = 2 * abs(((lastf + f) * (f - lastf) * 0.5) / acceleration)  # multiply by 2 because we have to accelerate and decelerate
                    if distance <= currenttravel and lastf + f != 0 and f != 0:
                        # Unsure about this formula -- iXce reviewing this code
                        moveduration = 2 * distance / (lastf + f)
                        currenttravel -= distance
                        moveduration += currenttravel/f
                    else:
                        moveduration = math.sqrt(2 * distance / acceleration) # probably buggy : not taking actual travel into account

                totalduration += moveduration

                lastx = x
                lasty = y
                laste = e
                lastf = f

            layer.duration = totalduration - layerbeginduration
            layerbeginduration = totalduration

        return "%d layers, %s" % (len(self.layers), str(datetime.timedelta(seconds = int(totalduration))))

def main():
    if len(sys.argv) < 2:
        print "usage: %s filename.gcode" % sys.argv[0]
        return

    print "Line object size:", sys.getsizeof(Line("G0 X0"))
    gcode = GCode(open(sys.argv[1])) 

    print "Dimensions:"
    print "\tX: %0.02f - %0.02f (%0.02f)" % (gcode.xmin,gcode.xmax,gcode.width)
    print "\tY: %0.02f - %0.02f (%0.02f)" % (gcode.ymin,gcode.ymax,gcode.depth)
    print "\tZ: %0.02f - %0.02f (%0.02f)" % (gcode.zmin,gcode.zmax,gcode.height)
    print "Filament used: %0.02fmm" % gcode.filament_length
    print "Number of layers: %d" % gcode.num_layers()
    print "Estimated duration: %s" % gcode.estimate_duration()

if __name__ == '__main__':
    main()
