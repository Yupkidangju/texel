import pytest

from texel.editing import set_matrix
from texel.model import Validation
from texel.operations import run_batch
from texel.session import ConflictError, Session


def test_preview_apply_and_single_undo_across_sheets(tmp_path):
    s = Session(tmp_path / "batch.texel")
    s.apply("second", lambda w: w.add_sheet("Other"))
    before, revision, history = s.store.path.read_bytes(), s.revision, s.store.history()
    operations = [
        {
            "op": "write",
            "sheet": "Sheet1",
            "start": "A1",
            "values": [["9007199254740993", "=A1+1"]],
        },
        {"op": "write", "sheet": "Other", "start": "A1", "values": [["=Sheet1!B1"]]},
        {"op": "format", "sheet": "Sheet1", "range": "A1:B1", "style": {"bold": True}},
    ]
    preview = run_batch(s, operations, revision, preview=True, diff_limit=1)
    assert preview["changed_cells"] == 3 and preview["truncated"]
    assert len(preview["changes"]) == 1
    assert s.revision == revision and s.store.history() == history
    assert s.store.path.read_bytes() == before
    result = run_batch(s, operations, revision)
    assert result["changed_cells"] == 3 and s.revision == revision + 1
    assert s.evaluator.value(1, 0, 0) == 9007199254740994
    assert s.undo() and s.workbook.sheet().cell(0, 0).raw == ""
    assert s.redo() and s.evaluator.value(1, 0, 0) == 9007199254740994


def test_batch_failure_validation_protection_and_conflict_are_atomic(tmp_path):
    s = Session(tmp_path / "atomic.texel")
    s.apply(
        "validation", lambda w: setattr(w.sheet().cell(0, 1), "validation", Validation(minimum=10))
    )
    operations = [
        {"op": "write", "sheet": "Sheet1", "start": "A1", "values": [["first"]]},
        {"op": "write", "sheet": "Sheet1", "start": "B1", "values": [["1"]]},
    ]
    for preview in (True, False):
        with pytest.raises(ValueError, match="validation"):
            run_batch(s, operations, s.revision, preview=preview)
        assert s.workbook.sheet().cell(0, 0).raw == "" and s.revision == 1
    operations[1]["values"] = [["20"]]
    other = Session(s.store.path)
    other.apply("external", lambda w: set_matrix(w, 0, "C1", [["remote"]]))
    for preview in (True, False):
        with pytest.raises(ConflictError):
            run_batch(s, operations, 1, preview=preview)
    s.reload()
    s.apply(
        "lock",
        lambda w: (
            setattr(w.sheet(), "protected", True),
            setattr(w.sheet().cell(0, 0), "locked", True),
        ),
    )
    with pytest.raises(ValueError, match="protected"):
        run_batch(s, operations, s.revision, preview=True)


def test_batch_bounds_partial_styles_and_error_location(tmp_path):
    s = Session(tmp_path / "bounds.texel")

    def seed(w):
        w.sheet().cell(0, 0).style.background = "#123456"
        w.sheet().cell(0, 0).style.italic = True

    s.apply("style", seed)
    patch = {
        "op": "format",
        "sheet": "Sheet1",
        "range": "A1",
        "style": {"bold": True, "background": None},
    }
    run_batch(s, [patch], s.revision)
    style = s.workbook.sheet().cell(0, 0).style
    assert style.bold and style.italic and style.background == "#123456"
    for operations in (
        [patch] * 51,
        [{**patch, "unexpected": True}],
        [{**patch, "range": "A1:A10000"}, {**patch, "range": "B1"}],
    ):
        with pytest.raises(ValueError):
            run_batch(s, operations, s.revision)
    with pytest.raises(ValueError, match="Operation 2"):
        run_batch(s, [patch, {"op": "clear", "sheet": "Missing", "range": "A1"}], s.revision)


def test_batch_preview_summaries_bound_text_and_metadata(tmp_path):
    s = Session(tmp_path / "preview.texel")
    operations = [
        {"op": "note", "sheet": "Sheet1", "cell": "A1", "note": "x" * 1000},
        {
            "op": "filter",
            "sheet": "Sheet1",
            "range": "A1:A4",
            "conditions": [{"column": 0, "criterion": ">0"}],
        },
    ]
    result = run_batch(s, operations, 0, preview=True)
    assert result["metadata_changed"]
    assert len(result["changes"][0]["after"]["note"]) == 256
    assert result["changes"][0]["after"]["text_truncated"]
    assert s.revision == 0 and not s.workbook.sheet().filter_spec


def test_remaining_batch_operations_share_normal_editing_contracts(tmp_path):
    s = Session(tmp_path / "operations.texel")
    operations = [
        {"op": "write", "sheet": "Sheet1", "start": "A1", "values": [["1"], ["2"]]},
        {"op": "fill", "sheet": "Sheet1", "range": "A1:A3", "direction": "series"},
        {"op": "copy", "sheet": "Sheet1", "range": "A1:A3", "destination": "C1"},
        {"op": "borders", "sheet": "Sheet1", "range": "C1:C3", "border_style": "double"},
        {
            "op": "replace",
            "sheet": "Sheet1",
            "range": "C1:C3",
            "query": "2",
            "replacement": "20",
            "whole_cell": True,
        },
        {"op": "note", "sheet": "Sheet1", "cell": "D1", "note": "literal note"},
        {"op": "clear", "sheet": "Sheet1", "range": "A1"},
    ]
    run_batch(s, operations, 0)
    assert s.revision == 1
    assert s.evaluator.value(0, 1, 2) == 20
    assert s.evaluator.value(0, 2, 2) == 3
    assert s.workbook.sheet().cell(0, 2).style.borders["top"].style == "double"
    assert s.workbook.sheet().cell(0, 3).note == "literal note"
    assert s.workbook.sheet().cell(0, 0).raw == ""
    assert s.undo() and not s.workbook.sheet().cells
