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

import sys
import os
from stat import S_IRUSR, S_IWUSR, S_IRGRP, S_IROTH
from distutils.core import setup
from distutils.command.install import install as _install
from distutils.command.install_data import install_data as _install_data
try:
    from Cython.Build import cythonize
    extensions = cythonize("printrun/gcoder_line.pyx")
    from Cython.Distutils import build_ext
except ImportError:
    extensions = None
    build_ext = None

from printrun.printcore import __version__ as printcore_version

INSTALLED_FILES = "installed_files"

class install (_install):

    def run(self):
        _install.run(self)
        outputs = self.get_outputs()
        length = 0
        if self.root:
            length += len(self.root)
        if self.prefix:
            length += len(self.prefix)
        if length:
            for counter in xrange(len(outputs)):
                outputs[counter] = outputs[counter][length:]
        data = "\n".join(outputs)
        try:
            file = open(INSTALLED_FILES, "w")
        except:
            self.warn("Could not write installed files list %s" %
                      INSTALLED_FILES)
            return
        file.write(data)
        file.close()

class install_data(_install_data):

    def run(self):
        def chmod_data_file(file):
            try:
                os.chmod(file, S_IRUSR | S_IWUSR | S_IRGRP | S_IROTH)
            except:
                self.warn("Could not chmod data file %s" % file)
        _install_data.run(self)
        map(chmod_data_file, self.get_outputs())

class uninstall(_install):

    def run(self):
        try:
            file = open(INSTALLED_FILES, "r")
        except:
            self.warn("Could not read installed files list %s" %
                      INSTALLED_FILES)
            return
        files = file.readlines()
        file.close()
        prepend = ""
        if self.root:
            prepend += self.root
        if self.prefix:
            prepend += self.prefix
        if len(prepend):
            for counter in xrange(len(files)):
                files[counter] = prepend + files[counter].rstrip()
        for file in files:
            print "Uninstalling", file
            try:
                os.unlink(file)
            except:
                self.warn("Could not remove file %s" % file)

ops = ("install", "build", "sdist", "uninstall", "clean", "build_ext")

if len(sys.argv) < 2 or sys.argv[1] not in ops:
    print "Please specify operation : %s" % " | ".join(ops)
    raise SystemExit

prefix = None
if len(sys.argv) > 2:
    i = 0
    for o in sys.argv:
        if o.startswith("--prefix"):
            if o == "--prefix":
                if len(sys.argv) >= i:
                    prefix = sys.argv[i + 1]
                sys.argv.remove(prefix)
            elif o.startswith("--prefix=") and len(o[9:]):
                prefix = o[9:]
            sys.argv.remove(o)
        i += 1
if not prefix and "PREFIX" in os.environ:
    prefix = os.environ["PREFIX"]
if not prefix or not len(prefix):
    prefix = sys.prefix

if sys.argv[1] in("install", "uninstall") and len(prefix):
    sys.argv += ["--prefix", prefix]

target_images_path = "share/pronterface/images/"
data_files = [('share/pixmaps/', ['pronterface.png', 'plater.png', 'pronsole.png']),
              ('share/applications', ['pronterface.desktop', 'pronsole.desktop', 'plater.desktop']),
              ('share/appdata', ['pronterface.appdata.xml', 'pronsole.appdata.xml', 'plater.appdata.xml'])]

for basedir, subdirs, files in os.walk("images"):
    images = []
    for filename in files:
        if filename.find(".svg") or filename.find(".png"):
            file_path = os.path.join(basedir, filename)
            images.append(file_path)
    data_files.append((target_images_path + basedir[len("images/"):], images))

for basedir, subdirs, files in os.walk("locale"):
    if not basedir.endswith("LC_MESSAGES"):
        continue
    destpath = os.path.join("share", "pronterface", basedir)
    files = filter(lambda x: x.endswith(".mo"), files)
    files = map(lambda x: os.path.join(basedir, x), files)
    data_files.append((destpath, files))

extra_data_dirs = ["css"]
for extra_data_dir in extra_data_dirs:
    for basedir, subdirs, files in os.walk(extra_data_dir):
        files = map(lambda x: os.path.join(basedir, x), files)
        destpath = os.path.join("share", "pronterface", basedir)
        data_files.append((destpath, files))

cmdclass = {"uninstall": uninstall,
            "install": install,
            "install_data": install_data}
if build_ext:
    cmdclass['build_ext'] = build_ext

setup(name = "Printrun",
      version = printcore_version,
      description = "Host software for 3D printers",
      author = "Kliment Yanev",
      url = "http://github.com/kliment/Printrun/",
      license = "GPLv3",
      data_files = data_files,
      packages = ["printrun", "printrun.gl", "printrun.gl.libtatlin", "printrun.gui", "printrun.power"],
      scripts = ["pronsole.py", "pronterface.py", "plater.py", "printcore.py"],
      cmdclass = cmdclass,
      ext_modules = extensions,
      )
