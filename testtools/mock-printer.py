#!/usr/bin/env python3
# Test network communication without networked 3d printer
# Usage:
# bash1$ ./mock-printer.py
# bash2$ ./pronsole
# pronsole> connect localhost:8080
# ...> load sliced.gcode
# ...> print
# ...> etc...
import socket, re
import time

def send(line):
    c.write((line + "\n").encode('ascii'))
    c.flush()

with socket.socket() as s:
    addr = '127.0.0.1', 8080
    s.bind(addr)
    s.listen(1)
    print('Listening. You can connect from pronterface to %s:%d' % addr)
    cs, addr = s.accept()
    print(cs)
    #text mode causes loss of incoming lines in Ubuntu 20.04.2 LTS, python 3.8.5
    c = cs.makefile('rwb') # , encoding='utf8', newline="\n"
    print(c)
    temp = 0
    pos = {'X': 0, 'Y': 0, 'Z': 0, 'F': 0}
    try:
        #c.sendall(b'start\n')
        send('start')
        while True:
        # for msg in c:
            #msg = c.recv(1024).decode('ascii').strip()
            time.sleep(1/20.)
            msg = c.readline().decode('utf8').strip()
            print('(', msg, ')')
            if not msg:
                break
            if msg == 'M105':
                send('ok T:%d'%(20 + temp))
                temp = (temp + 1)%30
            elif msg == 'M114':
                send(f'ok C: X:{pos["X"]} Y:{pos["Y"]} Z:{pos["Z"]} E:1')
            else:
                m = re.match('^G0 ([XYZF])([-0-9.]+)', msg)
                if m:
                    pos[m.group(1)] += float(m.group(2))
                    print(pos)

                send('ok')
    finally:
        c.close()
        cs.close()
        s.close()
