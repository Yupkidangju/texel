"""Legacy BIFF 값과 기본 서식만 가져온다. 매크로/수식 코드는 실행하지 않는다."""

import io
import re
import struct

import xlrd

from .addresses import CellRange
from .model import MAX_CELLS, BorderEdge, CellStyle, Workbook
from .values import exact_text

XLS_NOTICE = "XLS import reads cached values and basic styles. Original formulas, macros and Excel-only objects are not preserved. Save the imported workbook as .xlsx or .texel."


def load_xls(path):
    source = None
    try:
        source = xlrd.open_workbook(
            str(path), formatting_info=True, on_demand=True, logfile=io.StringIO()
        )
        book, count = Workbook(sheets=[]), 0
        for original in source.sheets():
            if original.nrows * original.ncols > 1000000:
                raise ValueError("XLS worksheet rectangle exceeds 1,000,000 cells")
            index = book.add_sheet(original.name)
            target = book.sheet(index)

            def color(number):
                rgb = source.colour_map.get(number)
                return "#" + "".join(f"{v:02x}" for v in rgb) if rgb else ""

            for r in range(original.nrows):
                for c in range(original.ncols):
                    cell = original.cell(r, c)
                    if cell.ctype == xlrd.XL_CELL_EMPTY:
                        continue
                    count += 1
                    if count > MAX_CELLS:
                        raise ValueError("XLS exceeds stored cell limit")
                    if cell.ctype == xlrd.XL_CELL_TEXT:
                        raw = "'" + cell.value
                    elif cell.ctype == xlrd.XL_CELL_DATE:
                        value = xlrd.xldate_as_datetime(cell.value, source.datemode)
                        raw = (
                            value.date().isoformat()
                            if value.hour == value.minute == value.second == 0
                            else value.isoformat()
                        )
                    elif cell.ctype == xlrd.XL_CELL_BOOLEAN:
                        raw = "TRUE" if cell.value else "FALSE"
                    elif cell.ctype == xlrd.XL_CELL_ERROR:
                        raw = "'" + xlrd.error_text_from_code.get(cell.value, "#VALUE!")
                    elif cell.ctype == xlrd.XL_CELL_BLANK:
                        raw = ""
                    else:
                        raw = exact_text(cell.value)
                    target.set_raw(r, c, raw)
                    xf = source.xf_list[original.cell_xf_index(r, c)]
                    font = source.font_list[xf.font_index]
                    style = CellStyle(
                        bold=bool(font.bold),
                        italic=bool(font.italic),
                        underline=bool(font.underlined),
                        strike=bool(font.struck_out),
                        wrap=bool(xf.alignment.text_wrapped),
                        align={1: "left", 2: "center", 3: "right"}.get(
                            xf.alignment.hor_align, "auto"
                        ),
                        vertical_align={0: "top", 1: "middle", 2: "bottom"}.get(
                            xf.alignment.vert_align, "top"
                        ),
                        foreground=color(font.colour_index),
                    )
                    if xf.background.fill_pattern == 1:
                        style.background = color(xf.background.pattern_colour_index)
                    fmt = source.format_map.get(xf.format_key)
                    fmt = fmt.format_str if fmt else "General"
                    style.number_format = (
                        "date"
                        if cell.ctype == xlrd.XL_CELL_DATE
                        else "percent"
                        if "%" in fmt
                        else "currency"
                        if any(v in fmt for v in ("$", "₩", "€", "£"))
                        else "number"
                        if "0" in fmt
                        else "general"
                    )
                    decimals = re.search(r"\.([0#]+)", fmt)
                    style.decimals = min(10, len(decimals[1])) if decimals else 0
                    for side in ("left", "right", "top", "bottom"):
                        code = getattr(xf.border, side + "_line_style")
                        if code:
                            style.borders[side] = BorderEdge(
                                {
                                    1: "thin",
                                    2: "medium",
                                    3: "dashed",
                                    4: "dotted",
                                    5: "thick",
                                    6: "double",
                                }.get(code, "thin"),
                                color(getattr(xf.border, side + "_colour_index")),
                            )
                    target.cell(r, c).style = style
            for c, info in original.colinfo_map.items():
                target.column_widths[c] = max(4, min(60, round(info.width / 256)))
                if info.hidden:
                    target.hidden_columns.add(c)
            for r, info in original.rowinfo_map.items():
                if info.hidden:
                    target.hidden_rows.add(r)
                if info.height:
                    target.row_heights[r] = max(1, min(12, round(info.height / 300)))
            target.merges = [
                str(CellRange(r1, c1, r2 - 1, c2 - 1)) for r1, r2, c1, c2 in original.merged_cells
            ]
            if original.panes_are_frozen:
                target.freeze_rows = int(original.horz_split_pos or 0)
                target.freeze_columns = int(original.vert_split_pos or 0)
        source.release_resources()
        book.validate()
        return book
    except (
        xlrd.XLRDError,
        xlrd.compdoc.CompDocError,
        IndexError,
        AssertionError,
        struct.error,
    ) as exc:
        raise ValueError(f"Invalid or unsupported XLS file: {exc}") from exc
    finally:
        if source is not None:
            source.release_resources()
