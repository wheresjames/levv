"""Docker container log format (docker logs / log-driver=json-file stdout lines)."""

import re
import time

import dateutil.parser

from .utils import calcPriority

NAME = 'docker'
DESCRIPTION = 'Docker log lines — ISO-8601 timestamp + stream + flag + message'
EXTENSIONS = []

# "2024-01-15T10:23:01.123456789Z stdout F message"
_DOCKER_RE = re.compile(
    r'^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z?(?:[+-]\d{2}:\d{2})?)\s+'
    r'(stdout|stderr)\s+\S\s+(.*)'
)

# Fallback: just ISO timestamp at start (some drivers omit stream/flag)
_ISO_TS = re.compile(
    r'^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z)\s+(.*)'
)


def probe(line):
    if _DOCKER_RE.match(line):
        return 0.95
    return 0.0


def parse(line):
    m = _DOCKER_RE.match(line)
    if m:
        ts, stream, msg = m.groups()
        t = time.time()
        try:
            d = dateutil.parser.parse(ts)
            t = time.mktime(d.timetuple())
        except Exception:
            pass
        # stderr lines are more likely to be errors
        sev = calcPriority(msg)
        if stream == 'stderr' and sev == 6:
            sev = 2
        return {'time': t, 'sev': sev, 'msg': msg}

    return {}
