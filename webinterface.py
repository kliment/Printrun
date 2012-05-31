#!/usr/bin/python
import cherrypy, pronterface, re, ConfigParser, io
import os.path

users = {}

def PrintHeader():
    return '<html>\n<head>\n<title>Pronterface-Web</title>\n<link rel="stylesheet" type="text/css" href="/css/style.css" type="text/css"></link>\n</head>\n<body>\n'

def PrintMenu():
    return '<div id="mainmenu"><ul><li><a href="/">home</a></li><li><a href="/settings">settings</a></li><li><a href="/console">console</a></li><li><a href="/status">status (XML)</a></li></ul></div>'
    
def PrintFooter():
    return "</body></html>"

def ReloadPage(action):
    return "<html><head><meta http-equiv='refresh' content='0;url=/'></head><body>"+action+"</body></html>"

def clear_text(mypass):
    return mypass
    
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

class XMLstatus(object):
    def index(self):
        #handle connect push, then reload page
        txt='<?xml version="1.0"?>\n<pronterface>\n'
        txt=txt+'<file>'+str(gPronterPtr.filename)+'</file>\n'
        txt=txt+'<status>'+str(gPronterPtr.status.GetStatusText())+'</status>\n'
        try:
            temp = str(float(filter(lambda x:x.startswith("T:"),gPronterPtr.tempreport.split())[0].split(":")[1]))
            txt=txt+'<hotend>'+temp+'</hotend>\n'
        except:
            txt=txt+'<hotend>NA</hotend>\n'
            pass
        try:
            temp = str(float(filter(lambda x:x.startswith("B:"),gPronterPtr.tempreport.split())[0].split(":")[1]))
            txt=txt+'<bed>'+temp+'</bed>\n'
        except:
            txt=txt+'<bed>NA</bed>\n'
            pass
        if gPronterPtr.sdprinting:
            fractioncomplete = float(gPronterPtr.percentdone/100.0)
            txt+= _("<progress>%04.2f %%") % (gPronterPtr.percentdone,)
            txt+="</progress>\n"
        elif gPronterPtr.p.printing:
            fractioncomplete = float(gPronterPtr.p.queueindex)/len(gPronterPtr.p.mainqueue)
            txt+= _("<progress>%04.2f %% |") % (100*float(gPronterPtr.p.queueindex)/len(gPronterPtr.p.mainqueue),)
            txt+="</progress>\n"
        else:
            txt+="<progress>NA</progress>\n"
        txt+='</pronterface>'
        return txt
    index.exposed = True

class WebInterface(object):
    
    def __init__(self, pface):
        config = ConfigParser.SafeConfigParser(allow_no_value=True)
        config.read('auth.config')
        users[config.get("user", "user")] = config.get("user", "pass")
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