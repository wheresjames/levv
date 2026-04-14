"""CEF — Common Event Format (ArcSight / Splunk security logs).

Line structure:
  CEF:Version|Vendor|Product|DevVer|SigID|Name|Severity|Extension

The line may be prefixed with a syslog header.  Severity is 0–10:
  0–3 = Low, 4–6 = Medium, 7–8 = High, 9–10 = Very-High.
Extension is a space-separated list of key=value pairs.
"""

import re
import time

import dateutil.parser

from .utils import calcPriority

NAME = 'cef'
DESCRIPTION = 'CEF (Common Event Format) — ArcSight/Splunk security event logs'
EXTENSIONS = ['cef.log']

# Locate the CEF: prefix (may follow a syslog timestamp header)
_CEF_RE = re.compile(
    r'CEF:(\d+)\|'        # version
    r'([^|]*)\|'          # device vendor
    r'([^|]*)\|'          # device product
    r'([^|]*)\|'          # device version
    r'([^|]*)\|'          # signature ID
    r'([^|]*)\|'          # name
    r'(\d+)\|?'           # severity 0–10
    r'(.*)'               # extension
)

# Extension key=value pairs; values may contain escaped characters
_EXT_RE = re.compile(r'(\w+)=((?:[^\\ =\r\n]|\\.)*(?:(?:\\ )+(?:[^\\ =\r\n]|\\.)*)*)')


def _cef_sev(n):
    if n >= 9:
        return 1   # Very-High
    if n >= 7:
        return 1   # High
    if n >= 4:
        return 2   # Medium
    if n >= 1:
        return 5   # Low
    return 6       # Unknown / 0


def probe(line):
    return 0.95 if re.search(r'CEF:\d+\|', line) else 0.0


def _parse_ext(raw):
    pairs = {}
    for m in _EXT_RE.finditer(raw):
        key = m.group(1)
        val = m.group(2).replace('\\=', '=').replace('\\|', '|').replace('\\n', '\n').replace('\\ ', ' ')
        pairs[key] = val
    return pairs


def parse(line):
    m = _CEF_RE.search(line)
    if not m:
        return {}

    _ver, vendor, product, _devver, _sigid, name, sev_str, ext_raw = m.groups()

    try:
        sev = _cef_sev(int(sev_str))
    except (ValueError, TypeError):
        sev = 6

    ext = _parse_ext(ext_raw)

    # Timestamp from extension — common CEF timestamp fields
    t = time.time()
    for ts_key in ('rt', 'start', 'end', 'deviceReceiptTime'):
        if ts_key in ext:
            raw_ts = ext[ts_key]
            try:
                val = float(raw_ts)
                t = val / 1000.0 if val > 1e10 else val
                break
            except (ValueError, TypeError):
                try:
                    d = dateutil.parser.parse(raw_ts, fuzzy=True)
                    t = time.mktime(d.timetuple())
                    break
                except Exception:
                    pass

    # Message
    src = ext.get('src', ext.get('sourceAddress', ''))
    dst = ext.get('dst', ext.get('destinationAddress', ''))
    detail = ext.get('msg', ext.get('message', ext.get('reason', '')))

    parts = [f'[{vendor}/{product}]', name]
    if src:
        parts.append(f'src={src}')
    if dst:
        parts.append(f'dst={dst}')
    if detail:
        parts.append(detail)

    return {'time': t, 'sev': sev, 'msg': ' '.join(parts)}
