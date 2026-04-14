"""W3C Extended Log Format — IIS, Azure, CDN access logs.

Lines starting with '#' are directives; '#Fields:' sets column order.
Data lines are space-separated values matching the declared field list.
"""

import re
import time

import dateutil.parser

NAME = 'w3c'
DESCRIPTION = 'W3C Extended Log Format (IIS, Azure, CDN access logs)'
EXTENSIONS = []

_FIELDS_RE = re.compile(r'^#Fields:\s+(.*)', re.IGNORECASE)

# Module-level column state updated by '#Fields:' directives.
_fields = []


def probe(line):
    s = line.strip()
    if _FIELDS_RE.match(s):
        return 0.95
    if re.match(r'^#(?:Version|Software|Date|Start-Date|End-Date):', s, re.IGNORECASE):
        return 0.80
    if s.startswith('#'):
        return 0.0
    # Data line heuristic: starts with YYYY-MM-DD and has many space-separated tokens
    parts = s.split()
    if len(parts) >= 4 and re.match(r'^\d{4}-\d{2}-\d{2}$', parts[0]):
        return 0.70
    return 0.0


def parse(line):
    global _fields
    s = line.strip()
    if not s:
        return {}

    # Handle directives
    m = _FIELDS_RE.match(s)
    if m:
        _fields = m.group(1).split()
        return {}
    if s.startswith('#'):
        return {}

    parts = s.split()
    if not parts:
        return {}

    # Build field map; lower-case keys for case-insensitive lookup
    fmap = {name.lower(): val for name, val in zip(_fields, parts)}

    # Timestamp
    t = time.time()
    date_val = fmap.get('date', '')
    time_val = fmap.get('time', '')
    if date_val and time_val:
        try:
            d = dateutil.parser.parse(f'{date_val} {time_val}')
            t = time.mktime(d.timetuple())
        except Exception:
            pass
    elif date_val:
        try:
            d = dateutil.parser.parse(date_val)
            t = time.mktime(d.timetuple())
        except Exception:
            pass

    # Status code → severity
    status_raw = fmap.get('sc-status', fmap.get('s-status', fmap.get('status', '')))
    try:
        sc = int(status_raw)
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

    # Message
    method   = fmap.get('cs-method', fmap.get('cs(method)', ''))
    uri_stem = fmap.get('cs-uri-stem', fmap.get('cs-uri', '-'))
    uri_qry  = fmap.get('cs-uri-query', '')
    client   = fmap.get('c-ip', '-')
    sent     = fmap.get('sc-bytes', fmap.get('bytes', '-'))

    uri = uri_stem
    if uri_qry and uri_qry != '-':
        uri = f'{uri_stem}?{uri_qry}'

    if method and uri_stem:
        msg = f'{client} : {method} {uri} : {status_raw} : {sent}b'
    else:
        msg = s

    return {'time': t, 'sev': sev, 'msg': msg}
