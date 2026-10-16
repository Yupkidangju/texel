import sqlite3

import pytest

from texel.editing import set_matrix
from texel.session import Session


def test_sqlite_reopens_and_history_is_bounded(tmp_path):
    path = tmp_path / "history.texel"
    session = Session(path)
    for i in range(105):
        session.apply("value", lambda w, i=i: set_matrix(w, 0, "A1", [[str(i)]]))
    assert Session(path).evaluator.value(0, 0, 0) == 104
    assert len(session.store.history()) == 100
    backup = tmp_path / "backup.texel"
    session.store.backup(backup)
    assert Session(backup).evaluator.value(0, 0, 0) == 104


def test_unsupported_schema_and_malformed_file(tmp_path):
    path = tmp_path / "bad.texel"
    path.write_text("not sqlite")
    with pytest.raises((ValueError, sqlite3.DatabaseError)):
        Session(path)
