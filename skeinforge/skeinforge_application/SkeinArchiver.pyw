#! /usr/bin/python

# Title:  SkeinArchiver.py
# Author: James Blackwell
# Date:   20-Apr-11
# Desc:   This script provides a simple GUI to save and restore Skeinforge user settings.


from __future__ import with_statement
import sys, os, datetime
import Tkinter, tkMessageBox, tkFileDialog
from contextlib import closing
from zipfile import ZipFile, ZIP_DEFLATED


AboutString = 'SkeinArchiver v0.1\nAuthor: James Blackwell\nDate: 20-Apr-11'
ArchDir = None

def ZipDir(basedir, archivename):
   """Zip everything in the specified directory and put in the specified archive"""
   assert os.path.isdir(basedir)
   with closing(ZipFile(archivename, "w", ZIP_DEFLATED)) as z:
      for root, dirs, files in os.walk(basedir):
         #NOTE: ignore empty directories
         for fn in files:
            absfn = os.path.join(root, fn)
            zfn = absfn[len(basedir)+len(os.sep):] #XXX: relative path
            z.write(absfn, zfn)

def UnzipDir(basedir, archivename):
   """Unzip everything from the specified archive to the specified directory"""
   zip = ZipFile(archivename, 'r')
   zip.extractall(basedir)
                
def About():
   """Show the About Information"""
   tkMessageBox.showinfo(title='About', message=AboutString)

def Save():
   """Allow user to specify zip filename, then zip up everything in the archive directory"""
   file='Archived Settings %s.zip' % (datetime.datetime.today().strftime('%d%b%y'))
   filename = tkFileDialog.asksaveasfilename(defaultextension='zip', initialfile=file)
   if filename != '':
      ZipDir(ArchDir, filename)
   
def Restore():
   """Let the user pick a zip file to restore to the archive directory"""
   filename = tkFileDialog.askopenfilename(filetypes=[('zip files', '.zip')])
   if filename != '':
      UnzipDir(ArchDir, filename)
   
def SetArch():
   """Allow the user to select the archive directory, it defaults to the default Skeinforge directory"""
   global ArchDir
   dir = tkFileDialog.askdirectory(initialdir=ArchDir)
   if dir != '':
      ArchDir = dir
   
def BuildMainWindow(tk):
   """Build the main window of the program"""
   pad = 2
   width = 9
   tk.Label(text='SkeinArchiver').grid(row=0, column=0, columnspan=2)#pack(fill=Tkinter.X)
   
   tk.Button(text='Save', width=width, command=Save).grid(row=1, column=0, padx=pad, pady =pad)
   tk.Button(text='Restore', width=width, command=Restore).grid(row=1, column=1, padx=pad, pady =pad)
   tk.Button(text='Dir to Arch', width=width, command=SetArch).grid(row=2, column=0, padx=pad, pady =pad)
   tk.Button(text='About', width=width, command=About).grid(row=2, column=1, padx=pad, pady =pad)
   tk.Button(text='Quit', width=width, command=sys.exit).grid(row=3, column=0, columnspan=2, padx=pad, pady =pad)
   
def Main():
   global ArchDir
   # Set Archive Directory to the default Skeinforge settings directory
   ArchDir = os.path.expanduser('~') + '\.skeinforge'
   root = Tkinter.Tk()
   root.title('SkeinArchiver')
   BuildMainWindow(Tkinter)
   root.mainloop()
   
if __name__ == '__main__':
   Main()