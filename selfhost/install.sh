#!/bin/sh
# Install or start the self-hosted stack.
# Usage: selfhost/install.sh <public-host>
# Example: selfhost/install.sh your-host.example
set -eu

cd "$(dirname "$0")"
DOMAIN="${1:-}"
if [ -z "$DOMAIN" ]; then
  echo "usage: selfhost/install.sh <public-host>" >&2
  echo "example: selfhost/install.sh localhost" >&2
  exit 2
fi

if docker info >/dev/null 2>&1; then
  DOCKER=docker
else
  DOCKER="sudo docker"
fi
export SELFHOST_DOCKER="$DOCKER"

if [ ! -f .env ]; then
  postgres_password="$(openssl rand -hex 24)"
  fusionauth_db_password="$(openssl rand -hex 24)"
  fusionauth_api_key="$(python3 -c 'import uuid; print(uuid.uuid4())')"
  jwt_secret="$(openssl rand -hex 32)"
  client_secret="$(openssl rand -hex 32)"
  internal_key="$(openssl rand -hex 32)"
  admin_password="$(openssl rand -hex 18)"
  account_link="$(openssl rand -hex 32)"
  mcp_key="$(openssl rand -base64 32 | tr -d '\n')"
  doc_perm="$(openssl rand -hex 32)"
  sed \
    -e "s/__DOMAIN__/${DOMAIN}/g" \
    -e "s/__POSTGRES_PASSWORD__/${postgres_password}/g" \
    -e "s/__FUSIONAUTH_DB_PASSWORD__/${fusionauth_db_password}/g" \
    -e "s/__FUSIONAUTH_API_KEY__/${fusionauth_api_key}/g" \
    -e "s/__JWT_SECRET__/${jwt_secret}/g" \
    -e "s/__CLIENT_SECRET__/${client_secret}/g" \
    -e "s/__INTERNAL_KEY__/${internal_key}/g" \
    -e "s/__ADMIN_PASSWORD__/${admin_password}/g" \
    -e "s/__ACCOUNT_LINK__/${account_link}/g" \
    -e "s|__MCP_KEY__|${mcp_key}|g" \
    -e "s/__DOC_PERM__/${doc_perm}/g" \
    .env.example > .env
  chmod 600 .env
  umask 077
  {
    echo "FusionAuth admin console user: admin@localhost"
    echo "FusionAuth admin password: ${admin_password}"
    echo "The admin user is for FusionAuth itself, not the Macro app."
    echo "Sign in to the app with any email and a password of 8 or more characters."
  } > credentials.txt
  chmod 600 credentials.txt
  echo "wrote .env and credentials.txt"
else
  echo "keeping existing .env"
fi

export DOMAIN
python3 kickstart.py

echo "building images"
# One image at a time. Two Rust compiles together do not fit a small VPS.
COMPOSE_PARALLEL_LIMIT=1 $DOCKER compose build

echo "starting data stores"
$DOCKER compose up -d postgres redis localstack search kafka
echo "waiting for postgres"
postgres_user="$(grep '^POSTGRES_USER=' .env | cut -d= -f2-)"
postgres_db="$(grep '^POSTGRES_DB=' .env | cut -d= -f2-)"
i=0
while ! $DOCKER compose exec -T postgres pg_isready -U "$postgres_user" -d "$postgres_db" >/dev/null 2>&1; do
  i=$((i + 1))
  if [ "$i" -gt 60 ]; then
    echo "postgres did not become ready" >&2
    exit 1
  fi
  sleep 2
done

echo "preparing localstack"
$DOCKER compose up localstack-init

echo "migrating"
python3 migrate.py

echo "starting the application"
$DOCKER compose up -d

echo
echo "Open https://${DOMAIN}/app/"
echo "The first email and password you submit creates the account."
