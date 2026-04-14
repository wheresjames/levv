"""Log4j / Log4net / Logback log format (Java ecosystem)."""

import re
import time

import dateutil.parser

from .utils import calcPriority

NAME = 'log4j'
DESCRIPTION = 'Log4j/Logback/Log4net (Java logging frameworks)'
EXTENSIONS = []

# "2024-01-15 10:23:01,123 INFO  [main] com.example.App - message"
# "2024-01-15 10:23:01.123 INFO  [main] c.e.App - message"
_LOG4J = re.compile(
    r'^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}[.,]\d+)\s+'
    r'(TRACE|DEBUG|INFO|WARN|WARNING|ERROR|FATAL|SEVERE)\s+'
    r'\[([^\]]*)\]\s+'      # [thread]
    r'(\S+)\s+-\s+(.*)'    # logger - message
)

# Simpler variant without thread: "2024-01-15 10:23:01,123 INFO  logger - message"
_LOG4J_SIMPLE = re.compile(
    r'^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}[.,]\d+)\s+'
    r'(TRACE|DEBUG|INFO|WARN|WARNING|ERROR|FATAL|SEVERE)\s+'
    r'(\S+)\s+-\s+(.*)'
)

_SEV_MAP = {
    'fatal': 1, 'error': 1, 'severe': 1,
    'warn': 2, 'warning': 2,
    'info': 6, 'debug': 6, 'trace': 6,
}


def probe(line):
    if _LOG4J.match(line) or _LOG4J_SIMPLE.match(line):
        return 0.9
    return 0.0


def _parse_ts(ts_str):
    ts_str = ts_str.replace(',', '.')
    try:
        d = dateutil.parser.parse(ts_str)
        return time.mktime(d.timetuple())
    except Exception:
        return time.time()


def parse(line):
    m = _LOG4J.match(line)
    if m:
        ts, level, thread, logger, msg = m.groups()
        return {'time': _parse_ts(ts), 'sev': _SEV_MAP.get(level.lower(), 6), 'msg': msg}

    m = _LOG4J_SIMPLE.match(line)
    if m:
        ts, level, logger, msg = m.groups()
        return {'time': _parse_ts(ts), 'sev': _SEV_MAP.get(level.lower(), 6), 'msg': msg}

    return {}
