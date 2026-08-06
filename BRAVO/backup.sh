#!/bin/bash
SCRIPT_DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

cd $SCRIPT_DIR
source $SCRIPT_DIR/venv/bin/activate

python3 $SCRIPT_DIR/manage.py dumpdata --natural-foreign --natural-primary -e auth.permission -e contenttypes.contenttype --indent 4 > $BACKUP_PATH/BRAVOSql_$(date +%Y%m%d_%H%M%S).json
sudo cp -r $DATASERVER_PATH $BACKUP_PATH
