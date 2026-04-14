"""Apache / nginx Combined Log Format (CLF) access logs."""

import re
import time
import shlex

import dateutil.parser

NAME = 'www'
DESCRIPTION = 'Apache/nginx Combined Log Format access logs'
EXTENSIONS = ['access.log', 'access_log']

# Quick structural probe: IP at start, bracket-delimited date field
_CLF_RE = re.compile(
    r'^\d{1,3}(?:\.\d{1,3}){3}\s'   # IPv4
    r'.*?\[[\w/: +-]+\]'            # [date field]
)


def probe(line):
    return 0.9 if _CLF_RE.match(line) else 0.0


def parse(line):
    try:
        d = shlex.split(line.replace('[', '"').replace(']', '"'))
    except ValueError:
        return {}

    if len(d) < 7:
        return {}

    ip = d[0]
    dt = d[3]
    ln = d[4]
    st = d[5]
    sz = d[6]

    t = time.time()
    if dt:
        try:
            parsed = dateutil.parser.parse(dt, fuzzy=True)
            if parsed:
                t = time.mktime(parsed.timetuple())
        except Exception:
            pass

    try:
        st = int(st)
    except Exception:
        st = 200

    if st >= 500:
        sev = 1
    elif st >= 400:
        sev = 2
    elif st >= 300:
        sev = 3
    else:
        sev = 6

    return {'sev': sev, 'time': t, 'msg': f'{ip} : {st} : {sz} : {ln}'}
