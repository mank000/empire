#!/bin/sh
set -eu
PATH=/usr/local/bin:/usr/bin:/bin

if [ "$#" -ne 1 ]; then
    echo "Использование: $0 empire-YYYYMMDDTHHMMSSffffffZ.sqlite3" >&2
    exit 2
fi
case "$1" in
    empire-*.sqlite3) ;;
    *) echo "Укажите имя копии из каталога backups/" >&2; exit 2 ;;
esac
case "$1" in
    */*|*..*) echo "Путь к копии не должен содержать каталог" >&2; exit 2 ;;
esac

PROJECT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$PROJECT_DIR"
services=$(docker compose -f compose.prod.yaml config --services)
for service in dispatcher beat worker backup web nginx; do
    if printf '%s\n' "$services" | grep -Fxq "$service"; then
        docker compose -f compose.prod.yaml stop "$service"
    fi
done
docker compose -f compose.prod.yaml run --rm --no-deps web python deploy/restore_database.py "/app/backups/$1"
docker compose -f compose.prod.yaml up -d
