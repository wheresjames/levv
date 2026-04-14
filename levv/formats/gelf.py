"""GELF — Graylog Extended Log Format.

GELF is a JSON-based format with mandatory fields 'version', 'host', and
'short_message'.  Severity uses syslog levels 0–7 (lower = more severe),
same scale as the PRI field in syslog.  The existing json_lines parser
handles the field extraction but doesn't recognise 'short_message' or
apply GELF-specific level semantics; this module handles those correctly.
"""

import json
import time

import dateutil.parser

from .utils import calcPriority

NAME = 'gelf'
DESCRIPTION = 'GELF (Graylog Extended Log Format) structured JSON logs'
EXTENSIONS = ['gelf.log']

# GELF syslog-style severity: 0=EMERG … 7=DEBUG (lower is more severe)
_GELF_SEV = {0: 1, 1: 1, 2: 1, 3: 1, 4: 2, 5: 5, 6: 6, 7: 6}


def probe(line):
    s = line.strip()
    if not (s.startswith('{') and s.endswith('}')):
        return 0.0
    try:
        obj = json.loads(s)
        if not isinstance(obj, dict):
            return 0.0
        if 'short_message' in obj or 'full_message' in obj:
            return 0.95
        if 'version' in obj and 'host' in obj:
            return 0.70
    except Exception:
        pass
    return 0.0


def parse(line):
    s = line.strip()
    try:
        obj = json.loads(s)
    except Exception:
        return {}
    if not isinstance(obj, dict):
        return {}

    # Timestamp
    t = time.time()
    ts = obj.get('timestamp')
    if ts is not None:
        try:
            t = float(ts)
            if t > 1e10:
                t /= 1000.0
        except (ValueError, TypeError):
            try:
                d = dateutil.parser.parse(str(ts))
                t = time.mktime(d.timetuple())
            except Exception:
                pass

    # Severity (syslog 0–7)
    level = obj.get('level')
    if isinstance(level, int):
        sev = _GELF_SEV.get(level, 6)
    else:
        sev = None

    # Message — prefer short_message, fall back to full_message or message
    msg = (obj.get('short_message') or obj.get('full_message')
           or obj.get('message') or s)
    msg = str(msg)

    if sev is None:
        sev = calcPriority(msg)

    host = obj.get('host', '')
    if host:
        msg = f'[{host}] {msg}'

    return {'time': t, 'sev': sev, 'msg': msg}
