Printrun consists of printcore, pronsole and pronterface, and a small collection of helpful scripts.

  * printcore.py is a library that makes writing reprap hosts easy
  * pronsole.py is an interactive command-line host software with tabcompletion goodness
  * pronterface.py is a graphical host software with the same functionality as pronsole

# GETTING PRINTRUN

This section suggests using precompiled binaries, this way you get everything bundled into one single package for an easy installation.

If you want the newest, shiniest features, you can run Printrun from source using the instructions further down this README.

## Windows

A precompiled version is available at http://koti.kapsi.fi/~kliment/printrun/

## Mac OS X

A precompiled version is available at http://koti.kapsi.fi/~kliment/printrun/

## Linux
### Ubuntu/Debian

You can run Printrun directly from source, as there are no packages available yet. Fetch and install the dependencies using

1. `sudo apt-get install python-serial python-wxgtk2.8 python-pyglet python-numpy cython python-libxml2 python-gobject python-dbus python-psutil git`

Clone the repository

`git clone https://github.com/kliment/Printrun.git`

and you can start using Printrun from the Printrun directory created by the git clone command.

### Chrome OS 

You can use Printrun via crouton ( https://github.com/dnschneid/crouton ). Assuming you want Ubuntu Trusty, you used probably `sudo sh -e ~/Downloads/crouton -r trusty -t xfce` to install Ubuntu. Fetch and install dependencies with the line given above for Ubuntu/Debian, and obtain the source via git clone.

By default you have no access to the serial port under Chrome OS crouton, so you cannot connect to your 3D printer. Add yourself to the serial group within the linux environment to fix this

`sudo usermod -G serial -a <username>` 

where `<username>` should be your username. Log out and in to make this group change active and allow communication with your printer. 

### Fedora

You can install Printrun from official packages. Install the whole package using

`sudo yum install printrun`

Or get only apps you need by

`sudo yum install pronsole` or `pronterface` or `plater`

Adding `--enablerepo updates-testing` option to `yum` might give you newer packages (but also not very tested).

You can also run Printrun directly from source, if the packages are too old for you. Fetch and install the dependencies using

1. `sudo yum install pyserial wxPython python-pyglet python-cairosvg`

Optional: `sudo yum install skeinforge simarrange`

### Archlinux

Packages are available in AUR. Just run

`yaourt printrun`

and enjoy the `pronterface`, `pronsole`, ... commands directly.

## RUNNING FROM SOURCE

Run Printrun for source if you want to test out the latest features.

### Dependencies

To use pronterface, you need:

  * python (ideally 2.6.x or 2.7.x),
  * pyserial (or python-serial on ubuntu/debian)
  * pyreadline (not needed on Linux) and
  * argparse (installed by default with python >= 2.7)
  * wxPython (some features such as Tabbed mode work better with wx 2.9)
  * pyglet
  * numpy (for 3D view)
  * pycairo (to use Projector feature)
  * cairosvg (to use Projector feature)
  * dbus (to inhibit sleep on some Linux systems)

Please see specific instructions for Windows and Mac OS X below. Under Linux, you should use your package manager directly (see the "GETTING PRINTRUN" section), or pip:

```pip install -r requirements.txt```

### Cython-based G-Code parser

Printrun default G-Code parser is quite memory hungry, but we also provide a much lighter one which just needs an extra build-time dependency (Cython), plus compiling the extension with:

    python setup.py build_ext --inplace

The warning message

    WARNING:root:Memory-efficient GCoder implementation unavailable: No module named gcoder_line

means that this optimized G-Code parser hasn't been compiled. To get rid of it and benefit from the better implementation, please install Cython and run the command above.

### Windows

Download the following, and install in this order:

  1. http://python.org/ftp/python/2.7.2/python-2.7.2.msi
  2. http://pypi.python.org/packages/any/p/pyserial/pyserial-2.5.win32.exe
  3. http://downloads.sourceforge.net/wxpython/wxPython2.8-win32-unicode-2.8.12.0-py27.exe
  4. https://pypi.python.org/packages/any/p/pyreadline/pyreadline-1.7.1.win32.exe
  5. http://pyglet.googlecode.com/files/pyglet-1.1.4.zip

For the last one, you will need to unpack it, open a command terminal, 
go into the the directory you unpacked it in and run
`python setup.py install`

### Mac OS X Lion

  1. Ensure that the active Python is the system version. (`brew uninstall python` or other appropriate incantations)
  2. Download an install [wxPython2.8-osx-unicode] matching to your python version (most likely 2.7 on Lion, 
        check with: python --version) from: http://wxpython.org/download.php#stable
  Known to work PythonWX: http://superb-sea2.dl.sourceforge.net/project/wxpython/wxPython/2.8.12.1/wxPython2.8-osx-unicode-2.8.12.1-universal-py2.7.dmg
  3. Download and unpack pyserial from http://pypi.python.org/packages/source/p/pyserial/pyserial-2.5.tar.gz
  4. In a terminal, change to the folder you unzipped to, then type in: `sudo python setup.py install`
  5. Repeat 4. with http://http://pyglet.googlecode.com/files/pyglet-1.1.4.zip

The tools will probably run just fine in 64bit on Lion, you don't need to mess
with any of the 32bit settings. In case they don't, try 
  5. export VERSIONER_PYTHON_PREFER_32_BIT=yes
in a terminal before running Pronterface

### Mac OS X (pre Lion)

A precompiled version is available at http://koti.kapsi.fi/~kliment/printrun/

  1. Download and install http://downloads.sourceforge.net/wxpython/wxPython2.8-osx-unicode-2.8.12.0-universal-py2.6.dmg
  2. Grab the source for pyserial from http://pypi.python.org/packages/source/p/pyserial/pyserial-2.5.tar.gz
  3. Unzip pyserial to a folder. Then, in a terminal, change to the folder you unzipped to, then type in:
     
     `defaults write com.apple.versioner.python Prefer-32-Bit -bool yes`
     
     `sudo python setup.py install`

Alternatively, you can run python in 32 bit mode by setting the following environment variable before running the setup.py command:

This alternative approach is confirmed to work on Mac OS X 10.6.8. 

`export VERSIONER_PYTHON_PREFER_32_BIT=yes`

`sudo python setup.py install`

Then repeat the same with http://http://pyglet.googlecode.com/files/pyglet-1.1.4.zip

# USING PRINTRUN

## USING PRONTERFACE

When you're done setting up Printrun, you can start pronterface.py in the directory you unpacked it.
Select the port name you are using from the first drop-down, select your baud rate, and hit connect.
Load an STL (see the note on skeinforge below) or GCODE file, and you can upload it to SD or print it directly.
The "monitor printer" function, when enabled, checks the printer state (temperatures, SD print progress) every 3 seconds.
The command box recognizes all pronsole commands, but has no tabcompletion.

If you want to load stl files, you need to install a slicing program such as Slic3r and add its path to the settings.
See the Slic3r readme for more details on integration.


## USING PRONSOLE

To use pronsole, you need:

  * python (ideally 2.6.x or 2.7.x),
  * pyserial (or python-serial on ubuntu/debian) and
  * pyreadline (not needed on Linux)

Start pronsole and you will be greeted with a command prompt. Type help to view the available commands.
All commands have internal help, which you can access by typing "help commandname", for example "help connect"

If you want to load stl files, you need to put a version of skeinforge (doesn't matter which one) in a folder called "skeinforge".
The "skeinforge" folder must be in the same folder as pronsole.py

## USING PRINTCORE

To use printcore you need python (ideally 2.6.x or 2.7.x) and pyserial (or python-serial on ubuntu/debian)
See pronsole for an example of a full-featured host, the bottom of printcore.py for a simple command-line
sender, or the following code example:

```python
#to send a file of gcode to the printer
from printrun.printcore import printcore
from printrun import gcoder
p=printcore('/dev/ttyUSB0',115200) # or p.printcore('COM3',115200) on Windows
gcode=[i.strip() for i in open('filename.gcode')] # or pass in your own array of gcode lines instead of reading from a file
gcode = gcoder.LightGCode(gcode)
p.startprint(gcode) # this will start a print

#If you need to interact with the printer:
p.send_now("M105") # this will send M105 immediately, ahead of the rest of the print
p.pause() # use these to pause/resume the current print
p.resume()
p.disconnect() # this is how you disconnect from the printer once you are done. This will also stop running prints.
```

## PLATERS

Printrun provides two platers: a STL plater (```plater.py```) and a G-Code plater (```gcodeplater.py```).

## 3D VIEWER CONTROLS

When the 3D viewer is enabled, the controls are the following:
- Mousewheel: zoom (Control reduces the zoom change steps)
- Shift+mousewheel: explore layers (in print gcode view ; Control key makes layer change by increments of 10 instead of 1) or rotate object (in platers)
- Left-click dragging: rotate view
- Right-click dragging: pan view
- Shift + left-click dragging: move object (in platers)
- Page up/down keys: zoom (Control reduces the zoom change steps)
- Up/down keys: explore layers
- R key: reset view
- F key: fit view to display entire print
- C key: toggle "display current layer only" mode (in print gcode view)

## RPC SERVER

```pronterface``` and ```pronsole``` start a RPC server, which runs by default
on localhost port 7978, which provides print progress information.
Here is a sample Python script querying the print status:

```python
import xmlrpclib

rpc = xmlrpclib.ServerProxy('http://localhost:7978')
print rpc.status()
```

## CONFIGURATION

### Build dimensions

Build dimensions can be specified using the build_dimensions option (which can
be graphically edited in Pronterface settings). This option is formed of 9 parameters:
3 for the build volume dimensions, 3 for the build volume coordinate system
offset minimum, 3 for the endstop positions.

The default value is `200x200x100+0+0+0+0+0+0`, which corresponds to a
200x200mm (width x height) bed with 100mm travel in Z (there are the first
three numbers) and no offset. The absolute coordinates system origin (0,0,0) is
at the bottom left corner on the bed surface, and the top right corner on the
bed surface is (200,200,0).

A common practice is to have the origin of the coordinate system (0,0,0) at the
center of the bed surface. This is achieved by using the next three parameters,
for instance with `200x200x100-100-100+0+0+0+0`.
In this case, the bottom left corner of the bed will be at (-100,-100,0) and
the top right one at (100,100,0).

These two sets of settings should be sufficient for most people. However, for
some specific complicated setups and GCodes and some features, we might also
need the endstops positions for perfect display. These positions (which are
usually 0,0,0, so if you don't know you probably have a standard setup) are
specified in absolute coordinates, so if you have your bed starting at
(-100,-100,0) and your endstops are 10mm away from the bed left and right and
the Z endstop 5mm above the bed, you'll want to set the endstops positions to
(-110,-110,5) for this option.

## USING MACROS AND CUSTOM BUTTONS

### Macros in pronsole and pronterface

To send simple G-code (or pronsole command) sequence is as simple as entering them one by one in macro definition.
If you want to use parameters for your macros, substitute them with {0} {1} {2} ... etc.

All macros are saved automatically immediately after being entered.

Example 1, simple one-line alias:

```python
PC> macro where M114
```

Instead of having to remember the code to query position, you can query the position:

```python
PC> where
X:25.00Y:11.43Z:5.11E:0.00
```

Example 2 - macros to switch between different slicer programs, using "set" command to change options:

```python
PC> macro use_slicer
Enter macro using indented lines, end with empty line
..> set sliceoptscommand Slic3r/slic3r.exe --load slic3r.ini
..> set slicecommand Slic3r/slic3r.exe $s --load slic3r.ini --output $o
Macro 'use_slicer' defined
PC> macro use_sfact
..> set sliceoptscommand python skeinforge/skeinforge_application/skeinforge.py
..> set slicecommand python skeinforge/skeinforge_application/skeinforge_utilities/skeinforge_craft.py $s
Macro 'use_sfact' defined
```

Example 3, simple parametric macro:

```python
PC> macro move_down_by
Enter macro using indented lines, end with empty line
..> G91
..> G1 Z-{0}
..> G92
..>
```

Invoke the macro to move the printhead down by 5 millimeters:

```python
PC> move_down_by 5
```

For more powerful macro programming, it is possible to use python code escaping using ! symbol in front of macro commands.
Note that this python code invocation also works in interactive prompt:

```python
PC> !print "Hello, printer!"
Hello printer!

PC> macro debug_on !self.p.loud = 1
Macro 'debug_on' defined
PC> debug_on
PC> M114
SENT:  M114
X:0.00Y:0.00Z:0.00E:0.00 Count X:0.00Y:0.00Z:0.00
RECV:  X:0.00Y:0.00Z:0.00E:0.00 Count X:0.00Y:0.00Z:0.00
RECV:  ok
```

You can use macro command itself to create simple self-modify or toggle functionality:

Example: swapping two macros to implement toggle:

```python
PC> macro toggle_debug_on
Enter macro using indented lines, end with empty line
..> !self.p.loud = 1
..> !print "Diagnostic information ON"
..> macro toggle_debug toggle_debug_off
..>
Macro 'toggle_debug_on' defined
PC> macro toggle_debug_off
Enter macro using indented lines, end with empty line
..> !self.p.loud = 0
..> !print "Diagnostic information OFF"
..> macro toggle_debug toggle_debug_on
..>
Macro 'toggle_debug_off' defined
PC> macro toggle_debug toggle_debug_on
Macro 'toggle_debug' defined
```

Now, each time we invoke "toggle_debug" macro, it toggles debug information on and off:

```python
PC> toggle_debug
Diagnostic information ON

PC> toggle_debug
Diagnostic information OFF
```

When python code (using ! symbol) is used in macros, it is even possible to use blocks/conditionals/loops.
It is okay to mix python code with pronsole commands, just keep the python indentation.
For example, following macro toggles the diagnostic information similarily to the previous example:

```python
!if self.p.loud:
  !self.p.loud = 0
  !print "Diagnostic information OFF"
!else:
  !self.p.loud = 1
  !print "Diagnostic information ON"
```

Macro parameters are available in '!'-escaped python code as locally defined list variable: arg[0] arg[1] ... arg[N]

All python code is executed in the context of the pronsole (or PronterWindow) object, 
so it is possible to use all internal variables and methods, which provide great deal of functionality.
However the internal variables and methods are not very well documented and may be subject of change, as the program is developed.
Therefore it is best to use pronsole commands, which easily contain majority of the functionality that might be needed.

Some useful python-mode-only variables:

```python
!self.settings - contains all settings, e.g. 
  port (!self.settings.port), baudrate, xy_feedrate, e_feedrate, slicecommand, final_command, build_dimensions
  You can set them also via pronsole command "set", but you can query the values only via python code.
!self.p - printcore object (see USING PRINTCORE section for using printcore object)
!self.cur_button - if macro was invoked via custom button, the number of the custom button, e.g. for usage in "button" command
!self.gwindow - wx graphical interface object for pronterface (highly risky to use because the GUI implementation details may change a lot between versions)
```

Some useful methods:

```python
!self.onecmd - invokes raw command, e.g. 
    !self.onecmd("move x 10")
    !self.onecmd("!print self.p.loud")
    !self.onecmd("button "+self.cur_button+" fanOFF /C cyan M107")
!self.project - invoke Projector
```

## USING HOST COMMANDS

Pronsole and the console interface in Pronterface accept a number of commands
which you can either use directly or inside your G-Code. To run a host command
from inside a G-Code, simply prefix it with `;@`.

List of available commands:

- `pause`: pauses the print until the user resumes it
- `run_script scriptname [arg1 ...]`: runs a custom script or program on the
  host computer. This can for instance be used to produce a sound to warn the
  user (e.g. `run_script beep -r 2` on machines were the `beep` util is
  available), or to send an email or text message at the end of a print. The $s
  token can be used in the arguments to get the current gcode file name
- `run_gcode_script scripname [arg1 ...]`: same as `run_script`, except that
  all lines displayed by the script will be interpreted in turn (so that G-Code
  lines will be immediately sent to the printer)
- `shell pythoncommand`: run a python command (can also be achieved by doing
  `!pythoncommand`)
- `set option value`: sets the value of an option, e.g. `set mainviz 3D`
- `connect`
- `block_until_online`: wait for the printer to be online. For instance you can
  do `python pronsole.py -e "connect" -e "block_until_online" -e "upload
  object.gcode"` to start pronsole, connect for the printer, wait for it to be
  online to start uploading the `object.gcode` file.
- `disconnect`
- `load gcodefile`
- `upload gcodefile target.g`: upload `gcodefile` to `target.g` on the SD card
- `slice stlfile`: slice `stlfile` and load the produced G-Code
- `print`: print the currently loaded file
- `sdprint target.g`: start a SD print
- `ls`: list files on SD card
- `eta`: display remaining print time
- `gettemp`: get current printer temperatures
- `settemp`: set hotend target temperature
- `bedtemp`: set bed target temperature
- `monitor`: monitor printer progress during a print
- `tool K`: switch to tool K
- `move xK`: move along `x` axis (works with other axes too)
- `extrude length [speed]`
- `reverse length [speed]`
- `home [axis]`
- `off`: turns off fans, motors, extruder, heatbed, power supply
- `exit`

# LICENSE

```
Printrun is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Printrun is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Printrun.  If not, see <http://www.gnu.org/licenses/>.
```

All scripts should contain this license note, if not, feel free to ask us. Please note that files where it is difficult to state this license note (such as images) are distributed under the same terms.
