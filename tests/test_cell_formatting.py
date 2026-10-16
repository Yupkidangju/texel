import pytest

from texel import editing
from texel.addresses import CellRange
from texel.exchange import export_file, load_file
from texel.model import CellStyle, Workbook
from texel.session import Session


def test_border_presets_and_native_undo(tmp_path):
    session = Session(tmp_path / "borders.texel")
    session.apply(
        "borders", lambda w: editing.apply_borders(w, 0, "A1:C3", "outer", "thick", "#ffcc00")
    )
    sheet = session.workbook.sheet()
    assert sheet.cell(0, 0).style.borders["top"].style == "thick"
    assert sheet.cell(1, 0).style.borders["left"].color == "#ffcc00"
    assert not sheet.cell(1, 1, False).style.borders
    restored = Session(session.store.path)
    assert restored.workbook.sheet().cell(2, 2).style.borders["bottom"].style == "thick"
    restored.undo()
    assert not restored.workbook.sheet().cell(0, 0, False).style.borders
    restored.redo()
    assert restored.workbook.sheet().cell(0, 0).style.borders["left"].style == "thick"


def test_extended_style_xlsx_round_trip(tmp_path):
    w = Workbook()
    w.sheet().set_raw(0, 0, "한글 줄바꿈\n두 번째 줄")
    w.sheet().cell(0, 0).style = CellStyle(
        bold=True, italic=True, strike=True, wrap=True, vertical_align="middle"
    )
    w.sheet().row_heights[0] = 3
    editing.apply_borders(w, 0, "A1:B2", "all", "double", "#336699")
    editing.merge_range(w, 0, "A1:B2")
    path = tmp_path / "style.xlsx"
    export_file(w, path)
    restored = load_file(path)
    style = restored.sheet().cell(0, 0).style
    assert style.bold and style.italic and style.strike and style.wrap
    assert style.vertical_align == "middle"
    assert style.borders["top"].style == "double"
    assert style.borders["left"].color == "#336699"
    assert restored.sheet().row_heights[0] == 3
    assert restored.sheet().merges == ["A1:B2"]


def test_merged_copy_cut_and_transpose_preserve_structure():
    w = Workbook()
    w.sheet().set_raw(0, 0, "title")
    editing.merge_range(w, 0, "A1:C2")
    editing.copy_range(w, 0, "A1:C2", "A4")
    assert "A4:C5" in w.sheet().merges
    assert w.sheet().cell(3, 0).raw == "title"
    editing.copy_range(w, 0, "A1:C2", "E1", transpose=True, cut=True)
    assert "E1:F3" in w.sheet().merges
    assert "A1:C2" not in w.sheet().merges
    assert w.sheet().cell(0, 4).raw == "title"
    with pytest.raises(ValueError):
        editing.copy_range(w, 0, "E1:E2", "H1")


def test_merge_combine_and_unmerge_keep_data_undo(tmp_path):
    s = Session(tmp_path / "merge.texel")
    s.apply("seed", lambda w: editing.set_matrix(w, 0, "A1", [["first", "second"]]))
    s.apply("merge", lambda w: editing.merge_range(w, 0, "A1:B1", contents="combine"))
    assert "first" in s.workbook.sheet().cell(0, 0).raw
    assert "second" in s.workbook.sheet().cell(0, 0).raw
    assert s.workbook.sheet().cell(0, 1).raw == ""
    s.undo()
    assert s.workbook.sheet().cell(0, 1).raw == "second"
    assert not s.workbook.sheet().merges


def test_clear_format_preserves_content_and_rules():
    w = Workbook()
    w.sheet().set_raw(0, 0, "42")
    editing.apply_borders(w, 0, "A1", "all", "medium")
    w.sheet().cell(0, 0).note = "note"
    editing.clear_formats(w, 0, "A1")
    assert w.sheet().cell(0, 0).style == CellStyle()
    assert w.sheet().cell(0, 0).raw == "42"
    assert w.sheet().cell(0, 0).note == "note"


def test_old_style_document_loads_with_defaults():
    w = Workbook.from_dict(
        {"sheets": [{"name": "old", "cells": {"A1": {"raw": "1", "style": {"bold": True}}}}]}
    )
    style = w.sheet().cell(0, 0).style
    assert style.bold and not style.wrap and not style.borders


@pytest.mark.parametrize(
    "preset", ["all", "outer", "inner", "top", "bottom", "left", "right", "none"]
)
def test_all_border_presets_are_valid(preset):
    w = Workbook()
    editing.apply_borders(w, 0, "B2:D4", preset, "medium")
    w.validate()
    assert w.sheet().used_range.right <= CellRange.parse("B2:D4").right
