from __future__ import annotations

import math
import re
from dataclasses import asdict, dataclass, field
from datetime import date
from typing import Any

from .addresses import MAX_COLUMNS, MAX_ROWS, CellRange, address, parse_address
from .criteria import validate_filter

MAX_CELLS = 200_000
BORDER_STYLES = {"none", "thin", "medium", "thick", "double", "dashed", "dotted"}


@dataclass
class BorderEdge:
    style: str = "thin"
    color: str = ""


@dataclass
class CellStyle:
    number_format: str = "general"
    decimals: int = 2
    bold: bool = False
    underline: bool = False
    foreground: str = ""
    background: str = ""
    align: str = "auto"
    italic: bool = False
    strike: bool = False
    wrap: bool = False
    vertical_align: str = "top"
    borders: dict[str, BorderEdge] = field(default_factory=dict)


@dataclass
class Validation:
    kind: str = "number"
    choices: list[str] = field(default_factory=list)
    minimum: float | None = None
    maximum: float | None = None
    allow_blank: bool = True

    def check(self, value: Any) -> bool:
        if value is None or value == "":
            return self.allow_blank
        if self.kind == "list":
            return str(value) in self.choices
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return False
        return (self.minimum is None or value >= self.minimum) and (
            self.maximum is None or value <= self.maximum
        )


@dataclass
class Cell:
    raw: str = ""
    style: CellStyle = field(default_factory=CellStyle)
    note: str = ""
    validation: Validation | None = None
    locked: bool = False

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> Cell:
        data = dict(data)
        style = dict(data.get("style", {}))
        style["borders"] = {
            side: BorderEdge(**edge) for side, edge in style.get("borders", {}).items()
        }
        data["style"] = CellStyle(**style)
        if data.get("validation") is not None:
            data["validation"] = Validation(**data["validation"])
        return cls(**data)


@dataclass
class Sheet:
    name: str = "Sheet1"
    cells: dict[tuple[int, int], Cell] = field(default_factory=dict)
    column_widths: dict[int, int] = field(default_factory=dict)
    row_heights: dict[int, int] = field(default_factory=dict)
    hidden_rows: set[int] = field(default_factory=set)
    hidden_columns: set[int] = field(default_factory=set)
    freeze_rows: int = 0
    freeze_columns: int = 0
    merges: list[str] = field(default_factory=list)
    conditional_rules: list[dict] = field(default_factory=list)
    protected: bool = False
    filter_spec: dict | None = None
    charts: list[dict] = field(default_factory=list)

    def cell(self, row: int, column: int, create: bool = True) -> Cell:
        address(row, column)
        key = (row, column)
        if create:
            if key not in self.cells:
                self.cells[key] = Cell()
            return self.cells[key]
        return self.cells.get(key, Cell())

    def set_raw(self, row: int, column: int, raw: str) -> None:
        if not isinstance(raw, str) or len(raw) > 32767:
            raise ValueError("Cell text must be a string of at most 32767 characters")
        self.cell(row, column).raw = raw

    @property
    def used_range(self) -> CellRange:
        used = [
            (r, c)
            for (r, c), cell in self.cells.items()
            if cell.raw or cell.note or cell.style != CellStyle()
        ]
        if not used:
            return CellRange(0, 0, 0, 0)
        return CellRange(0, 0, max(r for r, _ in used), max(c for _, c in used))

    def merge_anchor(self, row: int, column: int) -> tuple[int, int]:
        span = self.merged_range(row, column)
        if span:
            return span.top, span.left
        return row, column

    def merged_range(self, row: int, column: int) -> CellRange | None:
        for merge in self.merges:
            span = CellRange.parse(merge)
            if span.contains(row, column):
                return span
        return None

    def to_dict(self) -> dict:
        result = self.metadata()
        result["cells"] = {address(r, c): cell.to_dict() for (r, c), cell in self.cells.items()}
        return result

    def metadata(self) -> dict:
        return {
            "name": self.name,
            "column_widths": self.column_widths,
            "row_heights": self.row_heights,
            "hidden_rows": sorted(self.hidden_rows),
            "hidden_columns": sorted(self.hidden_columns),
            "freeze_rows": self.freeze_rows,
            "freeze_columns": self.freeze_columns,
            "merges": self.merges,
            "conditional_rules": self.conditional_rules,
            "protected": self.protected,
            "filter_spec": self.filter_spec,
            "charts": self.charts,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Sheet:
        values = dict(data)
        cells = values.pop("cells", {})
        values["column_widths"] = {int(k): v for k, v in values.get("column_widths", {}).items()}
        values["row_heights"] = {int(k): v for k, v in values.get("row_heights", {}).items()}
        values["hidden_rows"] = set(values.get("hidden_rows", []))
        values["hidden_columns"] = set(values.get("hidden_columns", []))
        sheet = cls(**values)
        sheet.cells = {parse_address(ref): Cell.from_dict(cell) for ref, cell in cells.items()}
        return sheet


def validate_sheet_name(name: str) -> None:
    if any(ord(c) < 32 or 127 <= ord(c) <= 159 for c in name):
        raise ValueError("Sheet names cannot contain control characters")
    if (
        not name.strip()
        or len(name) > 31
        or re.search(r"[\\/*?:\[\]]", name)
        or name.startswith("'")
        or name.endswith("'")
    ):
        raise ValueError("Sheet name must have 1..31 characters and no \\ / * ? : [ ]")


@dataclass
class Workbook:
    sheets: list[Sheet] = field(default_factory=lambda: [Sheet()])
    active_sheet: int = 0
    named_ranges: dict[str, tuple[str, str]] = field(default_factory=dict)

    def sheet(self, index: int | str | None = None) -> Sheet:
        if index is None:
            index = self.active_sheet
        if isinstance(index, str):
            return self.sheets[self.sheet_index(index)]
        if index < 0 or index >= len(self.sheets):
            raise ValueError("Unknown sheet")
        return self.sheets[index]

    def sheet_index(self, name: str) -> int:
        for index, sheet in enumerate(self.sheets):
            if sheet.name.casefold() == name.casefold():
                return index
        raise ValueError(f"Unknown sheet: {name}")

    def add_sheet(self, name: str) -> int:
        validate_sheet_name(name)
        if any(s.name.casefold() == name.casefold() for s in self.sheets):
            raise ValueError("Sheet name already exists")
        self.sheets.append(Sheet(name=name))
        return len(self.sheets) - 1

    def delete_sheet(self, index: int) -> None:
        if self.sheet(index).protected:
            raise ValueError("Unprotect the sheet before deleting it")
        if len(self.sheets) == 1:
            raise ValueError("Cannot delete the final sheet")
        del self.sheets[index]
        self.active_sheet = min(self.active_sheet, len(self.sheets) - 1)

    def validate(self) -> None:
        if not self.sheets or len(self.sheets) > 256:
            raise ValueError("Workbook requires 1..256 sheets")
        if type(self.active_sheet) is not int or not 0 <= self.active_sheet < len(self.sheets):
            raise ValueError("Invalid active sheet index")
        if sum(len(s.cells) for s in self.sheets) > MAX_CELLS:
            raise ValueError(f"Workbook exceeds {MAX_CELLS:,} stored cells")
        names = set()
        for sheet in self.sheets:
            validate_sheet_name(sheet.name)
            if sheet.name.casefold() in names:
                raise ValueError("Duplicate sheet name")
            names.add(sheet.name.casefold())
            validate_sheet_metadata(sheet)
            if (
                type(sheet.freeze_rows) is not int
                or type(sheet.freeze_columns) is not int
                or not 0 <= sheet.freeze_rows < MAX_ROWS
                or not 0 <= sheet.freeze_columns < MAX_COLUMNS
            ):
                raise ValueError("Invalid freeze bounds")
            if any(
                not 0 <= r < MAX_ROWS or not isinstance(h, int) or not 1 <= h <= 12
                for r, h in sheet.row_heights.items()
            ):
                raise ValueError("Row height must be 1..12 terminal lines")
            for (r, c), cell in sheet.cells.items():
                address(r, c)
                if len(cell.raw) > 32767 or not 0 <= cell.style.decimals <= 10:
                    raise ValueError("Invalid cell text or decimal count")
                if cell.style.number_format not in {
                    "general",
                    "number",
                    "percent",
                    "currency",
                    "date",
                }:
                    raise ValueError("Unknown number format")
                if cell.style.align not in {"auto", "left", "center", "right"}:
                    raise ValueError("Unknown alignment")
                if cell.style.vertical_align not in {"top", "middle", "bottom"}:
                    raise ValueError("Unknown vertical alignment")
                for side, edge in cell.style.borders.items():
                    if (
                        side not in {"left", "right", "top", "bottom"}
                        or edge.style not in BORDER_STYLES
                    ):
                        raise ValueError("Invalid border side or style")
                    if edge.color and not re.fullmatch(r"#[0-9a-fA-F]{6}", edge.color):
                        raise ValueError("Border color must be #RRGGBB or blank")
                for color in (cell.style.foreground, cell.style.background):
                    if color and not re.fullmatch(r"#[0-9a-fA-F]{6}", color):
                        raise ValueError("Color must be #RRGGBB or blank")
                rule = cell.validation
                if rule is not None:
                    if rule.kind not in {"number", "list"} or len(rule.choices) > 1000:
                        raise ValueError("Invalid validation kind or list size")
                    if any(
                        v is not None and not math.isfinite(v) for v in (rule.minimum, rule.maximum)
                    ):
                        raise ValueError("Validation bounds must be finite")
                    if (
                        rule.minimum is not None
                        and rule.maximum is not None
                        and rule.minimum > rule.maximum
                    ):
                        raise ValueError("Validation minimum exceeds maximum")
            for merge in sheet.merges:
                span = CellRange.parse(merge)
                for r, c in span.coordinates(limit=10000):
                    if (r, c) != (span.top, span.left) and sheet.cell(r, c, False).raw:
                        raise ValueError("Merged cells contain non-anchor data")
        self.sheet(self.active_sheet)
        for name, target in self.named_ranges.items():
            if not isinstance(name, str) or not name or len(target) != 2:
                raise ValueError("Invalid named range")
            sheet_name, region = target
            self.sheet(sheet_name)
            CellRange.parse(region)

    def to_dict(self) -> dict:
        return {
            "sheets": [s.to_dict() for s in self.sheets],
            "active_sheet": self.active_sheet,
            "named_ranges": self.named_ranges,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Workbook:
        book = cls(
            [Sheet.from_dict(s) for s in data["sheets"]],
            data.get("active_sheet", 0),
            {k: tuple(v) for k, v in data.get("named_ranges", {}).items()},
        )
        book.validate()
        return book


def validate_sheet_metadata(sheet):
    def bounded(value, limit):
        return type(value) is int and 0 <= value < limit

    if any(not bounded(r, MAX_ROWS) for r in sheet.hidden_rows) or any(
        not bounded(c, MAX_COLUMNS) for c in sheet.hidden_columns
    ):
        raise ValueError("Invalid hidden row or column")
    if any(
        not bounded(c, MAX_COLUMNS) or type(width) is not int or not 4 <= width <= 60
        for c, width in sheet.column_widths.items()
    ):
        raise ValueError("Column width must be 4..60 terminal columns")
    validate_filter(sheet.filter_spec)
    for rule in sheet.conditional_rules:
        CellRange.parse(rule["range"])
        value = rule["value"]
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
        ):
            raise ValueError("Conditional value must be a finite number")
        if rule.get("operator", "greaterThan") not in {
            "greaterThan",
            "lessThan",
            "equal",
            "greaterThanOrEqual",
        }:
            raise ValueError("Invalid conditional operator")
        if not re.fullmatch(r"#[0-9a-fA-F]{6}", rule.get("color", "#0f766e")):
            raise ValueError("Invalid conditional color")
    for chart in sheet.charts:
        CellRange.parse(chart["range"])
        if chart["kind"] not in {"bar", "line"} or not isinstance(chart.get("title", ""), str):
            raise ValueError("Invalid chart metadata")


def literal(raw: str) -> Any:
    if not raw:
        return None
    if raw.startswith("'"):
        return raw[1:]
    if raw.upper() in {"TRUE", "FALSE"}:
        return raw.upper() == "TRUE"
    if re.fullmatch(r"[+-]?\d+", raw.strip()):
        return int(raw.strip())
    if re.fullmatch(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?%?", raw.strip()):
        value = float(raw.strip().rstrip("%"))
        if not math.isfinite(value):
            return raw
        if raw.strip().endswith("%"):
            return value / 100
        return int(value) if value.is_integer() else value
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
        try:
            return date.fromisoformat(raw)
        except ValueError:
            pass
    return raw


def display_value(value: Any, style: CellStyle | None = None) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, (int, float)):
        style = style or CellStyle()
        if style.number_format == "percent":
            return f"{value * 100:,.{style.decimals}f}%"
        if style.number_format == "currency":
            return f"₩{value:,.{style.decimals}f}"
        if style.number_format == "number":
            return f"{value:,.{style.decimals}f}"
        return format(value, ".12g")
    return str(value)
