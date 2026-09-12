"""Local OCI launcher/monitor. --check and --status never change OCI."""
import argparse
import fcntl
import ipaddress
import json
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import random
import signal
import socket
import subprocess
import tempfile
import threading
import time
import uuid
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse

import oci
from launch import AD, BOOT, REGION, SUBNET, TENANCY, resource_config, valid_ocid

CACHE = Path.home() / '.cache/oci-vm'
CAPACITY_MIN_DELAY = 10
CAPACITY_MAX_DELAY = 300
TRANSIENT_DELAY = 300
THROTTLE_MIN_DELAY = 30
THROTTLE_MAX_DELAY = 600
RETRY_AFTER_MAX_DELAY = 600
STOP = threading.Event()
LOG = logging.getLogger('oci-vm')


def retry_after_seconds(headers):
    value = next((v for k, v in (headers or {}).items() if k.lower() == 'retry-after'), None)
    if value is None:
        return None
    value = str(value).strip()
    if value.isascii() and value.isdigit():
        return min(RETRY_AFTER_MAX_DELAY, int(value))
    try:
        when = parsedate_to_datetime(value)
        if when.tzinfo is None:
            when = when.replace(tzinfo=timezone.utc)
        return min(RETRY_AFTER_MAX_DELAY, max(0, when.timestamp() - time.time()))
    except (ValueError, TypeError, OverflowError):
        return None


def stamp(value=None):
    return datetime.fromtimestamp(time.time() if value is None else value, timezone.utc).isoformat()


def ensure_cache():
    CACHE.mkdir(mode=0o700, parents=True, exist_ok=True)
    CACHE.chmod(0o700)
    if CACHE.is_symlink() or not CACHE.is_dir() or CACHE.stat().st_uid != os.getuid():
        raise ValueError('Insecure cache directory')


def atomic(path, data):
    ensure_cache()
    fd, name = tempfile.mkstemp(prefix='.runner-', dir=CACHE)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, 'w') as stream:
            json.dump(data, stream, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
        os.chmod(path, 0o600)
        directory = os.open(CACHE, os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def read_json(path):
    if not path.exists() or path.is_symlink() or not path.is_file():
        return None
    if path.stat().st_size > 128 * 1024:
        raise ValueError('State file too large')
    return json.loads(path.read_text())


def validate_state(state):
    if not isinstance(state, dict):
        raise ValueError('Invalid persisted state')
    if not isinstance(state.get('token'), str) or len(state['token']) != 32 or not all(c in '0123456789abcdef' for c in state['token']):
        raise ValueError('Invalid persisted launch identity')
    if not isinstance(state.get('token_created'), (float, int)) or state['token_created'] > time.time() + 60:
        raise ValueError('Invalid token timestamp')
    for key in ('capacity_streak', 'throttle_streak'):
        if not isinstance(state.get(key, 0), int) or not 0 <= state.get(key, 0) <= 100000:
            raise ValueError('Invalid retry state')
    if state.get('instance_id') and not valid_ocid(state['instance_id']):
        raise ValueError('Invalid persisted instance identity')
    if not isinstance(state.get('launch_pending', False), bool):
        raise ValueError('Invalid pending state')


def notify(text):
    try:
        subprocess.run(['notify-send', '--expire-time=10000', 'OCI A1', text], timeout=5, check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        LOG.info('Desktop notification delivered')
    except (OSError, subprocess.SubprocessError) as exc:
        LOG.warning('Desktop notification unavailable (%s)', type(exc).__name__)
    url = os.environ.get('OCI_NOTIFY_WEBHOOK')
    if not url:
        return
    parsed = urlparse(url)
    allowed = {h.strip().lower() for h in os.environ.get('OCI_NOTIFY_WEBHOOK_HOSTS', '').split(',') if h.strip()}
    if parsed.scheme != 'https' or not parsed.hostname or (allowed and parsed.hostname.lower() not in allowed):
        LOG.warning('Webhook rejected: HTTPS and an allowed host are required')
        return
    try:
        import urllib.request
        req = urllib.request.Request(url, data=json.dumps({'text': text[:500]}).encode(),
                                     headers={'Content-Type': 'application/json'}, method='POST')
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status >= 300:
                raise OSError('webhook status')
        LOG.info('Webhook notification delivered')
    except Exception as exc:
        LOG.warning('Webhook notification unavailable (%s)', type(exc).__name__)


def clients():
    config = oci.config.from_file()
    if config.get('tenancy') != TENANCY:
        raise ValueError('Unexpected tenancy')
    config.update(region=REGION, log_requests=False)
    options = dict(timeout=(10, 60), retry_strategy=oci.retry.NoneRetryStrategy())
    return (oci.core.ComputeClient(config, **options),
            oci.core.BlockstorageClient(config, **options),
            oci.core.VirtualNetworkClient(config, **options))


def direct(fn, *args, **kwargs):
    return fn(*args, **kwargs)


def inspect(compute, block, call=direct):
    volume = call(block.get_boot_volume, BOOT).data
    if volume.availability_domain != AD or volume.compartment_id != TENANCY:
        raise ValueError('Unexpected boot volume location')
    attachments = call(oci.pagination.list_call_get_all_results, compute.list_boot_volume_attachments,
                       availability_domain=AD, compartment_id=volume.compartment_id, boot_volume_id=BOOT).data
    active = [a for a in attachments if a.lifecycle_state != 'DETACHED']
    if any(not a.instance_id or not valid_ocid(a.instance_id) for a in active):
        raise ValueError('Attachment without valid instance identity')
    if len({a.instance_id for a in active}) > 1:
        raise ValueError('Conflicting attachment identities')
    return volume, active


def public_ip(value):
    try:
        address = ipaddress.ip_address(value)
        return str(address) if address.is_global else None
    except ValueError:
        return None


def monitor(compute, network, instance_id, call=direct):
    if not valid_ocid(instance_id):
        raise ValueError('Invalid instance identity')
    instance = call(compute.get_instance, instance_id).data
    if instance.compartment_id != TENANCY or getattr(instance, 'availability_domain', AD) != AD:
        raise ValueError('Unexpected instance location')
    result = dict(result='monitor', instance_id=instance_id, instance_state=instance.lifecycle_state)
    if instance.lifecycle_state == 'RUNNING':
        vnics = call(oci.pagination.list_call_get_all_results, compute.list_vnic_attachments,
                     compartment_id=instance.compartment_id, instance_id=instance_id).data
        for attachment in vnics:
            if attachment.lifecycle_state != 'ATTACHED':
                continue
            ip = public_ip(call(network.get_vnic, attachment.vnic_id).data.public_ip)
            if not ip:
                continue
            result['public_ip'] = ip
            if os.environ.get('OCI_ENABLE_SSH_PROBE', '').lower() == 'true':
                try:
                    with socket.create_connection((ip, 22), timeout=10) as connection:
                        connection.settimeout(10)
                        banner = connection.recv(255).split(b'\n', 1)[0].decode('ascii', 'replace').strip()
                        result['ssh_banner_valid'] = banner.startswith('SSH-')
                except OSError as exc:
                    result['ssh_banner_error'] = type(exc).__name__
            break
    return result


def configure_logging():
    ensure_cache()
    LOG.setLevel(logging.INFO)
    LOG.propagate = False
    if not LOG.handlers:
        handler = RotatingFileHandler(CACHE / 'runner.log', maxBytes=5 * 1024 * 1024, backupCount=2)
        handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
        LOG.addHandler(handler)
        LOG.addHandler(logging.StreamHandler())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--status', action='store_true')
    args = parser.parse_args()
    if args.status:
        try:
            status = read_json(CACHE / 'status.json')
            if not status:
                print('No status available (runner has not executed).')
                return 0
            next_epoch = status.get('next_attempt_epoch')
            next_str = f"in {max(0, int(next_epoch - time.time()))}s" if isinstance(next_epoch, (int, float)) else 'stopped'
            print(f"Status: {status.get('result', 'unknown')} | Last: {status.get('last_result_time', 'unknown')} | Next: {next_str} | Delay: {status.get('delay_seconds')}s (jitter: {status.get('jitter_seconds', 0.0):+.2f}s) | Streak: {status.get('capacity_streak', 0)}")
            return 0
        except Exception as exc:
            print(f'Failed to read status: {type(exc).__name__}')
            return 1
    os.umask(0o077)
    try:
        configure_logging()
        signal.signal(signal.SIGTERM, lambda *_: STOP.set())
        signal.signal(signal.SIGINT, lambda *_: STOP.set())
        capacity_delay = int(os.environ.get('OCI_CAPACITY_DELAY', str(CAPACITY_MIN_DELAY)))
        capacity_max_delay = int(os.environ.get('OCI_CAPACITY_MAX_DELAY', str(CAPACITY_MAX_DELAY)))
        if not CAPACITY_MIN_DELAY <= capacity_delay <= capacity_max_delay <= CAPACITY_MAX_DELAY:
            raise ValueError('Invalid capacity delay configuration')
        ocpus, memory_gb = resource_config()
        compute, block, network = clients()
        if args.check:
            volume, active = inspect(compute, block)
            print(json.dumps(dict(result='attached' if active else 'ready' if volume.lifecycle_state == 'AVAILABLE' else 'unavailable', boot_state=volume.lifecycle_state, availability_domain=volume.availability_domain, attachments=[dict(instance_id=a.instance_id, state=a.lifecycle_state) for a in active])))
            return 0
        with (CACHE / 'launch.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            path = CACHE / 'runner-state.json'
            state = read_json(path) or dict(token=uuid.uuid4().hex, token_created=time.time())
            validate_state(state)
            capacity_delay = int(state.get('capacity_delay_seconds', capacity_delay))
            capacity_delay = min(max(capacity_delay, CAPACITY_MIN_DELAY), capacity_max_delay)
            state['capacity_delay_seconds'] = capacity_delay
            state.setdefault('capacity_streak', 0)
            atomic(path, state)
            notified = False
            while not STOP.is_set():
                if STOP.wait(max(0, (state.get('next_attempt_epoch') or 0) - time.time())):
                    break
                started_epoch, started = time.time(), stamp()
                operations = []

                def call(fn, *args, **kwargs):
                    operation = args[0].__name__ if fn is oci.pagination.list_call_get_all_results else fn.__name__
                    entry = dict(operation=operation, http_status=None)
                    operations.append(entry)
                    try:
                        response = fn(*args, **kwargs)
                        entry['http_status'] = getattr(response, 'status', None)
                        return response
                    except oci.exceptions.ServiceError as exc:
                        entry['http_status'] = exc.status
                        raise

                retry_after = recovery = None
                delay = TRANSIENT_DELAY
                permanent = False
                category = 'unknown'
                result = None
                try:
                    volume, active = inspect(compute, block, call)
                    ids = {a.instance_id for a in active}
                    if ids:
                        state['instance_id'] = next(iter(ids))
                        state['launch_pending'] = False
                        atomic(path, state)
                        result = monitor(compute, network, state['instance_id'], call)
                        if result['instance_state'] == 'RUNNING' and not notified:
                            notify('Instance RUNNING')
                            notified = True
                    elif state.get('launch_pending'):
                        category = 'reconcile_required'
                        permanent = True
                        result = dict(result='reconcile_required', reason='pending request has no confirmed attachment')
                    elif volume.lifecycle_state != 'AVAILABLE':
                        result = dict(result='boot_unavailable', boot_state=volume.lifecycle_state)
                    else:
                        if time.time() - state['token_created'] >= 23 * 3600:
                            state['token'] = uuid.uuid4().hex
                            state['token_created'] = time.time()
                        details = oci.core.models.LaunchInstanceDetails(availability_domain=AD, compartment_id=volume.compartment_id, display_name='oci-a1', shape='VM.Standard.A1.Flex', shape_config=oci.core.models.LaunchInstanceShapeConfigDetails(ocpus=ocpus, memory_in_gbs=memory_gb), source_details=oci.core.models.InstanceSourceViaBootVolumeDetails(boot_volume_id=BOOT), create_vnic_details=oci.core.models.CreateVnicDetails(subnet_id=SUBNET, assign_public_ip=True))
                        state['launch_pending'] = True
                        state['next_attempt_epoch'] = time.time() + TRANSIENT_DELAY
                        atomic(path, state)
                        response = call(compute.launch_instance, details, opc_retry_token=state['token'])
                        instance_id = getattr(response.data, 'id', None)
                        if not instance_id or not valid_ocid(instance_id):
                            raise ValueError('Launch accepted without valid instance identity')
                        state['instance_id'] = instance_id
                        state['launch_pending'] = False
                        atomic(path, state)
                        result = dict(result='accepted', instance_id=instance_id, instance_state=response.data.lifecycle_state)
                except oci.exceptions.ServiceError as exc:
                    if state.get('launch_pending') and exc.status not in (400, 401, 403, 404, 409, 429, 500):
                        category, result = 'ambiguous', dict(result='reconcile_required', http_status=exc.status)
                        permanent = True
                    elif exc.status == 429:
                        state['launch_pending'] = False
                        state['throttle_streak'] = state.get('throttle_streak', 0) + 1
                        retry_after = retry_after_seconds(exc.headers)
                        delay = max(min(THROTTLE_MAX_DELAY, THROTTLE_MIN_DELAY * 2 ** min(state['throttle_streak'] - 1, 5)), retry_after or 0)
                        category, result = 'throttled', dict(result='throttled', http_status=429)
                    elif exc.status == 500 and exc.code == 'InternalError' and 'out of host capacity' in exc.message.lower():
                        state['launch_pending'] = False
                        state['capacity_streak'] = state.get('capacity_streak', 0) + 1
                        capacity_delay = min(capacity_max_delay, max(CAPACITY_MIN_DELAY, capacity_delay + (10 if state['capacity_streak'] > 3 else 0)))
                        state['capacity_delay_seconds'] = capacity_delay
                        category, result, delay = 'capacity', dict(result='capacity', http_status=500), capacity_delay
                    elif exc.status in (400, 401, 403, 404, 409):
                        state['launch_pending'] = False
                        category, result, permanent = 'permanent', dict(result='permanent_service_error', http_status=exc.status), True
                    else:
                        category, result = 'transient', dict(result='transient_service_error', http_status=exc.status)
                except (oci.exceptions.RequestException, TimeoutError) as exc:
                    category, result, permanent = 'ambiguous', dict(result='reconcile_required', reason=type(exc).__name__), True
                except OSError:
                    raise
                except Exception as exc:
                    category, result, permanent = 'permanent', dict(result='permanent_error', error_type=type(exc).__name__), True
                jitter = round(random.uniform(-min(3.0, delay * 0.1), min(3.0, delay * 0.1)), 2) if not permanent else 0.0
                effective_delay = max(CAPACITY_MIN_DELAY, round(delay + jitter, 2)) if not permanent else None
                next_time = None if permanent else time.time() + effective_delay
                state['next_attempt_epoch'] = next_time
                atomic(path, state)
                status = dict(result, attempt_started=started, last_result_time=stamp(), next_attempt=stamp(next_time) if next_time else None, next_attempt_epoch=next_time, delay_seconds=effective_delay, base_delay_seconds=None if permanent else delay, jitter_seconds=jitter, capacity_delay_seconds=capacity_delay, capacity_streak=state.get('capacity_streak', 0), response_category=category, operations=operations, duration_seconds=round(time.time() - started_epoch, 3), throttle_streak=state.get('throttle_streak', 0), retry_after_seconds=retry_after, throttle_recovery_seconds=recovery)
                atomic(CACHE / 'status.json', status)
                LOG.info('Attempt=%s', json.dumps({k: status[k] for k in ('result', 'attempt_started', 'next_attempt', 'delay_seconds', 'response_category', 'duration_seconds')}))
                if permanent:
                    notify('Local OCI runner stopped; reconciliation may be required.')
                    return 2
            return 0
    except Exception as exc:
        LOG.error('Local runner failed closed (%s)', type(exc).__name__)
        try:
            atomic(CACHE / 'status.json', dict(result='permanent_local_error', error_type=type(exc).__name__, last_result_time=stamp(), next_attempt=None))
        except Exception:
            pass
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
