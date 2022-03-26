# PRINTRUN 2.X

The master branch holds the development of Printrun 2.x. This version of Printrun supports Python 3 and wxPython 4. All new features and developments should be merged to it.

Printrun consists of printcore, pronsole and pronterface, and a small collection of helpful scripts.

  * printcore.py is a library that makes writing reprap hosts easy
  * pronsole.py is an interactive command-line host software with tabcompletion goodness
  * pronterface.py is a graphical host software with the same functionality as pronsole

# CONTRIBUTORS

An enormous number of people helped make Printrun. See the list [here](CONTRIBUTORS.md)

# GETTING PRINTRUN

This section suggests using precompiled binaries, this way you get everything bundled into one single package for an easy installation.

If you want the newest, shiniest features, you can run Printrun from source using the instructions further down this README.

## Windows

A precompiled version is available at https://github.com/kliment/Printrun/releases

## MacOS

A precompiled version is available at https://github.com/kliment/Printrun/releases

Note for OSX users: if OSX tells you `"pronterface.app" cannot be opened because the developer cannot be verified.`, you don't need to redownload it. Instead, you need to allow OSX to run the unsigned app. To do this, right click the application in Finder and select `Open`. Then click `Open` in the popup window that appears. You only need to do this once.


## Linux
### Ubuntu/Debian

You can install Printrun from official packages. Install the whole package using

```
sudo apt update
sudo apt install printrun
```

Or get only apps you need by

`sudo apt install pronsole` or `pronterface` or `plater`

Only Printrun 1 is currently available for users running Debian 10, Ubuntu 18.04 or any earlier versions. Printrun 2 must be [run from source](https://github.com/kliment/Printrun/tree/master#running-from-source).

### Chrome OS

You can use Printrun via crouton ( https://github.com/dnschneid/crouton ). Assuming you want Ubuntu Trusty, you used probably `sudo sh -e ~/Downloads/crouton -r trusty -t xfce` to install Ubuntu. Fetch and install printrun with the line given above for Ubuntu/Debian.

By default you have no access to the serial port under Chrome OS crouton, so you cannot connect to your 3D printer. Add yourself to the serial group within the linux environment to fix this

`sudo usermod -G serial -a <username>`

where `<username>` should be your username. Log out and in to make this group change active and allow communication with your printer.

### Fedora

You can install Printrun from official packages. Install the whole package using

`sudo dnf install printrun`

Or get only apps you need by

`sudo dnf install pronsole` or `pronterface` or `plater`

Adding `--enablerepo updates-testing` option to `dnf` might sometimes give you newer packages (but also not very tested).


### Archlinux

Packages are available in AUR. Just run

`yaourt printrun`

and enjoy the `pronterface`, `pronsole`, ... commands directly.

## RUNNING FROM SOURCE

Run Printrun for source if you want to test out the latest features.

### Dependencies

To use pronterface, you need:

  * Python 3 (ideally 3.6),
  * pyserial (or python3-serial on ubuntu/debian)
  * pyreadline (not needed on Linux)
  * wxPython 4
  * pyglet
  * appdirs
  * numpy (for 3D view)
  * pycairo (to use Projector feature)
  * cairosvg (to use Projector feature)
  * dbus (to inhibit sleep on some Linux systems)

### Use Python virtual environment

Easiest way to run Printrun from source is to create and use a Python [virtual environment](https://docs.python.org/3/tutorial/venv.html).
The following section assumes Linux. Please see specific instructions for Windows and macOS below.

**Ubuntu/Debian note:** You might need to install `python3-venv` first.

**Note:** wxPython4 doesn't have Linux wheels available from the Python Package Index yet. Find a proper wheel for your distro at [extras.wxpython.org](https://extras.wxpython.org/wxPython4/extras/linux/gtk3/) and substitute the link in the below example. You might skip the wheel installation, but that results in compiling wxPython4 from source, which can be time and resource consuming and might fail.


```console
$ git clone https://github.com/kliment/Printrun.git  # clone the repository
$ cd Printrun  # change to Printrun directory
$ python3 -m venv venv  # create an virtual environment
$ . venv/bin/activate  # activate the virtual environment (notice the space after the dot)
(venv) $ python -m pip install https://extras.wxpython.org/wxPython4/extras/linux/gtk3/fedora-27/wxPython-4.0.1-cp36-cp36m-linux_x86_64.whl  # replace the link with yours
(venv) $ python -m pip install -r requirements.txt  # install the rest of dependencies
(venv) $ python pronterface.py  # run Pronterface
```

### Cython-based G-Code parser

Printrun default G-Code parser is quite memory hungry, but we also provide a much lighter one which just needs an extra build-time dependency (Cython), plus compiling the extension with:

```console
(venv) $ python -m pip install Cython
(venv) $ python setup.py build_ext --inplace
```

The warning message

    WARNING:root:Memory-efficient GCoder implementation unavailable: No module named gcoder_line

means that this optimized G-Code parser hasn't been compiled. To get rid of it and benefit from the better implementation, please install Cython and run the command above.

### Ubuntu/Debian

The above method is the recommended way to run Printrun 2 from source. However, if you can't find a suitable wxPython4 wheel, or if it fails for other reasons, it could be run without using a python virtual environment. For users of Debian 10 Buster or later and Ubuntu 18.04 Bionic Beaver or later.

Install the dependencies:

```
sudo apt install python3-serial python3-numpy cython3 python3-libxml2 python3-gi python3-dbus python3-psutil python3-cairosvg libpython3-dev python3-appdirs python3-wxgtk4.0
```

```
sudo apt install python3-pip
pip3 install --user pyglet
```

Install git, clone this repository:
```
sudo apt install git
git clone https://github.com/kliment/Printrun.git
cd Printrun
```

### Windows

Download and install [Python 3.6](https://www.python.org/downloads/) and follow the **Python virtual environment** section above except use the following to create and activate the virtual environment and install dependencies:

```cmd
> py -3 -m venv venv
> venv\Scripts\activate
> python -m pip install -r requirements.txt
> python pronterface.py
```


### macOS

Install Python 3, you can use Brew:

```console
$ brew install python3
```

Then continue to install and set up Printrun:

```console
$ git clone https://github.com/kliment/Printrun.git  # clone the repository
$ cd Printrun  # change to Printrun directory
$ python3 -m venv venv  # create an virtual environment
$ . venv/bin/activate  # activate the virtual environment (notice the space after the dot)
(venv) $ python -m pip install -r requirements.txt  # install the rest of dependencies
# follow instructions for cython gcoder here if desired
(venv) $ python pronterface.py  # run Pronterface
```


# USING PRINTRUN

## USING PRONTERFACE

When you're done setting up Printrun, you can start pronterface.py in the directory you unpacked it.
Select the port name you are using from the first drop-down, select your baud rate, and hit connect.
Load an STL (see the note on skeinforge below) or GCODE file, and you can upload it to SD or print it directly.
The "monitor printer" function, when enabled, checks the printer state (temperatures, SD print progress) every 3 seconds.
The command box recognizes all pronsole commands, but has no tabcompletion.

If you want to load stl files, you need to install a slicing program such as Slic3r or Skeinforge and add its path to the settings.

#### Slic3r integration

To invoke Slic3r directly from Pronterface your slicing command (_Settings_ > _Options_ > _External Commands_ > _Slice Command_) should look something like `slic3r $s -o $o`. If Slic3r is properly installed "slic3r" will suffice, otherwise, replace it with the full path to Slic3r's executable.

If the Slic3r integration option (_Settings_ > _Options_ > _User interface_ > _Enable Slic3r integration_) is checked a new menu will appear after application restart which will allow you to choose among your previously saved Slic3r Print/Filament/Printer settings.

## USING PRONSOLE

To use pronsole, you need:

  * Python 3 (ideally 3.6),
  * pyserial (or python3-serial on ubuntu/debian) and
  * pyreadline (not needed on Linux)

Start pronsole and you will be greeted with a command prompt. Type help to view the available commands.
All commands have internal help, which you can access by typing "help commandname", for example "help connect"

If you want to load stl files, you need to put a version of skeinforge (doesn't matter which one) in a folder called "skeinforge".
The "skeinforge" folder must be in the same folder as pronsole.py

## USING PRINTCORE

To use printcore you need Python 3 (ideally 3.6) and pyserial (or python3-serial on ubuntu/debian)
See pronsole for an example of a full-featured host, the bottom of printcore.py for a simple command-line
sender, or the following code example:

```python
#to send a file of gcode to the printer
from printrun.printcore import printcore
from printrun import gcoder
import time
p=printcore('/dev/ttyUSB0', 115200) # or p.printcore('COM3',115200) on Windows
gcode=[i.strip() for i in open('filename.gcode')] # or pass in your own array of gcode lines instead of reading from a file
gcode = gcoder.LightGCode(gcode)

# startprint silently exits if not connected yet
while not p.online:
  time.sleep(0.1)

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
import xmlrpc.client

rpc = xmlrpc.client.ServerProxy('http://localhost:7978')
print(rpc.status())
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
..> G90
..>
```

Invoke the macro to move the printhead down by 5 millimeters:

```python
PC> move_down_by 5
```

For more powerful macro programming, it is possible to use python code escaping using ! symbol in front of macro commands.
Note that this python code invocation also works in interactive prompt:

```python
PC> !print("Hello, printer!")
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
..> !print("Diagnostic information ON")
..> macro toggle_debug toggle_debug_off
..>
Macro 'toggle_debug_on' defined
PC> macro toggle_debug_off
Enter macro using indented lines, end with empty line
..> !self.p.loud = 0
..> !print("Diagnostic information OFF")
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
  !print("Diagnostic information OFF")
!else:
  !self.p.loud = 1
  !print("Diagnostic information ON")
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
Copyright (C) 2011-2022 Kliment Yanev, Guillaume Seguin, and the other contributors listed in CONTRIBUTORS.md

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
