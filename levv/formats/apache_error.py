"""Apache httpd error log format.

Handles two distinct timestamp styles:
  Pre-2.4 : [Mon Jan 15 10:23:45 2024] [error] [client 1.2.3.4] msg
  2.4+     : [Mon Jan 15 10:23:45.123456 2024] [core:error] [pid 1234] msg
"""

import re
import time

import dateutil.parser

from .utils import calcPriority

NAME = 'apache-error'
DESCRIPTION = 'Apache httpd error log (pre-2.4 and 2.4+ formats)'
EXTENSIONS = ['apache2/error.log', 'httpd/error_log']

# Apache 2.4+: [Weekday Mon DD HH:MM:SS.usec YYYY] [module:level] [pid N] …
_V24_RE = re.compile(
    r'^\[(\w{3}\s+\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}(?:\.\d+)?\s+\d{4})\]\s+'
    r'\[\w[\w.]*:(\w+)\]\s+'
    r'\[pid\s+\d+(?::tid\s+\d+)?\]\s+'
    r'(.*)'
)

# Pre-2.4: [Weekday Mon DD HH:MM:SS YYYY] [level] [client x.x.x.x] msg
_PRE24_RE = re.compile(
    r'^\[(\w{3}\s+\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}(?:\.\d+)?\s+\d{4})\]\s+'
    r'\[(\w+)\]\s+'
    r'(?:\[client\s+[\d.:a-fA-F\[\]]+(?::\d+)?\]\s+)?'
    r'(.*)'
)

_SEV_MAP = {
    'emerg': 1, 'alert': 1, 'crit': 1, 'error': 1,
    'warn': 2, 'notice': 5, 'info': 6, 'debug': 6,
}

_CLIENT_RE = re.compile(r'^\[client\s+[\d.:a-fA-F\[\]]+(?::\d+)?\]\s+')


def probe(line):
    if _V24_RE.match(line) or _PRE24_RE.match(line):
        return 0.95
    return 0.0


def _parse_ts(ts):
    try:
        d = dateutil.parser.parse(ts, fuzzy=True)
        return time.mktime(d.timetuple())
    except Exception:
        return time.time()


def parse(line):
    m = _V24_RE.match(line)
    if m:
        ts, level, msg = m.groups()
        msg = _CLIENT_RE.sub('', msg)
        sev = _SEV_MAP.get(level.lower(), calcPriority(msg))
        return {'time': _parse_ts(ts), 'sev': sev, 'msg': msg}

    m = _PRE24_RE.match(line)
    if m:
        ts, level, msg = m.groups()
        sev = _SEV_MAP.get(level.lower(), calcPriority(msg))
        return {'time': _parse_ts(ts), 'sev': sev, 'msg': msg}

    return {}
