
# levv - Log File Event Viewer

Command line based graphical log file viewer.

![Screen Shot](https://raw.githubusercontent.com/wheresjames/levv/master/imgs/view-syslog.png)

## Keyboard

* LEFT = Scroll back in time
* RIGHT = Scroll forward in time
* UP = Zoom in
* Down = Zoom out

* s = Scroll automatically
* l = Change number of lines per record
* q / esc = Quit

&nbsp;


---------------------------------------------------------------------
## Table of contents

* [Install](#install)
* [Examples](#examples)
* [References](#references)

&nbsp;

---------------------------------------------------------------------
## Install

    $ pip3 install levv

&nbsp;


---------------------------------------------------------------------
## Examples

* Navigate kernel messages

`sudo levv -i /dev/kmsg -I kmsg`

* Navigate syslog messages

`sudo levv -i /var/log/syslog`

* Navigate Apache web logs

`sudo levv -i /var/log/apache2/access.log -I www`

* View data from stdin

`echo "Hello World!" | levv -i -`


## Help

```
usage: levv [-h] [--inputfile INPUTFILE] [--inputformat INPUTFORMAT]
            [--inputbreak INPUTBREAK] [--inputfilter INPUTFILTER]
            [--outputfile OUTPUTFILE] [--outputformat OUTPUTFORMAT]
            [--timerange TIMERANGE] [--time TIME] [--refresh REFRESH]
            [--scroll SCROLL] [--lines LINES] [--maxmsgbuf MAXMSGBUF]
            [--maxfileread MAXFILEREAD] [--debug]

Event monitor.

optional arguments:
  -h, --help            show this help message and exit
  --inputfile INPUTFILE, -i INPUTFILE
                        Log file to parse
  --inputformat INPUTFORMAT, -I INPUTFORMAT
                        Input data format
  --inputbreak INPUTBREAK, -b INPUTBREAK
                        Line break
  --inputfilter INPUTFILTER, -f INPUTFILTER
                        Regex filter expression for input data
  --outputfile OUTPUTFILE, -o OUTPUTFILE
                        Append logs to output file
  --outputformat OUTPUTFORMAT, -O OUTPUTFORMAT
                        Output data format
  --timerange TIMERANGE, -r TIMERANGE
                        Time range
  --time TIME, -t TIME  Time start
  --refresh REFRESH, -R REFRESH
                        Data refresh interval in seconds, 0 for no refresh
  --scroll SCROLL, -s SCROLL
                        1-100, percentage of screen for auto scroll position,
                        0 = Do not auto scroll
  --lines LINES, -l LINES
                        Number of lines per timeline item, can be 1, 2, or 3
  --maxmsgbuf MAXMSGBUF, -m MAXMSGBUF
                        Maxium number of messages to queue
  --maxfileread MAXFILEREAD, -M MAXFILEREAD
                        Maxium number of bytes to read from a file, 0 for all
  --debug, -D           Show debug information
```

&nbsp;


---------------------------------------------------------------------
## References

- Python
    - https://www.python.org/

- pip
    - https://pip.pypa.io/en/stable/

