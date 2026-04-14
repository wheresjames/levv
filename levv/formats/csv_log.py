"""CSV / TSV log format with auto-detected column roles.

On the first line the parser checks for a recognised header (field names
matching known time / severity / message keywords).  If a header is found
it is used to map columns; otherwise column roles are inferred from the
content of the first data row.

Module-level state caches the column mapping across calls so detection
only runs once per file.  Call ``_reset()`` to start fresh (e.g. between
files or in tests).
"""

import csv
import io
import re
import time

import dateutil.parser

from .utils import calcPriority

NAME = 'csv'
DESCRIPTION = 'CSV/TSV logs with auto-detected time, severity, and message columns'
EXTENSIONS = ['csv', 'tsv']

_TIME_NAMES = frozenset({'time', 'timestamp', 'ts', 'date', 'datetime',
                         'when', '@timestamp', 'event_time', 'log_time'})
_SEV_NAMES  = frozenset({'level', 'severity', 'sev', 'loglevel', 'log_level',
                         'lvl', 'priority', 'status'})
_MSG_NAMES  = frozenset({'message', 'msg', 'text', 'body', 'log', 'event',
                         'description', 'detail', 'content'})

_SEV_MAP = {
    'fatal': 1, 'critical': 1, 'crit': 1,
    'error': 1, 'err': 1,
    'warn': 2, 'warning': 2,
    'notice': 5,
    'info': 6, 'information': 6,
    'debug': 6, 'trace': 6,
}

# --- Module-level column state ---
_delimiter    = ','
_col_time     = None
_col_sev      = None
_col_msg      = None
_header_done  = False   # True once we've processed the first line


def _reset():
    """Reset per-file state.  Called externally between files / in tests."""
    global _delimiter, _col_time, _col_sev, _col_msg, _header_done
    _delimiter   = ','
    _col_time    = None
    _col_sev     = None
    _col_msg     = None
    _header_done = False


def _best_delimiter(line):
    counts = {d: line.count(d) for d in (',', '\t', ';', '|')}
    best = max(counts, key=counts.get)
    return best if counts[best] > 0 else ','


def _split(line, delim):
    try:
        rows = list(csv.reader(io.StringIO(line), delimiter=delim))
        return rows[0] if rows else []
    except Exception:
        return line.split(delim)


def _is_header(fields):
    for f in fields:
        if f.strip().lower() in _TIME_NAMES | _SEV_NAMES | _MSG_NAMES:
            return True
    return False


def _cols_from_header(fields):
    ti = si = mi = None
    for i, f in enumerate(fields):
        fl = f.strip().lower()
        if ti is None and fl in _TIME_NAMES:
            ti = i
        elif si is None and fl in _SEV_NAMES:
            si = i
        elif mi is None and fl in _MSG_NAMES:
            mi = i
    return ti, si, mi


def _cols_from_data(fields):
    ti = si = mi = None
    for i, f in enumerate(fields):
        v = f.strip()
        if ti is None:
            # Unix epoch
            try:
                fv = float(v)
                if 1e9 < fv < 2e10:
                    ti = i
                    continue
            except ValueError:
                pass
            # ISO date prefix
            if re.match(r'\d{4}-\d{2}-\d{2}', v) or re.match(r'\d{2}/\d{2}/\d{4}', v):
                ti = i
                continue
        if si is None and v.lower() in _SEV_MAP:
            si = i
            continue
    # Last field as message fallback
    if mi is None and len(fields) > 0:
        mi = len(fields) - 1
    return ti, si, mi


def probe(line):
    s = line.strip()
    if not s or s.startswith('#'):
        return 0.0
    delim = _best_delimiter(s)
    fields = _split(s, delim)
    if len(fields) < 2:
        return 0.0
    if _is_header(fields):
        return 0.70
    # Multiple fields and at least one looks like a timestamp
    for f in fields:
        v = f.strip()
        if re.match(r'\d{4}-\d{2}-\d{2}', v):
            return 0.60
        try:
            fv = float(v)
            if 1e9 < fv < 2e10:
                return 0.55
        except ValueError:
            pass
    if len(fields) >= 3:
        return 0.30
    return 0.0


def parse(line):
    global _delimiter, _col_time, _col_sev, _col_msg, _header_done

    s = line.strip()
    if not s or s.startswith('#'):
        return {}

    if not _header_done:
        _delimiter = _best_delimiter(s)

    fields = _split(s, _delimiter)
    if len(fields) < 2:
        return {}

    if not _header_done:
        _header_done = True
        if _is_header(fields):
            _col_time, _col_sev, _col_msg = _cols_from_header(fields)
            return {}   # header row is not an event
        else:
            _col_time, _col_sev, _col_msg = _cols_from_data(fields)

    def _get(idx):
        if idx is not None and 0 <= idx < len(fields):
            return fields[idx].strip()
        return None

    time_val = _get(_col_time)
    sev_val  = _get(_col_sev)
    msg_val  = _get(_col_msg)

    # Parse timestamp
    t = time.time()
    if time_val:
        try:
            t = float(time_val)
            if t > 1e10:
                t /= 1000.0
        except ValueError:
            try:
                d = dateutil.parser.parse(time_val, fuzzy=True)
                t = time.mktime(d.timetuple())
            except Exception:
                pass

    # Parse severity
    sev = 6
    if sev_val:
        mapped = _SEV_MAP.get(sev_val.lower())
        if mapped is not None:
            sev = mapped
        else:
            try:
                sc = int(sev_val)
                sev = 1 if sc >= 500 else (2 if sc >= 400 else 6)
            except ValueError:
                sev = calcPriority(sev_val)

    msg = msg_val if msg_val else ','.join(fields)

    if sev == 6:
        sev = calcPriority(msg)

    return {'time': t, 'sev': sev, 'msg': msg}
