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
