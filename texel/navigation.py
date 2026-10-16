"""희소 표의 데이터 경계 이동과 수식 참조 전환."""

import re

from .addresses import MAX_COLUMNS, MAX_ROWS, CellRange
from .formula import tokenize
from .values import FormulaFault


def jump_target(sheet, cursor, direction, hidden_rows=()):
    vertical = direction in {"up", "down"}
    step = -1 if direction in {"up", "left"} else 1
    axis = 0 if vertical else 1
    limit = MAX_ROWS if vertical else MAX_COLUMNS
    hidden = sheet.hidden_rows | set(hidden_rows) if vertical else sheet.hidden_columns
    current = cursor[axis]
    merged = sheet.merged_range(*cursor)
    if merged:
        current = (
            (merged.bottom if step > 0 else merged.top)
            if vertical
            else (merged.right if step > 0 else merged.left)
        )
    occupied = {
        position[axis]
        for position, cell in sheet.cells.items()
        if cell.raw and position[1 - axis] == cursor[1 - axis]
    }
    for raw in sheet.merges:
        span = CellRange.parse(raw)
        crosses = (
            span.left <= cursor[1] <= span.right
            if vertical
            else span.top <= cursor[0] <= span.bottom
        )
        if crosses and sheet.cell(span.top, span.left, False).raw:
            occupied.update(
                range(span.top, span.bottom + 1) if vertical else range(span.left, span.right + 1)
            )
    occupied.difference_update(hidden)

    def next_visible(position, sign):
        position += sign
        while 0 <= position < limit and position in hidden:
            position += sign
        return position

    adjacent = next_visible(current, step)
    if current in occupied and adjacent in occupied:
        destination = adjacent
        while (following := next_visible(destination, step)) in occupied:
            destination = following
    else:
        candidates = [p for p in occupied if (p - current) * step > 0]
        if candidates:
            destination = min(candidates) if step > 0 else max(candidates)
        else:
            destination = limit - 1 if step > 0 else 0
            while destination in hidden and 0 <= destination - step < limit:
                destination -= step
    return (destination, cursor[1]) if vertical else (cursor[0], destination)


def cycle_reference(formula, cursor, selection_start=None, selection_end=None):
    if not formula.startswith("="):
        return formula, cursor
    try:
        tokens = tokenize(formula[1:])
    except FormulaFault:
        return formula, cursor
    selected = (
        selection_start is not None
        and selection_end is not None
        and selection_start != selection_end
    )
    lo, hi = sorted((selection_start, selection_end)) if selected else (cursor, cursor)
    changes = []
    for i, token in enumerate(tokens):
        if token.kind != "REF" or tokens[i + 1].value == "!":
            continue
        start, end = token.start + 1, token.end + 1
        if not (start < hi and end > lo if selected else start <= cursor <= end):
            continue
        match = re.fullmatch(r"(\$?)([A-Za-z]+)(\$?)([0-9]+)", token.value)
        col, letters, row, digits = match.groups()
        col, row = {
            (False, False): (True, True),
            (True, True): (False, True),
            (False, True): (True, False),
            (True, False): (False, False),
        }[(bool(col), bool(row))]
        replacement = ("$" if col else "") + letters + ("$" if row else "") + digits
        changes.append((start, end, replacement))
        if not selected:
            break
    new_cursor = cursor + sum(
        len(value) - (end - start) for start, end, value in changes if start <= cursor
    )
    for start, end, replacement in reversed(changes):
        formula = formula[:start] + replacement + formula[end:]
    return formula, min(len(formula), new_cursor)
