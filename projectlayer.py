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

import xml.etree.ElementTree
import wx
import time

def parsesvg(name):
    et= xml.etree.ElementTree.ElementTree(file=name)
    zlast=0
    zdiff=0
    ol=[]
    for i in et.findall("{http://www.w3.org/2000/svg}g")[0].findall("{http://www.w3.org/2000/svg}g"):
        z=float(i.get('id').split("z:")[-1])
        zdiff=z-zlast
        zlast=z
        path=i.find('{http://www.w3.org/2000/svg}path')
        ol+=[(path.get("d").split("z"))[:-1]]
    return ol,zdiff
    

class dispframe(wx.Frame):
    def __init__(self, parent, title, res=(1600,1200),printer=None):
        wx.Frame.__init__(self, parent=parent, title=title)
        self.p=printer
        self.pic=wx.StaticBitmap(self)
        self.bitmap=wx.EmptyBitmap(*res)
        self.SetBackgroundColour("black")
        self.pic.Hide()
        self.pen=wx.Pen("white")
        self.brush=wx.Brush("white")
        self.SetDoubleBuffered(True)
        self.Show()
    def drawlayer(self,svg):
        try:
            dc=wx.MemoryDC()
            dc.SelectObject(self.bitmap)
            dc.SetBackground(wx.Brush("black"))
            dc.Clear()
            dc.SetPen(self.pen)
            dc.SetBrush(self.brush)
            for i in svg:
                #print i
                points=[wx.Point(*map(lambda x:int(round(float(x)*self.scale)),j.strip().split())) for j in i.strip().split("M")[1].split("L")]
                dc.DrawPolygon(points,self.size[0]/2,self.size[1]/2)
                    
                
            dc.SelectObject(wx.NullBitmap)
            self.pic.SetBitmap(self.bitmap)
            self.pic.Show()
            self.Refresh()
        except:
            pass
            
    def nextimg(self,event):
        if self.index<len(self.layers):
            i=self.index
            #print self.layers[i]
            print i
            wx.CallAfter(self.drawlayer,self.layers[i])
            if self.p!=None:
                self.p.send_now("G91")
                self.p.send_now("G1 Z%f F300"%(self.thickness,))
                self.p.send_now("G90")
            
            self.index+=1
        else:
            print "end"
            wx.CallAfter(self.pic.Hide)
            wx.CallAfter(self.Refresh)
            wx.CallAfter(self.ShowFullScreen,0)
            wx.CallAfter(self.timer.Stop)
            
        
    def present(self,layers,interval=0.5,thickness=0.4,scale=20,size=(800,600)):
        wx.CallAfter(self.pic.Hide)
        wx.CallAfter(self.Refresh)
        self.layers=layers
        self.scale=scale
        self.thickness=thickness
        self.index=0
        self.size=size
        self.timer=wx.Timer(self,1)
        self.timer.Bind(wx.EVT_TIMER,self.nextimg)
        self.Bind(wx.EVT_TIMER,self.nextimg)
        self.timer.Start(1000*interval)
        #print "x"


class setframe(wx.Frame):
    
    def __init__(self,parent,printer=None):
        wx.Frame.__init__(self,parent,title="Projector setup")
        self.f=dispframe(None,"",printer=printer)
        self.panel=wx.Panel(self)
        self.panel.SetBackgroundColour("orange")
        self.bload=wx.Button(self.panel,-1,"Load",pos=(0,0))
        self.bload.Bind(wx.EVT_BUTTON,self.loadfile)
        wx.StaticText(self.panel,-1,"Layer:",pos=(0,30))
        wx.StaticText(self.panel,-1,"mm",pos=(130,30))
        self.thickness=wx.TextCtrl(self.panel,-1,"0.5",pos=(50,30))
        wx.StaticText(self.panel,-1,"Interval:",pos=(0,60))
        wx.StaticText(self.panel,-1,"s",pos=(130,60))
        self.interval=wx.TextCtrl(self.panel,-1,"0.5",pos=(50,60))
        wx.StaticText(self.panel,-1,"Scale:",pos=(0,90))
        wx.StaticText(self.panel,-1,"x",pos=(130,90))
        self.scale=wx.TextCtrl(self.panel,-1,"10",pos=(50,90))
        wx.StaticText(self.panel,-1,"X:",pos=(160,30))
        self.X=wx.TextCtrl(self.panel,-1,"800",pos=(180,30))
        wx.StaticText(self.panel,-1,"Y:",pos=(160,60))
        self.Y=wx.TextCtrl(self.panel,-1,"600",pos=(180,60))
        self.bload=wx.Button(self.panel,-1,"Present",pos=(0,150))
        self.bload.Bind(wx.EVT_BUTTON,self.startdisplay)
        self.Show()
        
    def loadfile(self,event):
        dlg=wx.FileDialog(self,("Open file to print"),style=wx.FD_OPEN|wx.FD_FILE_MUST_EXIST)
        dlg.SetWildcard(("Skeinforge svg files (;*.svg;*.SVG;)"))
        if(dlg.ShowModal() == wx.ID_OK):
            name=dlg.GetPath()
            import os
            if not(os.path.exists(name)):
                self.status.SetStatusText(("File not found!"))
                return
            layers=parsesvg(name)
            print "Layer thickness detected:",layers[1], "mm"
            print len(layers[0]), "layers found, total height", layers[1]*len(layers[0]), "mm"
            self.thickness.SetValue(str(layers[1]))
            self.layers=layers
        

    def startdisplay(self,event):
        self.f.Raise()
        self.f.ShowFullScreen(1)
        l=self.layers[0][:]
        #l=list(reversed(l))
        self.f.present(l,thickness=float(self.thickness.GetValue()),interval=float(self.interval.GetValue()),scale=float(self.scale.GetValue()), size=(float(self.X.GetValue()),float(self.Y.GetValue())))

if __name__=="__main__":
    a=wx.App()
    setframe(None).Show()
    a.MainLoop()
    
