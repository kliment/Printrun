#!/usr/bin/python
import cherrypy, pronterface, re
import os.path

def PrintHeader():
    return '<html>\n<head>\n<title>Pronterface-Web</title>\n<link rel="stylesheet" type="text/css" href="/css/style.css" type="text/css"></link>\n</head>\n<body>\n'

def PrintMenu():
    return '<div id="mainmenu"><ul><li><a href="/">home</a></li><li><a href="/settings">settings</a></li><li><a href="/console">console</a></li><li><a href="/status">status (XML)</a></li></ul></div>'
    
def PrintFooter():
    return "</body></html>"

def ReloadPage(action):
    return "<html><head><meta http-equiv='refresh' content='0;url=/'></head><body>"+action+"</body></html>"

gPronterPtr = 0
gWeblog     = ""
gLogRefresh =5
class SettingsPage(object):
    def __init__(self):
        self.name="<div id='title'>Pronterface Settings</div>"

    def index(self):
        pageText=PrintHeader()+self.name+PrintMenu()
        pageText=pageText+"<div id='settings'><table>\n<tr><th>setting</th><th>value</th>"
        pageText=pageText+"<tr>\n     <td><b>Build Dimenstions</b></td><td>"+str(gPronterPtr.settings.build_dimensions)+"</td>\n</tr>"
        pageText=pageText+"   <tr>\n     <td><b>Last Bed Temp</b></td><td>"+str(gPronterPtr.settings.last_bed_temperature)+"</td>\n</tr>"
        pageText=pageText+"   <tr>\n     <td><b>Last File Path</b></td><td>"+gPronterPtr.settings.last_file_path+"</td>\n</tr>"
        pageText=pageText+"   <tr>\n     <td><b>Last Temperature</b></td><td>"+str(gPronterPtr.settings.last_temperature)+"</td>\n</tr>"
        pageText=pageText+"   <tr>\n     <td><b>Preview Extrusion Width</b></td><td>"+str(gPronterPtr.settings.preview_extrusion_width)+"</td>\n</tr>"
        pageText=pageText+"   <tr>\n     <td><b>Filename</b></td><td>"+str(gPronterPtr.filename)+"</td></tr></div>"
        pageText=pageText+PrintFooter()
        return pageText
    index.exposed = True

class LogPage(object):
    def __init__(self):
        self.name="<div id='title'>Pronterface Console</div>"

    def index(self):
        pageText="<html><head><meta http-equiv='refresh' content='"+str(gLogRefresh)+"'></head><body>"
        pageText+="<div id='status'>"
        pageText+=gPronterPtr.status.GetStatusText()
        pageText+="</div>"
        pageText=pageText+"<div id='console'>"+gWeblog+"</div>"
        pageText=pageText+"</body></html>"
        return pageText
    index.exposed = True

class ConsolePage(object):
    def __init__(self):
        self.name="<div id='title'>Pronterface Settings</div>"

    def index(self):
        pageText=PrintHeader()+self.name+PrintMenu()
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

class DisconnectButton(object):
    def index(self):
        #handle connect push, then reload page
        gPronterPtr.disconnect(0)
        return ReloadPage("Disconnect...")
    index.exposed = True

class ResetButton(object):
    def index(self):
        #handle connect push, then reload page
        gPronterPtr.reset(0)
        return ReloadPage("Reset...")
    index.exposed = True

class PrintButton(object):
    def index(self):
        #handle connect push, then reload page
        gPronterPtr.printfile(0)
        return ReloadPage("Print...")
    index.exposed = True

class PauseButton(object):
    def index(self):
        #handle connect push, then reload page
        gPronterPtr.pause(0)
        return ReloadPage("Pause...")
    index.exposed = True

class XMLstatus(object):
    def index(self):
        #handle connect push, then reload page
        return '<?xml version="1.0"?>\n<xml>\n   <status>'+gPronterPtr.status.GetStatusText()+'</status>\n</xml>';
    index.exposed = True

class WebInterface(object):
    
    def __init__(self, pface):
        self.pface = pface
        global gPronterPtr
        global gWeblog
        self.name="<div id='title'>Pronterface Web-Interface</div>"
        gWeblog = "Connecting web interface to pronterface..."
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
    
    def index(self):
        pageText=PrintHeader()+self.name+PrintMenu()
        pageText+="<div id='controls'>"
        pageText+="<ul><li><a href='/connect'>Connect</a></li>"
        pageText+="<li><a href='/disconnect'>Disconnect</a></li>"
        pageText+="<li><a href='/reset'>Reset</a></li>"
        pageText+="<li><a href='/printbutton'>Print</a></li>"
        pageText+="<li><a href='/pausebutton'>Pause</a></li></ul>"
        pageText+="</div>"
        pageText=pageText+"<div id='file'>File Loaded: <i>"+str(gPronterPtr.filename)+"</i></div>"
        pageText+="<div id='logframe'><iframe src='/logpage' width='100%' height='100%'>iFraming Not Supported?? No log for you.</iframe></div>"
        pageText+=PrintFooter()
        return pageText

    def AddLog(self, log):
        global gWeblog
        gWeblog=gWeblog+"</br>"+log
    def AppendLog(self, log):
        global gWeblog
        gWeblog=re.sub("\n", "</br>", gWeblog)+log
    index.exposed = True

class WebInterfaceStub(object):
    def index(self):
        return "<b>Web Interface Must be launched by running Pronterface!</b>"
    index.exposed = True

def StartWebInterfaceThread(webInterface):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    cherrypy.config.update({'engine.autoreload_on':False})
    cherrypy.config.update("http.config")
    conf = {'/css/style.css': {'tools.staticfile.on': True,
                      'tools.staticfile.filename': os.path.join(current_dir, 'css/style.css'),
                     }}
    cherrypy.config.update("http.config")
    cherrypy.quickstart(webInterface, '/', config=conf)
    
if __name__ == '__main__':
    cherrypy.config.update("http.config")
    cherrypy.quickstart(WebInterfaceStub())