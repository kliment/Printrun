#!/usr/bin/env python

# Set up Internationalization using gettext
# searching for installed locales on /usr/share; uses relative folder if not found (windows)
import os, gettext

if os.path.exists('/usr/share/pronterface/locale'):
    gettext.install('pronterface', '/usr/share/pronterface/locale', unicode=1)
else: 
    gettext.install('pronterface', './locale', unicode=1)

try:
    import wx
except:
    print _("WX is not installed. This program requires WX to run.")
    raise
import printcore, sys, glob, time, threading, traceback, StringIO, gviz, traceback, cStringIO
try:
    os.chdir(os.path.split(__file__)[0])
except:
    pass
    
thread=threading.Thread
winsize=(800,500)
if os.name=="nt":
    winsize=(800,530)
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
    def __init__(self, filename=None,size=winsize):
        pronsole.pronsole.__init__(self)
        self.settings.last_file_path = ""
        self.settings.last_temperature = 0.0
        self.settings.last_bed_temperature = 0.0
        self.settings.bed_size_x = 200.
        self.settings.bed_size_y = 200.
        self.settings.preview_grid_step1 = 10.
        self.settings.preview_grid_step2 = 50.
        self.settings.preview_extrusion_width = 0.5
        self.filename=filename
        os.putenv("UBUNTU_MENUPROXY","0")
        wx.Frame.__init__(self,None,title=_("Printer Interface"),size=size);
        self.SetIcon(wx.Icon("P-face.ico",wx.BITMAP_TYPE_ICO))
        self.panel=wx.Panel(self,-1,size=size)
        self.statuscheck=False
        self.tempreport=""
        self.monitor=0
        self.monitor_interval=3
        self.paused=False
        xcol=(245,245,108)
        ycol=(180,180,255)
        zcol=(180,255,180)
        self.cpbuttons=[
        [_("X+100"),("move X 100"),(2,0),xcol,(1,3)],
        [_("X+10"),("move X 10"),(3,0),xcol,(1,3)],
        [_("X+1"),("move X 1"),(4,0),xcol,(1,3)],
        [_("X+0.1"),("move X 0.1"),(5,0),xcol,(1,3)],
        [_("HomeX"),("home X"),(6,0),(205,205,78),(1,3)],
        [_("X-0.1"),("move X -0.1"),(7,0),xcol,(1,3)],
        [_("X-1"),("move X -1"),(8,0),xcol,(1,3)],
        [_("X-10"),("move X -10"),(9,0),xcol,(1,3)],
        [_("X-100"),("move X -100"),(10,0),xcol,(1,3)],
        [_("Y+100"),("move Y 100"),(2,3),ycol,(1,3)],
        [_("Y+10"),("move Y 10"),(3,3),ycol,(1,3)],
        [_("Y+1"),("move Y 1"),(4,3),ycol,(1,3)],
        [_("Y+0.1"),("move Y 0.1"),(5,3),ycol,(1,3)],
        [_("HomeY"),("home Y"),(6,3),(150,150,205),(1,3)],
        [_("Y-0.1"),("move Y -0.1"),(7,3),ycol,(1,3)],
        [_("Y-1"),("move Y -1"),(8,3),ycol,(1,3)],
        [_("Y-10"),("move Y -10"),(9,3),ycol,(1,3)],
        [_("Y-100"),("move Y -100"),(10,3),ycol,(1,3)],
        [_("Motors off"),("M84"),(2,6),(250,250,250),(1,3)],
        [_("Z+10"),("move Z 10"),(3,6),zcol,(1,3)],
        [_("Z+1"),("move Z 1"),(4,6),zcol,(1,3)],
        [_("Z+0.1"),("move Z 0.1"),(5,6),zcol,(1,3)],
        [_("HomeZ"),("home Z"),(6,6),(150,205,150),(1,3)],
        [_("Z-0.1"),("move Z -0.1"),(7,6),zcol,(1,3)],
        [_("Z-1"),("move Z -1"),(8,6),zcol,(1,3)],
        [_("Z-10"),("move Z -10"),(9,6),zcol,(1,3)],
        [_("Home"),("home"),(10,6),(250,250,250),(1,3)],
        [_("Check temp"),("M105"),(11,6),(225,200,200),(1,3)],
        [_("Extrude"),("extrude"),(13,0),(225,200,200),(1,2)],
        [_("Reverse"),("reverse"),(14,0),(225,200,200),(1,2)],
        ]
        self.custombuttons=[]
        self.btndict={}
        self.parse_cmdline(sys.argv[1:])
        customdict={}
        try:
            execfile("custombtn.txt",customdict)
            if len(customdict["btns"]): 
                if not len(self.custombuttons):
                    try:
                        self.custombuttons = customdict["btns"]
                        for n in xrange(len(self.custombuttons)):
                            self.cbutton_save(n,self.custombuttons[n])
                        os.rename("custombtn.txt","custombtn.old")
                        rco=open("custombtn.txt","w")
                        rco.write(_("# I moved all your custom buttons into .pronsolerc.\n# Please don't add them here any more.\n# Backup of your old buttons is in custombtn.old\n"))
                        rco.close()
                    except IOError,x:
                        print str(x)
                else:
                    print _("Note!!! You have specified custom buttons in both custombtn.txt and .pronsolerc")
                    print _("Ignoring custombtn.txt. Remove all current buttons to revert to custombtn.txt")
                    
        except:
            pass
        self.popmenu()
        self.popwindow()
        self.t=Tee(self.catchprint)
        self.stdout=sys.stdout
        self.mini=False
        self.p.sendcb=self.sentcb
        self.p.startcb=self.startcb
        self.p.endcb=self.endcb
        self.starttime=0
        self.curlayer=0
        self.cur_button=None
    
    def startcb(self):
        self.starttime=time.time()
        
    def endcb(self):
        if(self.p.queueindex==0):
            print "Print took "+str(int(time.time()-self.starttime)/60)+" minutes "+str(int(time.time()-self.starttime)%60)+" seconds."
            wx.CallAfter(self.pausebtn.Disable)
            wx.CallAfter(self.printbtn.SetLabel,_("Print"))
            
    
    def online(self):
        print _("Printer is now online.")
        wx.CallAfter(self.connectbtn.Disable)
        for i in self.printerControls:
            wx.CallAfter(i.Enable)
        if self.filename:
            wx.CallAfter(self.printbtn.Enable)
        
    
    def sentcb(self,line):
        if("G1" in line):
            if("Z" in line):
                try:
                    layer=float(line.split("Z")[1].split()[0])
                    if(layer!=self.curlayer):
                        self.curlayer=layer
                        self.gviz.hilight=[]
                        threading.Thread(target=wx.CallAfter,args=(self.gviz.setlayer,layer)).start()
                except:
                    pass
            threading.Thread(target=self.gviz.addgcode,args=(line,1)).start()
            #self.gwindow.p.addgcode(line,hilight=1)
    
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
                l=str(float(self.edist.GetValue())*-1.0)
            pronsole.pronsole.do_extrude(self,l)
        except:
            pass
    
    def do_settemp(self,l=""):
        try:
            if not (l.__class__=="".__class__ or l.__class__==u"".__class__) or (not len(l)):
                l=str(self.htemp.GetValue().split()[0])
            l=l.lower().replace(",",".")
            for i in self.temps.keys():
                l=l.replace(i,self.temps[i])
            f=float(l)
            if f>=0:
                if self.p.online:
                    self.p.send_now("M104 S"+l)
                    print _("Setting hotend temperature to "),f,_(" degrees Celsius.")
                    self.htemp.SetValue(l)
                    self.set("last_temperature",str(f))
                else:
                    print _("Printer is not online.")
            else:
                print _("You cannot set negative temperatures. To turn the hotend off entirely, set its temperature to 0.")
        except:
            print _("You must enter a temperature.")
    
    def do_bedtemp(self,l=""):
        try:
            if not (l.__class__=="".__class__ or l.__class__==u"".__class__) or (not len(l)):
                l=str(self.btemp.GetValue().split()[0])
            l=l.lower().replace(",",".")
            for i in self.bedtemps.keys():
                l=l.replace(i,self.bedtemps[i])
            f=float(l)
            if f>=0:
                if self.p.online:
                    self.p.send_now("M140 S"+l)
                    print _("Setting bed temperature to "),f,_(" degrees Celsius.")
                    self.btemp.SetValue(l)
                    self.set("last_bed_temperature",str(f))
                else:
                    print _("Printer is not online.")
            else:
                print _("You cannot set negative temperatures. To turn the bed off entirely, set its temperature to 0.")
        except:
            print _("You must enter a temperature.")
            
    def end_macro(self):
        pronsole.pronsole.end_macro(self)
        self.update_macros_menu()
    
    def delete_macro(self,macro_name):
        pronsole.pronsole.delete_macro(self,macro_name)
        self.update_macros_menu()
    
    def start_macro(self,macro_name,old_macro_definition=""):
        if not self.processing_rc:
            def cb(definition):
                if len(definition.strip())==0:
                    if old_macro_definition!="":
                        dialog = wx.MessageDialog(self,_("Do you want to erase the macro?"),style=wx.YES_NO|wx.YES_DEFAULT|wx.ICON_QUESTION)
                        if dialog.ShowModal()==wx.ID_YES:
                            self.delete_macro(macro_name)
                            return
                    print _("Cancelled.")
                    return
                self.cur_macro_name = macro_name
                self.cur_macro_def = definition
                self.end_macro()
            macroed(macro_name,old_macro_definition,cb)
        else:
            pronsole.pronsole.start_macro(self,macro_name,old_macro_definition)
    
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
        # File menu
        m = wx.Menu()
        self.Bind(wx.EVT_MENU, self.loadfile, m.Append(-1,_("&Open..."),_(" Opens file")))
        self.Bind(wx.EVT_MENU, self.do_editgcode, m.Append(-1,_("&Edit..."),_(" Edit open file")))
        self.Bind(wx.EVT_MENU, self.clearOutput, m.Append(-1,_("Clear console"),_(" Clear output console")))
        self.Bind(wx.EVT_MENU, self.OnExit, m.Append(wx.ID_EXIT,_("E&xit"),_(" Closes the Window")))
        self.menustrip.Append(m,_("&File"))
        
        # Settings menu
        m = wx.Menu()
        self.macros_menu = wx.Menu()
        m.AppendSubMenu(self.macros_menu, _("&Macros"))
        self.Bind(wx.EVT_MENU, self.new_macro, self.macros_menu.Append(-1, _("<&New...>")))
        self.Bind(wx.EVT_MENU, lambda *e:options(self), m.Append(-1,_("&Options"),_(" Options dialog")))
        
        self.Bind(wx.EVT_MENU, lambda x:threading.Thread(target=lambda :self.do_skein("set")).start(), m.Append(-1,_("SFACT Settings"),_(" Adjust SFACT settings")))
        try:
            from SkeinforgeQuickEditDialog import SkeinforgeQuickEditDialog
            self.Bind(wx.EVT_MENU, lambda *e:SkeinforgeQuickEditDialog(self), m.Append(-1,_("SFACT Quick Settings"),_(" Quickly adjust SFACT settings for active profile")))
        except:
            pass

        self.menustrip.Append(m,_("&Settings"))
        self.update_macros_menu()
        self.SetMenuBar(self.menustrip)
    
    
    def doneediting(self,gcode):
        f=open(self.filename,"w")
        f.write("\n".join(gcode))
        f.close()
        wx.CallAfter(self.loadfile,None,self.filename)
    
    def do_editgcode(self,e=None):
        if(self.filename is not None):
            macroed(self.filename,self.f,self.doneediting,1)
    
    def new_macro(self,e=None):
        dialog = wx.Dialog(self,-1,_("Enter macro name"),size=(260,85))
        panel = wx.Panel(dialog,-1)
        vbox = wx.BoxSizer(wx.VERTICAL)
        wx.StaticText(panel,-1,_("Macro name:"),(8,14))
        dialog.namectrl = wx.TextCtrl(panel,-1,'',(110,8),size=(130,24),style=wx.TE_PROCESS_ENTER)
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        okb = wx.Button(dialog,wx.ID_OK,_("Ok"),size=(60,24))
        dialog.Bind(wx.EVT_TEXT_ENTER,lambda e:dialog.EndModal(wx.ID_OK),dialog.namectrl)
        #dialog.Bind(wx.EVT_BUTTON,lambda e:self.new_macro_named(dialog,e),okb)
        hbox.Add(okb)
        hbox.Add(wx.Button(dialog,wx.ID_CANCEL,_("Cancel"),size=(60,24)))
        vbox.Add(panel)
        vbox.Add(hbox,1,wx.ALIGN_CENTER|wx.TOP|wx.BOTTOM,10)
        dialog.SetSizer(vbox)
        dialog.Centre()
        macro = ""
        if dialog.ShowModal()==wx.ID_OK:
            macro = dialog.namectrl.GetValue()
            if macro != "":
                wx.CallAfter(self.edit_macro,macro)
        dialog.Destroy()
        return macro
        
    def edit_macro(self,macro):
        if macro == "": return self.new_macro()
        if self.macros.has_key(macro):
            old_def = self.macros[macro]
        elif hasattr(self.__class__,"do_"+macro):
            print _("Name '")+macro+_("' is being used by built-in command")
            return
        elif len([c for c in macro if not c.isalnum() and c != "_"]):
            print _("Macro name may contain only alphanumeric symbols and underscores")
            return
        else:
            old_def = ""
        self.start_macro(macro,old_def)
        return macro
        
    def update_macros_menu(self):
        if not hasattr(self,"macros_menu"):
            return # too early, menu not yet built
        try:
            while True:
                item = self.macros_menu.FindItemByPosition(1)
                if item is None: return
                self.macros_menu.DeleteItem(item)
        except:
            pass
        for macro in self.macros.keys():
            self.Bind(wx.EVT_MENU, lambda x,m=macro:self.start_macro(m,self.macros[m]), self.macros_menu.Append(-1, macro))

    def OnExit(self, event):
        self.Close()
        
    def popwindow(self):
        # this list will contain all controls that should be only enabled
        # when we're connected to a printer
        self.printerControls = []
        
        #sizer layout: topsizer is a column sizer containing two sections
        #upper section contains the mini view buttons
        #lower section contains the rest of the window - manual controls, console, visualizations
        #TOP ROW:
        uts=self.uppertopsizer=wx.BoxSizer(wx.HORIZONTAL)
        uts.Add(wx.StaticText(self.panel,-1,_("Port:"),pos=(0,5)),wx.TOP|wx.LEFT,5)
        scan=self.scanserial()
        portslist=list(scan)
        if self.settings.port != "" and self.settings.port not in portslist:
            portslist += [self.settings.port]
        self.serialport = wx.ComboBox(self.panel, -1,
                choices=portslist,
                style=wx.CB_DROPDOWN|wx.CB_SORT, pos=(50,0))
        try:
            if self.settings.port in scan:
                self.serialport.SetValue(self.settings.port)
            elif len(portslist)>0:
                self.serialport.SetValue(portslist[0])
        except:
            pass
        uts.Add(self.serialport)
        uts.Add(wx.StaticText(self.panel,-1,"@",pos=(250,5)),wx.RIGHT,5)
        self.baud = wx.ComboBox(self.panel, -1,
                choices=["2400", "9600", "19200", "38400", "57600", "115200"],
                style=wx.CB_DROPDOWN|wx.CB_SORT, size=(110,30),pos=(275,0))
        try:
            self.baud.SetValue("115200")
            self.baud.SetValue(str(self.settings.baudrate))
        except:
            pass
        uts.Add(self.baud)
        self.connectbtn=wx.Button(self.panel,-1,_("Connect"),pos=(380,0))
        uts.Add(self.connectbtn)
        self.connectbtn.SetToolTipString(_("Connect to the printer"))
        self.connectbtn.Bind(wx.EVT_BUTTON,self.connect)
        self.disconnectbtn=wx.Button(self.panel,-1,_("Disconnect"),pos=(470,0))
        self.disconnectbtn.Bind(wx.EVT_BUTTON,self.disconnect)
        self.printerControls.append(self.disconnectbtn)
        uts.Add(self.disconnectbtn)
        self.resetbtn=wx.Button(self.panel,-1,_("Reset"),pos=(560,0))
        self.resetbtn.Bind(wx.EVT_BUTTON,self.reset)
        uts.Add(self.resetbtn)
        self.minibtn=wx.Button(self.panel,-1,_("Mini mode"),pos=(690,0))
        self.minibtn.Bind(wx.EVT_BUTTON,self.toggleview)
        uts.Add((10,-1))
        self.monitorbox=wx.CheckBox(self.panel,-1,"",pos=(450,37))
        uts.Add((15,-1))
        uts.Add(self.monitorbox)
        uts.Add(wx.StaticText(self.panel,-1,_("Monitor\nprinter"),pos=(470,37)))
        self.monitorbox.Bind(wx.EVT_CHECKBOX,self.setmonitor)
        
        uts.Add((15,-1),flag=wx.EXPAND)
        uts.Add(self.minibtn)
        
        #SECOND ROW
        ubs=self.upperbottomsizer=wx.BoxSizer(wx.HORIZONTAL)
        
        self.loadbtn=wx.Button(self.panel,-1,_("Load file"),pos=(0,40))
        self.loadbtn.Bind(wx.EVT_BUTTON,self.loadfile)
        ubs.Add(self.loadbtn)
        self.uploadbtn=wx.Button(self.panel,-1,_("SD Upload"),pos=(90,40))
        self.uploadbtn.Bind(wx.EVT_BUTTON,self.upload)
        self.printerControls.append(self.uploadbtn)
        ubs.Add(self.uploadbtn)
        self.sdprintbtn=wx.Button(self.panel,-1,_("SD Print"),pos=(180,40))
        self.sdprintbtn.Bind(wx.EVT_BUTTON,self.sdprintfile)
        self.printerControls.append(self.sdprintbtn)
        ubs.Add(self.sdprintbtn)
        self.printbtn=wx.Button(self.panel,-1,_("Print"),pos=(270,40))
        self.printbtn.Bind(wx.EVT_BUTTON,self.printfile)
        self.printbtn.Disable()
        ubs.Add(self.printbtn)
        self.pausebtn=wx.Button(self.panel,-1,_("Pause"),pos=(360,40))
        self.pausebtn.Bind(wx.EVT_BUTTON,self.pause)
        ubs.Add(self.pausebtn)
        ubs.Add((50,-1),flag=wx.EXPAND)
        #Right full view
        lrs=self.lowerrsizer=wx.BoxSizer(wx.VERTICAL)
        self.logbox=wx.TextCtrl(self.panel,size=(350,340),pos=(440,75),style = wx.TE_MULTILINE)
        self.logbox.SetEditable(0)
        lrs.Add(self.logbox)
        lbrs=wx.BoxSizer(wx.HORIZONTAL)
        self.commandbox=wx.TextCtrl(self.panel,size=(295,30),pos=(440,420),style = wx.TE_PROCESS_ENTER)
        self.commandbox.Bind(wx.EVT_TEXT_ENTER,self.sendline)
        #self.printerControls.append(self.commandbox)
        lbrs.Add(self.commandbox)
        self.sendbtn=wx.Button(self.panel,-1,_("Send"),size=(55,28), pos=(700,420))
        self.sendbtn.Bind(wx.EVT_BUTTON,self.sendline)
        #self.printerControls.append(self.sendbtn)
        lbrs.Add(self.sendbtn)
        lrs.Add(lbrs)
        
        #left pane
        lls=self.lowerlsizer=wx.GridBagSizer()
        lls.Add(wx.StaticText(self.panel,-1,_("mm/min"),pos=(60,69)),pos=(0,4),span=(1,4))
        self.xyfeedc=wx.SpinCtrl(self.panel,-1,str(self.settings.xy_feedrate),min=0,max=50000,size=(70,25),pos=(25,83))
        lls.Add(wx.StaticText(self.panel,-1,_("XY:"),pos=(2,90-2)),pos=(1,0),span=(1,2))
        lls.Add(self.xyfeedc,pos=(1,2),span=(1,4))
        lls.Add(wx.StaticText(self.panel,-1,_("Z:"),pos=(90,90-2)),pos=(1,6),span=(1,2))
        self.zfeedc=wx.SpinCtrl(self.panel,-1,str(self.settings.z_feedrate),min=0,max=50000,size=(70,25),pos=(105,83))
        lls.Add(self.zfeedc,pos=(1,8),span=(1,4))
        
        #lls.Add((200,375))
        
        for i in self.cpbuttons:
            btn=wx.Button(self.panel,-1,i[0])#,size=(60,-1))
            btn.SetBackgroundColour(i[3])
            btn.SetForegroundColour("black")
            btn.properties=i
            btn.Bind(wx.EVT_BUTTON,self.procbutton)
            self.btndict[i[1]]=btn
            self.printerControls.append(btn)
            lls.Add(btn,pos=i[2],span=i[4])
        
        
        lls.Add(wx.StaticText(self.panel,-1,_("Heater:"),pos=(0,343)),pos=(11,0),span=(1,1))
        htemp_choices=[self.temps[i]+" ("+i+")" for i in sorted(self.temps.keys(),key=lambda x:self.temps[x])]
        
        if self.settings.last_temperature not in map(float,self.temps.values()):
            htemp_choices = [str(self.settings.last_temperature)] + htemp_choices
        self.htemp=wx.ComboBox(self.panel, -1,
                choices=htemp_choices,style=wx.CB_DROPDOWN, size=(90,25),pos=(45,337))

        
        lls.Add(self.htemp,pos=(11,1),span=(1,3))
        self.settbtn=wx.Button(self.panel,-1,_("Set"),size=(38,-1),pos=(135,335))
        self.settbtn.Bind(wx.EVT_BUTTON,self.do_settemp)
        self.printerControls.append(self.settbtn)
        lls.Add(self.settbtn,pos=(11,4),span=(1,2))
        lls.Add(wx.StaticText(self.panel,-1,_("Bed:"),pos=(0,343)),pos=(12,0),span=(1,1))
        btemp_choices=[self.bedtemps[i]+" ("+i+")" for i in sorted(self.bedtemps.keys(),key=lambda x:self.temps[x])]
        if self.settings.last_bed_temperature not in map(float,self.bedtemps.values()):
            btemp_choices = [str(self.settings.last_bed_temperature)] + btemp_choices
        self.btemp=wx.ComboBox(self.panel, -1,
                choices=btemp_choices,style=wx.CB_DROPDOWN, size=(90,25),pos=(45,367))
        self.btemp.SetValue(str(self.settings.last_bed_temperature))
        self.htemp.SetValue(str(self.settings.last_temperature))
         
        
        ## added for an error where only the bed would get (pla) or (abs). 
        #This ensures, if last temp is a default pla or abs, it will be marked so.
        # if it is not, then a (user) remark is added. This denotes a manual entry

        for i in btemp_choices:
            if i.split()[0] == str(self.settings.last_bed_temperature).split('.')[0] or i.split()[0] == str(self.settings.last_bed_temperature):
                self.btemp.SetValue(i)
        for i in htemp_choices:
            if i.split()[0] == str(self.settings.last_temperature).split('.')[0] or i.split()[0] == str(self.settings.last_temperature) :
               self.htemp.SetValue(i)

        if( '(' not in self.btemp.Value):
            self.btemp.SetValue(self.btemp.Value + ' (user)')
        if( '(' not in self.htemp.Value):
            self.htemp.SetValue(self.htemp.Value + ' (user)')   


        lls.Add(self.btemp,pos=(12,1),span=(1,3))
        self.setbbtn=wx.Button(self.panel,-1,_("Set"),size=(38,-1),pos=(135,365))
        self.setbbtn.Bind(wx.EVT_BUTTON,self.do_bedtemp)
        self.printerControls.append(self.setbbtn)
        lls.Add(self.setbbtn,pos=(12,4),span=(1,2))
        self.tempdisp=wx.StaticText(self.panel,-1,"")
        lls.Add(self.tempdisp,pos=(12,6),span=(1,3))
        
        self.edist=wx.SpinCtrl(self.panel,-1,"5",min=0,max=1000,size=(60,25),pos=(70,398))
        self.edist.SetBackgroundColour((225,200,200))
        self.edist.SetForegroundColour("black")
        lls.Add(self.edist,pos=(13,3),span=(1,2))
        lls.Add(wx.StaticText(self.panel,-1,_("mm"),pos=(130,407)),pos=(13,5),span=(1,2))
        self.efeedc=wx.SpinCtrl(self.panel,-1,str(self.settings.e_feedrate),min=0,max=50000,size=(60,25),pos=(70,397+28))
        self.efeedc.SetBackgroundColour((225,200,200))
        self.efeedc.SetForegroundColour("black")
        self.efeedc.Bind(wx.EVT_SPINCTRL,self.setfeeds)
        lls.Add(self.efeedc,pos=(14,3),span=(1,2))
        lls.Add(wx.StaticText(self.panel,-1,_("mm/min"),pos=(130,407+27)),pos=(14,5),span=(1,2))
        self.xyfeedc.Bind(wx.EVT_SPINCTRL,self.setfeeds)
        self.zfeedc.Bind(wx.EVT_SPINCTRL,self.setfeeds)
        self.zfeedc.SetBackgroundColour((180,255,180))
        self.zfeedc.SetForegroundColour("black")
        lls.Add((10,0),pos=(0,11),span=(1,1))
        self.gviz=gviz.gviz(self.panel,(300,300),
            bedsize=(self.settings.bed_size_x,self.settings.bed_size_y),
            grid=(self.settings.preview_grid_step1,self.settings.preview_grid_step2),
            extrusion_width=self.settings.preview_extrusion_width)
        self.gviz.showall=1
        self.gwindow=gviz.window([],
            bedsize=(self.settings.bed_size_x,self.settings.bed_size_y),
            grid=(self.settings.preview_grid_step1,self.settings.preview_grid_step2),
            extrusion_width=self.settings.preview_extrusion_width)
        self.gviz.Bind(wx.EVT_LEFT_DOWN,self.showwin)
        self.gwindow.Bind(wx.EVT_CLOSE,lambda x:self.gwindow.Hide())
        cs=self.centersizer=wx.GridBagSizer()
        cs.Add(self.gviz,pos=(0,0),span=(1,3))
        lls.Add(cs,pos=(0,10),span=(15,1))
        
        self.uppersizer=wx.BoxSizer(wx.VERTICAL)
        self.uppersizer.Add(self.uppertopsizer)
        self.uppersizer.Add(self.upperbottomsizer)
        
        self.lowersizer=wx.BoxSizer(wx.HORIZONTAL)
        self.lowersizer.Add(lls)
        self.lowersizer.Add(lrs)
        self.topsizer=wx.BoxSizer(wx.VERTICAL)
        self.topsizer.Add(self.uppersizer)
        self.topsizer.Add(self.lowersizer)
        self.panel.SetSizer(self.topsizer)
        self.status=self.CreateStatusBar()
        self.status.SetStatusText(_("Not connected to printer."))
        self.panel.Bind(wx.EVT_MOUSE_EVENTS,self.editbutton)
        self.Bind(wx.EVT_CLOSE, self.kill)
        self.topsizer.Layout()
        self.topsizer.Fit(self)
        
        # disable all printer controls until we connect to a printer
        self.pausebtn.Disable()
        for i in self.printerControls:
            i.Disable()
        
        #self.panel.Fit()
        #uts.Layout()
        self.cbuttons_reload()
        
    def showwin(self,event):
        if(self.f is not None):
            self.gwindow.Show()
        
    def setfeeds(self,e):
        self.feedrates_changed = True
        try:
            self.settings._set("e_feedrate",self.efeedc.GetValue())
        except:
            pass
        try:
            self.settings._set("z_feedrate",self.zfeedc.GetValue())
        except:
            pass
        try:
            self.settings._set("xy_feedrate",self.xyfeedc.GetValue())
        except:
            pass
        
        
    def toggleview(self,e):
        if(self.mini):
            self.mini=False
            self.topsizer.Fit(self)
        
            #self.SetSize(winsize)
            wx.CallAfter(self.minibtn.SetLabel, _("Mini mode"))
            
        else:
            self.mini=True
            self.uppersizer.Fit(self)
        
            #self.SetSize(winssize)
            wx.CallAfter(self.minibtn.SetLabel, _("Full mode"))
    
    def cbuttons_reload(self):
        allcbs = []
        ubs=self.upperbottomsizer
        cs=self.centersizer
        for item in ubs.GetChildren():
            if hasattr(item.GetWindow(),"custombutton"):
                allcbs += [(ubs,item.GetWindow())]
        for item in cs.GetChildren():
            if hasattr(item.GetWindow(),"custombutton"):
                allcbs += [(cs,item.GetWindow())]
        for sizer,button in allcbs:
            #sizer.Remove(button)
            button.Destroy()
        self.custombuttonbuttons=[]
        while len(self.custombuttons) < 13:
            self.custombuttons.append(None)
        for i in xrange(len(self.custombuttons)):
            btndef = self.custombuttons[i]
            try:
                b=wx.Button(self.panel,-1,btndef[0])
                if len(btndef)>2:
                    b.SetBackgroundColour(btndef[2])
                    rr,gg,bb=b.GetBackgroundColour().Get()
                    if 0.3*rr+0.59*gg+0.11*bb < 60:
                        b.SetForegroundColour("#ffffff")
            except:
                b=wx.Button(self.panel,-1,"")
                b.Freeze()
            b.custombutton=i
            b.properties=btndef
            b.Bind(wx.EVT_BUTTON,self.procbutton)
            b.Bind(wx.EVT_MOUSE_EVENTS,self.editbutton)
            self.custombuttonbuttons.append(b)
            if i<4:
                ubs.Add(b)
            else:
                cs.Add(b,pos=(1+(i-4)/3,(i-4)%3),span=(1,1))
        self.topsizer.Layout()
    
    def help_button(self):
        print _('Defines custom button. Usage: button <num> "title" [/c "colour"] command')
    
    def do_button(self,argstr):
        def nextarg(rest):
            rest=rest.lstrip()
            if rest.startswith('"'):
               return rest[1:].split('"',1)
            else:
               return rest.split(None,1)
        #try:
        num,argstr=nextarg(argstr)
        num=int(num)
        title,argstr=nextarg(argstr)
        colour=None
        try:
            c1,c2=nextarg(argstr)
            if c1=="/c":
                colour,argstr=nextarg(c2)
        except:
            pass
        command=argstr.strip()
        if num<0 or num>=64:
            print _("Custom button number should be between 0 and 63")
            return
        while num >= len(self.custombuttons):
            self.custombuttons+=[None]
        self.custombuttons[num]=[title,command]
        if colour is not None:
            self.custombuttons[num]+=[colour]
        if not self.processing_rc:
            self.cbuttons_reload()
        #except Exception,x:
        #    print "Bad syntax for button definition, see 'help button'"
        #    print x
        

    def cbutton_save(self,n,bdef,new_n=None):
        if new_n is None: new_n=n
        if bdef is None or bdef == "":
            self.save_in_rc(("button %d" % n),'')
        elif len(bdef)>2:
            colour=bdef[2]
            if type(colour) not in (str,unicode):
                #print type(colour),map(type,colour)
                if type(colour)==tuple and tuple(map(type,colour))==(int,int,int):
                    colour = map(lambda x:x%256,colour)
                    colour = wx.Colour(*colour).GetAsString(wx.C2S_NAME|wx.C2S_HTML_SYNTAX)
                else:
                    colour = wx.Colour(colour).GetAsString(wx.C2S_NAME|wx.C2S_HTML_SYNTAX)
            self.save_in_rc(("button %d" % n),'button %d "%s" /c "%s" %s' % (new_n,bdef[0],colour,bdef[1]))
        else:
            self.save_in_rc(("button %d" % n),'button %d "%s" %s' % (new_n,bdef[0],bdef[1]))

    def cbutton_edit(self,e,button=None):
        bedit=ButtonEdit(self)
        if button is not None:
            n = button.custombutton
            bedit.name.SetValue(button.properties[0])
            bedit.command.SetValue(button.properties[1])
            if len(button.properties)>2:
                colour=button.properties[2]
                if type(colour) not in (str,unicode):
                    #print type(colour)
                    if type(colour)==tuple and tuple(map(type,colour))==(int,int,int):
                        colour = map(lambda x:x%256,colour)
                        colour = wx.Colour(*colour).GetAsString(wx.C2S_NAME|wx.C2S_HTML_SYNTAX)
                    else:
                        colour = wx.Colour(colour).GetAsString(wx.C2S_NAME|wx.C2S_HTML_SYNTAX)
                bedit.color.SetValue(colour)
        else:
            n = len(self.custombuttons)
            while n>0 and self.custombuttons[n-1] is None:
                n -= 1
        if bedit.ShowModal()==wx.ID_OK:
            if n==len(self.custombuttons):
                self.custombuttons+=[None]
            self.custombuttons[n]=[bedit.name.GetValue().strip(),bedit.command.GetValue().strip()]
            if bedit.color.GetValue().strip()!="":
                self.custombuttons[n]+=[bedit.color.GetValue()]
            self.cbutton_save(n,self.custombuttons[n])
        bedit.Destroy()
        self.cbuttons_reload()

    def cbutton_remove(self,e,button):
        n = button.custombutton
        self.custombuttons[n]=None
        self.cbutton_save(n,None)
        #while len(self.custombuttons) and self.custombuttons[-1] is None:
        #    del self.custombuttons[-1]
        self.cbuttons_reload()
    
    def cbutton_order(self,e,button,dir):
        n = button.custombutton
        if dir<0:
            n=n-1
        if n+1 >= len(self.custombuttons):
            self.custombuttons+=[None] # pad
        # swap
        self.custombuttons[n],self.custombuttons[n+1] = self.custombuttons[n+1],self.custombuttons[n]
        self.cbutton_save(n,self.custombuttons[n])
        self.cbutton_save(n+1,self.custombuttons[n+1])
        #if self.custombuttons[-1] is None:
        #    del self.custombuttons[-1]
        self.cbuttons_reload()
    
    def editbutton(self,e):
        if e.IsCommandEvent() or e.ButtonUp(wx.MOUSE_BTN_RIGHT):
            if e.IsCommandEvent():
                pos = (0,0)
            else:
                pos = e.GetPosition()
            popupmenu = wx.Menu()
            obj = e.GetEventObject()
            if hasattr(obj,"custombutton"):
                item = popupmenu.Append(-1,_("Edit custom button '%s'") % e.GetEventObject().GetLabelText())
                self.Bind(wx.EVT_MENU,lambda e,button=e.GetEventObject():self.cbutton_edit(e,button),item)
                item = popupmenu.Append(-1,_("Move left <<"))
                self.Bind(wx.EVT_MENU,lambda e,button=e.GetEventObject():self.cbutton_order(e,button,-1),item)
                if obj.custombutton == 0: item.Enable(False)
                item = popupmenu.Append(-1,_("Move right >>"))
                self.Bind(wx.EVT_MENU,lambda e,button=e.GetEventObject():self.cbutton_order(e,button,1),item)
                if obj.custombutton == 63: item.Enable(False)
                pos = self.panel.ScreenToClient(e.GetEventObject().ClientToScreen(pos))
                item = popupmenu.Append(-1,_("Remove custom button '%s'") % e.GetEventObject().GetLabelText())
                self.Bind(wx.EVT_MENU,lambda e,button=e.GetEventObject():self.cbutton_remove(e,button),item)
            else:
                item = popupmenu.Append(-1,_("Add custom button"))
                self.Bind(wx.EVT_MENU,self.cbutton_edit,item)
            self.panel.PopupMenu(popupmenu, pos)
        elif e.Dragging() and e.ButtonIsDown(wx.MOUSE_BTN_LEFT):
            obj = e.GetEventObject()
            scrpos = obj.ClientToScreen(e.GetPosition())
            if not hasattr(self,"dragging"):
                # init dragging of the custom button
                if hasattr(obj,"custombutton"):
                    self.dragging = wx.Button(self.panel,-1,obj.GetLabel())
                    self.dragging.SetBackgroundColour(obj.GetBackgroundColour())
                    self.dragging.sourcebutton = obj
                    self.dragging.Raise()
                    self.dragging.Disable()
                    self.dragging.SetPosition(self.panel.ScreenToClient(scrpos))
                    for b in self.custombuttonbuttons:
                        if b.IsFrozen(): b.Thaw()
                    self.last_drag_dest = obj
                    self.dragging.label = obj.s_label = obj.GetLabel()
                    self.dragging.bgc = obj.s_bgc = obj.GetBackgroundColour()
            else: 
                # dragging in progress
                self.dragging.SetPosition(self.panel.ScreenToClient(scrpos))
                btns = self.custombuttonbuttons 
                dst = None
                src = self.dragging.sourcebutton
                drg = self.dragging
                for b in self.custombuttonbuttons:
                    if b.GetScreenRect().Contains(scrpos):
                        dst = b
                        break
                #if dst is None and self.panel.GetScreenRect().Contains(scrpos):
                #    # try to check if it is after buttons at the end
                #    tspos = self.panel.ClientToScreen(self.upperbottomsizer.GetPosition())
                #    bspos = self.panel.ClientToScreen(self.centersizer.GetPosition())
                #    tsrect = wx.Rect(*(tspos.Get()+self.upperbottomsizer.GetSize().Get()))
                #    bsrect = wx.Rect(*(bspos.Get()+self.centersizer.GetSize().Get()))
                #    lbrect = btns[-1].GetScreenRect()
                #    p = scrpos.Get()
                #    if len(btns)<4 and tsrect.Contains(scrpos):
                #        if lbrect.GetRight() < p[0]:
                #            print "Right of last button on upper cb sizer"
                #    if bsrect.Contains(scrpos):
                #        if lbrect.GetBottom() < p[1]:
                #            print "Below last button on lower cb sizer"
                #        if lbrect.GetRight() < p[0] and lbrect.GetTop() <= p[1] and lbrect.GetBottom() >= p[1]:
                #            print "Right to last button on lower cb sizer"
                if dst is not self.last_drag_dest:
                    if self.last_drag_dest is not None:
                        self.last_drag_dest.SetBackgroundColour(self.last_drag_dest.s_bgc)
                        self.last_drag_dest.SetLabel(self.last_drag_dest.s_label)
                    if dst is not None and dst is not src:
                        dst.s_bgc = dst.GetBackgroundColour()
                        dst.s_label = dst.GetLabel()
                        src.SetBackgroundColour(dst.GetBackgroundColour())
                        src.SetLabel(dst.GetLabel())
                        dst.SetBackgroundColour(drg.bgc)
                        dst.SetLabel(drg.label)
                    else:
                        src.SetBackgroundColour(drg.bgc)
                        src.SetLabel(drg.label)
                    self.last_drag_dest = dst
        elif hasattr(self,"dragging") and not e.ButtonIsDown(wx.MOUSE_BTN_LEFT):
            # dragging finished
            obj = e.GetEventObject()
            scrpos = obj.ClientToScreen(e.GetPosition())
            dst = None
            src = self.dragging.sourcebutton
            drg = self.dragging
            for b in self.custombuttonbuttons:
                if b.GetScreenRect().Contains(scrpos):
                    dst = b
                    break
            if dst is not None:
                src_i = src.custombutton
                dst_i = dst.custombutton
                self.custombuttons[src_i],self.custombuttons[dst_i] = self.custombuttons[dst_i],self.custombuttons[src_i]
                self.cbutton_save(src_i,self.custombuttons[src_i])
                self.cbutton_save(dst_i,self.custombuttons[dst_i])
                while self.custombuttons[-1] is None:
                    del self.custombuttons[-1]
            wx.CallAfter(self.dragging.Destroy)
            del self.dragging
            wx.CallAfter(self.cbuttons_reload)
            del self.last_drag_dest
        else:
            e.Skip()
    
    def procbutton(self,e):
        try:
            if hasattr(e.GetEventObject(),"custombutton"):
                if wx.GetKeyState(wx.WXK_CONTROL) or wx.GetKeyState(wx.WXK_ALT):
                    return self.editbutton(e)
                self.cur_button=e.GetEventObject().custombutton
            self.onecmd(e.GetEventObject().properties[1])
            self.cur_button=None
        except:
            print _("event object missing")
            self.cur_button=None
            raise
        
    def kill(self,e):
        self.statuscheck=0
        self.p.recvcb=None
        self.p.disconnect()
        if hasattr(self,"feedrates_changed"):
            self.save_in_rc("set xy_feedrate","set xy_feedrate %d" % self.settings.xy_feedrate)
            self.save_in_rc("set z_feedrate","set z_feedrate %d" % self.settings.z_feedrate)
            self.save_in_rc("set e_feedrate","set e_feedrate %d" % self.settings.e_feedrate)
        try:
            self.gwindow.Destroy()
        except:
            pass
        self.Destroy()
        
    def do_monitor(self,l=""):
        if l.strip()=="":
            self.monitorbox.SetValue(not self.monitorbox.GetValue())
        elif l.strip()=="off":
            self.monitorbox.SetValue(False)
        else:
            try:
                self.monitor_interval=float(l)
                self.monitorbox.SetValue(self.monitor_interval>0)
            except:
                print _("Invalid period given.")
        self.setmonitor(None)
        if self.monitor:
            print _("Monitoring printer.")
        else:
            print _("Done monitoring.")
            
        
    def setmonitor(self,e):
        self.monitor=self.monitorbox.GetValue()
        
    def sendline(self,e):
        command=self.commandbox.GetValue()
        if not len(command):
            return
        wx.CallAfter(self.logbox.AppendText,">>>"+command+"\n")
        self.onecmd(str(command))
        self.commandbox.SetSelection(0,len(command))

    def clearOutput(self,e):
        self.logbox.Clear()
        
    def statuschecker(self):
        try:
            while(self.statuscheck):
                string=""
                if(self.p.online):
                    string+=_("Printer is online. ")
                try:
                    string+=_("Loaded ")+os.path.split(self.filename)[1]+" "
                except:
                    pass
                string+=(self.tempreport.replace("\r","").replace("T",_("Hotend")).replace("B",_("Bed")).replace("\n","").replace("ok ",""))+" "
                wx.CallAfter(self.tempdisp.SetLabel,self.tempreport.strip().replace("ok ",""))
                if self.sdprinting:
                    string+= _(" SD printing:%04.2f %%") % (self.percentdone,)
                if self.p.printing:
                    string+= _(" Printing:%04.2f %%") % (100*float(self.p.queueindex)/len(self.p.mainqueue),)
                wx.CallAfter(self.status.SetStatusText,string)
                wx.CallAfter(self.gviz.Refresh)
                if(self.monitor and self.p.online):
                    if self.sdprinting:
                        self.p.send_now("M27")
                    self.p.send_now("M105")
                time.sleep(self.monitor_interval)
            wx.CallAfter(self.status.SetStatusText,_("Not connected to printer."))
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
            wx.CallAfter(self.tempdisp.SetLabel,self.tempreport.strip().replace("ok ",""))
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
            wx.CallAfter(self.status.SetStatusText,_("Opening file failed."))
            self.recvlisteners.remove(self.waitforsdresponse)
            return
        if "File opened" in l:
            wx.CallAfter(self.status.SetStatusText,l)
        if "File selected" in l:
            wx.CallAfter(self.status.SetStatusText,_("Starting print"))
            self.sdprinting=1
            self.p.send_now("M24")
            self.startcb()
            return
        if "Done printing file" in l:
            wx.CallAfter(self.status.SetStatusText,l)
            self.sdprinting=0
            self.recvlisteners.remove(self.waitforsdresponse)
            self.endcb()
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
        dlg=wx.SingleChoiceDialog(self, _("Select the file to print"), _("Pick SD file"), self.sdfiles)
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
            print _("Skeinforge execution failed.")
            self.stopsf=1
            traceback.print_exc(file=sys.stdout)
        
    def skein_monitor(self):
        while(not self.stopsf):
            try:
                wx.CallAfter(self.status.SetStatusText,_("Skeining..."))#+self.cout.getvalue().split("\n")[-1])
            except:
                pass
            time.sleep(0.1)
        fn=self.filename
        try:
            self.filename=self.filename.replace(".stl","_export.gcode").replace(".STL","_export.gcode")
            of=open(self.filename)
            self.f=[i.replace("\n","").replace("\r","") for i in of]
            of.close
            if self.p.online:
                    wx.CallAfter(self.printbtn.Enable)
                    
            wx.CallAfter(self.status.SetStatusText,_("Loaded ")+self.filename+_(", %d lines") % (len(self.f),))
            wx.CallAfter(self.pausebtn.Disable)
            wx.CallAfter(self.printbtn.SetLabel,_("Print"))

            threading.Thread(target=self.loadviz).start()
        except:
            self.filename=fn
        
    def skein(self,filename):
        print _("Skeining ") + filename
        if not os.path.exists("skeinforge"):
            print _("Skeinforge not found. \nPlease copy Skeinforge into a directory named \"skeinforge\" in the same directory as this file.")
            return
        if not os.path.exists("skeinforge/__init__.py"):
            f=open("skeinforge/__init__.py","w")
            f.close()
        self.cout=StringIO.StringIO()
        self.filename=filename
        self.stopsf=0
        thread(target=self.skein_func).start()
        thread(target=self.skein_monitor).start()
        
    def loadfile(self,event,filename=None):
        basedir=self.settings.last_file_path
        if not os.path.exists(basedir):
            basedir = "."
            try:
                basedir=os.path.split(self.filename)[0]
            except:
                pass
        dlg=wx.FileDialog(self,_("Open file to print"),basedir,style=wx.FD_OPEN|wx.FD_FILE_MUST_EXIST)
        dlg.SetWildcard(_("STL and GCODE files (;*.gcode;*.gco;*.g;*.stl;*.STL;)"))
        if(filename is not None or dlg.ShowModal() == wx.ID_OK):
            if filename is not None:
                name=filename
            else:
                name=dlg.GetPath()
            if not(os.path.exists(name)):
                self.status.SetStatusText(_("File not found!"))
                return
            path = os.path.split(name)[0]
            if path != self.settings.last_file_path:
                self.set("last_file_path",path)
            if name.lower().endswith(".stl"):
                self.skein(name)
            else:
                self.filename=name
                of=open(self.filename)
                self.f=[i.replace("\n","").replace("\r","") for i in of]
                of.close
                self.status.SetStatusText(_("Loaded ") + name + _(", %d lines") % (len(self.f),))
                wx.CallAfter(self.printbtn.SetLabel, _("Print"))
                wx.CallAfter(self.pausebtn.SetLabel, _("Pause"))
                wx.CallAfter(self.pausebtn.Disable)
                if self.p.online:
                    wx.CallAfter(self.printbtn.Enable)
                threading.Thread(target=self.loadviz).start()
                
    def loadviz(self):
        Xtot,Ytot,Ztot,Xmin,Xmax,Ymin,Ymax,Zmin,Zmax = pronsole.measurements(self.f)
        print pronsole.totalelength(self.f), _("mm of filament used in this print\n")
        print _("the print goes from"),Xmin,_("mm to"),Xmax,_("mm in X\nand is"),Xtot,_("mm wide\n")
        print _("the print goes from"),Ymin,_("mm to"),Ymax,_("mm in Y\nand is"),Ytot,_("mm wide\n")
        print _("the print goes from"),Zmin,_("mm to"),Zmax,_("mm in Z\nand is"),Ztot,_("mm high\n")
        self.gviz.clear()
        self.gwindow.p.clear()
        for i in self.f:
            self.gviz.addgcode(i)
            self.gwindow.p.addgcode(i)
        self.gviz.showall=1
        wx.CallAfter(self.gviz.Refresh)
                
    def printfile(self,event):
        if self.paused:
            self.p.paused=0
            self.paused=0
            self.on_startprint()
            if self.sdprinting:
                self.p.send_now("M26 S0")
                self.p.send_now("M24")
                return
        
        if self.f is None or not len(self.f):
            wx.CallAfter(self.status.SetStatusText, _("No file loaded. Please use load first."))
            return
        if not self.p.online:
            wx.CallAfter(self.status.SetStatusText,_("Not connected to printer."))
            return
        self.on_startprint()
        self.p.startprint(self.f)
    
    def on_startprint(self):
        wx.CallAfter(self.pausebtn.SetLabel, _("Pause"))
        wx.CallAfter(self.pausebtn.Enable)
        wx.CallAfter(self.printbtn.SetLabel, _("Restart"))
    
    def endupload(self):
        self.p.send_now("M29 ")
        wx.CallAfter(self.status.SetStatusText, _("File upload complete"))
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
        dlg=wx.TextEntryDialog(self, ("Enter a target filename in 8.3 format:"), _("Pick SD filename") ,dosify(self.filename))
        if dlg.ShowModal()==wx.ID_OK:
            self.p.send_now("M28 "+str(dlg.GetValue()))
            self.recvlisteners+=[self.uploadtrigger]
        pass
        
    def pause(self,event):
        print _("Paused.")
        if not self.paused:
            if self.sdprinting:
                self.p.send_now("M25")
            else:
                if(not self.p.printing):
                    #print "Not printing, cannot pause."
                    return
                self.p.pause()
            self.paused=True
            wx.CallAfter(self.pausebtn.SetLabel, _("Resume"))
        else:
            self.paused=False
            if self.sdprinting:
                self.p.send_now("M24")
            else:
                self.p.resume()
            wx.CallAfter(self.pausebtn.SetLabel, _("Pause"))
    
        
    def sdprintfile(self,event):
        self.on_startprint()
        threading.Thread(target=self.getfiles).start()
        pass
        
    def connect(self,event):
        print _("Connecting...")
        port=None
        try:
            port=self.scanserial()[0]
        except:
            pass
        if self.serialport.GetValue()!="":
            port=str(self.serialport.GetValue())
        baud=115200
        try:
            baud=int(self.baud.GetValue())
        except:
            pass
        if self.paused:
            self.p.paused=0
            self.p.printing=0
            wx.CallAfter(self.pausebtn.SetLabel, _("Pause"))
            wx.CallAfter(self.printbtn.SetLabel, _("Print"))
            self.paused=0
            if self.sdprinting:
                self.p.send_now("M26 S0")
        self.p.connect(port,baud)
        self.statuscheck=True
        if port != self.settings.port:
            self.set("port",port)
        if baud != self.settings.baudrate:
            self.set("baudrate",str(baud))
        threading.Thread(target=self.statuschecker).start()
        
        
    def disconnect(self,event):
        print _("Disconnected.")
        self.p.disconnect()
        self.statuscheck=False
        
        wx.CallAfter(self.connectbtn.Enable);
        wx.CallAfter(self.printbtn.Disable);
        wx.CallAfter(self.pausebtn.Disable);
        for i in self.printerControls:
            wx.CallAfter(i.Disable)
        
        if self.paused:
            self.p.paused=0
            self.p.printing=0
            wx.CallAfter(self.pausebtn.SetLabel, _("Pause"))
            wx.CallAfter(self.printbtn.SetLabel, _("Print"))
            self.paused=0
            if self.sdprinting:
                self.p.send_now("M26 S0")
                
    
    def reset(self,event):
        print _("Reset.")
        dlg=wx.MessageDialog(self, _("Are you sure you want to reset the printer?"), _("Reset?"), wx.YES|wx.NO)
        if dlg.ShowModal()==wx.ID_YES:
            self.p.reset()
            if self.paused:
                self.p.paused=0
                self.p.printing=0
                wx.CallAfter(self.pausebtn.SetLabel, _("Pause"))
                wx.CallAfter(self.printbtn.SetLabel, _("Print"))
                self.paused=0
            
class macroed(wx.Dialog):
    """Really simple editor to edit macro definitions"""
    def __init__(self,macro_name,definition,callback,gcode=False):
        self.indent_chars = "  "
        title="  macro %s"
        if gcode:
            title="  %s"
        self.gcode=gcode
        wx.Dialog.__init__(self,None,title=title % macro_name,style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)
        self.callback = callback
        self.panel=wx.Panel(self,-1)
        titlesizer=wx.BoxSizer(wx.HORIZONTAL)
        title = wx.StaticText(self.panel,-1,title%macro_name)
        #title.SetFont(wx.Font(11,wx.NORMAL,wx.NORMAL,wx.BOLD))
        titlesizer.Add(title,1)
        self.okb = wx.Button(self.panel, -1, _("Save"))
        self.okb.Bind(wx.EVT_BUTTON, self.save)
        self.Bind(wx.EVT_CLOSE, self.close)
        titlesizer.Add(self.okb)
        self.cancelb = wx.Button(self.panel, -1, _("Cancel"))
        self.cancelb.Bind(wx.EVT_BUTTON, self.close)
        titlesizer.Add(self.cancelb)
        topsizer=wx.BoxSizer(wx.VERTICAL)
        topsizer.Add(titlesizer,0,wx.EXPAND)
        self.e=wx.TextCtrl(self.panel,style=wx.TE_MULTILINE+wx.HSCROLL,size=(200,200))
        if not self.gcode:
            self.e.SetValue(self.unindent(definition))
        else:
            self.e.SetValue("\n".join(definition))
        topsizer.Add(self.e,1,wx.ALL+wx.EXPAND)
        self.panel.SetSizer(topsizer)
        topsizer.Layout()
        topsizer.Fit(self)
        self.Show()
        self.e.SetFocus()
    def save(self,ev):
        self.Destroy()
        if not self.gcode:
            self.callback(self.reindent(self.e.GetValue()))
        else:
            self.callback(self.e.GetValue().split("\n"))
    def close(self,ev):
        self.Destroy()
    def unindent(self,text):
        import re
        self.indent_chars = text[:len(text)-len(text.lstrip())]
        if len(self.indent_chars)==0:
            self.indent_chars="  "
        unindented = ""
        lines = re.split(r"(?:\r\n?|\n)",text)
        #print lines
        if len(lines) <= 1:
            return text
        for line in lines:
            if line.startswith(self.indent_chars):
                unindented += line[len(self.indent_chars):] + "\n"
            else:
                unindented += line + "\n"
        return unindented
    def reindent(self,text):
        import re
        lines = re.split(r"(?:\r\n?|\n)",text)
        if len(lines) <= 1:
            return text
        reindented = ""
        for line in lines:
            if line.strip() != "":
                reindented += self.indent_chars + line + "\n"
        return reindented
        
class options(wx.Dialog):
    """Options editor"""
    def __init__(self,pronterface):
        wx.Dialog.__init__(self, None, title=_("Edit settings"))
        topsizer=wx.BoxSizer(wx.VERTICAL)
        vbox=wx.StaticBoxSizer(wx.StaticBox(self, label=_("Defaults")) ,wx.VERTICAL)
        topsizer.Add(vbox,1,wx.ALL+wx.EXPAND)
        grid=wx.GridSizer(rows=0,cols=2,hgap=8,vgap=2)
        vbox.Add(grid,0,wx.EXPAND)
        ctrls = {}
        for k,v in pronterface.settings._all_settings().items():
            grid.Add(wx.StaticText(self,-1,k),0,wx.BOTTOM+wx.RIGHT)
            ctrls[k] = wx.TextCtrl(self,-1,str(v))
            grid.Add(ctrls[k],1,wx.EXPAND)
        topsizer.Add(self.CreateSeparatedButtonSizer(wx.OK+wx.CANCEL),0,wx.EXPAND)
        self.SetSizer(topsizer)        
        topsizer.Layout()
        topsizer.Fit(self)
        if self.ShowModal()==wx.ID_OK:
            for k,v in pronterface.settings._all_settings().items():
                if ctrls[k].GetValue() != str(v):
                    pronterface.set(k,str(ctrls[k].GetValue()))
        self.Destroy()
        
class ButtonEdit(wx.Dialog):
    """Custom button edit dialog"""
    def __init__(self,pronterface):
        wx.Dialog.__init__(self, None, title=_("Custom button"),style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)
        self.pronterface=pronterface
        topsizer=wx.BoxSizer(wx.VERTICAL)
        vbox=wx.StaticBoxSizer(wx.StaticBox(self,label=""),wx.VERTICAL)
        topsizer.Add(vbox,1,wx.ALL+wx.EXPAND)
        grid=wx.FlexGridSizer(rows=0,cols=2,hgap=4,vgap=2)
        grid.AddGrowableCol(1,1)
        vbox.Add(grid,0,wx.EXPAND)
        grid.Add(wx.StaticText(self,-1, _("Button title")), 0, wx.BOTTOM+wx.RIGHT)
        self.name=wx.TextCtrl(self,-1,"")
        grid.Add(self.name,1,wx.EXPAND)
        grid.Add(wx.StaticText(self, -1, _("Command")), 0, wx.BOTTOM+wx.RIGHT)
        self.command=wx.TextCtrl(self,-1,"")
        xbox=wx.BoxSizer(wx.HORIZONTAL)
        xbox.Add(self.command,1,wx.EXPAND)
        self.command.Bind(wx.EVT_TEXT,self.macrob_enabler)
        self.macrob=wx.Button(self,-1,"..",style=wx.BU_EXACTFIT)
        self.macrob.Bind(wx.EVT_BUTTON,self.macrob_handler)
        xbox.Add(self.macrob,0)
        grid.Add(xbox)
        grid.Add(wx.StaticText(self,-1, _("Color")),0,wx.BOTTOM+wx.RIGHT)
        self.color=wx.TextCtrl(self,-1,"")
        grid.Add(self.color,1,wx.EXPAND)
        topsizer.Add(self.CreateSeparatedButtonSizer(wx.OK+wx.CANCEL),0,wx.EXPAND)
        self.SetSizer(topsizer)        
        topsizer.Layout()
        topsizer.Fit(self)
    def macrob_enabler(self,e):
        macro = self.command.GetValue()
        valid = False
        if macro == "":
            valid = True
        elif self.pronterface.macros.has_key(macro):
            valid = True
        elif hasattr(self.pronterface.__class__,"do_"+macro):
            valid = False
        elif len([c for c in macro if not c.isalnum() and c != "_"]):
            valid = False
        else:
            valid = True
        self.macrob.Enable(valid)
    def macrob_handler(self,e):
        macro = self.command.GetValue()
        macro = self.pronterface.edit_macro(macro)
        self.command.SetValue(macro)
        if self.name.GetValue()=="":
            self.name.SetValue(macro)
    
if __name__ == '__main__':
    app = wx.App(False)
    main = PronterWindow()
    main.Show()
    try:
        app.MainLoop()
    except:
        pass

