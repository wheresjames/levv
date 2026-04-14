"""HAProxy access log format (HTTP and TCP modes).

Lines may arrive with or without a syslog header prefix.  The distinctive
fingerprint is an IP:port client address followed by a CLF-style timestamp
in brackets, then frontend/backend names and slash-separated timings.
"""

import re
import time

import dateutil.parser

NAME = 'haproxy'
DESCRIPTION = 'HAProxy access log (HTTP and TCP modes)'
EXTENSIONS = ['haproxy.log']

# CLF timestamp inside brackets: [15/Jan/2024:10:23:45.123]
_CLF_TS_RE = re.compile(
    r'\[(\d{2}/\w{3}/\d{4}:\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:\s*[+-]\d{4})?)\]'
)

# Full HAProxy HTTP-mode line (optional syslog prefix stripped via search)
_HAPROXY_RE = re.compile(
    r'(\d[\d.:a-fA-F\[\]]+:\d+|-)\s+'   # client IP:port (or '-')
    r'(\[[\w/: .+-]+\])\s+'              # [timestamp]
    r'(\S+)\s+'                          # frontend
    r'(\S+)\s+'                          # backend/server
    r'[\d/-]+\s+'                        # timings (slashes or dashes)
    r'(\d+)\s+'                          # status code
    r'(\d+)'                             # bytes
)

# Fast probe: look for "haproxy[pid]:" OR "client:port [clftime]" pattern
_PROBE_RE = re.compile(
    r'haproxy\[\d+\]:\s+\d'
    r'|'
    r'^\d[\d.]+:\d+\s+\[\d{2}/\w{3}/\d{4}:'
)


def probe(line):
    return 0.90 if _PROBE_RE.search(line) else 0.0


def parse(line):
    m = _HAPROXY_RE.search(line)
    if not m:
        return {}

    client, ts_bracket, frontend, backend, status, size = m.groups()

    t = time.time()
    ts_m = _CLF_TS_RE.search(ts_bracket)
    if ts_m:
        raw = ts_m.group(1)
        # "15/Jan/2024:10:23:45.123" → dateutil-parseable
        normalised = raw.replace('/', '-', 1).replace('/', ' ', 1).replace(':', ' ', 1)
        try:
            d = dateutil.parser.parse(raw.replace('/', ' '), fuzzy=True)
            t = time.mktime(d.timetuple())
        except Exception:
            pass

    try:
        sc = int(status)
    except (ValueError, TypeError):
        sc = 0

    if sc >= 500:
        sev = 1
    elif sc >= 400:
        sev = 2
    elif sc >= 300:
        sev = 3
    elif sc > 0:
        sev = 6
    else:
        sev = 6

    msg = f'{client} -> {frontend}/{backend} : {status} : {size}b'
    return {'time': t, 'sev': sev, 'msg': msg}
