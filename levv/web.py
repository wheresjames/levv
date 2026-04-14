"""
levv web interface — HTTP server + HTML/JS timeline viewer.
"""

import json
import os
import threading
import time
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler

# ---------------------------------------------------------------------------
# HTML page — loaded from web.html next to this file
# ---------------------------------------------------------------------------

def _load_html():
    path = os.path.join(os.path.dirname(__file__), 'web.html')
    with open(path, 'rb') as f:
        return f.read()


# ---------------------------------------------------------------------------
# HTTP handler
# ---------------------------------------------------------------------------

class _Handler(BaseHTTPRequestHandler):

    # These are set by start() before the server starts
    shared   = None   # dict: {p, msgs, lock}

    def do_GET(self):
        if self.path in ('/', '/index.html'):
            self._serve_bytes(_load_html(), 'text/html; charset=utf-8')
        elif self.path == '/api/state':
            self._serve_state()
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path == '/api/command':
            self._handle_command()
        else:
            self.send_error(404)

    # ------------------------------------------------------------------ #

    def _serve_bytes(self, data, ctype):
        self.send_response(200)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', len(data))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(data)

    def _serve_state(self):
        sh = self.__class__.shared
        with sh['lock']:
            p    = sh['p']
            msgs = list(sh['msgs'])   # snapshot
            files_info = sh['files_info']

        now       = time.time()
        timerange = p['timerange']
        autoscroll_active = p.get('autoscroll_active', True)

        if autoscroll_active:
            pct = p.get('autoscroll', 75)
            view_time = now - (timerange * pct / 100)
        else:
            view_time = p.get('view_time', now - timerange * 0.75)

        # If autoscroll is on but there are no messages in the current window,
        # snap view_time so the most recent messages are visible.
        if autoscroll_active and msgs:
            tmin = view_time
            tmax = view_time + timerange
            in_window = any(tmin <= m['time'] <= tmax for m in msgs)
            if not in_window:
                latest = max(m['time'] for m in msgs)
                pct    = p.get('autoscroll', 75)
                view_time = latest - (timerange * pct / 100)

        # Send only messages within the visible window (with a 2× buffer each side)
        # to avoid giant payloads that can cause browser JSON parse failures.
        tmin_buf = view_time - timerange * 2
        tmax_buf = view_time + timerange * 3
        visible_msgs = [m for m in msgs if tmin_buf <= m['time'] <= tmax_buf]

        payload = {
            'view_time':      view_time,
            'timerange':      timerange,
            'msgs':           visible_msgs,
            'files':          files_info,
            'file_filter':    p.get('file_filter', 0),
            'lines':          p.get('lines', 2),
            'autoscroll':     autoscroll_active,
            'autoscroll_pct': p.get('autoscroll', 75),
        }
        data = json.dumps(payload).encode()
        self._serve_bytes(data, 'application/json')

    def _handle_command(self):
        length = int(self.headers.get('Content-Length', 0))
        raw    = self.rfile.read(length)
        try:
            cmd = json.loads(raw)
        except Exception:
            self.send_error(400)
            return

        sh = self.__class__.shared
        with sh['lock']:
            p  = sh['p']
            c  = cmd.get('cmd', '')

            if c == 'zoom_in':
                if p['timerange'] > 0.001:
                    p['view_time'] = p.get('view_time', time.time() - p['timerange'] * 0.75)
                    p['view_time'] += p['timerange'] / 20
                    p['timerange'] /= 1.1

            elif c == 'zoom_out':
                p['view_time'] = p.get('view_time', time.time() - p['timerange'] * 0.75)
                p['view_time'] -= p['timerange'] / 20
                p['timerange'] *= 1.1

            elif c == 'scroll_left':
                p['autoscroll_active'] = False
                p['view_time'] = p.get('view_time', time.time() - p['timerange'] * 0.75)
                p['view_time'] -= p['timerange'] / 20

            elif c == 'scroll_right':
                p['autoscroll_active'] = False
                p['view_time'] = p.get('view_time', time.time() - p['timerange'] * 0.75)
                p['view_time'] += p['timerange'] / 20

            elif c == 'set_time':
                p['autoscroll_active'] = False
                p['view_time'] = float(cmd.get('value', p.get('view_time', 0)))

            elif c == 'autoscroll_on':
                p['autoscroll_active'] = True

            elif c == 'autoscroll_off':
                p['autoscroll_active'] = False

            elif c == 'set_lines':
                v = int(cmd.get('value', 2))
                p['lines'] = max(1, min(3, v))

            elif c == 'file_filter':
                p['file_filter'] = int(cmd.get('value', 0))

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', 4)
        self.end_headers()
        self.wfile.write(b'true')

    def log_message(self, fmt, *args):
        pass  # suppress access log


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def start(port, shared):
    """
    Start the web server in a daemon thread.

    :param port:   TCP port to listen on.
    :param shared: dict with keys: p (params dict), msgs (list), lock
                   (threading.Lock), files_info (list of file dicts).
    :returns: HTTPServer instance (already running in background thread).
    """
    _Handler.shared = shared

    server = HTTPServer(('', port), _Handler)

    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()

    return server
