#!/home/pi/pysolis/bin/python3
"""Query Solis Data Logger to collect Statistics"""

import umodbus.client.tcp
import socket
import struct
import time
import os
import sys

def query (addr, logdir):
    sid = 1
    registers = ((33022, 33041), (33049, 33059), (33071, 33085), (33091, 33096),
                 (33100, 33107), (33126, 33151), (33161, 33181), (33251, 33287),
                 (33115, 33122))
    nTry = 0
    while ( nTry < 2 ):
        nTry += 1
        try:
            fst = 0
            lst = 0
            rec = b'\xAA\x55'
            rec += struct.pack ('<Q', int (time.time ()))
            sock = socket.create_connection ((addr, 30003), timeout = 20)
            for fst, lst in registers:
                req = umodbus.client.tcp.read_input_registers (sid, fst, lst - fst)
                bFail = True
                for attempt in range (3):
                    try:
                        val = umodbus.client.tcp.send_message (req, sock)
                        bFail = False
                        break
                    except TimeoutError:
                        pass
                if ( bFail ):
                    sock.close ()
                    sys.stderr.write ('Failed to read registers ({:d}, {:d})\n'.format (fst, lst))
                    sys.exit (1)
                for v in val:
                    rec += struct.pack ('<H', v)
            sock.close ()
            break
        except ConnectionResetError:
            if ( fst == 0 ):
                sys.stderr.write ('{:s} Try {:d} - Connection reset on open\n'
                                  .format (time.strftime ('%Y-%m-%d %H:%M:%S'), nTry))
            else:
                sys.stderr.write ('{:s} Try {:d} - Connection reset reading registers ({:d{, {:d})\n'
                                  .format (time.strftime ('%Y-%m-%d %H:%M:%S'), nTry, fst, lst))
            time.sleep (120)
    rec += struct.pack ('<Q', int (time.time ()))
    rec += b'\x55\xAA'
    tm = time.gmtime (time.time ())
    dir = '{:s}/{:04d}/{:02d}'.format (logdir, tm.tm_year, tm.tm_mon)
    os.makedirs (dir, exist_ok=True)
    fname = 'Solis_{:04d}{:02d}{:02d}.dat'.format (tm.tm_year, tm.tm_mon, tm.tm_mday)
    with open (os.path.join (dir, fname), 'ab') as f:
        f.write (rec)
        
if __name__ == "__main__":
    query (sys.argv[1], sys.argv[2])
