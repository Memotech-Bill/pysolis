#!/home/pi/pysolis/bin/python3
#
# CGI program to return Solis data for a day
#
import os
import sys
import time
import calendar
import struct
import urllib.parse

reclen = 306
sLog = '/home/pi/pysolis/log'

def GetPath (treq):
    if ( len (sys.argv) > 1 ):
        return sys.argv[1]
    tm = time.gmtime (treq)
    sPath = '{:s}/{:4d}/{:2d}/Solis_{:4d}{:2d}{:2d}.dat'.format (sLog, tm.tm_year, tm.tm_mon, tm.tm_year,
                                                                 tm.tm_mon, tm.tm_mday)
    return sPath

def GetParam ():
    if ( len (sys.argv) > 2 ):
        if ( sys.argv[2].lower () == 'today' ):
            t = time.time ()
            t -= t % 86400
            return str (t)
        return str (calendar.timegm (time.strptime (sys.argv[2], '%Y-%m-%d-%H-%M')))
    return urllib.parse.parse_qs (os.environ['QUERY_STRING'])['From'][0]

def Decode (rec):
    t = struct.unpack ('<Q', rec[2:10])[0]
    w = struct.unpack ('<HH', rec[64:68])               # Total DC Input Power (W)
    solar = ( w[0] << 16 ) | w[1]
    w = struct.unpack ('<HH', rec[128:132])             # Meter Active Power
    grid = ( w[0] << 16 ) | w[1]
    if ( grid > 0x80000000 ):                           # +ve = Exporting
        grid -= 0x100000000                             # -ve = Inporting
    load = struct.unpack ('<H', rec[162:164])[0]        # House Load Power (W)
    w = struct.unpack ('<HH', rec[166:170])             # Battery Power (W)
    batt = ( w[0] << 16 ) | w[1]                        # +ve = Charging
    if ( struct.unpack ('<H', rec[138:140])[0] > 0 ):   # Battery Current Direction
        batt = -batt                                    # -ve = Discharging
    bsoc = struct.unpack ('<H', rec[146:148])[0]
    return (t, load, solar, batt, grid, bsoc)

def GetData ():
    print ('Context-type: text/csv\n')
    treq = int (GetParam ())
    sPath = GetPath (treq)
    with open (sPath, 'rb') as f:
        nrec = f.seek (0, os.SEEK_END) // reclen
        if ( nrec == 0 ):
            return
        r2 = nrec - 1
        f.seek (reclen * r2)
        d2 = Decode (f.read (reclen))
        if ( d2[0] < treq ):
            return
        r1 = 0
        f.seek (0)
        d1 = Decode (f.read (reclen))
        if ( d1[0] < treq ):
            while ( r2 - r1 > 1 ):
                r3 = r1 + ((r2 - r1) * (treq - d1[0])) // ( d2[0] - d1[0] )
                if ( r3 == r1 ):
                    r3 += 1
                elif ( r3 == r2 ):
                    r3 -= 1
                f.seek ( r3 * reclen )
                d3 = Decode (f.read (reclen))
                if ( d3[0] < treq ):
                    r1 = r3
                    d1 = d3
                else:
                    r2 = r3
                    d2 = d3
        else:
            r2 = r1
            d2 = d1
        print ('{:d},{:d},{:d},{:d},{:d},{:d}'.format (d2[0], d2[1], d2[2], d2[3], d2[4], d2[5]))
        r2 += 1
        f.seek (r2 * reclen)
        while ( r2 < nrec ):
            d2 = Decode (f.read (reclen))
            print ('{:d},{:d},{:d},{:d},{:d},{:d}'.format (d2[0], d2[1], d2[2], d2[3], d2[4], d2[5]))
            r2 += 1

GetData ()
