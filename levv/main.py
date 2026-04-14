#!/usr/bin/env python3

import re
import time
import dateutil.parser

try:
    import sparen
    Log = sparen.log
except Exception as e:
    Log = print

# ---------------------------------------------------------------------------
# Re-export shared utilities so callers that do ``import levv`` keep working
# ---------------------------------------------------------------------------
from levv.formats.utils import findDate, calcPriority, parse_time_str  # noqa: F401
from levv.formats import parse_line, detect_format, list_formats        # noqa: F401


# ---------------------------------------------------------------------------
# Built-in regex templates (used by the -I / --inputformat flag when the
# format name maps to a regex rather than a dedicated parser module)
# ---------------------------------------------------------------------------

_TEMPLATES = {
    'time:': r'(?P<time>.*?): (?P<msg>.*)',
    'pm2':   r'(?P<sev>.*?)\|.*?\|(?P<time>.*?): (?P<msg>.*)',
}


def getLogTemplate(ty):
    """Return a named regex template string, or None if *ty* is not a template."""
    return _TEMPLATES.get(ty)


# ---------------------------------------------------------------------------
# filterLine — apply a regex template to a raw log line
# ---------------------------------------------------------------------------

def filterLine(fstr, s):

    if not len(s):
        return {}, ''

    if not len(fstr):
        return {}, s

    try:
        m = re.match(fstr, s)
        if not m:
            return {}, ''

        g = m.groupdict()
        if not g:
            g = {}

        # Positional groups as fallback
        try:
            for i in range(1, 10):
                g[str(i)] = m.group(i)
        except Exception:
            pass

        r = {}

        # Message
        if 'msg' in g:
            s = g['msg']
            r['msg'] = s
        elif '1' in g:
            s = g['1']
            r['msg'] = s

        if not len(s):
            return {}, ''

        # Time
        if 'time' in g:
            r['time'] = g['time']
        elif '2' in g:
            r['time'] = g['2']

        # Severity
        if 'sev' in g:
            r['sev'] = g['sev']
        elif '3' in g:
            r['sev'] = g['3']

        # Parse time value
        if 'time' in r:
            try:
                r['time'] = float(r['time'])
            except Exception:
                try:
                    d = dateutil.parser.parse(r['time'], fuzzy=True)
                    if d:
                        r['time'] = time.mktime(d.timetuple())
                    else:
                        del r['time']
                except Exception:
                    del r['time']

            if 'time' in r:
                try:
                    if 'nsecs' in g:
                        r['time'] += float('0.%09d' % int(g['nsecs']))
                    if 'usecs' in g:
                        r['time'] += float('0.%06d' % int(g['usecs']))
                    if 'msecs' in g:
                        r['time'] += float('0.%03d' % int(g['msecs']))
                except Exception:
                    pass

        # Parse severity value
        if 'sev' in r:
            try:
                r['sev'] = int(r['sev'])
            except Exception:
                r['sev'] = calcPriority(s)

        return r, s

    except Exception:
        pass

    return {}, ''
