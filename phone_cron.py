"""Cron supervisor for the OCI runner in the phone chroot."""
import os
from pathlib import Path
import subprocess
import sys

HOME = Path('/var/lib/oci-a1')
PAUSED = HOME / 'paused'
EXIT = HOME / 'last-exit'
RUNNER = '/opt/oci-a1/app/phone-supervisor.sh'


def main():
    if PAUSED.exists():
        return 0
    state = EXIT.read_text().strip() if EXIT.exists() else ''
    if state == '2':
        return 0
    try:
        process = subprocess.Popen([RUNNER], start_new_session=True,
                                   stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL)
        result = process.wait()
    except OSError:
        result = 1
    pending = EXIT.with_suffix('.tmp')
    pending.write_text(f'{result}\n')
    pending.chmod(0o600)
    os.replace(pending, EXIT)
    return 0


if __name__ == '__main__':
    sys.exit(main())
