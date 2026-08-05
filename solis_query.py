#!/home/pi/pysolis/bin/python3
"""Query Solis Data Logger to collect Statistics"""

import umodbus.client.tcp
import socket
import struct
import time
import os
import sys

def query (addr, logdir):
    tm = time.gmtime (time.time ())
    dir = '{:s}/{:04d}/{:02d}'.format (logdir, tm.tm_year, tm.tm_mon)
    os.makedirs (dir, exist_ok=True)
    with open (os.path.join (dir, 'query.log'), 'a') as log:
        sid = 1
        registers = ((33022, 33041), (33049, 33059), (33071, 33085), (33091, 33096),
                     (33100, 33107), (33126, 33151), (33161, 33181), (33251, 33287),
                     (33115, 33122))
        nTry = 0
        while ( nTry < 2 ):
            nTry += 1
            # log.write ("Try {:d}\n".format (nTry))
            try:
                fst = 0
                lst = 0
                rec = b'\xAA\x55'
                rec += struct.pack ('<Q', int (time.time ()))
                sock = socket.create_connection ((addr, 502), timeout = 20)
                for fst, lst in registers:
                    req = umodbus.client.tcp.read_input_registers (sid, fst, lst - fst)
                    bFail = True
                    for attempt in range (3):
                        try:
                            val = umodbus.client.tcp.send_message (req, sock)
                            bFail = False
                            break
                        except TimeoutError:
                            log.write ("Attempt {:d}-{:d}: Timeout\n".format (nTry, attempt + 1))
                        except KeyError as e:
                            log.write ("Attempt {:d}-{:d}: Key error: {:s}\n".format (nTry, attempt + 1, str (e)))
                        except struct.error as e:
                            log.write ("Attempt {:d}-{:d}: Struct error: {:s}\n".format (nTry, attempt + 1, str (e)))
                    if ( bFail ):
                        sock.close ()
                        log.write ('{:s}: Try {:d}: Failed to read registers ({:d}, {:d})\n'
                                          .format (time.strftime ('%Y-%m-%d %H:%M:%S'), nTry, fst, lst))
                        if ( nTry == 2 ):
                            sys.exit (1)
                        break
                    if ( bFail ):
                        break
                    for v in val:
                        rec += struct.pack ('<H', v)
                sock.close ()
                if ( bFail ):
                    if ( nTry == 2 ):
                        sys.exit (1)
                    time.sleep (105)
                else:
                    break
            except ConnectionResetError:
                if ( fst == 0 ):
                    log.write ('{:s} Try {:d} - Connection reset on open\n'
                                      .format (time.strftime ('%Y-%m-%d %H:%M:%S'), nTry))
                else:
                    log.write ('{:s} Try {:d} - Connection reset reading registers ({:d{, {:d})\n'
                                      .format (time.strftime ('%Y-%m-%d %H:%M:%S'), nTry, fst, lst))
                if ( nTry == 2 ):
                    sys.exit (1)
                time.sleep (105)
        rec += struct.pack ('<Q', int (time.time ()))
        rec += b'\x55\xAA'
        if ( len (rec) == 306 ):
            fname = 'Solis_{:04d}{:02d}{:02d}.dat'.format (tm.tm_year, tm.tm_mon, tm.tm_mday)
            with open (os.path.join (dir, fname), 'ab') as f:
                f.write (rec)
                # log.write ("Query complete: {:d}:{:02d}\n".format (tm.tm_hour, tm.tm_min))
        
if __name__ == "__main__":
    query (sys.argv[1], sys.argv[2])
