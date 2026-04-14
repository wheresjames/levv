"""PostgreSQL server log format.

Handles the most common log_line_prefix variants:
  %t [%p]             → 2024-01-15 10:23:45.123 UTC [1234] LOG:  msg
  %t [%p] %u@%d       → 2024-01-15 10:23:45.123 UTC [1234] user@db LOG:  msg
  %m [%p]             → same but with millisecond timestamp
"""

import re
import time

import dateutil.parser

NAME = 'postgresql'
DESCRIPTION = 'PostgreSQL server log (log_line_prefix variants)'
EXTENSIONS = ['postgresql.log', 'pgsql.log', 'postgres.log', 'postgresql-*.log']

# ISO timestamp + optional timezone + [pid] + optional user@db + LEVEL:
_PG_RE = re.compile(
    r'^(\d{4}-\d{2}-\d{2}[\sT]\d{2}:\d{2}:\d{2}(?:\.\d+)?)\s*'
    r'(?:[A-Z]{2,5}\s+)?'               # optional TZ abbreviation (UTC, EST, …)
    r'\[(\d+)\]\s+'                     # [pid]
    r'(?:\S+@\S+\s+)?'                  # optional user@db
    r'(LOG|ERROR|WARNING|NOTICE|INFO|DEBUG\d?|FATAL|PANIC'
    r'|DETAIL|HINT|STATEMENT|CONTEXT|LOCATION):\s+'
    r'(.*)'
)

_SEV_MAP = {
    'panic': 1, 'fatal': 1, 'error': 1,
    'warning': 2,
    'notice': 5, 'info': 5,
    'log': 6, 'statement': 6, 'detail': 6,
    'hint': 6, 'context': 6, 'location': 6,
}


def probe(line):
    return 0.95 if _PG_RE.match(line) else 0.0


def parse(line):
    m = _PG_RE.match(line)
    if not m:
        return {}
    ts, pid, level, msg = m.groups()
    t = time.time()
    try:
        d = dateutil.parser.parse(ts)
        t = time.mktime(d.timetuple())
    except Exception:
        pass
    # DEBUG1 … DEBUG5 → normalise key
    sev_key = 'debug' if level.startswith('DEBUG') else level.lower()
    sev = _SEV_MAP.get(sev_key, 6)
    return {'time': t, 'sev': sev, 'msg': f'[pid:{pid}] {msg}'}
