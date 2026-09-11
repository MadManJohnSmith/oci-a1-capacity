"""Local OCI launcher/monitor. --check only reads OCI; never changes instances."""
import argparse
import fcntl
import json
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import signal
import socket
import subprocess
import tempfile
import threading
import time
import uuid
from datetime import datetime, timezone

import oci
from launch import AD, BOOT, REGION, SUBNET, TENANCY

CACHE = Path.home() / '.cache/oci-vm'
STOP = threading.Event()
LOG = logging.getLogger('oci-vm')


def stamp(value=None):
    return datetime.fromtimestamp(time.time() if value is None else value, timezone.utc).isoformat()


def atomic(path, data):
    fd, name = tempfile.mkstemp(prefix='.runner-', dir=CACHE)
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(data, stream, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
        directory = os.open(CACHE, os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def notify(text):
    try:
        subprocess.run(['notify-send', '--expire-time=10000', 'OCI A1', text],
                       timeout=5, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        LOG.info('Desktop notification delivered')
    except (OSError, subprocess.SubprocessError) as exc:
        LOG.warning('Desktop notification unavailable (%s); %s', type(exc).__name__, text)


def clients():
    config = oci.config.from_file()
    if config['tenancy'] != TENANCY:
        raise ValueError('Unexpected tenancy')
    config.update(region=REGION, log_requests=False)
    options = dict(timeout=(10, 60), retry_strategy=oci.retry.NoneRetryStrategy())
    return (oci.core.ComputeClient(config, **options),
            oci.core.BlockstorageClient(config, **options),
            oci.core.VirtualNetworkClient(config, **options))


def inspect(compute, block):
    volume = block.get_boot_volume(BOOT).data
    if volume.availability_domain != AD or volume.compartment_id != TENANCY:
        raise ValueError('Unexpected boot volume location')
    attachments = oci.pagination.list_call_get_all_results(
        compute.list_boot_volume_attachments, availability_domain=AD,
        compartment_id=volume.compartment_id, boot_volume_id=BOOT).data
    active = [a for a in attachments if a.lifecycle_state != 'DETACHED']
    if any(not a.instance_id for a in active):
        raise ValueError('Attachment without instance identity')
    return volume, active


def monitor(compute, network, instance_id):
    instance = compute.get_instance(instance_id).data
    result = dict(result='monitor', instance_id=instance_id, instance_state=instance.lifecycle_state)
    if instance.lifecycle_state == 'RUNNING':
        vnics = oci.pagination.list_call_get_all_results(
            compute.list_vnic_attachments, compartment_id=instance.compartment_id,
            instance_id=instance_id).data
        for attachment in vnics:
            if attachment.lifecycle_state != 'ATTACHED':
                continue
            ip = network.get_vnic(attachment.vnic_id).data.public_ip
            if not ip:
                continue
            result['public_ip'] = ip
            try:
                with socket.create_connection((ip, 22), timeout=10) as connection:
                    connection.settimeout(10)
                    banner = connection.recv(255).split(b'\n', 1)[0].decode('ascii', 'replace').strip()
                    result['ssh_banner'] = ''.join(c for c in banner if 32 <= ord(c) < 127)
                    result['ssh_banner_valid'] = banner.startswith('SSH-')
            except OSError as exc:
                result['ssh_banner_error'] = type(exc).__name__
            LOG.info('RUNNING public IP=%s SSH banner=%s', ip, result.get('ssh_banner', result.get('ssh_banner_error')))
            break
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    os.umask(0o077)
    CACHE.mkdir(mode=0o700, parents=True, exist_ok=True)
    CACHE.chmod(0o700)
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s',
                        handlers=[RotatingFileHandler(CACHE / 'runner.log', maxBytes=5*1024*1024, backupCount=2), logging.StreamHandler()])
    signal.signal(signal.SIGTERM, lambda *_: STOP.set())
    signal.signal(signal.SIGINT, lambda *_: STOP.set())
    try:
        compute, block, network = clients()
        if args.check:
            volume, active = inspect(compute, block)
            print(json.dumps(dict(result='attached' if active else 'ready' if volume.lifecycle_state == 'AVAILABLE' else 'unavailable',
                                  boot_state=volume.lifecycle_state, availability_domain=volume.availability_domain,
                                  attachments=[dict(instance_id=a.instance_id, state=a.lifecycle_state) for a in active])))
            return 0
        with (CACHE / 'launch.lock').open('a') as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                LOG.error('Another local runner holds the launch lock')
                return 2
            path = CACHE / 'runner-state.json'
            state = json.loads(path.read_text()) if path.exists() else dict(token=uuid.uuid4().hex, token_created=time.time())
            if not isinstance(state.get('token'), str) or len(state['token']) != 32 or not isinstance(state.get('token_created'), (float, int)):
                raise ValueError('Invalid persisted launch identity')
            atomic(path, state)
            notified = False
            while not STOP.is_set():
                if STOP.wait(max(0, (state.get('next_attempt_epoch') or 0) - time.time())):
                    break
                started = stamp()
                delay = 300
                permanent = False
                try:
                    volume, active = inspect(compute, block)
                    ids = {a.instance_id for a in active}
                    if len(ids) > 1 or (ids and state.get('instance_id') and state['instance_id'] not in ids):
                        raise ValueError('Conflicting attachment identities')
                    if ids:
                        state['instance_id'] = next(iter(ids))
                        atomic(path, state)
                    if state.get('instance_id'):
                        result = monitor(compute, network, state['instance_id'])
                        if result['instance_state'] == 'RUNNING' and not notified:
                            notify('Instance RUNNING; ' + result.get('public_ip', 'public IP not yet available'))
                            notified = True
                    elif volume.lifecycle_state != 'AVAILABLE':
                        result = dict(result='boot_unavailable', boot_state=volume.lifecycle_state)
                    elif STOP.is_set():
                        break
                    else:
                        # ponytail: token safety capped at 23 hours; operator reconciliation required beyond that.
                        if time.time() - state['token_created'] >= 23*3600:
                            raise ValueError('Token safety window expired; reconcile before retry')
                        details = oci.core.models.LaunchInstanceDetails(
                            availability_domain=AD, compartment_id=volume.compartment_id,
                            display_name='oci-a1', shape='VM.Standard.A1.Flex',
                            shape_config=oci.core.models.LaunchInstanceShapeConfigDetails(ocpus=2, memory_in_gbs=12),
                            source_details=oci.core.models.InstanceSourceViaBootVolumeDetails(boot_volume_id=BOOT),
                            create_vnic_details=oci.core.models.CreateVnicDetails(subnet_id=SUBNET, assign_public_ip=True))
                        state['launch_pending'] = True
                        state['next_attempt_epoch'] = time.time() + 300
                        atomic(path, state)
                        response = compute.launch_instance(details, opc_retry_token=state['token'])
                        state['instance_id'] = response.data.id
                        if not state['instance_id']:
                            raise ValueError('Launch accepted without instance identity')
                        state['launch_pending'] = False
                        atomic(path, state)
                        result = dict(result='accepted', instance_id=state['instance_id'], instance_state=response.data.lifecycle_state)
                except oci.exceptions.ServiceError as exc:
                    if exc.status == 429:
                        result, delay = dict(result='throttled', http_status=429), 600
                    elif exc.status == 500 and exc.code == 'InternalError' and 'out of host capacity' in exc.message.lower():
                        result = dict(result='capacity', http_status=500)
                    elif exc.status in (408, 500, 502, 503, 504):
                        result = dict(result='transient_service_error', http_status=exc.status)
                    else:
                        result, permanent = dict(result='permanent_service_error', http_status=exc.status), True
                except (oci.exceptions.RequestException, OSError) as exc:
                    # Disk failures must not be retried as network failures.
                    if isinstance(exc, OSError):
                        raise
                    result = dict(result='network_error', error_type=type(exc).__name__)
                except Exception as exc:
                    result, permanent = dict(result='permanent_error', error_type=type(exc).__name__), True
                next_time = None if permanent else time.time() + delay
                state['next_attempt_epoch'] = next_time
                atomic(path, state)
                status = dict(result, attempt_started=started, last_result_time=stamp(), next_attempt=stamp(next_time) if next_time else None,
                              next_attempt_epoch=next_time, delay_seconds=None if permanent else delay)
                atomic(CACHE / 'status.json', status)
                LOG.info('Result=%s next_attempt=%s', result['result'], status['next_attempt'])
                if permanent:
                    notify('Permanent OCI error; local runner stopped. See status.json.')
                    return 2
            LOG.info('Local runner stopped; no cloud action performed')
            return 0
    except Exception as exc:
        LOG.error('Local runner failed closed (%s)', type(exc).__name__)
        atomic(CACHE / 'status.json', dict(result='permanent_local_error', error_type=type(exc).__name__, last_result_time=stamp(), next_attempt=None))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
