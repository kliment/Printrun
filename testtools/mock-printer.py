#!/usr/bin/env python3
# Test network communication without networked 3d printer
# Usage:
# bash1$ ./mock-printer.py
# bash2$ ./pronsole
# pronsole> connect localhost:8080
# ...> load sliced.gcode
# ...> print
# ...> etc...
import socket
with socket.socket() as s:
    s.bind(('127.0.0.1', 8080))
    s.listen(1)
    c, addr = s.accept()
    print(c)
    temp = 0
    try:
        c.sendall(b'start\n')
        while True:
            msg = c.recv(1024)
            if not msg:
                break
            print(msg)
            if msg == b'M105\n':
                c.sendall(('ok T:%d\n'%(20 + temp)).encode('ascii'))
                temp = (temp + 1)%30
            else:
                c.sendall(b'ok\n')
    finally:
        c.close()
