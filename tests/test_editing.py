import pytest

from texel.addresses import CellRange
from texel.editing import (
    copy_range,
    fill_range,
    merge_range,
    rename_sheet,
    set_matrix,
    shift_axis,
    sort_range,
)
from texel.formula import Evaluator
from texel.model import Validation, Workbook
from texel.session import ConflictError, Session


def test_persistent_undo_redo_and_revision_conflict(tmp_path):
    path = tmp_path / "book.texel"
    first, second = Session(path), Session(path)
    first.apply("write", lambda w: set_matrix(w, 0, "A1", [["10", "=A1*2"]]))
    assert first.revision == 1
    with pytest.raises(ConflictError):
        second.apply("stale", lambda w: set_matrix(w, 0, "A1", [["lost"]]))
    second.reload()
    assert second.evaluator.value(0, 0, 1) == 20
    second.undo()
    third = Session(path)
    assert third.evaluator.value(0, 0, 0) is None
    third.redo()
    assert third.evaluator.value(0, 0, 1) == 20
    third.undo()
    third.apply("branch", lambda w: set_matrix(w, 0, "A1", [["30"]]))
    assert not third.redo()


def test_failed_validation_is_atomic(tmp_path):
    session = Session(tmp_path / "rules.texel")
    session.apply(
        "rule",
        lambda w: setattr(w.sheet().cell(0, 1), "validation", Validation(minimum=0, maximum=100)),
    )
    revision = session.revision
    with pytest.raises(ValueError):
        session.apply("batch", lambda w: set_matrix(w, 0, "A1", [["saved?", "101"]]))
    assert session.revision == revision
    assert session.workbook.sheet().cell(0, 0, False).raw == ""
    session.apply(
        "protected",
        lambda w: (
            setattr(w.sheet(), "protected", True),
            setattr(w.sheet().cell(0, 0), "locked", True),
        ),
    )
    with pytest.raises(ValueError):
        session.apply("locked", lambda w: set_matrix(w, 0, "A1", [["no"]]))


def test_copy_fill_and_literal_refs():
    w = Workbook()
    set_matrix(w, 0, "A1", [["1", '=A1+$A$1+LEN("A1")'], ["2", ""]])
    copy_range(w, 0, "B1", "B2")
    assert w.sheet().cell(1, 1).raw == '=A2+$A$1+LEN("A1")'
    assert Evaluator(w).value(0, 1, 1) == 5
    fill_range(w, 0, "A1:A5", "series")
    assert Evaluator(w).value(0, 4, 0) == 5


def test_structure_updates_cross_sheet_and_absolute_refs():
    w = Workbook()
    set_matrix(w, 0, "A1", [["10"], ["20"], ["30"]])
    w.add_sheet("분석")
    set_matrix(w, 1, "A1", [['=SUM(Sheet1!$A$1:A3)+LEN("A1")']])
    shift_axis(w, 0, "row", 1, 1, False)
    assert Evaluator(w).value(1, 0, 0) == 62
    assert "A4" in w.sheet(1).cell(0, 0).raw
    shift_axis(w, 0, "row", 1, 1, True)
    assert Evaluator(w).value(1, 0, 0) == 62
    rename_sheet(w, 0, "매출 자료")
    assert "'매출 자료'!" in w.sheet(1).cell(0, 0).raw
    assert Evaluator(w).value(1, 0, 0) == 62


def test_deleted_range_boundary_contract():
    w = Workbook()
    set_matrix(w, 0, "A1", [["1"], ["2"], ["3"], ["=SUM(A1:A3)"]])
    shift_axis(w, 0, "row", 0, 1, True)
    assert Evaluator(w).value(0, 2, 0) == 5


def test_sort_with_header_and_formulas():
    w = Workbook()
    set_matrix(w, 0, "A1", [["name", "n", "x"], ["b", "2", "=B2*2"], ["a", "1", "=B3*2"]])
    sort_range(w, 0, "A1:C3", 0, False, True)
    assert w.sheet().cell(1, 0).raw == "a"
    assert Evaluator(w).value(0, 1, 2) == 2


def test_merge_rejects_data_loss():
    w = Workbook()
    set_matrix(w, 0, "A1", [["a", "b"]])
    with pytest.raises(ValueError):
        merge_range(w, 0, "A1:B1")
    w.sheet().set_raw(0, 1, "")
    merge_range(w, 0, "A1:B1")
    assert w.sheet().merge_anchor(0, 1) == (0, 0)
    assert CellRange.parse(w.sheet().merges[0]).size == 2
