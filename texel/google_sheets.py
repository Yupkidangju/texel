"""공개 Google Sheets 바로가기 가져오기. 인증 쿠키/토큰을 사용하지 않는다."""

import json
import re
import tempfile
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from . import __version__

GSHEET_NOTICE = "GSHEET imports a public Google Sheets snapshot. Internet and anonymous download access are required. Save locally as .xlsx/.texel; Google cloud contents are not modified."
MAX_DOWNLOAD = 64 * 1024 * 1024


def export_target(shortcut):
    if not isinstance(shortcut, dict):
        raise ValueError("GSHEET must contain a Google Sheets shortcut object")
    url = shortcut.get("url")
    if url:
        if not isinstance(url, str) or len(url) > 4096:
            raise ValueError("Invalid GSHEET URL")
        parts = urlsplit(url)
        if (
            parts.scheme != "https"
            or parts.hostname != "docs.google.com"
            or parts.port not in (None, 443)
            or parts.username
            or parts.password
        ):
            raise ValueError("GSHEET links must use https://docs.google.com/spreadsheets/...")
        match = re.fullmatch(
            r"/spreadsheets/d/(e/)?([A-Za-z0-9_-]{10,200})(?:/[^?#]*)?", parts.path
        )
        if not match:
            raise ValueError("Invalid Google Sheets document ID")
        published, identifier = bool(match[1]), match[2]
        if shortcut.get("doc_id") and shortcut["doc_id"] != identifier:
            raise ValueError("GSHEET URL and doc_id identify different documents")
        if published:
            arguments = {"output": "csv"}
            gid = parse_qs(parts.query).get("gid", parse_qs(parts.fragment).get("gid", []))
            if gid and gid[0].isdigit():
                arguments["gid"] = gid[0]
            return (
                f"https://docs.google.com/spreadsheets/d/e/{identifier}/pub?{urlencode(arguments)}",
                ".csv",
            )
    else:
        identifier = shortcut.get("doc_id", "")
        if not isinstance(identifier, str) or not re.fullmatch(
            r"[A-Za-z0-9_-]{10,200}", identifier
        ):
            raise ValueError("GSHEET needs a Google Sheets URL or document ID")
    return f"https://docs.google.com/spreadsheets/d/{identifier}/export?format=xlsx", ".xlsx"


def validate_download_url(url):
    parts = urlsplit(url)
    host = (parts.hostname or "").lower()
    if (
        parts.scheme != "https"
        or parts.port not in (None, 443)
        or parts.username
        or parts.password
        or not (host == "docs.google.com" or host.endswith(".googleusercontent.com"))
    ):
        raise ValueError(
            "Google document download redirected outside allowed hosts, or needs login"
        )


class GoogleRedirects(HTTPRedirectHandler):
    max_redirections = 5

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_download_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch_public_export(url):
    validate_download_url(url)
    try:
        with build_opener(GoogleRedirects()).open(
            Request(url, headers={"User-Agent": f"Texel/{__version__}"}), timeout=20
        ) as response:
            validate_download_url(response.url)
            length = response.headers.get("Content-Length")
            if length and int(length) > MAX_DOWNLOAD:
                raise ValueError("Google export exceeds 64 MiB")
            chunks, total = [], 0
            while chunk := response.read(65536):
                total += len(chunk)
                if total > MAX_DOWNLOAD:
                    raise ValueError("Google export exceeds 64 MiB")
                chunks.append(chunk)
            return b"".join(chunks)
    except HTTPError as exc:
        if exc.code in {401, 403, 404}:
            raise ValueError(
                "Google Sheets is private, missing or disallows download. Make it accessible by link or download an XLSX copy while signed in."
            ) from exc
        raise ValueError(f"Google Sheets download failed: HTTP {exc.code}") from exc
    except URLError as exc:
        raise ValueError(
            "Cannot download Google Sheets. Check the internet connection or import a downloaded XLSX copy."
        ) from exc


def validate_payload(data, extension):
    if not isinstance(data, bytes) or not data or len(data) > MAX_DOWNLOAD:
        raise ValueError("Empty or oversized Google export")
    first = data.lstrip()[:256].lower()
    if first.startswith((b"<html", b"<!doctype", b"<head")):
        raise ValueError(
            "Google returned a sign-in/error page. Use a public download link or an XLSX copy."
        )
    if extension == ".xlsx" and not data.startswith(b"PK"):
        raise ValueError("Google did not return an XLSX spreadsheet")


def load_gsheet(path):
    path = Path(path)
    if path.stat().st_size > 65536:
        raise ValueError("GSHEET shortcut exceeds 64 KiB")
    try:
        shortcut = json.loads(path.read_text(encoding="utf-8-sig"))
    except (ValueError, UnicodeError) as exc:
        raise ValueError("Invalid GSHEET shortcut JSON") from exc
    url, extension = export_target(shortcut)
    data = fetch_public_export(url)
    validate_payload(data, extension)
    from .exchange import load_file

    with tempfile.TemporaryDirectory(prefix="texel-gsheet-") as directory:
        exported = Path(directory) / ("document" + extension)
        exported.write_bytes(data)
        return load_file(exported)
