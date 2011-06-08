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

class PronterWindow(wx.Frame):
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
        self.popmenu()
        self.popwindow()
        self.recvlisteners=[]
        self.p.recvcb=self.recvcb
        self.sdfiles=[]
        self.listing=0
        self.sdprinting=0
        self.temps={"pla":"210","abs":"230","off":"0"}
        self.bedtemps={"pla":"60","abs":"110","off":"0"}
        self.percentdone=0
        
        
    #Commands to implement:
    #gcodes(console)   move/extrude/settemp/bedtemp/extrude/reverse(control panel)
    #upload
    #help        
        
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
        self.serialport = wx.ComboBox(self.panel, -1,
                choices=self.scanserial(),
                style=wx.CB_SIMPLE|wx.CB_DROPDOWN|wx.CB_SORT, pos=(50,0))
        wx.StaticText(self.panel,-1,"@",pos=(250,5))
        self.baud = wx.ComboBox(self.panel, -1,
                choices=["2400", "9600", "19200", "38400", "57600", "115200"],
                style=wx.CB_SIMPLE|wx.CB_DROPDOWN|wx.CB_SORT, size=(90,30),pos=(275,0))
        self.connectbtn=wx.Button(self.panel,-1,"Connect",pos=(380,0))
        self.connectbtn.SetToolTipString("Connect to the printer")
        self.connectbtn.Bind(wx.EVT_BUTTON,self.connect)
        self.disconnectbtn=wx.Button(self.panel,-1,"Disconnect",pos=(470,0))
        self.disconnectbtn.Bind(wx.EVT_BUTTON,self.disconnect)
        self.resetbtn=wx.Button(self.panel,-1,"Reset",pos=(560,0))
        self.resetbtn.Bind(wx.EVT_BUTTON,self.reset)
        self.loadbtn=wx.Button(self.panel,-1,"Load file",pos=(0,40))
        self.loadbtn.Bind(wx.EVT_BUTTON,self.loadfile)
        self.printbtn=wx.Button(self.panel,-1,"Print",pos=(90,40))
        self.printbtn.Bind(wx.EVT_BUTTON,self.printfile)
        self.uploadbtn=wx.Button(self.panel,-1,"SD Upload",pos=(90,75))
        self.uploadbtn.Bind(wx.EVT_BUTTON,self.upload)
        self.pausebtn=wx.Button(self.panel,-1,"Pause",pos=(180,40))
        self.pausebtn.Bind(wx.EVT_BUTTON,self.pause)
        self.sdprintbtn=wx.Button(self.panel,-1,"SD Print",pos=(180,75))
        self.sdprintbtn.Bind(wx.EVT_BUTTON,self.sdprintfile)
        self.commandbox=wx.TextCtrl(self.panel,size=(250,30),pos=(400,400),style = wx.TE_PROCESS_ENTER)
        self.commandbox.Bind(wx.EVT_TEXT_ENTER,self.sendline)
        self.logbox=wx.TextCtrl(self.panel,size=(350,300),pos=(400,75),style = wx.TE_MULTILINE)
        self.logbox.Disable()
        self.sendbtn=wx.Button(self.panel,-1,"Send",pos=(660,400))
        self.sendbtn.Bind(wx.EVT_BUTTON,self.sendline)
        self.monitorbox=wx.CheckBox(self.panel,-1,"Monitor",pos=(10,430))
        self.monitorbox.Bind(wx.EVT_CHECKBOX,self.setmonitor)
        self.status=self.CreateStatusBar()
        self.status.SetStatusText("Not connected to printer.")
        self.Bind(wx.EVT_CLOSE, self.kill)
        pass
        
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
        if(command[0]=="g" or command[0]=="m"):
            command=command.upper()
        wx.CallAfter(self.logbox.AppendText,">>>"+command+"\n")
        self.p.send_now(command)
        
    def statuschecker(self):
        try:
            while(self.statuscheck):
                string=""
                if(self.p.online):
                    string+="Printer is online."
                string+=(self.tempreport.replace("\r","").replace("T","Hotend").replace("B","Bed").replace("\n","").replace("ok ",""))+" "
                if self.sdprinting:
                    string+= "SD printing:%04.2f %%"%(self.percentdone,)
                if self.p.printing:
                    string+= "printing:%04.2f %%"%(100*float(self.p.queueindex)/len(self.p.mainqueue),)
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
        tstring=l.replace("\n","").replace("\r","")
        print tstring
        if(tstring!="ok"):
            wx.CallAfter(self.logbox.AppendText,tstring+"\n")
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
            (self.capture(skeinforge_craft.writeOutput,self.filename,False))
            #print len(self.cout.getvalue().split())
            self.stopsf=1
        except:
            print "Skeinforge execution failed."
            self.stopsf=1
            raise
        
    def skein_monitor(self):
        while(not self.stopsf):
            try:
                wx.CallAfter(self.status.SetStatusText,"Skeining "+self.cout.getvalue().split("\n")[-1])
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
        
    def upload(self,event):
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
