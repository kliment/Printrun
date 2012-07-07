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
import wx.lib.agw.floatspin as floatspin
import os
import zipfile
import tempfile
import shutil
import svg.document as wxpsvgdocument
import imghdr
    
class dispframe(wx.Frame):
    def __init__(self, parent, title, res=(1024, 768), printer=None, scale=1.0, offset=(0,0)):
        wx.Frame.__init__(self, parent=parent, title=title, size=res)
        self.p = printer
        self.pic = wx.StaticBitmap(self)
        self.bitmap = wx.EmptyBitmap(*res)
        self.bbitmap = wx.EmptyBitmap(*res)
        self.slicer = 'Skeinforge'
        dc = wx.MemoryDC()
        dc.SelectObject(self.bbitmap)
        dc.SetBackground(wx.Brush("black"))
        dc.Clear()
        dc.SelectObject(wx.NullBitmap)

        self.SetBackgroundColour("black")
        self.pic.Hide()
        self.pen = wx.Pen("white")
        self.brush = wx.Brush("white")
        self.SetDoubleBuffered(True)
        self.Show()
        
        self.scale = scale
        self.index = 0
        self.size = res
        self.offset = offset

    def clearlayer(self):
        try:
            dc = wx.MemoryDC()
            dc.SelectObject(self.bitmap)
            dc.SetBackground(wx.Brush("black"))
            dc.Clear()
            self.pic.SetBitmap(self.bitmap)
            self.pic.Show()
            self.Refresh()
        except:
            raise
            pass
        
    def resize(self, res=(1024, 768)):
        self.bitmap = wx.EmptyBitmap(*res)
        self.bbitmap = wx.EmptyBitmap(*res)
        dc = wx.MemoryDC()
        dc.SelectObject(self.bbitmap)
        dc.SetBackground(wx.Brush("black"))
        dc.Clear()
        dc.SelectObject(wx.NullBitmap)
        
    def drawlayer(self, image, slicer):
        try:
            dc = wx.MemoryDC()
            dc.SelectObject(self.bitmap)
            dc.SetBackground(wx.Brush("black"))
            dc.Clear()
            dc.SetPen(self.pen)
            dc.SetBrush(self.brush)

            if slicer == 'Skeinforge':
                for i in image:
                    points = [wx.Point(*map(lambda x:int(round(float(x) * self.scale)), j.strip().split())) for j in i.strip().split("M")[1].split("L")]
                    dc.DrawPolygon(points, self.size[0] / 2, self.size[1] / 2)
            elif slicer == 'Slic3r':
                gc = wx.GraphicsContext_Create(dc)            
                gc.Translate(*self.offset)
                gc.Scale(self.scale, self.scale)
                wxpsvgdocument.SVGDocument(image).render(gc)
            elif slicer == 'bitmap':
                dc.DrawBitmap(wx.BitmapFromImage(image.Scale(image.Width*self.scale, image.Height*self.scale)), self.offset[0], -self.offset[1], True)
            else:
                raise Exception(self.slicer + " is an unknown method.")
            self.pic.SetBitmap(self.bitmap)
            self.pic.Show()
            self.Refresh()            
            
        except:
            raise
            pass
            
    def showimgdelay(self, image):
        self.drawlayer(image,self.slicer)
        print "Showing"
        self.pic.Show()
        self.Refresh()

    def rise(self):
        print "Rising"
        if self.p != None and self.p.online:
                self.p.send_now("G91")
                self.p.send_now("G1 Z%f F200" % (3,))
                self.p.send_now("G1 Z-%f F200" % (3-self.thickness,))
                self.p.send_now("G90")
    def hidePic(self):
        print "Hiding"
        self.pic.Hide()
        
    def hidePicAndRise(self):
        wx.CallAfter(self.hidePic)
        wx.FutureCall(250, self.rise)
                    
    def nextimg(self, event):
        if self.index < len(self.layers):
            i = self.index
            print i
            wx.CallAfter(self.showimgdelay, self.layers[i])
            wx.FutureCall(1000 * self.interval, self.hidePicAndRise)
            self.index += 1
        else:
            print "end"
            wx.CallAfter(self.pic.Hide)
            wx.CallAfter(self.Refresh)
            wx.CallAfter(self.timer.Stop)            
        
    def present(self, layers, interval=0.5, pause=0.2, thickness=0.4, scale=20, size=(1024, 768), offset=(0, 0)):
        wx.CallAfter(self.pic.Hide)
        wx.CallAfter(self.Refresh)
        self.layers = layers
        self.scale = scale
        self.thickness = thickness
        self.index = 0
        self.size = size
        self.interval = interval
        self.offset = offset
        self.timer = wx.Timer(self, 1)
        self.timer.Bind(wx.EVT_TIMER, self.nextimg)
        self.Bind(wx.EVT_TIMER, self.nextimg)
        self.timer.Start(1000 * interval + 1000 * pause)

class setframe(wx.Frame):
    
    def __init__(self, parent, printer=None):
        wx.Frame.__init__(self, parent, title="Projector setup", size=(400,400))
        self.f = dispframe(None, "", printer=printer)
        self.panel = wx.Panel(self)
        self.panel.SetBackgroundColour("orange")
        self.bload = wx.Button(self.panel, -1, "Load", pos=(0, 0))
        self.bload.Bind(wx.EVT_BUTTON, self.loadfile)
        
        leftlabelXPos = 0
        leftValueXPos = 70
        rightlabelXPos = 180
        rightValueXPos = 230
        
        wx.StaticText(self.panel, -1, "Layer (mm):", pos=(leftlabelXPos, 30))
        self.thickness = wx.TextCtrl(self.panel, -1, "0.3", pos=(leftValueXPos, 30))

        wx.StaticText(self.panel, -1, "Exposure (s):", pos=(leftlabelXPos, 60))
        self.interval = wx.TextCtrl(self.panel, -1, "3", pos=(leftValueXPos, 60))

        wx.StaticText(self.panel, -1, "Blank (s):", pos=(leftlabelXPos, 90))
        self.delay = wx.TextCtrl(self.panel, -1, "2", pos=(leftValueXPos, 90))

        wx.StaticText(self.panel, -1, "Scale:", pos=(leftlabelXPos, 120))
        self.scale = floatspin.FloatSpin(self.panel, -1, pos=(leftValueXPos, 120), value=1.0, increment=0.1, digits=1 )
        self.scale.Bind(floatspin.EVT_FLOATSPIN, self.updatescale)
        
        wx.StaticText(self.panel, -1, "X:", pos=(rightlabelXPos, 30))
        self.X = wx.SpinCtrl(self.panel, -1, '1024', pos=(rightValueXPos, 30), max=999999)
        self.X.Bind(wx.EVT_SPINCTRL, self.updateresolution)

        wx.StaticText(self.panel, -1, "Y:", pos=(rightlabelXPos, 60))
        self.Y = wx.SpinCtrl(self.panel, -1, '768', pos=(rightValueXPos, 60), max=999999)
        self.Y.Bind(wx.EVT_SPINCTRL, self.updateresolution)
        
        wx.StaticText(self.panel, -1, "OffsetX:", pos=(rightlabelXPos, 90))
        self.offsetX = floatspin.FloatSpin(self.panel, -1, pos=(rightValueXPos, 90), value=0.0, increment=1, digits=1 )
        self.offsetX.Bind(floatspin.EVT_FLOATSPIN, self.updateoffset)

        wx.StaticText(self.panel, -1, "OffsetY:", pos=(rightlabelXPos, 120))
        self.offsetY = floatspin.FloatSpin(self.panel, -1, pos=(rightValueXPos, 120), value=0.0, increment=1, digits=1 )
        self.offsetY.Bind(floatspin.EVT_FLOATSPIN, self.updateoffset)
        
        self.bload = wx.Button(self.panel, -1, "Present", pos=(leftlabelXPos, 150))
        self.bload.Bind(wx.EVT_BUTTON, self.startdisplay)
        
        self.pause = wx.Button(self.panel, -1, "Pause", pos=(leftlabelXPos, 180))
        self.pause.Bind(wx.EVT_BUTTON, self.pausepresent)
        
        wx.StaticText(self.panel, -1, "Fullscreen:", pos=(rightlabelXPos, 150))
        self.fullscreen = wx.CheckBox(self.panel, -1, pos=(rightValueXPos, 150))
        self.fullscreen.Bind(wx.EVT_CHECKBOX, self.updatefullscreen)
        
        wx.StaticText(self.panel, -1, "Calibrate:", pos=(rightlabelXPos, 180))
        self.calibrate = wx.CheckBox(self.panel, -1, pos=(rightValueXPos, 180))
        self.calibrate.Bind(wx.EVT_CHECKBOX, self.startcalibrate)
        
        wx.StaticText(self.panel, -1, "ProjectedX (mm):", pos=(rightlabelXPos, 210))
        self.projectedXmm = floatspin.FloatSpin(self.panel, -1, pos=(rightValueXPos+40, 210), value=150.0, increment=1, digits=1 )
        self.projectedXmm.Bind(floatspin.EVT_FLOATSPIN, self.updateprojectedXmm)

        wx.StaticText(self.panel, -1, "1st Layer:", pos=(rightlabelXPos, 240))
        self.showfirstlayer = wx.CheckBox(self.panel, -1, pos=(rightValueXPos, 240))
        self.showfirstlayer.Bind(wx.EVT_CHECKBOX, self.presentfirstlayer)
        
        wx.StaticText(self.panel, -1, "Raft:", pos=(rightlabelXPos, 270))
        self.raft = wx.CheckBox(self.panel, -1, pos=(rightValueXPos, 270))
        self.raft.Bind(wx.EVT_CHECKBOX, self.showRaft)
        
        wx.StaticText(self.panel, -1, "Red?:", pos=(rightlabelXPos +70, 270))
        self.previewRaft = wx.CheckBox(self.panel, -1, pos=(rightValueXPos +70, 270))
        self.previewRaft.Bind(wx.EVT_CHECKBOX, self.showRaft)
        
        wx.StaticText(self.panel, -1, "Raft Grid (mm):", pos=(rightlabelXPos, 300))
        self.raftGridSize = floatspin.FloatSpin(self.panel, -1, pos=(rightValueXPos +40, 300), value=5.0, increment=0.1, digits=1 )
        self.raftGridSize.Bind(floatspin.EVT_FLOATSPIN, self.showRaft)
                
        self.Show()

    def __del__(self):
        if hasattr(self, 'image_dir') and self.image_dir != '':
            shutil.rmtree(self.image_dir)
        if self.f:
            self.f.Destroy()
            
    def parsesvg(self, name):
        et = xml.etree.ElementTree.ElementTree(file=name)
        #xml.etree.ElementTree.dump(et)
        
        slicer = 'Slic3r' if et.getroot().find('{http://www.w3.org/2000/svg}metadata') == None else 'Skeinforge'
        zlast = 0
        zdiff = 0
        ol = []
        if (slicer == 'Slic3r'):
            height = et.getroot().get('height')
            width = et.getroot().get('width')
            
            for i in et.findall("{http://www.w3.org/2000/svg}g"):
                z = float(i.get('{http://slic3r.org/namespaces/slic3r}z'))
                zdiff = z - zlast
                zlast = z
    
                svgSnippet = xml.etree.ElementTree.Element('{http://www.w3.org/2000/svg}svg')
                svgSnippet.set('height', height + 'mm')
                svgSnippet.set('width', width + 'mm')
                svgSnippet.set('viewBox', '0 0 ' + height + ' ' + width)
                svgSnippet.append(i)
    
                ol += [svgSnippet]
        else :
            for i in et.findall("{http://www.w3.org/2000/svg}g")[0].findall("{http://www.w3.org/2000/svg}g"):
                z = float(i.get('id').split("z:")[-1])
                zdiff = z - zlast
                zlast = z
                path = i.find('{http://www.w3.org/2000/svg}path')
                ol += [(path.get("d").split("z"))[:-1]]
        return ol, zdiff, slicer
    
    def parse3DLPzip(self, name):
        if not zipfile.is_zipfile(name):
            raise Exception(name + " is not a zip file!")
        acceptedImageTypes = ['gif','tiff','jpg','jpeg','bmp','png']
        zipFile = zipfile.ZipFile(name, 'r')
        self.image_dir = tempfile.mkdtemp()
        zipFile.extractall(self.image_dir)
        ol = []
        imagefiles = os.listdir(self.image_dir)
        imagefiles.sort()
        for f in imagefiles:
            path = os.path.join(self.image_dir, f)
            if os.path.isfile(path) and imghdr.what(path) in acceptedImageTypes:
                ol.append(wx.Image(path))
        return ol, -1, "bitmap"
        
    def loadfile(self, event):
        dlg = wx.FileDialog(self, ("Open file to print"), style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
        dlg.SetWildcard(("Slic3r or Skeinforge svg files (;*.svg;*.SVG;);3DLP Zip (;*.3dlp.zip;)"))
        if(dlg.ShowModal() == wx.ID_OK):
            name = dlg.GetPath()
            if not(os.path.exists(name)):
                self.status.SetStatusText(("File not found!"))
                return
            if name.endswith(".3dlp.zip"):
                layers = self.parse3DLPzip(name)
                layerHeight = float(self.thickness.GetValue())
            else:
                layers = self.parsesvg(name)
                layerHeight = layers[1]
                self.thickness.SetValue(str(layers[1]))
                print "Layer thickness detected:", layerHeight, "mm"
            print len(layers[0]), "layers found, total height", layerHeight * len(layers[0]), "mm"
            self.layers = layers
            self.f.slicer = layers[2]
            if (self.f.slicer == 'Slic3r'):
                self.scale.SetValue(3.5)
                print "Slic3r SVG detected: setting scale to 3.5 to correct size displayed."
        dlg.Destroy()

    def startcalibrate(self, event):
        if self.calibrate.IsChecked():
            self.f.Raise()
            self.f.offset=(float(self.offsetX.GetValue()), float(self.offsetY.GetValue()))
            self.f.scale=1.0
            resolutionXPixels = int(self.X.GetValue())
            resolutionYPixels = int(self.Y.GetValue())
            
            gridBitmap = wx.EmptyBitmap(resolutionXPixels,resolutionYPixels)
            dc = wx.MemoryDC()
            dc.SelectObject(gridBitmap)
            dc.SetBackground(wx.Brush("black"))
            dc.Clear()
            
            dc.SetPen(wx.Pen("red",7))
            dc.DrawLine(0,0,resolutionXPixels,0);
            dc.DrawLine(0,0,0,resolutionYPixels);
            dc.DrawLine(resolutionXPixels,0,resolutionXPixels,resolutionYPixels);
            dc.DrawLine(0,resolutionYPixels,resolutionXPixels,resolutionYPixels);
            
            dc.SetPen(wx.Pen("red",2))
            aspectRatio = float(resolutionXPixels)/float(resolutionYPixels)
            
            projectedXmm = float(self.projectedXmm.GetValue())            
            projectedYmm = round(projectedXmm/aspectRatio)
            
            pixelsXPerMM = resolutionXPixels / projectedXmm
            pixelsYPerMM = resolutionYPixels / projectedYmm
            
            gridCountX = int(projectedXmm/10)
            gridCountY = int(projectedYmm/10)
            
            for y in xrange(0,gridCountY+1):
                for x in xrange(0,gridCountX+1):
                    dc.DrawLine(0,y*(pixelsYPerMM*10),resolutionXPixels,y*(pixelsYPerMM*10));
                    dc.DrawLine(x*(pixelsXPerMM*10),0,x*(pixelsXPerMM*10),resolutionYPixels);

            self.f.drawlayer(gridBitmap.ConvertToImage(), 'bitmap')
        else:
            self.f.scale=float(self.scale.GetValue())
            self.f.clearlayer()
    
    def showRaft(self, event):
        if self.raft.IsChecked():
            self.f.Raise()
            self.f.offset=(float(self.offsetX.GetValue()), -float(self.offsetY.GetValue()))
            self.f.scale=1.0
            resolutionXPixels = int(self.X.GetValue())
            resolutionYPixels = int(self.Y.GetValue())
            
            gridBitmap = wx.EmptyBitmap(resolutionXPixels,resolutionYPixels)
            dc = wx.MemoryDC()
            dc.SelectObject(gridBitmap)
            dc.SetBackground(wx.Brush("black"))
            dc.Clear()
            
            if (self.previewRaft.IsChecked()):
                raftColor = "red"
            else:
                raftColor = "white"
            
            dc.SetPen(wx.Pen(raftColor,2))
            aspectRatio = float(resolutionXPixels)/float(resolutionYPixels)

            projectedXmm = float(self.projectedXmm.GetValue())                        
            projectedYmm = round(projectedXmm/aspectRatio)            
            
            pixelsXPerMM = resolutionXPixels / projectedXmm
            pixelsYPerMM = resolutionYPixels / projectedYmm            

            if (hasattr(self, 'layers')):
                xDist = float(self.layers[0][0].get('width').replace('m',''))
                yDist = float(self.layers[0][0].get('height').replace('m',''))
            else:
                xDist = projectedXmm
                yDist = projectedYmm
            
            gridSize = self.raftGridSize.GetValue()
            gridCountX = int(xDist/gridSize)
            gridCountY = int(yDist/gridSize)
            
            xDistPixels = xDist * pixelsXPerMM
            yDistPixels = yDist * pixelsYPerMM
            
            # border
            dc.DrawLine(0,0,xDistPixels,0);
            dc.DrawLine(0,0,0,yDistPixels);
            dc.DrawLine(xDistPixels,0,xDistPixels,yDistPixels);
            dc.DrawLine(0,yDistPixels,xDistPixels,yDistPixels);
            
            # grid
            for y in xrange(0,gridCountY+1):
                for x in xrange(0,gridCountX+1):
                    dc.DrawLine(0,y*(pixelsYPerMM*gridSize),xDistPixels,y*(pixelsYPerMM*gridSize));
                    dc.DrawLine(x*(pixelsXPerMM*gridSize),0,x*(pixelsXPerMM*gridSize),yDistPixels);

            self.f.drawlayer(gridBitmap.ConvertToImage(), 'bitmap')
        else:
            self.f.offset=(float(self.offsetX.GetValue()), float(self.offsetY.GetValue()))
            self.f.scale=float(self.scale.GetValue())
            self.f.clearlayer()
    
    def updateoffset(self,event):
        self.f.offset=(float(self.offsetX.GetValue()), float(self.offsetY.GetValue()))
        self.startcalibrate(event)
    
    def updateprojectedXmm(self,event):
        self.startcalibrate(event)
        
    def updatescale(self,event):
        self.f.scale=float(self.scale.GetValue())
        self.startcalibrate(event)
        
    def updatefullscreen(self,event):
        if (self.fullscreen.GetValue()):
            self.f.ShowFullScreen(1)
        else:
            self.f.ShowFullScreen(0)
        self.startcalibrate(event)
    
    def updateresolution(self,event):
        self.f.resize((float(self.X.GetValue()), float(self.Y.GetValue())))
        self.startcalibrate(event)
    
    def startdisplay(self, event):
        self.pause.SetLabel("Pause")
        self.f.Raise()
        if (self.fullscreen.GetValue()):
            self.f.ShowFullScreen(1)
        l = self.layers[0][:]
        self.f.present(l,
            thickness=float(self.thickness.GetValue()),
            interval=float(self.interval.GetValue()),
            scale=float(self.scale.GetValue()),
            pause=float(self.delay.GetValue()),
            size=(float(self.X.GetValue()), float(self.Y.GetValue())),
            offset=(float(self.offsetX.GetValue()), float(self.offsetY.GetValue())))
        
    def pausepresent(self, event):        
        if self.f.timer.IsRunning():
            print "Pause"
            self.pause.SetLabel("Continue")
            self.f.timer.Stop()
        else:
            print "Continue"
            self.pause.SetLabel("Pause")
            self.f.timer.Start()

    def presentfirstlayer(self, event):
        if (self.showfirstlayer.GetValue()):
            self.f.offset=(float(self.offsetX.GetValue()), float(self.offsetY.GetValue()))
            self.f.scale=float(self.scale.GetValue())
            self.f.drawlayer(self.layers[0][0], self.f.slicer)
        else:
            self.f.hidePic()
        

if __name__ == "__main__":
    #a = wx.App(redirect=True,filename="mylogfile.txt")
    a = wx.App()
    setframe(None).Show()
    a.MainLoop()
