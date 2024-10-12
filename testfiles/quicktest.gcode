; Print this little gcode file for a quick test for repeated prints
; Area needed from homing position: x78 y70 z10 mm
; It takes only a half minute and prints above the print bed (z=7 mm)
; w/o heating and extrusion

G28 ; home
G0 Z10.0000 S0 ; lift z
G90 ; absolute mode
G21	; set unit to mm

G0 F2000
G0 Z 7.0000
G0 X 38.0000 Y 70.0000
G4 P0
G1 Z5.0000 S0
G4 P0
G1 F1000.0000
G1 X 78.0000 Y 70.0000
G1 X 78.0000 Y 20.0000
G1 X 75.0000 Y 20.0000
G1 X 75.0000 Y 23.0000
G1 X 73.0000 Y 23.0000
G1 X 73.0000 Y 20.0000
G1 X 43.0000 Y 20.0000
G1 X 43.0000 Y 23.0000
G1 X 41.0000 Y 23.0000
G1 X 41.0000 Y 20.0000
G1 X 38.0000 Y 20.0000
G1 X 38.0000 Y 70.0000
G4 P0
G0 Z10.0000 S0
G0 Z 7.0000
G0 X 20.0000 Y 60.0000
G1 Z 5.0000
G1 X 28.0000 Y 60.0000
G1 X 28.0000 Y 52.0000
G1 X 20.0000 Y 52.0000
G1 X 20.0000 Y 60.0000

G0 Z10.0000
G0 X5.0000
G0 Y5.0000

M84 ; motors off

