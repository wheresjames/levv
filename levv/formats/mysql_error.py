"""MySQL error log format.

Handles two eras:

  MySQL 5.7+ / 8.0   ISO-8601 timestamp + thread_id + [Level] + optional
                      [error-code] [subsystem] + message:
                        2024-01-15T10:23:45.123456Z 0 [Note] ready
                        2024-01-15T10:23:45.123456Z 0 [System] [MY-010116] [Server] msg

  Pre-5.7 compact     YYMMDD HH:MM:SS [Level] message:
                        240115 10:23:45 [Note] ready
"""

import re
import time

import dateutil.parser

NAME = 'mysql'
DESCRIPTION = 'MySQL error log (5.x and 8.x formats)'
EXTENSIONS = ['mysql.log', 'mysqld.log', 'mysql_error.log', 'error.log']

# Modern: ISO-8601 timestamp Z + thread id + [Level]
_MY_ISO_RE = re.compile(
    r'^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z?)\s+'
    r'(\d+)\s+'
    r'\[(System|Note|Warning|Error|ERROR)\]\s+'
    r'(?:\[MY-\d+\]\s+)?'      # optional error code  [MY-NNNNNN]
    r'(?:\[\w+\]\s+)?'         # optional subsystem   [Server]
    r'(.*)'
)

# Legacy compact: YYMMDD HH:MM:SS [Level] msg
_MY_OLD_RE = re.compile(
    r'^(\d{6}\s+\d{1,2}:\d{2}:\d{2})\s+'
    r'\[(Note|Warning|Error|ERROR)\]\s+(.*)'
)

_SEV_MAP = {
    'error': 1, 'ERROR': 1,
    'warning': 2,
    'system': 5, 'note': 6,
}


def probe(line):
    if _MY_ISO_RE.match(line) or _MY_OLD_RE.match(line):
        return 0.90
    return 0.0


def parse(line):
    m = _MY_ISO_RE.match(line)
    if m:
        ts, _tid, level, msg = m.groups()
        t = time.time()
        try:
            d = dateutil.parser.parse(ts)
            t = time.mktime(d.timetuple())
        except Exception:
            pass
        return {'time': t, 'sev': _SEV_MAP.get(level.lower(), 6), 'msg': msg}

    m = _MY_OLD_RE.match(line)
    if m:
        ts, level, msg = m.groups()
        t = time.time()
        try:
            d = dateutil.parser.parse(ts, fuzzy=True)
            t = time.mktime(d.timetuple())
        except Exception:
            pass
        return {'time': t, 'sev': _SEV_MAP.get(level.lower(), 6), 'msg': msg}

    return {}
