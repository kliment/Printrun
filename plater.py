import wx,time,random,threading,os,math
import stltool

class stlwrap:
    def __init__(self,obj,name=None):
        self.obj=obj
        self.name=name
        if name is None:
            self.name=obj.name
        
    def __repr__(self):
        return self.name
    

class showstl(wx.Window):
    def __init__(self,parent,size,pos):
        wx.Window.__init__(self,parent,size=size,pos=pos)
        self.l=wx.ListCtrl(self,size=(300,100),pos=(0,size[1]-100))
        self.eb=wx.Button(self,label="Export",pos=(300,size[1]-100))
        self.sb=wx.Button(self,label="Snap to Z=0",pos=(300,size[1]-70))
        self.cb=wx.Button(self,label="Put at 100,100",pos=(300,size[1]-40))
        self.eb.Bind(wx.EVT_BUTTON,self.export)
        self.sb.Bind(wx.EVT_BUTTON,self.snap)
        self.cb.Bind(wx.EVT_BUTTON,self.center)
        #self.SetBackgroundColour((0,0,0))
        #wx.FutureCall(200,self.paint)
        self.i=0
        self.previ=0
        self.Bind(wx.EVT_MOUSEWHEEL,self.rot)
        self.Bind(wx.EVT_MOUSE_EVENTS,self.move)
        self.Bind(wx.EVT_PAINT,self.repaint)
        #self.s=stltool.stl("sphere.stl").scale([2,1,1])
        self.triggered=0
        self.models={}
        self.basedir="."
        self.initpos=None
        self.prevsel=-1
        
    def center(self,event):
        i=self.l.GetFirstSelected()
        if i != -1:
                m=self.models[self.l.GetItemText(i)]
                m.offsets=[100,100,m.offsets[2]]
                self.Refresh()
                
    def snap(self,event):
        i=self.l.GetFirstSelected()
        if i != -1:
                m=self.models[self.l.GetItemText(i)]
                m.offsets[2]=-1.0*min(m.facetsminz)[0]
                #print m.offsets[2]
                self.Refresh()
        
        
    def export(self,event):
        dlg=wx.FileDialog(self,"Pick file to save to",self.basedir,style=wx.FD_SAVE)
        dlg.SetWildcard("STL files (;*.stl;)")
        if(dlg.ShowModal() == wx.ID_OK):
            name=dlg.GetPath()
            facets=[]
            for i in self.models.values():
                if i.offsets != [0,0,0]:
                    i=i.translate(i.offsets)
                facets+=i.facets
            stltool.emitstl(name,facets,"plater_export")
            print "wrote ",name
        
        
    def right(self,event):
        dlg=wx.FileDialog(self,"Open file to print",self.basedir,style=wx.FD_OPEN|wx.FD_FILE_MUST_EXIST)
        dlg.SetWildcard("STL files (;*.stl;)")
        if(dlg.ShowModal() == wx.ID_OK):
            name=dlg.GetPath()
            if not(os.path.exists(name)):
                return
            path = os.path.split(name)[0]
            self.basedir=path
            t=time.time()
            #print name
            if name.lower().endswith(".stl"):
                newname=name
                c=1
                while newname in self.models:
                    newname=name+"(%d)"%c
                    c+=1
                self.models[newname]=stltool.stl(name)
                self.models[newname].offsets=[0,0,0]
                #print time.time()-t
                self.l.Append([stlwrap(self.models[newname],newname)])
            self.Refresh()
            #print time.time()-t
        
    def move(self,event):
        if event.ButtonUp(wx.MOUSE_BTN_LEFT):
            if(self.initpos is not None):
                i=self.l.GetFirstSelected()
                if i != -1:
                    p=event.GetPositionTuple()
                    #print (p[0]-self.initpos[0]),(p[1]-self.initpos[1])
                    t=time.time()
                    m=self.models[self.l.GetItemText(i)]
                    m.offsets=[m.offsets[0]+0.5*(p[0]-self.initpos[0]),m.offsets[1]-0.5*(p[1]-self.initpos[1]),m.offsets[2]]
                    #self.models[self.l.GetItemText(i)]=self.models[self.l.GetItemText(i)].translate([0.5*(p[0]-self.initpos[0]),0.5*(p[1]-self.initpos[1]),0])
                    #print time.time()-t
                self.Refresh()
                self.initpos=None
        elif event.ButtonDown(wx.MOUSE_BTN_RIGHT):
            self.right(event)
        elif event.Dragging():
            if self.initpos is None:
                self.initpos=event.GetPositionTuple()
            self.Refresh()
            dc=wx.ClientDC(self)
            p=event.GetPositionTuple()
            dc.DrawLine(self.initpos[0],self.initpos[1],p[0],p[1])
            #print math.sqrt((p[0]-self.initpos[0])**2+(p[1]-self.initpos[1])**2)
                    
            del dc
        else:
            event.Skip()
        
    def cr(self):
        time.sleep(0.01)
        if(self.i!=self.previ):
            i=self.l.GetFirstSelected()
            if i != -1:
                o=self.models[self.l.GetItemText(i)].offsets
                self.models[self.l.GetItemText(i)]=self.models[self.l.GetItemText(i)].rotate([0,0,self.i-self.previ])
                self.models[self.l.GetItemText(i)].offsets=o
            self.previ=self.i
            wx.CallAfter(self.Refresh)
        self.triggered=0
        
    def rot(self, event):
        z=event.GetWheelRotation()
        s=self.l.GetFirstSelected()
        if self.prevsel!=s:
            self.i=0
            self.prevsel=s
        if z > 0:
            self.i-=1
        else:
            self.i+=1
        if not self.triggered:
            self.triggered=1
            threading.Thread(target=self.cr).start()
    
    def repaint(self,event):
        dc=wx.PaintDC(self)
        self.paint(dc=dc)
        
    def paint(self,coord1="x",coord2="y",dc=None):
        coords={"x":0,"y":1,"z":2}
        if dc is None:
            dc=wx.ClientDC(self)
        offset=[0,0]
        scale=2
        dc.SetPen(wx.Pen(wx.Colour(100,100,100)))
        for i in xrange(20):
            dc.DrawLine(0,i*scale*10,400,i*scale*10)
            dc.DrawLine(i*scale*10,0,i*scale*10,400)
        dc.SetPen(wx.Pen(wx.Colour(0,0,0)))
        for i in xrange(4):
            dc.DrawLine(0,i*scale*50,400,i*scale*50)
            dc.DrawLine(i*scale*50,0,i*scale*50,400)
        dc.SetBrush(wx.Brush(wx.Colour(128,255,128)))
        dc.SetPen(wx.Pen(wx.Colour(128,128,128)))
        t=time.time()
        for m in self.models.values():
            for i in m.facets:#random.sample(m.facets,min(100000,len(m.facets))):
                dc.DrawPolygon([wx.Point(offset[0]+scale*m.offsets[0]+scale*p[0],400-(offset[1]+scale*m.offsets[1]+scale*p[1])) for p in i[1]])
                #if(time.time()-t)>5:
                #    break
        del dc
        #print time.time()-t
        #s.export()
        
class stlwin(wx.Frame):
    def __init__(self,size=(400,500)):
        wx.Frame.__init__(self,None,title="Right-click to add a file",size=size)
        self.s=showstl(self,(400,500),(0,0))
        
if __name__ == '__main__':
    app = wx.App(False)
    main = stlwin()
    main.Show()
    app.MainLoop()

