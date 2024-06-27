curl -O https://uf-bravo.jcagle.solutions/static/docker-compose.yml
docker compose pull && docker compose -p bravo up -d
docker container prune -f && docker image prune -f
rm docker-compose.yml 