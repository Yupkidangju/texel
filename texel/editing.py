from __future__ import annotations

import math
import re
from copy import deepcopy

from .addresses import MAX_COLUMNS, MAX_ROWS, CellRange, address, parse_address
from .criteria import validate_filter
from .formula import Evaluator, rewrite_references, tokenize, translate_formula
from .functions import criterion_matches
from .model import BORDER_STYLES, BorderEdge, Cell, CellStyle, display_value, validate_sheet_name
from .values import Error, FormulaFault, exact_text


def set_matrix(book, sheet, start, values):
    if not values:
        return
    if sum(len(row) for row in values) > 10000:
        raise ValueError("A write request may change at most 10000 cells")
    r, c = parse_address(start)
    target = book.sheet(sheet)
    for dr, row in enumerate(values):
        for dc, value in enumerate(row):
            rr, cc = r + dr, c + dc
            if target.merge_anchor(rr, cc) != (rr, cc) and value:
                raise ValueError("Cannot write inside a merged cell; unmerge first")
            target.set_raw(rr, cc, str(value) if value is not None else "")


def clear_range(book, sheet, region, all_content=False):
    span = CellRange.parse(region)
    target = book.sheet(sheet)
    for r, c in span.coordinates(limit=10000):
        if all_content:
            target.cells[(r, c)] = Cell()
        else:
            target.set_raw(r, c, "")


def copy_range(book, sheet, region, destination, transpose=False, cut=False):
    source = book.sheet(sheet)
    span = CellRange.parse(region)
    span.coordinates(limit=10000)
    dest_row, dest_col = parse_address(destination)
    destination_span = CellRange(
        dest_row,
        dest_col,
        dest_row + (span.width if transpose else span.height) - 1,
        dest_col + (span.height if transpose else span.width) - 1,
    )
    source_merges = []
    destination_merges = []
    for merge in source.merges:
        other = CellRange.parse(merge)
        for selection in (span, destination_span):
            if not (
                other.bottom < selection.top
                or other.top > selection.bottom
                or other.right < selection.left
                or other.left > selection.right
            ):
                if not (
                    selection.contains(other.top, other.left)
                    and selection.contains(other.bottom, other.right)
                ):
                    raise ValueError("Select the complete merged region before copying or moving")
                (source_merges if selection is span else destination_merges).append(merge)
    copied = [(r, c, deepcopy(source.cell(r, c, False))) for r, c in span.coordinates(limit=10000)]
    heights = {r: source.row_heights.get(r, 1) for r in range(span.top, span.bottom + 1)}
    if cut:
        clear_range(book, sheet, region, True)
    source.merges = [
        m
        for m in source.merges
        if m not in destination_merges and (not cut or m not in source_merges)
    ]
    for r, c, cell in copied:
        rr = dest_row + (c - span.left if transpose else r - span.top)
        cc = dest_col + (r - span.top if transpose else c - span.left)
        address(rr, cc)
        if not cut:
            cell.raw = translate_formula(cell.raw, rr - r, cc - c)
        source.cells[(rr, cc)] = cell
    for rr in range(destination_span.top, destination_span.bottom + 1):
        source.row_heights[rr] = (
            max(heights.values()) if transpose else heights[span.top + rr - dest_row]
        )
    for merge in source_merges:
        merged = CellRange.parse(merge)
        if transpose:
            translated = CellRange(
                dest_row + merged.left - span.left,
                dest_col + merged.top - span.top,
                dest_row + merged.right - span.left,
                dest_col + merged.bottom - span.top,
            )
        else:
            translated = CellRange(
                dest_row + merged.top - span.top,
                dest_col + merged.left - span.left,
                dest_row + merged.bottom - span.top,
                dest_col + merged.right - span.left,
            )
        if str(translated) not in source.merges:
            source.merges.append(str(translated))
    if cut:
        name = source.name
        for other in book.sheets:
            for cell in other.cells.values():

                def move(ref, qualifier, other=other):
                    rr, cc = parse_address(ref)
                    if (qualifier or other.name).casefold() == name.casefold() and span.contains(
                        rr, cc
                    ):
                        return absolute_address(
                            ref,
                            dest_row + (cc - span.left if transpose else rr - span.top),
                            dest_col + (rr - span.top if transpose else cc - span.left),
                        )
                    return ref

                cell.raw = rewrite_references(cell.raw, move)


def fill_range(book, sheet, region, direction="down"):
    target = book.sheet(sheet)
    span = CellRange.parse(region)
    span.coordinates(limit=10000)
    if direction == "series":
        evaluator = Evaluator(book)
        for c in range(span.left, span.right + 1):
            first = evaluator.value(sheet, span.top, c)
            second = evaluator.value(sheet, span.top + 1, c) if span.height > 1 else None
            if isinstance(first, bool) or not isinstance(first, (int, float)):
                raise ValueError("Series starts with a number")
            second_is_number = not isinstance(second, bool) and isinstance(second, (int, float))
            step = second - first if second_is_number else 1
            start = span.top + (2 if second_is_number else 1)
            for value in (first, step):
                if isinstance(value, float) and not math.isfinite(value):
                    raise ValueError("Series values must be finite")
            for r in range(start, span.bottom + 1):
                value = first + (r - span.top) * step
                if isinstance(value, float) and not math.isfinite(value):
                    raise ValueError("Series values must be finite")
                target.set_raw(r, c, exact_text(value))
        return
    originals = {
        (r, c): deepcopy(target.cell(r, c, False)) for r, c in span.coordinates(limit=10000)
    }
    for r, c in span.coordinates(limit=10000):
        origin = (span.top, c) if direction == "down" else (r, span.left)
        cell = deepcopy(originals[origin])
        cell.raw = translate_formula(cell.raw, r - origin[0], c - origin[1])
        target.cells[(r, c)] = cell


def absolute_address(old, row, col):
    ref = address(row, col)
    letters = ref.rstrip("0123456789")
    return (
        ("$" if old.startswith("$") else "")
        + letters
        + ("$" if "$" in old.lstrip("$") else "")
        + str(row + 1)
    )


def adjust_formula(formula, current_sheet, target_sheet, axis, at, count, delete):
    if not formula.startswith("="):
        return formula
    try:
        tokens = tokenize(formula[1:])
    except FormulaFault:
        return formula
    replacements = {}
    qualifiers = {}
    for i, token in enumerate(tokens):
        if token.kind != "REF" or (i + 1 < len(tokens) and tokens[i + 1].value == "!"):
            continue
        qualifier = current_sheet
        if i >= 2 and tokens[i - 1].value == "!":
            previous = tokens[i - 2]
            qualifier = (
                previous.value[1:-1].replace("''", "'")
                if previous.kind == "SHEET"
                else previous.value
            )
        elif i >= 2 and tokens[i - 1].value == ":":
            qualifier = qualifiers.get(i - 2, current_sheet)
        qualifiers[i] = qualifier
        if qualifier.casefold() != target_sheet.casefold():
            continue
        try:
            r, c = parse_address(token.value)
            coordinate = r if axis == "row" else c
            partner = None
            if i + 2 < len(tokens) and tokens[i + 1].value == ":":
                following = i + 2
                if following + 2 < len(tokens) and tokens[following + 1].value == "!":
                    following += 2
                if tokens[following].kind == "REF":
                    partner = following
            preceding = i - 1
            if preceding >= 0 and tokens[preceding].value == "!":
                preceding -= 2
            if (
                preceding >= 1
                and tokens[preceding].value == ":"
                and tokens[preceding - 1].kind == "REF"
            ):
                partner = preceding - 1
            if delete and at <= coordinate < at + count:
                if partner is not None:
                    other_coord = parse_address(tokens[partner].value)[0 if axis == "row" else 1]
                    if other_coord >= at + count:
                        coordinate = at
                    elif other_coord < at:
                        coordinate = at - 1
                    else:
                        replacements[i] = "#REF!"
                        continue
                else:
                    replacements[i] = "#REF!"
                    continue
            elif coordinate >= (at + count if delete else at):
                coordinate += -count if delete else count
            if axis == "row":
                r = coordinate
            else:
                c = coordinate
            replacements[i] = absolute_address(token.value, r, c)
        except ValueError:
            replacements[i] = "#REF!"
    source, position, result = formula[1:], 0, "="
    for i, token in enumerate(tokens):
        result += source[position : token.start] + replacements.get(i, token.value)
        position = token.end
    return result


def shift_axis(book, sheet, axis, at, count=1, delete=False):
    target = book.sheet(sheet)
    if target.protected:
        raise ValueError("Unprotect the sheet before changing its structure")
    if axis not in {"row", "column"} or count < 1 or count > 10000 or at < 0:
        raise ValueError("Invalid structural operation")
    bound = MAX_ROWS if axis == "row" else MAX_COLUMNS
    if at + count > bound:
        raise ValueError("Structural operation outside worksheet")
    updated = {}
    for (r, c), cell in target.cells.items():
        coordinate = r if axis == "row" else c
        if delete and at <= coordinate < at + count:
            continue
        if coordinate >= at:
            coordinate += -count if delete else count
        rr, cc = (coordinate, c) if axis == "row" else (r, coordinate)
        address(rr, cc)
        updated[(rr, cc)] = cell
    target.cells = updated
    for other in book.sheets:
        for cell in other.cells.values():
            cell.raw = adjust_formula(cell.raw, other.name, target.name, axis, at, count, delete)
    for name, (sheet_name, region) in list(book.named_ranges.items()):
        if sheet_name.casefold() == target.name.casefold():
            adjusted = adjust_formula(
                "=" + region, target.name, target.name, axis, at, count, delete
            )[1:]
            book.named_ranges[name] = (sheet_name, adjusted)

    def adjust_set(values):
        return {
            value + (-count if delete else count) if value >= at else value
            for value in values
            if not (delete and at <= value < at + count)
        }

    if axis == "row":
        target.hidden_rows = adjust_set(target.hidden_rows)
        target.row_heights = {
            new: height for old, height in target.row_heights.items() for new in adjust_set({old})
        }
        if at < target.freeze_rows:
            target.freeze_rows = max(
                0, target.freeze_rows + (-min(count, target.freeze_rows - at) if delete else count)
            )
    else:
        target.hidden_columns = adjust_set(target.hidden_columns)
        target.column_widths = {
            new: width for old, width in target.column_widths.items() for new in adjust_set({old})
        }
        if at < target.freeze_columns:
            target.freeze_columns = max(
                0,
                target.freeze_columns
                + (-min(count, target.freeze_columns - at) if delete else count),
            )
    merges = []
    for region in target.merges:
        adjusted = adjust_formula("=" + region, target.name, target.name, axis, at, count, delete)[
            1:
        ]
        if "#REF!" not in adjusted:
            merges.append(adjusted)
    target.merges = merges
    for collection in (target.conditional_rules, target.charts):
        for item in list(collection):
            adjusted = adjust_formula(
                "=" + item["range"], target.name, target.name, axis, at, count, delete
            )[1:]
            if "#REF!" in adjusted:
                collection.remove(item)
            else:
                item["range"] = adjusted
    target.filter_spec = None


def rename_sheet(book, sheet, name):
    target = book.sheet(sheet)
    old = target.name
    validate_sheet_name(name)
    if any(s is not target and s.name.casefold() == name.casefold() for s in book.sheets):
        raise ValueError("Sheet name already exists")
    for other in book.sheets:
        for cell in other.cells.values():
            if not cell.raw.startswith("="):
                continue
            try:
                tokens = tokenize(cell.raw[1:])
            except FormulaFault:
                continue
            source, result, previous = cell.raw[1:], "=", 0
            for i, token in enumerate(tokens):
                value = token.value
                if i + 1 < len(tokens) and tokens[i + 1].value == "!":
                    candidate = value[1:-1].replace("''", "'") if token.kind == "SHEET" else value
                    if candidate.casefold() == old.casefold():
                        value = "'" + name.replace("'", "''") + "'"
                result += source[previous : token.start] + value
                previous = token.end
            cell.raw = result
    target.name = name
    book.named_ranges = {
        k: (name if n.casefold() == old.casefold() else n, r)
        for k, (n, r) in book.named_ranges.items()
    }


def delete_sheet(book, sheet):
    name = book.sheet(sheet).name
    book.delete_sheet(sheet)
    for other in book.sheets:
        for cell in other.cells.values():
            cell.raw = rewrite_references(
                cell.raw,
                lambda ref, qualifier: (
                    "#REF!" if qualifier and qualifier.casefold() == name.casefold() else ref
                ),
            )
    book.named_ranges = {
        k: v for k, v in book.named_ranges.items() if v[0].casefold() != name.casefold()
    }


def sort_range(book, sheet, region, column=0, descending=False, header=True):
    span, target = CellRange.parse(region), book.sheet(sheet)
    span.coordinates(limit=10000)
    if not 0 <= column < span.width:
        raise ValueError("Sort column outside range")
    if any(
        CellRange.parse(m).top <= span.bottom and CellRange.parse(m).bottom >= span.top
        for m in target.merges
    ):
        raise ValueError("Unmerge cells before sorting")
    evaluator = Evaluator(book)
    first = span.top + int(header)
    rows = list(range(first, span.bottom + 1))

    def key(r):
        value = evaluator.value(sheet, r, span.left + column)
        if value is None:
            return 3, ""
        if isinstance(value, Error):
            return 2, str(value)
        if isinstance(value, (int, float)):
            return 0, value
        return 1, str(value).casefold()

    ordered = sorted(rows, key=key, reverse=descending)
    contents = {
        (r, c): deepcopy(target.cell(r, c, False))
        for r in rows
        for c in range(span.left, span.right + 1)
    }
    for new, old in zip(rows, ordered, strict=True):
        for c in range(span.left, span.right + 1):
            cell = deepcopy(contents[(old, c)])
            cell.raw = translate_formula(cell.raw, new - old, 0)
            target.cells[(new, c)] = cell


def filtered_rows(book, sheet, evaluator=None):
    target = book.sheet(sheet)
    if not target.filter_spec:
        return set()
    spec = target.filter_spec
    validate_filter(spec)
    span = CellRange.parse(spec["range"])
    if span.height > 200000:
        raise ValueError("Filter range exceeds 200000 rows")
    evaluator = evaluator or Evaluator(book)
    conditions = spec.get(
        "conditions", [{"column": spec["column"], "criterion": spec["criterion"]}]
    )
    match = all if spec.get("match", "all") == "all" else any
    return {
        r
        for r in range(span.top + int(spec.get("header", True)), span.bottom + 1)
        if not match(
            criterion_matches(
                evaluator.value(sheet, r, span.left + condition["column"]), condition["criterion"]
            )
            for condition in conditions
        )
    }


def merge_range(book, sheet, region, unmerge=False, contents="strict"):
    target, span = book.sheet(sheet), CellRange.parse(region)
    span.coordinates(limit=10000)

    def intersects(other):
        return not (
            other.bottom < span.top
            or other.top > span.bottom
            or other.right < span.left
            or other.left > span.right
        )

    if unmerge:
        target.merges = [m for m in target.merges if not intersects(CellRange.parse(m))]
        return
    if span.size < 2:
        return
    if any(intersects(CellRange.parse(m)) for m in target.merges):
        raise ValueError("Merged regions cannot overlap")
    populated = [
        target.cell(r, c, False)
        for r, c in span.coordinates(limit=10000)
        if (r, c) != (span.top, span.left)
        and (target.cell(r, c, False).raw or target.cell(r, c, False).note)
    ]
    if populated and contents == "strict":
        raise ValueError("Merge would discard data; clear other cells explicitly first")
    if contents not in {"strict", "combine", "first"}:
        raise ValueError("Merge content mode must be strict/combine/first")
    if populated:
        anchor = target.cell(span.top, span.left)
        if contents == "combine":
            evaluator = Evaluator(book)
            values = [
                exact_text(evaluator.value(sheet, r, c))
                for r, c in span.coordinates(limit=10000)
                if target.cell(r, c, False).raw
            ]
            combined = "\n".join(values)
            if len(combined) > 32766:
                raise ValueError("Combined merged text exceeds cell text limit")
            notes = [cell.note for cell in [anchor, *populated] if cell.note]
            anchor.raw = "'" + combined
            anchor.note = "\n".join(notes)
            anchor.style.wrap = True
            target.row_heights[span.top] = min(
                12, max(target.row_heights.get(span.top, 1), len(values))
            )
        for r, c in span.coordinates(limit=10000):
            if (r, c) != (span.top, span.left):
                cell = target.cell(r, c)
                cell.raw, cell.note = "", ""
    target.merges.append(str(span))


def apply_borders(book, sheet, region, preset="all", border_style="thin", color=""):
    if preset not in {"all", "outer", "inner", "top", "bottom", "left", "right", "none"}:
        raise ValueError("Invalid border preset")
    if border_style not in BORDER_STYLES:
        raise ValueError("Invalid border style")
    span, target = CellRange.parse(region), book.sheet(sheet)
    for r, c in span.coordinates(limit=10000):
        borders = target.cell(r, c).style.borders
        if preset == "none":
            borders.clear()
            for rr, cc, opposite in (
                (r - 1, c, "bottom"),
                (r + 1, c, "top"),
                (r, c - 1, "right"),
                (r, c + 1, "left"),
            ):
                neighbor = target.cells.get((rr, cc))
                if neighbor:
                    neighbor.style.borders.pop(opposite, None)
            continue
        for side, outer in {
            "top": r == span.top,
            "bottom": r == span.bottom,
            "left": c == span.left,
            "right": c == span.right,
        }.items():
            enabled = (
                preset == "all"
                or (preset == "outer" and outer)
                or (preset == "inner" and not outer)
                or (preset == side and outer)
            )
            if enabled:
                if border_style == "none":
                    borders.pop(side, None)
                else:
                    borders[side] = BorderEdge(border_style, color)
                rr, cc, opposite = {
                    "top": (r - 1, c, "bottom"),
                    "bottom": (r + 1, c, "top"),
                    "left": (r, c - 1, "right"),
                    "right": (r, c + 1, "left"),
                }[side]
                neighbor = target.cells.get((rr, cc))
                if neighbor and opposite in neighbor.style.borders:
                    if border_style == "none":
                        neighbor.style.borders.pop(opposite, None)
                    else:
                        neighbor.style.borders[opposite] = BorderEdge(border_style, color)


def clear_formats(book, sheet, region):
    for r, c in CellRange.parse(region).coordinates(limit=10000):
        book.sheet(sheet).cell(r, c).style = CellStyle()


def format_range(book, sheet, region, **styles):
    for r, c in CellRange.parse(region).coordinates(limit=10000):
        style = book.sheet(sheet).cell(r, c).style
        for key, value in styles.items():
            if key not in CellStyle.__dataclass_fields__:
                raise ValueError(f"Unknown style: {key}")
            setattr(style, key, value)


def find_cells(book, sheet, query, case_sensitive=False, formulas=True):
    target, evaluator = book.sheet(sheet), Evaluator(book)
    matches = []
    for (r, c), cell in sorted(target.cells.items()):
        source = cell.raw if formulas else display_value(evaluator.value(sheet, r, c))
        if (query if case_sensitive else query.casefold()) in (
            source if case_sensitive else source.casefold()
        ):
            matches.append(address(r, c))
    return matches


def replace_cells(book, sheet, query, replacement, case_sensitive=False):
    if not query:
        raise ValueError("Search text cannot be empty")
    count = 0
    pattern = re.compile(re.escape(query), 0 if case_sensitive else re.IGNORECASE)
    for cell in book.sheet(sheet).cells.values():
        cell.raw, changed = pattern.subn(lambda _m: replacement, cell.raw)
        count += changed
    return count
