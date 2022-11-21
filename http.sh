#!/bin/sh
cd /home/pi/pysolis/html/
/usr/bin/python3 -m http.server 8080 --cgi >/dev/null 2>&1 &
