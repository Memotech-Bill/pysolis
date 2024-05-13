#!/usr/bin/python3
#
# CGI program to return Solis data for a day
#
import os
import sys
import time
import calendar
import struct
import urllib.parse

sLog = '/home/pi/pysolis/log'

def GetParam ():
    if ( len (sys.argv) > 1 ):
        if ( sys.argv[1].lower () == 'today' ):
            t = time.time ()
            t -= t % 86400
            return t
        return calendar.timegm (time.strptime (sys.argv[1], '%Y-%m-%d-%H-%M'))
    return int (urllib.parse.parse_qs (os.environ['QUERY_STRING'])['From'][0])

class Source:
    def GetFirst (self, treq):
        try:
            self.f = open (self.sPath, 'rb')
            # print ('Opened ' + self.sPath)
        except OSError:
            return None
        nlen = self.f.seek (0, os.SEEK_END)
        self.nrec = nlen // self.reclen
        # print ('nlen = {:d} = 0x{:X}, reclen = {:d}, nrec = {:d}'.format (nlen, nlen, self.reclen, self.nrec))
        if ( self.nrec == 0 ):
            return None
        r2 = self.nrec - 1
        # print ('reclen = {:d}, r2 = {:d}, seek = {:X}'.format (self.reclen, r2, self.reclen * r2))
        self.f.seek (self.reclen * r2)
        d2 = self.Decode (self.f.read (self.reclen))
        if ( d2[0] < treq ):
            return None
        r1 = 0
        # print ('Seek 0')
        self.f.seek (0)
        d1 = self.Decode (self.f.read (self.reclen))
        if ( d1[0] >= treq ):
            self.irec = r1
            return d1
        while ( r2 - r1 > 1 ):
            r3 = r1 + ((r2 - r1) * (treq - d1[0])) // ( d2[0] - d1[0] )
            if ( r3 == r1 ):
                r3 += 1
            elif ( r3 == r2 ):
                r3 -= 1
            # print ('reclen = {:d}, r3 = {:d}, seek = {:X}'.format (self.reclen, r3, r3 * self.reclen))
            self.f.seek ( r3 * self.reclen )
            d3 = self.Decode (self.f.read (self.reclen))
            if ( d3[0] < treq ):
                r1 = r3
                d1 = d3
            else:
                r2 = r3
                d2 = d3
        self.irec = r2 + 1
        self.f.seek (self.irec * self.reclen)
        return d2

    def GetNext (self):
        while (True):
            if ( self.irec >= self.nrec ):
                return None
            self.irec += 1
            r = self.Decode (self.f.read (self.reclen))
            if ( r is not None ):
                return r

class Source1 (Source):
    def __init__ (self, tm):
        self.reclen = 306
        if ( len (sys.argv) > 2 ):
            self.sPath = sys.argv[2]
        else:
            self.sPath = '{:s}/{:04d}/{:02d}/Solis_{:04d}{:02d}{:02d}.dat'.format (sLog, tm.tm_year, tm.tm_mon, tm.tm_year,
                                                                                   tm.tm_mon, tm.tm_mday)
     
    def Decode (self, rec):
        if ( len (rec) < self.reclen ):
            # sys.stderr.write ('Short Modbus record: {:d}\n'.format (len (rec)))
            return None
        if (( rec[0:2] != b'\xAA\x55' ) or ( rec[self.reclen-2:] != b'\x55\xAA' )):
            sys.stderr.write ('Invalid Modbus record\n')
            return None
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

class Source2 (Source):
    def __init__ (self, tm):
        self.reclen = 264
        if ( len (sys.argv) > 3 ):
            self.sPath = sys.argv[3]
        else:
            self.sPath = '{:s}/{:04d}/{:02d}/Solis_R250_{:04d}{:02d}{:02d}.cap'.format (sLog, tm.tm_year, tm.tm_mon, tm.tm_year,
                                                                                        tm.tm_mon, tm.tm_mday)
     
    def Decode (self, rec):
        if ( len (rec) < self.reclen ):
            # sys.stderr.write ('Short Capture record: {:d}\n'.format (len (rec)))
            return None
        if (( rec[0:2] != b'\xA5\x5A' ) or ( rec[self.reclen-2:] != b'\x5A\xA5' )):
            sys.stderr.write ('Invalid Capture record: {:02X} {:02X} {:02X} {:02X}\n'
                              .format (rec[0], rec[1], rec[self.reclen-2], rec[self.reclen-1]))
            return None
        t = struct.unpack ('<Q', rec[4:12])[0]
        rec = rec[12:262]
        solar = struct.unpack ('<H', rec[108:110])[0]       # Solar Power watts
        grid = struct.unpack ('<H', rec[156:158])[0]        # power from/to grid (import is -ve)
        if ( grid >= 0x8000 ):
            grid -= 0x10000
        batv = struct.unpack ('<H', rec[162:164])[0]        # Inverter Battery Voltage
        bata = struct.unpack ('<H', rec[164:166])[0]        # Inverter Battery Current
        bdir = struct.unpack ('<H', rec[166:168])[0]        # Inverter Battery Current Direction
        if ( bdir > 0 ):
            bata = -bata
        bsoc = struct.unpack ('<H', rec[172:174])[0]        # BMS reported battery SOC
        load = struct.unpack ('<H', rec[188:190])[0]        # Load power watts
        return (t, load, solar, batv * bata // 100, grid, bsoc)

def Main ():
    sys.stdout.write ('Context-type: text/csv\n\n')
    t1 = 0
    t2 = 0
    treq = GetParam ()
    tm = time.gmtime (treq)
    s1 = Source1 (tm)
    s2 = Source2 (tm)
    r1 = s1.GetFirst (treq)
    r2 = s2.GetFirst (treq)
    while (True):
        r = None
        if ( r1 is None ):
            if ( r2 is None ):
                break
            r = r2
            t2 = r2[0]
            r2 = s2.GetNext ()
        elif ( r2 is None ):
            r = r1
            t1 = r1[0]
            r1 = s1.GetNext ()
        elif ( r1[0] < r2[0] ):
            r = r1
            t1 = r1[0]
            r1 = s1.GetNext ()
        else:
            r = r2
            t2 = r2[0]
            r2 = s2.GetNext ()
        sys.stdout.write ('{:d},{:d},{:d},{:d},{:d},{:d}\n'.format (r[0], r[1], r[2], r[3], r[4], r[5]))
    sys.stdout.write ('{:d},{:d}\n'.format (t1, t2))

Main ()

