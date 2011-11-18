#!/usr/bin/env python
import wx,time,random,threading,os,math
import stltool
glview=True
try:
    import stlview
except:
    glview=False

def translate(l): return l

def rotate(l): return l

def import_stl(s): return s

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
        #self.SetBackgroundColour((0,0,0))
        #wx.FutureCall(200,self.paint)
        self.i=0
        self.parent=parent
        self.previ=0
        self.Bind(wx.EVT_MOUSEWHEEL,self.rot)
        self.Bind(wx.EVT_MOUSE_EVENTS,self.move)
        self.Bind(wx.EVT_PAINT,self.repaint)
        #self.s=stltool.stl("sphere.stl").scale([2,1,1])
        self.triggered=0
        self.initpos=None
        self.prevsel=-1

    def drawmodel(self,m,scale):
        m.bitmap=wx.EmptyBitmap(800,800,32)
        dc=wx.MemoryDC()
        dc.SelectObject(m.bitmap)
        dc.SetBackground(wx.Brush((0,0,0,0)))
        dc.SetBrush(wx.Brush((0,0,0,255)))
        #dc.DrawRectangle(-1,-1,10000,10000)
        dc.SetBrush(wx.Brush(wx.Colour(128,255,128)))
        dc.SetPen(wx.Pen(wx.Colour(128,128,128)))
        #m.offsets=[10,10,0]
        #print m.offsets,m.dims
        for i in m.facets:#random.sample(m.facets,min(100000,len(m.facets))):
            dc.DrawPolygon([wx.Point(400+scale*p[0],(400-scale*p[1])) for p in i[1]])
            #if(time.time()-t)>5:
            #    break
        dc.SelectObject(wx.NullBitmap)
        m.bitmap.SetMask(wx.Mask(m.bitmap,wx.Colour(0,0,0,255)))
    
            
    def move(self,event):
        if event.ButtonUp(wx.MOUSE_BTN_LEFT):
            if(self.initpos is not None):
                i=self.parent.l.GetSelection()
                if i != wx.NOT_FOUND:
                    p=event.GetPositionTuple()
                    #print (p[0]-self.initpos[0]),(p[1]-self.initpos[1])
                    t=time.time()
                    m=self.parent.models[self.parent.l.GetString(i)]
                    m.offsets=[m.offsets[0]+0.5*(p[0]-self.initpos[0]),m.offsets[1]-0.5*(p[1]-self.initpos[1]),m.offsets[2]]
                    #self.models[self.l.GetItemText(i)]=self.models[self.l.GetItemText(i)].translate([0.5*(p[0]-self.initpos[0]),0.5*(p[1]-self.initpos[1]),0])
                    #print time.time()-t
                self.Refresh()
                self.initpos=None
        elif event.ButtonDown(wx.MOUSE_BTN_RIGHT):
            self.parent.right(event)
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
        
    def rotateafter(self):
        if(self.i!=self.previ):
            i=self.parent.l.GetSelection()
            if i != wx.NOT_FOUND:
                #o=self.models[self.l.GetItemText(i)].offsets
                self.parent.models[self.parent.l.GetString(i)].rot-=5*(self.i-self.previ)
                #self.models[self.l.GetItemText(i)].offsets=o
            self.previ=self.i
            self.Refresh()
    def cr(self):
        time.sleep(0.01)
        wx.CallAfter(self.rotateafter)
        self.triggered=0
        
    def rot(self, event):
        z=event.GetWheelRotation()
        s=self.parent.l.GetSelection()
        if self.prevsel!=s:
            self.i=0
            self.prevsel=s
        if z < 0:
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
        dcs=wx.MemoryDC()
        for m in self.parent.models.values():
            b=m.bitmap
                #print b
            im=b.ConvertToImage()
                #print im
            imgc = wx.Point( im.GetWidth()/2,im.GetHeight()/2 )
                #print math.radians(5*(self.i-self.previ))
            im= im.Rotate( math.radians(m.rot), imgc, 0)
            bm=wx.BitmapFromImage(im)
            dcs.SelectObject(bm)
            bsz=bm.GetSize()
            dc.Blit(scale*m.offsets[0]-bsz[0]/2,400-(scale*m.offsets[1]+bsz[1]/2),bsz[0],bsz[1],dcs,0,0,useMask=1)
            #for i in m.facets:#random.sample(m.facets,min(100000,len(m.facets))):
            #    dc.DrawPolygon([wx.Point(offset[0]+scale*m.offsets[0]+scale*p[0],400-(offset[1]+scale*m.offsets[1]+scale*p[1])) for p in i[1]])
                #if(time.time()-t)>5:
                #    break
        del dc
        #print time.time()-t
        #s.export()
        
class stlwin(wx.Frame):
    def __init__(self,size=(800,580),callback=None,parent=None):
        wx.Frame.__init__(self,parent,title="Plate building tool",size=size)
        self.SetIcon(wx.Icon("plater.ico",wx.BITMAP_TYPE_ICO))
        self.mainsizer = wx.BoxSizer(wx.HORIZONTAL)
        self.panel=wx.Panel(self,-1,size=(150,600),pos=(0,0))
        self.panel.SetBackgroundColour((10,10,10))
        self.l=wx.ListBox(self.panel,size=(300,180),pos=(0,30))
        self.cl=wx.Button(self.panel,label="Clear",pos=(0,205))
        self.lb=wx.Button(self.panel,label="Load",pos=(0,0))
        if(callback is None):
            self.eb=wx.Button(self.panel,label="Export",pos=(100,0))
            self.eb.Bind(wx.EVT_BUTTON,self.export)
        else:
            self.eb=wx.Button(self.panel,label="Done",pos=(100,0))
            self.eb.Bind(wx.EVT_BUTTON,lambda e:self.done(e,callback))
            self.eb=wx.Button(self.panel,label="Cancel",pos=(200,0))
            self.eb.Bind(wx.EVT_BUTTON,lambda e:self.Destroy())
        self.sb=wx.Button(self.panel,label="Snap to Z=0",pos=(00,255))
        self.cb=wx.Button(self.panel,label="Put at 100,100",pos=(0,280))
        self.db=wx.Button(self.panel,label="Delete",pos=(0,305))
        self.ab=wx.Button(self.panel,label="Auto",pos=(0,330))
        self.cl.Bind(wx.EVT_BUTTON,self.clear)
        self.lb.Bind(wx.EVT_BUTTON,self.right)
        self.sb.Bind(wx.EVT_BUTTON,self.snap)
        self.cb.Bind(wx.EVT_BUTTON,self.center)
        self.db.Bind(wx.EVT_BUTTON,self.delete)
        self.ab.Bind(wx.EVT_BUTTON,self.autoplate)
        self.basedir="."
        self.models={}
        self.SetBackgroundColour((10,10,10))
        self.mainsizer.Add(self.panel)
        #self.mainsizer.AddSpacer(10)
        if glview:
            self.s=stlview.TestGlPanel(self,(580,580))
        else:
            self.s=showstl(self,(580,580),(0,0))
        self.mainsizer.Add(self.s, 1, wx.EXPAND)
        self.SetSizer(self.mainsizer)
        #self.mainsizer.Fit(self)
        self.Layout()
        
        #self.SetClientSize(size)
    
    def autoplate(self,event):
        print "Autoplating"
        separation = 2
        bedsize = [200,200,100]
        cursor = [0,0,0]
        newrow = 0
        max = [0,0]
        for i in self.models:
            self.models[i].offsets[2]=-1.0*self.models[i].dims[4]
            x = abs(self.models[i].dims[0] - self.models[i].dims[1])
            y = abs(self.models[i].dims[2] - self.models[i].dims[3])
            centre = [x/2, y/2]
            centreoffset = [self.models[i].dims[0] + centre[0], self.models[i].dims[2] + centre[1]]
            if (cursor[0]+x+separation) >= bedsize[0]:
                cursor[0] = 0
                cursor[1] += newrow+separation
                newrow = 0
            if (newrow == 0) or (newrow < y):
                newrow = y
            #To the person who works out why the offsets are applied differently here:
            # Good job, it confused the hell out of me.
            self.models[i].offsets[0] = cursor[0] + centre[0] - centreoffset[0]
            self.models[i].offsets[1] = cursor[1] + centre[1] - centreoffset[1]
            if (max[0] == 0) or (max[0] < (cursor[0]+x)):
                max[0] = cursor[0]+x
            if (max[1] == 0) or (max[1] < (cursor[1]+x)):
                max[1] = cursor[1]+x
            cursor[0] += x+separation
            if (cursor[1]+y) >= bedsize[1]:
                print "Bed full, sorry sir :("
                self.Refresh()
                return
        centreoffset = [(bedsize[0]-max[0])/2,(bedsize[1]-max[1])/2]
        for i in self.models:
            self.models[i].offsets[0] += centreoffset[0]
            self.models[i].offsets[1] += centreoffset[1]
        self.Refresh()
    
        
    def clear(self,event):
        result = wx.MessageBox('Are you sure you want to clear the grid? All unsaved changes will be lost.', 'Clear the grid?', 
            wx.YES_NO | wx.ICON_QUESTION)
        if (result == 2):
            self.models={}
            self.l.Clear()
            self.Refresh()
    
    def center(self,event):
        i=self.l.GetSelection()
        if i != -1:
                m=self.models[self.l.GetString(i)]
                m.offsets=[100,100,m.offsets[2]]
                self.Refresh()

    def snap(self,event):
        i=self.l.GetSelection()
        if i != -1:
                m=self.models[self.l.GetString(i)]
                m.offsets[2]=-1.0*min(m.facetsminz)[0]
                #print m.offsets[2]
                self.Refresh()

    def delete(self,event):
        i=self.l.GetSelection()
        if i != -1:
                del self.models[self.l.GetString(i)]
                self.l.Delete(i)
                self.l.Select(self.l.GetCount()-1)
                self.Refresh()

    def done(self,event,cb):
        import os,time
        try:
            os.mkdir("tempstl")
        except:
            pass
        name="tempstl/"+str(int(time.time())%10000)+".stl"
        self.writefiles(name)
        if cb is not None:
            cb(name)
        self.Destroy()
        
        
    def export(self,event):
        dlg=wx.FileDialog(self,"Pick file to save to",self.basedir,style=wx.FD_SAVE)
        dlg.SetWildcard("STL files (;*.stl;)")
        if(dlg.ShowModal() == wx.ID_OK):
            name=dlg.GetPath()
            self.writefiles(name)
            
    def writefiles(self,name):
        sf=open(name.replace(".","_")+".scad","w")
        facets=[]
        for i in self.models.values():
            
            r=i.rot
            o=i.offsets
            sf.write('translate([%s,%s,%s]) rotate([0,0,%s]) import_stl("%s");\n'%(str(o[0]),str(o[1]),str(o[2]),r,os.path.split(i.filename)[1]))
            if r != 0:
                i=i.rotate([0,0,r])
            if o != [0,0,0]:
                i=i.translate([o[0],o[1],o[2]])
            facets+=i.facets
        sf.close()
        stltool.emitstl(name,facets,"plater_export")
        print "wrote ",name
        
    def right(self,event):
        dlg=wx.FileDialog(self,"Pick file to load",self.basedir,style=wx.FD_OPEN|wx.FD_FILE_MUST_EXIST)
        dlg.SetWildcard("STL files (;*.stl;)|*.stl|OpenSCAD files (;*.scad;)|*.scad")
        if(dlg.ShowModal() == wx.ID_OK):
            name=dlg.GetPath()
            if (name.lower().endswith(".stl")):
                self.load_stl(event,name)
            elif (name.lower().endswith(".scad")):
                self.load_scad(event,name)
    
    def load_scad(self,event,name):
        lf=open(name)
        s=[i.replace("\n","").replace("\r","").replace(";","") for i in lf]
        lf.close()

        for i in s:
            parts = i.split()
            translate_list = eval(parts[0])
            rotate_list = eval(parts[1])
            stl_file = eval(parts[2])
            
            newname=os.path.split(stl_file.lower())[1]
            c=1
            while newname in self.models:
                newname=os.path.split(stl_file.lower())[1]
                newname=newname+"(%d)"%c
                c+=1
            stl_path = os.path.join(os.path.split(name)[0:len(os.path.split(stl_file))-1])
            stl_full_path = os.path.join(stl_path[0],str(stl_file))
            self.load_stl_into_model(stl_full_path,stl_file,translate_list,rotate_list[2])

    def load_stl(self,event,name):
        if not(os.path.exists(name)):
            return
        path = os.path.split(name)[0]
        self.basedir=path
        t=time.time()
        #print name
        if name.lower().endswith(".stl"):
            #Filter out the path, just show the STL filename.
            self.load_stl_into_model(name,name)
        self.Refresh()
        #print time.time()-t

    def load_stl_into_model(self,path,name,offset=[0,0,0],rotation=0,scale=[1.0,1.0,1.0]):
        newname=os.path.split(name.lower())[1]
        c=1
        while newname in self.models:
            newname=os.path.split(name.lower())[1]
            newname=newname+"(%d)"%c
            c+=1
        self.models[newname]=stltool.stl(path)
        self.models[newname].offsets=offset
        self.models[newname].rot=rotation
        self.models[newname].scale=scale
        self.models[newname].filename=name
        minx,miny,minz,maxx,maxy,maxz=(10000,10000,10000,0,0,0)
        for i in self.models[newname].facets:
            for j in i[1]:
                if j[0]<minx:
                    minx=j[0]
                if j[1]<miny:
                    miny=j[1]
                if j[2]<minz:
                    minz=j[2]
                if j[0]>maxx:
                    maxx=j[0]
                if j[1]>maxy:
                    maxy=j[1]
                if j[2]>maxz:
                    maxz=j[2]
        self.models[newname].dims=[minx,maxx,miny,maxy,minz,maxz]
        #if minx<0:
        #    self.models[newname].offsets[0]=-minx
        #if miny<0:
        #    self.models[newname].offsets[1]=-miny
        self.s.drawmodel(self.models[newname],2)
        
        #print time.time()-t
        self.l.Append(newname)
        i=self.l.GetSelection()
        if i==wx.NOT_FOUND:
            self.l.Select(0)
    
        self.l.Select(self.l.GetCount()-1)
    
        
if __name__ == '__main__':
    app = wx.App(False)
    main = stlwin()
    main.Show()
    app.MainLoop()

