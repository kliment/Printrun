from distutils.core import setup
import py2exe
import sys 
from glob import glob

data_files = [("Microsoft.VC90.CRT", glob(r'T:\\eclipse-workspace\\Printrun-garyhodgson\\Microsoft.VC90.CRT\\*.*')),
			  ("images", ["images\\arrow_keys.png", "images\\control_z.png", "images\\control_xy.png", "images\\arrow_up.png", "images\\arrow_down.png", "images\\zoom_in.png", "images\\inject.png", "images\\zoom_out.png"]),
			  ("", ["plater.ico", "P-face.ico", "pronsole.ico"])]
sys.path.append("T:\\eclipse-workspace\\Printrun-garyhodgson\\Microsoft.VC90.CRT")
setup(
	data_files=data_files,
	windows=['pronterface.py'],
	options={
                "py2exe":{
                        "excludes": [
				            "Tkconstants","Tkinter","tcl"
				            ]
                }
        }
	)