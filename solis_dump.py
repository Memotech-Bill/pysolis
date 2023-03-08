#!/usr/bin/python3
#
# Decode Solis binary log file to CSV file
#
import sys
import struct
import time
import calendar

all_regs = (
    ('H16', 1, b'\xAA\x55'),                                            #   0
    ('T64', -1, 'Data time'),                                            #   2
    ('D96', -1, 'System Time'),                                          #  10
    ('X16', 1, 'Not Used'),                                             #  22
    ('U32', 1, 'Total Generation (kWh)'),                               #  24
    ('U32', 1, 'Generated This Month (kWh)'),                           #  28
    ('U32', 1, 'Generated Last Month (kWh)'),                           #  32
    ('U16', 10, 'Generated Today (kWh)'),                               #  36
    ('U16', 10, 'Generated Yesterday (kWh)'),                           #  38
    ('U32', 1, 'Generated This Year (kWh)'),                            #  40
    ('U32', 1, 'Generated Last Year (kWh)'),                            #  44
    ('U16', 10, 'DC Voltage 1 (V)'),                                    #  48
    ('U16', 10, 'DC Current 1 (A)'),                                    #  50
    ('U16', 10, 'DC Voltage 2 (V)'),                                    #  52
    ('U16', 10, 'DC Current 2 (A)'),                                    #  54
    ('U16', 10, 'DC Voltage 3 (V)'),                                    #  56
    ('U16', 10, 'DC Current 3 (A)'),                                    #  58
    ('U16', 10, 'DC Voltage 4 (V)'),                                    #  60
    ('U16', 10, 'DC Current 4 (A)'),                                    #  62
    ('U32', 1, 'Total DC Input Power (W)'),                             #  64
    ('U16', 10, 'DC bus Voltage (V)'),                                  #  68
    ('U16', 10, 'DC bus half Voltage (V)'),                             #  70
    ('U16', 10, 'Phase A Voltage (V)'),                                 #  72
    ('U16', 10, 'Phase B Voltage (V)'),                                 #  74
    ('U16', 10, 'Phase C Voltage (V)'),                                 #  76
    ('U16', 10, 'Phase A Current (A)'),                                 #  78
    ('U16', 10, 'Phase B Current (A)'),                                 #  80
    ('U16', 10, 'Phase C Current (A)'),                                 #  82
    ('S32', 1, 'Active Power (W)'),                                     #  84
    ('S32', 1, 'Reactive power (W)'),                                   #  88
    ('S32', 1, 'Apparent Power (VA)'),                                  #  92
    ('U16', 1, 'Standard Working Mode'),                                #  96
    ('U16', 1, 'National Standard'),                                    #  98
    ('U16', 10, 'Inverter Temperature (C)'),                            # 100
    ('U16', 100, 'Grid Frequency (Hz'),                                 # 102
    ('U16', 1, 'Current State Of Inverter'),                            # 104
    ('S32', 1, 'Limit Active Power Output (W)'),                        # 106
    ('S32', 1, 'Limit Reactive Power Output (W)'),                      # 110
    ('U16', 100, 'Actual Power Limited Power (%)'),                     # 114
    ('S16', 1000, 'Actual Adjustment ()'),                              # 116
    ('S16', 1, 'Limit Reactive Power (%)'),                             # 118
    ('U32', 1, 'Electricity Meter Total Energy (Wh)'),                  # 120
    ('U16', 10, 'Meter Voltage (V)'),                                   # 124
    ('U16', 10, 'Meter Current (A)'),                                   # 126
    ('S32', 1, 'Meter Active Power (W)'),                               # 128
    ('U16', 1, 'Energy Storage Mode'),                                  # 132
    ('U16', 10, 'Battery Voltage (V)'),                                 # 134
    ('R16+16', 10, 'Battery Current (A)'),                              # 136
    ('U16', 1, 'Battery Current_Direction (0=Charging, 1=Discharging'), # 138
    ('U16', 10, 'LLCbus Voltage (V)'),                                  # 140
    ('U16', 10, 'Bypass AC Voltage (V)'),                               # 142
    ('U16', 10, 'Bypass AC Current (A)'),                               # 144
    ('U16', 1, 'Battery Capacity SOC (%)'),                             # 146
    ('U16', 1, 'Battery Health SOH (%)'),                               # 148
    ('U16', 100, 'Battery Voltage BMS (V)'),                            # 150
    ('S16', 100, 'Battery Current BMS (A)'),                            # 152
    ('U16', 10, 'Battery Charge Current Limit (A)'),                    # 154
    ('U16', 10, 'Battery Discharge Current Limit (A)'),                 # 156
    ('U16', 1, 'Battery Failure Information 01'),                       # 158
    ('U16', 1, 'Battery Failure Information 02'),                       # 160
    ('U16', 1, 'House Load Power (W)'),                                 # 162
    ('U16', 1, 'Bypass Load Power (W)'),                                # 164
    ('R32-224', 1, 'Battery Power (W)'),                                # 166
    ('U32', 1, 'Total Battery Charge (kWh)'),                           # 170
    ('U16', 10, 'Today Battery Charge (kWh)'),                          # 174
    ('U16', 10, 'Yesterday Battery Charge (kWh)'),                      # 176
    ('U32', 1, 'Total Battery Discharge (kWh)'),                        # 178
    ('U16', 10, 'Battery Discharge Capacity (kWh)'),                    # 182
    ('U16', 10, 'Yesterday Battery Discharge (kWh)'),                   # 184
    ('U32', 1, 'Total Imported Energy (kWh)'),                          # 186
    ('U16', 10, 'Today Imported Energy (kWh)'),                         # 190
    ('U16', 10, 'Yesterday Imported Energy (kWh)'),                     # 192
    ('U32', 1, 'Total Exported Energy (kWh)'),                          # 194
    ('U16', 10, 'Today Exported Energy (kWh)'),                         # 198
    ('U16', 10, 'Yesterday Exported Energy (kWh)'),                     # 200
    ('U32', 1, 'Total House Load (kWh)'),                               # 202
    ('U16', 10, 'Today House Load (kWh)'),                              # 206
    ('U16', 10, 'Yesterday House Load (kWh)'),                          # 208
    ('U16', 10, 'Meter AC Voltage A (V)'),                              # 210
    ('U16', 100, 'Meter AC Current A (A)'),                             # 212
    ('U16', 10, 'Meter AC Voltage B (V)'),                              # 214
    ('U16', 100, 'Meter AC Current B (A)'),                             # 216
    ('U16', 10, 'Meter AC Voltage C (V)'),                              # 218
    ('U16', 100, 'Meter AC Current C (A)'),                             # 220
    ('S32', 1000, 'Meter Active Power A (kW)'),                         # 222
    ('S32', 1000, 'Meter Active Power B (kW)'),                         # 226
    ('S32', 1000, 'Meter Active Power C (kW)'),                         # 230
    ('S32', 1000, 'Meter Total active Power (kW)'),                     # 234
    ('S32', 1, 'Meter Active Reactive Power A (VA)'),                   # 238
    ('S32', 1, 'Meter Active Reactive Power B (VA)'),                   # 242
    ('S32', 1, 'Meter Active Reactive Power C (VA)'),                   # 246
    ('S32', 1, 'Meter Total Reactive Power (VA)'),                      # 250
    ('S32', 1, 'Meter Active Apparent Power A (VA)'),                   # 254
    ('S32', 1, 'Meter Active Apparent Power B (VA)'),                   # 258
    ('S32', 1, 'Meter Active Apparent Power C (VA)'),                   # 262
    ('S32', 1, 'Meter Total Apparent Power (VA)'),                      # 266
    ('S16', 1, 'Meter Power Factor'),                                   # 270
    ('U16', 100, 'Meter Grid Frequency (Hz)'),                          # 272
    ('U32', 100, 'Meter Total Active Imported (kWh)'),                  # 274
    ('U32', 100, 'Meter Total Active Exported (kWh)'),                  # 278
    ('U16', 1, 'Set The Flag Bit'),                                     # 282
    ('U16', 1, 'Fault Code 01'),                                        # 284
    ('U16', 1, 'Fault Code 02'),                                        # 286
    ('U16', 1, 'Fault Code 03'),                                        # 288
    ('U16', 1, 'Fault Code 04'),                                        # 290
    ('U16', 1, 'Fault Code 05'),                                        # 292
    ('U16', 1, 'Working Status'),                                       # 294
    ('T64', -1, 'End data time'),                                        # 296
    ('H16', 1, b'\x55\xAA'))                                            # 304

def datalen ():
    dlen = 0
    for type, scl, desc in all_regs:
        dlen += int (type[1:3])
    return dlen // 8

def header ():
    ls = []
    addr = 0
    for type, scl, desc in all_regs:
        if ( type[0] not in 'HX' ):
            ls.append (desc)
        addr += int (type[1:3]) // 8
    return '"' + '","'.join (ls) + '"\n'

def decode (rec):
    lv = []
    addr = 0
    for type, scl, desc in all_regs:
        if ( type == 'H16' ):
            if ( rec[addr:addr+2] != desc ):
                sys.stderr.write ('Invalid record\n' + str (rec) + '\n')
                sys.exit (1)
            addr += 2
            continue
        elif ( type == 'T64' ):
            v = struct.unpack ('<Q', rec[addr:addr+8])[0]
            addr += 8
        elif ( type == 'D96' ):
            v = list (struct.unpack ('<6H', rec[addr:addr+12]))
            addr += 12
            v[0] += 2000
            v = calendar.timegm (v)
        elif ( type == 'X16' ):
            addr += 2
            continue
        elif ( type == 'U16' ):
            v = struct.unpack ('<H', rec[addr:addr+2])[0]
            addr += 2
        elif ( type == 'S16' ):
            v = struct.unpack ('<H', rec[addr:addr+2])[0]
            if ( v >= 0x8000 ):
                v -= 0x10000
            addr += 2
        elif ( type.startswith ('R16') ):
            v = struct.unpack ('<H', rec[addr:addr+2])[0]
            a2 = addr + int (type[3:]) // 8
            s = struct.unpack ('<H', rec[a2:a2+2])[0]
            if ( s > 0 ):
                v = -v
            addr += 2
        elif ( type == 'U32' ):
            v = struct.unpack ('<2H', rec[addr:addr+4])
            v = ( v[0] << 16 ) | v[1]
            addr += 4
        elif ( type == 'S32' ):
            v = struct.unpack ('<2H', rec[addr:addr+4])
            v = ( v[0] << 16 ) | v[1]
            if ( v >= 0x80000000 ):
                v -= 0x100000000
            addr += 4
        elif ( type.startswith ('R32') ):
            v = struct.unpack ('<2H', rec[addr:addr+4])
            v = ( v[0] << 16 ) | v[1]
            a2 = addr + int (type[3:]) // 8
            s = struct.unpack ('<H', rec[a2:a2+2])[0]
            if ( s > 0 ):
                v = -v
            addr += 4
        if ( scl == 1 ):
            lv.append ('{:d}'.format (v))
        elif ( scl == 10 ):
            lv.append ('{:3.1f}'.format (v/scl))
        elif ( scl == 100 ):
            lv.append ('{:4.2f}'.format (v/scl))
        elif ( scl == 1000 ):
            lv.append ('{:5.3f}'.format (v/scl))
        elif ( scl == -1 ):
            lv.append (time.strftime ('%Y-%m-%d %H:%M:%S', time.gmtime (v)))
    return ','.join (lv) + '\n'

def dump (sIn, sOut):
    dlen = datalen ()
    with open (sIn, 'rb') as fIn, open (sOut, 'w') as fOut:
        fOut.write (header ())
        while (True):
            rec = fIn.read (dlen)
            if ( len (rec) == 0 ):
                break
            fOut.write (decode (rec))

if ( len (sys.argv) == 3 ):
    dump (sys.argv[1], sys.argv[2])
else:
    sys.stderr.write ('Usage: solis_dump.py <log file> <csv file>\n')
    sys.exit (1)
