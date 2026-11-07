#!/bin/sh
set -eu
umask 077
export HOME=/var/lib/oci-a1
export OCI_VENV=/opt/oci-a1/venv
export OCI_NOTIFY_DESKTOP=false
export OCI_NOTIFY_NTFY_FILE="$HOME/.config/oci-a1/ntfy-url"
export OCI_NOTIFY_NTFY_HOSTS=ntfy.sh
export OCI_CAPACITY_MAX_DELAY=30
cd /opt/oci-a1/app
exec "$OCI_VENV/bin/python" /opt/oci-a1/app/local_runner.py
