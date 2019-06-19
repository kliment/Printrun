#!/usr/bin/python3
#generate many g1 to test serial buffer overflow in run_gcode_script

print('G28 X')
print('G1 X0')
for x in range(100):
    print()
    print('  ')
    print('G1 X', x)
