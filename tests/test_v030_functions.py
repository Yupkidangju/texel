from datetime import date

import pytest

from texel.editing import set_matrix
from texel.formula import Evaluator, function_names
from texel.functions import criterion_matches
from texel.model import Workbook
from texel.values import Error


def calculate(formula):
    book = Workbook()
    set_matrix(book, 0, "A1", [["a", "2"], ["b", "4"], ["a", "6"]])
    book.sheet().set_raw(0, 3, formula)
    return Evaluator(book).value(0, 0, 3)


@pytest.mark.parametrize(
    "formula,expected",
    [
        ('=AVERAGEIF(A1:A3,"a",B1:B3)', 4),
        ('=AVERAGEIFS(B1:B3,A1:A3,"a",B1:B3,">2")', 6),
        ('=MINIFS(B1:B3,A1:A3,"a")', 2),
        ('=MAXIFS(B1:B3,A1:A3,"a")', 6),
        ('=MINIFS(B1:B3,A1:A3,"none")', 0),
        ("=SUMPRODUCT(B1:B3,B1:B3)", 56),
        ('=IFNA(MATCH("none",A1:A3,0),42)', 42),
        ("=IFNA(7,1/0)", 7),
        ("=IFS(FALSE,1/0,TRUE,42,TRUE,1/0)", 42),
        ('=ISNA(MATCH("none",A1:A3,0))', True),
        ("=ISNA(1/0)", False),
        ("=ISEVEN(-4)", True),
        ("=ISODD(-3)", True),
        ("=SIGN(-20)", -1),
        ("=TRUNC(-12.345,2)", -12.34),
        ("=TRUNC(129,-1)", 120),
        ("=QUOTIENT(-7,2)", -3),
        ('=EXACT("A","a")', False),
        ('=CLEAN("a\tb\nc")', "abc"),
        ('=REPLACE("abcdef",2,3,"XY")', "aXYef"),
        ("=EDATE(DATE(2024,1,31),1)", date(2024, 2, 29)),
        ("=EOMONTH(DATE(2024,1,5),1)", date(2024, 2, 29)),
        ("=NETWORKDAYS(DATE(2026,10,12),DATE(2026,10,16))", 5),
        ("=NETWORKDAYS(DATE(2026,10,16),DATE(2026,10,12))", -5),
        ("=NETWORKDAYS(DATE(2026,10,12),DATE(2026,10,16),DATE(2026,10,14))", 4),
        ("=WORKDAY(DATE(2026,10,16),1)", date(2026, 10, 19)),
        ("=WORKDAY(DATE(2026,10,19),-1)", date(2026, 10, 16)),
        ("=WORKDAY(DATE(2026,10,16),1,DATE(2026,10,19))", date(2026, 10, 20)),
    ],
)
def test_extended_function_examples(formula, expected):
    assert calculate(formula) == expected


@pytest.mark.parametrize(
    "formula,code",
    [
        ('=AVERAGEIFS(B1:B3,A1:A3,"none")', "#DIV/0!"),
        ('=AVERAGEIFS(B1:B2,A1:B1,"a")', "#VALUE!"),
        ("=SUMPRODUCT(B1:B2,A1:B1)", "#VALUE!"),
        ('=SUMIFS(B1:B2,A1:B1,"a")', "#VALUE!"),
        ("=IFNA(1/0,42)", "#DIV/0!"),
        ("=IFS(FALSE,1)", "#N/A"),
        ("=IFS(TRUE)", "#VALUE!"),
        ("=WORKDAY(DATE(2026,1,1),100001)", "#LIMIT!"),
        ('=REPLACE("abc",0,1,"x")', "#VALUE!"),
    ],
)
def test_extended_function_boundaries(formula, code):
    value = calculate(formula)
    assert isinstance(value, Error) and value.code == code


def test_criteria_precision_and_excel_wildcard_escape():
    assert criterion_matches(9007199254740993, "9007199254740993")
    assert not criterion_matches(9007199254740992, "9007199254740993")
    assert criterion_matches("a*b", "a~*b")
    assert criterion_matches("a?b", "a~?b")
    assert criterion_matches("[a]", "[a]")
    assert not criterion_matches("a", "[a]")


def test_registry_and_holiday_deduplication():
    assert len(function_names()) == 89
    book = Workbook()
    set_matrix(book, 0, "A1", [["2026-10-19"], ["2026-10-19"], ["2026-10-18"]])
    book.sheet().set_raw(0, 1, "=WORKDAY(DATE(2026,10,16),1,A1:A3)")
    assert Evaluator(book).value(0, 0, 1) == date(2026, 10, 20)
