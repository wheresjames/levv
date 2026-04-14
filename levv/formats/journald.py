"""systemd journald — output of journalctl --output=short-iso."""

import re
import time

import dateutil.parser

from .utils import calcPriority

NAME = 'journald'
DESCRIPTION = 'systemd journald (journalctl --output=short-iso)'
EXTENSIONS = ['journal']

# "2024-01-15T10:23:01+0000 hostname proc[pid]: message"
_JD_RE = re.compile(
    r'^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{4})\s+'
    r'(\S+)\s+'
    r'(\S+?)(?:\[\d+\])?:\s*(.*)'
)

# Short variant without TZ offset (short format)
_JD_SHORT = re.compile(
    r'^(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\s+'
    r'(\S+)\s+'
    r'(\S+?)(?:\[\d+\])?:\s*(.*)'
)


def probe(line):
    if _JD_RE.match(line):
        return 0.9
    if _JD_SHORT.match(line):
        return 0.6  # overlaps with syslog; lower confidence
    return 0.0


def parse(line):
    for pattern in (_JD_RE, _JD_SHORT):
        m = pattern.match(line)
        if m:
            ts, host, unit, msg = m.groups()
            t = time.time()
            try:
                d = dateutil.parser.parse(ts)
                t = time.mktime(d.timetuple())
            except Exception:
                pass
            return {'time': t, 'sev': calcPriority(msg), 'msg': f'[{unit}] {msg}'}

    return {}
