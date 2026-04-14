
# levv - Log File Event Viewer

A graphical log viewer that plots events on an interactive timeline,
with color-coded severity levels and live auto-scrolling.
Runs as a terminal UI or in your browser with `-w`.

![Web UI](https://raw.githubusercontent.com/wheresjames/levv/main/imgs/webview-kmsg.png)

&nbsp;


---------------------------------------------------------------------
## Table of contents

* [Features](#features)
* [Install](#install)
* [Quick Start](#quick-start)
* [Examples](#examples)
* [Keyboard](#keyboard)
* [Web Interface](#web-interface)
* [Input Formats](#input-formats)
* [Auto-Detection](#auto-detection)
* [Regex Templates](#regex-templates)
* [Command Line](#command-line)
* [Extending](#extending)
* [Testing](#testing)
* [Building and publishing](#building-and-publishing)
* [References](#references)

&nbsp;


---------------------------------------------------------------------
<h2 id="features">Features</h2>

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
  nginx error logs, Apache error logs, Python logging, Log4j/Logback, kernel
  messages, Apache/nginx access logs, HAProxy, Traefik, PostgreSQL, MySQL,
  GELF, CEF, W3C Extended (IIS), Android logcat, Kubernetes, CSV/TSV, PM2,
  and plain text
- **Multiple files** — monitor several log files simultaneously on one timeline;
  messages are labelled by source and individual files can be isolated with a keypress
- **Web interface** — add `-w` to open a browser-based viewer with the same
  functionality and a dark theme; no extra dependencies required
- **Automatic permission elevation** — prompts to re-run under `sudo` when a file
  cannot be read due to permissions
- **Custom regex templates** — describe any log format with a named-capture regex
  so levv can extract time, severity, and message fields
- **Filtering** — include only lines that match a regex, or exclude lines that match

&nbsp;


---------------------------------------------------------------------
<h2 id="install">Install</h2>

```
pip3 install levv
```

&nbsp;


---------------------------------------------------------------------
<h2 id="quick-start">Quick Start</h2>

With no arguments, levv opens `/var/log/syslog` (if it exists):

```
levv
```

Point it at any log file:

```
levv /path/to/app.log
levv -i /path/to/app.log
```

Monitor multiple files at once:

```
levv /var/log/syslog /var/log/auth.log
levv -i /var/log/syslog,/var/log/auth.log
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
<h2 id="examples">Examples</h2>

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

**Apache httpd error log**

```
levv -i /var/log/apache2/error.log -I apache-error
```

**HAProxy**

```
levv -i /var/log/haproxy.log -I haproxy
```

**Traefik**

```
# JSON mode (recommended in modern Traefik configs)
levv -i /var/log/traefik/access.log -I traefik

# Pipe live from a running container
docker logs -f traefik | levv -i - -I traefik
```

**PostgreSQL**

```
levv -i /var/log/postgresql/postgresql-*.log -I postgresql

# Live tail via psql
tail -f /var/log/postgresql/postgresql-*.log | levv -i - -I postgresql
```

**MySQL**

```
levv -i /var/log/mysql/error.log -I mysql
```

**W3C Extended Log Format (IIS / Azure / CDN)**

```
levv -i /var/log/iis/u_ex*.log -I w3c
```

**GELF (Graylog)**

```
# Pipe from a Graylog-compatible log shipper
my-app --log-format=gelf | levv -i - -I gelf
```

**CEF (ArcSight / Splunk security logs)**

```
levv -i /var/log/security/events.cef -I cef
tail -f /var/log/security/events.cef | levv -i -
```

**CSV / TSV logs**

```
# With a header row — columns are auto-mapped by name
levv -i app.csv -I csv

# Tab-separated
levv -i events.tsv -I csv
```

**Docker — single container**

```
docker logs -f <container> | levv -i -

# Force the docker format if auto-detection picks the wrong parser
docker logs -f <container> | levv -i - -I docker
```

**Docker — multiple containers**

```
{ docker logs -f container1 & docker logs -f container2; } | levv -i -
```

**Docker Compose — all services**

```
docker compose logs -f | levv -i -
```

**Kubernetes**

```
# Single pod (requires --timestamps for time extraction)
kubectl logs -f <pod> --timestamps | levv -i - -I k8s

# All pods matching a label
kubectl logs -f -l app=myapp --timestamps | levv -i - -I k8s

# Previous (crashed) container
kubectl logs <pod> --previous --timestamps | levv -i - -I k8s
```

**Android logcat via ADB**

```
# Default — auto-detects logcat format
adb logcat | levv -i - -I logcat

# Threadtime format (recommended — includes PID/TID)
adb logcat -v threadtime | levv -i - -I logcat

# Clear buffer first so you only see new messages
adb logcat -c && adb logcat -v threadtime | levv -i - -I logcat

# Filter to a specific tag (warnings and above, silence everything else)
adb logcat MyApp:W *:S | levv -i - -I logcat

# Specific device when multiple are connected
adb -s <device-serial> logcat -v threadtime | levv -i - -I logcat
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

**Monitor multiple files together**

```
levv /var/log/syslog /var/log/auth.log /var/log/kern.log
levv -i /var/log/syslog,/var/log/auth.log
```

**Multiple files with per-file formats**

```
levv -i app.log,access.log -I json,www
```

**Write a normalised copy of the log to a file**

```
levv -i app.log -o normalised.log
```

**Open in a browser instead of the terminal**

```
levv /var/log/syslog -w
levv /dev/kmsg -w 9000
```

&nbsp;


---------------------------------------------------------------------
<h2 id="keyboard">Keyboard</h2>

| Key | Action |
|-----|--------|
| `LEFT` | Scroll backward in time |
| `RIGHT` | Scroll forward in time |
| `UP` | Zoom in (shrink the visible time window) |
| `DOWN` | Zoom out (expand the visible time window) |
| `PgUp` | Scroll event rows up |
| `PgDn` | Scroll event rows down |
| `s` | Resume auto-scroll (tracks current time) |
| `1`–`9` | **Single file:** set auto-scroll anchor (10 %–90 % of screen width) |
| `1`–`9` | **Multiple files:** show only messages from that file; press again to show all |
| `0` | **Multiple files:** show all files (clear file filter) |
| `l` | Cycle lines per event: 1 → 2 → 3 → 1 |
| `q` / `Esc` | Quit |

&nbsp;


---------------------------------------------------------------------
<h2 id="web-interface">Web Interface</h2>

![Web UI](https://raw.githubusercontent.com/wheresjames/levv/main/imgs/webview-kmsg.png)

&nbsp;

Add `-w` (or `--web`) to any command to start an HTTP server and open a
browser-based viewer instead of the terminal UI.  Press **Ctrl+C** in the
terminal to stop the server.

```
levv /var/log/syslog -w            # default port 8000
levv /dev/kmsg -w 9000             # custom port
levv app.log access.log -w         # multiple files
```

The browser interface mirrors the terminal UI: same timeline, same color
coding, same zoom/scroll controls.

| Control | Action |
|---------|--------|
| `◀` / `▶` buttons | Scroll backward / forward in time |
| `+` / `−` buttons | Zoom in / out |
| `⟳ Auto` button | Toggle auto-scroll to current time |
| Lines `1` / `2` / `3` buttons | Lines per event |
| File buttons | Filter by source file (multi-file only) |
| Mouse wheel | Zoom in / out |
| Click & drag | Scroll timeline |
| Scrollbar (right edge) | Scroll event rows up / down |
| `PgUp` / `PgDn` | Scroll event rows up / down |
| `s` | Resume auto-scroll |
| `l` | Cycle lines per event |
| `h` | Toggle help overlay |

&nbsp;


---------------------------------------------------------------------
<h2 id="input-formats">Input Formats</h2>

Pass a format name with `-I` / `--inputformat`, or let levv detect it automatically.
The active format is always shown in the top-right corner of the screen as `[fmt:name]`.
When monitoring multiple files with different formats, the label shows `[fmt:multi]`
unless a single file is selected with a digit key, in which case it shows that file's format.

When using multiple files, `-I` and `-T` accept comma-separated values — one per file
in the same order as `-i`, or a single value applied to all files:

```
levv -i app.log,access.log -I json,www
levv -i app.log,access.log -I auto        # auto-detect each file independently
```

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
| `apache-error` | Apache httpd error log (pre-2.4 and 2.4+ formats) |
| `python` | Python `logging` module (`basicConfig` and common formatters) |
| `log4j` | Log4j / Logback / Log4net (Java logging frameworks) |
| `postgresql` | PostgreSQL server log (`log_line_prefix` variants) |
| `mysql` | MySQL error log (5.x and 8.x formats) |
| `haproxy` | HAProxy access log (HTTP and TCP modes) |
| `traefik` | Traefik reverse proxy access logs (JSON and CLF-text modes) |
| `w3c` | W3C Extended Log Format (IIS, Azure, CDN access logs) |
| `gelf` | GELF (Graylog Extended Log Format) structured JSON logs |
| `cef` | CEF (Common Event Format) — ArcSight/Splunk security event logs |
| `logcat` | Android logcat (threadtime and brief formats) |
| `k8s` | Kubernetes `kubectl logs --timestamps` output |
| `csv` | CSV/TSV logs with auto-detected time, severity, and message columns |
| `pm2` | PM2 process manager log format |
| `time:` | Simple `<timestamp>: <message>` format |

&nbsp;


---------------------------------------------------------------------
<h2 id="auto-detection">Auto-Detection</h2>

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
<h2 id="regex-templates">Regex Templates</h2>

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
<h2 id="command-line">Command Line</h2>

```
usage: levv [-h] [-i INPUTFILE] [-I INPUTFORMAT] [-s SEPARATOR]
            [-T INPUTTEMPLATE] [-f FILTER] [-x EXCLUDE]
            [-o OUTPUTFILE] [-O OUTPUTFORMAT]
            [-r TIMERANGE] [-t TIME] [-R REFRESH]
            [-a AUTOSCROLL] [-l LINES]
            [-w [PORT]]
            [-m MAXMSGBUF] [-M MAXFILEREAD]
            [-k] [-D] [--listformats]
            [FILE ...]

Event monitor.

options:
  -h, --help                        show this help message and exit
  --listformats                     list all supported input formats and exit

Input:
  FILE                              One or more log files (space-separated positional arguments)
  -i, --inputfile INPUTFILE         Log file(s), comma-separated; use - for stdin
                                    (default: /var/log/syslog)
  -I, --inputformat INPUTFORMAT     Format(s), comma-separated — one per file or one for all
                                    (default: auto); see --listformats
  -s, --separator SEPARATOR         Record separator; default is CR/LF
  -T, --inputtemplate INPUTTEMPLATE Regex template(s), comma-separated — one per file or one for all
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
  -w, --web [PORT]                  Open browser-based viewer instead of terminal UI;
                                    optional PORT (default: 8000); press Ctrl+C to stop

Advanced:
  -m, --maxmsgbuf MAXMSGBUF         Maximum events to keep in memory (default: 5000)
  -M, --maxfileread MAXFILEREAD     Maximum bytes to read from file; 0 = all (default: 10000)
  -k, --keyboard                    Kept for compatibility; keyboard input is always enabled
  -D, --debug                       Show debug information
```

&nbsp;


---------------------------------------------------------------------
<h2 id="extending">Extending</h2>

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
<h2 id="testing">Testing</h2>

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
pytest test/test_bin.py     # bin/levv      — utility functions and parse_line dispatch
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
<h2 id="building-and-publishing">Building and publishing</h2>

**1. Install the build tools (once):**

```bash
pip3 install build twine
```

**2. Bump the version** in `levv/PROJECT.txt` — PyPI rejects uploads for a version that already exists.

**3. Build the package:**

```bash
python3 -m build
```

This creates a `dist/` folder containing a `.tar.gz` (source distribution) and a `.whl` (wheel).

**4. Upload to PyPI:**

```bash
twine upload dist/*
```

Twine will prompt for your PyPI username and password. The recommended approach is to use an API token: enter `__token__` as the username and your token as the password.

**Optional — test the upload first** using [TestPyPI](https://test.pypi.org) before publishing publicly:

```bash
twine upload --repository testpypi dist/*
```

**Optional — save credentials** to avoid being prompted each time by creating `~/.pypirc`:

```ini
[pypi]
username = __token__
password = pypi-your-token-here
```

&nbsp;

---------------------------------------------------------------------
<h2 id="references">References</h2>

- [levv on GitHub](https://github.com/wheresjames/levv)
- [levv on PyPI](https://pypi.org/project/levv/)
- [Python](https://www.python.org/)
- [pip](https://pip.pypa.io/en/stable/)
- [python-dateutil](https://dateutil.readthedocs.io/)
