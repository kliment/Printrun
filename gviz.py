import wx,time

class window(wx.Frame):
    def __init__(self):
        wx.Frame.__init__(self,None,title="Slicetest",size=(200,200))
        self.p=gviz(self,size=(200,200),bedsize=(200,200))
        s=time.time()
        for i in open("/home/kliment/designs/spinner/gearend_export.gcode"):
            self.p.addgcode(i)
        print time.time()-s
        self.p.Bind(wx.EVT_KEY_DOWN,self.key)
    def key(self, event):
        x=event.GetKeyCode()
        #print x
        if x==wx.WXK_UP:
            self.p.layerup()
        if x==wx.WXK_DOWN:
            self.p.layerdown()
    
        #print p.lines.keys()
        
class gviz(wx.Panel):
    def __init__(self,parent,size=(200,200),bedsize=(200,200)):
        wx.Panel.__init__(self,parent,-1,size=size)
        self.bedsize=bedsize
        self.lastpos=[0,0,0,0,0]
        self.Bind(wx.EVT_PAINT,self.paint)
        self.lines={}
        self.pens={}
        self.layers=[]
        self.layerindex=0
        self.scale=[min(float(size[0])/bedsize[0],float(size[1])/bedsize[1])]*2
        self.mainpen=wx.Pen(wx.Colour(0,0,0))
        self.fades=[wx.Pen(wx.Colour(150+20*i,150+20*i,150+20*i)) for i in xrange(6)]
        self.showall=0
        
    def clear(self):
        self.lastpos=[0,0,0,0,0]
        self.Bind(wx.EVT_PAINT,self.paint)
        self.lines={}
        self.pens={}
        self.layers=[]
        self.layerindex=0
        self.showall=0
        
    def layerup(self):
        if(self.layerindex+1<len(self.layers)):
            self.layerindex+=1
            self.Refresh()
    
    def layerdown(self):
        if(self.layerindex>0):
            self.layerindex-=1
            self.Refresh()
        
    def paint(self,event):
        dc=wx.PaintDC(self)
        dc.SetBackground(wx.Brush((250,250,200)))
        dc.Clear()
        if self.showall:
            l=[]
            for i in self.layers:
                dc.DrawLineList(l,self.fades[0])
                l=map(lambda x:(self.scale[0]*x[0],self.scale[1]*x[1],self.scale[0]*x[2],self.scale[1]*x[3],) ,self.lines[i])
                dc.DrawLineList(l,self.pens[i])
            return
        if self.layerindex<len(self.layers) and self.layers[self.layerindex] in self.lines.keys():
            for i in range(min(self.layerindex,6))[-6:]:
                #print i, self.layerindex, self.layerindex-i
                l=map(lambda x:(self.scale[0]*x[0],self.scale[1]*x[1],self.scale[0]*x[2],self.scale[1]*x[3],) ,self.lines[self.layers[self.layerindex-i-1]])
                dc.DrawLineList(l,self.fades[i])
            l=map(lambda x:(self.scale[0]*x[0],self.scale[1]*x[1],self.scale[0]*x[2],self.scale[1]*x[3],) ,self.lines[self.layers[self.layerindex]])
            dc.DrawLineList(l,self.pens[self.layers[self.layerindex]])
        del dc
        
    def showall(self,v):
        self.showall=v
        self.Refresh()
        
    def addgcode(self,gcode="M105"):
        if "g1" in gcode.lower():
            gcode=gcode.lower().split()
            target=self.lastpos[:]
            for i in gcode:
                if i[0]=="x":
                    target[0]=float(i[1:])
                elif i[0]=="y":
                    target[1]=float(i[1:])
                elif i[0]=="z":
                    target[2]=float(i[1:])
                elif i[0]=="e":
                    target[3]=float(i[1:])
                elif i[0]=="f":
                    target[4]=float(i[1:])
            #draw line
            if not target[2] in self.lines.keys():
                self.lines[target[2]]=[]
                self.pens[target[2]]=[]
                self.layers+=[target[2]]
            self.lines[target[2]]+=[(self.lastpos[0],self.lastpos[1],target[0],target[1])]
            self.pens[target[2]]+=[self.mainpen]
            self.lastpos=target
            
            
if __name__ == '__main__':
    app = wx.App(False)
    main = window()
    main.Show()
    app.MainLoop()

