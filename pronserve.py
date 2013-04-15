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

log = logging.getLogger("root")

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

class InspectHandler(tornado.web.RequestHandler):
  def prepare(self):
    auth(self, None)

  def get(self):
    self.render("inspect.html")

#class EchoWebSocketHandler(tornado.web.RequestHandler):
class ConstructSocketHandler(tornado.websocket.WebSocketHandler):

  def _execute(self, transforms, *args, **kwargs):
    if socket_auth(self):
      super(ConstructSocketHandler, self)._execute(transforms, *args, **kwargs)
    else:
      self.stream.close();

  def open(self):
    pronserve.clients.add(self)
    print "WebSocket opened. %i sockets currently open." % len(pronserve.clients)

  def on_sensor_change(self):
    self.write_message({'sensors': pronserve.sensors, 'timestamp': time.time()})

  def on_pronsole_log(self, msg):
    self.write_message({'log': {msg: msg, level: "debug"}})

  def on_message(self, msg):
    # TODO: the read bit of repl!
    self.write_message("You said: " + msg)

  def on_close(self):
    pronserve.clients.remove(self)
    print "WebSocket closed. %i sockets currently open." % len(pronserve.clients)

dir = os.path.dirname(__file__)
settings = dict(
  template_path=os.path.join(dir, "server", "templates"),
  static_path=os.path.join(dir, "server", "static"),
  debug=True,
)

application = tornado.web.Application([
  (r"/", RootHandler),
  (r"/inspect", InspectHandler),
  (r"/socket", ConstructSocketHandler)
], **settings)


# Pronserve: Server-specific functionality
# -------------------------------------------------

class Pronserve(pronsole.pronsole):

  def __init__(self):
    pronsole.pronsole.__init__(self)
    self.settings.sensor_names = {'T': 'extruder', 'B': 'bed'}
    self.stdout = sys.stdout
    self.ioloop = tornado.ioloop.IOLoop.instance()
    self.clients = set()
    self.settings.sensor_poll_rate = 0.3 # seconds
    self.sensors = {'extruder': -1, 'bed': -1}
    self.load_default_rc()
    services = ({'type': '_construct._tcp', 'port': 8888, 'domain': "local."})
    self.mdns = mdns.publisher().save_group({'name': 'pronserve', 'services': services })

  def run_sensor_loop(self):
    self.request_sensor_update()
    next_timeout = time.time() + self.settings.sensor_poll_rate
    gen.Task(self.ioloop.add_timeout(next_timeout, self.run_sensor_loop))

  def request_sensor_update(self):
    if self.p.online: self.p.send_now("M105")

  def recvcb(self, l):
    """ Parses a line of output from the printer via printcore """
    l = l.rstrip()

    if "T:" in l:
      self._receive_sensor_update(l)
    if l!="ok" and not l.startswith("ok T") and not l.startswith("T:"):
      self._receive_printer_error(l)

  def _receive_sensor_update(self, l):
    words = l.split(" ")
    words.pop(0)
    d = dict([ s.split(":") for s in words])

    for key, value in d.iteritems():
      self.__update_item(key, value)

    self.fire("sensor_change")

  def __update_item(self, key, value):
    sensor_name = self.settings.sensor_names[key]
    self.sensors[sensor_name] = float(value)


  def fire(self, event_name, content=None):
    for client in self.clients:
      if content == None:
        getattr(client, "on_" + event_name)()
      else:
        getattr(client, "on_" + event_name)(content)

  def log(self, *msg):
    msg = ''.join(str(i) for i in msg)
    print msg
    self.fire("pronsole_log", msg)

  def write_prompt(self):
    None


# Server Start Up
# -------------------------------------------------

print "Pronserve is starting..."
pronserve = Pronserve()
pronserve.do_connect("")

time.sleep(0.2)
pronserve.run_sensor_loop()

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
