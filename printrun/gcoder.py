#!/usr/bin/env python3
#
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

import sys
import re
import math
import datetime
import logging
from array import array

gcode_parsed_args = ["x", "y", "e", "f", "z", "i", "j"]
gcode_parsed_nonargs = ["g", "t", "m", "n"]
to_parse = "".join(gcode_parsed_args + gcode_parsed_nonargs)
gcode_exp = re.compile("\([^\(\)]*\)|;.*|[/\*].*\n|([%s])\s*([-+]?[0-9]*\.?[0-9]*)" % to_parse)
gcode_strip_comment_exp = re.compile("\([^\(\)]*\)|;.*|[/\*].*\n")
m114_exp = re.compile("\([^\(\)]*\)|[/\*].*\n|([XYZ]):?([-+]?[0-9]*\.?[0-9]*)")
specific_exp = "(?:\([^\(\)]*\))|(?:;.*)|(?:[/\*].*\n)|(%s[-+]?[0-9]*\.?[0-9]*)"
move_gcodes = ["G0", "G1", "G2", "G3"]

class PyLine:

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

class PyLightLine:

    __slots__ = ('raw', 'command')

    def __init__(self, l):
        self.raw = l

    def __getattr__(self, name):
        return None

try:
    from . import gcoder_line
    Line = gcoder_line.GLine
    LightLine = gcoder_line.GLightLine
except Exception as e:
    logging.warning("Memory-efficient GCoder implementation unavailable: %s" % e)
    Line = PyLine
    LightLine = PyLightLine

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
    if split_raw and split_raw[0][0] == "n":
        del split_raw[0]
    if not split_raw:
        line.command = line.raw
        line.is_move = False
        logging.warning("raw G-Code line \"%s\" could not be parsed" % line.raw)
        return [line.raw]
    command = split_raw[0]
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

class GCode:

    line_class = Line

    lines = None
    layers = None
    all_layers = None
    layer_idxs = None
    line_idxs = None
    append_layer = None
    append_layer_id = None

    imperial = False
    cutting = False
    relative = False
    relative_e = False
    current_tool = 0
    # Home position: current absolute position counted from machine origin
    home_x = 0
    home_y = 0
    home_z = 0
    # Current position: current absolute position counted from machine origin
    current_x = 0
    current_y = 0
    current_z = 0
    # For E this is the absolute position from machine start
    current_e = 0
    current_e_multi=[0]
    total_e = 0
    total_e_multi=[0]
    max_e = 0
    max_e_multi=[0]
    # Current feedrate
    current_f = 0
    # Offset: current offset between the machine origin and the machine current
    # absolute coordinate system (as shifted by G92s)
    offset_x = 0
    offset_y = 0
    offset_z = 0
    offset_e = 0
    offset_e_multi = [0]

    # Expected behavior:
    # - G28 X => X axis is homed, offset_x <- 0, current_x <- home_x
    # - G92 Xk => X axis does not move, so current_x does not change
    #             and offset_x <- current_x - k,
    # - absolute G1 Xk => X axis moves, current_x <- offset_x + k
    # How to get...
    # current abs X from machine origin: current_x
    # current abs X in machine current coordinate system: current_x - offset_x

    filament_length = None
    filament_length_multi=[0]
    duration = None
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

    # abs_x is the current absolute X in machine current coordinate system
    # (after the various G92 transformations) and can be used to store the
    # absolute position of the head at a given time
    def _get_abs_x(self):
        return self.current_x - self.offset_x
    abs_x = property(_get_abs_x)

    def _get_abs_y(self):
        return self.current_y - self.offset_y
    abs_y = property(_get_abs_y)

    def _get_abs_z(self):
        return self.current_z - self.offset_z
    abs_z = property(_get_abs_z)

    def _get_abs_e(self):
        return self.current_e - self.offset_e
    abs_e = property(_get_abs_e)

    def _get_abs_e_multi(self,i):
        return self.current_e_multi[i] - self.offset_e_multi[i]
    abs_e = property(_get_abs_e)

    def _get_abs_pos(self):
        return (self.abs_x, self.abs_y, self.abs_z)
    abs_pos = property(_get_abs_pos)

    def _get_current_pos(self):
        return (self.current_x, self.current_y, self.current_z)
    current_pos = property(_get_current_pos)

    def _get_home_pos(self):
        return (self.home_x, self.home_y, self.home_z)

    def _set_home_pos(self, home_pos):
        if home_pos:
            self.home_x, self.home_y, self.home_z = home_pos
    home_pos = property(_get_home_pos, _set_home_pos)

    def _get_layers_count(self):
        return len(self.all_zs)
    layers_count = property(_get_layers_count)

    def __init__(self, data = None, home_pos = None,
                 layer_callback = None, deferred = False,
                 cutting_as_extrusion = False):
        self.cutting_as_extrusion = cutting_as_extrusion
        if not deferred:
            self.prepare(data, home_pos, layer_callback)

    def prepare(self, data = None, home_pos = None, layer_callback = None):
        self.home_pos = home_pos
        if data:
            line_class = self.line_class
            self.lines = [line_class(l2) for l2 in
                          (l.strip() for l in data)
                          if l2]
            self._preprocess(build_layers = True,
                             layer_callback = layer_callback)
        else:
            self.lines = []
            self.append_layer_id = 0
            self.append_layer = Layer([])
            self.all_layers = [self.append_layer]
            self.all_zs = set()
            self.layers = {}
            self.layer_idxs = array('I', [])
            self.line_idxs = array('I', [])

    def has_index(self, i):
        return i < len(self)
    def __len__(self):
        return len(self.line_idxs)

    def __iter__(self):
        return self.lines.__iter__()

    def prepend_to_layer(self, commands, layer_idx):
        # Prepend commands in reverse order
        commands = [c.strip() for c in commands[::-1] if c.strip()]
        layer = self.all_layers[layer_idx]
        # Find start index to append lines
        # and end index to append new indices
        start_index = self.layer_idxs.index(layer_idx)
        for i in range(start_index, len(self.layer_idxs)):
            if self.layer_idxs[i] != layer_idx:
                end_index = i
                break
        else:
            end_index = i + 1
        end_line = self.line_idxs[end_index - 1]
        for i, command in enumerate(commands):
            gline = Line(command)
            # Split to get command
            split(gline)
            # Force is_move to False
            gline.is_move = False
            # Insert gline at beginning of layer
            layer.insert(0, gline)
            # Insert gline at beginning of list
            self.lines.insert(start_index, gline)
            # Update indices arrays & global gcodes list
            self.layer_idxs.insert(end_index + i, layer_idx)
            self.line_idxs.insert(end_index + i, end_line + i + 1)
        return commands[::-1]

    def rewrite_layer(self, commands, layer_idx):
        # Prepend commands in reverse order
        commands = [c.strip() for c in commands[::-1] if c.strip()]
        layer = self.all_layers[layer_idx]
        # Find start index to append lines
        # and end index to append new indices
        start_index = self.layer_idxs.index(layer_idx)
        for i in range(start_index, len(self.layer_idxs)):
            if self.layer_idxs[i] != layer_idx:
                end_index = i
                break
        else:
            end_index = i + 1
        self.layer_idxs = self.layer_idxs[:start_index] + array('I', len(commands) * [layer_idx]) + self.layer_idxs[end_index:]
        self.line_idxs = self.line_idxs[:start_index] + array('I', range(len(commands))) + self.line_idxs[end_index:]
        del self.lines[start_index:end_index]
        del layer[:]
        for i, command in enumerate(commands):
            gline = Line(command)
            # Split to get command
            split(gline)
            # Force is_move to False
            gline.is_move = False
            # Insert gline at beginning of layer
            layer.insert(0, gline)
            # Insert gline at beginning of list
            self.lines.insert(start_index, gline)
        return commands[::-1]

    def append(self, command, store = True):
        command = command.strip()
        if not command:
            return
        gline = Line(command)
        self._preprocess([gline])
        if store:
            self.lines.append(gline)
            self.append_layer.append(gline)
            self.layer_idxs.append(self.append_layer_id)
            self.line_idxs.append(len(self.append_layer)-1)
        return gline

    def _preprocess(self, lines = None, build_layers = False,
                    layer_callback = None):
        """Checks for imperial/relativeness settings and tool changes"""
        if not lines:
            lines = self.lines
        imperial = self.imperial
        relative = self.relative
        relative_e = self.relative_e
        current_tool = self.current_tool
        current_x = self.current_x
        current_y = self.current_y
        current_z = self.current_z
        offset_x = self.offset_x
        offset_y = self.offset_y
        offset_z = self.offset_z

        # Extrusion computation
        current_e = self.current_e
        offset_e = self.offset_e
        total_e = self.total_e
        max_e = self.max_e
        cutting = self.cutting

        current_e_multi = self.current_e_multi[current_tool]
        offset_e_multi = self.offset_e_multi[current_tool]
        total_e_multi = self.total_e_multi[current_tool]
        max_e_multi = self.max_e_multi[current_tool]

        # Store this one out of the build_layers scope for efficiency
        cur_layer_has_extrusion = False

        # Initialize layers and other global computations
        if build_layers:
            # Bounding box computation
            xmin = float("inf")
            ymin = float("inf")
            zmin = 0
            xmax = float("-inf")
            ymax = float("-inf")
            zmax = float("-inf")
            # Also compute extrusion-only values
            xmin_e = float("inf")
            ymin_e = float("inf")
            xmax_e = float("-inf")
            ymax_e = float("-inf")

            # Duration estimation
            # TODO:
            # get device caps from firmware: max speed, acceleration/axis
            # (including extruder)
            # calculate the maximum move duration accounting for above ;)
            lastx = lasty = lastz = laste = lastf = 0.0
            lastdx = 0
            lastdy = 0
            x = y = e = f = 0.0
            currenttravel = 0.0
            moveduration = 0.0
            totalduration = 0.0
            acceleration = 2000.0  # mm/s^2
            layerbeginduration = 0.0

            # Initialize layers
            all_layers = self.all_layers = []
            all_zs = self.all_zs = set()
            layer_idxs = self.layer_idxs = []
            line_idxs = self.line_idxs = []

            layer_id = 0
            layer_line = 0

            last_layer_z = None
            prev_z = None
            prev_base_z = (None, None)
            cur_z = None
            cur_lines = []

        if self.line_class != Line:
            get_line = lambda l: Line(l.raw)
        else:
            get_line = lambda l: l
        for true_line in lines:
            # # Parse line
            # Use a heavy copy of the light line to preprocess
            line = get_line(true_line)
            split_raw = split(line)
            if line.command:
                # Update properties
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
                    try:
                        current_tool = int(line.command[1:])
                    except:
                        pass #handle T? by treating it as no tool change
                    while(current_tool+1>len(self.current_e_multi)):
                        self.current_e_multi+=[0]
                        self.offset_e_multi+=[0]
                        self.total_e_multi+=[0]
                        self.max_e_multi+=[0]
                elif line.command == "M3" or line.command == "M4":
                    cutting = True
                elif line.command == "M5":
                    cutting = False

                current_e_multi = self.current_e_multi[current_tool]
                offset_e_multi = self.offset_e_multi[current_tool]
                total_e_multi = self.total_e_multi[current_tool]
                max_e_multi = self.max_e_multi[current_tool]


                if line.command[0] == "G":
                    parse_coordinates(line, split_raw, imperial)

                # Compute current position
                if line.is_move:
                    x = line.x
                    y = line.y
                    z = line.z

                    if line.f is not None:
                        self.current_f = line.f

                    if line.relative:
                        x = current_x + (x or 0)
                        y = current_y + (y or 0)
                        z = current_z + (z or 0)
                    else:
                        if x is not None: x = x + offset_x
                        if y is not None: y = y + offset_y
                        if z is not None: z = z + offset_z

                    if x is not None: current_x = x
                    if y is not None: current_y = y
                    if z is not None: current_z = z

                elif line.command == "G28":
                    home_all = not any([line.x, line.y, line.z])
                    if home_all or line.x is not None:
                        offset_x = 0
                        current_x = self.home_x
                    if home_all or line.y is not None:
                        offset_y = 0
                        current_y = self.home_y
                    if home_all or line.z is not None:
                        offset_z = 0
                        current_z = self.home_z

                elif line.command == "G92":
                    if line.x is not None: offset_x = current_x - line.x
                    if line.y is not None: offset_y = current_y - line.y
                    if line.z is not None: offset_z = current_z - line.z

                line.current_x = current_x
                line.current_y = current_y
                line.current_z = current_z

                # # Process extrusion
                if line.e is not None:
                    if line.is_move:
                        if line.relative_e:
                            line.extruding = line.e > 0
                            total_e += line.e
                            current_e += line.e
                            total_e_multi += line.e
                            current_e_multi += line.e
                        else:
                            new_e = line.e + offset_e
                            line.extruding = new_e > current_e
                            total_e += new_e - current_e
                            current_e = new_e
                            new_e_multi = line.e + offset_e_multi
                            total_e_multi += new_e_multi - current_e_multi
                            current_e_multi = new_e_multi

                        max_e = max(max_e, total_e)
                        max_e_multi=max(max_e_multi, total_e_multi)
                        cur_layer_has_extrusion |= line.extruding
                    elif line.command == "G92":
                        offset_e = current_e - line.e
                        offset_e_multi = current_e_multi - line.e
                if cutting and self.cutting_as_extrusion:
                    line.extruding = True

                self.current_e_multi[current_tool]=current_e_multi
                self.offset_e_multi[current_tool]=offset_e_multi
                self.max_e_multi[current_tool]=max_e_multi
                self.total_e_multi[current_tool]=total_e_multi

                # # Create layers and perform global computations
                if build_layers:
                    # Update bounding box
                    if line.is_move:
                        if line.extruding:
                            if line.current_x is not None:
                                xmin_e = min(xmin_e, line.current_x)
                                xmax_e = max(xmax_e, line.current_x)
                            if line.current_y is not None:
                                ymin_e = min(ymin_e, line.current_y)
                                ymax_e = max(ymax_e, line.current_y)
                        if max_e <= 0:
                            if line.current_x is not None:
                                xmin = min(xmin, line.current_x)
                                xmax = max(xmax, line.current_x)
                            if line.current_y is not None:
                                ymin = min(ymin, line.current_y)
                                ymax = max(ymax, line.current_y)

                    # Compute duration
                    if line.command == "G0" or line.command == "G1":
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
                    elif line.command == "G4":
                        moveduration = P(line)
                        if moveduration:
                            moveduration /= 1000.0
                            totalduration += moveduration

                    # FIXME : looks like this needs to be tested with "lift Z on move"
                    if line.z is not None:
                        if line.command == "G92":
                            cur_z = line.z
                        elif line.is_move:
                            if line.relative and cur_z is not None:
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
                                    heights = [height for height in heights if height]
                                    if len(heights) >= 2: self.est_layer_height = heights[1]
                                    elif heights: self.est_layer_height = heights[0]
                                    else: self.est_layer_height = 0.1
                                base_z = round(prev_z - (prev_z % self.est_layer_height), 2)
                            else:
                                base_z = round(prev_z, 2)
                        else:
                            base_z = prev_z

                        if base_z != prev_base_z:
                            new_layer = Layer(cur_lines, base_z)
                            new_layer.duration = totalduration - layerbeginduration
                            layerbeginduration = totalduration
                            all_layers.append(new_layer)
                            if cur_layer_has_extrusion and prev_z not in all_zs:
                                all_zs.add(prev_z)
                            cur_lines = []
                            cur_layer_has_extrusion = False
                            layer_id += 1
                            layer_line = 0
                            last_layer_z = base_z
                            if layer_callback is not None:
                                layer_callback(self, len(all_layers) - 1)

                        prev_base_z = base_z

            if build_layers:
                cur_lines.append(true_line)
                layer_idxs.append(layer_id)
                line_idxs.append(layer_line)
                layer_line += 1
                prev_z = cur_z
            # ## Loop done

        # Store current status
        self.imperial = imperial
        self.relative = relative
        self.relative_e = relative_e
        self.current_tool = current_tool
        self.current_x = current_x
        self.current_y = current_y
        self.current_z = current_z
        self.offset_x = offset_x
        self.offset_y = offset_y
        self.offset_z = offset_z
        self.current_e = current_e
        self.offset_e = offset_e
        self.max_e = max_e
        self.total_e = total_e
        self.current_e_multi[current_tool]=current_e_multi
        self.offset_e_multi[current_tool]=offset_e_multi
        self.max_e_multi[current_tool]=max_e_multi
        self.total_e_multi[current_tool]=total_e_multi
        self.cutting = cutting


        # Finalize layers
        if build_layers:
            if cur_lines:
                new_layer = Layer(cur_lines, prev_z)
                new_layer.duration = totalduration - layerbeginduration
                layerbeginduration = totalduration
                all_layers.append(new_layer)
                if cur_layer_has_extrusion and prev_z not in all_zs:
                    all_zs.add(prev_z)

            self.append_layer_id = len(all_layers)
            self.append_layer = Layer([])
            self.append_layer.duration = 0
            all_layers.append(self.append_layer)
            self.layer_idxs = array('I', layer_idxs)
            self.line_idxs = array('I', line_idxs)

            # Compute bounding box
            all_zs = self.all_zs.union({zmin}).difference({None})
            zmin = min(all_zs)
            zmax = max(all_zs)

            self.filament_length = self.max_e
            while len(self.filament_length_multi)<len(self.max_e_multi):
                    self.filament_length_multi+=[0]
            for i in enumerate(self.max_e_multi):
                self.filament_length_multi[i[0]]=i[1]


            if self.filament_length > 0:
                self.xmin = xmin_e if not math.isinf(xmin_e) else 0
                self.xmax = xmax_e if not math.isinf(xmax_e) else 0
                self.ymin = ymin_e if not math.isinf(ymin_e) else 0
                self.ymax = ymax_e if not math.isinf(ymax_e) else 0
            else:
                self.xmin = xmin if not math.isinf(xmin) else 0
                self.xmax = xmax if not math.isinf(xmax) else 0
                self.ymin = ymin if not math.isinf(ymin) else 0
                self.ymax = ymax if not math.isinf(ymax) else 0
            self.zmin = zmin if not math.isinf(zmin) else 0
            self.zmax = zmax if not math.isinf(zmax) else 0
            self.width = self.xmax - self.xmin
            self.depth = self.ymax - self.ymin
            self.height = self.zmax - self.zmin

            # Finalize duration
            totaltime = datetime.timedelta(seconds = int(totalduration))
            self.duration = totaltime

    def idxs(self, i):
        return self.layer_idxs[i], self.line_idxs[i]

    def estimate_duration(self):
        return self.layers_count, self.duration

class LightGCode(GCode):
    line_class = LightLine

def main():
    if len(sys.argv) < 2:
        print("usage: %s filename.gcode" % sys.argv[0])
        return

    print("Line object size:", sys.getsizeof(Line("G0 X0")))
    print("Light line object size:", sys.getsizeof(LightLine("G0 X0")))
    gcode = GCode(open(sys.argv[1], "rU"))

    print("Dimensions:")
    xdims = (gcode.xmin, gcode.xmax, gcode.width)
    print("\tX: %0.02f - %0.02f (%0.02f)" % xdims)
    ydims = (gcode.ymin, gcode.ymax, gcode.depth)
    print("\tY: %0.02f - %0.02f (%0.02f)" % ydims)
    zdims = (gcode.zmin, gcode.zmax, gcode.height)
    print("\tZ: %0.02f - %0.02f (%0.02f)" % zdims)
    print("Filament used: %0.02fmm" % gcode.filament_length)
    for i in enumerate(gcode.filament_length_multi):
        print("E%d %0.02fmm" % (i[0],i[1]))
    print("Number of layers: %d" % gcode.layers_count)
    print("Estimated duration: %s" % gcode.estimate_duration()[1])

if __name__ == '__main__':
    main()
