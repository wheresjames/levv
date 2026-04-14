"""Logfmt key=value log format (common in Go: Prometheus, Loki, etc.)."""

import re
import time

import dateutil.parser

from .utils import calcPriority
from .json_lines import _TIME_KEYS, _SEV_KEYS, _MSG_KEYS, _SEV_MAP

NAME = 'logfmt'
DESCRIPTION = 'Logfmt key=value pairs (Prometheus, Loki, Go services)'
EXTENSIONS = []

_PAIR_RE = re.compile(r'(\w+)=("(?:[^"\\]|\\.)*"|\S+)')
_LOGFMT_HINT = re.compile(r'^\w+=\S')


def probe(line):
    if not _LOGFMT_HINT.match(line):
        return 0.0
    pairs = _PAIR_RE.findall(line)
    if len(pairs) < 2:
        return 0.0
    keys = {k for k, _ in pairs}
    # Confident if it has at least one recognised time/msg key
    if keys & set(_TIME_KEYS) | keys & set(_MSG_KEYS):
        return 0.85
    return 0.4


def _unquote(v):
    if v.startswith('"') and v.endswith('"'):
        return v[1:-1].replace('\\"', '"').replace('\\\\', '\\')
    return v


def parse(line):
    if not line:
        return {}

    pairs = {k: _unquote(v) for k, v in _PAIR_RE.findall(line)}
    if not pairs:
        return {}

    # Timestamp
    t = time.time()
    for key in _TIME_KEYS:
        if key in pairs:
            val = pairs[key]
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

    # Severity
    sev = None
    for key in _SEV_KEYS:
        if key in pairs:
            sev = _SEV_MAP.get(pairs[key].lower(), None)
            break

    # Message
    msg = None
    for key in _MSG_KEYS:
        if key in pairs:
            msg = pairs[key]
            break
    if msg is None:
        msg = line

    if sev is None:
        sev = calcPriority(msg)

    return {'time': t, 'sev': sev, 'msg': msg}
