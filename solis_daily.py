#!/usr/bin/python3
#
# Generate an HTML file showing daily Solar Power usage
#
import os
import sys
import time
import struct
import csv
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

reclen = 306
sDataDir = '/home/pi/pysolis/log'
sLogDir = '/home/pi/pysolis/html'

rdTime = 0
rdSolar = 1
rdLoad = 2
rdInvtr = 3
rdBatt = 4
rdGrid = 5
rdSoC = 6

scSolar = 0
scBatt = 1
scGrid = 2

skHouse = 0
skInvtr = 1
skBatt = 2
skGrid = 3

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
    invtr = solar - load - batt - grid
    bsoc = struct.unpack ('<H', rec[146:148])[0]
    return (t, solar, load, invtr, batt, grid, bsoc)

def TimeFmt (t, pos):
    t = int (t)
    h = ( t // 3600 ) % 24
    m = ( t // 60 ) % 60
    return '{:d}:{:02d}'.format (h, m)

class Daily:
    def Load (self, sDir, tm):
        sFile = os.path.join (sDir, 'Solis_{:04d}{:02d}{:02d}.dat'.format (tm.tm_year, tm.tm_mon, tm.tm_mday))
        with open (sFile, 'rb') as f:
            self.time = []
            self.solar = []
            self.invtr = []
            self.load = []
            self.batt = []
            self.grid = []
            self.soc = []
            self.use = [[0.0, 0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 0.0]]
            src = [0.0, 0.0, 0.0]
            sink = [0.0, 0.0, 0.0, 0.0]
            while (True):
                rec = f.read (reclen)
                if ( not rec ):
                    break
                data = Decode (rec)
                self.time.append (data[rdTime])
                self.solar.append (data[rdSolar])
                self.load.append (data[rdLoad])
                self.invtr.append (data[rdInvtr])
                self.batt.append (-data[rdBatt])
                self.grid.append (-data[rdGrid])
                self.soc.append (data[rdSoC])
                src[scSolar] = data[rdSolar]
                if ( data[rdGrid] >= 0.0 ):
                    sink[skGrid] = data[rdGrid]
                    src[scGrid] = 0.0
                else:
                    sink[skGrid] = 0
                    src[scGrid] = - data[rdGrid]
                if ( data[rdBatt] >= 0.0 ):
                    sink[skBatt] = data[rdBatt]
                    src[scBatt] = 0.0
                else:
                    sink[skBatt] = 0.0
                    src[scBatt] = -data[rdBatt]
                sink[skInvtr] = data[rdInvtr]
                sink[skHouse] = data[rdLoad]
                for sc in [scSolar, scBatt, scGrid]:
                    if ( src[sc] == 0.0 ):
                        continue
                    for sk in [skGrid, skBatt, skInvtr, skHouse]:
                        if ( src[sc] > sink[sk] ):
                            self.use[sc][sk] += sink[sk]
                            src[sc] -= sink[sk]
                            sink[sk] = 0.0
                        else:
                            self.use[sc][sk] += src[sc]
                            sink[sk] -= src[sc]
                            src[sc] = 0.0
                            break
            scl = 0.024 / len (self.time)
            for sc in [scSolar, scBatt, scGrid]:
                for sk in [skGrid, skBatt, skInvtr, skHouse]:
                    self.use[sc][sk] *= scl

    def Log (self, sDir, tm):
        sFile = os.path.join (sDir, 'Solis_Monthly_{:04d}{:02d}.csv'.format (tm.tm_year, tm.tm_mon))
        if ( os.path.exists (sFile) ):
            f = open (sFile, 'a')
        else:
            os.makedirs (sDir, exist_ok = True)
            f = open (sFile, 'w')
            f.write ('Year,Month,Day')
            for sSrc in ['Solar', 'Battery', 'Grid']:
                for sSink in ['House', 'Inverter', 'Battery', 'Grid']:
                    f.write (',{:s} to {:s}'.format (sSrc, sSink))
            f.write ('\n')
        f.write ('{:d},{:d},{:d}'.format (tm.tm_year, tm.tm_mon, tm.tm_mday))
        for sc in [scSolar, scBatt, scGrid]:
            for sk in [skHouse, skInvtr, skBatt, skGrid]:
                f.write (',{:5.3f}'.format (self.use[sc][sk]))
        f.write ('\n')
        f.close ()

    def PowerPlt (self, sDir, tm):
        fig = plt.figure (figsize=(10.0, 7.5), dpi = 100, facecolor='w')
        ax = fig.add_axes ([0.1, 0.1, 0.85, 0.85])
        tmin = self.time[0] - self.time[0] % 86400
        tmax = tmin + 86400
        ax.set_xlim (tmin, tmax)
        ax.plot (self.time, self.solar, label='Solar', color='#00FF00')
        ax.plot (self.time, self.load, label='Load', color='#000000')
        ax.plot (self.time, self.invtr, label='Inverter', color='#FFFF00')
        ax.plot (self.time, self.batt, label='Battery', color = '#0000FF')
        ax.plot (self.time, self.grid, label='Grid', color = '#FF0000')
        ax.set_xlabel ('Time')
        ax.set_ylabel ('Power (W)')
        ax.set_title (time.strftime ('%d %B %Y', tm))
        ax.legend (loc='upper center', ncol=4)
        ax.xaxis.set_major_formatter (ticker.FuncFormatter(TimeFmt))
        ax.xaxis.set_major_locator (ticker.LinearLocator (numticks = 13))
        fig.savefig (os.path.join (sDir, 'Power_{:04d}{:02d}{:02d}.png'
                                   .format (tm.tm_year, tm.tm_mon, tm.tm_mday)),
                     format = 'png')

    def BatteryPlt (self, sDir, tm):
        fig = plt.figure (figsize=(10.0, 4.5), dpi = 100, facecolor='w')
        ax = fig.add_axes ([0.1, 0.1, 0.85, 0.85])
        tmin = self.time[0] - self.time[0] % 86400
        tmax = tmin + 86400
        ax.set_xlim (tmin, tmax)
        ax.set_ylim (0.0, 100.0)
        ax.plot (self.time, self.soc, label='State of Charge', color='#0000FF')
        ax.set_xlabel ('Time')
        ax.set_ylabel ('State of Charge')
        ax.set_title (time.strftime ('%d %B %Y', tm))
        ax.xaxis.set_major_formatter (ticker.FuncFormatter(TimeFmt))
        ax.xaxis.set_major_locator (ticker.LinearLocator (numticks = 13))
        ax.yaxis.set_major_formatter (ticker.PercentFormatter ())
        fig.savefig (os.path.join (sDir, 'Battery_{:04d}{:02d}{:02d}.png'
                                   .format (tm.tm_year, tm.tm_mon, tm.tm_mday)),
                     format = 'png')

    def ConsumePie (self, sDir, tm):
        fig = plt.figure (figsize=(4.5, 4.5), dpi = 100, facecolor='w')
        ax = fig.add_axes ([0.05, 0.05, 0.9, 0.9])
        ax.pie ([self.use[scSolar][skHouse] + self.use[scSolar][skInvtr],
                 self.use[scBatt][skHouse] + self.use[scBatt][skInvtr],
                 self.use[scGrid][skHouse] + self.use[scGrid][skInvtr]],
                labels = ['Solar', 'Battery', 'Grid'],
                colors = ['#00FF00', '#0000FF', '#FF0000'],
                autopct = '%5.3f kWh',
                radius = 1.0,
                center = (2.25, 2.25))
        ax.set_title (time.strftime ('%d %B %Y', tm) + ' Consumed Power')
        fig.savefig (os.path.join (sDir, 'Consume_{:04d}{:02d}{:02d}.png'
                                   .format (tm.tm_year, tm.tm_mon, tm.tm_mday)),
                     format = 'png')

    def ProducePie (self, sDir, tm):
        fig = plt.figure (figsize=(4.5, 4.5), dpi = 100, facecolor='w')
        ax = fig.add_axes ([0.05, 0.05, 0.9, 0.9])
        ax.pie (self.use[scSolar],
                labels = ['House', 'Inverter', 'Battery', 'Grid'],
                colors = ['#00FF00', '#FFFF00', '#0000FF', '#FF0000'],
                autopct = '%5.3f kWh',
                radius = 1.0,
                center = (2.25, 2.25))
        ax.set_title (time.strftime ('%d %B %Y', tm) + ' Produced Power')
        fig.savefig (os.path.join (sDir, 'Produce_{:04d}{:02d}{:02d}.png'
                                   .format (tm.tm_year, tm.tm_mon, tm.tm_mday)),
                     format = 'png')

    def Process (self, sDDir, sLDir, tm):
        self.Load (sDDir, tm)
        self.Log (sLDir, tm)
        self.ConsumePie (sLDir, tm)
        self.ProducePie (sLDir, tm)
        self.PowerPlt (sLDir, tm)
        self.BatteryPlt (sLDir, tm)

class Monthly:
    def Load (self, sDir, tm):
        sFile = os.path.join (sDir, 'Solis_Monthly_{:04d}{:02d}.csv'.format (tm.tm_year, tm.tm_mon))
        with open (sFile, 'r', newline='') as f:
            nrow = 0
            self.days = []
            self.data = [[[], [], [], []], [[], [], [], []], [[], [], [], []]]
            for row in csv.reader (f):
                nrow += 1
                if (( nrow > 1 ) and ( len (row) == 15 )):
                    self.days.append (int (row[2]))
                    icol = 3
                    for sc in [scSolar, scBatt, scGrid]:
                        d1 = []
                        for sk in [skHouse, skInvtr, skBatt, skGrid]:
                            self.data[sc][sk].append (float (row[icol]))
                            icol += 1
        self.days = np.array (self.days)
        self.data = np.array (self.data)

    def ConsumePlt (self, sDir, tm):
        fig = plt.figure (figsize=(10.0, 4.5), dpi = 100, facecolor='w')
        ax = fig.add_axes ([0.1, 0.1, 0.85, 0.85])
        consume = self.data[scSolar, :, :] + self.data[scBatt, :, :] + self.data[scGrid, :, :]
        ax.bar (self.days, consume[skInvtr, :], color='#FFFF00', label='Inverter')
        ax.bar (self.days, consume[skHouse, :], bottom=consume[skInvtr, :], color='#00FF00', label='House')
        ax.set_xlabel ('Day of the Month')
        ax.set_ylabel ('Energy (kWh)')
        ax.set_title ('Energy Consumption ' + time.strftime ('%B %Y', tm))
        fig.savefig (os.path.join (sDir, 'Monthly_Consume_{:04d}{:02d}.png'
                                   .format (tm.tm_year, tm.tm_mon)),
                     format = 'png')

    def SupplyPlt (self, sDir, tm):
        fig = plt.figure (figsize=(10.0, 4.5), dpi = 100, facecolor='w')
        ax = fig.add_axes ([0.1, 0.1, 0.85, 0.85])
        supply = self.data[:,skHouse,:] + self.data[:,skInvtr,:]
        ax.bar (self.days, supply[scGrid, :], color='#FF0000', label='Grid')
        ax.bar (self.days, supply[scBatt, :], bottom=supply[scGrid, :], color='#0000FF', label='Battery')
        ax.bar (self.days, supply[scSolar, :], bottom=supply[scGrid, :] + supply[scBatt, :],
                color='#00FF00', label='Solar')
        ax.set_xlabel ('Day of the Month')
        ax.set_ylabel ('Energy (kWh)')
        ax.set_title ('Energy Supply ' + time.strftime ('%B %Y', tm))
        fig.savefig (os.path.join (sDir, 'Monthly_Supply_{:04d}{:02d}.png'
                                   .format (tm.tm_year, tm.tm_mon)),
                     format = 'png')

    def ProducePlt (self, sDir, tm):
        fig = plt.figure (figsize=(10.0, 4.5), dpi = 100, facecolor='w')
        ax = fig.add_axes ([0.1, 0.1, 0.85, 0.85])
        ax.bar (self.days, self.data[scSolar, skGrid, :], color='#FF0000', label='Grid')
        ax.bar (self.days, self.data[scSolar, skBatt, :], bottom=self.data[scSolar, skGrid, :],
                color='#0000FF', label='Battery')
        ax.bar (self.days, self.data[scSolar, skInvtr, :],
                bottom=self.data[scSolar, skGrid, :] + self.data[scSolar, skBatt, :],
                color = '#FFFF00', label='Inverter')
        ax.bar (self.days, self.data[scSolar, skHouse, :],
                bottom=self.data[scSolar, skGrid, :] + self.data[scSolar, skBatt, :]
                + self.data[scSolar, skInvtr, :],
                color = '#00FF00', label='House')
        ax.set_xlabel ('Day of the Month')
        ax.set_ylabel ('Energy (kWh)')
        ax.set_title ('Energy Production ' + time.strftime ('%B %Y', tm))
        fig.savefig (os.path.join (sDir, 'Monthly_Produce_{:04d}{:02d}.png'
                                   .format (tm.tm_year, tm.tm_mon)),
                     format = 'png')

    def Process (self, sDir, tm):
        self.Load (sDir, tm)
        self.ConsumePlt (sDir, tm)
        self.SupplyPlt (sDir, tm)
        self.ProducePlt (sDir, tm)

def Main ():
    if ( len (sys.argv) > 1 ):
        tm = time.strptime (sys.argv[1], '%Y-%m-%d')
    else:
        tm = time.gmtime (time.time () - 86400)
    sDDir = os.path.join (sDataDir, '{:04d}'.format (tm.tm_year), '{:02d}'.format (tm.tm_mon))
    sLDir = os.path.join (sLogDir, '{:04d}'.format (tm.tm_year), '{:02d}'.format (tm.tm_mon))
    if ( len (sys.argv) == 3 ):
        sDDir = sys.argv[2]
        sLDir = sys.argv[2]
    elif ( len (sys.argv) > 3 ):
        sDDir = sys.argv[2]
        sLDir = sys.argv[3]
    Daily ().Process (sDDir, sLDir, tm)
    Monthly ().Process (sLDir, tm)

Main ()
