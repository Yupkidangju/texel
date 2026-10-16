import tracemalloc
from datetime import date

import pytest

from texel.editing import set_matrix
from texel.formula import Evaluator
from texel.model import Workbook
from texel.tables import replace_matches
from texel.values import Error


def test_replace_rejects_expansion_before_large_allocation():
    w = Workbook()
    w.sheet().set_raw(0, 0, "a" * 1024)
    replacement = "x" * 32767
    tracemalloc.start()
    try:
        with pytest.raises(ValueError, match="limit"):
            replace_matches(w, "a", replacement)
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert peak < 2_000_000
    assert w.sheet().cell(0, 0).raw == "a" * 1024


@pytest.mark.parametrize(
    "formula,code",
    [
        ('=SUMIF(A1:B1,">0",C1:C2)', "#VALUE!"),
        ('=SUMIF(A1:A2,">0",B1:B2)', "#DIV/0!"),
    ],
)
def test_sumif_obeys_common_aggregate_contract(formula, code):
    w = Workbook()
    set_matrix(w, 0, "A1", [["1", "TRUE", "10"], ["1", "=1/0", "20"]])
    w.sheet().set_raw(0, 3, formula)
    result = Evaluator(w).value(0, 0, 3)
    assert isinstance(result, Error) and result.code == code


def test_workday_accepts_exact_calendar_limit():
    w = Workbook()
    w.sheet().set_raw(0, 0, "=WORKDAY(DATE(2026,1,7),71428)")
    assert Evaluator(w).value(0, 0, 0) == date(2299, 10, 23)
