#!/bin/sh
VENV="${OCI_VENV:-$HOME/venvs/oci-official}"
exec env -u PYTHONHOME -u PYTHONPATH -u __PYVENV_LAUNCHER__ "$VENV/bin/python" "$@"
