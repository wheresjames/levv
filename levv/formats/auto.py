"""Auto format — per-line heuristic cascade used when no format is specified."""

import time

from . import date as date_fmt
from .utils import calcPriority

NAME = 'auto'
DESCRIPTION = 'Auto-detect per line: Unix timestamp → human date → current time'
EXTENSIONS = []

# Seconds in a year — used for Unix timestamp plausibility check
_YEAR = 60 * 60 * 24 * 365


def probe(line):
    """Auto never wins a format election; it is the fallback."""
    return 0.0


def parse(line):
    if not line:
        return {}

    t = time.time()
    p = -1
    ok = False

    # 1. Try Unix timestamp float as first space-delimited token
    parts = line.split(' ', 1)
    if len(parts) == 2:
        try:
            _t = float(parts[0])
            if (t - _YEAR) < _t < (t + _YEAR):
                t = _t
                rest = parts[1]
                ok = True

                # Optional second token as numeric priority (1-99)
                parts2 = rest.split(' ', 1)
                if len(parts2) == 2:
                    try:
                        _p = int(parts2[0])
                        if 0 < _p < 100:
                            p = _p
                            rest = parts2[1]
                    except Exception:
                        pass
                line = rest
        except Exception:
            pass

    # 2. Fall back to human-readable date prefix
    if not ok:
        r = date_fmt.parse(line)
        if r:
            return r

    if p < 0:
        p = calcPriority(line)

    return {'time': t, 'sev': p, 'msg': line}
