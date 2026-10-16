"""형식이 정해진 편집 작업과 단일 트랜잭션/미리보기."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from .addresses import CellRange, parse_address
from .editing import apply_borders, clear_range, copy_range, fill_range, format_range, set_matrix
from .store import make_patch
from .tables import replace_matches, selected_cells, set_filter, sort_table


class InputModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)


class SortKey(InputModel):
    column: int = Field(ge=0, le=16383)
    descending: bool = False


class FilterCondition(InputModel):
    column: int = Field(ge=0, le=16383)
    criterion: str = Field(max_length=32767)


class StylePatch(InputModel):
    number_format: Literal["general", "number", "percent", "currency", "date"] | None = None
    decimals: int | None = Field(default=None, ge=0, le=10)
    bold: bool | None = None
    underline: bool | None = None
    italic: bool | None = None
    strike: bool | None = None
    wrap: bool | None = None
    align: Literal["auto", "left", "center", "right"] | None = None
    vertical_align: Literal["top", "middle", "bottom"] | None = None
    foreground: str | None = Field(default=None, pattern=r"^(#[0-9a-fA-F]{6})?$")
    background: str | None = Field(default=None, pattern=r"^(#[0-9a-fA-F]{6})?$")


class SheetOperation(InputModel):
    sheet: str = Field(min_length=1, max_length=31)


class RangeOperation(SheetOperation):
    range: str


class WriteOperation(SheetOperation):
    op: Literal["write"]
    start: str
    values: list[list[str | int | float | bool | None]] = Field(max_length=10000)


class ClearOperation(RangeOperation):
    op: Literal["clear"]
    include_formatting: bool = False


class CopyOperation(RangeOperation):
    op: Literal["copy"]
    destination: str
    transpose: bool = False
    cut: bool = False


class FillOperation(RangeOperation):
    op: Literal["fill"]
    direction: Literal["down", "right", "series"] = "down"


class FormatOperation(RangeOperation):
    op: Literal["format"]
    style: StylePatch


class BordersOperation(RangeOperation):
    op: Literal["borders"]
    preset: Literal["all", "outer", "inner", "top", "bottom", "left", "right", "none"] = "all"
    border_style: Literal["thin", "medium", "thick", "double", "dashed", "dotted"] = "thin"
    color: str = Field(default="", pattern=r"^(#[0-9a-fA-F]{6})?$")


class SortOperation(RangeOperation):
    op: Literal["sort"]
    keys: list[SortKey] = Field(min_length=1, max_length=8)
    header: bool = True


class FilterOperation(SheetOperation):
    op: Literal["filter"]
    range: str = "A1"
    conditions: list[FilterCondition] = Field(default_factory=list, max_length=8)
    match: Literal["all", "any"] = "all"
    header: bool = True
    clear: bool = False


class ReplaceOperation(SheetOperation):
    op: Literal["replace"]
    query: str = Field(min_length=1, max_length=32767)
    replacement: str = Field(max_length=32767)
    range: str | None = None
    case_sensitive: bool = False
    whole_cell: bool = False


class NoteOperation(SheetOperation):
    op: Literal["note"]
    cell: str
    note: str = Field(max_length=32767)


BatchOperation = Annotated[
    WriteOperation
    | ClearOperation
    | CopyOperation
    | FillOperation
    | FormatOperation
    | BordersOperation
    | SortOperation
    | FilterOperation
    | ReplaceOperation
    | NoteOperation,
    Field(discriminator="op"),
]
Batch = Annotated[list[BatchOperation], Field(min_length=1, max_length=50)]
BATCH_ADAPTER = TypeAdapter(Batch)
OPERATION_NAMES = [
    "write",
    "clear",
    "copy",
    "fill",
    "format",
    "borders",
    "sort",
    "filter",
    "replace",
    "note",
]


class OperationError(ValueError):
    def __init__(self, index, operation, cause):
        self.operation_index, self.operation = index, operation
        super().__init__(f"Operation {index + 1} ({operation}): {cause}")


def operation_cost(book, op):
    book.sheet(op.sheet)
    if isinstance(op, WriteOperation):
        parse_address(op.start)
        return sum(map(len, op.values))
    if isinstance(op, NoteOperation):
        parse_address(op.cell)
        return 1
    if isinstance(op, FilterOperation):
        CellRange.parse(op.range)
        return 0
    if isinstance(op, ReplaceOperation):
        return sum(1 for _ in selected_cells(book, op.sheet, op.range))
    span = CellRange.parse(op.range)
    return span.size * (2 if isinstance(op, CopyOperation) and op.cut else 1)


def execute_operation(book, op):
    index = book.sheet_index(op.sheet)
    if isinstance(op, WriteOperation):
        return set_matrix(book, index, op.start, op.values)
    if isinstance(op, NoteOperation):
        book.sheet(index).cell(*parse_address(op.cell)).note = op.note
    elif isinstance(op, ClearOperation):
        clear_range(book, index, op.range, op.include_formatting)
    elif isinstance(op, CopyOperation):
        copy_range(book, index, op.range, op.destination, op.transpose, op.cut)
    elif isinstance(op, FillOperation):
        fill_range(book, index, op.range, op.direction)
    elif isinstance(op, FormatOperation):
        format_range(book, index, op.range, **op.style.model_dump(exclude_none=True))
    elif isinstance(op, BordersOperation):
        apply_borders(book, index, op.range, op.preset, op.border_style, op.color)
    elif isinstance(op, SortOperation):
        sort_table(book, index, op.range, [key.model_dump() for key in op.keys], op.header)
    elif isinstance(op, FilterOperation):
        if op.clear:
            book.sheet(index).filter_spec = None
        else:
            set_filter(
                book, index, op.range, [c.model_dump() for c in op.conditions], op.match, op.header
            )
    elif isinstance(op, ReplaceOperation):
        return replace_matches(
            book, op.query, op.replacement, index, op.range, op.case_sensitive, op.whole_cell
        )
    return None


def summarize_patch(before, after, limit):
    from .addresses import address

    patch = make_patch(before, after)
    if len(patch["cells"]) > 10000:
        raise ValueError("Batch changes exceed 10000 cells")

    def summary(cell):
        if cell is None:
            return None
        raw, note = cell.get("raw", ""), cell.get("note", "")
        return {
            "raw": raw[:256],
            "note": note[:256],
            "style": cell.get("style"),
            "locked": cell.get("locked", False),
            "text_truncated": len(raw) > 256 or len(note) > 256,
        }

    changes = sorted(patch["cells"], key=lambda c: c[:3])
    return {
        "changed_cells": len(changes),
        "metadata_changed": patch["before"] != patch["after"],
        "changes": [
            {
                "sheet": after.sheet(i).name,
                "cell": address(r, c),
                "before": summary(old),
                "after": summary(new),
            }
            for i, r, c, old, new in changes[:limit]
        ],
        "truncated": len(changes) > limit,
    }


def run_batch(session, operations, expected_revision, preview=False, diff_limit=50):
    parsed = BATCH_ADAPTER.validate_python(operations)
    if type(diff_limit) is not int or not 1 <= diff_limit <= 200:
        raise ValueError("Diff limit must be 1..200")
    before, base_revision = session.workbook, session.revision

    def mutation(candidate):
        cost, results = 0, []
        for i, op in enumerate(parsed):
            try:
                cost += operation_cost(candidate, op)
                if cost > 10000:
                    raise ValueError("Batch processing exceeds 10000 cells")
                results.append(
                    {"index": i, "operation": op.op, "result": execute_operation(candidate, op)}
                )
            except (ValueError, TypeError, ArithmeticError) as exc:
                raise OperationError(i, op.op, exc) from exc
        return {
            "preview": preview,
            "base_revision": base_revision,
            "operations": results,
            **summarize_patch(before, candidate, diff_limit),
        }

    if preview:
        _, result = session.preview(mutation, expected_revision)
        return result
    return session.apply("batch operations", mutation, expected_revision)
