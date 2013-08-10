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

__doc__="""
#######################
### How to use this ###
#######################
  1. Check that you can run pronterface.py and pronsole.py directly with python.
  2. Get and install py2exe (see: www.py2exe.org)
  3. Copy "msvcp90.dll" from some copy into the directory that holds all of printruns
     files (same directory as this file ;)).
     You either have it already somewhere on your hard drive as it comes with the Microsoft 
     Visual C++ Runtime Components or you can get it from older binaries of print run.
  4. Run "compile_with_py2exe.bat". This will create the directories "build" and "dist" and
     "compile_output.txt" which contains all the output from the packing. Check this file for
     any errors and missing dependencies (especially the missing packages at the end of 
     compile_output.txt). It also tells you which other Windows related files you will need to
     distribute this package. Lastly the "dist" folder contains the *.exe files you want.
     

  TO DO: this does not change the slic3r settings and the resulting executables will still
         attemt to run slic3r via python.

#######################
###  End of How-To  ###
#######################
"""

import sys
import os
from stat import S_IRUSR, S_IWUSR, S_IRGRP, S_IROTH
from distutils.core import setup
import py2exe
from distutils.command.install import install as _install
from distutils.command.install_data import install_data as _install_data
try:
    from Cython.Build import cythonize
    extensions = cythonize("printrun/gcoder_line.pyx")
    from Cython.Distutils import build_ext
except ImportError:
    extensions = None
    build_ext = None

target_images_path = "./images"
data_files = [('.', ['P-face.ico', 'plater.ico', 'pronsole.ico'])]

for basedir, subdirs, files in os.walk("images"):
    images = []
    for filename in files:
        if filename.find(".svg") or filename.find(".png"):
            file_path = os.path.join(basedir, filename)
            images.append(file_path)
    data_files.append((target_images_path + basedir[len("images"):], images))

for basedir, subdirs, files in os.walk("locale"):
    if not basedir.endswith("LC_MESSAGES"):
        continue
    destpath = basedir
    files = filter(lambda x: x.endswith(".mo"), files)
    files = map(lambda x: os.path.join(basedir, x), files)
    data_files.append((destpath, files))

extra_data_dirs = ["css"]
for extra_data_dir in extra_data_dirs:
    for basedir, subdirs, files in os.walk(extra_data_dir):
        files = map(lambda x: os.path.join(basedir, x), files)
        destpath = basedir
        data_files.append((destpath, files))

print data_files

setup(
    windows=[{'script':'pronterface.py','icon_resources':[(1,'P-face.ico')]}, {'script':'plater.py','icon_resources':[(1,'plater.ico')]}],
    console=[{'script':'pronsole.py','icon_resources':[(1,'pronsole.ico')]}],
    data_files=data_files,
    options={'py2exe':{'bundle_files':1,'compressed':1}}
)

