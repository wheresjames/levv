"""Python standard-library logging module output."""

import re
import time

import dateutil.parser

from .utils import calcPriority

NAME = 'python'
DESCRIPTION = 'Python logging module (basicConfig and common formatters)'
EXTENSIONS = []

# Default basicConfig: "2024-01-15 10:23:01,123 LEVEL logger: message"
_PY_DEFAULT = re.compile(
    r'^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2},\d+)\s+'
    r'(DEBUG|INFO|WARNING|WARN|ERROR|CRITICAL|FATAL)\s+'
    r'(\S+?):\s+(.*)'
)

# Extended formatter: "2024-01-15 10:23:01,123 - logger - LEVEL - message"
_PY_EXTENDED = re.compile(
    r'^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2},\d+)\s+-\s+'
    r'(\S+?)\s+-\s+'
    r'(DEBUG|INFO|WARNING|WARN|ERROR|CRITICAL|FATAL)\s+-\s+(.*)'
)

_SEV_MAP = {
    'fatal': 1, 'critical': 1, 'error': 1,
    'warning': 2, 'warn': 2,
    'info': 6, 'debug': 6,
}


def probe(line):
    if _PY_DEFAULT.match(line) or _PY_EXTENDED.match(line):
        return 0.9
    return 0.0


def _parse_ts(ts_str):
    # Python uses comma for milliseconds separator
    ts_str = ts_str.replace(',', '.')
    try:
        d = dateutil.parser.parse(ts_str)
        return time.mktime(d.timetuple())
    except Exception:
        return time.time()


def parse(line):
    m = _PY_EXTENDED.match(line)
    if m:
        ts, logger, level, msg = m.groups()
        return {'time': _parse_ts(ts), 'sev': _SEV_MAP.get(level.lower(), 6), 'msg': msg}

    m = _PY_DEFAULT.match(line)
    if m:
        ts, level, logger, msg = m.groups()
        return {'time': _parse_ts(ts), 'sev': _SEV_MAP.get(level.lower(), 6), 'msg': msg}

    return {}
