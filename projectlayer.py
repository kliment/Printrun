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
from cairosvg.surface import PNGSurface
import cStringIO
import imghdr
import copy

class DisplayFrame(wx.Frame):
    def __init__(self, parent, title, res=(1024, 768), printer=None, scale=1.0, offset=(0,0)):
        wx.Frame.__init__(self, parent=parent, title=title, size=res)
        self.printer = printer
        self.control_frame = parent
        self.pic = wx.StaticBitmap(self)
        self.bitmap = wx.EmptyBitmap(*res)
        self.bbitmap = wx.EmptyBitmap(*res)
        self.slicer = 'bitmap'
        self.dpi = 96
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
                
                if int(self.scale) != 1:
                    layercopy = copy.deepcopy(image)
                    height = float(layercopy.get('height').replace('m',''))
                    width = float(layercopy.get('width').replace('m',''))
                    
                    layercopy.set('height', str(height*self.scale) + 'mm')
                    layercopy.set('width', str(width*self.scale) + 'mm')
                    layercopy.set('viewBox', '0 0 ' + str(height*self.scale) + ' ' + str(width*self.scale))
                    
                    g = layercopy.find("{http://www.w3.org/2000/svg}g")
                    g.set('transform', 'scale('+str(self.scale)+')')
                    stream = cStringIO.StringIO(PNGSurface.convert(dpi=self.dpi, bytestring=xml.etree.ElementTree.tostring(layercopy)))
                    image = wx.ImageFromStream(stream)
                    dc.DrawBitmap(wx.BitmapFromImage(image), self.offset[0], self.offset[1], True)    
                else:    
                    stream = cStringIO.StringIO(PNGSurface.convert(dpi=self.dpi, bytestring=xml.etree.ElementTree.tostring(image)))
                    image = wx.ImageFromStream(stream)
                    dc.DrawBitmap(wx.BitmapFromImage(image), self.offset[0], self.offset[1], True)
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

    def rise(self):
        print "Rising "+ str(time.clock())
        if self.printer != None and self.printer.online:
            self.printer.send_now("G91")
            self.printer.send_now("G1 Z%f F200" % (3,))
            self.printer.send_now("G1 Z-%f F200" % (3-self.thickness,))
            self.printer.send_now("G90")
        else:
            time.sleep(self.pause)
        
        wx.FutureCall(1000 * self.pause, self.next_img)
        
    def hide_pic(self):
        print "Hiding "+ str(time.clock())
        self.pic.Hide()
        
    def hide_pic_and_rise(self):
        wx.CallAfter(self.hide_pic)
        wx.FutureCall(500, self.rise)
                    
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
        
    def present(self, layers, interval=0.5, pause=0.2, thickness=0.4, scale=1, size=(1024, 768), offset=(0, 0)):
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
    
    def _set_setting(self, name, value):
        if self.pronterface:
            self.pronterface.set(name,value)
    
    def _get_setting(self,name, val):
        if self.pronterface:
            try:
                return getattr(self.pronterface.settings,name)
            except AttributeError, x:
                print x
                return val
        else: 
            return val
        
    def __init__(self, parent, printer=None):
        wx.Frame.__init__(self, parent, title="ProjectLayer Control", size=(400, 400))
        self.pronterface = parent
        self.display_frame = DisplayFrame(self, title="ProjectLayer Display", printer=printer)
        
        left_label_X_pos = 0
        left_value_X_pos = 70
        right_label_X_pos = 180
        right_value_X_pos = 230
        info_pos = 300
        
        self.panel = wx.Panel(self)
        self.panel.SetBackgroundColour("orange")
        self.load_button = wx.Button(self.panel, -1, "Load", pos=(0, 0))
        self.load_button.Bind(wx.EVT_BUTTON, self.load_file)
        
        wx.StaticText(self.panel, -1, "Layer (mm):", pos=(left_label_X_pos, 30))
        self.thickness = wx.TextCtrl(self.panel, -1, "0.3", pos=(left_value_X_pos, 30))

        wx.StaticText(self.panel, -1, "Exposure (s):", pos=(left_label_X_pos, 60))
        self.interval = wx.TextCtrl(self.panel, -1, str(self._get_setting("project_interval", "0.5")), pos=(left_value_X_pos, 60))
        self.interval.Bind(wx.EVT_SPINCTRL, self.update_interval)
        
        wx.StaticText(self.panel, -1, "Blank (s):", pos=(left_label_X_pos, 90))
        self.pause = wx.TextCtrl(self.panel, -1, str(self._get_setting("project_pause", "0.5")), pos=(left_value_X_pos, 90))
        self.pause.Bind(wx.EVT_SPINCTRL, self.update_pause)
        
        wx.StaticText(self.panel, -1, "Scale:", pos=(left_label_X_pos, 120))
        self.scale = floatspin.FloatSpin(self.panel, -1, pos=(left_value_X_pos, 120), value=self._get_setting('project_scale', 1.0), increment=0.1, digits=1)
        self.scale.Bind(floatspin.EVT_FLOATSPIN, self.update_scale)
        
        wx.StaticText(self.panel, -1, "X:", pos=(right_label_X_pos, 30))
        self.X = wx.SpinCtrl(self.panel, -1, str(int(self._get_setting("project_x", 1024))), pos=(right_value_X_pos, 30), max=999999)
        self.X.Bind(wx.EVT_SPINCTRL, self.update_resolution)

        wx.StaticText(self.panel, -1, "Y:", pos=(right_label_X_pos, 60))
        self.Y = wx.SpinCtrl(self.panel, -1, str(int(self._get_setting("project_y", 768))), pos=(right_value_X_pos, 60), max=999999)
        self.Y.Bind(wx.EVT_SPINCTRL, self.update_resolution)
        
        wx.StaticText(self.panel, -1, "OffsetX:", pos=(right_label_X_pos, 90))
        self.offset_X = floatspin.FloatSpin(self.panel, -1, pos=(right_value_X_pos, 90), value=self._get_setting("project_offset_x", 0.0), increment=1, digits=1)
        self.offset_X.Bind(floatspin.EVT_FLOATSPIN, self.update_offset)

        wx.StaticText(self.panel, -1, "OffsetY:", pos=(right_label_X_pos, 120))
        self.offset_Y = floatspin.FloatSpin(self.panel, -1, pos=(right_value_X_pos, 120), value=self._get_setting("project_offset_y", 0.0), increment=1, digits=1)
        self.offset_Y.Bind(floatspin.EVT_FLOATSPIN, self.update_offset)
        
        self.load_button = wx.Button(self.panel, -1, "Present", pos=(left_label_X_pos, 150))
        self.load_button.Bind(wx.EVT_BUTTON, self.start_present)
        
        self.pause_button = wx.Button(self.panel, -1, "Pause", pos=(left_label_X_pos, 180))
        self.pause_button.Bind(wx.EVT_BUTTON, self.pause_present)
        
        self.stop_button = wx.Button(self.panel, -1, "Stop", pos=(left_label_X_pos, 210))
        self.stop_button.Bind(wx.EVT_BUTTON, self.stop_present)
        
        wx.StaticText(self.panel, -1, "Fullscreen:", pos=(right_label_X_pos, 150))
        self.fullscreen = wx.CheckBox(self.panel, -1, pos=(right_value_X_pos, 150))
        self.fullscreen.Bind(wx.EVT_CHECKBOX, self.update_fullscreen)
        
        wx.StaticText(self.panel, -1, "Calibrate:", pos=(right_label_X_pos, 180))
        self.calibrate = wx.CheckBox(self.panel, -1, pos=(right_value_X_pos, 180))
        self.calibrate.Bind(wx.EVT_CHECKBOX, self.start_calibrate)
        
        wx.StaticText(self.panel, -1, "ProjectedX (mm):", pos=(right_label_X_pos, 210))
        self.projected_X_mm = floatspin.FloatSpin(self.panel, -1, pos=(right_value_X_pos + 40, 210), value=self._get_setting("project_projected_x", 415.0), increment=1, digits=1)
        self.projected_X_mm.Bind(floatspin.EVT_FLOATSPIN, self.update_projected_Xmm)

        wx.StaticText(self.panel, -1, "1st Layer:", pos=(right_label_X_pos, 240))
        self.show_first_layer = wx.CheckBox(self.panel, -1, pos=(right_value_X_pos, 240))
        self.show_first_layer.Bind(wx.EVT_CHECKBOX, self.present_first_layer)

        wx.StaticText(self.panel, -1, "(s):", pos=(right_value_X_pos +20, 240))
        self.show_first_layer_timer = floatspin.FloatSpin(self.panel, -1, pos=(right_value_X_pos +40, 240), value=-1, increment=1, digits=1)

        wx.StaticText(self.panel, -1, "Boundary:", pos=(right_label_X_pos, 270))
        self.bounding_box = wx.CheckBox(self.panel, -1, pos=(right_value_X_pos, 270))
        self.bounding_box.Bind(wx.EVT_CHECKBOX, self.show_bounding_box)
        
        wx.StaticText(self.panel, -1, "File:", pos=(left_label_X_pos, info_pos))
        self.filename = wx.StaticText(self.panel, -1, "", pos=(left_value_X_pos + 10, info_pos))
        
        wx.StaticText(self.panel, -1, "Total Layers:", pos=(left_label_X_pos, info_pos + 20))
        self.total_layers = wx.StaticText(self.panel, -1, "0", pos=(left_value_X_pos + 10, info_pos + 20))

        wx.StaticText(self.panel, -1, "Current Layer:", pos=(left_label_X_pos, info_pos + 40))
        self.current_layer = wx.StaticText(self.panel, -1, "0", pos=(left_value_X_pos + 20, info_pos + 40))
        
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

    def set_filename(self,name):
        self.filename.SetLabel(name)
            
    def parse_svg(self, name):
        et = xml.etree.ElementTree.ElementTree(file=name)
        #xml.etree.ElementTree.dump(et)
        
        slicer = 'Slic3r' if et.getroot().find('{http://www.w3.org/2000/svg}metadata') == None else 'Skeinforge'
        zlast = 0
        zdiff = 0
        ol = []
        if (slicer == 'Slic3r'):
            height = et.getroot().get('height').replace('m','')
            width = et.getroot().get('width').replace('m','')
            
            for i in et.findall("{http://www.w3.org/2000/svg}g"):
                z = float(i.get('{http://slic3r.org/namespaces/slic3r}z'))
                zdiff = z - zlast
                zlast = z
    
                svgSnippet = xml.etree.ElementTree.Element('{http://www.w3.org/2000/svg}svg')
                svgSnippet.set('height', height + 'mm')
                svgSnippet.set('width', width + 'mm')
                
                svgSnippet.set('viewBox', '0 0 ' + height + ' ' + width)
                svgSnippet.set('style','background-color:black')
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
            self.set_filename(os.path.basename(name)) 
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
        
        offset_x = float(self.offset_X.GetValue())
        offset_y = float(self.offset_Y.GetValue())
        self.display_frame.offset = (offset_x, offset_y)
        
        self._set_setting('project_offset_x',offset_x)
        self._set_setting('project_offset_y',offset_y)
        
        self.start_calibrate(event)
    
    def update_projected_Xmm(self, event):
        self._set_setting('project_projected_x',self.projected_X_mm.GetValue())
        self.start_calibrate(event)
        
    def update_scale(self, event):
        scale = float(self.scale.GetValue())
        self.display_frame.scale = scale
        self._set_setting('project_scale',scale)
        self.start_calibrate(event)
        
    def update_interval(self, event):
        interval = float(self.interval.GetValue())
        self.display_frame.interval = interval
        self._set_setting('project_interval',interval)
        self.start_calibrate(event)
        
    def update_pause(self, event):
        pause = float(self.pause.GetValue())
        self.display_frame.pause = pause
        self._set_setting('project_pause',pause)
        self.start_calibrate(event)
        
    def update_fullscreen(self, event):
        if (self.fullscreen.GetValue()):
            self.display_frame.ShowFullScreen(1)
        else:
            self.display_frame.ShowFullScreen(0)
        self.start_calibrate(event)
    
    def update_resolution(self, event):
        x = float(self.X.GetValue())
        y = float(self.Y.GetValue())
        self.display_frame.resize((x,y))
        self._set_setting('project_x',x)
        self._set_setting('project_y',y)
        self.start_calibrate(event)
    
    def get_dpi(self):
        resolution_x_pixels = int(self.X.GetValue())
        projected_x_mm = float(self.projected_X_mm.GetValue())
        projected_x_inches = projected_x_mm / 25.4
        
        return resolution_x_pixels / projected_x_inches                         
        
    def start_present(self, event):
        if not hasattr(self, "layers"):
            print "No model loaded!"
            return
        
        self.pause_button.SetLabel("Pause")
        self.display_frame.Raise()
        if (self.fullscreen.GetValue()):
            self.display_frame.ShowFullScreen(1)
        self.display_frame.slicer = self.layers[2]
        self.display_frame.dpi = self.get_dpi()
        self.display_frame.present(self.layers[0][:],
            thickness=float(self.thickness.GetValue()),
            interval=float(self.interval.GetValue()),
            scale=float(self.scale.GetValue()),
            pause=float(self.pause.GetValue()),
            size=(float(self.X.GetValue()), float(self.Y.GetValue())),
            offset=(float(self.offset_X.GetValue()), float(self.offset_Y.GetValue())))
        
    def stop_present(self, event):
        print "Stop"
        self.pause_button.SetLabel("Pause")
        self.display_frame.running = False
        
    def pause_present(self, event):        
        if self.pause_button.GetLabel() == 'Pause':
            print "Pause"
            self.pause_button.SetLabel("Continue")
            self.display_frame.running = False
        else:
            print "Continue"
            self.pause_button.SetLabel("Pause")
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
            self.display_frame.dpi = self.get_dpi()
            self.display_frame.draw_layer(copy.deepcopy(self.layers[0][0]))
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
