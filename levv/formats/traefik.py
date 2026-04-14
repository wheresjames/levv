"""Traefik reverse proxy access log format.

Traefik can emit access logs in two modes:

  JSON  (recommended, default in modern configs)
        {"ClientAddr":"1.2.3.4:56789","DownstreamStatus":200,
         "Duration":1234567,"RequestMethod":"GET","RequestPath":"/api",
         "RouterName":"my-router@docker","ServiceName":"my-svc@docker",
         "StartUTC":"2024-01-15T10:23:45.123456789Z","level":"info","msg":""}

  CLF-text  (similar to Apache Combined Log but with extra trailing fields)
        1.2.3.4 - - [15/Jan/2024:10:23:45 +0000] "GET /api HTTP/1.1"
        200 1234 "-" "curl" 1 "my-router@docker" "http://backend:8080" 12345678ms

The JSON mode is detected by the presence of Traefik-specific keys.
The text mode is detected by the trailing router-name "@provider" pattern.
"""

import json
import re
import time
import shlex

import dateutil.parser

NAME = 'traefik'
DESCRIPTION = 'Traefik reverse proxy access logs (JSON and CLF-text modes)'
EXTENSIONS = ['traefik.log', 'traefik_access.log']

_TRAEFIK_JSON_KEYS = frozenset(
    ['RouterName', 'ServiceName', 'DownstreamStatus', 'RequestPath',
     'ClientAddr', 'StartUTC', 'OriginStatus']
)

# CLF text mode: IP … status … "@provider" pattern near the end
_TRAEFIK_TEXT_RE = re.compile(
    r'^\d[\d.:a-fA-F]+\s'   # client IP
    r'.*"[^"]+@\w+"'        # quoted "router@provider" somewhere in line
)


def probe(line):
    s = line.strip()
    if s.startswith('{') and s.endswith('}'):
        try:
            obj = json.loads(s)
            if isinstance(obj, dict) and (_TRAEFIK_JSON_KEYS & set(obj.keys())):
                return 0.97
        except Exception:
            pass
    if _TRAEFIK_TEXT_RE.match(s):
        return 0.85
    return 0.0


def _status_to_sev(sc):
    if sc >= 500:
        return 1
    if sc >= 400:
        return 2
    if sc >= 300:
        return 3
    return 6


def parse(line):
    s = line.strip()

    # JSON mode
    if s.startswith('{') and s.endswith('}'):
        try:
            obj = json.loads(s)
        except Exception:
            obj = None

        if obj and isinstance(obj, dict):
            t = time.time()
            for ts_key in ('StartUTC', 'time', 'timestamp', '@timestamp'):
                if ts_key in obj:
                    try:
                        d = dateutil.parser.parse(str(obj[ts_key]))
                        t = time.mktime(d.timetuple())
                        break
                    except Exception:
                        pass

            sc = 0
            for sc_key in ('DownstreamStatus', 'OriginStatus', 'StatusCode'):
                if sc_key in obj:
                    try:
                        sc = int(obj[sc_key])
                        break
                    except (ValueError, TypeError):
                        pass

            client = obj.get('ClientAddr', obj.get('ClientHost', '-'))
            method = obj.get('RequestMethod', '')
            path   = obj.get('RequestPath', obj.get('RequestURI', '-'))
            router = obj.get('RouterName', '')
            dur_ns = obj.get('Duration', 0)
            try:
                dur_str = f'{int(dur_ns) // 1_000_000}ms'
            except (ValueError, TypeError):
                dur_str = ''

            parts = [client, f'{method} {path}'.strip(), str(sc) if sc else '']
            if router:
                parts.append(f'rt={router}')
            if dur_str:
                parts.append(dur_str)

            return {'time': t, 'sev': _status_to_sev(sc),
                    'msg': ' : '.join(p for p in parts if p)}

    # CLF text mode
    try:
        tokens = shlex.split(line.replace('[', '"').replace(']', '"'))
    except ValueError:
        tokens = line.split()

    if len(tokens) < 7:
        return {}

    ip = tokens[0]
    dt = tokens[3] if len(tokens) > 3 else ''
    request = tokens[4] if len(tokens) > 4 else ''
    status = tokens[5] if len(tokens) > 5 else '0'

    t = time.time()
    if dt:
        try:
            d = dateutil.parser.parse(dt, fuzzy=True)
            t = time.mktime(d.timetuple())
        except Exception:
            pass

    try:
        sc = int(status)
    except (ValueError, TypeError):
        sc = 0

    return {'time': t, 'sev': _status_to_sev(sc),
            'msg': f'{ip} : {request} : {status}'}
