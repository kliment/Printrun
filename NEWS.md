Printrun - 2.0.0rc8
====================

Pre-release for test purposes

### New Features

 - Improved layer detection algorithm (#1111)
 - Support for D-codes (#1119)
 - Improvements to macos build (#1117)
 - Improvements to windows build (#1146)
 - Improved German translation (#1144)
 - Improved arc rendering (#1131)

### Fixed Bugs

 - Mouse wheel events duplicated (#1110)
 - Correctly resume files with relative extrusion (#1114)
 - Projector used deprecated/obsolete API (#1140)
 - Send/clear race condition causing stuck prints (#1124)
 - Fix mouse interaction with dpi scaling (#1156)
 - Fix internationalization (95e6830)
 - Fix projector tooltips and layout (8d0510d)
 - Fix incorrect layer count (#1155)

### Administrative matters

 - Correctly attribute ownership of gcoder to printrun project (#1048)
 - Add github actions to build mac app and windows exe (#1106, #1108)


Printrun - 2.0.0rc7
====================

Pre-release for testing purposes.

### New Features

 - Live resizing of panels and many other UI improvements (#1073)
 - Render G2/G3 arcs in 3D view by interpolating them as line segments (#1092 and #1097)
 - Apply grid size settings to 3d view (#1093)
 - Visualize moves with laser/spindle active as extrusion (#1094)
 - Keyboard shortcuts for important UI elements (00a932e)
 - Keyboard jogging improvements (#1100)

### Fixed Bugs

 - Do not expand setting spinners, combo boxes and dropdown lists (5d42c19)
 - Build wheels for Windows and manylinux1/2014 correctly (#1087)
 - Allow spaces between coordinate and value when parsing coordinates in gcode (#1090)
 - Fix G2/G3 arc rendering error and scaling in 2D view (#1091)
 - Correct index of appended command in gcoder (#1057)
 - Fix incorrect string comparisons using "is" (#1096)
 - Fix D-pad/keyboard jog movements (#1084)
 - Fix incorrect enabled state of controls on UI settings change (f02f4ef)
 - Fix command history traversal (9d5620f)
 - Fix toolbar shortcuts, blank jog, jog tab-out on Windows (1f0290b)
 - Fix lost messages from Marlin that contain the string "Count" (#1104)
 - Fix wheel install paths for locales and images (#1101)

Printrun - 2.0.0rc6
====================

Pre-release for testing purposes.

### New Features

 - Change the default background color to the theme one (#931)
 - Add setting for graph background color (#791)
 - Hide second extruder from graph if not present (#791)
 - Support for disabling Mate screensaver service (#979)
 - Armenian translation (#1042)
 - Don't print the M117 status msg to the console (#1081)
 - Packages installable by pip are available on PyPI (#921)

### Fixed Bugs

 - Don't ask for exit confirmation on the console when asking in GUI (b48fe7b)
 - Preset for temperatures does not affect Selection on the main screen (#676)
 - Several Python 3 related followups, mostly in run_gcode_script
 - Issue connecting to a remote port (#1027)
 - Run "Final command" from settings when print is finished (#1014)
 - Fix a crash in wx at startup due to locale settings (#1015)
 - Only apply PARITY_ODD workaround where it's actually needed (#1017)
 - Do not attempt to read extra device name patterns on windows (#1040)
 - Several Linux packaging fixes
 - Removed error-causing wxPython horizontal alignment flags (#1052)
 - Rewrite deprecated Serial functions (#1017), pySerial >= 3 is now needed
 - 3D Viewer color options don't update (#1054)
 - Settings change callbacks not called (#1063 and others)


Printrun - 2.0.0rc5
====================

Pre-release for testing purposes.

### New Features

 - Slic3r integration works with Slic3r PE (959e03e)
 - Disable extrude and retract while printing (284f793, c772209)
 - Add disable autoscroll option (4df9d58)

### Fixed Bugs

 - sys.frozen problem with installed Printrun (#920)
 - Button dragging (#690)
 - Repetier M20 (#848)
 - Crash on startup with tabbed mode enabled (979df4a)
 - Absurd 3D viewer viewport rotation control (#622)
 - STL parser and GCODE plater export Python 3 problems (f8aeafd, 2ea0835)


Printrun - 2.0.0rc4
====================

Pre-release for testing purposes.

### New Features

 - Support for the T? command (#888)
 - Have slic3r as default slicing option (#904)

### Fixed Bugs

 - Segmentation fault (#909)
 - Button text incorrectly changing (#903)
 - Dialogs resized (#905, #915)
 - Macro duplicates (#907)
 - Ok messages with Repetire firmware (#917)
 - Messages printed twice in terminal (#916)
 - Prevent race condition on exit (42d7cd0, 16ee30b)
 - Object has no attribute 'slic3r_configs' (#865)


Printrun - 2.0.0rc3
====================

Pre-release for testing purposes.

### Fixed Bugs

 - Couple of wxPython 4 incompatibilities (116fdda, eb6bd43)
 - Couple of GTK3 visibility problems (#899, f265256, 9193014)
 - Added spoolmanager to installed modules (#896)
 - Setlocale issues on Windows (bf53af9)
 - Installation on macOS and Windows (#901)
 - Macro-related functionality (95877a4)
 - Clicking +Z⇑ and -Z⇓ (#910)
 - Python 3 incompatibilities (#912)
 - Segmentation fault (#895)


Printrun - 2.0.0rc2
====================

Pre-release for testing purposes.

### Fixed Bugs

 - Fix SyntaxError at startup (497179c)


Printrun - 2.0.0rc1
====================

Pre-release for testing purpouses.

### New Features

 - Support the XDG Directory Specification (#866)
    * New dependency: appdirs
 - Port to wxPython 4 (#886)
 - Port to Python 3 (#887)
 - Disable tabbed mode (8590f33)
 
### Fixed Bugs

 - Pronsole depending on the wx module (#867)
 - Error at loading non-existent configuration files (#890)


Printrun - 1.6.0
================

New Features
------------

- Fan power graph (ace6637)
- Improved help messages for main scripts (#727)
- Flow rate slider (#693)
- AR translation from @aboobed (#680)
- Report length of filament used by multiple extruders (de635f1)
- Support for custom baudrates on Linux (#712)
- Filter gcode or model files only (#753)
- Progress update on printer screen (#794)
- Additional RPC functions (#759)
- Spool manager (#827)
- OOP based event handler (#831)

Fixed Bugs
----------

- Unwanted exit while printing (#595)
- Failing at setting power settings on OSX (#619)
- Silent cython failure (#641, #642)
- Jitter on remote connections (#698)
- Error at displaying the percentage done through RPC (#707)
- Error at calculating total filament used (#731)
- Connect function crashing (#732)
- Unintended gcode files being loaded by default (#753)
- Missing dependency on Ubuntu/Debian (#763)
- Run on X11 instead of Wayland (#785 and #789)
- Missing Slic3r integration notes (#779)
- Too generic MIME types listed (#796)
- Pronsole spamming "wait" and "OK o" messages (#813)
- Plugins not being installed by setup.py (#834)
- Compatibility with Slic3r (alexrj/Slic3r#3813)


printrun-20140406
=================

New features
------------

- New 3D visualization
- New GCode plater
- Updated "standard" controls
- New "mini" controls mode
- New print speed control slider in Pronterface
- New plater features:
  * STL cutter
  * STL rebase
- G-Code injection at beginning of layer and edition of entire G-Code
- The G-Code modified using the injector or layer editor can be saved
- Controls and log pane can be folded to leave more space for visualization
- Added a lighter GCode parser for non-graphical interfaces
- Window size and configuration is now saved across runs
- Power management: Printrun now runs on high priority during prints and should
  inhibit sleep modes
- New host commands, `run_script` and `run_gcode_script` to run custom scripts
  during prints. The output of the script ran by `run_gcode_script` will in
  turn be processed as G-Code or host commands
- 3D viewer colors are now configurable

Bugs fixed
----------

- Many fixes around custom buttons
- Much more :)

[Printrun - UNRELEASED]: https://github.com/kliment/Printrun/compare/printrun-20150310...HEAD
