#/bin/bash
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

docker compose --env-file=/dev/null -p bravo up -d
$SCRIPT_DIR/venv/bin/python3 $SCRIPT_DIR/manage.py runserver 0:3001
