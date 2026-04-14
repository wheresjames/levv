"""nginx error log format."""

import re
import time

import dateutil.parser

from .utils import calcPriority

NAME = 'nginx-error'
DESCRIPTION = 'nginx error log (2024/01/15 10:23:01 [level] pid#tid: message)'
EXTENSIONS = ['error.log', 'error_log']

# "2024/01/15 10:23:01 [error] 1234#5678: *99 message"
_NGINX_ERR = re.compile(
    r'^(\d{4}/\d{2}/\d{2}\s+\d{2}:\d{2}:\d{2})\s+'
    r'\[(\w+)\]\s+'
    r'\d+#\d+:\s+(.*)'
)

_SEV_MAP = {
    'emerg': 1, 'alert': 1, 'crit': 1, 'error': 1,
    'warn': 2, 'notice': 5, 'info': 6, 'debug': 6,
}


def probe(line):
    return 0.95 if _NGINX_ERR.match(line) else 0.0


def parse(line):
    m = _NGINX_ERR.match(line)
    if not m:
        return {}

    ts, level, msg = m.groups()
    t = time.time()
    try:
        d = dateutil.parser.parse(ts)
        t = time.mktime(d.timetuple())
    except Exception:
        pass

    sev = _SEV_MAP.get(level.lower(), calcPriority(msg))
    return {'time': t, 'sev': sev, 'msg': msg}
