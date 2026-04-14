"""Linux kernel ring-buffer format (/dev/kmsg)."""

import re
import time

import psutil

NAME = 'kmsg'
DESCRIPTION = 'Linux kernel messages — sev,seq,usec_offset,flags;message'
EXTENSIONS = ['kmsg']

_KMSG_RE = re.compile(r'^\d+,\d+,\d+,[^;]*;')


def probe(line):
    return 0.9 if _KMSG_RE.match(line) else 0.0


def parse(line):
    d = line.split(',')
    if len(d) < 4:
        return {}

    try:
        boot = float(psutil.boot_time()) or time.time()
        offset_sec = float(d[2]) / 1_000_000.0
        # Message starts after the first ';'
        msg = line.split(';', 1)[1] if ';' in line else d[3]
        return {
            'sev': d[0],
            'seq': d[1],
            'offset': d[2],
            'time': offset_sec + boot,
            'msg': msg,
        }
    except Exception:
        return {}
