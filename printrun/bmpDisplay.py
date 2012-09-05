# create a simple image slide show using the
# wx.PaintDC surface as a canvas and
# DrawBitmap(bitmap, x, y, bool transparent)
# Source:  vegaseat

import wx
import os
import zipfile
import tempfile
import shutil

class MyFrame(wx.Frame):
    def __init__(self, parent, mysize):
        wx.Frame.__init__(self, parent, wx.ID_ANY, size = mysize)
        self.SetBackgroundColour('black')

        # milliseconds per frame
        self.delay = 60
        # number of loops
        self.loops = 1

        zipfilename = 'images/out.3dlp.zip'
        if not zipfile.is_zipfile(zipfilename):
            raise Exception(zipfilename + " is not a zip file!")
        zip = zipfile.ZipFile(zipfilename, 'r')
        self.mytmpdir = tempfile.mkdtemp()
        zip.extractall(self.mytmpdir)

        image_type = ".bmp"
        image_dir = self.mytmpdir
        file_list = []
        self.name_list = []
        for file in os.listdir(image_dir):
            path = os.path.join(image_dir, file)
            if os.path.isfile(path) and path.endswith(image_type):
                # just the file name
                self.name_list.append(file)
                # full path name
                file_list.append(path)
        # create a list of image objects
        self.image_list = []
        for image_file in file_list:
            self.image_list.append(wx.Bitmap(image_file))

        # bind the panel to the paint event
        wx.EVT_PAINT(self, self.onPaint)

    def __del__(self):
        if self.mytmpdir:
            shutil.rmtree(self.mytmpdir)

    def onPaint(self, event = None):
        # this is the wxPython drawing surface/canvas
        dc = wx.PaintDC(self)
        while self.loops:
            self.loops -= 1
            for ix, bmp in enumerate(self.image_list):
                # optionally show some image information
                w, h = bmp.GetSize()
                info = "%s  %dx%d" % (self.name_list[ix], w, h)
                self.SetTitle(info)
                #self.SetSize((w, h))
                # draw the image
                dc.DrawBitmap(bmp, 0, 0, True)
                wx.MilliSleep(self.delay)
                # don't clear on fast slide shows to avoid flicker
                if self.delay > 200:
                    dc.Clear()


app = wx.App()
width = 800
frameoffset = 35
height = 600 + frameoffset
MyFrame(None, (width, height)).Show()
app.MainLoop()
