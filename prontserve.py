#!/usr/bin/env python

import tornado.ioloop
import tornado.web
import tornado.websocket
from tornado.web import asynchronous
from tornado import gen
import tornado.httpserver
import uuid
import time
import base64
import logging
import logging.config
import cmd, sys
import glob, os, time, datetime
import sys, subprocess
import math, codecs
from math import sqrt
from pprint import pprint
import printcore
from printrun import gcoder
import pronsole
from server import basic_auth
import random
import json
import textwrap
import SocketServer
import socket
import pybonjour
import atexit
import uuid
import re
import traceback
import argparse
from operator import itemgetter, attrgetter
import codecs
sys.stdout = codecs.getwriter('utf8')(sys.stdout)

log = logging.getLogger("root")
__UPLOADS__ = "./uploads"

# Authentication
# -------------------------------------------------

def authenticator(realm,handle,password):
    """ 
    This method is a sample authenticator. 
    It treats authentication as successful
    if the handle and passwords are the same.
    It returns a tuple of handle and user name 
    """
    if handle == "admin" and password == "admin" :
        return (handle,'Authorized User')
    return None

def user_extractor(user_data):
    """
    This method extracts the user handle from
    the data structure returned by the authenticator
    """
    return user_data[0]

def socket_auth(self):
  user = self.get_argument("user", None)
  password = self.get_argument("password", None)
  return authenticator(None, user, password)

interceptor = basic_auth.interceptor
auth = basic_auth.authenticate('auth_realm', authenticator, user_extractor)
#@interceptor(auth)


# Routing
# -------------------------------------------------

class RootHandler(tornado.web.RequestHandler):
  def get(self):
    self.render("index.html")

class PrintHandler(tornado.web.RequestHandler):
  def put(self):
    prontserve.do_print()
    self.finish("ACK")

class PauseHandler(tornado.web.RequestHandler):
  def put(self):
    prontserve.do_pause()
    self.finish("ACK")

class StopHandler(tornado.web.RequestHandler):
  def put(self):
    prontserve.do_stop()
    self.finish("ACK")

@tornado.web.stream_body
class JobsHandler(tornado.web.RequestHandler):

  def post(self):
    self.read_bytes = 0
    self.total_bytes = self.request.content_length
    self.body = ''
    print self.request
    session_uuid = self.get_argument("session_uuid", None)
    print "me"
    print session_uuid
    print "them"
    self.websocket = None
    for c in ConstructSocketHandler.clients:
      print c.session_uuid
      if c.session_uuid == session_uuid: self.websocket = c
    self.request.request_continue()
    self.read_chunks()

  def read_chunks(self, chunk=''):
    self.read_bytes += len(chunk)
    self.body += chunk
    if chunk: self.process_chunk()

    chunk_length = min(100000, self.request.content_length - self.read_bytes)
    if chunk_length > 0:
      self.request.connection.stream.read_bytes(
              chunk_length, self.read_chunks)
    else:
      self.request._on_request_body(self.body, self.uploaded)

  def process_chunk(self):
    print self.get_argument("session_uuid", None)
    print "bytes: (%i / %i)"%(self.read_bytes, self.total_bytes)
    msg = {'uploaded': self.read_bytes, 'total': self.total_bytes}
    if self.websocket != None:
      self.websocket.send(job_upload_progress_changed = msg)

  def uploaded(self):
    fileinfo = self.request.files['job'][0]
    prontserve.do_add_job(fileinfo['filename'], fileinfo['body'])

    self.finish("ACK")


class JobHandler(tornado.web.RequestHandler):
  def delete(self, job_id):
    prontserve.do_rm_job(job_id)
    self.finish("ACK")

  def put(self, job_id):
    args = {'position': int(self.get_argument("job[position]"))}
    prontserve.do_change_job(job_id, **args)
    self.finish("ACK")


class InspectHandler(tornado.web.RequestHandler):
  def prepare(self):
    auth(self, None)

  def get(self):
    self.render("inspect.html")

#class EchoWebSocketHandler(tornado.web.RequestHandler):
class ConstructSocketHandler(tornado.websocket.WebSocketHandler):
  clients = []

  def on_sensor_changed(self):
    for name in ['bed', 'extruder']:
      self.send(
        sensor_changed= {'name': name, 'value': prontserve.sensors[name]},
      )

  def on_uncaught_event(self, event_name, data):
    listener = "on_%s"%event_name

    if event_name[:4] == 'job_' and event_name != "job_progress_changed":
      data = prontserve.jobs.sanitize(data)
    self.send({event_name: data})

  def _execute(self, transforms, *args, **kwargs):
    if socket_auth(self):
      super(ConstructSocketHandler, self)._execute(transforms, *args, **kwargs)
    else:
      self.stream.close();

  def select_subprotocol(self, subprotocols):
    print subprotocols
    return "construct.text.0.0.1"

  def open(self):
    self.session_uuid = str(uuid.uuid4())
    self.clients.append(self)
    prontserve.listeners.add(self)
    self.write_message({'headers': {
      'jobs': prontserve.jobs.public_list(),
      'continous_movement': False
    }})
    # Send events to initialize the machine's state
    self.on_sensor_changed()
    for k, v in prontserve.target_values.iteritems():
      self.on_uncaught_event("target_temp_changed", {k: v})
    self.on_uncaught_event("job_progress_changed", prontserve.previous_job_progress)
    self.send(initialized= {'session_uuid': self.session_uuid} )
    print "WebSocket opened. %i sockets currently open." % len(prontserve.listeners)

  def send(self, dict_args = {}, **kwargs):
    args = dict(dict_args.items() + kwargs.items())
    args['timestamp']= time.time()
    self.write_message(args)

  def on_message(self, msg):
    cmds = self._cmds()

    print "message received: %s"%(msg)
    msg = re.sub(r'\s+', "\s" ,msg).strip()
    msg = msg.replace(":\s", ":")
    msg = msg.replace("@\s", "@")
    msg = msg.replace("@", "at:")
    words = msg.split("\s")

    cmd = words[0]
    arg_words = words[1:]
    args = []
    kwargs = {}

    for w in arg_words:
      if len(w) == 0: continue
      if w.find(":") > -1:
        k, v = w.split(":")
        kwargs[k] = v
      else:
        args.append(w)

    if cmd in cmds.keys():
      try:
        self._throwArgErrors(cmd, args, kwargs)
        # Set is already used by pronsole so we use construct_set
        if cmd == "set": cmd = "construct_set"
        # Run the command
        response = getattr(prontserve, "do_%s"%cmd)(*args, **kwargs)
        self.write_message({"ack": response})
      except Exception as ex:
        print traceback.format_exc()
        self.write_message({"error": str(ex)})
    else:
      self.write_message({"error": "%s command does not exist."%cmd})

  def _cmds(self):
    return {
      "home": {
        'array_args': True,
        'args_error': "Home only (optionally) accepts axe names."
      },
      "move": {
        'named_args': True,
        'args_error': textwrap.dedent("""
          Move only takes a list of axes, distance pairs and optionally @ 
          prefixed feedrates.
        """).strip()
      },
      "set": {
        'namespaced': True, # namespaced by the machine aspect (temp)
        'named_args': True,
        'args_error': textwrap.dedent("""
          Set only accepts a namespace and a list of heater, value pairs.
        """).strip()
      },
      "estop": {
        'args_error': "Estop does not accept any parameters."
      },
      "print": {
        'args_error': "Print does not accept any parameters."
      },
      "rm_job": {
        'namespaced': True, # namespaced by the job id
        'args_error': "Rm_job only accepts a job_id."
      },
      "change_job": {
        'namespaced': True, # namespaced by the job id
        'named_args': True,
        'args_error': textwrap.dedent("""
          Change_job only accepts a job_id and a list of key/value pairs.
        """).strip()
      },
      "get_jobs": {
        'args_error': "Get_jobs does not accept any parameters."
      }
    }

  def _throwArgErrors(self, cmd, args, kwargs):
    meta = self._cmds()[cmd]

    arg_errors = (len(kwargs) > 0 and not 'named_args' in meta)
    arg_errors = arg_errors or (len(args) == 0 and 'namespaced' in meta)
    minArgs = 0
    if 'namespaced' in meta: minArgs = 1
    arg_errors = arg_errors or (len(args) > minArgs and not 'array_args' in meta)
    if arg_errors: raise Exception(meta['args_error'])

  def on_close(self):
    self.clients.remove(self)
    prontserve.listeners.remove(self)
    print "WebSocket closed. %i sockets currently open." % len(prontserve.listeners)

dir = os.path.dirname(__file__)
settings = dict(
  template_path=os.path.join(dir, "server", "templates"),
  static_path=os.path.join(dir, "server", "static"),
  debug=True
)

application = tornado.web.Application([
  (r"/", RootHandler),
  (r"/inspect", InspectHandler),
  (r"/socket", ConstructSocketHandler),
  (r"/jobs", JobsHandler),
  (r"/jobs/([0-9]*)", JobHandler),
  (r"/jobs/print", PrintHandler),
  (r"/jobs/pause", PauseHandler),
  (r"/stop", StopHandler)
], **settings)


# Event Emitter
# -------------------------------------------------

class EventEmitter(object):
  def __init__(self):
    self.listeners = set()

  def fire(self, event_name, content=None):
    callback_name = "on_%s" % event_name
    for listener in self.listeners:
      if hasattr(listener, callback_name):
        callback = getattr(listener, callback_name)
        if content == None: callback()
        else:               callback(content)
      elif hasattr(listener, "on_uncaught_event"):
        listener.on_uncaught_event(event_name, content)
      else:
        continue


# Prontserve: Server-specific functionality
# -------------------------------------------------

class Prontserve(pronsole.pronsole, EventEmitter):

  def __init__(self, **kwargs):
    self.initializing = True
    pronsole.pronsole.__init__(self)
    EventEmitter.__init__(self)
    self.settings.sensor_names = {'T': 'extruder', 'B': 'bed'}
    self.settings.pause_between_prints = True
    self.dry_run = kwargs['dry_run'] == True
    self.stdout = sys.stdout
    self.ioloop = tornado.ioloop.IOLoop.instance()
    self.settings.sensor_poll_rate = 1 # seconds
    self.sensors = {'extruder': -1, 'bed': -1}
    self.target_values = {'e': 0, 'b': 0}
    self.load_default_rc()
    self.jobs = PrintJobQueue()
    self.job_id_incr = 0
    self.printing_jobs = False
    self.current_job = None
    self.previous_job_progress = 0
    self.silent = True
    self._sensor_update_received = True
    self.init_mdns()
    self.jobs.listeners.add(self)
    self.initializing = False

  def init_mdns(self):
    sdRef = pybonjour.DNSServiceRegister(name = None,
                                         regtype = '_construct._tcp',
                                         port = 8888,
                                         domain = "local.")
    atexit.register(self.cleanup_service, sdRef)

  def cleanup_service(self, sdRef):
    sdRef.close()

  def do_print(self):
    if not self.p.online: raise Exception("not online")
    self.printing_jobs = True

  def do_home(self, *args, **kwargs):
    pronsole.pronsole.do_home(self, " ".join(args))
    print "wut homing!"

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
    pronsole.pronsole.do_pause(self, "")
    # self.p.reset()
    print "Emergency Stop!"
    self.fire("estop")

  def do_construct_set(self, subCmd, **kwargs):
    method = "do_set_%s"%subCmd
    if not hasattr(self, method):
      raise Exception("%s is not a real namespace"%subCmd)
    getattr(self, method)(**kwargs)

  def do_set_temp(self, **kwargs):
    # Setting each temperature individually
    prefixes = {'b': 'bed', 'e0': 'set', 'e': 'set'}
    for k, prefix in prefixes.iteritems():
      if not k in kwargs: continue
      print "%stemp %s"%(prefix, kwargs[k])
      setter = getattr(pronsole.pronsole, "do_%stemp"%prefix)
      setter(self, kwargs[k])
      pprint({prefix: kwargs[k]})
      self.target_values[k] = kwargs[k]
      self.fire("target_temp_changed", {k: kwargs[k]})

  def do_set_feedrate(self, **kwargs):
    # TODO: kwargs[xy] * 60 and kwargs[z] * 60
    pass

  def do_add_job(self, filename, filebody):
    self.jobs.add(filename, filebody)

  def do_rm_job(self, job_id):
    self.jobs.remove(int(job_id))

  def do_change_job(self, job_id, **kwargs):
    print job_id
    print kwargs
    try:
      job_id = int(job_id)
    except:
      raise Exception("job_id must be a number")

    self.jobs.update(job_id, kwargs)

  def do_get_jobs(self):
    jobexport = []
    if self.current_job != None:
      jobexport.append(
        dict(
          id = self.current_job["id"],
          file_name = self.current_job["file_name"],
          printing = True
        )
      )
    jobexport.extend(self.jobs.public_list())
    return {'jobs': jobexport}

  def run_print_queue_loop(self):
    # This is a polling work around to the current lack of events in printcore
    # A better solution would be one in which a print_finised event could be 
    # listend for asynchronously without polling.
    p = self.p
    if self.printing_jobs and p.printing == False and p.paused == False and p.online:
      if self.current_job != None:
        self.update_job_progress(100)
        self.fire("job_finished", self.jobs.sanitize(self.current_job))

      if self.settings.pause_between_prints and self.current_job != None:
        print "Print job complete. Pausing between jobs."
        self.current_job = None
        self.printing_jobs = False
      elif len(self.jobs.list) > 0:
        print "Starting the next print job"
        self.current_job = self.jobs.list.pop(0)
        gc = gcoder.GCode(self.current_job['body'].split("\n"))
        self.p.startprint(gc)
        self.fire("job_started", self.jobs.sanitize(self.current_job))
      else:
        print "Finished all print jobs"
        self.current_job = None
        self.printing_jobs = False

    # Updating the job progress
    self.update_job_progress(self.print_progress())

    #print "print loop"
    next_timeout = time.time() + 0.3
    gen.Task(self.ioloop.add_timeout(next_timeout, self.run_print_queue_loop))

  def update_job_progress(self, progress):
    if progress != self.previous_job_progress and self.current_job != None:
      self.previous_job_progress = progress
      self.fire("job_progress_changed", progress)

  def print_progress(self):
    if(self.p.printing):
      return 100*float(self.p.queueindex)/len(self.p.mainqueue)
    if(self.sdprinting):
      return self.percentdone
    return 0

  def run_sensor_loop(self):
    if self._sensor_update_received:
      self._sensor_update_received = False
      if self.dry_run:
        self._receive_sensor_update("ok T:%i"%random.randint(20, 50))
      else:
        self.request_sensor_update()
    next_timeout = time.time() + self.settings.sensor_poll_rate
    gen.Task(self.ioloop.add_timeout(next_timeout, self.run_sensor_loop))

  def request_sensor_update(self):
    if self.p.online: self.p.send_now("M105")

  def recvcb(self, l):
    """ Parses a line of output from the printer via printcore """
    l = l.rstrip()
    #print l
    if "T:" in l:
      self._receive_sensor_update(l)
    if l!="ok" and not l.startswith("ok T") and not l.startswith("T:"):
      self._receive_printer_error(l)

  def _receive_sensor_update(self, l):
    self._sensor_update_received = True
    words = filter(lambda s: s.find(":") > 0, l.split(" "))
    d = dict([ s.split(":") for s in words])

    for key, value in d.iteritems():
      self.__update_sensor(key, value)

    self.fire("sensor_changed")

  def __update_sensor(self, key, value):
    if (key in self.settings.sensor_names) == False:
      return
    sensor_name = self.settings.sensor_names[key]
    self.sensors[sensor_name] = float(value)

  def on_uncaught_event(self, event_name, content=None):
    self.fire(event_name, content)

  def log(self, *msg):
    msg = ''.join(str(i) for i in msg)
    msg.replace("\r", "")
    print msg
    self.fire("log", {'msg': msg, 'level': "debug"})

  def logError(self, *msg):
    print u"".join(unicode(i) for i in msg)
    if self.initializing == False:
      raise Exception(u"".join(unicode(i) for i in msg))

  def write_prompt(self):
    None

  def confirm(self):
    True


class PrintJobQueue(EventEmitter):

  def __init__(self):
    super(PrintJobQueue, self).__init__()
    self.list = []
    self.__last_id = 0

  def public_list(self):
    # A sanitized version of list for public consumption via construct
    l2 = []
    for job in self.list:
      l2.append(self.sanitize(job))
    return l2

  def sanitize(self, job):
    return dict(
      id = job["id"],
      file_name = job["file_name"],
      printing = False,
    )

  def add(self, file_name, body):
    ext = os.path.splitext(file_name)[1]
    job = dict(
      id = self.__last_id,
      file_name=file_name,
      body= body,
    )
    self.__last_id += 1

    self.list.append(job)
    print "Added %s"%(file_name)
    self.fire("job_added", job)

  def display_summary(self):
    print "Print Jobs:"
    for job in self.list:
      print "  %i: %s"%(job['id'], job['file_name'])
    print ""
    return True

  def remove(self, job_id):
    job = self.find_by_id(job_id)
    if job == None:
      return False
    self.list.remove(job)
    print "Print Job Removed"
    self.fire("job_removed", job)

  def update(self, job_id, job_attrs):
    job = self.find_by_id(job_id)
    if job == None:
      raise Exception("There is no job #%i."%job_id)
    # proposed future print quantity functionality
    # if hasattr(job_attrs, 'qty'): job['qty'] = qty
    if job_attrs['position']:
      position = int(job_attrs['position'])
      self.list.remove(job)
      self.list.insert(position, job)
    print int(job_attrs['position'])
    print "Print #%s Job Updated ( %s )."%(job['id'], job['file_name'])
    self.fire("job_updated", job)

  def find_by_id(self, job_id):
    for job in self.list:
      if job['id'] == job_id: return job
    return None

  def fire(self, event_name, content):
    self.display_summary()
    super(PrintJobQueue, self).fire(event_name, content)



# Server Start Up
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

  args = parser.parse_args()
  dry_run = args.dry_run

  def warn_if_dry_run():
    if dry_run:
      for i in range(0,7):
        sys.stdout.write("\x1B[0;33m  Dry Run  \x1B[0m")
    print ""

  prontserve = Prontserve(dry_run=dry_run)
  prontserve.p.loud = args.loud

  try:
    if dry_run==False:
      prontserve.do_connect("")
      if prontserve.p.printer == None: sys.exit(1)
      print "Connecting to printer..."
      for x in range(0,50-1):
        if prontserve.p.online == True: break
        sys.stdout.write(".")
        sys.stdout.flush()
        time.sleep(0.1)
      print ""
      if prontserve.p.online == False:
        print "Unable to connect to printer: Connection timed-out."
        sys.exit(1)

    time.sleep(1)
    prontserve.run_sensor_loop()
    prontserve.run_print_queue_loop()

    application.listen(8888)
    print "\n"+"-"*80
    welcome = textwrap.dedent(u"""
              +---+  \x1B[0;32mProntserve: Your printer just got a whole lot better.\x1B[0m
              | \u2713 |  Ready to print.
              +---+  More details at http://localhost:8888/""")
    warn_if_dry_run()
    sys.stdout.write(welcome)
    print "\n"
    warn_if_dry_run()
    print "-"*80 + "\n"

    prontserve.ioloop.start()
  except:
    prontserve.p.disconnect()
