import pytest

from texel.editing import copy_range, set_matrix, shift_axis
from texel.exchange import export_file, load_file
from texel.formula import Evaluator
from texel.model import Validation, Workbook
from texel.session import Session


def test_removing_locked_cell_is_rejected(tmp_path):
    s = Session(tmp_path / "lock.texel")

    def protect(w):
        set_matrix(w, 0, "A1", [["10"]])
        w.sheet().cell(0, 0).locked = True
        w.sheet().protected = True

    s.apply("protect", protect)
    with pytest.raises(ValueError):
        s.apply("remove", lambda w: w.sheet().cells.pop((0, 0)))
    assert s.evaluator.value(0, 0, 0) == 10


def test_dependent_validation_is_enforced_atomically(tmp_path):
    s = Session(tmp_path / "dependent.texel")

    def initial(w):
        set_matrix(w, 0, "A1", [["2", "=A1*2"]])
        w.sheet().cell(0, 1).validation = Validation(minimum=0, maximum=10)

    s.apply("initial", initial)
    with pytest.raises(ValueError):
        s.apply("invalid dependency", lambda w: set_matrix(w, 0, "A1", [["10"]]))
    assert s.evaluator.value(0, 0, 1) == 4


def test_invalid_style_and_validation_metadata_are_rejected():
    w = Workbook()
    w.sheet().cell(0, 0).style.foreground = "not-a-color"
    with pytest.raises(ValueError):
        w.validate()
    w.sheet().cell(0, 0).style.foreground = ""
    w.sheet().cell(0, 0).validation = Validation(minimum=10, maximum=0)
    with pytest.raises(ValueError):
        w.validate()


def test_cut_updates_qualified_range_both_ends():
    w = Workbook()
    set_matrix(w, 0, "A1", [["1"], ["2"]])
    w.add_sheet("Analysis")
    set_matrix(w, 1, "A1", [["=SUM(Sheet1!A1:A2)"]])
    copy_range(w, 0, "A1:A2", "B3", cut=True)
    assert Evaluator(w).value(1, 0, 0) == 3
    assert w.sheet(1).cell(0, 0).raw == "=SUM(Sheet1!B3:B4)"


def test_structure_moves_chart_and_conditional_ranges():
    w = Workbook()
    w.sheet().conditional_rules.append(
        {"range": "A1:A3", "operator": "greaterThan", "value": 1, "color": "#0f766e"}
    )
    w.sheet().charts.append({"range": "A1:B3", "kind": "bar"})
    shift_axis(w, 0, "row", 1, 1)
    assert w.sheet().conditional_rules[0]["range"] == "A1:A4"
    assert w.sheet().charts[0]["range"] == "A1:B4"


def test_named_ranges_survive_xlsx_round_trip(tmp_path):
    w = Workbook()
    set_matrix(w, 0, "A1", [["1"], ["2"], ["=SUM(Revenue)"]])
    w.named_ranges["Revenue"] = ("Sheet1", "A1:A2")
    path = tmp_path / "names.xlsx"
    export_file(w, path)
    restored = load_file(path)
    assert Evaluator(restored).value(0, 2, 0) == 3


def test_rept_rejects_oversized_result_before_allocation():
    w = Workbook()
    w.sheet().set_raw(0, 0, '=REPT("long",1000000)')
    assert str(Evaluator(w).value(0, 0, 0)) == "#LIMIT!"


def test_copy_merged_cells_cannot_silently_discard_structure():
    w = Workbook()
    w.sheet().merges = ["A1:B1"]
    w.sheet().set_raw(0, 0, "label")
    copy_range(w, 0, "A1:B1", "A3")
    assert "A3:B3" in w.sheet().merges
    with pytest.raises(ValueError):
        copy_range(w, 0, "A1", "A5")
