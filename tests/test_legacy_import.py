import json
from datetime import date

import pytest
import xlwt

from texel.exchange import export_file, load_file
from texel.model import Workbook
from texel.ui.app import TexelApp


def legacy_file(path):
    source = xlwt.Workbook()
    sheet = source.add_sheet("매출")
    sheet.write(0, 0, "항목")
    sheet.write(0, 1, "값")
    sheet.write(1, 0, "서울", xlwt.easyxf("font: bold on; borders: left thick, bottom double;"))
    sheet.write(1, 1, 42)
    sheet.write(2, 0, date(2026, 10, 10), xlwt.easyxf(num_format_str="YYYY-MM-DD"))
    sheet.write_merge(3, 3, 0, 1, "병합")
    sheet.row(1).height = 900
    sheet.col(0).width = 24 * 256
    source.add_sheet("분석").write(0, 0, True)
    source.save(str(path))


def test_real_biff_xls_import_and_conversion(tmp_path):
    source = tmp_path / "legacy.xls"
    legacy_file(source)
    book = load_file(source)
    assert len(book.sheets) == 2
    assert book.sheet(0).cell(1, 0).raw == "'서울"
    assert book.sheet(0).cell(1, 1).raw == "42"
    assert book.sheet(0).cell(2, 0).raw == "2026-10-10"
    assert book.sheet(0).cell(1, 0).style.bold
    assert book.sheet(0).cell(1, 0).style.borders["left"].style == "thick"
    assert book.sheet(0).row_heights[1] == 3
    assert book.sheet(0).column_widths[0] == 24
    assert book.sheet(0).merges == ["A4:B4"]
    converted = tmp_path / "converted.xlsx"
    export_file(book, converted)
    assert load_file(converted).sheet(0).cell(1, 1).raw == "42"


@pytest.mark.asyncio
async def test_xls_open_in_ui_and_save_defaults_to_xlsx(tmp_path):
    source = tmp_path / "legacy.xls"
    legacy_file(source)
    app = TexelApp(tmp_path / "native.texel")
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.press("ctrl+o")
        app.screen.query_one("#field-path").value = str(source)
        await pilot.click("#apply")
        assert app.session.evaluator.value(0, 1, 1) == 42
        await pilot.press("ctrl+s")
        assert app.screen.query_one("#field-path").value.endswith("legacy.xlsx")


@pytest.mark.parametrize("payload", ["not xls", "not json"])
def test_unsupported_legacy_input_is_clear_error(tmp_path, payload):
    path = tmp_path / ("bad.xls" if payload == "not xls" else "bad.gsheet")
    path.write_text(payload)
    with pytest.raises(ValueError):
        load_file(path)


def test_gsheet_public_export_is_imported(monkeypatch, tmp_path):
    from texel import google_sheets

    workbook = Workbook()
    workbook.sheet().set_raw(0, 0, "42")
    exported = tmp_path / "remote.xlsx"
    export_file(workbook, exported)
    shortcut = tmp_path / "public.gsheet"
    shortcut.write_text(
        json.dumps({"url": "https://docs.google.com/spreadsheets/d/abcdEFGH1234567890/edit#gid=0"})
    )
    requested = []

    def download(url):
        requested.append(url)
        return exported.read_bytes()

    monkeypatch.setattr(google_sheets, "fetch_public_export", download)
    book = load_file(shortcut)
    assert book.sheet().cell(0, 0).raw == "42"
    assert requested == [
        "https://docs.google.com/spreadsheets/d/abcdEFGH1234567890/export?format=xlsx"
    ]


def test_published_gsheet_csv_and_doc_id(monkeypatch, tmp_path):
    from texel import google_sheets

    shortcut = tmp_path / "published.gsheet"
    shortcut.write_text(
        json.dumps(
            {"url": "https://docs.google.com/spreadsheets/d/e/2PACX-abcdEFGH1234567890/pubhtml"}
        )
    )
    monkeypatch.setattr(
        google_sheets, "fetch_public_export", lambda url: "항목,값\n서울,42\n".encode()
    )
    assert load_file(shortcut).sheet().cell(1, 1).raw == "42"
    url, extension = google_sheets.export_target({"doc_id": "abcdEFGH1234567890"})
    assert extension == ".xlsx" and "export?format=xlsx" in url


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/data",
        "https://evil.example/spreadsheets/d/abcdEFGH1234567890",
        "file:///C:/secret",
        "https://docs.google.com.evil.example/spreadsheets/d/abcdEFGH1234567890",
        "https://user:pass@docs.google.com/spreadsheets/d/abcdEFGH1234567890",
    ],
)
def test_gsheet_rejects_non_google_links(url, tmp_path):
    from texel.google_sheets import export_target

    with pytest.raises(ValueError):
        export_target({"url": url})


def test_gsheet_redirect_and_payload_limits():
    from texel.google_sheets import validate_download_url, validate_payload

    validate_download_url("https://doc-abc-sheets.googleusercontent.com/export/data")
    with pytest.raises(ValueError):
        validate_download_url("https://example.com/data")
    with pytest.raises(ValueError):
        validate_payload(b"<html>Sign in</html>", ".xlsx")
