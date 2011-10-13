#!/usr/bin/python
import os
import wx,math,stltool
from wx import glcanvas
import time
import threading
        
import pyglet
pyglet.options['shadow_window'] = False
pyglet.options['debug_gl'] = False
from pyglet import gl
from pyglet.gl import *

class GLPanel(wx.Panel):

    '''A simple class for using OpenGL with wxPython.'''

    def __init__(self, parent, id, pos=wx.DefaultPosition,
                 size=wx.DefaultSize, style=0):
        # Forcing a no full repaint to stop flickering
        style = style | wx.NO_FULL_REPAINT_ON_RESIZE
        #call super function
        super(GLPanel, self).__init__(parent, id, pos, size, style)

        #init gl canvas data
        self.GLinitialized = False
        attribList = (glcanvas.WX_GL_RGBA, # RGBA
                      glcanvas.WX_GL_DOUBLEBUFFER, # Double Buffered
                      glcanvas.WX_GL_DEPTH_SIZE, 24) # 24 bit
        # Create the canvas
        self.sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.canvas = glcanvas.GLCanvas(self, attribList=attribList)
        self.sizer.Add(self.canvas, 1, wx.EXPAND)
        self.SetSizer(self.sizer)
        #self.sizer.Fit(self)
        self.Layout()
        
        # bind events
        self.canvas.Bind(wx.EVT_ERASE_BACKGROUND, self.processEraseBackgroundEvent)
        self.canvas.Bind(wx.EVT_SIZE, self.processSizeEvent)
        self.canvas.Bind(wx.EVT_PAINT, self.processPaintEvent)

    #==========================================================================
    # Canvas Proxy Methods
    #==========================================================================
    def GetGLExtents(self):
        '''Get the extents of the OpenGL canvas.'''
        return self.canvas.GetClientSize()

    def SwapBuffers(self):
        '''Swap the OpenGL buffers.'''
        self.canvas.SwapBuffers()

    #==========================================================================
    # wxPython Window Handlers
    #==========================================================================
    def processEraseBackgroundEvent(self, event):
        '''Process the erase background event.'''
        pass # Do nothing, to avoid flashing on MSWin

    def processSizeEvent(self, event):
        '''Process the resize event.'''
        if self.canvas.GetContext():
            # Make sure the frame is shown before calling SetCurrent.
            self.Show()
            self.canvas.SetCurrent()
            size = self.GetGLExtents()
            self.winsize = (size.width, size.height)
            self.width, self.height = size.width, size.height
            self.OnReshape(size.width, size.height)
            self.canvas.Refresh(False)
        event.Skip()

    def processPaintEvent(self, event):
        '''Process the drawing event.'''
        self.canvas.SetCurrent()
        
        # This is a 'perfect' time to initialize OpenGL ... only if we need to
        if not self.GLinitialized:
            self.OnInitGL()
            self.GLinitialized = True
        
        self.OnDraw()
        event.Skip()
        
    def Destroy(self):
        #clean up the pyglet OpenGL context
        #self.pygletcontext.destroy()
        #call the super method
        super(wx.Panel, self).Destroy()

    #==========================================================================
    # GLFrame OpenGL Event Handlers
    #==========================================================================
    def OnInitGL(self):
        '''Initialize OpenGL for use in the window.'''
        #create a pyglet context for this panel
        self.pmat=(GLdouble * 16)()
        self.mvmat=(GLdouble * 16)()
        self.pygletcontext = Context(current_context)
        self.pygletcontext.set_current()
        self.dist=1000
        self.vpmat=None
        #normal gl init
        glClearColor(0, 0, 0, 0.5)
        glColor3f(1, 0, 0)
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_CULL_FACE)
        # Uncomment this line for a wireframe view
        #glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
    
        # Simple light setup.  On Windows GL_LIGHT0 is enabled by default,
        # but this is not the case on Linux or Mac, so remember to always 
        # include it.
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glEnable(GL_LIGHT1)
        
        # Define a simple function to create ctypes arrays of floats:
        def vec(*args):
            return (GLfloat * len(args))(*args)
    
        glLightfv(GL_LIGHT0, GL_POSITION, vec(.5, .5, 1, 0))
        glLightfv(GL_LIGHT0, GL_SPECULAR, vec(.5, .5, 1, 1))
        glLightfv(GL_LIGHT0, GL_DIFFUSE, vec(1, 1, 1, 1))
        glLightfv(GL_LIGHT1, GL_POSITION, vec(1, 0, .5, 0))
        glLightfv(GL_LIGHT1, GL_DIFFUSE, vec(.5, .5, .5, 1))
        glLightfv(GL_LIGHT1, GL_SPECULAR, vec(1, 1, 1, 1))
    
        glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE, vec(0.5, 0, 0.3, 1))
        glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, vec(1, 1, 1, 1))
        glMaterialf(GL_FRONT_AND_BACK, GL_SHININESS, 200)
        glMaterialfv(GL_FRONT_AND_BACK, GL_EMISSION, vec(0,0.1,0,0.9))
        #create objects to draw
        #self.create_objects()
                                         
                                         
                                         
    def OnReshape(self, width, height):
        '''Reshape the OpenGL viewport based on the dimensions of the window.'''
        
        if not self.GLinitialized:
            self.OnInitGL()
            self.GLinitialized = True
        self.pmat=(GLdouble * 16)()
        self.mvmat=(GLdouble * 16)()
        glViewport(0, 0, width, height)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(60., width / float(height), .1, 1000.)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        #pyglet stuff
        self.vpmat=(GLint * 4)(0,0,*list(self.GetClientSize()))
        glGetDoublev(GL_PROJECTION_MATRIX,self.pmat)
        glGetDoublev(GL_MODELVIEW_MATRIX,self.mvmat)
        #glMatrixMode(GL_PROJECTION)
        
        
        # Wrap text to the width of the window
        if self.GLinitialized:
            self.pygletcontext.set_current()
            self.update_object_resize()
            
    def OnDraw(self, *args, **kwargs):
        """Draw the window."""
        #clear the context
        self.canvas.SetCurrent()
        self.pygletcontext.set_current()
        glClear(GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT)
        #draw objects
        self.draw_objects()
        #update screen
        self.SwapBuffers()
            
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
       
class stlview(object):
    list = None
    def __init__(self, facets, batch):
        # Create the vertex and normal arrays.
        vertices = []
        normals = []

        for i in facets:
            for j in i[1]:
                vertices.extend(j)
                normals.extend(i[0])

        # Create a list of triangle indices.
        indices = range(3*len(facets))#[[3*i,3*i+1,3*i+2] for i in xrange(len(facets))]
        #print indices[:10]
        self.vertex_list = batch.add_indexed(len(vertices)//3, 
                                             GL_TRIANGLES,
                                             None,#group,
                                             indices,
                                             ('v3f/static', vertices),
                                             ('n3f/static', normals))
       
    def delete(self):
        self.vertex_list.delete()

def trackball(p1x, p1y, p2x, p2y, r):
    TRACKBALLSIZE=r
#float a[3]; /* Axis of rotation */
#float phi;  /* how much to rotate about axis */
#float p1[3], p2[3], d[3];
#float t;

    if (p1x == p2x and p1y == p2y):
        return [0.0,0.0,0.0,1.0]

    p1=[p1x,p1y,project_to_sphere(TRACKBALLSIZE,p1x,p1y)]
    p2=[p2x,p2y,project_to_sphere(TRACKBALLSIZE,p2x,p2y)]
    a=stltool.cross(p2,p1)
    
    d=map(lambda x,y:x-y,p1,p2)
    t = math.sqrt(sum(map(lambda x:x*x, d))) / (2.0*TRACKBALLSIZE)

    if (t > 1.0): t = 1.0
    if (t < -1.0): t = -1.0
    phi = 2.0 * math.asin(t)

    return axis_to_quat(a,phi)

def vec(*args):
    return (GLfloat * len(args))(*args)
    
def axis_to_quat(a,phi):
    #print a, phi
    lena=math.sqrt(sum(map(lambda x:x*x, a)))
    q=map(lambda x:x*(1/lena),a)
    q=map(lambda x:x*math.sin(phi/2.0),q)
    q.append(math.cos(phi/2.0))
    return q
    
def build_rotmatrix(q):
    m=(GLdouble * 16)()
    m[0] = 1.0 - 2.0 * (q[1] * q[1] + q[2] * q[2])
    m[1] = 2.0 * (q[0] * q[1] - q[2] * q[3]);
    m[2] = 2.0 * (q[2] * q[0] + q[1] * q[3]);
    m[3] = 0.0;

    m[4] = 2.0 * (q[0] * q[1] + q[2] * q[3]);
    m[5]= 1.0 - 2.0 * (q[2] * q[2] + q[0] * q[0]);
    m[6] = 2.0 * (q[1] * q[2] - q[0] * q[3]);
    m[7] = 0.0;

    m[8] = 2.0 * (q[2] * q[0] - q[1] * q[3]);
    m[9] = 2.0 * (q[1] * q[2] + q[0] * q[3]);
    m[10] = 1.0 - 2.0 * (q[1] * q[1] + q[0] * q[0]);
    m[11] = 0.0;

    m[12] = 0.0;
    m[13] = 0.0;
    m[14] = 0.0;
    m[15] = 1.0;
    return m

def project_to_sphere(r, x, y):
    d = math.sqrt(x*x + y*y)
    if (d < r * 0.70710678118654752440):
        return math.sqrt(r*r - d*d)
    else:
        t = r / 1.41421356237309504880
        return t*t / d
        
def mulquat(q1,rq):
    return [q1[3] * rq[0] + q1[0] * rq[3] + q1[1] * rq[2] - q1[2] * rq[1],
                    q1[3] * rq[1] + q1[1] * rq[3] + q1[2] * rq[0] - q1[0] * rq[2],
                    q1[3] * rq[2] + q1[2] * rq[3] + q1[0] * rq[1] - q1[1] * rq[0],
                    q1[3] * rq[3] - q1[0] * rq[0] - q1[1] * rq[1] - q1[2] * rq[2]]

class TestGlPanel(GLPanel):
    
    def __init__(self, parent, id=wx.ID_ANY, pos=(10, 10)):
        super(TestGlPanel, self).__init__(parent, id, wx.DefaultPosition, wx.DefaultSize, 0)
        self.batches=[]
        self.rot=0
        self.canvas.Bind(wx.EVT_MOUSE_EVENTS,self.move)
        self.initialized=1
        self.canvas.Bind(wx.EVT_MOUSEWHEEL,self.wheel)
        self.initp=None
        self.selected=0
        self.dist=200
        self.transv=[0, 0, -self.dist]
        self.basequat=[0,0,0,1]
        wx.CallAfter(self.forceresize)
        
    def forceresize(self):
        self.SetClientSize((self.GetClientSize()[0],self.GetClientSize()[1]+1))
        self.SetClientSize((self.GetClientSize()[0],self.GetClientSize()[1]-1))
        threading.Thread(target=self.update).start()
        self.initialized=0
    
    def move(self, event):
        if event.Dragging() and event.LeftIsDown():
            if self.initp==None:
                self.initp=event.GetPositionTuple()
            else:
                if event.ShiftDown():
                    if self.selected<0:
                        return
                    p1=list(self.initp)
                    p1[1]*=-1
                    self.initp=None
                    p2=list(event.GetPositionTuple())
                    p2[1]*=-1
                    self.batches[self.selected][0]=map(lambda old,new,original:original+(new-old), list(p1)+[0],list(p2)+[0],self.batches[0][0])
                    return
                #print self.initp
                p1=self.initp
                self.initp=None
                p2=event.GetPositionTuple()
                sz=self.GetClientSize()
                p1x=(float(p1[0])-sz[0]/2)/(sz[0]/2)
                p1y=-(float(p1[1])-sz[1]/2)/(sz[1]/2)
                p2x=(float(p2[0])-sz[0]/2)/(sz[0]/2)
                p2y=-(float(p2[1])-sz[1]/2)/(sz[1]/2)
                #print p1x,p1y,p2x,p2y
                quat=trackball(p1x, p1y, p2x, p2y, -self.transv[2]/250.0)
                if self.rot:
                    self.basequat=mulquat(self.basequat,quat)
                #else:
                glGetDoublev(GL_MODELVIEW_MATRIX,self.mvmat)
                #self.basequat=quatx
                mat=build_rotmatrix(self.basequat)
                glLoadIdentity()
                #glTranslatef(-self.transv[0],-self.transv[1],-self.transv[2])
                glTranslatef(*self.transv)
                glMultMatrixd(mat)
                glGetDoublev(GL_MODELVIEW_MATRIX,self.mvmat)
                self.rot=1
            
        elif event.ButtonUp(wx.MOUSE_BTN_LEFT):
            if self.initp is not None:
                self.initp=None
        elif event.ButtonUp(wx.MOUSE_BTN_RIGHT):
            if self.initp is not None:
                self.initp=None
        
        elif event.Dragging() and event.RightIsDown():
                if self.initp is None:
                    self.initp=event.GetPositionTuple()
                else:
                    p1=self.initp
                    p2=event.GetPositionTuple()
                    sz=self.GetClientSize()
                    p1=list(p1)
                    p2=list(p2)
                    p1[1]*=-1
                    p2[1]*=-1
                    
                    self.transv=map(lambda x,y,z,c:c-self.dist*(x-y)/z, list(p1)+[0], list(p2)+[0], list(sz)+[1], self.transv)
                    
                    glLoadIdentity()
                    glTranslatef(*self.transv)
                    if(self.rot):
                        glMultMatrixd(build_rotmatrix(self.basequat))
                    glGetDoublev(GL_MODELVIEW_MATRIX,self.mvmat)
                    self.rot=1
                    self.initp=None
                
    def wheel(self,event):
        z=event.GetWheelRotation()
        delta=10
        if event.ShiftDown():
            if self.selected<0:
                return
                    
            if z > 0:
                self.batches[self.selected][2]+=delta/2
            else:
                self.batches[self.selected][2]-=delta/2
            return
        if z > 0:
            self.transv[2]+=delta
        else:
            self.transv[2]-=delta
        
        glLoadIdentity()
        glTranslatef(*self.transv)
        if(self.rot):
            glMultMatrixd(build_rotmatrix(self.basequat))
        glGetDoublev(GL_MODELVIEW_MATRIX,self.mvmat)
        self.rot=1
    
                
    def update(self):
        while(1):
            dt=0.05
            time.sleep(0.05)
            try:
                wx.CallAfter(self.Refresh)
            except:
                return
            #continue
            global rx, ry, rz
            rx += dt * 1
            ry += dt * 80
            rz += dt * 30
            rx %= 360
            ry %= 360
            rz %= 360
        
    def create_objects(self):
        '''create opengl objects when opengl is initialized'''
        import stltool
        batch = pyglet.graphics.Batch()
        s= stltool.stl("x-end-idler.stl")
        stl = stlview(s.facets, batch=batch)
        #print "added vertices"
        self.batches+=[[[50,50,0],batch,0]]
        #batch = pyglet.graphics.Batch()
        #s= stltool.stl("../prusa/metric-prusa/mbotplate1.stl")
        #stl = stlview(s.facets, batch=batch)
        #print "added vertices"
        #self.batches+=[([-50,-50,0],batch)]
        self.initialized=1
        wx.CallAfter(self.Refresh)
        
    def update_object_resize(self):
        '''called when the window recieves only if opengl is initialized'''
        pass
        
    def draw_objects(self):
        '''called in the middle of ondraw after the buffer has been cleared'''
        if self.vpmat is None:
            return
        if not self.initialized:
            self.create_objects()
        
        #glLoadIdentity()
        #print list(self.pmat)
        if self.rot==1:
            glLoadIdentity()
            glMultMatrixd(self.mvmat)
        else:
            glLoadIdentity()
            glTranslatef(*self.transv)
        #glRotatef(rz, 0, 0, 1)
        #glRotatef(ry, 0, 1, 0)
        #glRotatef(rx, 1, 0, 0)
        glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE, vec(0.2, 0.2, 0.2, 1))
        glBegin(GL_LINES)
        rows=10
        cols=10
        zheight=50
        for i in xrange(-rows,rows+1):
            if i%5==0:
                glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE, vec(0.6, 0.6, 0.6, 1))
            else:
                glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE, vec(0.2, 0.2, 0.2, 1))
            glVertex3f(10*-cols, 10*i,0)
            glVertex3f(10*cols, 10*i,0)
        for i in xrange(-cols,cols+1):
            if i%5==0:
                glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE, vec(0.6, 0.6, 0.6, 1))
            else:
                glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE, vec(0.2, 0.2, 0.2, 1))
            glVertex3f(10*i, 10*-rows,0)
            glVertex3f(10*i, 10*rows,0)
        glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE, vec(0.6, 0.6, 0.6, 1))
        glVertex3f(10*-cols, 10*-rows,0)
        glVertex3f(10*-cols, 10*-rows,zheight)
        glVertex3f(10*cols, 10*rows,0)
        glVertex3f(10*cols, 10*rows,zheight)
        glVertex3f(10*cols, 10*-rows,0)
        glVertex3f(10*cols, 10*-rows,zheight)
        glVertex3f(10*-cols, 10*rows,0)
        glVertex3f(10*-cols, 10*rows,zheight)
        
        glVertex3f(10*-cols, 10*rows,zheight)
        glVertex3f(10*cols, 10*rows,zheight)
        glVertex3f(10*cols, 10*rows,zheight)
        glVertex3f(10*cols, 10*-rows,zheight)
        glVertex3f(10*cols, 10*-rows,zheight)
        glVertex3f(10*-cols, 10*-rows,zheight)
        glVertex3f(10*-cols, 10*-rows,zheight)
        glVertex3f(10*-cols, 10*rows,zheight)
        
        glEnd()
        glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE, vec(0.5, 0.6, 0.3, 1))
        #glTranslatef(0,40,0)
        for i in self.batches:
            glPushMatrix()
            glTranslatef(*i[0])
            glRotatef(i[2],0.0,0.0,1.0)
            #glScalef(1,1,0)
            i[1].draw()
            glPopMatrix()
        #print "drawn batch"
class TestFrame(wx.Frame):
    '''A simple class for using OpenGL with wxPython.'''

    def __init__(self, parent, ID, title, pos=wx.DefaultPosition,
            size=wx.DefaultSize, style=wx.DEFAULT_FRAME_STYLE):
        super(TestFrame, self).__init__(parent, ID, title, pos, size, style)
        
        self.mainsizer = wx.BoxSizer(wx.HORIZONTAL)
        self.GLPanel1 = TestGlPanel(self)
        self.mainsizer.Add(self.GLPanel1, 1, wx.EXPAND)
        #self.GLPanel2 = TestGlPanel(self, wx.ID_ANY, (20, 20))
        #self.mainsizer.Add(self.GLPanel2, 1, wx.EXPAND)
        self.SetSizer(self.mainsizer)
        #self.mainsizer.Fit(self)
        self.Layout()
        
        

    
rx = ry = rz = 0

app = wx.App(redirect=False)
frame = TestFrame(None, wx.ID_ANY, 'GL Window', size=(400,400))
#frame = wx.Frame(None, -1, "GL Window", size=(400,400))
#panel = TestGlPanel(frame)
frame.Show(True)
app.MainLoop()
app.Destroy()
