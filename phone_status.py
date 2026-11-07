"""Read-only OCI runner status and daily ntfy summary."""
import argparse
from collections import Counter
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import ipaddress
import json
from pathlib import Path
import re
import time

from local_runner import read_json

HOME = Path('/var/lib/oci-a1')
CACHE = HOME / '.cache/oci-vm'
RUNNER_CMD = b'/opt/oci-a1/app/local_runner.py'
RESULTS = {'capacity', 'accepted', 'monitor', 'pending', 'reconciled', 'boot_unavailable',
           'throttled', 'transient_service_error', 'transient_network_error',
           'ambiguous_launch', 'permanent_error', 'permanent_service_error'}


def runner_alive():
    for entry in Path('/proc').iterdir():
        if not entry.name.isdigit():
            continue
        try:
            if entry.stat().st_uid != HOME.stat().st_uid:
                continue
            args = (entry / 'cmdline').read_bytes().split(b'\0')
            if RUNNER_CMD in args and any(arg.endswith(b'/python') for arg in args[:1]):
                return True
        except (OSError, ProcessLookupError):
            continue
    return False


def snapshot(now=None):
    now = time.time() if now is None else now
    status = read_json(CACHE / 'status.json') or {}
    state = read_json(CACHE / 'runner-state.json') or {}
    last = status.get('last_result_time')
    try:
        age = max(0, int(now - datetime.fromisoformat(last).timestamp()))
    except (TypeError, ValueError, OverflowError):
        age = None
    paused = (HOME / 'paused').exists()
    exit_path = HOME / 'last-exit'
    permanent = exit_path.exists() and exit_path.read_text().strip() == '2'
    alive = runner_alive()
    result = status.get('result') if status.get('result') in RESULTS else 'unknown'
    next_epoch = status.get('next_attempt_epoch')
    return {
        'service': 'running' if alive else 'paused' if paused else 'permanent_error' if permanent else 'stopped',
        'result': result,
        'instance_state': status.get('instance_state') if status.get('instance_state') in {'RUNNING', 'PROVISIONING', 'STARTING', 'STOPPED', 'TERMINATED'} else None,
        'last_update': last if age is not None else None,
        'age_seconds': age,
        'stale': age is None or age > 600,
        'next_attempt': status.get('next_attempt') if alive and isinstance(next_epoch, (int, float)) and next_epoch >= now else None,
        'capacity_streak': state.get('capacity_streak') if isinstance(state.get('capacity_streak'), int) else None,
        'attempts': state.get('attempts') if isinstance(state.get('attempts'), int) else None,
        'launch_pending': state.get('launch_pending') is True,
    }


def counts_since(since):
    counts = Counter()
    for file in [CACHE / 'runner.log.2', CACHE / 'runner.log.1', CACHE / 'runner.log']:
        if not file.is_file():
            continue
        with file.open(errors='replace') as stream:
            for line in stream:
                match = re.match(r'^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d', line)
                if not match:
                    continue
                try:
                    when = datetime.strptime(match.group(), '%Y-%m-%d %H:%M:%S').astimezone()
                    if when < since:
                        continue
                    marker = 'Attempt='
                    if marker in line:
                        payload = json.loads(line.split(marker, 1)[1])
                        if payload.get('result') in RESULTS:
                            counts[payload['result']] += 1
                except (ValueError, json.JSONDecodeError):
                    continue
    return counts


def summary(now=None):
    now = datetime.now().astimezone() if now is None else now
    current = snapshot(now.timestamp())
    counts = counts_since(now - timedelta(hours=24))
    total = sum(counts.values())
    return (f'OCI A1, últimas 24 h: {total} ciclos; '
            f'{counts["capacity"]} sin capacidad, {counts["throttled"]} limitados, '
            f'{counts["accepted"]} aceptados. '
            f'Ahora: {current["service"]}, {current["result"]}; '
            f'datos {"obsoletos" if current["stale"] else "recientes"}; '
            f'pendiente de reconciliar: {"sí" if current["launch_pending"] else "no"}.')


def send_daily():
    sent = HOME / 'daily-sent'
    today = datetime.now().astimezone().date().isoformat()
    if sent.exists() and sent.read_text().strip() == today:
        return True
    from local_runner import notify
    if not notify(summary()):
        return False
    tmp = sent.with_suffix('.tmp')
    tmp.write_text(today + '\n')
    tmp.chmod(0o600)
    tmp.replace(sent)
    return True


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            peer = ipaddress.ip_address(self.client_address[0])
            if not peer.is_loopback:
                self.send_error(403)
                return
        except ValueError:
            self.send_error(403)
            return
        if self.path not in ('/', '/status'):
            self.send_error(404)
            return
        try:
            status = snapshot()
            body = json.dumps(status, ensure_ascii=False).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except (OSError, ValueError, json.JSONDecodeError):
            self.send_error(503)

    def log_message(self, format, *args):
        pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--daily', action='store_true')
    parser.add_argument('--port', type=int, default=18791)
    args = parser.parse_args()
    if args.daily:
        return 0 if send_daily() else 1
    with ThreadingHTTPServer(('127.0.0.1', args.port), Handler) as server:
        server.serve_forever()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
