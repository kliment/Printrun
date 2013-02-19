#!/usr/bin/python
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

import pronterface
import cherrypy, re, ConfigParser, threading, sys
import os.path

from printrun.printrun_utils import configfile, imagefile, sharedfile

users = {}

def PrintHeader():
    return '<html>\n<head>\n<title>Pronterface-Web</title>\n<link rel = "stylesheet" type = "text/css" href = "/css/style.css" type = "text/css"></link>\n</head>\n<body>\n'

def PrintMenu():
    return '<div id = "mainmenu"><ul><li><a href = "/">home</a></li><li><a href = "/settings">settings</a></li><li><a href = "/console">console</a></li><li><a href = "/status">status (XML)</a></li></ul></div>'

def PrintFooter():
    return "</body></html>"

def ReloadPage(action):
    return "<html><head><meta http-equiv='refresh' content='0;url=/'></head><body>"+action+"</body></html>"

def TReloadPage(action):
    return action

def clear_text(mypass):
    return mypass

gPronterPtr = 0
gWeblog     = ""
gLogRefresh =5
class SettingsPage(object):
    def __init__(self):
        self.name = "<div id='title'>Pronterface Settings</div>"

    def index(self):
        pageText = PrintHeader()+self.name+PrintMenu()
        pageText = pageText+"<div id='settings'><table>\n<tr><th>setting</th><th>value</th>"
        pageText = pageText+"<tr>\n     <td><b>Build Dimenstions</b></td><td>"+str(gPronterPtr.settings.build_dimensions)+"</td>\n</tr>"
        pageText = pageText+"   <tr>\n     <td><b>Last Bed Temp</b></td><td>"+str(gPronterPtr.settings.last_bed_temperature)+"</td>\n</tr>"
        pageText = pageText+"   <tr>\n     <td><b>Last File Path</b></td><td>"+gPronterPtr.settings.last_file_path+"</td>\n</tr>"
        pageText = pageText+"   <tr>\n     <td><b>Last Temperature</b></td><td>"+str(gPronterPtr.settings.last_temperature)+"</td>\n</tr>"
        pageText = pageText+"   <tr>\n     <td><b>Preview Extrusion Width</b></td><td>"+str(gPronterPtr.settings.preview_extrusion_width)+"</td>\n</tr>"
        pageText = pageText+"   <tr>\n     <td><b>Filename</b></td><td>"+str(gPronterPtr.filename)+"</td></tr></div>"
        pageText = pageText+PrintFooter()
        return pageText
    index.exposed = True

class LogPage(object):
    def __init__(self):
        self.name = "<div id='title'>Pronterface Console</div>"

    def index(self):
        pageText = "<html><head><meta http-equiv='refresh' content='"+str(gLogRefresh)+"'></head><body>"
        pageText+="<div id='status'>"
        pageText+=gPronterPtr.status.GetStatusText()
        pageText+="</div>"
        pageText = pageText+"<div id='console'>"+gWeblog+"</div>"
        pageText = pageText+"</body></html>"
        return pageText
    index.exposed = True

class ConsolePage(object):
    def __init__(self):
        self.name = "<div id='title'>Pronterface Settings</div>"

    def index(self):
        pageText = PrintHeader()+self.name+PrintMenu()
        pageText+="<div id='logframe'><iframe src='/logpage' width='100%' height='100%'>iFraming Not Supported?? No log for you.</iframe></div>"
        pageText+=PrintFooter()
        return pageText
    index.exposed = True

class ConnectButton(object):
    def index(self):
        #handle connect push, then reload page
        gPronterPtr.connect(0)
        return ReloadPage("Connect...")
    index.exposed = True
    index._cp_config = {'tools.basic_auth.on': True,
        'tools.basic_auth.realm': 'My Print Server',
        'tools.basic_auth.users': users,
        'tools.basic_auth.encrypt': clear_text}

class DisconnectButton(object):
    def index(self):
        #handle connect push, then reload page
        gPronterPtr.disconnect(0)
        return ReloadPage("Disconnect...")
    index.exposed = True
    index._cp_config = {'tools.basic_auth.on': True,
        'tools.basic_auth.realm': 'My Print Server',
        'tools.basic_auth.users': users,
        'tools.basic_auth.encrypt': clear_text}

class ResetButton(object):
    def index(self):
        #handle connect push, then reload page
        gPronterPtr.reset(0)
        return ReloadPage("Reset...")
    index.exposed = True
    index._cp_config = {'tools.basic_auth.on': True,
        'tools.basic_auth.realm': 'My Print Server',
        'tools.basic_auth.users': users,
        'tools.basic_auth.encrypt': clear_text}

class PrintButton(object):
    def index(self):
        #handle connect push, then reload page
        gPronterPtr.printfile(0)
        return ReloadPage("Print...")
    index.exposed = True
    index._cp_config = {'tools.basic_auth.on': True,
        'tools.basic_auth.realm': 'My Print Server',
        'tools.basic_auth.users': users,
        'tools.basic_auth.encrypt': clear_text}

class PauseButton(object):
    def index(self):
        #handle connect push, then reload page
        gPronterPtr.pause(0)
        return ReloadPage("Pause...")
    index.exposed = True
    index._cp_config = {'tools.basic_auth.on': True,
        'tools.basic_auth.realm': 'My Print Server',
        'tools.basic_auth.users': users,
        'tools.basic_auth.encrypt': clear_text}

class MoveButton(object):
    def axis(self, *args):
        if not args:
            raise cherrypy.HTTPError(400, "No Move Command Provided!")
        margs = list(args)
        axis = margs.pop(0)
        if(margs and axis == "x"):
            distance = margs.pop(0)
            gPronterPtr.onecmd('move X %s' % distance)
            return ReloadPage("Moving X Axis " + str(distance))
        if(margs and axis == "y"):
            distance = margs.pop(0)
            gPronterPtr.onecmd('move Y %s' % distance)
            return ReloadPage("Moving Y Axis " + str(distance))
        if(margs and axis == "z"):
            distance = margs.pop(0)
            gPronterPtr.onecmd('move Z %s' % distance)
            return ReloadPage("Moving Z Axis " + str(distance))
        raise cherrypy.HTTPError(400, "Unmached Move Command!")
    axis.exposed = True
    axis._cp_config = {'tools.basic_auth.on': True,
        'tools.basic_auth.realm': 'My Print Server',
        'tools.basic_auth.users': users,
        'tools.basic_auth.encrypt': clear_text}

class CustomButton(object):
    def button(self, *args):
        if not args:
            raise cherrypy.HTTPError(400, "No Custom Command Provided!")
        margs = list(args)
        command = margs.pop(0)
        if(command):
            gPronterPtr.onecmd(command)
            return ReloadPage(str(command))
    button.exposed = True
    button._cp_config = {'tools.basic_auth.on': True,
        'tools.basic_auth.realm': 'My Print Server',
        'tools.basic_auth.users': users,
        'tools.basic_auth.encrypt': clear_text}

class HomeButton(object):
    def axis(self, *args):
        if not args:
            raise cherrypy.HTTPError(400, "No Axis Provided!")
        margs = list(args)
        taxis = margs.pop(0)
        if(taxis == "x"):
            gPronterPtr.onecmd('home X')
            return ReloadPage("Home X")
        if(taxis == "y"):
            gPronterPtr.onecmd('home Y')
            return ReloadPage("Home Y")
        if(taxis == "z"):
            gPronterPtr.onecmd('home Z')
            return ReloadPage("Home Z")
        if(taxis == "all"):
            gPronterPtr.onecmd('home')
            return ReloadPage("Home All")

    axis.exposed = True
    axis._cp_config = {'tools.basic_auth.on': True,
        'tools.basic_auth.realm': 'My Print Server',
        'tools.basic_auth.users': users,
        'tools.basic_auth.encrypt': clear_text}

class XMLstatus(object):
    def index(self):
        #handle connect push, then reload page
        txt='<?xml version = "1.0"?>\n<pronterface>\n'
        state = "Offline"
        if gPronterPtr.statuscheck or gPronterPtr.p.online:
            state = "Idle"
        if gPronterPtr.sdprinting:
            state = "SDPrinting"
        if gPronterPtr.p.printing:
            state = "Printing"
        if gPronterPtr.paused:
            state = "Paused"

        txt = txt+'<state>'+state+'</state>\n'
        txt = txt+'<file>'+str(gPronterPtr.filename)+'</file>\n'
        txt = txt+'<status>'+str(gPronterPtr.status.GetStatusText())+'</status>\n'
        try:
            temp = str(float(filter(lambda x:x.startswith("T:"), gPronterPtr.tempreport.split())[0].split(":")[1]))
            txt = txt+'<hotend>'+temp+'</hotend>\n'
        except:
            txt = txt+'<hotend>NA</hotend>\n'
            pass
        try:
            temp = str(float(filter(lambda x:x.startswith("B:"), gPronterPtr.tempreport.split())[0].split(":")[1]))
            txt = txt+'<bed>'+temp+'</bed>\n'
        except:
            txt = txt+'<bed>NA</bed>\n'
            pass
        if gPronterPtr.sdprinting:
            fractioncomplete = float(gPronterPtr.percentdone/100.0)
            txt+= _("<progress>%04.2f") % (gPronterPtr.percentdone,)
            txt+="</progress>\n"
        elif gPronterPtr.p.printing:
            fractioncomplete = float(gPronterPtr.p.queueindex)/len(gPronterPtr.p.mainqueue)
            txt+= _("<progress>%04.2f") % (100*float(gPronterPtr.p.queueindex)/len(gPronterPtr.p.mainqueue),)
            txt+="</progress>\n"
        else:
            txt+="<progress>NA</progress>\n"
        txt+='</pronterface>'
        return txt
    index.exposed = True

class WebInterface(object):

    def __init__(self, pface):
        if (sys.version_info[1] > 6):
            # 'allow_no_value' wasn't added until 2.7
            config = ConfigParser.SafeConfigParser(allow_no_value = True)
        else:
            config = ConfigParser.SafeConfigParser()
        config.read(configfile(pface.web_auth_config or 'auth.config'))
        users[config.get("user", "user")] = config.get("user", "pass")
        self.pface = pface
        global gPronterPtr
        global gWeblog
        self.name = "<div id='title'>Pronterface Web-Interface</div>"
        gWeblog = ""
        gPronterPtr = self.pface

    settings = SettingsPage()
    logpage  = LogPage()
    console = ConsolePage()

    #actions
    connect = ConnectButton()
    disconnect = DisconnectButton()
    reset = ResetButton()
    printbutton = PrintButton()
    pausebutton = PrintButton()
    status = XMLstatus()
    home = HomeButton()
    move = MoveButton()
    custom =CustomButton()

    def index(self):
        pageText = PrintHeader()+self.name+PrintMenu()
        pageText+="<div id='content'>\n"
        pageText+="<div id='controls'>\n"
        pageText+="<ul><li><a href='/connect'>Connect</a></li>\n"
        pageText+="<li><a href='/disconnect'>Disconnect</a></li>\n"
        pageText+="<li><a href='/reset'>Reset</a></li>\n"
        pageText+="<li><a href='/printbutton'>Print</a></li>\n"
        pageText+="<li><a href='/pausebutton'>Pause</a></li>\n"

        for i in gPronterPtr.cpbuttons:
            pageText+="<li><a href='/custom/button/"+i[1]+"'>"+i[0]+"</a></li>\n"

        #for i in gPronterPtr.custombuttons:
        #    print(str(i));

        pageText+="</ul>\n"
        pageText+="</div>\n"
        pageText+="<div id='gui'>\n"
        pageText+="<div id='control_xy'>"
        pageText+="<img src='/images/control_xy.png' usemap='#xymap'/>"
        pageText+='<map name = "xymap">'

        pageText+='<area shape = "rect" coords = "8, 5, 51, 48" href = "/home/axis/x" alt = "X Home" title = "X Home"    />'
        pageText+='<area shape = "rect" coords = "195, 6, 236, 46" href = "/home/axis/y" alt = "Y Home" title = "Y Home"    />'
        pageText+='<area shape = "rect" coords = "7, 192, 48, 232" href = "/home/axis/all" alt = "All Home" title = "All Home"    />'
        pageText+='<area shape = "rect" coords = "194, 192, 235, 232" href = "/home/axis/z" alt = "Z Home" title = "Z Home"    />'
        pageText+='<area shape = "rect" coords = "62, 7, 185, 34" href = "/move/axis/y/100" alt = "Y 100" title = "Y 100"    />'
        pageText+='<area shape = "rect" coords = "68, 34, 175, 61" href = "/move/axis/y/10" alt = "Y 10" title = "Y 10"    />'
        pageText+='<area shape = "rect" coords = "80, 60, 163, 84" href = "/move/axis/y/1" alt = "Y 1" title = "Y 1"    />'
        pageText+='<area shape = "rect" coords = "106, 83, 138, 107" href = "/move/axis/y/.1" alt = "Y .1" title = "Y .1"    />'
        pageText+='<area shape = "rect" coords = "110, 135, 142, 159" href = "/move/axis/y/-.1" alt = "Y -.1" title = "Y -.1"    />'
        pageText+='<area shape = "rect" coords = "81, 157, 169, 181" href = "/move/axis/y/-1" alt = "Y -1" title = "Y -1"    />'
        pageText+='<area shape = "rect" coords = "69, 180, 178, 206" href = "/move/axis/y/-10" alt = "Y -10" title = "Y -10"    />'
        pageText+='<area shape = "rect" coords = "60, 205, 186, 231" href = "/move/axis/y/-100" alt = "Y -100" title = "Y -100"    />'
        pageText+='<area shape = "rect" coords = "11, 53, 37, 179" href = "/move/axis/x/-100" alt = "X -100" title = "X -100"    />'
        pageText+='<area shape = "rect" coords = "210, 59, 236, 185" href = "/move/axis/x/100" alt = "X 100" title = "X 100"    />'
        pageText+='<area shape = "rect" coords = "38, 60, 64, 172" href = "/move/axis/x/-10" alt = "X -10" title = "X -10"    />'
        pageText+='<area shape = "rect" coords = "185, 66, 211, 178" href = "/move/axis/x/10" alt = "X 10" title = "X 10"    />'
        pageText+='<area shape = "rect" coords = "62, 84, 83, 157" href = "/move/axis/x/-1" alt = "X -1" title = "X -1"    />'
        pageText+='<area shape = "rect" coords = "163, 87, 187, 160" href = "/move/axis/x/1" alt = "X 1" title = "X 1"    />'
        pageText+='<area shape = "rect" coords = "82, 104, 110, 139" href = "/move/axis/x/-.1" alt = "X -.1" title = "X -.1"    />'
        pageText+='<area shape = "rect" coords = "137, 105, 165, 140" href = "/move/axis/x/.1" alt = "X .1" title = "X .1"    />'

        pageText+="</map>"
        pageText+="</div>\n" #endxy
        pageText+="<div id='control_z'>"
        pageText+="<img src='/images/control_z.png' usemap='#zmap'/>"
        pageText+='<map name = "zmap">'
        pageText+='<area shape = "rect" coords = "4, 35, 54, 64" href = "/move/axis/z/10" alt = "Z 10" title = "Z 10"    />'
        pageText+='<area shape = "rect" coords = "4, 60, 54, 89" href = "/move/axis/z/1" alt = "Z 1" title = "Z 1"    />'
        pageText+='<area shape = "rect" coords = "4, 87, 54, 116" href = "/move/axis/z/.1" alt = "Z .1" title = "Z .1"    />'
        pageText+='<area shape = "rect" coords = "4, 121, 54, 150" href = "/move/axis/z/-.1" alt = "Z -.1" title = "Z -.1"    />'
        pageText+='<area shape = "rect" coords = "4, 147, 54, 176" href = "/move/axis/z/-1" alt = "Z -1" title = "Z -1"    />'
        pageText+='<area shape = "rect" coords = "4, 173, 54, 202" href = "/move/axis/z/-10" alt = "Z -10" title = "Z -10"    />'
        pageText+="</map>"
        #TODO Map Z Moves
        pageText+="</div>\n" #endz
        pageText+="</div>\n" #endgui
        pageText+="</div>\n" #endcontent
        pageText+="</br>\n"

       # Temp Control TBD
       # pageText+="<div id='temp'>"
       # pageText+="<div id='tempmenu'>"
       # pageText+="<ul><li><b>Heater Temp:</b></li><li><a href='/off'>OFF</a></li><li><a href='/185'>185 (PLA)</a></li><li><a href='/240'>240 (ABS)</a></li></ul>"
       # pageText+="</div>"
       # pageText+="<div id='tempmenu'>"
       # pageText+="<ul><li><b>Bed Temp:</b></li><li><a href='/off'>OFF</a></li><li><a href='/185'>185 (PLA)</a></li><li><a href='/240'>240 (ABS)</a></li></ul>"
       # pageText+="</div>"
       # pageText+="</div>"

        pageText = pageText+"<div id='file'>File Loaded: <i>"+str(gPronterPtr.filename)+"</i></div>"
        pageText+="<div id='logframe'><iframe src='/logpage' width='100%' height='100%'>iFraming Not Supported?? No log for you.</iframe></div>"
        pageText+=PrintFooter()
        return pageText

    def AddLog(self, log):
        global gWeblog
        gWeblog = gWeblog+"</br>"+log
    def AppendLog(self, log):
        global gWeblog
        gWeblog = re.sub("\n", "</br>", gWeblog)+log
    index.exposed = True

class WebInterfaceStub(object):
    def index(self):
        return "<b>Web Interface Must be launched by running Pronterface!</b>"
    index.exposed = True

def KillWebInterfaceThread():
    cherrypy.engine.exit()

def StartWebInterfaceThread(webInterface):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    cherrypy.config.update({'engine.autoreload_on':False})
    cherrypy.config.update(configfile(webInterface.pface.web_config or "http.config"))
    conf = {'/css/style.css': {'tools.staticfile.on': True,
                      'tools.staticfile.filename': sharedfile('css/style.css'),
                     },
             '/images/control_xy.png': {'tools.staticfile.on': True,
                      'tools.staticfile.filename': imagefile('control_xy.png'),
                     },
             '/images/control_z.png': {'tools.staticfile.on': True,
                      'tools.staticfile.filename': imagefile('control_z.png'),
                     }}
    cherrypy.config.update(configfile(webInterface.pface.web_config or "http.config"))
    cherrypy.quickstart(webInterface, '/', config = conf)

if __name__ == '__main__':
    cherrypy.config.update(configfile("http.config"))
    cherrypy.quickstart(WebInterfaceStub())
