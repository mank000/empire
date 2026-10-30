import shutil
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from restore_database import restore_database


class RestoreDatabaseTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="impery-restore-test-"))
        self.addCleanup(shutil.rmtree, self.root)
        self.target = self.root / "db.sqlite3"
        self.backups = self.root / "backups"
        self.backups.mkdir()
        with sqlite3.connect(self.target) as database:
            database.execute("CREATE TABLE tickets (phone TEXT)")
            database.execute("INSERT INTO tickets VALUES ('first')")
        self.source = self.backups / "empire-test.sqlite3"
        shutil.copyfile(self.target, self.source)

    def test_restore_preserves_previous_database(self):
        with sqlite3.connect(self.target) as database:
            database.execute("INSERT INTO tickets VALUES ('second')")

        previous = restore_database(self.source, self.target, self.backups)

        with sqlite3.connect(self.target) as database:
            self.assertEqual(database.execute("SELECT phone FROM tickets").fetchall(), [("first",)])
        with sqlite3.connect(previous) as database:
            self.assertEqual(database.execute("SELECT phone FROM tickets").fetchall(), [("first",), ("second",)])

    def test_corrupt_copy_does_not_replace_current_database(self):
        self.source.write_bytes(b"not a SQLite database")
        with self.assertRaises(sqlite3.DatabaseError):
            restore_database(self.source, self.target, self.backups)
        with sqlite3.connect(self.target) as database:
            self.assertEqual(database.execute("SELECT phone FROM tickets").fetchall(), [("first",)])

    def test_restore_removes_old_wal_sidecars(self):
        with closing(sqlite3.connect(self.target)) as database:
            database.execute("PRAGMA journal_mode=WAL")
            database.execute("INSERT INTO tickets VALUES ('second')")
            database.commit()

        restore_database(self.source, self.target, self.backups)

        with closing(sqlite3.connect(self.target)) as database:
            self.assertEqual(database.execute("SELECT phone FROM tickets").fetchall(), [("first",)])
