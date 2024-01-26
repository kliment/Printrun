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
from setuptools import Extension, find_packages, setup

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

extensions = [
    Extension(
        name="printrun.gcoder_line",
        sources=["printrun/gcoder_line.pyx"])
    ]

setup(
    version=__version__,
    data_files=data_files,
    packages=find_packages(),
    scripts=["pronsole.py", "pronterface.py", "plater.py", "printcore.py"],
    ext_modules=extensions,
    install_requires=install_requires,
    zip_safe=False,
)
