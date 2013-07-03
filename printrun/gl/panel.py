#!/usr/bin/env python

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

import os
import math

import wx
from wx import glcanvas

import pyglet
pyglet.options['debug_gl'] = True

from pyglet.gl import *
from pyglet import gl

class wxGLPanel(wx.Panel):
    '''A simple class for using OpenGL with wxPython.'''

    orthographic = True

    def __init__(self, parent, id, pos = wx.DefaultPosition,
                 size = wx.DefaultSize, style = 0):
        # Forcing a no full repaint to stop flickering
        style = style | wx.NO_FULL_REPAINT_ON_RESIZE
        super(wxGLPanel, self).__init__(parent, id, pos, size, style)

        self.GLinitialized = False
        self.mview_initialized = False
        attribList = (glcanvas.WX_GL_RGBA,  # RGBA
                      glcanvas.WX_GL_DOUBLEBUFFER,  # Double Buffered
                      glcanvas.WX_GL_DEPTH_SIZE, 24)  # 24 bit

        self.sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.canvas = glcanvas.GLCanvas(self, attribList = attribList)
        self.context = glcanvas.GLContext(self.canvas)
        self.sizer.Add(self.canvas, 1, wx.EXPAND)
        self.SetSizerAndFit(self.sizer)

        # bind events
        self.canvas.Bind(wx.EVT_ERASE_BACKGROUND, self.processEraseBackgroundEvent)
        self.canvas.Bind(wx.EVT_SIZE, self.processSizeEvent)
        self.canvas.Bind(wx.EVT_PAINT, self.processPaintEvent)

    def processEraseBackgroundEvent(self, event):
        '''Process the erase background event.'''
        pass  # Do nothing, to avoid flashing on MSWin

    def processSizeEvent(self, event):
        '''Process the resize event.'''
        size = self.GetClientSize()
        self.width, self.height = size.width, size.height
        if (wx.VERSION > (2,9) and self.canvas.IsShownOnScreen()) or self.canvas.GetContext():
            # Make sure the frame is shown before calling SetCurrent.
            self.canvas.SetCurrent(self.context)
            self.OnReshape(size.width, size.height)
            self.canvas.Refresh(False)
        event.Skip()

    def processPaintEvent(self, event):
        '''Process the drawing event.'''
        self.canvas.SetCurrent(self.context)
 
        if not self.GLinitialized:
            self.OnInitGL()
            self.GLinitialized = True

        self.OnDraw()
        event.Skip()

    def Destroy(self):
        #clean up the pyglet OpenGL context
        self.pygletcontext.destroy()
        #call the super method
        super(wx.Panel, self).Destroy()

    #==========================================================================
    # GLFrame OpenGL Event Handlers
    #==========================================================================
    def OnInitGL(self):
        '''Initialize OpenGL for use in the window.'''
        #create a pyglet context for this panel
        self.pygletcontext = gl.Context(gl.current_context)
        self.pygletcontext.canvas = self
        self.pygletcontext.set_current()
        #normal gl init
        glClearColor(0.98, 0.98, 0.78, 1)
        glClearDepth(1.0)                # set depth value to 1
        glDepthFunc(GL_LEQUAL)
        glEnable(GL_COLOR_MATERIAL)
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_CULL_FACE)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        self.OnReshape(*self.GetClientSize())

    def OnReshape(self, width, height):
        '''Reshape the OpenGL viewport based on the dimensions of the window.'''
        if not self.GLinitialized:
            self.GLinitialized = True
            self.OnInitGL()
        glViewport(0, 0, width, height)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        if self.orthographic:
            glOrtho(-width / 2, width / 2, -height / 2, height / 2, 0.1, 3 * self.dist)
        else:
            gluPerspective(60., float(width) / height, 10.0, 3 * self.dist)

        if not self.mview_initialized:
            self.reset_mview(0.9)
            self.mview_initialized = True

        # Wrap text to the width of the window
        if self.GLinitialized:
            self.pygletcontext.set_current()
            self.update_object_resize()

    def reset_mview(self, factor):
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        if self.orthographic:
            ratio = factor * float(min(self.width, self.height)) / self.dist
            glScalef(ratio, ratio, 1)

    def OnDraw(self, *args, **kwargs):
        """Draw the window."""
        self.pygletcontext.set_current()
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        self.draw_objects()
        self.canvas.SwapBuffers()

    #==========================================================================
    # To be implemented by a sub class
    #==========================================================================
    def create_objects(self):
        '''create opengl objects when opengl is initialized'''
        pass

    def update_object_resize(self):
        '''called when the window recieves only if opengl is initialized'''
        pass

    def draw_objects(self):
        '''called in the middle of ondraw after the buffer has been cleared'''
        pass
