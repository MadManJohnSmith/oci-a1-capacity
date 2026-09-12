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
    try:
        status = json.loads(status_path.read_text())
    except Exception:
        status = {}
    if status.get('next_attempt_epoch') and status.get('last_result_time') and status.get('delay_seconds') is not None:
        from datetime import datetime
        gap = status['next_attempt_epoch'] - datetime.fromisoformat(status['last_result_time']).timestamp()
        assert abs(gap - status['delay_seconds']) < 1
        delay = status['delay_seconds']
        if status.get('result') == 'capacity':
            assert 10 <= delay <= 305
            base = status.get('capacity_delay_seconds', 10)
            assert abs(delay - base) <= 3.5
            assert status.get('throttle_streak', 0) == 0
            if 'response_category' in status:
                assert status['response_category'] == 'capacity'
        elif status.get('result') == 'throttled' and 'throttle_streak' in status:
            streak = status['throttle_streak']
            assert streak >= 1
            assert delay == max(min(600, 30 * 2 ** min(streak - 1, 5)), status.get('retry_after_seconds') or 0)
            assert status.get('response_category') == 'throttled'
        else:
            assert delay >= 300
        if status.get('result') == 'monitor':
            assert delay == 300
        report['verified_scheduled_delay_seconds'] = status['delay_seconds']
        atomic(CACHE / 'assessment.json', report)

import sys
if '--markdown' in sys.argv:
    import re
    from pathlib import Path
    reviews_path = Path(__file__).resolve().parent / 'reports/hourly-reviews.md'
    baseline = None
    if reviews_path.exists():
        matches = re.findall(r'Evidence cutoff:\s*([0-9T:\.\-+Z]+)', reviews_path.read_text())
        if matches:
            baseline = matches[-1].rstrip('.')
    from datetime import datetime
    now_stamp = report['checked_at']
    now_dt = datetime.fromisoformat(now_stamp)
    baseline_dt = datetime.fromisoformat(baseline) if baseline else now_dt
    interval_sec = max(0.0, (now_dt - baseline_dt).total_seconds())
    complete = interval_sec >= 3600
    complete_str = "counted as one complete review window." if complete else "Incomplete; below 3,600 seconds and not counted as a completed hourly review."

    log_path = CACHE / 'runner.log'
    attempts = 0
    durations = []
    if log_path.exists():
        for line in log_path.read_text().splitlines():
            if 'Attempt=' in line:
                try:
                    payload = json.loads(line.split('Attempt=', 1)[1])
                    t_str = payload.get('attempt_started')
                    if t_str:
                        if datetime.fromisoformat(t_str) >= baseline_dt:
                            attempts += 1
                            if 'duration_seconds' in payload:
                                durations.append(payload['duration_seconds'])
                    else:
                        attempts += 1
                        if 'duration_seconds' in payload:
                            durations.append(payload['duration_seconds'])
                except Exception:
                    pass
    dur_str = f"{min(durations):.3f}–{max(durations):.3f} seconds" if durations else "no parsed attempts"
    sched_delay = report.get('verified_scheduled_delay_seconds')
    active = report.get('attachment_count')
    storage = report.get('boot_volumes', [])
    markdown_attempts = f"{attempts} parsed attempts" if attempts else "no parsed attempts"
    markdown_delay = f"{sched_delay:g} seconds" if isinstance(sched_delay, (int, float)) else "not verified"

    md = f"""## Local OCI review — {now_stamp[:10]}{'' if complete else ' (incomplete)'}

- Baseline: {baseline or 'not available'}. Evidence cutoff: {now_stamp}. Observed interval: **{interval_sec:,.6f} seconds**. {complete_str}
- Read-only OCI check: boot volume state **{report.get('boot_state', 'unknown')}**, active attachment count **{active if active is not None else 'unknown'}**, and scheduled delay **{markdown_delay}**. No launch operation is performed by this report command.
- Local log summary: **{markdown_attempts}**; parsed duration range **{dur_str}**. The report does not infer unobserved response categories or claim that no instance exists outside the queried attachment set.
- Quota/storage observations: compute and storage values are copied from the current assessment when available; they are not billing proof, capacity proof, or an Always Free guarantee.
- This is a draft generated from local state and read-only OCI results. Review it before publishing and remove identifiers or operational details that should remain private.
"""
    print(md)
else:
    print(json.dumps(report, indent=2))
