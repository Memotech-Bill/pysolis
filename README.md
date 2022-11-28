# pysolis - Stand Alone HTML Monitor for Solis PV System

## Introduction

This is a set of Python programs and HTML scripts to provide monitoring of a Solis S5-EH1P-L Hybrid
Inverter, independent of the manufacturer's cloud based system. At present the system purely provides
monitoring and does not attempt to take any action based upon the data.

The code has been developed ad-hoc, and is not entirely consistent. Use at your own risk.

The data is obtained via a Solis data logger with Ethernet connection. The particular data logger
I have has serial number 1905XXXXXX and firmware version ME-121001-V1.0.6(202011261020). This data logger
has port 30003 open and standard Modbus protocol may be used on this port to access Inverter registers.

My understanding is that other Solis data loggers use port 8899, and some use a propriatory wrapper
around the Modbus protocol. See https://github.com/jmccrohan/pysolarmanv5 for how to obtain data in
this case.

Details of the registers in the inverter have been taken from
https://www.scss.tcd.ie/coghlan/Elios4you/RS485_MODBUS-Hybrid-BACoghlan-201811228-1854.pdf .

Most of the documented registers are being captured, but at present only the following
are being displayed.

* 33057-8 Total DC output power (generated by the solar cells)
* 33130-1 Meter active power (power to (+)/from (-) the grid)
* 33135   Battery current direction (0 = charging, 1 = discharging)
* 33147   House load
* 33149-5 Battery power (use current direction to provide sign)

The values provided from these registers have been checked against those from the cloud based system,
and proved consistent.

One would expect that the power in and the power out from the above registers should match. However,
in practice I have found that there is always a difference, typically between 100-200W. Failing any
other information I have assumed that this is power used by the inverter itself.

### Revision

Experience has shown that port 30003 sometimes stops working for extended periods for unknown reasons.
No sooner is the connection opened than it is closed again by the data logger before any data can
be requested.

Therefore to provide a fallback, the data being sent to the cloud is captured as it passes through.
Again, all the available data is being captured but only the same small subset is being displayed.

## Configuration

I run the software on a Raspberry Pi. The Raspberry Pi ethernet port is wired directly to the
ethernet port on the data logger. The Raspberry Pi is connected to the home router by WiFi.

To provide DHCP to the data logger and to NAT its connection to the cloud, "Network Manager"
is used.

* Use apt to install the "network-manager" package.
* Run raspi-config (as root). Select "Advanced Options" / "Network Config" / "NetworkManager".
* Run the command `sudo nmcli con modify "Wired Connection 1" ipv4.method shared`.

The software is written for Python 3, and requires the following additional packages:

* matplotlib - Used for generating the statistical plots. Install using APT
* umodbus - To access the Modbus registers on the inverter. This has to be unstalled in a
Python virtual environment using PIP.

The following folder structure is used:

* /home/pi/pysolis - This is the root of the Python virtual environment.
  * solis_query.py - Obtain data from Modbus registers and save it to binary data files.
  * solis_daily.py - Generate daily summeries of inverter data.
  * log - Root folder for logged data
    * Per year and per month sub-folders containing the data files.
  * http - Root folder for web interface
    * solis.html - Page providing live monitoring information
    * daily.html - Page providing data from previous days
    * monthly.html - Page providing monthly statistics
    * htbin - Folder for CGI programs
      * solis_data.py - A CGI program to provide inverter data to solis.html
    * Per year and per month folders containing statistical plots
  * bin - Python virtual environment folder
  * include - Python virtual environment folder
  * lib - Python virtual environment folder
  * share - Python virtual environment folder

### solis_query.py - Get data from inverter

This program takes two parameters:

* The IP address of the data logger.
* The top level directory to receive logged data.

Each time it is run it reads most of the inverter registers and stores them in a binary file named:

     <log dir>/yyyy/mm/Solis_yyyymmdd.dat

Crontab should be configured to run this program every 5 minutes.

All times recorded, and file names are based upon GMT (UTC) so that each day contains 24h, irrespective
of daylight saving time.

### solis_capture.c

This program uses libpcap to capture the data being sent to the cloud as it passes through the
Raspberry Pi.

Although there are Python interfaces to libpcap, they are poorly documented. Also with a compiled
executable it is possible to configure it to run as a normal user, whereas a python script would
need to be run as root.

To compile the program use:

````
gcc -o solis_capture solis_capture.c -lpcap
````

The program takes three command line parameters:

* The name of the ethernet port that is connected to the Solis inverter.
* The IP address of the Solis inverter.
* The top level directory in which to record the captured data.

The captured data is recorded as records in files named `yyyy/mm/Solis_Rnnn_yyyymmdd.cap`, where
nnn is the length of the data packet being sent to the cloud. Only the data in the 250 byte
records is currently being used.

Information on the contents of this record was obtained from:
https://community.home-assistant.io/t/getting-data-from-solis-inverter/302189/30.

Configuring the program to work without root permissions was based upon:
https://web.archive.org/web/20160403142820/http://peternixon.net/news/2012/01/28/configure-tcpdump-work-non-root-user-opensuse-using-file-system-capabilities/

Since I already had Wireshark installed with dumpcap configured to work as non-root using group
`wireshark`, I reused this for `solis_capture` using the commands:

````
chgrp wireshark solis_capture
chmod 750 solis_capture
setcap cap_net_raw,cap_net_admin=ep solis_capture
````

This program is started from the same script as starts the webserver (see below). This script is
started from `crontab` using `@reboot`.

### solis_daily.py - Generate or update plots on a daily basis

This program reads the binary file created by solis_query.py for the previous day and generates the
following plots (PNG files):

* `html/yyyy/mm/Consume_yyyymmdd.png` - Pie chart showing the fraction of power consumed by the house
  or inverter comming from the solar panels, battery or grid.
* `html/yyyy/mm/Produce_yyyymmdd.png` - Pie chart showing the fraction of power produced by the solar
  panels going to the house, inverter, battery or grid.
* `html/yyyy/mm/Power_yyyymmdd.png` - Time history of power to the house, to the inverter, to or from
  the battery, to or from the grid.
* `html/yyyy/mm/Battery_yyyymmdd.png` - Time history of battery state of charge.
* `html/yyyy/mm/Monthly_Consume_yyyymm.png` - Power consumed by house and inverter for each day of the
  month.
* `html/yyyy/mm/Monthly_Supply_yyyymm.png` - For each day of the month, the fraction of consumed power
  that was supplied by the solar panels, battery or grid.
* `html/yyyy/mm/Monthly_Produce_yyyymm.png` - For each day of the month, the fraction of power generated
  by the solar panels that went to the house, inverter, battery or grid.

In order to generate the monthly plots it also generates a CSV file `html/yyyy/mm/Solis_Monthly_yyyymm.csv`
which contains one line for each day indicating how much power flowed from each source (solar panels,
battery or grid) to each sink (house, inverter, battery, grid).

The top level folders for the binary data and the plot output are configured by statements near the top
of the Python code.

### solis_data.py - CGI program to provide time series data to solis.html

This program takes one query parameter:

* From= C time (seconds since 1 Jan 1970) from which to supply data. Data is supplied from this time
  until the last record or the end of the day.

The following data is supplied in CSV format:

* Time of data (C time, seconds)
* House consumption (W)
* Solar panel production (W)
* Battery charge / discharge (W)
* Grid export / import (W)
* Battery state of charge (%)

Once the page `solis.html` is loaded, it calls this program every 5 minutes (AJAX code) to update the
displayed statistics.

The top level folder for the binary datais configured by a statement near the top of the Python code.

Crontab should be configured to run this program once per day. Since crontab uses local time, the
time selected should be after 02:00 to ensure that during the summer the program is run in the new
day wrt GMT, and to prevent it being run twice the day the clocks are put back in the autumn.

### solis_dump.py - Decode the binary dump files generated by solis_query.py.

This program converts the binary dump files into CSV files that can be further examined in a spreadsheet.

The program takes two command line parameters:

* Path to the binary data file to decode.
* Path to the CSV file to create.

TODO: Convert the program to a CGI program providing browser download of the decoded data.

### Webserver

A webserver is required to serve the HTML pages and data. Most webservers could be used, but consistent
with the small scale of the project, and the Python programming, the Python server is used. This is
started by the script `http.sh`:

````
#!/bin/sh
cd /home/pi/pysolis
./solis_capture eth0 1.42.0.174 log >capture.log 2>&1 &
cd html
/usr/bin/python3 -m http.server 8080 --cgi >/dev/null 2>&1 &
````

Which is in turn started from crontab using `@reboot`.

This is acceptable for a system that is only accessible from within the home network. If there is any
exposure to the wider internet then a more secure server should be used.

