#!/bin/sh
# Rebuild images from the current checkout and restart. Volumes are kept.
# Usage: selfhost/upgrade.sh
set -eu
cd "$(dirname "$0")"
if [ ! -f .env ]; then
  echo "no .env; run install.sh first" >&2
  exit 1
fi
if docker info >/dev/null 2>&1; then
  DOCKER=docker
else
  DOCKER="sudo docker"
fi
export SELFHOST_DOCKER="$DOCKER"
python3 kickstart.py
COMPOSE_PARALLEL_LIMIT=1 $DOCKER compose build
$DOCKER compose up -d postgres redis localstack search kafka
python3 migrate.py
$DOCKER compose up -d
echo "upgraded"
