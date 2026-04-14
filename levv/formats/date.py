"""Human-readable date prefix format."""

import re
import time

from .utils import findDate, calcPriority

NAME = 'date'
DESCRIPTION = 'Human-readable date/time prefix (e.g. "2024-01-15 10:23:01 message")'
EXTENSIONS = []

# Lightweight pre-check: line must start with something date-like
_DATE_HINT = re.compile(
    r'^(?:\d{4}[-/]\d{2}[-/]\d{2}'   # ISO date
    r'|[A-Z][a-z]{2}\s+\d{1,2}\s+'   # "Jan 15 "
    r'|\d{1,2}/[A-Z][a-z]{2}/\d{4})'  # "15/Jan/2024"
)


def probe(line):
    if _DATE_HINT.match(line):
        ln, _ = findDate(line)
        if ln > 0:
            return 0.75
    return 0.0


def parse(line):
    if not line:
        return {}

    ln, d = findDate(line)
    if ln <= 0:
        return {}

    try:
        ts = time.mktime(d.timetuple())
    except Exception:
        return {}

    msg = line[ln:].lstrip()
    return {'time': ts, 'msg': msg, 'sev': calcPriority(msg)}
