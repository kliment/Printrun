#!/usr/bin/python
import cherrypy, pronterface

def PrintHeader():
    return "<h3><a href='/'>main</a> | <a href='/settings'>settings</a> </h3>"

pronterPtr = 0
class SettingsPage(object):
    def __init__(self):
        self.name="<h1>Pronterface Settings</h1>"
    def SetPface(self, pface):
        self.pface = pface
    def index(self):
        pageText=self.name+PrintHeader()
        pageText=pageText+"<table><tr><td><b>Build Dimenstions</b></td><td>"+str(pronterPtr.settings.build_dimensions)+"</td></tr>"
        pageText=pageText+"<tr><td><b>Last Bed Temp</b></td><td>"+str(pronterPtr.settings.last_bed_temperature)+"</td></tr>"
        pageText=pageText+"<tr><td><b>Last File Path</b></td><td>"+pronterPtr.settings.last_file_path+"</td></tr>"
        pageText=pageText+"<tr><td><b>Last Temperature</b></td><td>"+str(pronterPtr.settings.last_temperature)+"</td></tr>"
        pageText=pageText+"<tr><td><b>Preview Extrusion Width</b></td><td>"+str(pronterPtr.settings.preview_extrusion_width)+"</td></tr>"
        pageText=pageText+"<tr><td><b>Filename</b></td><td>"+str(pronterPtr.filename)+"</td></tr>"
        return pageText
    index.exposed = True
  
class WebInterface(object):
    def __init__(self, pface):
        self.pface = pface
        self.name="<h1>Pronterface Settings</h1>"
        global pronterPtr
        pronterPtr = self.pface 

    settings = SettingsPage()

    def index(self):
        pageText=self.name+PrintHeader()
        return pageText
    index.exposed = True

class WebInterfaceStub(object):
    def index(self):
        return "<b>Web Interface Must be launched by running Pronterface!</b>"
    index.exposed = True

def StartWebInterfaceThread(pface):
    cherrypy.config.update({'engine.autoreload_on':False})
    cherrypy.config.update("http.config")
    cherrypy.quickstart(WebInterface(pface))
    
if __name__ == '__main__':
    cherrypy.config.update("http.config")
    cherrypy.quickstart(WebInterfaceStub())