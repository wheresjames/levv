"""Shared utilities for log format parsers."""

import time
import warnings
import dateutil.parser


def findDate(txt):
    """Scan *txt* for the longest leading substring parseable as a date.

    Returns (length, datetime) or (0, 0) if no date is found.
    """
    max_len = min(len(txt), 40)
    fm = 0
    fd = 0

    while 8 <= max_len:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                d = dateutil.parser.parse(txt[:max_len])
            if fd and d != fd:
                return fm, fd
            fm = max_len
            fd = d
        except Exception:
            pass
        max_len -= 1

    if not fd:
        return 0, 0
    return fm, fd


def parse_time_str(s):
    """Parse *s* as a Unix timestamp (float) or a date string.

    Returns a float epoch or None on failure.
    """
    try:
        return float(s)
    except (ValueError, TypeError):
        pass
    try:
        d = dateutil.parser.parse(s, fuzzy=True)
        if d:
            return time.mktime(d.timetuple())
    except Exception:
        pass
    return None


def calcPriority(s):
    """Map keywords in *s* to a severity level (1 = critical … 6 = normal)."""
    sl = s.lower()
    if any(w in sl for w in ('fatal', 'critical', 'crit', 'error', 'err')):
        return 1
    if any(w in sl for w in ('warn', 'warning')):
        return 2
    if 'notice' in sl:
        return 5
    return 6
