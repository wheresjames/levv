"""Android logcat log format.

Supports two common output formats:

  Threadtime  MM-DD HH:MM:SS.mmm  PID  TID  L Tag  : msg
  Brief       L/Tag(PID): msg

Threadtime is the default for `adb logcat -v threadtime` and is the most
common format seen in captured logs.  Brief is the legacy default.
"""

import re
import time

import dateutil.parser

NAME = 'logcat'
DESCRIPTION = 'Android logcat (threadtime and brief formats)'
EXTENSIONS = ['logcat.log', 'logcat', 'android.log']

# Threadtime: "01-15 10:23:45.123  1234  5678 D TagName  : msg"
# Optional 4-digit year prefix: "2024-01-15 10:23:45.123 ..."
_THREADTIME_RE = re.compile(
    r'^(\d{2,4}-\d{2}(?:-\d{2})?\s+\d{2}:\d{2}:\d{2}\.\d+)\s+'
    r'\d+\s+\d+\s+'
    r'([VDIWEFA])\s+'
    r'([\w./ -]+?):\s+'
    r'(.*)'
)

# Brief: "D/TagName(1234): msg"
_BRIEF_RE = re.compile(
    r'^([VDIWEFA])/(\S+?)\(\s*(\d+)\):\s+(.*)'
)

_SEV_MAP = {
    'V': 6, 'D': 6, 'I': 6,
    'W': 2, 'E': 1, 'F': 1, 'A': 1,
}


def probe(line):
    if _THREADTIME_RE.match(line):
        return 0.90
    if _BRIEF_RE.match(line):
        return 0.85
    return 0.0


def parse(line):
    m = _THREADTIME_RE.match(line)
    if m:
        ts, level, tag, msg = m.groups()
        t = time.time()
        # Prepend current year when only month-day is present
        if re.match(r'^\d{2}-\d{2}\s', ts):
            ts = f'{time.strftime("%Y")}-{ts}'
        try:
            d = dateutil.parser.parse(ts, fuzzy=True)
            t = time.mktime(d.timetuple())
        except Exception:
            pass
        return {'time': t, 'sev': _SEV_MAP.get(level, 6), 'msg': f'[{tag.strip()}] {msg}'}

    m = _BRIEF_RE.match(line)
    if m:
        level, tag, pid, msg = m.groups()
        return {'time': time.time(), 'sev': _SEV_MAP.get(level, 6), 'msg': f'[{tag}({pid})] {msg}'}

    return {}
