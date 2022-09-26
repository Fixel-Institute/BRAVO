#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
from pathlib import Path
import json

import DatabaseManager

BASE_DIR = Path(__file__).resolve().parent
if os.path.exists(os.path.join(BASE_DIR, '.env')):
    with open(os.path.join(BASE_DIR, '.env'), "r") as file:
        config = json.load(file)
    for key in config.keys():
        os.environ[key] = config[key]

    sys.path.append(os.environ["PYTHON_UTILITY"])

def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'BRAVO.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)

if __name__ == '__main__':
    if not DatabaseManager.processInput(sys.argv):
        main()