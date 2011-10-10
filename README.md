Printrun consists of printcore, pronsole and pronterface, and a small collection of helpful scripts.

  * printcore.py is a library that makes writing reprap hosts easy
  * pronsole.py is an interactive command-line host software with tabcompletion goodness
  * pronterface.py is a graphical host software with the same functionality as pronsole

# INSTALLING DEPENDENCIES

## Windows
Download the following, and install in this order:

  1. http://python.org/ftp/python/2.7.2/python-2.7.2.msi
  2. http://pypi.python.org/packages/any/p/pyserial/pyserial-2.5.win32.exe
  3. http://downloads.sourceforge.net/wxpython/wxPython2.8-win32-unicode-2.8.12.0-py27.exe
  4. http://launchpad.net/pyreadline/1.7/1.7/+download/pyreadline-1.7.zip
## Ubuntu/Debian
`sudo apt-get install python-serial python-wxgtk2.8`

## Fedora 15
`sudo yum install pyserial wxpython`

## Mac OS X Lion

  1. Ensure that the active Python is the system version. (`brew uninstall python` or other appropriate incantations)
  2. Download an install [wxPython version 2.9-Carbon](http://wxpython.org/download.php#unstable) (the Cocoa version doesn't work)
  3. Download and unpack pyserial from http://pypi.python.org/packages/source/p/pyserial/pyserial-2.5.tar.gz
  4. In a terminal, change to the folder you unzipped to, then type in: `sudo python setup.py install`

The tools will probably run just fine in 64bit on Lion, you don't need to mess
with any of the 32bit settings. In case they don't, try 
  5. export VERSIONER_PYTHON_PREFER_32_BIT=yes
in a terminal before running Pronterface

## Mac OS X (pre Lion)
  1. Download and install http://downloads.sourceforge.net/wxpython/wxPython2.8-osx-unicode-2.8.12.0-universal-py2.6.dmg
  2. Grab the source for pyserial from http://pypi.python.org/packages/source/p/pyserial/pyserial-2.5.tar.gz
  3. Unzip pyserial to a folder. Then, in a terminal, change to the folder you unzipped to, then type in:
     
     `defaults write com.apple.versioner.python Prefer-32-Bit -bool yes`
     
     `sudo python setup.py install`

Alternatively, you can run python in 32 bit mode by setting the following environment variable before running the setup.py command:

`export VERSIONER_PYTHON_PREFER_32_BIT=yes`

Then repeat the same with http://launchpad.net/pyreadline/trunk/1.7/+download/pyreadline-1.7.zip

# USING PRONTERFACE

To use pronterface, you need:

  * python (ideally 2.6.x or 2.7.x),
  * pyserial (or python-serial on ubuntu/debian),
  * pyreadline (not needed on Linux) and
  * wxPython

Download and install the above, and start pronterface.py
Select the port name you are using from the first drop-down, select your baud rate, and hit connect.
Load an STL (see the note on skeinforge below) or GCODE file, and you can upload it to SD or print it directly.
The "monitor printer" function, when enabled, checks the printer state (temperatures, SD print progress) every 3 seconds.
The command box recognizes all pronsole commands, but has no tabcompletion.

If you want to load stl files, you need to put a version of skeinforge (doesn't matter which one) in a folder called "skeinforge".
The "skeinforge" folder must be in the same folder as pronterface.py

# USING PRONSOLE

To use pronsole, you need:

  * python (ideally 2.6.x or 2.7.x),
  * pyserial (or python-serial on ubuntu/debian) and
  * pyreadline (not needed on Linux)

Start pronsole and you will be greeted with a command prompt. Type help to view the available commands.
All commands have internal help, which you can access by typing "help commandname", for example "help connect"

If you want to load stl files, you need to put a version of skeinforge (doesn't matter which one) in a folder called "skeinforge".
The "skeinforge" folder must be in the same folder as pronsole.py

# USING PRINTCORE

To use printcore you need python (ideally 2.6.x or 2.7.x) and pyserial (or python-serial on ubuntu/debian)
See pronsole for an example of a full-featured host, the bottom of printcore.py for a simple command-line
sender, or the following code example:

    p=printcore('/dev/ttyUSB0',115200)
    p.startprint(data) # data is an array of gcode lines
    p.send_now("M105") # sends M105 as soon as possible
    p.pause()
    p.resume()
    p.disconnect()


