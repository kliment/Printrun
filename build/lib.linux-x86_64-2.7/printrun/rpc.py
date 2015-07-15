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

from SimpleXMLRPCServer import SimpleXMLRPCServer
from threading import Thread
import socket
import logging

from .utils import install_locale, parse_temperature_report
install_locale('pronterface')

RPC_PORT = 7978

class ProntRPC(object):

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
            progress = self.percentdone
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
