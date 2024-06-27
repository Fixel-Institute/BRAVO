# Guide from https://stackoverflow.com/a/185473

LOCKFILE=/tmp/bravo_processingqueue_lock.txt
if [ -e ${LOCKFILE} ] && kill -0 `cat ${LOCKFILE}`; then
    echo "already running"
    exit
fi

# make sure the lockfile is removed when we exit and then claim it
trap "rm -f ${LOCKFILE}; exit" INT TERM EXIT
echo $$ > ${LOCKFILE}

SCRIPT_DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
$SCRIPT_DIR/venv/bin/python3 $SCRIPT_DIR/ProcessingQueueService.py
#python3 $SCRIPT_DIR/ProcessingQueueService.py

rm -f ${LOCKFILE}