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
import time
import zipfile
import tempfile
import shutil
import svg.document as wxpsvgdocument
import imghdr
    
class DisplayFrame(wx.Frame):
    def __init__(self, parent, title, res=(1024, 768), printer=None, scale=1.0, offset=(0,0)):
        wx.Frame.__init__(self, parent=parent, title=title, size=res)
        self.printer = printer
        self.control_frame = parent
        self.pic = wx.StaticBitmap(self)
        self.bitmap = wx.EmptyBitmap(*res)
        self.bbitmap = wx.EmptyBitmap(*res)
        self.slicer = 'bitmap'
        dc = wx.MemoryDC()
        dc.SelectObject(self.bbitmap)
        dc.SetBackground(wx.Brush("black"))
        dc.Clear()
        dc.SelectObject(wx.NullBitmap)

        self.SetBackgroundColour("black")
        self.pic.Hide()
        self.SetDoubleBuffered(True)
        self.SetPosition((self.control_frame.GetSize().x, 0))
        self.Show()
        
        self.scale = scale
        self.index = 0
        self.size = res
        self.offset = offset
        self.running = False

    def clear_layer(self):
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
        
    def draw_layer(self, image):
        try:
            dc = wx.MemoryDC()
            dc.SelectObject(self.bitmap)
            dc.SetBackground(wx.Brush("black"))
            dc.Clear()
            dc.SetPen(wx.Pen("white"))
            dc.SetBrush(wx.Brush("white"))

            if self.slicer == 'Skeinforge':
                for i in image:
                    points = [wx.Point(*map(lambda x:int(round(float(x) * self.scale)), j.strip().split())) for j in i.strip().split("M")[1].split("L")]
                    dc.DrawPolygon(points, self.size[0] / 2, self.size[1] / 2)
            elif self.slicer == 'Slic3r':
                gc = wx.GraphicsContext_Create(dc)            
                gc.Translate(*self.offset)
                gc.Scale(self.scale, self.scale)
                wxpsvgdocument.SVGDocument(image).render(gc)
            elif self.slicer == 'bitmap':
                if isinstance(image, str):
                    image = wx.Image(image)
                dc.DrawBitmap(wx.BitmapFromImage(image.Scale(image.Width * self.scale, image.Height * self.scale)), self.offset[0], -self.offset[1], True)
            else:
                raise Exception(self.slicer + " is an unknown method.")
            
            self.pic.SetBitmap(self.bitmap)
            self.pic.Show()
            self.Refresh()            
            
        except:
            raise
            pass
            
    def show_img_delay(self, image):
        print "Showing "+ str(time.clock())
        self.control_frame.set_current_layer(self.index)
        self.draw_layer(image)
        wx.FutureCall(1000 * self.interval, self.hide_pic_and_rise)
        self.pic.Show()
        self.Refresh()

    def rise(self):
        print "Rising "+ str(time.clock())
        if self.printer != None and self.printer.online:
                self.printer.send_now("G91")
                self.printer.send_now("G1 Z%f F200" % (3,))
                self.printer.send_now("G1 Z-%f F200" % (3-self.thickness,))
                self.printer.send_now("G90")
        
        self.next_img()
        
    def hide_pic(self):
        print "Hiding "+ str(time.clock())
        self.pic.Hide()
        
    def hide_pic_and_rise(self):
        wx.CallAfter(self.hide_pic)
        wx.FutureCall(self.pause * 1000, self.rise)
                    
    def next_img(self):
        if not self.running:
            return
        if self.index < len(self.layers):
            print self.index
            wx.CallAfter(self.show_img_delay, self.layers[self.index])
            self.index += 1
        else:
            print "end"
            wx.CallAfter(self.pic.Hide)
            wx.CallAfter(self.Refresh)
        
    def present(self, layers, interval=0.5, pause=0.2, thickness=0.4, scale=20, size=(1024, 768), offset=(0, 0)):
        wx.CallAfter(self.pic.Hide)
        wx.CallAfter(self.Refresh)
        self.layers = layers
        self.scale = scale
        self.thickness = thickness
        self.size = size
        self.interval = interval
        self.pause = pause
        self.offset = offset
        self.index = 0
        self.running = True
       
        self.next_img()

class SettingsFrame(wx.Frame):
    
    def __init__(self, parent, printer=None):
        wx.Frame.__init__(self, parent, title="ProjectLayer Control", size=(400, 400))
        self.display_frame = DisplayFrame(self, title="ProjectLayer Display", printer=printer)
        left_label_X_pos = 0
        left_value_X_pos = 70
        right_label_X_pos = 180
        right_value_X_pos = 230        
        self.panel = wx.Panel(self)
        self.panel.SetBackgroundColour("red")
        self.load_button = wx.Button(self.panel, -1, "Load", pos=(0, 0))
        self.load_button.Bind(wx.EVT_BUTTON, self.load_file)
        
        wx.StaticText(self.panel, -1, "Layer (mm):", pos=(left_label_X_pos, 30))
        self.thickness = wx.TextCtrl(self.panel, -1, "0.3", pos=(left_value_X_pos, 30))

        wx.StaticText(self.panel, -1, "Exposure (s):", pos=(left_label_X_pos, 60))
        self.interval = wx.TextCtrl(self.panel, -1, "0.5", pos=(left_value_X_pos, 60))

        wx.StaticText(self.panel, -1, "Blank (s):", pos=(left_label_X_pos, 90))
        self.delay = wx.TextCtrl(self.panel, -1, "0.5", pos=(left_value_X_pos, 90))

        wx.StaticText(self.panel, -1, "Scale:", pos=(left_label_X_pos, 120))
        self.scale = floatspin.FloatSpin(self.panel, -1, pos=(left_value_X_pos, 120), value=1.0, increment=0.1, digits=1)
        self.scale.Bind(floatspin.EVT_FLOATSPIN, self.update_scale)
        
        wx.StaticText(self.panel, -1, "X:", pos=(right_label_X_pos, 30))
        self.X = wx.SpinCtrl(self.panel, -1, '1440', pos=(right_value_X_pos, 30), max=999999)
        self.X.Bind(wx.EVT_SPINCTRL, self.update_resolution)

        wx.StaticText(self.panel, -1, "Y:", pos=(right_label_X_pos, 60))
        self.Y = wx.SpinCtrl(self.panel, -1, '900', pos=(right_value_X_pos, 60), max=999999)
        self.Y.Bind(wx.EVT_SPINCTRL, self.update_resolution)
        
        wx.StaticText(self.panel, -1, "OffsetX:", pos=(right_label_X_pos, 90))
        self.offset_X = floatspin.FloatSpin(self.panel, -1, pos=(right_value_X_pos, 90), value=0.0, increment=1, digits=1)
        self.offset_X.Bind(floatspin.EVT_FLOATSPIN, self.update_offset)

        wx.StaticText(self.panel, -1, "OffsetY:", pos=(right_label_X_pos, 120))
        self.offset_Y = floatspin.FloatSpin(self.panel, -1, pos=(right_value_X_pos, 120), value=0.0, increment=1, digits=1)
        self.offset_Y.Bind(floatspin.EVT_FLOATSPIN, self.update_offset)
        
        self.load_button = wx.Button(self.panel, -1, "Present", pos=(left_label_X_pos, 150))
        self.load_button.Bind(wx.EVT_BUTTON, self.start_present)
        
        self.pause = wx.Button(self.panel, -1, "Pause", pos=(left_label_X_pos, 180))
        self.pause.Bind(wx.EVT_BUTTON, self.pause_present)
        
        self.stop = wx.Button(self.panel, -1, "Stop", pos=(left_label_X_pos, 210))
        self.stop.Bind(wx.EVT_BUTTON, self.stop_present)
        
        wx.StaticText(self.panel, -1, "Fullscreen:", pos=(right_label_X_pos, 150))
        self.fullscreen = wx.CheckBox(self.panel, -1, pos=(right_value_X_pos, 150))
        self.fullscreen.Bind(wx.EVT_CHECKBOX, self.update_fullscreen)
        
        wx.StaticText(self.panel, -1, "Calibrate:", pos=(right_label_X_pos, 180))
        self.calibrate = wx.CheckBox(self.panel, -1, pos=(right_value_X_pos, 180))
        self.calibrate.Bind(wx.EVT_CHECKBOX, self.start_calibrate)
        
        wx.StaticText(self.panel, -1, "ProjectedX (mm):", pos=(right_label_X_pos, 210))
        self.projected_X_mm = floatspin.FloatSpin(self.panel, -1, pos=(right_value_X_pos + 40, 210), value=415.0, increment=1, digits=1)
        self.projected_X_mm.Bind(floatspin.EVT_FLOATSPIN, self.update_projected_Xmm)

        wx.StaticText(self.panel, -1, "1st Layer:", pos=(right_label_X_pos, 240))
        self.show_first_layer = wx.CheckBox(self.panel, -1, pos=(right_value_X_pos, 240))
        self.show_first_layer.Bind(wx.EVT_CHECKBOX, self.present_first_layer)

        wx.StaticText(self.panel, -1, "(s):", pos=(right_value_X_pos +20, 240))
        self.show_first_layer_timer = floatspin.FloatSpin(self.panel, -1, pos=(right_value_X_pos +40, 240), value=-1, increment=1, digits=1)

        wx.StaticText(self.panel, -1, "Boundary:", pos=(right_label_X_pos, 270))
        self.bounding_box = wx.CheckBox(self.panel, -1, pos=(right_value_X_pos, 270))
        self.bounding_box.Bind(wx.EVT_CHECKBOX, self.show_bounding_box)
        
        wx.StaticText(self.panel, -1, "Total Layers:", pos=(left_label_X_pos, 260))
        self.total_layers = wx.StaticText(self.panel, -1, "0", pos=(left_value_X_pos + 10, 260))

        wx.StaticText(self.panel, -1, "Current Layer:", pos=(left_label_X_pos, 280))
        self.current_layer = wx.StaticText(self.panel, -1, "0", pos=(left_value_X_pos + 20, 280))
        
        self.SetPosition((0, 0)) 
        self.Show()

    def __del__(self):
        if hasattr(self, 'image_dir') and self.image_dir != '':
            shutil.rmtree(self.image_dir)
        if self.display_frame:
            self.display_frame.Destroy()

    def set_total_layers(self, total):
        self.total_layers.SetLabel(str(total)) 

    def set_current_layer(self, index):
        self.current_layer.SetLabel(str(index)) 
            
    def parse_svg(self, name):
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
    
    def parse_3DLP_zip(self, name):
        if not zipfile.is_zipfile(name):
            raise Exception(name + " is not a zip file!")
        accepted_image_types = ['gif','tiff','jpg','jpeg','bmp','png']
        zipFile = zipfile.ZipFile(name, 'r')
        self.image_dir = tempfile.mkdtemp()
        zipFile.extractall(self.image_dir)
        ol = []
        imagefiles = os.listdir(self.image_dir)
        imagefiles.sort()
        for f in imagefiles:
            path = os.path.join(self.image_dir, f)
            if os.path.isfile(path) and imghdr.what(path) in accepted_image_types:
                ol.append(path)
        return ol, -1, "bitmap"
        
    def load_file(self, event):
        dlg = wx.FileDialog(self, ("Open file to print"), style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
        dlg.SetWildcard(("Slic3r or Skeinforge svg files (;*.svg;*.SVG;);3DLP Zip (;*.3dlp.zip;)"))
        if(dlg.ShowModal() == wx.ID_OK):
            name = dlg.GetPath()
            if not(os.path.exists(name)):
                self.status.SetStatusText(("File not found!"))
                return
            if name.endswith(".3dlp.zip"):
                layers = self.parse_3DLP_zip(name)
                layerHeight = float(self.thickness.GetValue())
            else:
                layers = self.parse_svg(name)
                layerHeight = layers[1]
                self.thickness.SetValue(str(layers[1]))
                print "Layer thickness detected:", layerHeight, "mm"
            print len(layers[0]), "layers found, total height", layerHeight * len(layers[0]), "mm"
            self.layers = layers
            self.set_total_layers(len(layers[0]))
            self.set_current_layer(0) 
            self.display_frame.slicer = layers[2]
        dlg.Destroy()

    def start_calibrate(self, event):
        if self.calibrate.IsChecked():
            self.display_frame.Raise()
            self.display_frame.offset = (float(self.offset_X.GetValue()), float(self.offset_Y.GetValue()))
            self.display_frame.scale = 1.0
            resolution_x_pixels = int(self.X.GetValue())
            resolution_y_pixels = int(self.Y.GetValue())
            
            gridBitmap = wx.EmptyBitmap(resolution_x_pixels, resolution_y_pixels)
            dc = wx.MemoryDC()
            dc.SelectObject(gridBitmap)
            dc.SetBackground(wx.Brush("black"))
            dc.Clear()
            
            dc.SetPen(wx.Pen("red", 7))
            dc.DrawLine(0, 0, resolution_x_pixels, 0);
            dc.DrawLine(0, 0, 0, resolution_y_pixels);
            dc.DrawLine(resolution_x_pixels, 0, resolution_x_pixels, resolution_y_pixels);
            dc.DrawLine(0, resolution_y_pixels, resolution_x_pixels, resolution_y_pixels);
            
            dc.SetPen(wx.Pen("red", 2))
            aspectRatio = float(resolution_x_pixels) / float(resolution_y_pixels)
            
            projectedXmm = float(self.projected_X_mm.GetValue())            
            projectedYmm = round(projectedXmm / aspectRatio)
            
            pixelsXPerMM = resolution_x_pixels / projectedXmm
            pixelsYPerMM = resolution_y_pixels / projectedYmm
            
            gridCountX = int(projectedXmm / 10)
            gridCountY = int(projectedYmm / 10)
            
            for y in xrange(0, gridCountY + 1):
                for x in xrange(0, gridCountX + 1):
                    dc.DrawLine(0, y * (pixelsYPerMM * 10), resolution_x_pixels, y * (pixelsYPerMM * 10));
                    dc.DrawLine(x * (pixelsXPerMM * 10), 0, x * (pixelsXPerMM * 10), resolution_y_pixels);

            self.show_first_layer.SetValue(False)
            self.bounding_box.SetValue(False)
            self.display_frame.slicer = 'bitmap'
            self.display_frame.draw_layer(gridBitmap.ConvertToImage())

        else:
            if hasattr(self, 'layers'):
                self.display_frame.slicer = self.layers[2] 
            self.display_frame.scale = float(self.scale.GetValue())
            self.display_frame.clear_layer()

    def show_bounding_box(self, event):
        if self.bounding_box.IsChecked():
            self.display_frame.Raise()
            self.display_frame.offset=(float(self.offset_X.GetValue()), -float(self.offset_Y.GetValue()))
            self.display_frame.scale=1.0
            resolutionXPixels = int(self.X.GetValue())
            resolutionYPixels = int(self.Y.GetValue())
            
            boxBitmap = wx.EmptyBitmap(resolutionXPixels,resolutionYPixels)
            dc = wx.MemoryDC()
            dc.SelectObject(boxBitmap)
            dc.SetBackground(wx.Brush("black"))
            dc.Clear()
            
            dc.SetPen(wx.Pen("red",2))
            aspectRatio = float(resolutionXPixels)/float(resolutionYPixels)

            projectedXmm = float(self.projected_X_mm.GetValue())                        
            projectedYmm = round(projectedXmm/aspectRatio)            
            
            pixelsXPerMM = resolutionXPixels / projectedXmm
            pixelsYPerMM = resolutionYPixels / projectedYmm            

            if (hasattr(self, 'layers')):
                xDist = float(self.layers[0][0].get('width').replace('m',''))
                yDist = float(self.layers[0][0].get('height').replace('m',''))
            else:
                xDist = projectedXmm
                yDist = projectedYmm
            
            xDistPixels = xDist * pixelsXPerMM
            yDistPixels = yDist * pixelsYPerMM
            
            # boundary
            dc.DrawLine(0,0,xDistPixels,0);
            dc.DrawLine(0,0,0,yDistPixels);
            dc.DrawLine(xDistPixels,0,xDistPixels,yDistPixels);
            dc.DrawLine(0,yDistPixels,xDistPixels,yDistPixels);
            
            self.show_first_layer.SetValue(False)
            self.calibrate.SetValue(False)
            self.display_frame.slicer = 'bitmap'
            self.display_frame.draw_layer(boxBitmap.ConvertToImage())
        else:
            if hasattr(self, 'layers'):
                self.display_frame.slicer = self.layers[2] 
            self.display_frame.offset=(float(self.offset_X.GetValue()), float(self.offset_Y.GetValue()))
            self.display_frame.scale=float(self.scale.GetValue())
            self.display_frame.clear_layer()
            
    def update_offset(self, event):
        self.display_frame.offset = (float(self.offset_X.GetValue()), float(self.offset_Y.GetValue()))
        self.start_calibrate(event)
    
    def update_projected_Xmm(self, event):
        self.start_calibrate(event)
        
    def update_scale(self, event):
        self.display_frame.scale = float(self.scale.GetValue())
        self.start_calibrate(event)
        
    def update_fullscreen(self, event):
        if (self.fullscreen.GetValue()):
            self.display_frame.ShowFullScreen(1)
        else:
            self.display_frame.ShowFullScreen(0)
        self.start_calibrate(event)
    
    def update_resolution(self, event):
        self.display_frame.resize((float(self.X.GetValue()), float(self.Y.GetValue())))
        self.start_calibrate(event)
    
    def start_present(self, event):
        if not hasattr(self, "layers"):
            print "No model loaded!"
            return
        
        self.pause.SetLabel("Pause")
        self.display_frame.Raise()
        if (self.fullscreen.GetValue()):
            self.display_frame.ShowFullScreen(1)
        self.display_frame.slicer = self.layers[2]
        self.display_frame.present(self.layers[0][:],
            thickness=float(self.thickness.GetValue()),
            interval=float(self.interval.GetValue()),
            scale=float(self.scale.GetValue()),
            pause=float(self.delay.GetValue()),
            size=(float(self.X.GetValue()), float(self.Y.GetValue())),
            offset=(float(self.offset_X.GetValue()), float(self.offset_Y.GetValue())))
        
    def stop_present(self, event):
        print "Stop"
        self.pause.SetLabel("Pause")
        self.display_frame.running = False
        
    def pause_present(self, event):        
        if self.pause.GetLabel() == 'Pause':
            print "Pause"
            self.pause.SetLabel("Continue")
            self.display_frame.running = False
        else:
            print "Continue"
            self.pause.SetLabel("Pause")
            self.display_frame.running = True
            self.display_frame.next_img()

    def present_first_layer(self, event):
        if not hasattr(self, "layers"):
            print "No model loaded!"
            self.show_first_layer.SetValue(False)
            return
        if (self.show_first_layer.GetValue()):
            self.display_frame.offset = (float(self.offset_X.GetValue()), float(self.offset_Y.GetValue()))
            self.display_frame.scale = float(self.scale.GetValue())

            self.display_frame.slicer = self.layers[2]
            self.display_frame.draw_layer(self.layers[0][0])
            self.calibrate.SetValue(False)
            self.bounding_box.SetValue(False)
            if self.show_first_layer_timer != -1.0 :
                def unpresent_first_layer():
                    self.display_frame.clear_layer()
                    self.show_first_layer.SetValue(False)
                wx.CallLater(self.show_first_layer_timer.GetValue() * 1000, unpresent_first_layer)
        else:
            self.display_frame.clear_layer()
        

if __name__ == "__main__":
    #a = wx.App(redirect=True,filename="mylogfile.txt")
    a = wx.App()
    SettingsFrame(None).Show()
    a.MainLoop()
