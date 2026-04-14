
# levv - Log File Event Viewer

A terminal-based graphical log viewer that plots events on an interactive timeline,
with color-coded severity levels and live auto-scrolling.

![Screen Shot](https://raw.githubusercontent.com/wheresjames/levv/main/imgs/view-syslog.png)

&nbsp;


---------------------------------------------------------------------
## Table of contents

* [Features](#features)
* [Install](#install)
* [Quick Start](#quick-start)
* [Examples](#examples)
* [Keyboard](#keyboard)
* [Input Formats](#input-formats)
* [Regex Templates](#regex-templates)
* [Command Line](#command-line)
* [Testing](#testing)
* [References](#references)

&nbsp;


---------------------------------------------------------------------
## Features

- **Timeline view** — events are plotted along a horizontal time axis, so you can
  see bursts, gaps, and patterns at a glance
- **Color-coded severity** — errors appear red, warnings yellow, and normal events
  green, making problems stand out immediately
- **Live tailing** — follows log files and stdin in real time, refreshing
  automatically on a configurable interval
- **Zoom and scroll** — navigate backward/forward in time and zoom the visible
  window from milliseconds to months
- **Multiple built-in formats** — understands syslog, kernel (`kmsg`), Apache/nginx
  access logs (`www`), PM2, and plain text out of the box
- **Custom regex templates** — describe any log format with a named-capture regex
  so levv can extract time, severity, and message fields
- **Filtering** — include only lines that match a regex, or exclude lines that match

&nbsp;


---------------------------------------------------------------------
## Install

```
pip3 install levv
```

&nbsp;


---------------------------------------------------------------------
## Quick Start

With no arguments, levv opens `/var/log/syslog` (if it exists):

```
levv
```

Point it at any log file:

```
levv -i /path/to/app.log
```

Pipe data directly into levv:

```
tail -f /path/to/app.log | levv -i -
```

&nbsp;


---------------------------------------------------------------------
## Examples

**Kernel messages**

```
levv -i /dev/kmsg -I kmsg
```

**Syslog**

```
levv -i /var/log/syslog
```

**Apache or nginx access logs**

```
levv -i /var/log/apache2/access.log -I www
levv -i /var/log/nginx/access.log   -I www
```

**Pipe from stdin**

```
echo "Hello World!" | levv -i -
tail -f /path/to/some/file.log | levv -i -
```

**Show only errors in the last 30 minutes**

```
levv -i app.log -f 'error|ERROR' -r 1800
```

**Hide noisy health-check lines**

```
levv -i /var/log/nginx/access.log -I www -x 'GET /health'
```

**Parse a custom log format with a regex template**

```
levv -i app.log -T '(?P<time>[^ ]+) (?P<sev>\w+) (?P<msg>.*)'
```

**Write a normalised copy of the log to a file**

```
levv -i app.log -o normalised.log
```

&nbsp;


---------------------------------------------------------------------
## Keyboard

| Key | Action |
|-----|--------|
| `LEFT` | Scroll backward in time |
| `RIGHT` | Scroll forward in time |
| `UP` | Zoom in (shrink the visible time window) |
| `DOWN` | Zoom out (expand the visible time window) |
| `PgUp` | Scroll event rows up |
| `PgDn` | Scroll event rows down |
| `s` | Resume auto-scroll (tracks current time) |
| `1`–`9` | Set auto-scroll anchor point (10 %–90 % of screen width) |
| `l` | Cycle lines per event: 1 → 2 → 3 → 1 |
| `q` / `Esc` | Quit |

&nbsp;


---------------------------------------------------------------------
## Input Formats

Pass a format name with `-I` / `--inputformat`:

| Format | Description |
|--------|-------------|
| `auto` | *(default)* Detects a Unix timestamp or a human-readable date at the start of each line; falls back to the current time |
| `text` | Plain text — timestamps the line with the current time |
| `date` | Searches for a human-readable date string at the start of each line |
| `kmsg` | Linux kernel message format read from `/dev/kmsg` |
| `www` | Apache / nginx Combined Log Format |
| `pm2` | PM2 process manager log format |
| `time:` | Simple `<timestamp>: <message>` format |

&nbsp;


---------------------------------------------------------------------
## Regex Templates

For log formats not covered above, supply a named-capture regex with
`-T` / `--inputtemplate`.  levv looks for three named groups:

| Group name | Description |
|------------|-------------|
| `time` | Timestamp string or Unix epoch (float). Parsed automatically. |
| `sev` | Severity — a number (lower = more severe) or a word like `error` / `warn`. |
| `msg` | The message text to display. |

Unnamed groups `1`, `2`, `3` are treated as `msg`, `time`, `sev` respectively
if the named groups are absent.

**Example** — a log that looks like `2024-01-15T10:23:45 ERROR connection refused`:

```
levv -i app.log -T '(?P<time>\S+)\s+(?P<sev>\S+)\s+(?P<msg>.*)'
```

Built-in templates can also be referenced by name with `-I`:

| Name | Pattern |
|------|---------|
| `time:` | `(?P<time>.*?): (?P<msg>.*)` |
| `pm2` | `(?P<sev>.*?)\|.*?\|(?P<time>.*?): (?P<msg>.*)` |

&nbsp;


---------------------------------------------------------------------
## Command Line

```
usage: levv [-h] [-i INPUTFILE] [-I INPUTFORMAT] [-s SEPARATOR]
            [-T INPUTTEMPLATE] [-f FILTER] [-x EXCLUDE]
            [-o OUTPUTFILE] [-O OUTPUTFORMAT]
            [-r TIMERANGE] [-t TIME] [-R REFRESH]
            [-a AUTOSCROLL] [-l LINES]
            [-m MAXMSGBUF] [-M MAXFILEREAD]
            [-k] [-D]

Event monitor.

options:
  -h, --help                        show this help message and exit

Input:
  -i, --inputfile INPUTFILE         Log file to read; use - for stdin
  -I, --inputformat INPUTFORMAT     Input format (auto, text, date, kmsg, www, pm2, time:)
  -s, --separator SEPARATOR         Record separator; default is CR/LF
  -T, --inputtemplate INPUTTEMPLATE Regex template with named groups: time, sev, msg
  -f, --filter FILTER               Show only lines matching this regex
  -x, --exclude EXCLUDE             Hide lines matching this regex

Output:
  -o, --outputfile OUTPUTFILE       Append normalised logs to this file
  -O, --outputformat OUTPUTFORMAT   Output data format

Display:
  -r, --timerange TIMERANGE         Visible time window in seconds (default: 600)
  -t, --time TIME                   Starting time
  -R, --refresh REFRESH             File refresh interval in seconds; 0 = no refresh (default: 3)
  -a, --autoscroll AUTOSCROLL       Auto-scroll anchor: 1–100 % of screen width; 0 = disabled (default: 75)
  -l, --lines LINES                 Lines per event: 1, 2, or 3 (default: 2)

Advanced:
  -m, --maxmsgbuf MAXMSGBUF         Maximum events to keep in memory (default: 5000)
  -M, --maxfileread MAXFILEREAD     Maximum bytes to read from file; 0 = all (default: 10000)
  -k, --keyboard                    Force keyboard processing even when reading from stdin
  -D, --debug                       Show debug information
```

&nbsp;


---------------------------------------------------------------------
## Testing

Install [pytest](https://pytest.org) if you don't have it already:

```
pip3 install pytest
```

Run the full test suite from the project root:

```
pytest test/
```

Run a specific test file:

```
pytest test/test_levv.py   # levv/main.py — filterLine, calcPriority, getLogTemplate
pytest test/test_bin.py    # bin/levv    — parsing and utility functions
```

Run only tests whose name matches a keyword:

```
pytest test/ -k "www"
pytest test/ -k "filterLine or processLine"
```

Add `-v` for verbose output (one line per test) or `--tb=short` for shorter
failure tracebacks:

```
pytest test/ -v --tb=short
```

&nbsp;


---------------------------------------------------------------------
## References

- [levv on GitHub](https://github.com/wheresjames/levv)
- [levv on PyPI](https://pypi.org/project/levv/)
- [Python](https://www.python.org/)
- [pip](https://pip.pypa.io/en/stable/)
- [python-dateutil](https://dateutil.readthedocs.io/)
