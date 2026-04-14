"""JSON Lines (NDJSON) structured log format.

Handles output from Go zerolog/zap, Python structlog, Node pino, GCP, etc.
"""

import json
import time

import dateutil.parser

from .utils import calcPriority

NAME = 'json'
DESCRIPTION = 'JSON Lines / NDJSON structured logs (zerolog, zap, structlog, pino, …)'
EXTENSIONS = ['json', 'ndjson', 'jsonl']

_TIME_KEYS = ('timestamp', 'time', 'ts', '@timestamp', 'date', 'datetime', 't')
_SEV_KEYS = ('level', 'severity', 'sev', 'loglevel', 'log_level', 'lvl', 'priority', 'status')
_MSG_KEYS = ('message', 'msg', 'text', 'body', 'log', 'event', 'm', 'MESSAGE')

_SEV_MAP = {
    'fatal': 1, 'critical': 1, 'crit': 1,
    'error': 1, 'err': 1,
    'warn': 2, 'warning': 2,
    'notice': 5,
    'info': 6, 'information': 6,
    'debug': 6, 'trace': 6,
}


def probe(line):
    s = line.strip()
    if s.startswith('{') and s.endswith('}'):
        try:
            obj = json.loads(s)
            if isinstance(obj, dict):
                return 0.95
        except Exception:
            pass
    return 0.0


def parse(line):
    s = line.strip()
    if not s:
        return {}
    try:
        obj = json.loads(s)
    except Exception:
        return {}

    if not isinstance(obj, dict):
        return {}

    # Extract timestamp
    t = time.time()
    for key in _TIME_KEYS:
        if key in obj:
            val = obj[key]
            if isinstance(val, (int, float)):
                # Could be Unix seconds or Unix milliseconds
                candidate = float(val)
                # If > 1e10 assume milliseconds
                if candidate > 1e10:
                    candidate /= 1000.0
                t = candidate
                break
            if isinstance(val, str):
                try:
                    t = float(val)
                    if t > 1e10:
                        t /= 1000.0
                    break
                except ValueError:
                    pass
                try:
                    d = dateutil.parser.parse(val)
                    t = time.mktime(d.timetuple())
                    break
                except Exception:
                    pass

    # Extract severity
    sev = None
    for key in _SEV_KEYS:
        if key in obj:
            val = obj[key]
            if isinstance(val, int):
                # Syslog-style numeric: 0-7 where 0=emerg, 3=err, 6=info
                if 0 <= val <= 7:
                    from .syslog import _PRI_SEV
                    sev = _PRI_SEV.get(val, 6)
                else:
                    sev = 6
                break
            if isinstance(val, str):
                sev = _SEV_MAP.get(val.lower(), None)
                break

    # Extract message
    msg = None
    for key in _MSG_KEYS:
        if key in obj:
            msg = str(obj[key])
            break

    if msg is None:
        # Fall back to full JSON as message
        msg = s

    if sev is None:
        sev = calcPriority(msg)

    return {'time': t, 'sev': sev, 'msg': msg}
