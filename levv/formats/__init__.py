"""levv.formats — log format registry, dispatch, and auto-detection.

Adding a new format
-------------------
1. Create ``levv/formats/myformat.py`` exporting:
       NAME        : str          — name used with -I flag (lowercase, no spaces)
       DESCRIPTION : str          — one-line description shown in --help
       EXTENSIONS  : list[str]    — filename suffixes / basenames that hint at this format
       probe(line) -> float       — confidence in [0, 1] that *line* belongs here
       parse(line) -> dict        — return {time, sev, msg} or {} on failure
2. Import it below and add it to ``_FORMAT_MODULES``.
"""

import os

from . import auto, text, date, kmsg, www
from . import syslog, journald, docker, json_lines, logfmt
from . import nginx_error, python_log, log4j

# Ordered list used to build the registry.  Place more-specific formats before
# generic ones so that probe() tie-breaking naturally picks the right winner.
_FORMAT_MODULES = [
    json_lines,
    docker,
    syslog,
    journald,
    nginx_error,
    python_log,
    log4j,
    logfmt,
    www,
    kmsg,
    date,
    text,
    auto,
]

# Map format name → module
REGISTRY = {m.NAME: m for m in _FORMAT_MODULES}

# Extension/basename → format name lookup
_EXT_MAP = {}
for _mod in _FORMAT_MODULES:
    for _ext in _mod.EXTENSIONS:
        _EXT_MAP[_ext.lower()] = _mod.NAME


def list_formats():
    """Return a list of (name, description) tuples for all registered formats."""
    return [(m.NAME, m.DESCRIPTION) for m in _FORMAT_MODULES]


def parse_line(fmt_name, line):
    """Parse *line* using the format named *fmt_name*.

    Falls back to ``auto`` for unknown names.  Returns a dict with keys
    ``time`` (float), ``sev`` (int), ``msg`` (str), or ``{}`` on failure.
    """
    mod = REGISTRY.get(fmt_name.lower() if fmt_name else 'auto', REGISTRY['auto'])
    return mod.parse(line)


def detect_format(sample_lines, filename=None):
    """Detect the most likely format from a list of sample lines.

    Uses a three-step strategy:
    1. Unambiguous JSON lines check (fast, zero false-positives).
    2. Per-line probe scoring across all non-fallback formats.
    3. Filename extension hint as a tiebreaker when scores are close.

    Returns a format name string suitable for ``parse_line()``.
    """
    non_empty = [l for l in sample_lines if l.strip()]
    if not non_empty:
        return 'auto'

    # 1. JSON lines are unambiguous — check first
    json_hits = sum(1 for l in non_empty if json_lines.probe(l) > 0.5)
    if json_hits >= max(1, len(non_empty) * 0.6):
        return 'json'

    # 2. Score every non-fallback format
    candidates = [m for m in _FORMAT_MODULES if m.NAME not in ('auto', 'text')]
    scores = {}
    for mod in candidates:
        total = sum(mod.probe(l) for l in non_empty)
        if total > 0:
            scores[mod.NAME] = total / len(non_empty)

    # 3. Extension hint
    ext_hint = None
    if filename:
        basename = os.path.basename(filename).lower()
        # Try full basename first, then extension
        ext_hint = _EXT_MAP.get(basename) or _EXT_MAP.get(
            os.path.splitext(basename)[1].lstrip('.'))

    if not scores:
        return ext_hint or 'auto'

    best_name = max(scores, key=scores.get)
    best_score = scores[best_name]

    # Require at least 50 % of lines to match convincingly
    if best_score < 0.5:
        return ext_hint or 'auto'

    # If extension hint matches a competitive format, prefer it
    if ext_hint and ext_hint in scores:
        if scores[ext_hint] >= best_score * 0.8:
            return ext_hint

    return best_name
