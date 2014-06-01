from SimpleXMLRPCServer import SimpleXMLRPCServer
from threading import Thread

from .utils import parse_temperature_report

RPC_PORT = 7978

class ProntRPC(object):

    server = None

    def __init__(self, pronsole, port = RPC_PORT):
        self.pronsole = pronsole
        self.server = SimpleXMLRPCServer(("localhost", port),
                                         allow_none = True,
                                         logRequests = False)
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
            eta = self.get_eta()
        else:
            eta = None
        if self.pronsole.tempreadings:
            temps = parse_temperature_report(self.pronsole.tempreadings)
        else:
            temps = None
        return {"filename": self.pronsole.filename,
                "progress": progress,
                "eta": eta,
                "temps": temps,
                }
