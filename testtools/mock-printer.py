#!/usr/bin/env python3
# Test network communication without networked 3d printer
# Usage:
# bash1$ ./testtools/mock-printer.py
# bash2$ ./pronterface.py
# Enter localhost:8080 in Port, press Connect, Load file, Print
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
                # c.sendall(('ok T:%d\n'%(20 + temp)).encode('ascii'))
                # test multiple extruders, see #1234
                c.sendall('ok T0:24.06 /34.00 B:23.45 /0.00 T1:44.28 /54 @:0 B@:0 @0:0 @1:0\n'.encode('ascii'))
                temp = (temp + 1)%30
            else:
                c.sendall(b'ok\n')
    finally:
        c.close()
