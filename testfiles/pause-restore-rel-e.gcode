; test restoring of relative extrusion mode
; after pause https://github.com/kliment/Printrun/issues/1083
G28
G90 ; abs all, including E
M83 ; relative E
;@!print('Please press Resume and check for M 83')
;@!self.p.loud = True
;@pause
;@!self.p.loud = False
;@!threading.Timer(2, lambda logbox: print('PASSED. Seen M 83' if 'M' + '83' in logbox.Value else 'FAILED: M 83 not seen'), (self.logbox,)).start()
