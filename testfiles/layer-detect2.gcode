; Print this file to see the parsed layers
; This file tests problem reported in
; https://github.com/kliment/Printrun/pull/1069#issuecomment-770091308

G28
G0 Z15
G1 E6 ; should not count as x,y not moved

G0 X10 Y10 Z0.2
G1 X20 E7

G0 Z10
M83 ;relative extrusion mode
G1 E-3 ; retract should not create layer

;@!print([l.z for l in self.fgcode.all_layers])
;@!print('test ', 'passed' if len(self.fgcode.all_layers) == 1 else 'failed')
