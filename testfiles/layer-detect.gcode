; Print this file to see the parsed layers
; This file contains lines from https://github.com/kliment/Printrun/pull/1069#issuecomment-692127342
; Interesting points:
; Are layers snapped (merged,disappear) to near ones?
; Are layers z coordinates modified?
; Are layers without extrusion snapped to previous?
; Handling of last layer - is extrusion respected?

G1 Z5 ; lift nozzle

G1 Z0.200 ; move to next layer (0)
G0 Y1
G1 X100 E1
G1 Z0.203 ; move to next layer (1)
G0 X1
G1 X100 E2
G1 Z0.300 ; move to next layer (2)
G0 X1
G1 X100 E3
G1 Z0.398 ; move to next layer (3)
G0 X1
G1 X100 E4
G1 Z0.458 ; move to next layer (4)
G0 X1
G1 X100 E5
G1 Z0.503 ; move to next layer (5)

;@!print([l.z for l in self.fgcode.all_layers])
