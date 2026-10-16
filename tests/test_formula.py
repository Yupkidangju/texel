from datetime import date

import pytest

from texel.addresses import CellRange, address, parse_address
from texel.formula import Evaluator, translate_formula
from texel.model import Workbook


@pytest.fixture
def book():
    wb = Workbook()
    for ref, raw in {"A1": "10", "A2": "20", "A3": "hello", "B1": "=A1+A2*2"}.items():
        wb.sheet().set_raw(*parse_address(ref), raw)
    return wb


@pytest.mark.parametrize(
    "ref,coord", [("A1", (0, 0)), ("$AA$100", (99, 26)), ("XFD1048576", (1048575, 16383))]
)
def test_address_round_trip(ref, coord):
    assert parse_address(ref) == coord
    assert parse_address(address(*coord)) == coord


@pytest.mark.parametrize("ref", ["A0", "XFE1", "A1048577", "../A1", "A1:A2"])
def test_address_rejects_invalid(ref):
    with pytest.raises(ValueError):
        parse_address(ref)


@pytest.mark.parametrize(
    "formula,expected",
    [
        ("=A1+A2*2", 50),
        ("=SUM(A1:A3)", 30),
        ("=AVERAGE(A1:A3)", 15),
        ("=COUNT(A1:A4)", 2),
        ("=COUNTA(A1:A4)", 3),
        ("=2^3^2", 512),
        ("=-2^2", -4),
        ("=50%*200", 100),
        ("=IF(A1>5,99,1/0)", 99),
        ("=IFERROR(1/0,42)", 42),
        ('=SUMIF(A1:A3,">15")', 20),
        ('=COUNTIF(A1:A3,"*ell*")', 1),
        ("=ROUND(2.675,2)", 2.68),
        ('=LEFT("한국어",2)&"!"', "한국!"),
        ('=TEXTJOIN("-",TRUE,A1:A3)', "10-20-hello"),
        ("=DATE(2026,10,10)", date(2026, 10, 10)),
        ("=VLOOKUP(20,A1:B2,2,FALSE)", None),
        ("=INDEX(A1:A3,2)", 20),
        ("=MATCH(20,A1:A3,0)", 2),
        ('=XLOOKUP(20,A1:A3,B1:B3,"missing")', None),
        ("=SUM(A4,2)", 2),
        ("=TRUE", True),
    ],
)
def test_formula_features(book, formula, expected):
    book.sheet().set_raw(5, 3, formula)
    assert Evaluator(book).value(0, 5, 3) == expected


@pytest.mark.parametrize(
    "formula,error",
    [
        ("=1/0", "#DIV/0!"),
        ("=UNKNOWN(1)", "#NAME?"),
        ('=SUM("x")', "#VALUE!"),
        ("=SQRT(-1)", "#NUM!"),
        ('=__import__("os")', "#NAME?"),
        ("=A1.__class__", "#VALUE!"),
        ("=XFE1", "#REF!"),
        ("=A1+", "#VALUE!"),
    ],
)
def test_formula_errors_are_data(book, formula, error):
    book.sheet().set_raw(8, 3, formula)
    assert str(Evaluator(book).value(0, 8, 3)) == error
    assert book.sheet().cell(8, 3).raw == formula


def test_cycles_and_cross_sheet(book):
    book.add_sheet("분석 자료")
    book.sheet(1).set_raw(0, 0, "='Sheet1'!B1")
    assert Evaluator(book).value(1, 0, 0) == 50
    book.sheet(0).set_raw(0, 0, "=B1")
    assert str(Evaluator(book).value(0, 0, 1)) == "#CYCLE!"


def test_named_range(book):
    book.named_ranges["Revenue"] = ("Sheet1", "A1:A2")
    book.sheet().set_raw(4, 0, "=SUM(Revenue)")
    assert Evaluator(book).value(0, 4, 0) == 30


def test_translation_preserves_literals_and_absolute_references():
    assert translate_formula('=A1+$B1+C$1+$D$1+LEN("A1")', 2, 1) == '=B3+$B3+D$1+$D$1+LEN("A1")'
    assert translate_formula("=A1", -1, 0) == "=#REF!"


def test_range_is_bounded():
    assert CellRange.parse("B2:A1").size == 4
    with pytest.raises(ValueError):
        CellRange.parse("A1:XFD1048576").coordinates(limit=10000)
