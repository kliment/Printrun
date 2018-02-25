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

from xmlrpc.server import SimpleXMLRPCServer
from threading import Thread
import socket
import logging

from .utils import install_locale, parse_temperature_report
install_locale('pronterface')

RPC_PORT = 7978

class ProntRPC:

    server = None

    def __init__(self, pronsole, port = RPC_PORT):
        self.pronsole = pronsole
        used_port = port
        while True:
            try:
                self.server = SimpleXMLRPCServer(("localhost", used_port),
                                                 allow_none = True,
                                                 logRequests = False)
                if used_port != port:
                    logging.warning(_("RPC server bound on non-default port %d") % used_port)
                break
            except socket.error as e:
                if e.errno == 98:
                    used_port += 1
                    continue
                else:
                    raise
        self.server.register_function(self.get_status, 'status')
        self.server.register_function(self.set_extruder_temperature,'settemp')
        self.server.register_function(self.set_bed_temperature,'setbedtemp')
        self.server.register_function(self.load_file,'load_file')
        self.server.register_function(self.startprint,'startprint')
        self.server.register_function(self.pauseprint,'pauseprint')
        self.server.register_function(self.resumeprint,'resumeprint')
        self.server.register_function(self.sendhome,'sendhome')
        self.server.register_function(self.connect,'connect')
        self.server.register_function(self.disconnect, 'disconnect')
        self.server.register_function(self.send, 'send')
        self.thread = Thread(target = self.run_server)
        self.thread.start()

    def run_server(self):
        self.server.serve_forever()

    def shutdown(self):
        self.server.shutdown()
        self.thread.join()

    def get_status(self):
        if self.pronsole.p.printing:
            progress = 100 * float(self.pronsole.p.queueindex) / len(self.pronsole.p.mainqueue)
        elif self.pronsole.sdprinting:
            progress = self.pronsole.percentdone
        else: progress = None
        if self.pronsole.p.printing or self.pronsole.sdprinting:
            eta = self.pronsole.get_eta()
        else:
            eta = None
        if self.pronsole.tempreadings:
            temps = parse_temperature_report(self.pronsole.tempreadings)
        else:
            temps = None
        z = self.pronsole.curlayer
        return {"filename": self.pronsole.filename,
                "progress": progress,
                "eta": eta,
                "temps": temps,
                "z": z,
                }
    def set_extruder_temperature(self, targettemp):
        if self.pronsole.p.online:
           self.pronsole.p.send_now("M104 S" + targettemp)

    def set_bed_temperature(self,targettemp):
        if self.pronsole.p.online:
           self.pronsole.p.send_now("M140 S" + targettemp)

    def load_file(self,filename):
        self.pronsole.do_load(filename)

    def startprint(self):
        self.pronsole.do_print("")

    def pauseprint(self):
        self.pronsole.do_pause("")

    def resumeprint(self):
        self.pronsole.do_resume("")
    def sendhome(self):
        self.pronsole.do_home("")
    def connect(self):
        self.pronsole.do_connect("")
    def disconnect(self):
        self.pronsole.do_disconnect("")
    def send(self, command):
        self.pronsole.p.send_now(command)
