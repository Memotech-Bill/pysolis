#!/home/pi/pysolis/bin/python3
"""Query Solis Data Logger to collect timed charge details"""

import umodbus.client.tcp
import socket
import argparse
import time
import os
import sys
import logging

logger = logging.getLogger (__name__)

class Solis:
    def __init__ (self, addr):
        self.sid = 1
        self.sock = socket.create_connection ((addr, 502), timeout = 20)

    def request (self, req):
        val = None
        try:
            val = umodbus.client.tcp.send_message (req, self.sock)
        except TimeoutError:
            logger.exception ('Timeout')
        except KeyError as e:
            logger.exception ('Key Error')
        except struct.error as e:
            logger.exception ('Structure Error')
        return val

    def get_current (self):
        req = umodbus.client.tcp.read_holding_registers (self.sid, 43141, 2)
        return self.request (req)

    def set_current (self, chg, dis):
        val = self.get_current ()
        if val is None:
            logger.error ('Failed to get previous currents')
            return False
        if val[0] != chg or val[1] != dis:
            req = umodbus.client.tcp.write_single_register (self.sid, 43141, chg)
            self.request (req)
            req = umodbus.client.tcp.write_single_register (self.sid, 43142, dis)
            self.request (req)
            val = self.get_current ()
            logger.info ('Currents set to: ' + str(val))
            if val is not None:
                sta = True
                if val[0] != chg:
                    logger.error ('Failed to set charging current')
                    sta = False
                if val[1] != dis:
                    logger.error ('Failed to set discharge current')
                    sta = False
                return sta
            return False
        return True

    def get_times (self):
        req = umodbus.client.tcp.read_holding_registers (self.sid, 43143, 8)
        return self.request (req)

    def match_times (self, times):
        val = self.get_times ()
        if val is None:
            logger.error ('Failed to get timed charge times')
            return False
        match = True
        for i, t in enumerate (times):
            if val[i] != t:
                match = False
                break
        return match

    def set_times (self, times):
        if not self.match_times (times):
            req = umodbus.client.tcp.write_multiple_registers (self.sid, 43143, times)
            self.request (req)
            if self.match_times (times):
                logger.info ('Charging times set to: ' + str (times))
            else:
                logger.error ('Failed to set charging times')
                return False
        return True

    def get_control_word (self):
        req = umodbus.client.tcp.read_holding_registers (self.sid, 43110, 1)
        self.cwd = self.request (req)[0]
        return self.cwd

    def set_control_word (self, cwd):
        req = umodbus.client.tcp.write_single_register (self.sid, 43110, cwd)
        self.request (req)
        if self.get_control_word () != cwd:
            logger.error (f'Failed to set control word: Requested: {cwd:02X}, Actual {self.cwd:02X}')
            return False
        return True

    def get_time_charge (self):
        return self.get_control_word () & 0x02 > 0

    def enable_time_charge (self, enable):
        if self.get_time_charge () != enable:
            cwd = self.cwd & 0xFFFD
            if cwd != 0x21:
                logger.error (f'Unexpected control word: {self.cwd:02X}')
                return False
            if enable:
                cwd |= 0x02
            if self.set_control_word (cwd):
                if enable:
                    logger.info ('Enabled time charge')
                else:
                    logger.info ('Disabled time charge')
                return True
            return False
        return True

    def get_battery (self):
        req = umodbus.client.tcp.read_input_registers (self.sid, 33139, 1)
        return self.request (req)[0]

if __name__ == '__main__':
    p = argparse.ArgumentParser (description = 'Controls timed charging according to battery charge')
    p.add_argument ('-a', '--ip_address', required = True, help = 'Address of Solis Invertor')
    p.add_argument ('-b', '--battery-level', type = int, default = 25, help = 'Battery level below which to enable timed charge')
    p.add_argument ('-c', '--current', type = int, default = 10, help = 'Timed charge charging current')
    p.add_argument ('-s', '--start-time', default = '23:00', help = 'Charging start time (hh:mm)')
    p.add_argument ('-e', '--end-time', default = '01:00', help = 'Charging stop time (hh:mm)')
    p.add_argument ('-l', '--log-dir', default = None, help = 'Directory for log files')
    args = p.parse_args ()

    if args.log_dir is not None:
        tm = time.gmtime (time.time ())
        dir = '{:s}/{:04d}/{:02d}'.format (args.log_dir, tm.tm_year, tm.tm_mon)
        os.makedirs (dir, exist_ok=True)
        logging.basicConfig (filename = os.path.join (dir, 'tcharge.log'), level = logging.INFO,
                             format = '{asctime}: {levelname}: {message}', style = '{')
    else:
        logging.basicConfig (stream = sys.stderr, level = logging.INFO)

    s = Solis (args.ip_address)
    bat = s.get_battery ()
    logging.info (f'Battery level: {bat}%')
    if bat < args.battery_level:
        chg = 10 * args.current
        times = [0, 0, 0, 0, 0, 0, 0, 0]
        ts = args.start_time.split (':')
        times[0] = int (ts[0])
        times[1] = int (ts[1])
        te = args.end_time.split (':')
        times[2] = int (te[0])
        times[3] = int (te[1])
        s.set_current (chg, chg) and s.set_times (times) and s.enable_time_charge (True)
    else:
        s.enable_time_charge (False)
