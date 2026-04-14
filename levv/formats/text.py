"""Plain-text format — no timestamp extraction; every line stamped with now."""

import time

from .utils import calcPriority

NAME = 'text'
DESCRIPTION = 'Plain text — stamp every line with the current time'
EXTENSIONS = []


def probe(line):
    """Text is the universal fallback; never self-selects during detection."""
    return 0.0


def parse(line):
    if not line:
        return {}
    return {'time': time.time(), 'msg': line, 'sev': calcPriority(line)}
