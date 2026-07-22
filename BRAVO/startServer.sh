#/bin/bash
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
$SCRIPT_DIR/venv/bin/python3 -m uvicorn BRAVO.asgi:application --reload --host 0.0.0.0 --port 27286