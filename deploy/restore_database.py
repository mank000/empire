"""Восстановить SQLite из проверенной копии после остановки всех сервисов."""

import os
import shutil
import sqlite3
import sys
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from backup_database import private_temporary_file


def check_database(path):
    with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as database:
        if database.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise RuntimeError(f"База повреждена: {path}")


def restore_database(source, target, backup_dir):
    source = source.resolve()
    target = target.resolve()
    if source == target or not source.is_file() or not target.is_file():
        raise ValueError("Укажите существующую копию и существующую базу")
    check_database(source)
    backup_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    before = backup_dir / f"pre-restore-{stamp}.sqlite3"
    saved_path = private_temporary_file(backup_dir, f".{before.name}.")
    try:
        with closing(sqlite3.connect(target)) as current:
            with closing(sqlite3.connect(saved_path)) as saved:
                current.backup(saved)
            if current.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()[0]:
                raise RuntimeError("Текущая база занята; остановите все сервисы")
        check_database(saved_path)
        os.replace(saved_path, before)
    finally:
        saved_path.unlink(missing_ok=True)

    temporary = private_temporary_file(target.parent, f".{target.name}.restore.")
    try:
        shutil.copyfile(source, temporary)
        check_database(temporary)
        for suffix in ("-wal", "-shm"):
            target.with_name(target.name + suffix).unlink(missing_ok=True)
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)
    return before


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Использование: restore_database.py /app/backups/empire-...sqlite3")
    previous = restore_database(
        Path(sys.argv[1]),
        Path(os.environ.get("DJANGO_DB_PATH", "/app/data/db.sqlite3")),
        Path(os.environ.get("BACKUP_DIR", "/app/backups")),
    )
    print(f"Восстановлено; предыдущая база сохранена: {previous}")
