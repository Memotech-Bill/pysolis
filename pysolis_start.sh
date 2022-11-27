#!/bin/sh
cd /home/pi/pysolis
./solis_capture eth0 1.42.0.174 log >capture.log 2>&1 &
cd html
/usr/bin/python3 -m http.server 8080 --cgi >/dev/null 2>&1 &
