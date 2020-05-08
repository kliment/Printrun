Printrun - 2.0.0
================

### New Features

 - Armenian translation by @Avag-Sayan (#1042)

### Fixed Bugs

 - Settings reset with Ctrl+DoubleClick (c6a4d3d)
 - Apply settings without restart (2ea52b2)
 - Colors on 3D viewer not working (#1054)
 - Decode messages from printer as UTF-8 (#1058)
 - Update to pySerial 3.0 (#1055)
 - Compatibility with wxPython 4.1.0 (#1051)
 - Metadata updated to AppStream's spec 0.12 (#1049)
 - Building on Windows (#1040)
 - Timeout on socket connections (#1027)
 - Port not allowed to be set before connecting (#1019)
 - Serial parity nor working correctly on FreeBSD (#1017)
 - Mismatch between C/C++ and Windows locale (#1015)
 - Completion and buffer overflow on `run_gcode_script` (#1009)
 - Mate screensaver disabling not supported (#979)
 - Crashing of `run_script` and `run_gcode_script` (#978)
 - Dependency gathering explanation (#962)
 - Image path on setup file (#942)
 - CoreFoundation encoding errors (#937)
 - Final command not executing (#933)
 - Use theme background colour (#932)
 - Hide stats for second extruder when not used (#791)
 - Preset temperatures not read from config file (#676)
 - Hardcoded icon paths in launchers (71e4476)


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
