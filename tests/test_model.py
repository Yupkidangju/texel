import pytest

from texel.model import Workbook


def test_sparse_model_round_trip():
    book = Workbook()
    book.sheet().set_raw(4, 7, "한글\n메모")
    book.sheet().cell(4, 7).note = "원문 보존"
    book.sheet().cell(4, 7).style.bold = True
    restored = Workbook.from_dict(book.to_dict())
    assert restored.sheet().cell(4, 7).raw == "한글\n메모"
    assert restored.sheet().cell(4, 7).note == "원문 보존"
    assert restored.sheet().cell(4, 7).style.bold
    assert len(restored.sheet().cells) == 1


def test_unique_sheet_names_and_final_sheet():
    book = Workbook()
    with pytest.raises(ValueError):
        book.add_sheet("Sheet1")
    with pytest.raises(ValueError):
        book.add_sheet("bad/name")
    with pytest.raises(ValueError):
        book.delete_sheet(0)
