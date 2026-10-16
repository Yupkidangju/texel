"""TUI와 MCP의 표 정리 및 검색 공용 동작."""

import re
from copy import deepcopy
from datetime import date

from .addresses import CellRange, address
from .criteria import validate_filter
from .formula import Evaluator, translate_formula
from .values import Error, exact_text


def sort_table(book, sheet, region, keys, header=True):
    span, target = CellRange.parse(region), book.sheet(sheet)
    span.coordinates(limit=10000)
    if not 1 <= len(keys) <= 8 or type(header) is not bool:
        raise ValueError("Sort requires 1..8 keys and a boolean header")
    for key in keys:
        if type(key.get("column")) is not int or not 0 <= key["column"] < span.width:
            raise ValueError("Sort column outside range")
        if type(key.get("descending", False)) is not bool:
            raise ValueError("Sort direction must be boolean")
    for raw in target.merges:
        merged = CellRange.parse(raw)
        if not (
            merged.bottom < span.top
            or merged.top > span.bottom
            or merged.right < span.left
            or merged.left > span.right
        ):
            raise ValueError("Unmerge cells before sorting")
    evaluator = Evaluator(book)
    rows = list(range(span.top + int(header), span.bottom + 1))
    ordered = rows[:]
    for key in reversed(keys):
        values = {r: evaluator.value(sheet, r, span.left + key["column"]) for r in rows}
        missing = [r for r in ordered if values[r] in (None, "") or isinstance(values[r], Error)]
        present = [
            r for r in ordered if values[r] not in (None, "") and not isinstance(values[r], Error)
        ]

        def sort_key(r, values=values):
            value = values[r]
            if isinstance(value, bool):
                return 3, value
            if isinstance(value, (int, float)):
                return 0, value
            if isinstance(value, date):
                return 1, value.toordinal()
            return 2, str(value).casefold()

        ordered = sorted(present, key=sort_key, reverse=key.get("descending", False)) + missing
    contents = {
        (r, c): deepcopy(target.cell(r, c, False))
        for r in rows
        for c in range(span.left, span.right + 1)
    }
    for new, old in zip(rows, ordered, strict=True):
        for c in range(span.left, span.right + 1):
            cell = contents[(old, c)]
            cell.raw = translate_formula(cell.raw, new - old, 0)
            target.cells[(new, c)] = cell


def set_filter(book, sheet, region, conditions, match="all", header=True):
    if not conditions:
        raise ValueError("Filters require 1..8 conditions")
    spec = {
        "range": str(CellRange.parse(region)),
        "header": header,
        "match": match,
        "conditions": deepcopy(conditions),
        "column": conditions[0]["column"],
        "criterion": conditions[0]["criterion"],
    }
    validate_filter(spec)
    book.sheet(sheet).filter_spec = spec


def match_pattern(query, case_sensitive=False):
    if not query or len(query) > 32767:
        raise ValueError("Search text requires 1..32767 characters")
    return re.compile(re.escape(query), 0 if case_sensitive else re.IGNORECASE)


def selected_cells(book, sheet=None, region=None):
    span = CellRange.parse(region) if region else None
    indices = (
        range(len(book.sheets))
        if sheet is None
        else [book.sheet_index(sheet) if isinstance(sheet, str) else sheet]
    )
    for index in indices:
        for (r, c), cell in sorted(book.sheet(index).cells.items()):
            if span is None or span.contains(r, c):
                yield index, r, c, cell


def search_cells(
    book,
    query,
    sheet=None,
    region=None,
    case_sensitive=False,
    whole_cell=False,
    look_in="raw",
    offset=0,
    limit=200,
):
    if type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= 2000:
        raise ValueError("Invalid search page")
    if look_in not in {"raw", "values"}:
        raise ValueError("Search mode must be raw or values")
    pattern, evaluator = match_pattern(query, case_sensitive), Evaluator(book)
    matches, total = [], 0
    for index, r, c, cell in selected_cells(book, sheet, region):
        value = evaluator.value(index, r, c) if look_in == "values" else None
        source = exact_text(value) if look_in == "values" else cell.raw
        if (pattern.fullmatch if whole_cell else pattern.search)(source):
            if offset <= total < offset + limit:
                matches.append(
                    {
                        "sheet": book.sheet(index).name,
                        "address": address(r, c),
                        "raw": cell.raw,
                        "match": source,
                    }
                )
            total += 1
    return {
        "matches": matches,
        "total": total,
        "next_offset": offset + len(matches) if offset + len(matches) < total else None,
    }


def find_next_match(
    book, query, current, sheet=None, case_sensitive=False, whole_cell=False, look_in="raw"
):
    pattern, evaluator = match_pattern(query, case_sensitive), Evaluator(book)
    first = following = None
    total, following_index = 0, 1
    for index, r, c, cell in selected_cells(book, sheet):
        source = exact_text(evaluator.value(index, r, c)) if look_in == "values" else cell.raw
        if (pattern.fullmatch if whole_cell else pattern.search)(source):
            total += 1
            position = (index, r, c)
            if first is None:
                first = position
            if following is None and position > current:
                following, following_index = position, total
    return {
        "position": following or first,
        "index": following_index if following else 1,
        "total": total,
    }


def replace_matches(
    book, query, replacement, sheet=None, region=None, case_sensitive=False, whole_cell=False
):
    pattern = match_pattern(query, case_sensitive)
    changes, replacements = [], 0
    for _, _, _, cell in selected_cells(book, sheet, region):
        if whole_cell:
            count = int(pattern.fullmatch(cell.raw) is not None)
            result = replacement if count else cell.raw
        else:
            count = sum(1 for _ in pattern.finditer(cell.raw))
            if len(cell.raw) + count * (len(replacement) - len(query)) > 32767:
                raise ValueError("Replacement exceeds cell text limit")
            result, count = pattern.subn(lambda _: replacement, cell.raw)
        if count:
            if len(result) > 32767:
                raise ValueError("Replacement exceeds cell text limit")
            changes.append((cell, result))
            replacements += count
        if len(changes) > 10000:
            raise ValueError("Replacement exceeds 10000 cells")
    for cell, raw in changes:
        cell.raw = raw
    return replacements
