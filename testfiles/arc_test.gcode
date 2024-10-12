; Print this file for a quick test of support for arc movements with 
; G2 and G3 and z helix movement up and down +- 10 mm, 6 times a full cycle
; It takes only a half minute and prints above the print bed (z=20 mm)
; w/o heating and extrusion

G28 ; home
G0 Z10.0000 S0 ; lift z
G90 ; absolute mode
G21	; set unit to mm

G2 X15 Y20 I30 J40 Z20 F8000
G3 X15 Y20 I30 J40 Z10 F8000
G2 X15 Y20 I30 J40 Z20 F8000
G3 X15 Y20 I30 J40 Z10 F8000
G2 X15 Y20 I30 J40 Z20 F8000
G3 X15 Y20 I30 J40 Z10 F8000

G0 X5.0000
G0 Y5.0000

M84; motors off