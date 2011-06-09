#!/usr/bin/env python
try:
    import wx
except:
    print "WX is not installed. This program requires WX to run."
    raise
import printcore, os, sys, glob, time, threading, traceback, StringIO
thread=threading.Thread
if os.name=="nt":
    try:
        import _winreg
    except:
        pass

import pronsole

def dosify(name):
    return os.path.split(name)[1].split(".")[0][:8]+".g"

class Tee(object):
    def __init__(self, target):
        self.stdout = sys.stdout
        sys.stdout = self
        self.target=target
    def __del__(self):
        sys.stdout = self.stdout
    def write(self, data):
        self.target(data)
        self.stdout.write(data)
    def flush(self):
        self.stdout.flush()


class PronterWindow(wx.Frame,pronsole.pronsole):
    def __init__(self, filename=None,size=(800,500)):
        self.filename=filename
        os.putenv("UBUNTU_MENUPROXY","0")
        wx.Frame.__init__(self,None,title="Printer Interface",size=size);
        self.panel=wx.Panel(self,-1,size=size)
        self.p=printcore.printcore()
        self.statuscheck=False
        self.tempreport=""
        self.monitor=0
        self.paused=False
        xcol=(255,255,128)
        ycol=(180,180,255)
        zcol=(180,255,180)
        self.temps={"pla":"210","abs":"230","off":"0"}
        self.bedtemps={"pla":"60","abs":"110","off":"0"}
        self.cpbuttons=[
        ["X+100",("move X 100"),(0,110),xcol,(55,25)],
        ["X+10",("move X 10"),(0,135),xcol,(55,25)],
        ["X+1",("move X 1"),(0,160),xcol,(55,25)],
        ["X+0.1",("move X 0.1"),(0,185),xcol,(55,25)],
        ["HomeX",("home X"),(0,210),xcol,(55,25)],
        ["X-0.1",("move X -0.1"),(0,235),xcol,(55,25)],
        ["X-1",("move X -1"),(0,260),xcol,(55,25)],
        ["X-10",("move X -10"),(0,285),xcol,(55,25)],
        ["X-100",("move X -100"),(0,310),xcol,(55,25)],
        ["Y+100",("move Y 100"),(55,110),ycol,(55,25)],
        ["Y+10",("move Y 10"),(55,135),ycol,(55,25)],
        ["Y+1",("move Y 1"),(55,160),ycol,(55,25)],
        ["Y+0.1",("move Y 0.1"),(55,185),ycol,(55,25)],
        ["HomeY",("home Y"),(55,210),ycol,(55,25)],
        ["Y-0.1",("move Y -0.1"),(55,235),ycol,(55,25)],
        ["Y-1",("move Y -1"),(55,260),ycol,(55,25)],
        ["Y-10",("move Y -10"),(55,285),ycol,(55,25)],
        ["Y-100",("move Y -100"),(55,310),ycol,(55,25)],
        ["Z+10",("move Z 10"),(110,110+25),zcol,(55,25)],
        ["Z+1",("move Z 1"),(110,135+25),zcol,(55,25)],
        ["Z+0.1",("move Z 0.1"),(110,160+25),zcol,(55,25)],
        ["HomeZ",("home Z"),(110,185+25),zcol,(55,25)],
        ["Z-0.1",("move Z -0.1"),(110,210+25),zcol,(55,25)],
        ["Z-1",("move Z -1"),(110,235+25),zcol,(55,25)],
        ["Z-10",("move Z -10"),(110,260+25),zcol,(55,25)],
        ["Home",("home"),(110,310),(250,250,250),(55,25)],
        ["Extrude",("extrude"),(0,397+1),(200,200,200),(65,25)],
        ["Reverse",("reverse"),(0,397+28),(200,200,200),(65,25)],
        ]
        self.btndict={}
        self.popmenu()
        self.popwindow()
        self.recvlisteners=[]
        self.p.recvcb=self.recvcb
        self.sdfiles=[]
        self.listing=0
        self.sdprinting=0
        self.percentdone=0
        self.t=Tee(self.catchprint)
        self.stdout=sys.stdout
        self.mini=False
        
    
    def do_extrude(self,l=""):
        try:
            if not (l.__class__=="".__class__ or l.__class__==u"".__class__) or (not len(l)):
                l=str(self.edist.GetValue())
            pronsole.pronsole.do_extrude(self,l)
        except:
            raise
    
    def do_reverse(self,l=""):
        try:
            if not (l.__class__=="".__class__ or l.__class__==u"".__class__) or (not len(l)):
                l=str(self.edist.GetValue())
            pronsole.pronsole.do_extrude(self,l)
        except:
            pass
    
    
    def do_settemp(self,l=""):
        try:
            if not (l.__class__=="".__class__ or l.__class__==u"".__class__) or (not len(l)):
                l=self.htemp.GetValue().split()[0]
            l=l.lower().replace(",",".")
            for i in self.temps.keys():
                l=l.replace(i,self.temps[i])
            f=float(l)
            if f>=0:
                if self.p.online:
                    self.p.send_now("M104 S"+l)
                    print "Setting hotend temperature to ",f," degrees Celsius."
                    self.htemp.SetValue(l)
                else:
                    print "Printer is not online."
            else:
                print "You cannot set negative temperatures. To turn the hotend off entirely, set its temperature to 0."
        except:
            print "You must enter a temperature."
    
    def do_bedtemp(self,l=""):
        try:
            if not (l.__class__=="".__class__ or l.__class__==u"".__class__) or (not len(l)):
                l=self.btemp.GetValue().split()[0]
            l=l.lower().replace(",",".")
            for i in self.bedtemps.keys():
                l=l.replace(i,self.bedtemps[i])
            f=float(l)
            if f>=0:
                if self.p.online:
                    self.p.send_now("M140 S"+l)
                    print "Setting bed temperature to ",f," degrees Celsius."
                    self.btemp.SetValue(l)
                else:
                    print "Printer is not online."
            else:
                print "You cannot set negative temperatures. To turn the bed off entirely, set its temperature to 0."
        except:
            print "You must enter a temperature."
            
    
    def catchprint(self,l):
        wx.CallAfter(self.logbox.AppendText,l)
        
    def scanserial(self):
        """scan for available ports. return a list of device names."""
        baselist=[]
        if os.name=="nt":
            try:
                key=_winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE,"HARDWARE\\DEVICEMAP\\SERIALCOMM")
                i=0
                while(1):
                    baselist+=[_winreg.EnumValue(key,i)[1]]
                    i+=1
            except:
                pass
        return baselist+glob.glob('/dev/ttyUSB*') + glob.glob('/dev/ttyACM*') +glob.glob("/dev/tty.*")+glob.glob("/dev/cu.*")+glob.glob("/dev/rfcomm*")
        
    def popmenu(self):
        self.menustrip = wx.MenuBar()
        m = wx.Menu()
        self.Bind(wx.EVT_MENU, self.OnExit, m.Append(wx.ID_EXIT,"Close"," Closes the Window"))
        self.menustrip.Append(m,"&Print")
        self.SetMenuBar(self.menustrip)
        pass
    
    def OnExit(self, event):
        self.Close()
        
    def popwindow(self):
        wx.StaticText(self.panel,-1,"Port:",pos=(0,5))
        scan=self.scanserial()
        self.serialport = wx.ComboBox(self.panel, -1,
                choices=scan,
                style=wx.CB_SIMPLE|wx.CB_DROPDOWN|wx.CB_SORT, pos=(50,0))
        try:
            self.serialport.SetValue(scan[0])
        except:
            pass
        wx.StaticText(self.panel,-1,"@",pos=(250,5))
        self.baud = wx.ComboBox(self.panel, -1,
                choices=["2400", "9600", "19200", "38400", "57600", "115200"],
                style=wx.CB_SIMPLE|wx.CB_DROPDOWN|wx.CB_SORT, size=(90,30),pos=(275,0))
        self.baud.SetValue("115200")
        self.connectbtn=wx.Button(self.panel,-1,"Connect",pos=(380,0))
        self.connectbtn.SetToolTipString("Connect to the printer")
        self.connectbtn.Bind(wx.EVT_BUTTON,self.connect)
        self.disconnectbtn=wx.Button(self.panel,-1,"Disconnect",pos=(470,0))
        self.disconnectbtn.Bind(wx.EVT_BUTTON,self.disconnect)
        self.resetbtn=wx.Button(self.panel,-1,"Reset",pos=(560,0))
        self.resetbtn.Bind(wx.EVT_BUTTON,self.reset)
        self.loadbtn=wx.Button(self.panel,-1,"Load file",pos=(0,40))
        self.loadbtn.Bind(wx.EVT_BUTTON,self.loadfile)
        self.printbtn=wx.Button(self.panel,-1,"Print",pos=(270,40))
        self.printbtn.Bind(wx.EVT_BUTTON,self.printfile)
        self.uploadbtn=wx.Button(self.panel,-1,"SD Upload",pos=(90,40))
        self.uploadbtn.Bind(wx.EVT_BUTTON,self.upload)
        self.pausebtn=wx.Button(self.panel,-1,"Pause",pos=(360,40))
        self.pausebtn.Bind(wx.EVT_BUTTON,self.pause)
        self.sdprintbtn=wx.Button(self.panel,-1,"SD Print",pos=(180,40))
        self.sdprintbtn.Bind(wx.EVT_BUTTON,self.sdprintfile)
        self.commandbox=wx.TextCtrl(self.panel,size=(250,30),pos=(440,420),style = wx.TE_PROCESS_ENTER)
        self.commandbox.Bind(wx.EVT_TEXT_ENTER,self.sendline)
        self.logbox=wx.TextCtrl(self.panel,size=(350,340),pos=(440,75),style = wx.TE_MULTILINE)
        self.logbox.SetEditable(0)
        self.sendbtn=wx.Button(self.panel,-1,"Send",pos=(700,420))
        self.sendbtn.Bind(wx.EVT_BUTTON,self.sendline)
        self.monitorbox=wx.CheckBox(self.panel,-1,"Monitor printer",pos=(500,40))
        self.monitorbox.Bind(wx.EVT_CHECKBOX,self.setmonitor)
        self.status=self.CreateStatusBar()
        self.status.SetStatusText("Not connected to printer.")
        self.Bind(wx.EVT_CLOSE, self.kill)
        for i in self.cpbuttons:
            btn=wx.Button(self.panel,-1,i[0],pos=i[2],size=i[4])
            btn.SetBackgroundColour(i[3])
            btn.SetForegroundColour("black")
            btn.properties=i
            btn.Bind(wx.EVT_BUTTON,self.procbutton)
            self.btndict[i[1]]=btn
        wx.StaticText(self.panel,-1,"Heater:",pos=(0,345))
        self.htemp=wx.ComboBox(self.panel, -1,
                choices=[self.temps[i]+" ("+i+")" for i in sorted(self.temps.keys())],
                style=wx.CB_SIMPLE|wx.CB_DROPDOWN, size=(90,30),pos=(45,337))
        self.htemp.SetValue("0")
        self.settbtn=wx.Button(self.panel,-1,"Set",size=(30,-1),pos=(135,337))
        self.settbtn.Bind(wx.EVT_BUTTON,self.do_settemp)
        
        wx.StaticText(self.panel,-1,"Bed:",pos=(0,375))
        self.btemp=wx.ComboBox(self.panel, -1,
                choices=[self.temps[i]+" ("+i+")" for i in sorted(self.temps.keys())],
                style=wx.CB_SIMPLE|wx.CB_DROPDOWN, size=(90,30),pos=(45,367))
        self.btemp.SetValue("0")
        self.setbbtn=wx.Button(self.panel,-1,"Set",size=(30,-1),pos=(135,367))
        self.setbbtn.Bind(wx.EVT_BUTTON,self.do_bedtemp)
        
        self.edist=wx.SpinCtrl(self.panel,-1,"5",min=0,max=1000,size=(60,30),pos=(70,397+10))
        wx.StaticText(self.panel,-1,"mm",pos=(130,407+10))
        self.minibtn=wx.Button(self.panel,-1,"Mini mode",pos=(690,0))
        self.minibtn.Bind(wx.EVT_BUTTON,self.toggleview)
        
        pass
        
    def toggleview(self,e):
        if(self.mini):
            self.mini=False
            self.SetSize((800,500))
            self.minibtn.SetLabel("Mini mode")
            
        else:
            self.mini=True
            self.SetSize((800,120))
            self.minibtn.SetLabel("Full mode")
                
        
    def procbutton(self,e):
        try:
            self.onecmd(e.GetEventObject().properties[1])
        except:
            print "event object missing"
            raise
        
    def kill(self,e):
        self.statuscheck=0
        self.p.recvcb=None
        self.p.disconnect()
        self.Destroy()
        
        
    def setmonitor(self,e):
        self.monitor=self.monitorbox.GetValue()
        
    def sendline(self,e):
        command=self.commandbox.GetValue()
        if not len(command):
            return
        wx.CallAfter(self.logbox.AppendText,">>>"+command+"\n")
        self.onecmd(command)
        
    def statuschecker(self):
        try:
            while(self.statuscheck):
                string=""
                if(self.p.online):
                    string+="Printer is online. "
                string+=(self.tempreport.replace("\r","").replace("T","Hotend").replace("B","Bed").replace("\n","").replace("ok ",""))+" "
                if self.sdprinting:
                    string+= " SD printing:%04.2f %%"%(self.percentdone,)
                if self.p.printing:
                    string+= " Printing:%04.2f %%"%(100*float(self.p.queueindex)/len(self.p.mainqueue),)
                wx.CallAfter(self.status.SetStatusText,string)
                if(self.monitor and self.p.online):
                    if self.sdprinting:
                        self.p.send_now("M27")
                    self.p.send_now("M105")
                time.sleep(3)
            wx.CallAfter(self.status.SetStatusText,"Not connected to printer.")
        except:
            pass #if window has been closed
    def capture(self, func, *args, **kwargs):
        stdout=sys.stdout
        cout=None
        try:
            cout=self.cout
        except:
            pass
        if cout is None:
            cout=cStringIO.StringIO()
        
        sys.stdout=cout
        retval=None
        try:
            retval=func(*args,**kwargs)
        except:
            traceback.print_exc()
        sys.stdout=stdout
        return retval

    def recvcb(self,l):
        if "T:" in l:
            self.tempreport=l
        tstring=l.rstrip()
        #print tstring
        if(tstring!="ok"):
            print tstring
            #wx.CallAfter(self.logbox.AppendText,tstring+"\n")
        for i in self.recvlisteners:
            i(l)
    
    def listfiles(self,line):
        if "Begin file list" in line:
            self.listing=1
        elif "End file list" in line:
            self.listing=0
            self.recvlisteners.remove(self.listfiles)
            wx.CallAfter(self.filesloaded)
        elif self.listing:
            self.sdfiles+=[line.replace("\n","").replace("\r","").lower()]
        
    def waitforsdresponse(self,l):
        if "file.open failed" in l:
            wx.CallAfter(self.status.SetStatusText,"Opening file failed.")
            self.recvlisteners.remove(self.waitforsdresponse)
            return
        if "File opened" in l:
            wx.CallAfter(self.status.SetStatusText,l)
        if "File selected" in l:
            wx.CallAfter(self.status.SetStatusText,"Starting print")
            self.sdprinting=1
            self.p.send_now("M24")
            return
        if "Done printing file" in l:
            wx.CallAfter(self.status.SetStatusText,l)
            self.sdprinting=0
            self.recvlisteners.remove(self.waitforsdresponse)
            return
        if "SD printing byte" in l:
            #M27 handler
            try:
                resp=l.split()
                vals=resp[-1].split("/")
                self.percentdone=100.0*int(vals[0])/int(vals[1])
            except:
                pass
    
        
        
    def filesloaded(self):
        dlg=wx.SingleChoiceDialog(self, "Select the file to print", "Pick SD file", self.sdfiles)
        if(dlg.ShowModal()==wx.ID_OK):
            target=dlg.GetStringSelection()
            if len(target):
                self.recvlisteners+=[self.waitforsdresponse]
                self.p.send_now("M23 "+target.lower())
        
        #print self.sdfiles
        pass

    def getfiles(self):
        if not self.p.online:
            self.sdfiles=[]
            return
        self.listing=0
        self.sdfiles=[]
        self.recvlisteners+=[self.listfiles]
        self.p.send_now("M20")
        
    def skein_func(self):
        try:
            from skeinforge.skeinforge_application.skeinforge_utilities import skeinforge_craft
            from skeinforge.skeinforge_application import skeinforge
            from skeinforge.fabmetheus_utilities import settings
            skeinforge_craft.writeOutput(self.filename,False)
            #print len(self.cout.getvalue().split())
            self.stopsf=1
        except:
            print "Skeinforge execution failed."
            self.stopsf=1
            raise
        
    def skein_monitor(self):
        while(not self.stopsf):
            try:
                wx.CallAfter(self.status.SetStatusText,"Skeining...")#+self.cout.getvalue().split("\n")[-1])
            except:
                pass
            time.sleep(0.1)
        fn=self.filename
        try:
            self.filename=self.filename.replace(".stl","_export.gcode")
            self.f=[i.replace("\n","").replace("\r","") for i in open(self.filename)]
            wx.CallAfter(self.status.SetStatusText,"Loaded "+self.filename+", %d lines"%(len(self.f),))
        except:
            self.filename=fn
        
    def skein(self,filename):
        print "Skeining "+filename
        if not os.path.exists("skeinforge"):
            print "Skeinforge not found. \nPlease copy Skeinforge into a directory named \"skeinforge\" in the same directory as this file."
            return
        if not os.path.exists("skeinforge/__init__.py"):
            with open("skeinforge/__init__.py","w"):
                pass
        self.cout=StringIO.StringIO()
        self.filename=filename
        self.stopsf=0
        thread(target=self.skein_func).start()
        thread(target=self.skein_monitor).start()
        
    def loadfile(self,event):
        dlg=wx.FileDialog(self,"Open file to print")
        dlg.SetWildcard("STL and GCODE files (;*.gcode;*.g;*.stl;)")
        if(dlg.ShowModal() == wx.ID_OK):
            name=dlg.GetPath()
            if not(os.path.exists(name)):
                self.status.SetStatusText("File not found!")
                return
            if name.endswith(".stl"):
                self.skein(name)
            else:
                self.f=[i.replace("\n","").replace("\r","") for i in open(name)]
                self.filename=name
                self.status.SetStatusText("Loaded "+name+", %d lines"%(len(self.f),))
                
    def printfile(self,event):
        if self.f is None or not len(self.f):
            wx.CallAfter(self.status.SetStatusText,"No file loaded. Please use load first.")
            return
        if not self.p.online:
            wx.CallAfter(self.status.SetStatusText,"Not connected to printer.")
            return
        self.p.startprint(self.f)
        
    def endupload(self):
        self.p.send_now("M29 ")
        wx.CallAfter(self.status.SetStatusText,"File upload complete")
        time.sleep(0.5)
        self.p.clear=True
        self.uploading=False
        
    def uploadtrigger(self,l):
        if "Writing to file" in l:
            self.uploading=True
            self.p.startprint(self.f)
            self.p.endcb=self.endupload
            self.recvlisteners.remove(self.uploadtrigger)
        elif "open failed, File" in l:
            self.recvlisteners.remove(self.uploadtrigger)
        
    def upload(self,event):
        if not len(self.f):
            return
        if not self.p.online:
            return
        dlg=wx.TextEntryDialog(self,"Enter a target filename in 8.3 format:","Pick SD filename",dosify(self.filename))
        if dlg.ShowModal()==wx.ID_OK:
            self.p.send_now("M28 "+dlg.GetValue())
            self.recvlisteners+=[self.uploadtrigger]
        pass
        
    def pause(self,event):
        if not self.paused:
            if self.sdprinting:
                self.p.send_now("M25")
            else:
                if(not self.p.printing):
                    #print "Not printing, cannot pause."
                    return
                self.p.pause()
            self.paused=True
            self.pausebtn.SetLabel("Resume")
        else:
            self.paused=False
            if self.sdprinting:
                self.p.send_now("M24")
            else:
                self.p.resume()
            self.pausebtn.SetLabel("Pause")
    
        
    def sdprintfile(self,event):
        threading.Thread(target=self.getfiles).start()
        pass
        
    def connect(self,event):
        port=None
        try:
            port=self.scanserial()[0]
        except:
            pass
        if self.serialport.GetValue()!="":
            port=self.serialport.GetValue()
        baud=115200
        try:
            baud=int(self.baud.GetValue())
        except:
            pass
        self.p.connect(port,baud)
        self.statuscheck=True
        threading.Thread(target=self.statuschecker).start()
        
    def disconnect(self,event):
        self.p.disconnect()
        self.statuscheck=False
    
    def reset(self,event):
        dlg=wx.MessageDialog(self,"Are you sure you want to reset the printer?","Reset?",wx.YES|wx.NO)
        if dlg.ShowModal()==wx.ID_YES:
            self.p.reset()
        
        
if __name__ == '__main__':
    app = wx.App(False)
    main = PronterWindow()
    main.Show()
    app.MainLoop()
