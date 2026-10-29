"""Создать согласованную копию SQLite и оставить 14 последних копий."""

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def backup_database(source, directory, keep=14):
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    destination = directory / f"empire-{stamp}.sqlite3"
    temporary = directory / f".{destination.name}.tmp"
    try:
        with sqlite3.connect(source.resolve().as_uri() + "?mode=ro", uri=True) as database:
            with sqlite3.connect(temporary) as backup:
                database.backup(backup)
                if backup.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                    raise RuntimeError("Проверка целостности резервной копии не прошла")
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)

    copies = sorted(directory.glob("empire-????????T????????????Z.sqlite3"), reverse=True)
    for old_copy in copies[keep:]:
        old_copy.unlink()
    return destination


if __name__ == "__main__":
    source = Path(os.environ.get("DJANGO_DB_PATH", "/app/data/db.sqlite3"))
    if not source.is_file():
        raise SystemExit(f"База не найдена: {source}")
    print(backup_database(source, Path(os.environ.get("BACKUP_DIR", "/app/backups"))))
