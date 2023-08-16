# PRINTRUN
![License](https://img.shields.io/github/license/kliment/Printrun)
![GitHub - Downloads](https://img.shields.io/github/downloads/kliment/Printrun/total?logo=github)
![GitHub contributors](https://img.shields.io/github/contributors/kliment/Printrun?logo=github)
![PyPI - Version](https://img.shields.io/pypi/v/Printrun?logo=pypi&label=PyPI)
![PyPI - Downloads](https://img.shields.io/pypi/dm/Printrun?logo=pypi)

Printrun consists of a suite of hosts for 3D printers and other CNC machines
(printcore, pronsole and pronterface) and a small collection of helpful
scripts.

 * **printcore.py** is a library that makes writing [RepRap][1] hosts easy
 * **pronsole.py** is an interactive command-line host with tab-completion
   goodness
 * **pronterface.py** is a graphical host with the same functionality as
   pronsole

The contents of this document are organized in the following sections:

 - [Getting Printrun](#getting-printrun)
   * [Distributed Binaries and Packages](#distributed-binaries-and-packages)
     + [Windows and macOS pre-compiled binaries](#windows-and-macos-pre-compiled-binaries)
     + [Linux packages from official repositories](#linux-packages-from-official-repositories)
     + [Printrun package from PyPI](#printrun-package-from-pypi)
   * [Running From Source](#running-from-source)
 - [Using Printrun](#using-printrun)
   * [Using Pronterface](#using-pronterface)
   * [Using Pronsole](#using-pronsole)
   * [Using Printcore](#using-printcore)
   * [Platers](#platers)
   * [3D Viewer Controls](#3d-viewer-controls)
   * [RPC Server](#rpc-server)
   * [Configuration](#configuration)
   * [Using Macros And Custom Buttons](#using-macros-and-custom-buttons)
   * [Using Host Commands](#using-host-commands)
 - [Testing](#testing)
 - [Contributing](#contributing)
 - [Contributors](#contributors)
 - [License](#license)


[1]: https://en.wikipedia.org/wiki/RepRap


# GETTING PRINTRUN

Installation of Printrun can be done in several ways, either installing a
pre-compiled binary, via distribution-specific packages from official
repositories or from PyPI. If you want the newest, shiniest features, you can
[run Printrun from source](#running-from-source).

## Distributed Binaries and Packages

### Windows and macOS pre-compiled binaries

Everything bundled into one single package for easy installation. Downloads
available at: https://github.com/kliment/Printrun/releases/latest

> **Note for OSX users**: if OSX tells you `"pronterface.app" cannot be opened
> because the developer cannot be verified.`, you don't need to re-download
> it. Instead, you need to allow OSX to run the unsigned app. To do this,
> right click the application in Finder and select `Open`. Then click `Open`
> in the popup window that appears. You only need to do this once.


### Linux packages from official repositories

#### Ubuntu / Mint / Raspberry Pi OS / Debian

Install the full suite: `sudo apt install printrun`

Or only the apps you need: `sudo apt install pronsole` or `pronterface` or
`plater`


#### Chrome OS

You can use Printrun via crouton ( https://github.com/dnschneid/crouton ). Assuming you want Ubuntu Trusty, you used probably `sudo sh -e ~/Downloads/crouton -r trusty -t xfce` to install Ubuntu. Fetch and install printrun with the line given above for Ubuntu/Debian.

By default you have no access to the serial port under Chrome OS crouton, so you cannot connect to your 3D printer. Add yourself to the serial group within the linux environment to fix this

`sudo usermod -G serial -a <username>`

where `<username>` should be your username. Log out and in to make this group change active and allow communication with your printer.


#### Fedora

Install the full suite: `sudo dnf install printrun`

Or only the apps you need: `sudo dnf install pronsole` or `pronterface` or
`plater`

> Adding `--enablerepo updates-testing` option to `dnf` might sometimes give
> you newer packages (but also not very tested).


#### Arch Linux

Packages are available in AUR. Just run

`yaourt printrun`


### Printrun package from PyPI

If you have a working Python environment, regardless of your OS, you can
install the latest release distributed through the PyPI repository using
[pip][2] and, optionally (but highly recommended), a [virtual environment][3].

Activate your virtual environment, and run (Linux / macOS):

`python -m pip install Printrun`

or (Windows):

`py -m pip install Printrun`


[2]: https://pip.pypa.io/
[3]: https://docs.python.org/3/tutorial/venv

## Running From Source

By running Printrun from source you get access to the latest features and
in-development changes. Warning note: these might not be fully working or
stable.

### Linux / macOS

#### 1. Install Python

Almost all Linux distributions come with Python already pre-installed. If not,
install Python normally from your package manager. On macOS download and
install the latest Python from [python.org][4].

[4]: https://www.python.org/downloads/macos/


#### 2. Download the latest Printrun source code

Obtain the latest source code by running the following in a terminal window:

```shell
$ git clone https://github.com/kliment/Printrun.git  # clone the repository
$ cd Printrun  # change to Printrun directory
```


#### 3. Use a Python virtual environment

Easiest way to run Printrun from source is to create and use a Python [virtual
environment][3]. This step is optional but highly recommended to avoid
conflicts with other Python libraries already installed (or that will be
installed in the future) in your system. Within the Printrun's root directory,
create and activate a virtual environment by running:

```shell
$ python -m venv venv       # create a virtual environment
$ source venv/bin/activate  # activate the virtual environment
```

> **Note for Ubuntu/Debian**: You might need to install `python3-venv` first.

> **Note for Ubuntu/Debian**: If you get `python: command not found` use
> `python3` instead of just `python` on all commands below.


#### 4. Install dependencies

Dependencies for running Printrun are laid out in the [`requirements.txt`][5]
file. Once activated your virtual environment, install required dependencies
with:

```
(venv) $ python -m pip install -r requirements.txt  # install the rest of dependencies
```

> **Note for Linux users**: wxPython4 doesn't have Linux wheels available from
> the Python Package Index yet. Before running the command above, find a
> proper wheel for your distro at [extras.wxpython.org][6] and substitute the
> link in the below example. You might skip this wheel installation, but that
> results in compiling wxPython4 from source, which can be time and resource
> consuming and might fail.
> ```shell
> (venv) $ python -m pip install https://extras.wxpython.org/wxPython4/extras/linux/gtk3/fedora-27/wxPython-4.0.1-cp36-cp36m-linux_x86_64.whl  # replace the link with yours
> ```

[5]: requirements.txt
[6]: https://extras.wxpython.org/wxPython4/extras/linux/gtk3


#### 5. (Optional) Cython-based G-Code parser

Printrun default G-Code parser is quite memory hungry, but we also provide a
much lighter one which just needs an extra build-time dependency (Cython). The
warning message `WARNING:root:Memory-efficient GCoder implementation
unavailable: No module named gcoder_line` means that this optimized G-Code
parser hasn't been compiled. To get rid of it and benefit from the better
implementation, install Cython and build the extension with the following
commands:

```console
(venv) $ python -m pip install Cython
(venv) $ python setup.py build_ext --inplace
```


#### 6. Run Printrun

With your virtual environment still active, invoke the app you need like:

```shell
(venv) $ python pronterface.py  # or `pronsole.py` or `plater.py`
```


### Windows

First download and install [GIT for Windows](https://git-scm.com/downloads), [Python 3.10](https://www.python.org/downloads/) and a [C-compiler environment](https://wiki.python.org/moin/WindowsCompilers/).
For the next steps we need a CMD window or a PowerShell window. You can use Windows Terminal for this as well.
Create and navigate to a directory of your choice where you want to download the source files of this repository and follow the next steps:

CMD
```cmd
> git clone https://github.com/kliment/Printrun.git
> cd Printrun
> git submodule update --init --recursive
> release_windows.bat
```

PowerShell:
```ps
> git clone https://github.com/kliment/Printrun.git
> cd Printrun
> git submodule update --init --recursive
> ./release_windows.bat
```

The script above will clone this repository and the submodule PrintrunGTK3. The script 'release_windows.bat' will install a virtual environment named v3, download all needed python libraries and compile the binaries for Pronterface.exe and Pronsole.exe.
You will find the files in the new created directory 'dist'. You will find further and more detailed information in the script release_windows.bat. Further information for the linked submodul: [PrintrunGTK3](https://github.com/DivingDuck/PrintrunGTK3)
Run Pronterface or Pronsole from the binary files or from source calling pronterface.py for the GUI version and pronsole.py for the commandline version.

Run 'release_windows.bat' when ever you make changes or updates. With each new run it will compile the binaries and update all involved libraries in the virtual environment if needed. Delete the virtual environment if you have problems with it. Use 'git submodule update --init --recursive' for updating the submodule


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

  * Python 3 (ideally 3.10),
  * pyserial (or python3-serial on ubuntu/debian) and
  * pyreadline (not needed on Linux)

Start pronsole and you will be greeted with a command prompt. Type help to view the available commands.
All commands have internal help, which you can access by typing "help commandname", for example "help connect"

If you want to load stl files, you need to put a version of skeinforge (doesn't matter which one) in a folder called "skeinforge".
The "skeinforge" folder must be in the same folder as pronsole.py

## USING PRINTCORE

To use printcore you need Python 3 (ideally 3.10) and pyserial (or python3-serial on ubuntu/debian)
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


# TESTING

A small (work in progress) test suite is developed within folder `tests` using
[unittest][8] which can be run with (requires Python 3.11+):

```
python -m unittest discover tests
```

Small utilities for testing/debugging communications or g-code reading/writing
are also provided within folder `testtools`.


[8]: https://docs.python.org/3/library/unittest


# CONTRIBUTING

Thinking of contributing to Printrun? Awesome! Thank you! ❤️

Printrun is an open source project and we love to receive contributions from
anyone. There are many ways to contribute:

 * Improving the documentation. This README is our main source of
   documentation and it surely lacks some love here and there or requires
   being brought up to date.

 * Submitting bug reports and feature requests.
   - We use GitHub's [issue tracker][9] to keep track of them.
   - Please remember to state your OS and Printrun version on new issues.

 * Improving the test code base. Current code coverage is extremely low. See
   [testing section](#testing) for more information.

 * Fixing existing issues and/or implementing requested features. There is a
   fair amount of known issues and a great deal of requested features waiting
   to be implemented. We (the maintainers) don't have the time and resources
   to look at them all so every code contribution will be very welcome.
   - We use GitHub's [pull requests][10] to review and incorporate new code.
   - Issues labeled [`Regression`][11] would be the most urgent fixes needed,
     followed by issues/requests labeled [`2.x`][12] and lastly those with
     [`3.x`][13].
   - Ideally every new contribution should comply with [PEP 8][14] style guide
     as much as possible and should be thoroughly documented to ease reviewing
     and future understanding of the code.
   - Please note that breaking changes might need to wait to be incorporated
     until the next major release is due.


[9]: https://github.com/kliment/Printrun/issues
[10]: https://github.com/kliment/Printrun/pulls
[14]: https://peps.python.org/pep-0008
[11]: https://github.com/kliment/Printrun/labels/Regression
[12]: https://github.com/kliment/Printrun/labels/2.x
[13]: https://github.com/kliment/Printrun/labels/3.x


# CONTRIBUTORS

An enormous number of people helped make Printrun. See the list
[here](CONTRIBUTORS.md).


# LICENSE

```
Copyright (C) 2011-2023 Kliment Yanev, Guillaume Seguin, and the other contributors listed in CONTRIBUTORS.md

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
