#!/usr/bin/env python
import glob, os, time, datetime, sys, codecs, random, textwrap, re, traceback
import logging, argparse, tornado.ioloop, printcore, pronsole

# Allow construct protocol developers to use a specific lib for dev purposes
c_path = os.getenv('PY_CONSTRUCT_PATH')
if c_path != None:
  print "$PY_CONSTRUCT_PATH detected, loading server lib from: \n%s"%c_path
  sys.path.insert(1, c_path)

from construct_server.construct_server import ConstructServer
from construct_server.event_emitter import EventEmitter
from pprint import pprint
from printrun import gcoder

sys.stdout = codecs.getwriter('utf8')(sys.stdout)
log = logging.getLogger("root")


# Args
# -------------------------------------------------

if __name__ == "__main__":

  parser = argparse.ArgumentParser(
    description='Runs a 3D printer server using the Construct Protocol'
  )

  parser.add_argument('--dry-run', default=False, action='store_true',
    help='Does not connect to the 3D printer'
  )

  parser.add_argument('--loud', default=False, action='store_true',
    help='Enables verbose printer output'
  )

  parser.add_argument('--heaptrace', default=False, action='store_true',
    help='Enables a heap trace on exit (for developer use)'
  )

  args = parser.parse_args()
  if args.heaptrace: from guppy import hpy


# Routes
# -------------------------------------------------

class RootHandler(tornado.web.RequestHandler):
  def get(self):
    self.render("index.html")

class InspectHandler(tornado.web.RequestHandler):
  def prepare(self):
    construct_auth(self, None)

  def get(self):
    self.render("inspect.html")


# Faster GCoder implementation without any parsing
# -------------------------------------------------

class Line(object):

    __slots__ = ('raw', 'command', 'is_move')

    def __init__(self, l):
        self.raw = l

    def __getattr__(self, name):
        return None

class FastGCode(object):
  def __init__(self,data):
    self.lines = [Line(l2) for l2 in
                    (l.strip() for l in data)
                  if l2]
    self.all_layers = [self.lines]

  def __len__(self):
    return len(self.lines)

  def __iter__(self):
    return self.lines.__iter__()

  def idxs(self, index):
    return (0, index)


# Prontserve: Server-specific functionality
# -------------------------------------------------

class Prontserve(pronsole.pronsole, EventEmitter):

  def __init__(self, **kwargs):
    self.initializing = True
    self.max_w_val = 0
    pronsole.pronsole.__init__(self)
    EventEmitter.__init__(self)
    self.settings.sensor_names = {'T': 'extruder', 'B': 'bed'}
    self.settings.sensor_poll_rate = 1 # seconds
    self.p.loud = kwargs['loud']
    self.dry_run = kwargs['dry_run'] == True
    self.stdout = sys.stdout
    self.load_default_rc()
    self.p.sendcb = self.sendcb
    self.initializing = False

    dir = os.path.dirname(__file__)
    self.server = ConstructServer(
      printer= self,
      settings= self.settings,
      components= dict(
        temps= ["e0", "b"],
        fans= ["f0"],
        conveyors= ["c0"],
        axes= ["x", "y", "z"]
      ),
      server_settings= dict(
        template_path= os.path.join(dir, "printrun", "server", "templates"),
        static_path= os.path.join(dir, "printrun", "server", "static"),
        debug= True
      ),
      routes= [
        (r"/", RootHandler),
        (r"/inspect", InspectHandler)
      ]
    )

  def display_startup_padding(self):
    if self.dry_run:
      for i in range(0,7):
        sys.stdout.write("\x1B[0;33m  Dry Run  \x1B[0m")
    print ""

  def display_startup_message(self):
    welcome = textwrap.dedent(u"""
      +---+  \x1B[0;32mProntserve: Your printer just got a whole lot better.
      \x1B[0m| \u2713 |  Ready to print.
      +---+  More details at http://localhost:8888/""")
    print "\n"+"-"*80
    self.display_startup_padding()
    sys.stdout.write(welcome)
    print "\n"
    self.display_startup_padding()
    print "-"*80 + "\n"

  def start(self):
    try:
      # Connect to the printer
      if self.dry_run == False:
        self.do_connect("")
        if self.p.printer == None: sys.exit(1)
        print "Connecting to printer..."
        for x in range(0,50-1):
          if self.p.online == True: break
          sys.stdout.write(".")
          sys.stdout.flush()
          time.sleep(0.1)
        print ""
        if self.p.online == False:
          print "Unable to connect to printer: Connection timed-out."
          sys.exit(1)
        # Wait for the printer to finish connecting and then reset it
        time.sleep(2)
        self.reset()
      # Start the server, display the startup message and start the ioloop
      self.server.start()
      self.display_startup_message()
      self.server.ioloop.start()
    except Exception as ex:
      print traceback.format_exc()
      if args.heaptrace: print hpy().heap()
      self.p.disconnect()
      exit()

  def is_online(self):
    return self.p.online == True

  def is_printing(self):
    return self.p.printing == False and self.p.online

  def post_process_print_job(self, filename, filebody):
    return FastGCode(filebody.split("\n"))

  def print_progress(self):
    if(self.p.printing):
      return 100*float(self.p.queueindex)/len(self.p.mainqueue)
    if(self.sdprinting):
      return self.percentdone
    return 0

  def start_print_job(self, job):
    self.p.startprint(job['body'])
    self.p.paused = False

  def do_home(self, *args, **kwargs):
    pronsole.pronsole.do_home(self, " ".join(args))

  def do_move(self, **kwargs):
    # Convert mm/s to mm/minute
    if "at" in kwargs:
      speed_multiplier = float(kwargs['at'].replace("%",""))*0.01
    else:
      speed_multiplier = 1

    for k, v in kwargs.iteritems():
      if k == "at": continue

      # Getting the feedrate
      if k in ["z", "e"]:
        prefix = k
      else:
        prefix = "xy"
      speed = getattr(self.settings, "%s_feedrate"%prefix) * speed_multiplier

      # Creating the pronsole axial move command
      args = {"axis" : k, "dist" : v, "speed" : speed }
      cmd = "%(axis)s %(dist)s %(speed)s" % args
      print "move %s"%cmd
      pronsole.pronsole.do_move(self, cmd )

  def do_stop_move(self):
    raise Exception("Continuous movement not supported")

  def do_estop(self):
    self.reset()
    print "Emergency Stop!"

  # Not thread safe; must be run from the ioloop thread.
  def reset(self):
    self.async(self.server.set_waiting_to_reach_temp, None)
    # pause the print job if any is printing
    if self.p.printing:
      pronsole.pronsole.do_pause(self, "")
    # Prevent the sensor from polling for 2 seconds while the firmware 
    # restarts
    self.server.set_reset_timeout(time.time() + 2)
    self.server.set_sensor_update_received(True)
    # restart the firmware
    pronsole.pronsole.do_reset(self, "")

    self.p.printing = False

  def on_target_temp_changed(self, target=None, value=None):
    gcode = "M104"
    if target == "b": gcode = "M140"
    if not target in ["b", "e0"]: gcode += " p%i"%(int(target[1:]))
    gcode += " S%f"%float(value)
    self.p.send_now(gcode)

  def on_fan_enabled_changed(self, target=None, value=None):
    update_fan()

  def on_fan_speed_changed(self, target=None, value=None):
    update_fan()

  def update_fan(self):
    if self.fan_enabled == False:
      speed = 0
    else:
      speed = int(self.server.c_get("f0", "fan_speed"))
    print "M106 S%i"%speed
    self.p.send_now("M106 S%i"%speed)

  def on_motors_enabled_changed(self, target=None, value=None):
    self.p.send_now({True: "M17", False: "M18"}[value])

  def request_sensor_update(self):
    if self.dry_run:
      return self._receive_sensor_update(
        "ok T:%i B:%i"%(random.randint(30, 60), random.randint(30, 60))
      )
    if self.p.online: self.p.send_now("M105")

  def recvcb(self, l):
    """ Parses a line of output from the printer via printcore """
    l = l.rstrip()
    #print l
    if self.server.waiting_to_reach_temp and ("ok" in l):
      self.async(self.server.set_waiting_to_reach_temp, None)
    if ("T:" in l):
      self.async(self._receive_sensor_update, l)
    if l!="ok" and not l.startswith("ok T") and not l.startswith("T:"):
      self.async(self._receive_printer_error, l)

  def sendcb(self, l):
    # Monitor the sent commands for new extruder target temperatures
    if ("M109" in l) or ("M104" in l) or ("M140" in l) or ("M190" in l):
      temp = float(re.search('S([0-9]+)', l).group(1))
      if ("M109" in l) or ("M104" in l):
        target = "e0"
        if " P" in l: target = "e%i"%(int(re.search(' P([0-9]+)', l).group(1)))
      else:
        target = "b"
      self.async(self.server.c_set, target, "target_temp", temp, internal=True)
    if ("M109" in l) or ("M190" in l) or ("M116" in l):
      if ("M116" in l): target = "e0"
      self.async(self.server.set_waiting_to_reach_temp, [target])

  # Adds a callback to the ioloop to run a method later on in the server thread
  def async(self, *args, **kwargs):
    self.server.ioloop.add_callback(*args, **kwargs)

  def _receive_sensor_update(self, l):
    try:
      self.async(self.server.set_sensor_update_received, True)
      words = filter(lambda s: s.find(":") > 0, l.lower().split(" "))
      d = dict([ s.split(":") for s in words])

      for key, value in d.iteritems():
        if key == "t": key = "e0"
        if not key in self.server.components: continue
        self.server.c_set(key, "current_temp", float(value), internal=True)

      # Fire a event if the extruder is giving us a countdown till it's online
      # see: TEMP_RESIDENCY_TIME (via the googles)
      # see: https://github.com/ErikZalm/Marlin/blob/Marlin_v1/Marlin/Marlin_main.cpp#L1191
      if ("w" in d):
        percent = 0
        if not d["w"] == "?":
          w_val = float(d["w"])
          if w_val > self.max_w_val: self.max_w_val = w_val
          percent = (100 - w_val*100/self.max_w_val)
          progress = {'eta': w_val, 'percent': percent}
        else:
          progress = {'percent': percent}
        for target in (self.server.waiting_to_reach_temp):
          self.server.c_set(
            target, "target_temp_progress", progress, internal=True
          )
    except Exception as ex:
      print traceback.format_exc()

  def log(self, *msg):
    msg = ''.join(str(i) for i in msg)
    msg.replace("\r", "")
    print msg
    self.server.broadcast([
      dict(type= "log", data= dict(msg= msg, level= "debug"))
    ])

  def logError(self, *msg):
    print u"".join(unicode(i) for i in msg)
    if self.initializing == False:
      raise Exception(u"".join(unicode(i) for i in msg))

  def write_prompt(self):
    None

  def confirm(self):
    True


# Server Start Up
# -------------------------------------------------

if __name__ == "__main__":
  prontserve = Prontserve(dry_run=args.dry_run, loud=args.loud).start()
