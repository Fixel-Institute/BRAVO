#/bin/bash
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

$SCRIPT_DIR/venv/bin/python3 $SCRIPT_DIR/manage.py runserver 0:3001
