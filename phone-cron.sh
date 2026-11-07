#!/bin/sh
set -eu
umask 077
home=/var/lib/oci-a1
marker="$home/paused"
[ ! -e "$marker" ] || exit 0
cd /opt/oci-a1/app
exec /usr/bin/flock -n "$home/cron.lock" /usr/bin/python3 /opt/oci-a1/app/phone_cron.py
