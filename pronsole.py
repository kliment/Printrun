#!/usr/bin/env python

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

import cmd, sys
import glob, os, time, datetime
import sys, subprocess
import math, codecs
from math import sqrt
from gcoder import GCode

import printcore
from printrun.printrun_utils import install_locale
install_locale('pronterface')

if os.name == "nt":
    try:
        import _winreg
    except:
        pass
READLINE = True
try:
    import readline
    try:
        readline.rl.mode.show_all_if_ambiguous = "on" #config pyreadline on windows
    except:
        pass
except:
    READLINE = False #neither readline module is available

def dosify(name):
    return os.path.split(name)[1].split(".")[0][:8]+".g"

def measurements(g):
    gcode = GCode(g)
    gcode.measure()
    return (gcode.width, gcode.depth, gcode.height, gcode.xmin, gcode.xmax, gcode.ymin, gcode.ymax, gcode.zmin, gcode.zmax)

def totalelength(g):
    gcode = GCode(g)
    return gcode.filament_length()

def get_coordinate_value(axis, parts):
    for i in parts:
        if (axis in i):
            return float(i[1:])
    return None

def hypot3d(X1, Y1, Z1, X2 = 0.0, Y2 = 0.0, Z2 = 0.0):
    return math.hypot(X2-X1, math.hypot(Y2-Y1, Z2-Z1))

def estimate_duration(g):

    lastx = lasty = lastz = laste = lastf = 0.0
    x = y = z = e = f = 0.0
    currenttravel = 0.0
    totaltravel = 0.0
    moveduration = 0.0
    totalduration = 0.0
    acceleration = 1500.0 #mm/s/s  ASSUMING THE DEFAULT FROM SPRINTER !!!!
    layerduration = 0.0
    layerbeginduration = 0.0
    layercount = 0
    #TODO:
    # get device caps from firmware: max speed, acceleration/axis (including extruder)
    # calculate the maximum move duration accounting for above ;)
    # self.log(".... estimating ....")
    for i in g:
        i = i.split(";")[0]
        if "G4" in i or "G1" in i:
            if "G4" in i:
                parts = i.split(" ")
                moveduration = get_coordinate_value("P", parts[1:])
                if moveduration is None:
                    continue
                else:
                    moveduration /= 1000.0
            if "G1" in i:
                parts = i.split(" ")
                x = get_coordinate_value("X", parts[1:])
                if x is None: x = lastx
                y = get_coordinate_value("Y", parts[1:])
                if y is None: y = lasty
                z = get_coordinate_value("Z", parts[1:])
                if (z is None) or  (z<lastz): z = lastz # Do not increment z if it's below the previous (Lift z on move fix)
                e = get_coordinate_value("E", parts[1:])
                if e is None: e = laste
                f = get_coordinate_value("F", parts[1:])
                if f is None: f = lastf
                else: f /= 60.0 # mm/s vs mm/m

                # given last feedrate and current feedrate calculate the distance needed to achieve current feedrate.
                # if travel is longer than req'd distance, then subtract distance to achieve full speed, and add the time it took to get there.
                # then calculate the time taken to complete the remaining distance

                currenttravel = hypot3d(x, y, z, lastx, lasty, lastz)
                distance = abs(2* ((lastf+f) * (f-lastf) * 0.5 ) / acceleration)  #2x because we have to accelerate and decelerate
                if distance <= currenttravel and ( lastf + f )!=0 and f!=0:
                    moveduration = 2 * distance / ( lastf + f )
                    currenttravel -= distance
                    moveduration += currenttravel/f
                else:
                    moveduration = math.sqrt( 2 * distance / acceleration )

            totalduration += moveduration

            if z > lastz:
                layercount +=1
                #self.log("layer z: ", lastz, " will take: ", time.strftime('%H:%M:%S', time.gmtime(totalduration-layerbeginduration)))
                layerbeginduration = totalduration

            lastx = x
            lasty = y
            lastz = z
            laste = e
            lastf = f

    #self.log("Total Duration: " #, time.strftime('%H:%M:%S', time.gmtime(totalduration)))
    return "{0:d} layers, ".format(int(layercount)) + str(datetime.timedelta(seconds = int(totalduration)))

class Settings:
    #def _temperature_alias(self): return {"pla":210, "abs":230, "off":0}
    #def _temperature_validate(self, v):
    #    if v < 0: raise ValueError("You cannot set negative temperatures. To turn the hotend off entirely, set its temperature to 0.")
    #def _bedtemperature_alias(self): return {"pla":60, "abs":110, "off":0}
    def _baudrate_list(self): return ["2400", "9600", "19200", "38400", "57600", "115200"]
    def __init__(self):
        # defaults here.
        # the initial value determines the type
        self.port = ""
        self.baudrate = 115200
        self.bedtemp_abs = 110
        self.bedtemp_pla = 60
        self.temperature_abs = 230
        self.temperature_pla = 185
        self.xy_feedrate = 3000
        self.z_feedrate = 200
        self.e_feedrate = 300
        self.slicecommand = "python skeinforge/skeinforge_application/skeinforge_utilities/skeinforge_craft.py $s"
        self.sliceoptscommand = "python skeinforge/skeinforge_application/skeinforge.py"
        self.final_command = ""

    def _set(self, key, value):
        try:
            value = getattr(self, "_%s_alias"%key)()[value]
        except KeyError:
            pass
        except AttributeError:
            pass
        try:
            getattr(self, "_%s_validate"%key)(value)
        except AttributeError:
            pass
        setattr(self, key, type(getattr(self, key))(value))
        try:
            getattr(self, "_%s_cb"%key)(key, value)
        except AttributeError:
            pass
        return value
    def _tabcomplete(self, key):
        try:
            return getattr(self, "_%s_list"%key)()
        except AttributeError:
            pass
        try:
            return getattr(self, "_%s_alias"%key)().keys()
        except AttributeError:
            pass
        return []
    def _all_settings(self):
        return dict([(k, getattr(self, k)) for k in self.__dict__.keys() if not k.startswith("_")])

class pronsole(cmd.Cmd):
    def __init__(self):
        cmd.Cmd.__init__(self)
        if not READLINE:
            self.completekey = None
        self.p = printcore.printcore()
        self.p.recvcb = self.recvcb
        self.recvlisteners = []
        self.prompt = "PC>"
        self.p.onlinecb = self.online
        self.f = None
        self.listing = 0
        self.sdfiles = []
        self.paused = False
        self.sdprinting = 0
        self.temps = {"pla":"185", "abs":"230", "off":"0"}
        self.bedtemps = {"pla":"60", "abs":"110", "off":"0"}
        self.percentdone = 0
        self.tempreadings = ""
        self.macros = {}
        self.rc_loaded = False
        self.processing_rc = False
        self.processing_args = False
        self.settings = Settings()
        self.settings._port_list = self.scanserial
        self.settings._temperature_abs_cb = self.set_temp_preset
        self.settings._temperature_pla_cb = self.set_temp_preset
        self.settings._bedtemp_abs_cb = self.set_temp_preset
        self.settings._bedtemp_pla_cb = self.set_temp_preset
        self.monitoring = 0
        self.helpdict = {}
        self.helpdict["baudrate"] = _("Communications Speed (default: 115200)")
        self.helpdict["bedtemp_abs"] = _("Heated Build Platform temp for ABS (default: 110 deg C)")
        self.helpdict["bedtemp_pla"] = _("Heated Build Platform temp for PLA (default: 60 deg C)")
        self.helpdict["e_feedrate"] = _("Feedrate for Control Panel Moves in Extrusions (default: 300mm/min)")
        self.helpdict["port"] = _("Port used to communicate with printer")
        self.helpdict["slicecommand"] = _("Slice command\n   default:\n       python skeinforge/skeinforge_application/skeinforge_utilities/skeinforge_craft.py $s)")
        self.helpdict["sliceoptscommand"] = _("Slice settings command\n   default:\n       python skeinforge/skeinforge_application/skeinforge.py")
        self.helpdict["temperature_abs"] = _("Extruder temp for ABS (default: 230 deg C)")
        self.helpdict["temperature_pla"] = _("Extruder temp for PLA (default: 185 deg C)")
        self.helpdict["xy_feedrate"] = _("Feedrate for Control Panel Moves in X and Y (default: 3000mm/min)")
        self.helpdict["z_feedrate"] = _("Feedrate for Control Panel Moves in Z (default: 200mm/min)")
        self.helpdict["final_command"] = _("Executable to run when the print is finished")
        self.commandprefixes='MGT$'

    def log(self, *msg):
        print ''.join(str(i) for i in msg)

    def set_temp_preset(self, key, value):
        if not key.startswith("bed"):
            self.temps["pla"] = str(self.settings.temperature_pla)
            self.temps["abs"] = str(self.settings.temperature_abs)
            self.log("Hotend temperature presets updated, pla:%s, abs:%s" % (self.temps["pla"], self.temps["abs"]))
        else:
            self.bedtemps["pla"] = str(self.settings.bedtemp_pla)
            self.bedtemps["abs"] = str(self.settings.bedtemp_abs)
            self.log("Bed temperature presets updated, pla:%s, abs:%s" % (self.bedtemps["pla"], self.bedtemps["abs"]))

    def scanserial(self):
        """scan for available ports. return a list of device names."""
        baselist = []
        if os.name == "nt":
            try:
                key = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE, "HARDWARE\\DEVICEMAP\\SERIALCOMM")
                i = 0
                while(1):
                    baselist+=[_winreg.EnumValue(key, i)[1]]
                    i+=1
            except:
                pass

        return baselist+glob.glob('/dev/ttyUSB*') + glob.glob('/dev/ttyACM*') +glob.glob("/dev/tty.*")+glob.glob("/dev/cu.*")+glob.glob("/dev/rfcomm*")

    def online(self):
        self.log("printer is now online")
        self.write_prompt()

    def write_prompt(self):
        sys.stdout.write(self.prompt)
        sys.stdout.flush()

    def help_help(self, l):
        self.do_help("")

    def do_gcodes(self, l):
        self.help_gcodes()

    def help_gcodes(self):
        self.log("Gcodes are passed through to the printer as they are")

    def complete_macro(self, text, line, begidx, endidx):
        if (len(line.split()) == 2 and line[-1] != " ") or (len(line.split()) == 1 and line[-1]==" "):
            return [i for i in self.macros.keys() if i.startswith(text)]
        elif(len(line.split()) == 3 or (len(line.split()) == 2 and line[-1]==" ")):
            return [i for i in ["/D", "/S"] + self.completenames(text) if i.startswith(text)]
        else:
            return []

    def hook_macro(self, l):
        l = l.rstrip()
        ls = l.lstrip()
        ws = l[:len(l)-len(ls)] # just leading whitespace
        if len(ws) == 0:
            self.end_macro()
            # pass the unprocessed line to regular command processor to not require empty line in .pronsolerc
            return self.onecmd(l)
        self.cur_macro_def += l + "\n"

    def end_macro(self):
        if self.__dict__.has_key("onecmd"): del self.onecmd # remove override
        self.prompt = "PC>"
        if self.cur_macro_def!="":
            self.macros[self.cur_macro_name] = self.cur_macro_def
            macro = self.compile_macro(self.cur_macro_name, self.cur_macro_def)
            setattr(self.__class__, "do_"+self.cur_macro_name, lambda self, largs, macro = macro:macro(self,*largs.split()))
            setattr(self.__class__, "help_"+self.cur_macro_name, lambda self, macro_name = self.cur_macro_name: self.subhelp_macro(macro_name))
            if not self.processing_rc:
                self.log("Macro '"+self.cur_macro_name+"' defined")
                # save it
                if not self.processing_args:
                    macro_key = "macro "+self.cur_macro_name
                    macro_def = macro_key
                    if "\n" in self.cur_macro_def:
                        macro_def += "\n"
                    else:
                        macro_def += " "
                    macro_def += self.cur_macro_def
                    self.save_in_rc(macro_key, macro_def)
        else:
            self.log("Empty macro - cancelled")
        del self.cur_macro_name, self.cur_macro_def

    def compile_macro_line(self, line):
        line = line.rstrip()
        ls = line.lstrip()
        ws = line[:len(line)-len(ls)] # just leading whitespace
        if ls == "" or ls.startswith('#'): return "" # no code
        if ls.startswith('!'):
            return ws + ls[1:] + "\n" # python mode
        else:
            return ws + 'self.onecmd("'+ls+'".format(*arg))\n' # parametric command mode

    def compile_macro(self, macro_name, macro_def):
        if macro_def.strip() == "":
            self.log("Empty macro - cancelled")
            return
        pycode = "def macro(self,*arg):\n"
        if "\n" not in macro_def.strip():
            pycode += self.compile_macro_line("  "+macro_def.strip())
        else:
            lines = macro_def.split("\n")
            for l in lines:
                pycode += self.compile_macro_line(l)
        exec pycode
        return macro

    def start_macro(self, macro_name, prev_definition = "", suppress_instructions = False):
        if not self.processing_rc and not suppress_instructions:
            self.log("Enter macro using indented lines, end with empty line")
        self.cur_macro_name = macro_name
        self.cur_macro_def = ""
        self.onecmd = self.hook_macro # override onecmd temporarily
        self.prompt = "..>"

    def delete_macro(self, macro_name):
        if macro_name in self.macros.keys():
            delattr(self.__class__, "do_"+macro_name)
            del self.macros[macro_name]
            self.log("Macro '"+macro_name+"' removed")
            if not self.processing_rc and not self.processing_args:
                self.save_in_rc("macro "+macro_name, "")
        else:
            self.log("Macro '"+macro_name+"' is not defined")
    def do_macro(self, args):
        if args.strip()=="":
            self.print_topics("User-defined macros", self.macros.keys(), 15, 80)
            return
        arglist = args.split(None, 1)
        macro_name = arglist[0]
        if macro_name not in self.macros and hasattr(self.__class__, "do_"+macro_name):
            self.log("Name '"+macro_name+"' is being used by built-in command")
            return
        if len(arglist) == 2:
            macro_def = arglist[1]
            if macro_def.lower() == "/d":
                self.delete_macro(macro_name)
                return
            if macro_def.lower() == "/s":
                self.subhelp_macro(macro_name)
                return
            self.cur_macro_def = macro_def
            self.cur_macro_name = macro_name
            self.end_macro()
            return
        if self.macros.has_key(macro_name):
            self.start_macro(macro_name, self.macros[macro_name])
        else:
            self.start_macro(macro_name)

    def help_macro(self):
        self.log("Define single-line macro: macro <name> <definition>")
        self.log("Define multi-line macro:  macro <name>")
        self.log("Enter macro definition in indented lines. Use {0} .. {N} to substitute macro arguments")
        self.log("Enter python code, prefixed with !  Use arg[0] .. arg[N] to substitute macro arguments")
        self.log("Delete macro:             macro <name> /d")
        self.log("Show macro definition:    macro <name> /s")
        self.log("'macro' without arguments displays list of defined macros")

    def subhelp_macro(self, macro_name):
        if macro_name in self.macros.keys():
            macro_def = self.macros[macro_name]
            if "\n" in macro_def:
                self.log("Macro '"+macro_name+"' defined as:")
                self.log(self.macros[macro_name]+"----------------")
            else:
                self.log("Macro '"+macro_name+"' defined as: '"+macro_def+"'")
        else:
            self.log("Macro '"+macro_name+"' is not defined")

    def set(self, var, str):
        try:
            t = type(getattr(self.settings, var))
            value = self.settings._set(var, str)
            if not self.processing_rc and not self.processing_args:
                self.save_in_rc("set "+var, "set %s %s" % (var, value))
        except AttributeError:
            self.log("Unknown variable '%s'" % var)
        except ValueError, ve:
            self.log("Bad value for variable '%s', expecting %s (%s)" % (var, repr(t)[1:-1], ve.args[0]))

    def do_set(self, argl):
        args = argl.split(None, 1)
        if len(args) < 1:
            for k in [kk for kk in dir(self.settings) if not kk.startswith("_")]:
                self.log("%s = %s" % (k, str(getattr(self.settings, k))))
            return
            value = getattr(self.settings, args[0])
        if len(args) < 2:
            try:
                self.log("%s = %s" % (args[0], getattr(self.settings, args[0])))
            except AttributeError:
                self.log("Unknown variable '%s'" % args[0])
            return
        self.set(args[0], args[1])

    def help_set(self):
        self.log("Set variable:   set <variable> <value>")
        self.log("Show variable:  set <variable>")
        self.log("'set' without arguments displays all variables")

    def complete_set(self, text, line, begidx, endidx):
        if (len(line.split()) == 2 and line[-1] != " ") or (len(line.split()) == 1 and line[-1]==" "):
            return [i for i in dir(self.settings) if not i.startswith("_") and i.startswith(text)]
        elif(len(line.split()) == 3 or (len(line.split()) == 2 and line[-1]==" ")):
            return [i for i in self.settings._tabcomplete(line.split()[1]) if i.startswith(text)]
        else:
            return []

    def postloop(self):
        self.p.disconnect()
        cmd.Cmd.postloop(self)

    def load_rc(self, rc_filename):
        self.processing_rc = True
        try:
            rc = codecs.open(rc_filename, "r", "utf-8")
            self.rc_filename = os.path.abspath(rc_filename)
            for rc_cmd in rc:
                if not rc_cmd.lstrip().startswith("#"):
                    self.onecmd(rc_cmd)
            rc.close()
            if hasattr(self, "cur_macro_def"):
                self.end_macro()
            self.rc_loaded = True
        finally:
            self.processing_rc = False

    def load_default_rc(self, rc_filename = ".pronsolerc"):
        try:
            try:
                self.load_rc(os.path.join(os.path.expanduser("~"), rc_filename))
            except IOError:
                self.load_rc(rc_filename)
        except IOError:
            # make sure the filename is initialized
            self.rc_filename = os.path.abspath(os.path.join(os.path.expanduser("~"), rc_filename))

    def save_in_rc(self, key, definition):
        """
        Saves or updates macro or other definitions in .pronsolerc
        key is prefix that determines what is being defined/updated (e.g. 'macro foo')
        definition is the full definition (that is written to file). (e.g. 'macro foo move x 10')
        Set key as empty string to just add (and not overwrite)
        Set definition as empty string to remove it from .pronsolerc
        To delete line from .pronsolerc, set key as the line contents, and definition as empty string
        Only first definition with given key is overwritten.
        Updates are made in the same file position.
        Additions are made to the end of the file.
        """
        rci, rco = None, None
        if definition != "" and not definition.endswith("\n"):
            definition += "\n"
        try:
            written = False
            if os.path.exists(self.rc_filename):
                import shutil
                shutil.copy(self.rc_filename, self.rc_filename+"~bak")
                rci = codecs.open(self.rc_filename+"~bak", "r", "utf-8")
            rco = codecs.open(self.rc_filename, "w", "utf-8")
            if rci is not None:
                overwriting = False
                for rc_cmd in rci:
                    l = rc_cmd.rstrip()
                    ls = l.lstrip()
                    ws = l[:len(l)-len(ls)] # just leading whitespace
                    if overwriting and len(ws) == 0:
                        overwriting = False
                    if not written and key != "" and  rc_cmd.startswith(key) and (rc_cmd+"\n")[len(key)].isspace():
                        overwriting = True
                        written = True
                        rco.write(definition)
                    if not overwriting:
                        rco.write(rc_cmd)
                        if not rc_cmd.endswith("\n"): rco.write("\n")
            if not written:
                rco.write(definition)
            if rci is not None:
                rci.close()
            rco.close()
            #if definition != "":
            #    self.log("Saved '"+key+"' to '"+self.rc_filename+"'")
            #else:
            #    self.log("Removed '"+key+"' from '"+self.rc_filename+"'")
        except Exception, e:
            self.log("Saving failed for", key+":", str(e))
        finally:
            del rci, rco

    def preloop(self):
        self.log("Welcome to the printer console! Type \"help\" for a list of available commands.")
        cmd.Cmd.preloop(self)

    def do_connect(self, l):
        a = l.split()
        p = self.scanserial()
        port = self.settings.port
        if (port == "" or port not in p) and len(p)>0:
            port = p[0]
        baud = self.settings.baudrate or 115200
        if(len(a)>0):
            port = a[0]
        if(len(a)>1):
            try:
                baud = int(a[1])
            except:
                self.log("Bad baud value '"+a[1]+"' ignored")
        if len(p) == 0 and not port:
            self.log("No serial ports detected - please specify a port")
            return
        if len(a) == 0:
            self.log("No port specified - connecting to %s at %dbps" % (port, baud))
        if port != self.settings.port:
            self.settings.port = port
            self.save_in_rc("set port", "set port %s" % port)
        if baud != self.settings.baudrate:
            self.settings.baudrate = baud
            self.save_in_rc("set baudrate", "set baudrate %d" % baud)
        self.p.connect(port, baud)

    def help_connect(self):
        self.log("Connect to printer")
        self.log("connect <port> <baudrate>")
        self.log("If port and baudrate are not specified, connects to first detected port at 115200bps")
        ports = self.scanserial()
        if(len(ports)):
            self.log("Available ports: ", " ".join(ports))
        else:
            self.log("No serial ports were automatically found.")

    def complete_connect(self, text, line, begidx, endidx):
        if (len(line.split()) == 2 and line[-1] != " ") or (len(line.split()) == 1 and line[-1]==" "):
            return [i for i in self.scanserial() if i.startswith(text)]
        elif(len(line.split()) == 3 or (len(line.split()) == 2 and line[-1]==" ")):
            return [i for i in ["2400", "9600", "19200", "38400", "57600", "115200"] if i.startswith(text)]
        else:
            return []

    def do_disconnect(self, l):
        self.p.disconnect()

    def help_disconnect(self):
        self.log("Disconnects from the printer")

    def do_load(self,l):
        self._do_load(l)

    def _do_load(self,l):
        if len(l)==0:
            self.log("No file name given.")
            return
        self.log("Loading file:"+l)
        if not(os.path.exists(l)):
            self.log("File not found!")
            return
        self.f = [i.replace("\n", "").replace("\r", "") for i in open(l)]
        self.filename = l
        self.log("Loaded ", l, ", ", len(self.f)," lines.")

    def complete_load(self, text, line, begidx, endidx):
        s = line.split()
        if len(s)>2:
            return []
        if (len(s) == 1 and line[-1]==" ") or (len(s) == 2 and line[-1]!=" "):
            if len(s)>1:
                return [i[len(s[1])-len(text):] for i in glob.glob(s[1]+"*/")+glob.glob(s[1]+"*.g*")]
            else:
                return glob.glob("*/")+glob.glob("*.g*")

    def help_load(self):
        self.log("Loads a gcode file (with tab-completion)")

    def do_upload(self, l):
        if len(l) == 0:
            self.log("No file name given.")
            return
        self.log("Loading file:"+l.split()[0])
        if not(os.path.exists(l.split()[0])):
            self.log("File not found!")
            return
        if not self.p.online:
            self.log("Not connected to printer.")
            return
        self.f = [i.replace("\n", "") for i in open(l.split()[0])]
        self.filename = l.split()[0]
        self.log("Loaded ", l, ", ", len(self.f)," lines.")
        tname = ""
        if len(l.split())>1:
            tname = l.split()[1]
        else:
            self.log("please enter target name in 8.3 format.")
            return
        self.log("Uploading as ", tname)
        self.log(("Uploading "+self.filename))
        self.p.send_now("M28 "+tname)
        self.log(("Press Ctrl-C to interrupt upload."))
        self.p.startprint(self.f)
        try:
            sys.stdout.write("Progress: 00.0%")
            sys.stdout.flush()
            time.sleep(1)
            while self.p.printing:
                time.sleep(1)
                sys.stdout.write("\b\b\b\b\b%04.1f%%" % (100*float(self.p.queueindex)/len(self.p.mainqueue),) )
                sys.stdout.flush()
            self.p.send_now("M29 "+tname)
            self.sleep(0.2)
            self.p.clear = 1
            self.listing = 0
            self.sdfiles = []
            self.recvlisteners+=[self.listfiles]
            self.p.send_now("M20")
            time.sleep(0.5)
            self.log("\b\b\b\b\b100%. Upload completed. ", tname, " should now be on the card.")
            return
        except:
            self.log("...interrupted!")
            self.p.pause()
            self.p.send_now("M29 "+tname)
            time.sleep(0.2)
            self.p.clear = 1
            self.p.startprint([])
            self.log("A partial file named ", tname, " may have been written to the sd card.")


    def complete_upload(self, text, line, begidx, endidx):
        s = line.split()
        if len(s)>2:
            return []
        if (len(s) == 1 and line[-1]==" ") or (len(s) == 2 and line[-1]!=" "):
            if len(s)>1:
                return [i[len(s[1])-len(text):] for i in glob.glob(s[1]+"*/")+glob.glob(s[1]+"*.g*")]
            else:
                return glob.glob("*/")+glob.glob("*.g*")

    def help_upload(self):
        self.log("Uploads a gcode file to the sd card")

    def help_print(self):
        if self.f is None:
            self.log("Send a loaded gcode file to the printer. Load a file with the load command first.")
        else:
            self.log("Send a loaded gcode file to the printer. You have "+self.filename+" loaded right now.")

    def do_print(self, l):
        if self.f is None:
            self.log("No file loaded. Please use load first.")
            return
        if not self.p.online:
            self.log("Not connected to printer.")
            return
        self.log(("printing "+self.filename))
        self.log(("You can monitor the print with the monitor command."))
        self.p.startprint(self.f)
        #self.p.pause()
        #self.paused = True
        #self.do_resume(None)

    def do_pause(self, l):
        if self.sdprinting:
            self.p.send_now("M25")
        else:
            if(not self.p.printing):
                self.log("Not self.log(ing, cannot pause.")
                return
            self.p.pause()
            #self.p.connect()# This seems to work, but is not a good solution.
        self.paused = True

        #self.do_resume(None)

    def help_pause(self):
        self.log("Pauses a running print")

    def do_resume(self, l):
        if not self.paused:
            self.log("Not paused, unable to resume. Start a print first.")
            return
        self.paused = False
        if self.sdprinting:
            self.p.send_now("M24")
            return
        else:
            self.p.resume()

    def help_resume(self):
        self.log("Resumes a paused print.")

    def emptyline(self):
        pass

    def do_shell(self, l):
        exec(l)

    def listfiles(self, line):
        if "Begin file list" in line:
            self.listing = 1
        elif "End file list" in line:
            self.listing = 0
            self.recvlisteners.remove(self.listfiles)
        elif self.listing:
            self.sdfiles+=[line.replace("\n", "").replace("\r", "").lower()]

    def do_ls(self, l):
        if not self.p.online:
            self.log("printer is not online. Try connect to it first.")
            return
        self.listing = 2
        self.sdfiles = []
        self.recvlisteners+=[self.listfiles]
        self.p.send_now("M20")
        time.sleep(0.5)
        self.log(" ".join(self.sdfiles))

    def help_ls(self):
        self.log("lists files on the SD card")

    def waitforsdresponse(self, l):
        if "file.open failed" in l:
            self.log("Opening file failed.")
            self.recvlisteners.remove(self.waitforsdresponse)
            return
        if "File opened" in l:
            self.log(l)
        if "File selected" in l:
            self.log("Starting print")
            self.p.send_now("M24")
            self.sdprinting = 1
            #self.recvlisteners.remove(self.waitforsdresponse)
            return
        if "Done printing file" in l:
            self.log(l)
            self.sdprinting = 0
            self.recvlisteners.remove(self.waitforsdresponse)
            return
        if "SD printing byte" in l:
            #M27 handler
            try:
                resp = l.split()
                vals = resp[-1].split("/")
                self.percentdone = 100.0*int(vals[0])/int(vals[1])
            except:
                pass

    def do_reset(self, l):
        self.p.reset()

    def help_reset(self):
        self.log("Resets the printer.")

    def do_sdprint(self, l):
        if not self.p.online:
            self.log("printer is not online. Try connect to it first.")
            return
        self.listing = 2
        self.sdfiles = []
        self.recvlisteners+=[self.listfiles]
        self.p.send_now("M20")
        time.sleep(0.5)
        if not (l.lower() in self.sdfiles):
            self.log("File is not present on card. Upload it first")
            return
        self.recvlisteners+=[self.waitforsdresponse]
        self.p.send_now("M23 "+l.lower())
        self.log("printing file: "+l.lower()+" from SD card.")
        self.log("Requesting SD print...")
        time.sleep(1)

    def help_sdprint(self):
        self.log("print a file from the SD card. Tabcompletes with available file names.")
        self.log("sdprint filename.g")

    def complete_sdprint(self, text, line, begidx, endidx):
        if self.sdfiles==[] and self.p.online:
            self.listing = 2
            self.recvlisteners+=[self.listfiles]
            self.p.send_now("M20")
            time.sleep(0.5)
        if (len(line.split()) == 2 and line[-1] != " ") or (len(line.split()) == 1 and line[-1]==" "):
            return [i for i in self.sdfiles if i.startswith(text)]

    def recvcb(self, l):
        if "T:" in l:
            self.tempreadings = l

        tstring = l.rstrip()
        if(tstring!="ok" and not tstring.startswith("ok T") and not tstring.startswith("T:") and not self.listing and not self.monitoring):
            self.log(tstring)
            self.write_prompt()
        for i in self.recvlisteners:
            i(l)

    def help_shell(self):
        self.log("Executes a python command. Example:")
        self.log("! os.listdir('.')")

    def default(self, l):
        if(l[0] in self.commandprefixes.upper()):
            if(self.p and self.p.online):
                if(not self.p.loud):
                    self.log("SENDING:"+l)
                self.p.send_now(l)
            else:
                self.log("printer is not online.")
            return
        elif(l[0] in self.commandprefixes.lower()):
            if(self.p and self.p.online):
                if(not self.p.loud):
                    self.log("SENDING:"+l.upper())
                self.p.send_now(l.upper())
            else:
                self.log("printer is not online.")
            return
        else:
            cmd.Cmd.default(self, l)

    def help_help(self):
        self.do_help("")

    def tempcb(self, l):
        if "T:" in l:
            self.log(l.replace("\r", "").replace("T", "Hotend").replace("B", "Bed").replace("\n", "").replace("ok ", ""))

    def do_gettemp(self, l):
        if self.p.online:
            self.recvlisteners+=[self.tempcb]
            self.p.send_now("M105")
            time.sleep(0.75)
            self.recvlisteners.remove(self.tempcb)

    def help_gettemp(self):
        self.log("Read the extruder and bed temperature.")

    def do_settemp(self, l):
        try:
            l = l.lower().replace(", ",".")
            for i in self.temps.keys():
                l = l.replace(i, self.temps[i])
            f = float(l)
            if f>=0:
                if self.p.online:
                    self.p.send_now("M104 S"+l)
                    self.log("Setting hotend temperature to ", f, " degrees Celsius.")
                else:
                    self.log("printer is not online.")
            else:
                self.log("You cannot set negative temperatures. To turn the hotend off entirely, set its temperature to 0.")
        except:
            self.log("You must enter a temperature.")

    def help_settemp(self):
        self.log("Sets the hotend temperature to the value entered.")
        self.log("Enter either a temperature in celsius or one of the following keywords")
        self.log(", ".join([i+"("+self.temps[i]+")" for i in self.temps.keys()]))

    def complete_settemp(self, text, line, begidx, endidx):
        if (len(line.split()) == 2 and line[-1] != " ") or (len(line.split()) == 1 and line[-1]==" "):
            return [i for i in self.temps.keys() if i.startswith(text)]

    def do_bedtemp(self, l):
        try:
            l = l.lower().replace(", ",".")
            for i in self.bedtemps.keys():
                l = l.replace(i, self.bedtemps[i])
            f = float(l)
            if f>=0:
                if self.p.online:
                    self.p.send_now("M140 S"+l)
                    self.log("Setting bed temperature to ", f, " degrees Celsius.")
                else:
                    self.log("printer is not online.")
            else:
                self.log("You cannot set negative temperatures. To turn the bed off entirely, set its temperature to 0.")
        except:
            self.log("You must enter a temperature.")

    def help_bedtemp(self):
        self.log("Sets the bed temperature to the value entered.")
        self.log("Enter either a temperature in celsius or one of the following keywords")
        self.log(", ".join([i+"("+self.bedtemps[i]+")" for i in self.bedtemps.keys()]))

    def complete_bedtemp(self, text, line, begidx, endidx):
        if (len(line.split()) == 2 and line[-1] != " ") or (len(line.split()) == 1 and line[-1]==" "):
            return [i for i in self.bedtemps.keys() if i.startswith(text)]

    def do_move(self, l):
        if(len(l.split())<2):
            self.log("No move specified.")
            return
        if self.p.printing:
            self.log("printer is currently printing. Please pause the print before you issue manual commands.")
            return
        if not self.p.online:
            self.log("printer is not online. Unable to move.")
            return
        l = l.split()
        if(l[0].lower()=="x"):
            feed = self.settings.xy_feedrate
            axis = "X"
        elif(l[0].lower()=="y"):
            feed = self.settings.xy_feedrate
            axis = "Y"
        elif(l[0].lower()=="z"):
            feed = self.settings.z_feedrate
            axis = "Z"
        elif(l[0].lower()=="e"):
            feed = self.settings.e_feedrate
            axis = "E"
        else:
            self.log("Unknown axis.")
            return
        dist = 0
        try:
            dist = float(l[1])
        except:
            self.log("Invalid distance")
            return
        try:
            feed = int(l[2])
        except:
            pass
        self.p.send_now("G91")
        self.p.send_now("G1 "+axis+str(l[1])+" F"+str(feed))
        self.p.send_now("G90")

    def help_move(self):
        self.log("Move an axis. Specify the name of the axis and the amount. ")
        self.log("move X 10 will move the X axis forward by 10mm at ", self.settings.xy_feedrate, "mm/min (default XY speed)")
        self.log("move Y 10 5000 will move the Y axis forward by 10mm at 5000mm/min")
        self.log("move Z -1 will move the Z axis down by 1mm at ", self.settings.z_feedrate, "mm/min (default Z speed)")
        self.log("Common amounts are in the tabcomplete list.")

    def complete_move(self, text, line, begidx, endidx):
        if (len(line.split()) == 2 and line[-1] != " ") or (len(line.split()) == 1 and line[-1]==" "):
            return [i for i in ["X ", "Y ", "Z ", "E "] if i.lower().startswith(text)]
        elif(len(line.split()) == 3 or (len(line.split()) == 2 and line[-1]==" ")):
            base = line.split()[-1]
            rlen = 0
            if base.startswith("-"):
                rlen = 1
            if line[-1]==" ":
                base = ""
            return [i[rlen:] for i in ["-100", "-10", "-1", "-0.1", "100", "10", "1", "0.1", "-50", "-5", "-0.5", "50", "5", "0.5", "-200", "-20", "-2", "-0.2", "200", "20", "2", "0.2"] if i.startswith(base)]
        else:
            return []

    def do_extrude(self, l, override = None, overridefeed = 300):
        length = 5#default extrusion length
        feed = self.settings.e_feedrate#default speed
        if not self.p.online:
            self.log("printer is not online. Unable to move.")
            return
        if self.p.printing:
            self.log("printer is currently printing. Please pause the print before you issue manual commands.")
            return
        ls = l.split()
        if len(ls):
            try:
                length = float(ls[0])
            except:
                self.log("Invalid length given.")
        if len(ls)>1:
            try:
                feed = int(ls[1])
            except:
                self.log("Invalid speed given.")
        if override is not None:
            length = override
            feed = overridefeed
        if length > 0:
            self.log("Extruding %fmm of filament."%(length,))
        elif length <0:
            self.log("Reversing %fmm of filament."%(-1*length,))
        else:
            "Length is 0, not doing anything."
        self.p.send_now("G91")
        self.p.send_now("G1 E"+str(length)+" F"+str(feed))
        self.p.send_now("G90")

    def help_extrude(self):
        self.log("Extrudes a length of filament, 5mm by default, or the number of mm given as a parameter")
        self.log("extrude - extrudes 5mm of filament at 300mm/min (5mm/s)")
        self.log("extrude 20 - extrudes 20mm of filament at 300mm/min (5mm/s)")
        self.log("extrude -5 - REVERSES 5mm of filament at 300mm/min (5mm/s)")
        self.log("extrude 10 210 - extrudes 10mm of filament at 210mm/min (3.5mm/s)")

    def do_reverse(self, l):
        length = 5#default extrusion length
        feed = self.settings.e_feedrate#default speed
        if not self.p.online:
            self.log("printer is not online. Unable to move.")
            return
        if self.p.printing:
            self.log("printer is currently printing. Please pause the print before you issue manual commands.")
            return
        ls = l.split()
        if len(ls):
            try:
                length = float(ls[0])
            except:
                self.log("Invalid length given.")
        if len(ls)>1:
            try:
                feed = int(ls[1])
            except:
                self.log("Invalid speed given.")
        self.do_extrude("", length*-1.0, feed)

    def help_reverse(self):
        self.log("Reverses the extruder, 5mm by default, or the number of mm given as a parameter")
        self.log("reverse - reverses 5mm of filament at 300mm/min (5mm/s)")
        self.log("reverse 20 - reverses 20mm of filament at 300mm/min (5mm/s)")
        self.log("reverse 10 210 - extrudes 10mm of filament at 210mm/min (3.5mm/s)")
        self.log("reverse -5 - EXTRUDES 5mm of filament at 300mm/min (5mm/s)")

    def do_exit(self, l):
        self.log("Disconnecting from printer...")
        self.p.disconnect()
        self.log("Exiting program. Goodbye!")
        return True

    def help_exit(self):
        self.log("Disconnects from the printer and exits the program.")

    def do_monitor(self, l):
        interval = 5
        if not self.p.online:
            self.log("printer is not online. Please connect first.")
            return
        self.log("Monitoring printer, use ^C to interrupt.")
        if len(l):
            try:
                interval = float(l)
            except:
                self.log("Invalid period given.")
        self.log("Updating values every %f seconds."%(interval,))
        self.monitoring = 1
        try:
            while(1):
                self.p.send_now("M105")
                if(self.sdprinting):
                    self.p.send_now("M27")
                time.sleep(interval)
                #self.log((self.tempreadings.replace("\r", "").replace("T", "Hotend").replace("B", "Bed").replace("\n", "").replace("ok ", "")))
                if(self.p.printing):
                    self.log("print progress: ", 100*float(self.p.queueindex)/len(self.p.mainqueue), "%")

                if(self.sdprinting):
                    self.log("SD print progress: ", self.percentdone, "%")

        except:
            self.log("Done monitoring.")
            pass
        self.monitoring = 0

    def help_monitor(self):
        self.log("Monitor a machine's temperatures and an SD print's status.")
        self.log("monitor - Reports temperature and SD print status (if SD printing) every 5 seconds")
        self.log("monitor 2 - Reports temperature and SD print status (if SD printing) every 2 seconds")

    def expandcommand(self, c):
        return c.replace("$python", sys.executable)

    def do_skein(self, l):
        l = l.split()
        if len(l) == 0:
            self.log("No file name given.")
            return
        settings = 0
        if(l[0]=="set"):
            settings = 1
        else:
            self.log("Skeining file:"+l[0])
            if not(os.path.exists(l[0])):
                self.log("File not found!")
                return
        try:
            import shlex
            if(settings):
                param = self.expandcommand(self.settings.sliceoptscommand).replace("\\", "\\\\").encode()
                self.log("Entering slicer settings: ", param)
                subprocess.call(shlex.split(param))
            else:
                param = self.expandcommand(self.settings.slicecommand).encode()
                self.log("Slicing: ", param)
                params = [i.replace("$s", l[0]).replace("$o", l[0].replace(".stl", "_export.gcode").replace(".STL", "_export.gcode")).encode() for i in shlex.split(param.replace("\\", "\\\\").encode())]
                subprocess.call(params)
                self.log("Loading sliced file.")
                self.do_load(l[0].replace(".stl", "_export.gcode"))
        except Exception, e:
            self.log("Skeinforge execution failed: ", e)

    def complete_skein(self, text, line, begidx, endidx):
        s = line.split()
        if len(s)>2:
            return []
        if (len(s) == 1 and line[-1]==" ") or (len(s) == 2 and line[-1]!=" "):
            if len(s)>1:
                return [i[len(s[1])-len(text):] for i in glob.glob(s[1]+"*/")+glob.glob(s[1]+"*.stl")]
            else:
                return glob.glob("*/")+glob.glob("*.stl")

    def help_skein(self):
        self.log("Creates a gcode file from an stl model using the slicer (with tab-completion)")
        self.log("skein filename.stl - create gcode file")
        self.log("skein filename.stl view - create gcode file and view using skeiniso")
        self.log("skein set - adjust slicer settings")


    def do_home(self, l):
        if not self.p.online:
            self.log("printer is not online. Unable to move.")
            return
        if self.p.printing:
            self.log("printer is currently printing. Please pause the print before you issue manual commands.")
            return
        if "x" in l.lower():
            self.p.send_now("G28 X0")
        if "y" in l.lower():
            self.p.send_now("G28 Y0")
        if "z" in l.lower():
            self.p.send_now("G28 Z0")
        if "e" in l.lower():
            self.p.send_now("G92 E0")
        if not len(l):
            self.p.send_now("G28")
            self.p.send_now("G92 E0")

    def help_home(self):
        self.log("Homes the printer")
        self.log("home - homes all axes and zeroes the extruder(Using G28 and G92)")
        self.log("home xy - homes x and y axes (Using G28)")
        self.log("home z - homes z axis only (Using G28)")
        self.log("home e - set extruder position to zero (Using G92)")
        self.log("home xyze - homes all axes and zeroes the extruder (Using G28 and G92)")

    def parse_cmdline(self, args):
        import getopt
        opts, args = getopt.getopt(args, "c:e:hw", ["conf = ", "config = ", "help"])
        for o, a in opts:
            #self.log(repr((o, a)))
            if o in ("-c", "--conf", "--config"):
                self.load_rc(a)
            elif o in ("-h", "--help"):
                self.log("Usage: "+sys.argv[0]+' [-c filename [-c filename2 ... ] ] [-e "command" ...]')
                self.log("  -c | --conf | --config   - override startup .pronsolerc file")
                self.log("     may chain config files, settings auto-save will go into last file in the chain")
                self.log('  -e <command> - executes command after configuration/.pronsolerc is loaded')
                self.log("     macros/settings from these commands are not autosaved")
                sys.exit()
        if not self.rc_loaded:
            self.load_default_rc()
        for o, a in opts:
            if o == "-e":
                self.processing_args = True
                self.onecmd(a)
                self.processing_args = False

if __name__ == "__main__":

    interp = pronsole()
    interp.parse_cmdline(sys.argv[1:])
    try:
        interp.cmdloop()
    except:
        interp.p.disconnect()
        #raise
