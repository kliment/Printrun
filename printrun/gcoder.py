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
import logging
from array import array

gcode_parsed_args = ["x", "y", "e", "f", "z", "i", "j"]
gcode_parsed_nonargs = ["g", "t", "m", "n"]
to_parse = "".join(gcode_parsed_args + gcode_parsed_nonargs)
gcode_exp = re.compile("\([^\(\)]*\)|;.*|[/\*].*\n|([%s])([-+]?[0-9]*\.?[0-9]*)" % to_parse)
m114_exp = re.compile("\([^\(\)]*\)|[/\*].*\n|([XYZ]):?([-+]?[0-9]*\.?[0-9]*)")
specific_exp = "(?:\([^\(\)]*\))|(?:;.*)|(?:[/\*].*\n)|(%s[-+]?[0-9]*\.?[0-9]*)"
move_gcodes = ["G0", "G1", "G2", "G3"]

class PyLine(object):

    __slots__ = ('x', 'y', 'z', 'e', 'f', 'i', 'j',
                 'raw', 'command', 'is_move',
                 'relative', 'relative_e',
                 'current_x', 'current_y', 'current_z', 'extruding',
                 'current_tool',
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
    if not split_raw:
        line.command = line.raw
        line.is_move = False
        logging.warning("raw G-Code line \"%s\" could not be parsed" % line.raw)
        return line.raw
    command = split_raw[0] if split_raw[0][0] != "n" else split_raw[1]
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
            setattr(line, code, unit_factor * float(bit[1]))

class Layer(list):

    __slots__ = ("duration", "z")

    def __init__(self, lines, z = None):
        super(Layer, self).__init__(lines)
        self.z = z

    def _preprocess(self, current_x, current_y, current_z,
                    offset_x, offset_y, offset_z, ignore_noe = False):
        xmin = float("inf")
        ymin = float("inf")
        zmin = 0
        xmax = float("-inf")
        ymax = float("-inf")
        zmax = float("-inf")

        for line in self:
            if not line.is_move and line.command != "G92" and line.command != "G28":
                continue
            if line.is_move:
                x = line.x
                y = line.y
                z = line.z

                if line.relative:
                    x = current_x + (x or 0)
                    y = current_y + (y or 0)
                    z = current_z + (z or 0)
                else:
                    if line.x: x = line.x + offset_x
                    if line.y: y = line.y + offset_y
                    if line.z: z = line.z + offset_z

                current_x = x or current_x
                current_y = y or current_y
                current_z = z or current_z

                if line.e or not ignore_noe:
                    if x:
                        xmin = min(xmin, x)
                        xmax = max(xmax, x)
                    if y:
                        ymin = min(ymin, y)
                        ymax = max(ymax, y)
                    if current_z:
                        zmin = min(zmin, current_z)
                        zmax = max(zmax, current_z)

            elif line.command == "G28":
                if not any([line.x, line.y, line.z]):
                    current_x = current_y = current_z = 0
                else:
                    if line.x: current_x = 0
                    if line.y: current_y = 0
                    if line.z: current_z = 0

            elif line.command == "G92":
                if line.x: offset_x = current_x - line.x
                if line.y: offset_y = current_y - line.y
                if line.z: offset_z = current_z - line.z

            line.current_x = current_x
            line.current_y = current_y
            line.current_z = current_z
        return ((current_x, current_y, current_z),
                (offset_x, offset_y, offset_z),
                (xmin, xmax), (ymin, ymax), (zmin, zmax))

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

    est_layer_height = None

    def __init__(self, data):
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
        self.append_layer.append(gline)
        self.layer_idxs.append(self.append_layer_id)
        self.line_idxs.append(len(self.append_layer))
        return gline

    def _preprocess_lines(self, lines = None):
        """Checks for imperial/relativeness settings and tool changes"""
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
            if line.e is None:
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

        last_layer_z = None
        prev_z = None
        prev_base_z = (None, None)
        cur_z = None
        cur_lines = []
        for line in self.lines:
            if line.command == "G92" and line.z is not None:
                cur_z = line.z
            elif line.is_move:
                if line.z is not None:
                    if line.relative:
                        cur_z += line.z
                    else:
                        cur_z = line.z

            # FIXME: the logic behind this code seems to work, but it might be
            # broken
            if cur_z != prev_z:
                if prev_z is not None and last_layer_z is not None:
                    offset = self.est_layer_height if self.est_layer_height else 0.01
                    if abs(prev_z - last_layer_z) < offset:
                        if self.est_layer_height is None:
                            zs = sorted([l.z for l in all_layers if l.z is not None])
                            heights = [round(zs[i + 1] - zs[i], 3) for i in range(len(zs) - 1)]
                            if len(heights) >= 2: self.est_layer_height = heights[1]
                            elif heights: self.est_layer_height = heights[0]
                            else: self.est_layer_height = 0.1
                        base_z = round(prev_z - (prev_z % self.est_layer_height), 2)
                    else:
                        base_z = round(prev_z, 2)
                else:
                    base_z = prev_z

                if base_z != prev_base_z:
                    all_layers.append(Layer(cur_lines, base_z))
                    old_lines = layers.get(base_z, [])
                    old_lines += cur_lines
                    layers[base_z] = old_lines
                    cur_lines = []
                    layer_id += 1
                    layer_line = 0
                    last_layer_z = base_z

                prev_base_z = base_z

            cur_lines.append(line)
            layer_idxs.append(layer_id)
            line_idxs.append(layer_line)
            layer_line += 1
            prev_z = cur_z

        if cur_lines:
            all_layers.append(Layer(cur_lines, prev_z))
            old_lines = layers.get(prev_z, [])
            old_lines += cur_lines
            layers[prev_z] = old_lines

        for zindex in layers.keys():
            cur_lines = layers[zindex]
            has_movement = False
            for l in layers[zindex]:
                if l.is_move and l.e is not None:
                    has_movement = True
                    break
            if has_movement:
                layers[zindex] = Layer(cur_lines, zindex)
            else:
                del layers[zindex]

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
        offset_x = 0
        offset_y = 0
        offset_z = 0

        ignore_noe = self.filament_length > 0

        for l in self.all_layers:
            meta = l._preprocess(current_x, current_y, current_z,
                                 offset_x, offset_y, offset_z,
                                 ignore_noe)
            current_x, current_y, current_z = meta[0]
            offset_x, offset_y, offset_z = meta[1]
            (xm, xM), (ym, yM), (zm, zM) = meta[2:]
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
        lastdx = 0
        lastdy = 0
        x = y = e = f = 0.0
        currenttravel = 0.0
        moveduration = 0.0
        totalduration = 0.0
        acceleration = 2000.0  # mm/s^2
        layerbeginduration = 0.0
        #TODO:
        # get device caps from firmware: max speed, acceleration/axis
        # (including extruder)
        # calculate the maximum move duration accounting for above ;)
        for layer in self.all_layers:
            for line in layer:
                if line.command not in ["G1", "G0", "G4"]:
                    continue
                if line.command == "G4":
                    moveduration = line.p
                    if not moveduration:
                        continue
                    else:
                        moveduration /= 1000.0
                else:
                    x = line.x if line.x is not None else lastx
                    y = line.y if line.y is not None else lasty
                    z = line.z if line.z is not None else lastz
                    e = line.e if line.e is not None else laste
                    # mm/s vs mm/m => divide by 60
                    f = line.f / 60.0 if line.f is not None else lastf

                    # given last feedrate and current feedrate calculate the
                    # distance needed to achieve current feedrate.
                    # if travel is longer than req'd distance, then subtract
                    # distance to achieve full speed, and add the time it took
                    # to get there.
                    # then calculate the time taken to complete the remaining
                    # distance

                    # FIXME: this code has been proven to be super wrong when 2
                    # subsquent moves are in opposite directions, as requested
                    # speed is constant but printer has to fully decellerate
                    # and reaccelerate
                    # The following code tries to fix it by forcing a full
                    # reacceleration if this move is in the opposite direction
                    # of the previous one
                    dx = x - lastx
                    dy = y - lasty
                    if dx * lastdx + dy * lastdy <= 0:
                        lastf = 0

                    currenttravel = math.hypot(dx, dy)
                    if currenttravel == 0:
                        if line.z is not None:
                            currenttravel = abs(line.z) if line.relative else abs(line.z - lastz)
                        elif line.e is not None:
                            currenttravel = abs(line.e) if line.relative_e else abs(line.e - laste)
                    # Feedrate hasn't changed, no acceleration/decceleration planned
                    if f == lastf:
                        moveduration = currenttravel / f if f != 0 else 0.
                    else:
                        # FIXME: review this better
                        # this looks wrong : there's little chance that the feedrate we'll decelerate to is the previous feedrate
                        # shouldn't we instead look at three consecutive moves ?
                        distance = 2 * abs(((lastf + f) * (f - lastf) * 0.5) / acceleration)  # multiply by 2 because we have to accelerate and decelerate
                        if distance <= currenttravel and lastf + f != 0 and f != 0:
                            moveduration = 2 * distance / (lastf + f)  # This is distance / mean(lastf, f)
                            moveduration += (currenttravel - distance) / f
                        else:
                            moveduration = 2 * currenttravel / (lastf + f)  # This is currenttravel / mean(lastf, f)
                            # FIXME: probably a little bit optimistic, but probably a much better estimate than the previous one:
                            # moveduration = math.sqrt(2 * distance / acceleration) # probably buggy : not taking actual travel into account

                    lastdx = dx
                    lastdy = dy

                totalduration += moveduration

                lastx = x
                lasty = y
                lastz = z
                laste = e
                lastf = f

            layer.duration = totalduration - layerbeginduration
            layerbeginduration = totalduration

        totaltime = datetime.timedelta(seconds = int(totalduration))
        return "%d layers, %s" % (len(self.layers), str(totaltime))

def main():
    if len(sys.argv) < 2:
        print "usage: %s filename.gcode" % sys.argv[0]
        return

    print "Line object size:", sys.getsizeof(Line("G0 X0"))
    gcode = GCode(open(sys.argv[1], "rU"))

    print "Dimensions:"
    xdims = (gcode.xmin, gcode.xmax, gcode.width)
    print "\tX: %0.02f - %0.02f (%0.02f)" % xdims
    ydims = (gcode.ymin, gcode.ymax, gcode.depth)
    print "\tY: %0.02f - %0.02f (%0.02f)" % ydims
    zdims = (gcode.zmin, gcode.zmax, gcode.height)
    print "\tZ: %0.02f - %0.02f (%0.02f)" % zdims
    print "Filament used: %0.02fmm" % gcode.filament_length
    print "Number of layers: %d" % gcode.num_layers()
    print "Estimated duration: %s" % gcode.estimate_duration()

if __name__ == '__main__':
    main()
