from copy import deepcopy

from texel.diagnostics import evaluate_formula, trace_dependencies
from texel.editing import merge_range, set_matrix
from texel.model import Workbook
from texel.navigation import cycle_reference, jump_target


def test_formula_evaluation_diagnostics_are_read_only():
    w = Workbook()
    set_matrix(w, 0, "A1", [["6", "=A1*7"]])
    w.add_sheet("Other")
    w.sheet(1).set_raw(0, 0, "=Sheet1!B1+1")
    w.named_ranges["Source"] = ("Sheet1", "A1:B1")
    w.sheet(1).set_raw(1, 0, "=SUM(Source)")
    before = deepcopy(w.to_dict())
    assert evaluate_formula(w, "Sheet1", "=ROW()+SUM(A1:B1)", "D5")["value"] == 53
    assert evaluate_formula(w, "Sheet1", "=1/0")["error"]["code"] == "#DIV/0!"
    trace = trace_dependencies(w, "Sheet1", "B1")
    assert trace["precedents"] == [{"sheet": "Sheet1", "range": "A1"}]
    assert trace["dependents"] == [
        {"sheet": "Other", "cell": "A1"},
        {"sheet": "Other", "cell": "A2"},
    ]
    assert not trace["truncated"]
    assert w.to_dict() == before


def test_trace_static_branches_cycles_and_limit():
    w = Workbook()
    set_matrix(w, 0, "A1", [["=IF(TRUE,B1,C1)", "=A1", "=A1"]])
    trace = trace_dependencies(w, 0, "A1", limit=1)
    assert len(trace["precedents"]) == len(trace["dependents"]) == 1
    assert trace["truncated"]
    w.sheet().cell(0, 0).raw = "=UNKNOWN!B1"
    assert trace_dependencies(w, 0, "A1")["unresolved"]


def test_expression_context_does_not_shadow_source_cell():
    w = Workbook()
    set_matrix(w, 0, "A1", [["6"], ["7"]])
    assert evaluate_formula(w, "Sheet1", "=SUMPRODUCT(A1:A2,A1:A2)")["value"] == 85
    assert evaluate_formula(w, "Sheet1", "=A1+ROW()", "A1")["value"] == 7
    assert w.sheet().cell(0, 0).raw == "6"


def test_sparse_jump_data_blocks_hidden_and_merge():
    w = Workbook()
    set_matrix(w, 0, "A1", [["1", "2", "3"]])
    set_matrix(w, 0, "G1", [["7", "8"]])
    s = w.sheet()
    assert jump_target(s, (0, 0), "right") == (0, 2)
    assert jump_target(s, (0, 2), "right") == (0, 6)
    assert jump_target(s, (0, 6), "right") == (0, 7)
    assert jump_target(s, (0, 7), "left") == (0, 6)
    s.hidden_columns.add(1)
    assert jump_target(s, (0, 0), "right") == (0, 2)
    s.set_raw(999999, 0, "tail")
    assert jump_target(s, (0, 0), "down") == (999999, 0)
    assert jump_target(s, (0, 0), "down", hidden_rows={999999}) == (1048575, 0)
    merge_range(w, 0, "D1:F1")
    s.cell(0, 3).raw = "merge"
    assert jump_target(s, (0, 3), "right") == (0, 7)


def test_f4_reference_cycle_and_selection_excludes_literals_qualifiers():
    value, cursor = "=A1", 3
    for expected in ("=$A$1", "=A$1", "=$A1", "=A1"):
        value, cursor = cycle_reference(value, cursor)
        assert value == expected
    source = "=SUM(A1:B2)+\"C3\"+'D4'!E5"
    value, _ = cycle_reference(source, len(source), 0, len(source))
    assert value == "=SUM($A$1:$B$2)+\"C3\"+'D4'!$E$5"
    assert cycle_reference('="A1"', 4)[0] == '="A1"'
    assert cycle_reference("=SUM(A1", 7)[0] == "=SUM($A$1"
