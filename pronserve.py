#!/usr/bin/env python

import tornado.ioloop
import tornado.web
import tornado.websocket
from tornado import gen
import tornado.httpserver
import time
import base64
import logging
import logging.config
import cmd, sys
import glob, os, time, datetime
import sys, subprocess
import math, codecs
from math import sqrt
from gcoder import GCode
import printcore
from pprint import pprint
import pronsole
from server import basic_auth
import random
import textwrap
import SocketServer
import socket
import mdns
import uuid
from operator import itemgetter, attrgetter
from collections import deque

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
    pronserve.do_print()
    self.finish("ACK")

class PauseHandler(tornado.web.RequestHandler):
  def put(self):
    pronserve.do_pause()
    self.finish("ACK")

class StopHandler(tornado.web.RequestHandler):
  def put(self):
    pronserve.do_stop()
    self.finish("ACK")

class JobsHandler(tornado.web.RequestHandler):
  def post(self):
    fileinfo = self.request.files['job'][0]
    pronserve.jobs.add(fileinfo['filename'], fileinfo['body'])
    self.finish("ACK")

class JobHandler(tornado.web.RequestHandler):
  def delete(self, job_id):
    pronserve.jobs.remove(int(job_id))
    self.finish("ACK")

  def put(self, job_id):
    args = {'position': int(self.get_argument("job[position]"))}
    pronserve.jobs.update(int(job_id), args)
    self.finish("ACK")


class InspectHandler(tornado.web.RequestHandler):
  def prepare(self):
    auth(self, None)

  def get(self):
    self.render("inspect.html")

#class EchoWebSocketHandler(tornado.web.RequestHandler):
class ConstructSocketHandler(tornado.websocket.WebSocketHandler):

  def on_sensor_changed(self):
    for name in ['bed', 'extruder']:
      self.send(
        sensor_changed= {'name': name, 'value': pronserve.sensors[name]},
      )

  def on_uncaught_event(self, event_name, data):
    listener = "on_%s"%event_name

    if event_name[:4] == 'job_' and event_name != "job_progress_changed":
      data = pronserve.jobs.sanitize(data)
    self.send({event_name: data})

  def _execute(self, transforms, *args, **kwargs):
    if socket_auth(self):
      super(ConstructSocketHandler, self)._execute(transforms, *args, **kwargs)
    else:
      self.stream.close();

  def open(self):
    pronserve.listeners.add(self)
    self.write_message({'connected': {'jobs': pronserve.jobs.public_list()}})
    print "WebSocket opened. %i sockets currently open." % len(pronserve.listeners)

  def send(self, dict_args = {}, **kwargs):
    args = dict(dict_args.items() + kwargs.items())
    args['timestamp']= time.time()
    self.write_message(args)

  def on_message(self, msg):
    print "message received: %s"%(msg)
    # TODO: the read bit of repl!
    # self.write_message("You said: " + msg)

  def on_close(self):
    pronserve.listeners.remove(self)
    print "WebSocket closed. %i sockets currently open." % len(pronserve.listeners)

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


# Pronserve: Server-specific functionality
# -------------------------------------------------

class Pronserve(pronsole.pronsole, EventEmitter):

  def __init__(self):
    pronsole.pronsole.__init__(self)
    EventEmitter.__init__(self)
    self.settings.sensor_names = {'T': 'extruder', 'B': 'bed'}
    self.stdout = sys.stdout
    self.ioloop = tornado.ioloop.IOLoop.instance()
    self.settings.sensor_poll_rate = 1 # seconds
    self.sensors = {'extruder': -1, 'bed': -1}
    self.load_default_rc()
    self.jobs = PrintJobQueue()
    self.job_id_incr = 0
    self.printing_jobs = False
    self.current_job = None
    self.previous_job_progress = 0
    self.silent = True
    services = ({'type': '_construct._tcp', 'port': 8888, 'domain': "local."})
    self.mdns = mdns.publisher().save_group({'name': 'pronserve', 'services': services })
    self.jobs.listeners.add(self)

  def do_print(self):
    if self.p.online:
      self.printing_jobs = True

  def run_print_queue_loop(self):
    # This is a polling work around to the current lack of events in printcore
    # A better solution would be one in which a print_finised event could be 
    # listend for asynchronously without polling.
    p = self.p
    if self.printing_jobs and p.printing == False and p.paused == False and p.online:
      if self.current_job != None:
        self.update_job_progress(100)
        self.fire("job_finished", self.jobs.sanitize(self.current_job))
      if len(self.jobs.list) > 0:
        print "Starting the next print job"
        self.current_job = self.jobs.list.popleft()
        self.p.startprint(self.current_job['body'].split("\n"))
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

  def run_sensor_loop(self):
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

  def print_progress(self):
    if(self.p.printing):
      return 100*float(self.p.queueindex)/len(self.p.mainqueue)
    if(self.sdprinting):
      return self.percentdone
    return 0


  def _receive_sensor_update(self, l):
    words = filter(lambda s: s.find(":") > 0, l.split(" "))
    d = dict([ s.split(":") for s in words])

    # print "sensor update received!"

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

  def write_prompt(self):
    None


class PrintJobQueue(EventEmitter):

  def __init__(self):
    super(PrintJobQueue, self).__init__()
    self.list = deque([])
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
      original_file_name = job["original_file_name"],
      rank = job["rank"]
    )

  def order(self):
    sorted(self.list, key=lambda job: job['rank'])


  def add(self, original_file_name, body):
    ext = os.path.splitext(original_file_name)[1]
    job = dict(
      id = self.__last_id,
      rank = len(self.list),
      original_file_name=original_file_name,
      body= body,
    )
    self.__last_id += 1

    self.list.append(job)
    print "Added %s"%(original_file_name)
    self.fire("job_added", job)

  def display_summary(self):
    print "Print Jobs:"
    for job in self.list:
      print "  %i: %s"%(job['id'], job['original_file_name'])
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
      return False
    job['rank'] = job_attrs['position']
    self.order()
    print "Print Job Updated"
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

print "Pronserve is starting..."
pronserve = Pronserve()
pronserve.do_connect("")

time.sleep(1)
pronserve.run_sensor_loop()
pronserve.run_print_queue_loop()

if __name__ == "__main__":
    application.listen(8888)
    print "\n"+"-"*80
    welcome = textwrap.dedent(u"""
              +---+  \x1B[0;32mPronserve: Your printer just got a whole lot better.\x1B[0m
              | \u2713 |  Ready to print.
              +---+  More details at http://localhost:8888/""")
    sys.stdout.write(welcome)
    print "\n\n" + "-"*80 + "\n"

    try:
      pronserve.ioloop.start()
    except:
      pronserve.p.disconnect()
