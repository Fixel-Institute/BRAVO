SCRIPT_DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd $SCRIPT_DIR
docker compose pull && docker compose -p bravo up -d
docker image prune -f
