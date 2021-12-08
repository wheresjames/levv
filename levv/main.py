#!/usr/bin/env python3

import re
import time
import dateutil.parser

try:
    import sparen
    Log = sparen.log
except Exception as e:
    Log = print


def getLogTemplate(ty):
    tmpls = {
        'time:': '(?P<time>.*?): (?P<msg>.*)',
        'pm2': '(?P<sev>.*?)\|.*?\|(?P<time>.*?): (?P<msg>.*)'
    }
    if ty in tmpls:
        return tmpls[ty]
    return None


def calcPriority(s):
    if 0 <= s.lower().find('error'):
        return 1
    elif 0 <= s.lower().find('warn'):
        return 2
    return 6


def filterLine(fstr, s):

    if not len(s):
        return {}, ''

    # Do we have a filter?
    if not len(fstr):
        return {}, s

    try:

        # Apply filter
        m = re.match(fstr, s)

        if not m:
            return {}, ''

        # Grab the results
        g = m.groupdict()
        if not g:
            g = {}

        # Stuff integer values into dictionary
        try:
            for i in range(1, 10):
                g[str(i)] = m.group(i)
        except:
            pass

        r = {}

        # Message
        if 'msg' in g:
            s = g['msg']
            r['msg'] = s
        elif '1' in g:
            s = g['1']
            r['msg'] = s

        # Punt if we didn't get a message
        if not len(s):
            return {}, ''

        # Did we get a time?
        if 'time' in g:
            r['time'] = g['time']
        elif '2' in g:
            r['time'] = g['2']

        # Did we get a severity?
        if 'sev' in g:
            r['sev'] = g['sev']
        elif '3' in g:
            r['sev'] = g['3']

        # Process time
        if 'time' in r:
            try:
                r['time'] = float(r['time'])
            except:
                try:
                    d = dateutil.parser.parse(r['time'], fuzzy=True)
                    if d:
                        r['time'] = time.mktime(d.timetuple())
                    else:
                        del r['time']
                except Exception as e:
                    del r['time']

            # fractional seconds
            if 'time' in r:
                try:
                    if 'nsecs' in g:
                        r['time'] += float("0.%09d" % int(g['nsecs']))
                    if 'usecs' in g:
                        r['time'] += float("0.%06d" % int(g['nsecs']))
                    if 'msecs' in g:
                        r['time'] += float("0.%03d" % int(g['nsecs']))
                except:
                    pass

        # Process severity
        if 'sev' in r:
            try:
                r['sev'] = int(r['sev'])
            except:
                r['sev'] = calcPriority(s)

        return r, s

    except Exception as e:
        pass

    return {}, ''

