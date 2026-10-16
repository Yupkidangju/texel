from copy import deepcopy

import pytest

from texel.editing import filtered_rows, merge_range, set_matrix
from texel.model import Workbook
from texel.session import Session
from texel.tables import find_next_match, replace_matches, search_cells, set_filter, sort_table


def seed():
    w = Workbook()
    set_matrix(
        w,
        0,
        "A1",
        [
            ["team", "n", "calc"],
            ["b", "2", "=B2*10"],
            ["a", "1", "=B3*10"],
            ["a", "3", "=B4*10"],
            ["a", "3", "=B5*10"],
            ["a", "", ""],
            ["a", "=1/0", ""],
        ],
    )
    w.sheet().cell(3, 0).note = "stable first"
    w.sheet().cell(4, 0).note = "stable second"
    return w


def test_multi_sort_stable_formula_and_blank_error_last():
    w = seed()
    sort_table(w, 0, "A1:C7", [{"column": 0}, {"column": 1, "descending": True}])
    assert [w.sheet().cell(r, 1).raw for r in range(1, 7)] == ["3", "3", "1", "", "=1/0", "2"]
    assert w.sheet().cell(1, 0).note == "stable first"
    assert w.sheet().cell(2, 0).note == "stable second"
    assert w.sheet().cell(1, 2).raw == "=B2*10"
    assert w.sheet().cell(5, 2).raw == ""


def test_multi_sort_merge_and_invalid_keys_are_atomic(tmp_path):
    s = Session(tmp_path / "sort.texel")
    s.apply("seed", lambda w: merge_range(w, 0, "A1:B1"))
    before = s.workbook.to_dict(), s.revision
    with pytest.raises(ValueError):
        s.apply("sort", lambda w: sort_table(w, 0, "A1:C3", [{"column": 0}]))
    assert (s.workbook.to_dict(), s.revision) == before
    w = seed()
    for keys in ([], [{"column": 99}], [{"column": True}], [{"column": 0}] * 9):
        with pytest.raises(ValueError):
            sort_table(w, 0, "A1:C7", keys)


def test_compound_filter_all_any_persistence_and_undo(tmp_path):
    s = Session(tmp_path / "filter.texel")
    s.apply(
        "seed",
        lambda w: set_matrix(w, 0, "A1", [["team", "n"], ["a", "1"], ["b", "3"], ["a", "4"]]),
    )
    s.apply(
        "filter",
        lambda w: set_filter(
            w, 0, "A1:B4", [{"column": 0, "criterion": "a"}, {"column": 1, "criterion": ">2"}]
        ),
    )
    assert filtered_rows(s.workbook, 0) == {1, 2}
    assert filtered_rows(Session(s.store.path).workbook, 0) == {1, 2}
    assert s.workbook.sheet().filter_spec["criterion"] == "a"
    s.apply(
        "any",
        lambda w: set_filter(
            w,
            0,
            "A1:B4",
            [{"column": 0, "criterion": "a"}, {"column": 1, "criterion": ">2"}],
            "any",
        ),
    )
    assert filtered_rows(s.workbook, 0) == set()
    assert s.undo() and filtered_rows(s.workbook, 0) == {1, 2}
    bad = deepcopy(s.workbook)
    bad.sheet().filter_spec["conditions"][1]["column"] = 9
    with pytest.raises(ValueError):
        bad.validate()


def test_search_values_scope_pagination_and_literal_replace(tmp_path):
    w = seed()
    w.add_sheet("Other")
    set_matrix(w, 1, "A1", [["Alpha"], ["alpha beta"], ["=6*7"]])
    found = search_cells(w, "alpha", whole_cell=True)
    assert [(c["sheet"], c["address"]) for c in found["matches"]] == [("Other", "A1")]
    assert search_cells(w, "42", look_in="values")["total"] == 1
    assert search_cells(w, "a", sheet="Other", limit=1)["next_offset"] == 1
    assert search_cells(w, "alpha", sheet="Other", region="A2")["total"] == 1
    assert replace_matches(w, "alpha", r"\1", sheet="Other", whole_cell=True) == 1
    assert w.sheet("Other").cell(0, 0).raw == r"\1"
    assert w.sheet("Other").cell(1, 0).raw == "alpha beta"
    with pytest.raises(ValueError):
        search_cells(w, "")


def test_ui_next_match_advances_beyond_first_api_page():
    w = Workbook()
    set_matrix(w, 0, "A1", [["match"] for _ in range(2100)])
    found = find_next_match(w, "match", (0, 1999, 0))
    assert found == {"position": (0, 2000, 0), "index": 2001, "total": 2100}
    assert find_next_match(w, "match", (0, 2099, 0))["position"] == (0, 0, 0)
