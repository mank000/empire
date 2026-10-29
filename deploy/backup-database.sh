#!/bin/sh
set -eu
PATH=/usr/local/bin:/usr/bin:/bin

PROJECT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$PROJECT_DIR"
docker compose -f compose.prod.yaml exec -T web python deploy/backup_database.py
