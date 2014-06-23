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

import platform
import traceback
import logging
import os

if platform.system() == "Darwin":
    from .osx import inhibit_sleep_osx, deinhibit_sleep_osx
    inhibit_sleep = inhibit_sleep_osx
    deinhibit_sleep = deinhibit_sleep_osx
elif platform.system() == "Windows":
    import ctypes
    ES_CONTINUOUS = 0x80000000
    ES_SYSTEM_REQUIRED = 0x00000001

    def inhibit_sleep(reason):
        mode = ES_CONTINUOUS | ES_SYSTEM_REQUIRED
        ctypes.windll.kernel32.SetThreadExecutionState(ctypes.c_int(mode))

    def deinhibit_sleep():
        ctypes.windll.kernel32.SetThreadExecutionState(ctypes.c_int(ES_CONTINUOUS))
else:
    import dbus

    try:
        inhibit_sleep_handler = None
        inhibit_sleep_token = None
        bus = dbus.SessionBus()
        try:
            # GNOME uses the right object path, try it first
            service_name = "org.freedesktop.ScreenSaver"
            proxy = bus.get_object(service_name,
                                   "/org/freedesktop/ScreenSaver")
            inhibit_sleep_handler = dbus.Interface(proxy, service_name)
            # Do a test run
            token = inhibit_sleep_handler.Inhibit("printrun", "test")
            inhibit_sleep_handler.UnInhibit(token)
        except dbus.DBusException:
            # KDE uses /ScreenSaver object path, let's try it as well
            proxy = bus.get_object(service_name,
                                   "/ScreenSaver")
            inhibit_sleep_handler = dbus.Interface(proxy, service_name)
            token = inhibit_sleep_handler.Inhibit("printrun", "test")
            inhibit_sleep_handler.UnInhibit(token)

        def inhibit_sleep(reason):
            global inhibit_sleep_handler, inhibit_sleep_token
            inhibit_sleep_token = inhibit_sleep_handler.Inhibit("printrun", reason)

        def deinhibit_sleep():
            global inhibit_sleep_handler, inhibit_sleep_token
            if inhibit_sleep_handler is None or inhibit_sleep_token is None:
                return
            inhibit_sleep_handler.UnInhibit(inhibit_sleep_token)
            inhibit_sleep_token = None
    except dbus.DBusException, e:
        logging.warning("Could not setup DBus for sleep inhibition: %s" % e)

        def inhibit_sleep(reason):
            return

        def deinhibit_sleep():
            return

try:
    import psutil

    if platform.system() != "Windows":
        import resource
        rlimit_nice = 13 if not hasattr(psutil, "RLIMIT_NICE") else psutil.RLIMIT_NICE
        nice_limit, _ = resource.getrlimit(rlimit_nice)
        high_priority_nice = 20 - nice_limit

    def set_nice(nice):
        p = psutil.Process(os.getpid())
        if callable(p.nice):
            p.nice(nice)
        else:
            p.nice = nice

    def set_priority():
        if platform.system() == "Windows":
            set_nice(psutil.HIGH_PRIORITY_CLASS)
        else:
            if high_priority_nice < 0:
                set_nice(high_priority_nice)

    def reset_priority():
        if platform.system() == "Windows":
            set_nice(psutil.NORMAL_PRIORITY_CLASS)
        else:
            if high_priority_nice < 0:
                set_nice(0)

    def powerset_print_start(reason):
        set_priority()
        inhibit_sleep(reason)

    def powerset_print_stop():
        reset_priority()
        deinhibit_sleep()
except ImportError:
    print "psutil unavailable, could not import power utils:"
    traceback.print_exc()

    def powerset_print_start(reason):
        pass

    def powerset_print_stop():
        pass
