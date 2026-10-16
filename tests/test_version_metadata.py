"""공개 다운로드 요청의 제품 버전 표기를 검증한다."""

from io import BytesIO
from unittest.mock import Mock

from texel import __version__, google_sheets


def test_google_export_request_uses_package_version(monkeypatch):
    url = "https://docs.google.com/spreadsheets/d/abcdEFGH1234567890/export?format=xlsx"
    response = BytesIO(b"export data")
    response.url = url
    response.headers = {"Content-Length": "11"}
    opener = Mock()
    opener.open.return_value = response
    build_opener = Mock(return_value=opener)
    monkeypatch.setattr(google_sheets, "build_opener", build_opener)

    assert google_sheets.fetch_public_export(url) == b"export data"

    request = opener.open.call_args.args[0]
    assert request.full_url == url
    assert request.get_header("User-agent") == f"Texel/{__version__}"
    assert opener.open.call_args.kwargs == {"timeout": 20}
    assert isinstance(build_opener.call_args.args[0], google_sheets.GoogleRedirects)
