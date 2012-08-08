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
import os
import zipfile
import tempfile
import shutil
import svg.document as wxpsvgdocument
import imghdr

class dispframe(wx.Frame):
    def __init__(self, parent, title, res = (800, 600), printer = None):
        wx.Frame.__init__(self, parent = parent, title = title)
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

    def drawlayer(self, image):
        try:
            dc = wx.MemoryDC()
            dc.SelectObject(self.bitmap)
            dc.SetBackground(wx.Brush("black"))
            dc.Clear()
            dc.SetPen(self.pen)
            dc.SetBrush(self.brush)

            if self.slicer == 'Skeinforge':
                for i in image:
                    #print i
                    points = [wx.Point(*map(lambda x:int(round(float(x) * self.scale)), j.strip().split())) for j in i.strip().split("M")[1].split("L")]
                    dc.DrawPolygon(points, self.size[0] / 2, self.size[1] / 2)
            elif self.slicer == 'Slic3r':
                gc = wx.GraphicsContext_Create(dc)
                gc.Translate(*self.offset)
                gc.Scale(self.scale, self.scale)
                wxpsvgdocument.SVGDocument(image).render(gc)
            elif self.slicer == 'bitmap':
                dc.DrawBitmap(image, self.offset[0], -self.offset[1], True)
            else:
                raise Exception(self.slicer + " is an unknown method.")
            self.pic.SetBitmap(self.bitmap)
            self.pic.Show()
            self.Refresh()


        except:
            raise
            pass

    def showimgdelay(self, image):
        self.drawlayer(image)
        self.pic.Show()
        self.Refresh()

        self.Refresh()
        if self.p != None and self.p.online:
            self.p.send_now("G91")
            self.p.send_now("G1 Z%f F300" % (self.thickness,))
            self.p.send_now("G90")

    def nextimg(self, event):
        if self.index < len(self.layers):
            i = self.index

            print i
            wx.CallAfter(self.showimgdelay, self.layers[i])
            wx.FutureCall(1000 * self.interval, self.pic.Hide)
            self.index += 1
        else:
            print "end"
            wx.CallAfter(self.pic.Hide)
            wx.CallAfter(self.Refresh)
            wx.CallAfter(self.ShowFullScreen, 0)
            wx.CallAfter(self.timer.Stop)

    def present(self, layers, interval = 0.5, pause = 0.2, thickness = 0.4, scale = 20, size = (800, 600), offset = (0, 0)):
        wx.CallAfter(self.pic.Hide)
        wx.CallAfter(self.Refresh)
        self.layers = layers
        self.scale = scale
        self.thickness = thickness
        self.index = 0
        self.size = (size[0] + offset[0], size[1] + offset[1])
        self.interval = interval
        self.offset = offset
        self.timer = wx.Timer(self, 1)
        self.timer.Bind(wx.EVT_TIMER, self.nextimg)
        self.Bind(wx.EVT_TIMER, self.nextimg)
        self.timer.Start(1000 * interval + 1000 * pause)

class setframe(wx.Frame):

    def __init__(self, parent, printer = None):
        wx.Frame.__init__(self, parent, title = "Projector setup")
        self.f = dispframe(None, "", printer = printer)
        self.panel = wx.Panel(self)
        self.panel.SetBackgroundColour("orange")
        self.bload = wx.Button(self.panel, -1, "Load", pos = (0, 0))
        self.bload.Bind(wx.EVT_BUTTON, self.loadfile)

        wx.StaticText(self.panel, -1, "Layer:", pos = (0, 30))
        wx.StaticText(self.panel, -1, "mm", pos = (130, 30))
        self.thickness = wx.TextCtrl(self.panel, -1, "0.5", pos = (50, 30))

        wx.StaticText(self.panel, -1, "Exposure:", pos = (0, 60))
        wx.StaticText(self.panel, -1, "s", pos = (130, 60))
        self.interval = wx.TextCtrl(self.panel, -1, "0.5", pos = (50, 60))

        wx.StaticText(self.panel, -1, "Blank:", pos = (0, 90))
        wx.StaticText(self.panel, -1, "s", pos = (130, 90))
        self.delay = wx.TextCtrl(self.panel, -1, "0.5", pos = (50, 90))

        wx.StaticText(self.panel, -1, "Scale:", pos = (0, 120))
        wx.StaticText(self.panel, -1, "x", pos = (130, 120))
        self.scale = wx.TextCtrl(self.panel, -1, "5", pos = (50, 120))

        wx.StaticText(self.panel, -1, "X:", pos = (160, 30))
        self.X = wx.TextCtrl(self.panel, -1, "1024", pos = (210, 30))

        wx.StaticText(self.panel, -1, "Y:", pos = (160, 60))
        self.Y = wx.TextCtrl(self.panel, -1, "768", pos = (210, 60))

        wx.StaticText(self.panel, -1, "OffsetX:", pos = (160, 90))
        self.offsetX = wx.TextCtrl(self.panel, -1, "50", pos = (210, 90))

        wx.StaticText(self.panel, -1, "OffsetY:", pos = (160, 120))
        self.offsetY = wx.TextCtrl(self.panel, -1, "50", pos = (210, 120))

        self.bload = wx.Button(self.panel, -1, "Present", pos = (0, 150))
        self.bload.Bind(wx.EVT_BUTTON, self.startdisplay)

        wx.StaticText(self.panel, -1, "Fullscreen:", pos = (160, 150))
        self.fullscreen = wx.CheckBox(self.panel, -1, pos = (220, 150))
        self.fullscreen.SetValue(True)

        self.Show()

    def __del__(self):
        if hasattr(self, 'image_dir') and self.image_dir != '':
            shutil.rmtree(self.image_dir)

    def parsesvg(self, name):
        et = xml.etree.ElementTree.ElementTree(file = name)
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
        for f in os.listdir(self.image_dir):
            path = os.path.join(self.image_dir, f)
            if os.path.isfile(path) and imghdr.what(path) in acceptedImageTypes:
                ol.append(wx.Bitmap(path))
        return ol, -1, "bitmap"

    def loadfile(self, event):
        dlg = wx.FileDialog(self, ("Open file to print"), style = wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
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
        dlg.Destroy()

    def startdisplay(self, event):
        self.f.Raise()
        if (self.fullscreen.GetValue()):
            self.f.ShowFullScreen(1)
        l = self.layers[0][:]
        self.f.present(l,
            thickness = float(self.thickness.GetValue()),
            interval = float(self.interval.GetValue()),
            scale = float(self.scale.GetValue()),
            pause = float(self.delay.GetValue()),
            size = (float(self.X.GetValue()), float(self.Y.GetValue())),
            offset = (float(self.offsetX.GetValue()), float(self.offsetY.GetValue())))

if __name__ == "__main__":
    a = wx.App()
    setframe(None).Show()
    a.MainLoop()
