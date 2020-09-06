#!/usr/bin/env python3

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

import ast
import glob
from setuptools import setup
from setuptools import find_packages

try:
    from Cython.Build import cythonize
    extensions = cythonize("printrun/gcoder_line.pyx")
    from Cython.Distutils import build_ext
except ImportError as e:
    print("WARNING: Failed to cythonize: %s" % e)
    # Debug helper: uncomment these:
    # import traceback
    # traceback.print_exc()
    extensions = None
    build_ext = None


with open('README.md') as f:
    long_description = f.read()

with open('requirements.txt') as f:
    install_requires = f.readlines()

with open('printrun/printcore.py') as f:
    for line in f.readlines():
        if line.startswith("__version__"):
            __version__ = ast.literal_eval(line.split("=")[1].strip())


def multiglob(*globs):
    paths = []
    for g in globs:
        paths.extend(glob.glob(g))
    return paths


data_files = [
    ('share/pixmaps', multiglob('*.png')),
    ('share/applications', multiglob('*.desktop')),
    ('share/metainfo', multiglob('*.appdata.xml')),
    ('share/pronterface/images', multiglob('images/*.png',
                                    'images/*.svg')),
]

for locale in glob.glob('locale/*/LC_MESSAGES/'):
    data_files.append((f'share/{locale}', glob.glob(f'{locale}/*.mo')))


setup(
    name="Printrun",
    version=__version__,
    description="Host software for 3D printers",
    author="Kliment Yanev, Guillaume Seguin and others",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="http://github.com/kliment/Printrun/",
    license="GPLv3+",
    data_files=data_files,
    packages=find_packages(),
    scripts=["pronsole.py", "pronterface.py", "plater.py", "printcore.py"],
    ext_modules=extensions,
    python_requires=">=3.6",
    install_requires=install_requires,
    setup_requires=["Cython"],
    classifiers=[
        "Environment :: X11 Applications :: GTK",
        "Intended Audience :: End Users/Desktop",
        "Intended Audience :: Manufacturing",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Topic :: Printing",
    ],
    zip_safe=False,
)
