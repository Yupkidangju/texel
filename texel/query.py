"""동일 스냅샷에서 단일/다중 범위를 읽는 공용 페이지 계약."""

from datetime import date

from pydantic import Field

from .addresses import CellRange, address
from .model import display_value
from .operations import InputModel
from .values import Error


class ReadRequest(InputModel):
    sheet: str
    range: str
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=200, ge=1, le=2000)
    column_offset: int = Field(default=0, ge=0)
    column_limit: int = Field(default=50, ge=1, le=2000)


def page_shape(span, offset, limit, column_offset, column_limit):
    if offset < 0 or column_offset < 0 or not 1 <= limit <= 2000 or not 1 <= column_limit <= 2000:
        raise ValueError("Invalid page bounds")
    width = max(0, min(span.width - column_offset, column_limit))
    height = max(0, min(span.height - offset, limit, 2000 // width if width else 0))
    return height, width


def read_page(
    book, evaluator, sheet, region, offset=0, limit=200, column_offset=0, column_limit=50
):
    span, index = CellRange.parse(region), book.sheet_index(sheet)
    height, width = page_shape(span, offset, limit, column_offset, column_limit)
    rows = []
    for r in range(span.top + offset, span.top + offset + height):
        row = []
        for c in range(span.left + column_offset, span.left + column_offset + width):
            cell, value = book.sheet(index).cell(r, c, False), evaluator.value(index, r, c)
            row.append(
                {
                    "address": address(r, c),
                    "raw": cell.raw,
                    "value": value.isoformat()
                    if isinstance(value, date)
                    else str(value)
                    if isinstance(value, Error)
                    else value,
                    "error": value.detail if isinstance(value, Error) else None,
                    "display": display_value(value, cell.style),
                    "note": cell.note,
                    "style": cell.to_dict()["style"],
                    "locked": cell.locked,
                }
            )
        rows.append(row)
    return {
        "sheet": sheet,
        "range": str(span),
        "rows": rows,
        "total_rows": span.height,
        "total_columns": span.width,
        "next_offset": offset + height if offset + height < span.height and height else None,
        "next_column_offset": column_offset + width
        if column_offset + width < span.width and width
        else None,
    }


def read_pages(book, evaluator, requests):
    if not 1 <= len(requests) <= 20:
        raise ValueError("Read requests require 1..20 ranges")
    cell_count = 0
    for request in requests:
        h, w = page_shape(
            CellRange.parse(request.range),
            request.offset,
            request.limit,
            request.column_offset,
            request.column_limit,
        )
        cell_count += h * w
    if cell_count > 2000:
        raise ValueError("Multi-range response exceeds 2000 cells; request smaller pages")
    return {
        "cell_count": cell_count,
        "ranges": [
            read_page(
                book,
                evaluator,
                r.sheet,
                r.range,
                r.offset,
                r.limit,
                r.column_offset,
                r.column_limit,
            )
            for r in requests
        ],
    }
