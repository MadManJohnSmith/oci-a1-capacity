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


## Round 5 — 2026-09-11

- Baseline: 2026-09-11T04:56:12Z. Evidence cutoff: 2026-09-11T06:05:02.380650Z. Actual observed interval: **4,130.380650 seconds (1h 08m 50.380650s)**. One complete 3,600-second interval; **one completed hourly review**.
- Real read-only `local_runner.py --check` passed at 06:04:59Z: boot volume AVAILABLE, zero active attachments. Real `check_local.py` passed at 06:05:02Z with sanitized OCI SDK, timeout/no-retry assertions, and the actual 60-second scheduled-delay assertion. No mock OCI checks were used.
- During this interval, the running authorized local retry recorded **2 capacity results**, both launch HTTP 500 responses, with attempt durations **2.775s** and **1.235s**, effective delays **60s** and **60s**, no Retry-After values, throttle streak 0, and no recovery/accepted launch. No 429, network, or permanent result was measured in the current interval. The older legacy log's 429s remain outside this baseline and are not counted.
- A1 limits report 2 cores and 12 GB available, zero used, at AD and regional scopes; no quota policies returned. Root-compartment/configured-AD storage remains one AVAILABLE 200-GB boot volume and zero block volumes; total/free storage remains 200 GB used, zero GB remaining. These limits are not billing proof or an Always Free guarantee.
- The authorized local retry process remains running; systemd unit inspection shows active/running, unchanged main PID, zero restarts, and no ExecStop action. No local restart was performed. GitHub API verified `capacity.yml` remains `disabled_manually`. No OCI lifecycle mutation, resource creation/deletion, shutdown/reboot, workflow change, automation, mock, or unrelated code change occurred.
- No evidence-backed implementation defect was found; report-only review. Public report contains no OCIDs, IPs, fingerprints, emails, credentials, personal paths, or raw logs.

Commit URL and completion timing are recorded in the private local review cache after push/remote-SHA verification.


## Round 6 — 2026-09-11

- Baseline: 2026-09-11T06:05:02.380650Z (commit `50f4d3d`). Evidence cutoff: 2026-09-11T06:56:20.245311Z. Actual observed interval: **3,077.864661 seconds (51m 17.864661s)**. **No complete 3,600-second interval; this observation is not counted as a completed hourly review.** The retry process remained running; incomplete elapsed time was not counted.
- Real read-only `local_runner.py --check` passed at 06:55:56Z: boot volume AVAILABLE, zero active attachments. Real `check_local.py` passed at 06:56:20Z with sanitized OCI SDK, timeout/no-retry assertions, and the actual 60-second scheduled-delay assertion. No mock OCI checks were used.
- The sequential authorized retry recorded **50 capacity results**, each launch HTTP 500, from 06:06:01Z through 06:56:12Z. Attempt durations were **0.933–3.059s (mean 1.438s)**; effective wait was **60s for every attempt**; no `Retry-After`, 429, network, transient, permanent, accepted, or recovery result occurred. No instance was created or attached.
- A1 limits remain 2 OCPU and 12 GB available, zero used, at AD and regional scopes; no quota policies returned. Root-compartment/configured-AD storage remains one AVAILABLE 200-GB boot volume and zero block volumes; total/free storage remains 200 GB used, zero GB available. These limits are not billing proof or an Always Free guarantee.
- The authorized local retry process remains running under the sanitized OCI venv (`local_runner.py`, one process, sequential/no burst). `oci-vm.service` is inactive/dead in this inspection environment with zero restarts and no ExecStop; no local restart was performed, and the running process was left untouched. GitHub API verified the sole workflow remains `capacity.yml`, `disabled_manually`.
- No OCI lifecycle mutation, resource creation/deletion, shutdown/reboot, workflow change, automation, mock, or unrelated code change occurred. This is report-only because no evidence-backed implementation defect was found. Public report contains no OCIDs, IPs, fingerprints, emails, credentials, personal paths, or raw logs.

Commit URL and remote SHA verification follow after committing and pushing this report.

## Round 7 — 2026-09-11

- Baseline: 2026-09-11T06:05:02.380650Z (commit `f58b8be`). Evidence cutoff: 2026-09-11T07:56:22.660000Z. Actual observed interval: **6,680.279350 seconds (1h 51m 20.279350s)**. **One complete 3,600-second interval; one completed hourly review**.
- Real read-only `local_runner.py --check` passed at 07:56:21Z: boot volume AVAILABLE, zero active attachments. Real `check_local.py` passed at 07:56:22Z with sanitized OCI SDK, timeout/no-retry assertions, and the actual 60-second scheduled-delay assertion. No mock OCI checks were used.
- The sequential authorized retry recorded **108 capacity results**, each launch HTTP 500, from 06:06:01Z through 07:55:35Z. Attempt durations were **0.925–3.163s (mean 1.457s)**; effective wait was **60s for every attempt**; no `Retry-After`, 429, network, transient, permanent, accepted, or recovery result occurred. No instance was created or attached.
- A1 limits remain 2 OCPU and 12 GB available, zero used, at AD and regional scopes; no quota policies returned. Root-compartment/configured-AD storage remains one AVAILABLE 200-GB boot volume and zero block volumes; total/free storage remains 200 GB used, zero GB available. These limits are not billing proof or an Always Free guarantee.
- The authorized local retry process remains running under the sanitized OCI venv (`local_runner.py`, one process, sequential/no burst). `oci-vm.service` is inactive/dead in this inspection environment with zero restarts and no ExecStop; no local restart was performed, and the running process was left untouched. GitHub API verification remains that the sole workflow `capacity.yml` is `disabled_manually`.
- No OCI lifecycle mutation, resource creation/deletion, shutdown/reboot, workflow change, automation, mock, or unrelated code change occurred. This is report-only because no evidence-backed implementation defect was found. Public report contains no OCIDs, IPs, fingerprints, emails, credentials, personal paths, or raw logs.

Commit URL and remote SHA verification follow after committing and pushing this report.


## Round 8 — 2026-09-11

- Baseline: 2026-09-11T07:56:22.660000Z. Evidence cutoff: 2026-09-11T08:56:24.239045Z. Actual observed interval: **3,601.579045 seconds (1h 00m 01.579045s)**. **One complete 3,600-second interval; one completed hourly review.**
- Real read-only `local_runner.py --check` passed at 08:56:23Z: boot volume AVAILABLE, zero active attachments. Real `check_local.py` passed at 08:56:24Z with sanitized OCI SDK, timeout/no-retry assertions, and the actual 60-second scheduled-delay assertion. Local regression tests passed 10/10. No mock OCI checks were used.
- The sequential authorized retry recorded **59 capacity results**, each launch HTTP 500, from 07:56:38Z through 08:56:01Z. Attempt durations were **0.923–3.079s (mean 1.426s)**; effective wait was **60s for every attempt**; `Retry-After` was absent on every result, throttle streak remained 0, and no transient, network, permanent, accepted, or recovery result occurred. No instance was created or attached.
- The authorized local retry process remains running under the sanitized OCI venv (`local_runner.py`, one process, sequential/no burst). `oci-vm.service` is not installed in this inspection environment (`LoadState=not-found`, inactive/dead, zero restarts); therefore no restart was performed and no cloud ExecStop could be invoked. The running process was left untouched. GitHub workflow listing was unavailable for the configured remote (HTTP 404), so disabled workflow state could not be independently re-verified in this environment; no workflow mutation was attempted.
- No OCI lifecycle mutation, resource creation/deletion, shutdown/reboot, workflow change, automation, mock, or evidence-backed implementation change occurred. Report-only review. Public report contains no OCIDs, IPs, fingerprints, emails, credentials, personal paths, or raw logs.

Commit URL and remote SHA verification follow after committing and pushing this report.

## Round 9 — 2026-09-11

- Baseline: 2026-09-11T08:56:24.239045Z (commit `0e50f16`). Evidence cutoff: 2026-09-11T09:56:24.831412Z. Actual observed interval: **3,600.592367 seconds (1h 00m 00.592367s)**. **One complete 3,600-second interval; one completed hourly review.**
- Real read-only `local_runner.py --check` passed at 09:56:24Z: boot volume AVAILABLE, zero active attachments. Real `check_local.py` passed at 09:56:24Z with sanitized OCI SDK, timeout/no-retry assertions, and actual 60-second scheduled-delay assertion. No mock OCI checks were used.
- The sequential authorized retry recorded **58 capacity results**, each launch HTTP 500, from 08:57:02Z through 09:55:23Z. Attempt durations were **0.919–2.819s (mean 1.420s)**; effective wait was **60s for every attempt**; `Retry-After` was absent on all 58 results, throttle streak remained 0, and no 429, transient, network, permanent, accepted, or recovery result occurred. No instance was created or attached.
- A1 limits remain 2 OCPU and 12 GB available, zero used, at AD and regional scopes; no quota policies returned. Root-compartment/configured-AD storage remains one AVAILABLE 200-GB boot volume and zero block volumes; total/free storage remains 200 GB used, zero GB available. These limits are not billing proof or an Always Free guarantee.
- The authorized local retry process remains running under the sanitized OCI venv (`local_runner.py`, one process, sequential/no burst). `oci-vm.service` inspection was unavailable in this shell; the runner PID was observed running and was left untouched. No local restart was performed, and no cloud ExecStop was invoked. GitHub API verified the sole workflow remains `capacity.yml`, `disabled_manually`.
- No OCI lifecycle mutation, resource creation/deletion, shutdown/reboot, workflow change, automation, mock, or evidence-backed implementation change occurred. Report-only review. Public report contains no OCIDs, IPs, fingerprints, emails, credentials, personal paths, or raw logs.

Commit URL and remote SHA verification follow after committing and pushing this report.


## Round 10 — 2026-09-11

- Baseline: 2026-09-11T09:56:24.831412Z (commit `5d92444`). Evidence cutoff: 2026-09-11T10:55:54.920056Z. Actual observed interval: **3,570.088644 seconds (59m 30.088644s)**. **No complete 3,600-second interval; this final observation is incomplete and is not counted as a completed hourly review.**
- Real read-only `local_runner.py --check` passed at 10:55:54Z: boot volume AVAILABLE, zero active attachments. Real `check_local.py` passed with sanitized OCI SDK, timeout/no-retry assertions, and actual 60-second scheduled-delay assertion. No mock OCI checks were used.
- The sequential authorized retry recorded **59 capacity results**, each launch HTTP 500, from 09:56:24Z through 10:55:48Z. Attempt durations were **0.972–2.448s (mean 1.457s)**; effective wait was **60s for every attempt**; `Retry-After` was absent on all 59 results, throttle streak remained 0, and no 429, transient, network, permanent, accepted, or recovery result occurred. No instance was created or attached. This reports the observed absence only; it does not claim that 429 never occurred outside this interval.
- A1 limits remain 2 OCPU and 12 GB available, zero used, at AD and regional scopes; no quota policies returned. Root-compartment/configured-AD storage remains one AVAILABLE 200-GB boot volume and zero block volumes; total/free storage remains 200 GB used, zero GB available. These limits are not billing proof or an Always Free guarantee.
- The authorized local retry process remains running under the sanitized OCI venv (`local_runner.py`, one process, sequential/no burst). `oci-vm.service` inspection reports `LoadState=not-found`, inactive/dead, zero restarts and no ExecStop; no restart was necessary or performed, and no cloud ExecStop was invoked. GitHub API verified the sole workflow remains `capacity.yml`, `disabled_manually`.
- No OCI lifecycle mutation, resource creation/deletion, shutdown/reboot, workflow change, automation, mock, or evidence-backed implementation change occurred. Report-only review. Public report contains no OCIDs, IPs, fingerprints, emails, credentials, personal paths, or raw logs.

Commit URL and remote SHA verification follow after committing and pushing this report.

## Persistent cycle review — 2026-09-11

- Baseline: 2026-09-11T10:55:54.920056Z, the prior recorded cutoff. Evidence cutoff: 2026-09-11T16:00:57.044693Z. Actual observed interval: **18,302.124637 seconds**. This exceeds 3,600 seconds and is counted as one complete review window.
- Real read-only `local_runner.py --check` passed at 16:00:55Z: boot volume AVAILABLE and zero active attachments. Real `check_local.py` passed at 16:00:57Z with the configured OCI SDK timeout/no-retry checks and a verified 300-second scheduled delay. No mocks were used.
- The sequential runner process remained active (one process, no burst). The observed log interval contains **18 capacity results**, each launch HTTP 500. Request durations were **1.973–5.432 seconds**; effective wait was **300 seconds** after every result; `Retry-After` was absent; no 429, network, transient, permanent, accepted, or recovery result was observed. No instance was created or attached.
- Current OCI state: boot volume AVAILABLE, zero active attachments, no observed instance identity; A1 availability is 2 OCPU and 12 GB at the checked AD and regional scopes; configured storage inventory is one 200-GB boot volume and no block volumes, with 200 GB used and no remaining free allocation in the reported free-storage quota. These observations are not billing proof or an Always Free guarantee.
- `oci-vm.service` is not installed or visible in this environment (`systemctl cat` reported no files), so no restart was attempted. The runner PID and command were verified directly and left untouched. GitHub Actions workflow listing returned no entries; no workflow was enabled or dispatched.
- No OCI lifecycle mutation, resource creation/deletion, automation, mock, or code change was made. The public report contains no OCIDs, IPs, fingerprints, emails, credentials, personal paths, or raw logs.

## Persistent cycle review — 2026-09-11 (incomplete)

- Baseline: 2026-09-11T16:00:57.044693Z. Evidence cutoff: 2026-09-11T17:00:34.499955Z. Actual observed interval: **3,577.455262 seconds**. **Incomplete; below 3,600 seconds and not counted as a completed hourly review.**
- Real read-only `local_runner.py --check` passed at 17:00:33Z: boot volume AVAILABLE and zero active attachments. Real `check_local.py` passed at 17:00:34Z with the configured OCI SDK timeout/no-retry checks and a verified 300-second scheduled delay. No mocks were used.
- The sequential runner process remained active (one process, no burst). The interval contained **11 capacity results**, each launch HTTP 500. Request durations were **1.973–4.314 seconds**; effective wait was **300 seconds** after every result; `Retry-After` was absent; no 429, network, transient, permanent, accepted, or recovery result was observed. No instance was created or attached.
- Current OCI state: boot volume AVAILABLE, zero active attachments; A1 availability is 2 OCPU and 12 GB at the checked AD and regional scopes; configured storage inventory is one 200-GB boot volume and no block volumes, with 200 GB used and no remaining free allocation in the reported free-storage quota. These observations are not billing proof or an Always Free guarantee.
- `oci-vm.service` is not installed or visible in this environment (`systemctl cat` reported no files), so no restart was attempted. The runner PID and command were verified directly and left untouched. GitHub Actions workflow listing returned no entries; no workflow was enabled or dispatched.
- No OCI lifecycle mutation, resource creation/deletion, automation, mock, or code change was made. The public report contains no OCIDs, IPs, fingerprints, emails, credentials, personal paths, or raw logs.

## Persistent cycle review — 2026-09-11

- Baseline: 2026-09-11T17:00:34.499955Z. Evidence cutoff: 2026-09-11T18:00:58.994500Z. Actual observed interval: **3,624.494545 seconds**. This exceeds 3,600 seconds and is counted as one complete review window.
- Real read-only `local_runner.py --check` passed at 18:00:57Z: boot volume AVAILABLE and zero active attachments. Real `check_local.py` passed at 18:00:58Z with the configured OCI SDK timeout/no-retry checks and a verified 300-second scheduled delay. No mocks were used.
- The sequential runner process remained active (one process, no burst). The interval contained **12 capacity results**, each launch HTTP 500. Request durations were **1.804–3.415 seconds**; effective wait was **300 seconds** after every result; `Retry-After` was absent; no 429, network, transient, permanent, accepted, or recovery result was observed. No instance was created or attached.
- Current OCI state: boot volume AVAILABLE, zero active attachments; A1 availability is 2 OCPU and 12 GB at the checked AD and regional scopes; configured storage inventory is one 200-GB boot volume and no block volumes, with 200 GB used and no remaining free allocation in the reported free-storage quota. These observations are not billing proof or an Always Free guarantee.
- `oci-vm.service` is not installed or visible in this environment (`systemctl cat` reported no files), so no restart was attempted. The runner PID and command were verified directly and left untouched. GitHub Actions workflow listing returned no entries; no workflow was enabled or dispatched.
- No OCI lifecycle mutation, resource creation/deletion, automation, mock, or code change was made. The public report contains no OCIDs, IPs, fingerprints, emails, credentials, personal paths, or raw logs.
