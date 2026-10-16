import tracemalloc

import pytest

from texel.analysis import deduplicate, pivot_table, profile_range
from texel.editing import set_matrix, shift_axis
from texel.exchange import export_file, load_file
from texel.formula import Evaluator, translate_formula
from texel.model import Workbook


def test_analysis_preserves_distinct_large_numeric_values():
    w = Workbook()
    set_matrix(w, 0, "A1", [["key", "n"], ["1234567890123", "10"], ["1234567890124", "20"]])
    assert profile_range(w, 0, "A1:B3")["columns"][0]["unique"] == 2
    index = pivot_table(w, 0, "A1:B3", [0], 1)
    assert w.sheet(index).used_range.bottom == 2
    assert Evaluator(w).value(index, 1, 1) == 10
    assert Evaluator(w).value(index, 2, 1) == 20
    assert deduplicate(w, 0, "A1:B3") == 0


def test_exact_integer_and_csv_values_are_not_display_rounded(tmp_path):
    w = Workbook()
    w.sheet().set_raw(0, 0, "9007199254740993")
    w.sheet().set_raw(1, 0, "1234567890123")
    assert Evaluator(w).value(0, 0, 0) == 9007199254740993
    path = tmp_path / "exact.csv"
    export_file(w, path)
    restored = load_file(path)
    assert Evaluator(restored).value(0, 0, 0) == 9007199254740993
    assert Evaluator(restored).value(0, 1, 0) == 1234567890123


def test_cell_shaped_sheet_names_are_not_translated():
    assert translate_formula("=A1!B1", 1, 0) == "=A1!B2"
    w = Workbook()
    w.add_sheet("A1")
    w.sheet(1).set_raw(0, 1, "10")
    w.sheet(0).set_raw(0, 0, "=A1!B1")
    shift_axis(w, 1, "row", 0)
    assert w.sheet(0).cell(0, 0).raw == "=A1!B2"
    assert Evaluator(w).value(0, 0, 0) == 10


@pytest.mark.parametrize(
    "formula,at,expected",
    [("=SUM(A3:A1)", 2, 3), ("=SUM(A3:A1)", 0, 5), ("=SUM(Sheet1!A1:Sheet1!A3)", 0, 5)],
)
def test_structural_delete_shrinks_both_range_directions(formula, at, expected):
    w = Workbook()
    set_matrix(w, 0, "A1", [["1"], ["2"], ["3"]])
    w.sheet().set_raw(4, 1, formula)
    shift_axis(w, 0, "row", at, delete=True)
    assert Evaluator(w).value(0, 3, 1) == expected


def test_rept_and_concatenation_reject_before_large_allocation():
    w = Workbook()
    w.sheet().set_raw(0, 0, "'" + "x" * 8192)
    w.sheet().set_raw(0, 1, "=REPT(A1,1000)")
    tracemalloc.start()
    value = Evaluator(w).value(0, 0, 1)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    assert str(value) == "#LIMIT!"
    assert peak < 2_000_000
    w.sheet().set_raw(0, 1, '=REPT("x",-1)')
    assert str(Evaluator(w).value(0, 0, 1)) == "#VALUE!"
    w.sheet().set_raw(0, 1, "=CONCAT(A1,A1,A1,A1,A1)")
    assert str(Evaluator(w).value(0, 0, 1)) == "#LIMIT!"


@pytest.mark.parametrize("extension", [".texel", ".xlsx"])
def test_malformed_exchange_files_are_user_errors(tmp_path, extension):
    path = tmp_path / ("bad" + extension)
    path.write_text("not this format")
    with pytest.raises(ValueError):
        load_file(path)
    assert path.read_text() == "not this format"
