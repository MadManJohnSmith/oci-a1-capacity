"""Real read-only OCI checks and quota/storage report; no mocks or cloud writes."""
import json
import os
import time
import oci
from local_runner import CACHE, AD, TENANCY, REGION, clients, inspect, atomic, stamp

os.umask(0o077)
compute, block, _ = clients()
assert compute.base_client.timeout == (10, 60)
assert isinstance(compute.retry_strategy, oci.retry.NoneRetryStrategy)
volume, attachments = inspect(compute, block)
assert volume.availability_domain == AD
report = dict(checked_at=stamp(), region=REGION,
              caveat='Service limits, quotas and visible storage are not billing proof or an Always Free guarantee. Storage inventory covers the root compartment and configured AD only; other compartments, regions, backups and billing may add usage.',
              boot_state=volume.lifecycle_state, attachment_count=len(attachments), requested_ocpus=2, requested_memory_gb=12)
config = oci.config.from_file()
config.update(region=REGION, log_requests=False)
options = dict(timeout=(10, 60), retry_strategy=oci.retry.NoneRetryStrategy())
limits = oci.limits.LimitsClient(config, **options)
quotas = oci.limits.QuotasClient(config, **options)

def read(name, fn):
    try:
        report[name] = fn()
    except Exception as exc:
        report[name] = dict(error_type=type(exc).__name__, http_status=getattr(exc, 'status', None))

read('quota_policies', lambda: [dict(name=q.name, state=q.lifecycle_state) for q in oci.pagination.list_call_get_all_results(quotas.list_quotas, TENANCY).data])
for service in ('compute', 'block-storage'):
    def assess(service=service):
        values = oci.pagination.list_call_get_all_results(limits.list_limit_values, TENANCY, service).data
        selected = [v for v in values if 'a1' in v.name.lower() or service == 'block-storage']
        output = []
        for value in selected:
            item = oci.util.to_dict(value)
            try:
                kwargs = dict(availability_domain=value.availability_domain) if value.availability_domain else {}
                item['resource_availability'] = oci.util.to_dict(limits.get_resource_availability(service, value.name, TENANCY, **kwargs).data)
            except Exception as exc:
                item['availability_error'] = dict(error_type=type(exc).__name__, http_status=getattr(exc, 'status', None))
            output.append(item)
        return output
    read(service + '_limits', assess)
read('boot_volumes', lambda: [dict(size_gb=v.size_in_gbs, state=v.lifecycle_state, name=v.display_name) for v in oci.pagination.list_call_get_all_results(block.list_boot_volumes, availability_domain=AD, compartment_id=TENANCY).data])
read('block_volumes', lambda: [dict(size_gb=v.size_in_gbs, state=v.lifecycle_state, name=v.display_name) for v in oci.pagination.list_call_get_all_results(block.list_volumes, compartment_id=TENANCY, availability_domain=AD).data])
atomic(CACHE / 'assessment.json', report)
status_path = CACHE / 'status.json'
if status_path.exists():
    status = json.loads(status_path.read_text())
    if status.get('next_attempt_epoch'):
        from datetime import datetime
        gap = status['next_attempt_epoch'] - datetime.fromisoformat(status['last_result_time']).timestamp()
        assert abs(gap - status['delay_seconds']) < 1
        delay = status['delay_seconds']
        if status['result'] == 'capacity':
            assert 30 <= delay <= 300
            assert delay == status.get('capacity_delay_seconds', 300)
            assert status.get('throttle_streak', 0) == 0
        elif status['result'] == 'throttled' and 'throttle_streak' in status:
            streak = status['throttle_streak']
            assert streak >= 1
            assert delay == max(min(600, 30 * 2 ** min(streak - 1, 5)), status['retry_after_seconds'] or 0)
        else:
            assert delay >= 300
        if status['result'] == 'monitor':
            assert delay == 300
        report['verified_scheduled_delay_seconds'] = status['delay_seconds']
        atomic(CACHE / 'assessment.json', report)
print(json.dumps(report, indent=2))
