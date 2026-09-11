# Manual hourly reviews

## Round 1 — 2026-09-11

- Baseline: 2026-09-11T00:49:53Z. Evidence cutoff: 2026-09-11T01:58:34Z. Actual elapsed: **4,121 seconds (1h 08m 41s)**. One complete 3,600-second interval plus 521 seconds; one review, not two. No earlier review cache was found. No automation was created or configured.
- Current-run log: **14 capacity results including the baseline**, hence 13 subsequent results; zero accepted launches, throttles, transient errors or permanent errors in that log. These are result records, not independently audited HTTP-request counts. Latest result: 01:55:29.670933Z, HTTP 500 capacity; next scheduled attempt: 02:00:29.668918Z. The older 131-line legacy log contains three explicit HTTP 429 entries but predates the baseline and is excluded from interval counts.
- `oci-vm.service`: active/running, zero systemd restarts, active since 00:49:52Z. Unit has no ExecStop; wrapper executes the inspected local runner with Python contamination variables removed. No restart was needed or performed. Two obsolete desktop-launch units remain failed; the actual service is healthy.
- Real read-only `local_runner.py --check` passed: boot volume AVAILABLE, zero active attachments. This means launch prerequisites, not physical host capacity. Real `check_local.py` passed, assessment timestamp 01:58:15.400047Z; SDK timeout/no-retry assertions and actual 300-second scheduled-delay assertion passed. Both used the existing OCI virtual-environment Python with PYTHONHOME, PYTHONPATH and __PYVENV_LAUNCHER__ removed. No mock tests were run.
- OCI A1 limits: 2 cores and 12 GB available, zero used, at both AD and regional scopes; request is 2 cores/12 GB. No quota policies returned. Root-compartment/configured-AD storage inventory: one AVAILABLE 200-GB boot volume, zero block volumes. Free-storage and total-storage limits report 200 GB used, zero GB remaining. These limits **are not a cost guarantee or proof of Always Free eligibility**, nor proof of physical capacity. Other compartments, regions, backups, network usage and billing were not comprehensively audited. No extra storage should be inferred safe from compute headroom.
- Real desktop notification test failed with exit 127: installed notify-send has an unresolved libnotify symbol. Notification delivery is unavailable; status/log files remain the evidence channel. No package/library changes were attempted. Success-state SSH/banner and notification handling remain untested because no attached instance exists.
- GitHub API confirmed the sole workflow, `capacity.yml`, is `disabled_manually`; workflow configuration was not changed. Review actions made no cloud mutations, extra resources, instance lifecycle calls, machine shutdowns or reboots; the already-authorized local retry service remained running.
- Included previously untracked `local_runner.py` and `check_local.py` after inspection; no runtime code changes. Updated stale README claims and documented the existing local runner/read-only checks. The runner deliberately fails closed after its 23-hour token window without a known instance; reconcile manually rather than clearing state or blindly renewing the token. Local locking does not exclude other hosts. Public changes omit resource identifiers, addresses, fingerprints, emails, credential paths and raw logs.

Commit URL and completion timing are recorded in the private local review cache after push/remote-SHA verification, avoiding a self-referential commit hash in this report.


## Round 2 — 2026-09-11

- Baseline: 2026-09-11T01:58:34Z. Evidence cutoff: 2026-09-11T02:58:52Z. Actual elapsed: **3,618 seconds (1h 00m 18s)**. One complete 3,600-second interval; one review.
- Real read-only `local_runner.py --check` passed: boot volume AVAILABLE, zero active attachments. Real `check_local.py` passed at 02:58:52Z with sanitized OCI venv Python, SDK timeout/no-retry assertions, and the actual 300-second scheduled-delay assertion. No mock tests were run.
- A1 limits remain 2 cores and 12 GB available, zero used, at AD and regional scopes; no quota policies returned. Root-compartment/configured-AD storage inventory remains one AVAILABLE 200-GB boot volume and zero block volumes; free-storage and total-storage limits remain 200 GB used, zero GB remaining. These limits are not billing proof or an Always Free guarantee.
- `oci-vm.service` remained active/running with zero systemd restarts; main process unchanged, unit has no ExecStop. The authorized local retry remained running. No restart, shutdown/reboot, OCI STOP/START/reboot/terminate/delete, extra resource, workflow, or automation action occurred.
- No evidence-backed code defect or unrelated change found. Report-only review.

Commit URL and completion timing are recorded in the private local review cache after push/remote-SHA verification.


## Round 3 — 2026-09-11

- Baseline: 2026-09-11T02:58:52Z. Evidence cutoff: 2026-09-11T03:55:48Z. Actual elapsed: **3,416 seconds (56m 56s)**. **No complete 3,600-second interval; this is not counted as a completed hourly review.**
- Real read-only `local_runner.py --check` passed: boot volume AVAILABLE, zero active attachments. Real `check_local.py` passed at 03:55:48Z with sanitized OCI venv Python, SDK timeout/no-retry assertions, and the actual 300-second scheduled-delay assertion. No mock tests were run.
- A1 limits remain 2 cores and 12 GB available, zero used, at AD and regional scopes; no quota policies returned. Root-compartment/configured-AD storage inventory remains one AVAILABLE 200-GB boot volume and zero block volumes; free-storage and total-storage limits remain 200 GB used, zero GB remaining. These limits are not billing proof or an Always Free guarantee.
- `oci-vm.service` remained active/running with zero systemd restarts; main process unchanged, unit has no ExecStop. The authorized local retry remains running with recent capacity results. No restart, shutdown/reboot, OCI STOP/START/reboot/terminate/delete, extra resource, workflow, or automation action occurred.
- No evidence-backed code defect or unrelated change found. Report-only review. Workflow `capacity.yml` remains `disabled_manually`.

Commit URL and completion timing are recorded in the private local review cache after push/remote-SHA verification.


## Round 4 — 2026-09-11

- Baseline: 2026-09-11T02:58:52Z. Evidence cutoff: 2026-09-11T04:56:12Z. Actual observed interval: **5,840 seconds (1h 37m 20s)**. One complete 3,600-second interval; **one completed hourly review**. The prior 3,416-second observation remains incomplete and is not combined or counted.
- Real read-only `local_runner.py --check` passed at 04:55:57Z: boot volume AVAILABLE, zero active attachments. Real `check_local.py` passed at 04:55:57Z with sanitized OCI venv Python, SDK timeout/no-retry assertions and actual 300-second scheduled-delay assertion. No mock tests were used for OCI evidence; local regression tests separately passed 10/10 in the sanitized OCI venv.
- A1 limits remain 2 cores and 12 GB available, zero used, at AD and regional scopes; no quota policies returned. Root-compartment/configured-AD storage inventory remains one AVAILABLE 200-GB boot volume and zero block volumes; free-storage and total-storage limits remain 200 GB used, zero GB remaining. These limits are not billing proof or an Always Free guarantee.
- The authorized local retry remains running as the OCI venv `local_runner.py` process, with recent real capacity results and the latest status capacity/HTTP 500; no accepted launch, instance attachment or success/SSH path exists. The named `oci-vm.service` is not installed/active in the current inspection environment, so no restart was performed and no cloud ExecStop could be invoked or proven; the runner process was left untouched.
- GitHub API verified the sole workflow remains `capacity.yml`, state `disabled_manually`. No OCI lifecycle mutation, resource creation/deletion, restart, shutdown/reboot, workflow change, automation, or extra resource occurred. No evidence-backed code change was found; report-only review.

Commit URL and completion timing are recorded in the private local review cache after push/remote-SHA verification.
