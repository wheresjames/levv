
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
* [Auto-Detection](#auto-detection)
* [Regex Templates](#regex-templates)
* [Command Line](#command-line)
* [Extending](#extending)
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
- **Auto-detection** — samples the first lines of a file and selects the best
  matching format automatically; the active format is shown in the top-right corner
- **Many built-in formats** — syslog, journald, Docker, JSON Lines, logfmt,
  nginx error logs, Python logging, Log4j/Logback, kernel messages, Apache/nginx
  access logs, PM2, and plain text
- **Automatic permission elevation** — prompts to re-run under `sudo` when a file
  cannot be read due to permissions
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

List all supported input formats:

```
levv --listformats
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

**nginx error log**

```
levv -i /var/log/nginx/error.log -I nginx-error
```

**systemd journal**

```
journalctl -f | levv -i -
journalctl --output=short-iso -f | levv -i - -I journald
```

**Docker container logs**

```
docker logs -f mycontainer | levv -i -
```

**JSON Lines / structured logs**

```
levv -i /var/log/myapp/app.log -I json
```

**Go logfmt (Prometheus, Loki, etc.)**

```
levv -i /var/log/myapp/app.log -I logfmt
```

**Python application logs**

```
levv -i /var/log/myapp/app.log -I python
```

**Java / Log4j / Logback**

```
levv -i /var/log/myapp/app.log -I log4j
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

Pass a format name with `-I` / `--inputformat`, or let levv detect it automatically.
The active format is always shown in the top-right corner of the screen as `[fmt:name]`.

Run `levv --listformats` to see the full list with descriptions.

| Format | Description |
|--------|-------------|
| `auto` | *(default)* Auto-detects per line: Unix timestamp → human-readable date → current time |
| `text` | Plain text — stamps every line with the current time |
| `date` | Human-readable date/time prefix |
| `kmsg` | Linux kernel messages from `/dev/kmsg` |
| `www` | Apache / nginx Combined Log Format (access logs) |
| `syslog` | Syslog — RFC 3164 and RFC 5424, including `/var/log/syslog` |
| `journald` | systemd journal (`journalctl --output=short-iso`) |
| `docker` | Docker log driver output (ISO timestamp + stream + message) |
| `json` | JSON Lines / NDJSON (zerolog, zap, structlog, pino, GCP, …) |
| `logfmt` | `key=value` pairs (Prometheus, Loki, Go services) |
| `nginx-error` | nginx error log (`YYYY/MM/DD HH:MM:SS [level] …`) |
| `python` | Python `logging` module (`basicConfig` and common formatters) |
| `log4j` | Log4j / Logback / Log4net (Java logging frameworks) |
| `pm2` | PM2 process manager log format |
| `time:` | Simple `<timestamp>: <message>` format |

&nbsp;


---------------------------------------------------------------------
## Auto-Detection

When `-I` is not specified (or is set to `auto`), levv samples the first 20 lines
of the file and scores each format using a probe function before reading any events.
The detection strategy is:

1. **JSON Lines** — checked first because it is unambiguous (lines that are valid
   JSON objects).
2. **Probe scoring** — each non-fallback format returns a confidence value (0–1)
   for each sampled line.  The format with the highest average score wins, provided
   it matches at least 50 % of the sample.
3. **Filename hint** — the file's extension or basename (e.g. `syslog`,
   `access.log`, `*.json`) is used as a tiebreaker when two formats score closely.

The detected (or user-specified) format name is always visible in the top-right
corner of the screen so you know what levv is using.

&nbsp;


---------------------------------------------------------------------
## Regex Templates

For log formats not covered by the built-in parsers, supply a named-capture regex
with `-T` / `--inputtemplate`.  levv looks for three named groups:

| Group name | Description |
|------------|-------------|
| `time` | Timestamp string or Unix epoch (float). Parsed automatically. |
| `sev` | Severity — a number (lower = more severe) or a word like `error` / `warn`. |
| `msg` | The message text to display. |

Optional sub-second groups can be added alongside `time`:

| Group name | Description |
|------------|-------------|
| `msecs` | Milliseconds to add to `time` |
| `usecs` | Microseconds to add to `time` |
| `nsecs` | Nanoseconds to add to `time` |

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
            [-k] [-D] [--listformats]

Event monitor.

options:
  -h, --help                        show this help message and exit
  --listformats                     list all supported input formats and exit

Input:
  -i, --inputfile INPUTFILE         Log file to read; use - for stdin (default: /var/log/syslog)
  -I, --inputformat INPUTFORMAT     Input format name (default: auto); see --listformats
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
## Extending

Each input format lives in its own module under `levv/formats/`.  Adding a new
format requires only two steps:

**1. Create `levv/formats/myformat.py`** and export these five names:

```python
NAME        = 'myformat'          # used with -I flag
DESCRIPTION = 'My log format'     # shown by --listformats
EXTENSIONS  = ['myformat.log']    # filename hints for auto-detection

def probe(line: str) -> float:
    """Return confidence 0.0–1.0 that *line* belongs to this format."""
    ...

def parse(line: str) -> dict:
    """Return {'time': float, 'sev': int, 'msg': str} or {} on failure."""
    ...
```

**2. Register it in `levv/formats/__init__.py`**:

```python
from . import myformat          # add this import
...
_FORMAT_MODULES = [
    ...
    myformat,                   # add to the list
]
```

The format is then available via `-I myformat`, included in `--listformats` output,
and automatically considered during format detection.

Shared utilities (`findDate`, `calcPriority`, `parse_time_str`) are available in
`levv.formats.utils`.

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
pytest test/test_levv.py    # levv/main.py  — filterLine, calcPriority, getLogTemplate
pytest test/test_bin.py     # bin/levv      — utility functions and processLine dispatch
pytest test/test_formats.py # levv/formats/ — all format parsers and auto-detection
```

Run only tests whose name matches a keyword:

```
pytest test/ -k "json"
pytest test/ -k "probe or detect"
```

Add `-v` for verbose output or `--tb=short` for shorter failure tracebacks:

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
