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

# Module for sending sync gcodes to printer with optional return info, e.g. M114 position
import time
from printrun.plugins.sample import SampleHandler
import re
import threading
import printcore
import numpy as np

verbose = False
class MyHandler(SampleHandler):
    def __init__(self):
        SampleHandler.__init__(self)
        self.clear()
    def clear(self):
        self.printer_response = []
    def on_recv(self, ln):
        self.printer_response.append(ln)
        if ln.startswith('ok'):
            with ok_received:
                ok_received.notify()
        elif verbose:
            print('>', ln, end='');

def connect(tty, baud):
    global p, h
    p = printcore.printcore(tty, baud, True)
    h = MyHandler()
    p.event_handler.append(h)
    while not p.online:
        print('not online, reset()...')
        p.reset();
        time.sleep(3)
        if p.online:
            print('online')
            return p
ok_received = threading.Condition()
def wait_ok():
    with ok_received:
        ok_received.wait()
def send(gcode):
    h.clear()
    p.send(gcode)
    wait_ok()
#--
class SyncCommand(object):
    def __init__(self, has_return=False):
        self.has_return = has_return
    def send(self, *args):
        send(self.name() + ' ' + ' '.join(args))
        if self.has_return:
            self.parseResponse(h.printer_response)
    def name(self):
        return self.__class__.__name__.replace('Class', '')
        
    def parseResponse(self, resp):
        pass # override

class M114Class(SyncCommand):
    def __init__(self):
        SyncCommand.__init__(self, True)
        self.x = self.y = self.z = None
    def parseResponse(self, lines):
        #X:0.00 Y:0.00 Z:0.00 E:0.00
        # process all lines b/c we can receive 'echo:busy: processing' from previous G0 cmds
        for ln in lines:
            m = re.match('X:([\d.-]+)\sY:([\d.-]+)\sZ:([\d.-]+)', ln)
            if m:
                self.x, self.y, self.z = [float(f) for f in m.groups()]
class M420Class(SyncCommand):
    def __init__(self):
        SyncCommand.__init__(self,True)
    def parseResponse(self, lines):
        self.leveling_enabled = None
        dc = {}
        max_j = -1
        for ln in lines:
            #UBL:
            #  2 | +0.500  +0.400   0.000
            #  0 |[+0.170] +0.370  +0.100
            #ABL:
            # 0  =====  =====  =====
            m = re.match('\s+([\d]+)\s*\|?([ \[+\d.\]=-]+)', ln)
            if m:
                j = int(m.group(1))
                max_j = max(max_j, j)
                dc[j] = [float(z.strip('[]').replace('=====', 'nan')) for z in m.group(2).split()]
            #echo:Bed Leveling On
            else:
                m = re.match('echo:Bed Leveling (On|Off)', ln)
                if m:
                    self.leveling_enabled = m.group(1) == 'On'
        self.topology = [None] * (max_j + 1)
        for j, r in dc.items():
            self.topology[j] = r
        if self.leveling_enabled is None:
            assert False, 'Did not find bed status'
class M503Class(SyncCommand):
    def __init__(self):
        SyncCommand.__init__(self,True)
        self.hasUBL = False
    def parseResponse(self, lines):
        self.hasUBL = self.hasABL = False
        z_map = {}
        max_i = max_j = -1
        for ln in lines:
            if ln.startswith('Unified Bed Leveling'):
                self.hasUBL = True
            elif ln.startswith('echo:Auto Bed Leveling:'):
                self.hasABL = True
            else:
                #echo:  G29 W I1 J2 Z0.00000
                #print(ln)
                m = re.match('echo:  G29 W I([\d]+) J([\d]+) Z([\d.-]+)', ln)
                #print('m', m)
                if m:
                    i = int(m.group(1))
                    j = int(m.group(2))
                    z_map[i,j] = float(m.group(3))
                    max_i = max(max_i, i)
                    max_j = max(max_j, j)
        self.topology = [[None] * (max_i + 1) for j in range(max_j + 1)]
        #print('self.topology', z_map, self.topology)
        for (i, j), z in z_map.items():
            #print(i, j, z)
            self.topology[j][i] = z

class G29WClass(SyncCommand):
    def __init__(self):
        SyncCommand.__init__(self, True)
    def parseResponse(self, lines):
        for ln in lines:
            m = re.match('(GRID_MAX_POINTS_[XY])\s+([\d]+)', ln)
            if m:
                setattr(self, m.group(1), int(m.group(2)))
                continue
            #X-Axis Mesh Points at: 0.000  150.000  300.000
            m = re.match('[XY]-Axis Mesh Points at:', ln)
            if m:
                pts = ln.split(':')[1]
                pts = np.array([float(pt) for pt in pts.split()])
                if ln[0] == 'X':
                    self.x_mesh_points = pts
                else:
                    self.y_mesh_points = pts
    def send(self, *args):
        SyncCommand.send(self, 'W')
    def name(self):
        return 'G29'
class G42Class(SyncCommand):
    def __init__(self):
        SyncCommand.__init__(self, True)
    def parseResponse(self, lines):
        for ln in lines:
            m = re.match('(GRID_MAX_POINTS_[XY])\s+([\d]+)', ln)
            if m:
                setattr(self, m.group(1), int(m.group(2)))
                continue
            #X-Axis Mesh Points at: 0.000  150.000  300.000
            m = re.match('[XY]-Axis Mesh Points at:', ln)
            if m:
                pts = ln.split(':')[1]
                pts = np.array([float(pt) for pt in pts.split()])
                if ln[0] == 'X':
                    self.x_mesh_points = pts
                else:
                    self.y_mesh_points = pts
    
M114 = M114Class()
M420 = M420Class()
M503 = M503Class()
G29W = G29WClass()

if __name__ == '__main__':
    #dev testing
    print('run from cmd line')
    try:
        p = connect('/dev/ttyUSB0', 115200)
        send('G28 X Y')
        M114.send()
        print('pos', M114.x, M114.y, M114.z)
        M503.send()
        if M503.hasUBL:
            print('UBL detected')
            G29W.send()
            print('mesh pts', G29W.x_mesh_points)
        send('G0 X10')
        send('M400')
    finally:
        p.disconnect()
