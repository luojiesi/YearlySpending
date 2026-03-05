"""
Local dev server for the Spending Dashboard.
Serves static files from output/ and provides an API to save overrides.

Usage:
    python server.py              # starts on port 8000
    python server.py --port 9000  # custom port
    python server.py --stop       # stop a running server
"""
import argparse
import json
import os
import signal
import sys
import threading
import time
from http.server import HTTPServer, SimpleHTTPRequestHandler

overrides_lock = threading.Lock()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, 'output')
OVERRIDES_PATH = os.path.join(OUTPUT_DIR, 'overrides.json')
PID_FILE = os.path.join(BASE_DIR, '.server.pid')
DEFAULT_PORT = 18234
HEARTBEAT_TIMEOUT = 600  # seconds without heartbeat before auto-shutdown
WAKE_GRACE = 15         # extra seconds after sleep/wake to allow heartbeat
INITIAL_GRACE = 120     # seconds to wait for first page load

last_heartbeat = 0  # 0 means no heartbeat received yet
server_start_time = 0


class DashboardHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=OUTPUT_DIR, **kwargs)

    def do_GET(self):
        if self.path == '/api/overrides':
            self._send_overrides()
        elif self.path == '/api/heartbeat':
            self._heartbeat()
        else:
            super().do_GET()

    def do_POST(self):
        if self.path == '/api/overrides':
            self._save_overrides()
        else:
            self.send_error(404)

    def do_PATCH(self):
        if self.path == '/api/overrides':
            self._patch_override()
        else:
            self.send_error(404)

    def _heartbeat(self):
        global last_heartbeat
        last_heartbeat = time.time()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(b'{"ok":true}')

    VALID_SECTIONS = ('reimbursable', 'notSpending', 'categories')

    def _load_overrides(self):
        """Load overrides from disk (caller must hold overrides_lock).

        Storage format uses embedded timestamps:
          {"reimbursable": {"id": {"v": true, "ts": 1234}}, ...}
        Auto-migrates legacy flat values (bare bool/string) to {"v": val, "ts": 0}.
        """
        if not os.path.isfile(OVERRIDES_PATH):
            return {'reimbursable': {}, 'notSpending': {}, 'categories': {}}
        with open(OVERRIDES_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        # Auto-migrate legacy flat values and strip old _ts map
        migrated = False
        data.pop('_ts', None)
        for section in self.VALID_SECTIONS:
            entries = data.get(section, {})
            for key, val in entries.items():
                if not isinstance(val, dict) or 'v' not in val:
                    entries[key] = {'v': val, 'ts': 0}
                    migrated = True
            data[section] = entries
        if migrated:
            self._write_overrides(data)
        return data

    def _write_overrides(self, data):
        """Write overrides to disk (caller must hold overrides_lock)."""
        with open(OVERRIDES_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

    @staticmethod
    def _unwrap(data):
        """Unwrap {"v": val, "ts": ...} to flat values for client."""
        out = {}
        for section in DashboardHandler.VALID_SECTIONS:
            entries = data.get(section, {})
            out[section] = {k: e['v'] if isinstance(e, dict) else e
                            for k, e in entries.items()}
        return out

    def _send_overrides(self):
        with overrides_lock:
            data = self._load_overrides()
        flat = self._unwrap(data)
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(flat).encode('utf-8'))

    def _save_overrides(self):
        """Full replace — wraps flat values with ts: 0."""
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length)

        try:
            incoming = json.loads(body)
        except json.JSONDecodeError:
            self.send_error(400, 'Invalid JSON')
            return

        # Wrap flat values with ts: 0
        data = {}
        for section in self.VALID_SECTIONS:
            entries = incoming.get(section, {})
            data[section] = {}
            for k, v in entries.items():
                if isinstance(v, dict) and 'v' in v:
                    data[section][k] = v
                else:
                    data[section][k] = {'v': v, 'ts': 0}

        with overrides_lock:
            self._write_overrides(data)

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(b'{"ok": true}')

    def _patch_override(self):
        """Apply one or more individual changes atomically.

        Body: {"changes": [{"section": "...", "id": "txn_id",
                             "value": <bool|string|null>, "ts": <ms>}, ...]}
        Each value is stored with its timestamp. A change is only applied
        if its ts >= the stored ts for that key (last-writer-wins).
        A null value removes the key (undo override).
        """
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length)

        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            self.send_error(400, 'Invalid JSON')
            return

        changes = payload.get('changes', [])
        if not changes:
            self.send_error(400, 'No changes provided')
            return

        with overrides_lock:
            data = self._load_overrides()
            for ch in changes:
                section = ch.get('section')
                txn_id = ch.get('id')
                value = ch.get('value')
                ts = ch.get('ts', 0)
                if section not in self.VALID_SECTIONS or not txn_id:
                    continue
                if section not in data:
                    data[section] = {}
                existing = data[section].get(txn_id, {})
                existing_ts = existing.get('ts', 0) if isinstance(existing, dict) else 0
                if ts < existing_ts:
                    continue  # stale change, skip
                if value is None:
                    data[section].pop(txn_id, None)
                else:
                    data[section][txn_id] = {'v': value, 'ts': ts}
            self._write_overrides(data)

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(b'{"ok": true}')

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PATCH, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()


def cleanup_pid():
    try:
        os.remove(PID_FILE)
    except OSError:
        pass


def main():
    parser = argparse.ArgumentParser(description='Spending Dashboard dev server')
    parser.add_argument('--port', type=int, default=DEFAULT_PORT)
    parser.add_argument('--bind', default='0.0.0.0',
                        help='Address to bind (default: 0.0.0.0 for LAN access, use localhost for local only)')
    parser.add_argument('--stop', action='store_true', help='Stop a running server')
    args = parser.parse_args()

    if args.stop:
        stop_server()
        return

    # Write PID file
    with open(PID_FILE, 'w') as f:
        f.write(str(os.getpid()))

    bind = args.bind
    server = HTTPServer((bind, args.port), DashboardHandler)
    port = server.server_address[1]  # actual port (may differ from args.port if 0)
    if bind == '0.0.0.0':
        import socket
        local_ip = socket.gethostbyname(socket.gethostname())
        print(f'Serving dashboard at http://localhost:{port}/spending_dashboard.html')
        print(f'  LAN access: http://{local_ip}:{port}/spending_dashboard.html')
    else:
        print(f'Serving dashboard at http://{bind}:{port}/spending_dashboard.html')
    print(f'Overrides file: {OVERRIDES_PATH}')
    print(f'PID: {os.getpid()}')
    print(f'Auto-shutdown after {HEARTBEAT_TIMEOUT}s without heartbeat.')
    print('Stop with: python server.py --stop')
    sys.stdout.flush()

    global server_start_time
    server_start_time = time.time()

    def watchdog():
        """Shut down the server if no heartbeat received within timeout."""
        last_check = time.time()
        wake_deadline = 0  # 0 means no wake grace active
        while True:
            time.sleep(10)
            now = time.time()
            elapsed = now - last_check
            last_check = now

            # Detect sleep/wake: if the 10s sleep took much longer, the PC slept
            if elapsed > 30:
                wake_deadline = now + WAKE_GRACE
                print(f'\nSleep detected (gap {elapsed:.0f}s) — '
                      f'waiting {WAKE_GRACE}s for heartbeat.')
                continue

            # Still in wake grace period — give the page time to reconnect
            if wake_deadline and now < wake_deadline:
                if last_heartbeat > wake_deadline - WAKE_GRACE:
                    wake_deadline = 0  # heartbeat arrived, resume normal
                continue
            wake_deadline = 0

            if last_heartbeat == 0:
                # No heartbeat yet — use initial grace period
                if now - server_start_time > INITIAL_GRACE:
                    print(f'\nNo page opened within {INITIAL_GRACE}s — shutting down.')
                    server.shutdown()
                    break
            else:
                # Had heartbeat before — use normal timeout
                if now - last_heartbeat > HEARTBEAT_TIMEOUT:
                    print(f'\nNo heartbeat for {HEARTBEAT_TIMEOUT}s — shutting down.')
                    server.shutdown()
                    break

    t = threading.Thread(target=watchdog, daemon=True)
    t.start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        print('\nShutting down.')
        server.server_close()
        cleanup_pid()


def stop_server():
    if not os.path.isfile(PID_FILE):
        print('No server running (no PID file found).')
        return
    with open(PID_FILE, 'r') as f:
        pid = int(f.read().strip())
    try:
        os.kill(pid, signal.SIGTERM)
        print(f'Stopped server (PID {pid}).')
    except OSError as e:
        print(f'Could not stop PID {pid}: {e}')
    cleanup_pid()


if __name__ == '__main__':
    main()
