from __future__ import annotations

import json
import sqlite3
import zlib
from contextlib import contextmanager
from pathlib import Path

from .model import Cell, Sheet, Workbook


class ConflictError(ValueError):
    def __init__(self, expected: int, actual: int):
        self.expected, self.actual = expected, actual
        super().__init__(
            f"Revision conflict: expected {expected}, actual {actual}. Reload and retry."
        )


def metadata(book):
    return {
        "sheets": [s.metadata() for s in book.sheets],
        "active_sheet": book.active_sheet,
        "named_ranges": book.named_ranges,
    }


def encode(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def make_patch(before: Workbook, after: Workbook):
    changes = []
    for i in range(max(len(before.sheets), len(after.sheets))):
        old = before.sheets[i].cells if i < len(before.sheets) else {}
        new = after.sheets[i].cells if i < len(after.sheets) else {}
        for r, c in old.keys() | new.keys():
            previous = old[(r, c)].to_dict() if (r, c) in old else None
            following = new[(r, c)].to_dict() if (r, c) in new else None
            if previous != following:
                changes.append([i, r, c, previous, following])
    return {"cells": changes, "before": metadata(before), "after": metadata(after)}


class Store:
    def __init__(self, path: Path | str, *, read_only=False):
        self.path = Path(path).resolve()
        self.read_only = read_only
        existing = self.path.exists()
        if existing and not read_only:
            # 기존 입력은 WAL 설정이나 생성 전에 읽기 전용으로 검사한다.
            Store(self.path, read_only=True).load()
        if not read_only:
            self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            tables = {
                row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")
            }
            if tables and "texel_state" not in tables:
                raise ValueError("This SQLite file is not a Texel workbook")
            if "texel_state" not in tables:
                if existing or read_only:
                    raise ValueError("This SQLite file is not a Texel workbook")
                db.executescript("""
                    CREATE TABLE texel_state (
                        singleton INTEGER PRIMARY KEY CHECK(singleton=1), schema_version INTEGER,
                        revision INTEGER, cursor INTEGER, metadata TEXT NOT NULL
                    );
                    CREATE TABLE cells (
                        sheet INTEGER, row INTEGER, col INTEGER, data TEXT NOT NULL,
                        PRIMARY KEY(sheet,row,col)
                    );
                    CREATE TABLE history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT, label TEXT, source TEXT,
                        created TEXT DEFAULT CURRENT_TIMESTAMP, patch BLOB NOT NULL
                    );
                """)
                db.execute(
                    "INSERT INTO texel_state VALUES (1,1,0,0,?)", (encode(metadata(Workbook())),)
                )
            state = db.execute(
                "SELECT schema_version FROM texel_state WHERE singleton=1"
            ).fetchone()
            if state is None or not {"cells", "history"} <= tables and existing:
                raise ValueError("Incomplete Texel workbook schema")
            version = state[0]
            if version != 1:
                raise ValueError(f"Unsupported Texel schema: {version}")
            if not read_only:
                db.execute("PRAGMA journal_mode=WAL")

    @contextmanager
    def connect(self):
        db = sqlite3.connect(
            self.path.as_uri() + "?mode=ro" if self.read_only else self.path,
            timeout=5,
            uri=self.read_only,
        )
        try:
            db.execute("PRAGMA busy_timeout=5000")
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    @property
    def revision(self):
        with self.connect() as db:
            return db.execute("SELECT revision FROM texel_state WHERE singleton=1").fetchone()[0]

    def load(self) -> tuple[Workbook, int]:
        try:
            return self._load()
        except (TypeError, KeyError, IndexError, AttributeError) as exc:
            raise ValueError(f"Invalid workbook metadata: {exc}") from exc

    def _load(self) -> tuple[Workbook, int]:
        with self.connect() as db:
            db.execute("BEGIN")
            revision, raw = db.execute(
                "SELECT revision,metadata FROM texel_state WHERE singleton=1"
            ).fetchone()
            data = json.loads(raw)
            sheets = [Sheet.from_dict(s) for s in data["sheets"]]
            for sheet, r, c, content in db.execute("SELECT sheet,row,col,data FROM cells"):
                if not 0 <= sheet < len(sheets):
                    raise ValueError("Workbook contains cells for an unknown sheet")
                sheets[sheet].cells[(r, c)] = Cell.from_dict(json.loads(content))
        book = Workbook(
            sheets, data["active_sheet"], {k: tuple(v) for k, v in data["named_ranges"].items()}
        )
        book.validate()
        return book, revision

    def check_revision(self, db, expected):
        actual, cursor = db.execute(
            "SELECT revision,cursor FROM texel_state WHERE singleton=1"
        ).fetchone()
        if actual != expected:
            raise ConflictError(expected, actual)
        return actual, cursor

    def apply_patch(self, db, patch, forward):
        side = "after" if forward else "before"
        for sheet, row, col, before, after in patch["cells"]:
            value = after if forward else before
            if value is None:
                db.execute("DELETE FROM cells WHERE sheet=? AND row=? AND col=?", (sheet, row, col))
            else:
                db.execute(
                    "INSERT OR REPLACE INTO cells VALUES (?,?,?,?)",
                    (sheet, row, col, encode(value)),
                )
        db.execute(
            "UPDATE texel_state SET metadata=?,revision=revision+1 WHERE singleton=1",
            (encode(patch[side]),),
        )

    def commit(self, before, after, expected, label, source="tui") -> int:
        patch = make_patch(before, after)
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            actual, cursor = self.check_revision(db, expected)
            if not patch["cells"] and patch["before"] == patch["after"]:
                return actual
            db.execute("DELETE FROM history WHERE id>?", (cursor,))
            row = db.execute(
                "INSERT INTO history(label,source,patch) VALUES(?,?,?)",
                (label, source, zlib.compress(encode(patch).encode("utf-8"))),
            )
            self.apply_patch(db, patch, True)
            db.execute("UPDATE texel_state SET cursor=? WHERE singleton=1", (row.lastrowid,))
            db.execute(
                "DELETE FROM history WHERE id NOT IN (SELECT id FROM history ORDER BY id DESC LIMIT 100)"
            )
        return actual + 1

    def navigate_history(self, expected, redo=False) -> bool:
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            _, cursor = self.check_revision(db, expected)
            query = (
                "SELECT id,patch FROM history WHERE id>? ORDER BY id LIMIT 1"
                if redo
                else "SELECT id,patch FROM history WHERE id<=? ORDER BY id DESC LIMIT 1"
            )
            entry = db.execute(query, (cursor,)).fetchone()
            if entry is None:
                return False
            entry_id, raw = entry
            self.apply_patch(db, json.loads(zlib.decompress(raw)), redo)
            if redo:
                new_cursor = entry_id
            else:
                new_cursor = db.execute(
                    "SELECT COALESCE(MAX(id),0) FROM history WHERE id<?", (entry_id,)
                ).fetchone()[0]
            db.execute("UPDATE texel_state SET cursor=? WHERE singleton=1", (new_cursor,))
        return True

    def history(self):
        with self.connect() as db:
            cursor = db.execute("SELECT cursor FROM texel_state WHERE singleton=1").fetchone()[0]
            return [
                {
                    "id": i,
                    "label": label,
                    "source": source,
                    "created": created,
                    "applied": i <= cursor,
                }
                for i, label, source, created in db.execute(
                    "SELECT id,label,source,created FROM history ORDER BY id DESC"
                )
            ]

    def backup(self, destination):
        destination = Path(destination).resolve()
        if destination == self.path:
            raise ValueError("Backup destination must differ from the current workbook")
        if destination.exists():
            raise FileExistsError("Backup destination already exists")
        destination.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as source, sqlite3.connect(destination) as target:
            source.backup(target)
