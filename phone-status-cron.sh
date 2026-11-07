#!/bin/sh
set -eu
umask 077
export HOME=/var/lib/oci-a1
export PYTHONDONTWRITEBYTECODE=1
exec /usr/bin/flock -n /var/lib/oci-a1/status.lock /opt/oci-a1/venv/bin/python /opt/oci-a1/app/phone_status.py --port 18791
