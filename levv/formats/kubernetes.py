"""Kubernetes kubectl log output (--timestamps flag).

When `kubectl logs --timestamps` is used, each line is prefixed with an
RFC3339Nano timestamp followed by a space and the original container output:

  2024-01-15T10:23:45.123456789Z <original container line>

Docker lines have the same ISO prefix but are followed by a stream token
("stdout"/"stderr") and a flag byte; this module deliberately scores lower
than the docker parser so Docker lines are handled by docker.py.
"""

import re
import time

import dateutil.parser

from .utils import calcPriority

NAME = 'k8s'
DESCRIPTION = 'Kubernetes kubectl logs --timestamps output'
EXTENSIONS = ['k8s.log', 'kubernetes.log']

# RFC3339Nano timestamp at start of line
_K8S_RE = re.compile(
    r'^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z)\s+(.*)'
)

# Docker lines start the same way but have "stdout F" or "stderr F" next
_DOCKER_HINT = re.compile(r'^(?:stdout|stderr)\s+\S\s+')


def probe(line):
    m = _K8S_RE.match(line)
    if m and not _DOCKER_HINT.match(m.group(2)):
        return 0.60
    return 0.0


def parse(line):
    m = _K8S_RE.match(line)
    if not m:
        return {}
    ts, msg = m.groups()
    if _DOCKER_HINT.match(msg):
        return {}
    t = time.time()
    try:
        d = dateutil.parser.parse(ts)
        t = time.mktime(d.timetuple())
    except Exception:
        pass
    return {'time': t, 'sev': calcPriority(msg), 'msg': msg}
