from distutils.core import setup

setup(windows = [{"script": "pronterface.py", "icon_resources": [(1, "P-face.ico")]},
                 {"script": "plater.py", "icon_resources": [(1, "plater.ico")]},
                 ],
      console = [{"script": "pronsole.py", "icon_resources": [(1, "pronsole.ico")]},
                 ],
      options = {"py2exe": {"bundle_files": 1,
                            "dll_excludes": ["w9xpopen.exe"],
                            "compressed": 1,
                            "excludes": ['_ssl', 'pickle', 'calendar', 'Tkconstants', 'Tkinter', 'tcl', 'email']
                            }
                 }
      )
