import csv

import pytest

from texel.analysis import chart_text, deduplicate, pivot_table, profile_range
from texel.editing import set_matrix
from texel.exchange import export_file, load_file, safe_path
from texel.formula import Evaluator
from texel.model import Workbook


def sample():
    w = Workbook()
    set_matrix(
        w,
        0,
        "A1",
        [["부서", "매출", "비용"], ["영업", "10", "3"], ["개발", "20", "5"], ["영업", "30", "7"]],
    )
    return w


def test_profile_and_pivot_use_calculated_values():
    w = sample()
    w.sheet().set_raw(3, 1, "=B2*3")
    report = profile_range(w, 0, "A1:C4")
    assert report["columns"][1]["sum"] == 60
    assert report["columns"][1]["mean"] == 20
    assert report["columns"][0]["unique"] == 2
    index = pivot_table(w, 0, "A1:C4", [0], 1, "sum", "피벗")
    assert index == 1
    assert w.sheet(index).cell(1, 0).raw == "개발"
    assert Evaluator(w).value(index, 1, 1) == 20
    assert Evaluator(w).value(index, 2, 1) == 40


def test_chart_and_deduplication():
    w = sample()
    text = chart_text(w, 0, "A1:B4", "bar")
    assert "영업" in text and "30" in text and "█" in text
    set_matrix(w, 0, "A5", [["영업", "30", "7"]])
    assert deduplicate(w, 0, "A1:C5", True) == 1
    assert w.sheet().cell(4, 0, False).raw == ""


def test_csv_quotes_unicode_and_calculated_values(tmp_path):
    w = sample()
    w.sheet().set_raw(1, 0, '한글,"인용"\n줄바꿈')
    w.sheet().set_raw(1, 1, "=20/2")
    target = tmp_path / "한글.csv"
    export_file(w, target)
    restored = load_file(target)
    assert restored.sheet().cell(1, 0).raw == '한글,"인용"\n줄바꿈'
    assert restored.sheet().cell(1, 1).raw == "10"


def test_xlsx_roundtrip_formula_style_notes_and_sheets(tmp_path):
    w = sample()
    w.add_sheet("분석")
    w.sheet(1).set_raw(0, 0, "=SUM(Sheet1!B2:B4)")
    cell = w.sheet(0).cell(1, 1)
    cell.style.number_format, cell.style.bold, cell.note = "currency", True, "메모"
    w.sheet().freeze_rows = 1
    w.sheet().column_widths[0] = 24
    path = tmp_path / "book.xlsx"
    export_file(w, path)
    result = load_file(path)
    assert Evaluator(result).value(1, 0, 0) == 60
    assert result.sheet().cell(1, 1).note == "메모"
    assert result.sheet().cell(1, 1).style.bold
    assert result.sheet().cell(1, 1).style.number_format == "currency"
    assert result.sheet().freeze_rows == 1
    assert result.sheet().column_widths[0] == 24


def test_failed_export_preserves_file(tmp_path):
    target = tmp_path / "keep.unknown"
    target.write_text("original")
    with pytest.raises(ValueError):
        export_file(sample(), target)
    assert target.read_text() == "original"


def test_mcp_path_scope(tmp_path):
    root = tmp_path / "data"
    root.mkdir()
    assert safe_path(root, "book.xlsx") == root / "book.xlsx"
    with pytest.raises(ValueError):
        safe_path(root, "../escape.xlsx")


def test_csv_protects_text_formula_injection(tmp_path):
    w = Workbook()
    w.sheet().set_raw(0, 0, '\'=HYPERLINK("bad")')
    target = tmp_path / "safe.csv"
    export_file(w, target)
    with target.open(encoding="utf-8-sig", newline="") as source:
        value = next(csv.reader(source))[0]
    assert value == '\'=HYPERLINK("bad")'
