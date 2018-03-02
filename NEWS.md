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
