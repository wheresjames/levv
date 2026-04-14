"""Syslog formats — RFC 3164 and the common /var/log/syslog variant."""

import re
import time
import warnings

import dateutil.parser

from .utils import calcPriority

NAME = 'syslog'
DESCRIPTION = 'Syslog (RFC 3164/5424 and /var/log/syslog variants)'
EXTENSIONS = ['syslog', 'messages', 'kern.log', 'auth.log', 'daemon.log', 'user.log']

# RFC 3164: optional <PRI> then BSD timestamp "Mmm dd HH:MM:SS"
_BSD_TS = re.compile(
    r'^(?:<\d+>)?'                          # optional <PRI>
    r'([A-Z][a-z]{2}\s+\d{1,2}\s+'         # "Jan  5 " or "Jan 15 "
    r'\d{2}:\d{2}:\d{2})\s+'               # HH:MM:SS
    r'(\S+)\s+'                             # hostname
    r'(\S+?)(?:\[\d+\])?:\s*(.*)'          # proc[pid]: msg
)

# RFC 5424: <PRI>VERSION ISO-TIMESTAMP HOST APP PID MSGID STRUCTURED MSG
_RFC5424 = re.compile(
    r'^<(\d+)>1\s+'
    r'(\d{4}-\d{2}-\d{2}T[\d:.]+(?:Z|[+-]\d{2}:\d{2})?)\s+'
    r'(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(.*)'
)

# PRI field → syslog severity (lower = more severe)
_PRI_SEV = {0: 1, 1: 1, 2: 1, 3: 1, 4: 2, 5: 5, 6: 6, 7: 6}


def _pri_to_sev(pri_str):
    try:
        facility_sev = int(pri_str) & 0x07
        return _PRI_SEV.get(facility_sev, 6)
    except Exception:
        return 6


def probe(line):
    if _RFC5424.match(line):
        return 0.95
    if _BSD_TS.match(line):
        return 0.85
    return 0.0


def parse(line):
    # RFC 5424
    m = _RFC5424.match(line)
    if m:
        pri, ts, host, app, pid, mid, sd, msg = m.groups()
        t = time.time()
        try:
            d = dateutil.parser.parse(ts)
            t = time.mktime(d.timetuple())
        except Exception:
            pass
        sev = _pri_to_sev(pri)
        if sev == 6:
            sev = calcPriority(msg)
        return {'time': t, 'sev': sev, 'msg': f'[{app}] {msg}'}

    # RFC 3164 / BSD syslog
    m = _BSD_TS.match(line)
    if m:
        ts, host, proc, msg = m.groups()
        t = time.time()
        try:
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                d = dateutil.parser.parse(ts, default=_default_date())
            t = time.mktime(d.timetuple())
        except Exception:
            pass
        # Extract PRI if present
        pri_m = re.match(r'^<(\d+)>', line)
        sev = _pri_to_sev(pri_m.group(1)) if pri_m else calcPriority(msg)
        return {'time': t, 'sev': sev, 'msg': f'[{proc}] {msg}'}

    return {}


def _default_date():
    """dateutil default: use current year/month so BSD timestamps parse correctly."""
    from datetime import datetime
    now = datetime.now()
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
