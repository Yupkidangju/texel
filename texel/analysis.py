from __future__ import annotations

import statistics
from collections import Counter, defaultdict
from copy import deepcopy

from .addresses import CellRange, address
from .formula import Evaluator, translate_formula
from .model import display_value, literal
from .values import Error, exact_text, value_key


def numeric(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def values_for(book, sheet, region):
    span = CellRange.parse(region)
    span.coordinates(limit=100000)
    evaluator = Evaluator(book)
    return span, [
        [evaluator.value(sheet, r, c) for c in range(span.left, span.right + 1)]
        for r in range(span.top, span.bottom + 1)
    ]


def profile_range(book, sheet, region, header=True):
    span, rows = values_for(book, sheet, region)
    names = [display_value(v) or address(span.top, span.left + i) for i, v in enumerate(rows[0])]
    data = rows[1:] if header else rows
    columns = []
    for i in range(span.width):
        values = [row[i] for row in data]
        numbers = [value for value in values if numeric(value)]
        missing = sum(value is None or value == "" for value in values)
        counts = Counter(value_key(v) for v in values if v is not None and v != "")
        labels = {value_key(v): exact_text(v) for v in values if v is not None and v != ""}
        columns.append(
            {
                "name": names[i] if header else address(span.top, span.left + i),
                "count": len(values),
                "missing": missing,
                "errors": sum(isinstance(v, Error) for v in values),
                "numeric_count": len(numbers),
                "unique": len(counts),
                "sum": sum(numbers),
                "mean": statistics.mean(numbers) if numbers else None,
                "median": statistics.median(numbers) if numbers else None,
                "min": min(numbers) if numbers else None,
                "max": max(numbers) if numbers else None,
                "std": statistics.stdev(numbers) if len(numbers) > 1 else None,
                "top": [
                    {"value": labels[value], "count": count}
                    for value, count in counts.most_common(5)
                ],
            }
        )
    return {"range": str(span), "rows": len(data), "columns": columns}


def selection_summary(evaluator, sheet, region):
    if region.size > 10000:
        return {"count": region.size, "sum": None, "mean": None}
    values = [evaluator.value(sheet, r, c) for r, c in region.coordinates(limit=10000)]
    numbers = [v for v in values if numeric(v)]
    return {
        "count": sum(v is not None for v in values),
        "sum": sum(numbers),
        "mean": statistics.mean(numbers) if numbers else None,
    }


def pivot_table(
    book, sheet, region, key_columns, value_column, aggregate="sum", name="Pivot", header=True
):
    span, rows = values_for(book, sheet, region)
    if (
        not key_columns
        or any(not 0 <= c < span.width for c in key_columns)
        or not 0 <= value_column < span.width
    ):
        raise ValueError("Pivot columns must be inside the source range")
    if aggregate not in {"sum", "mean", "count", "min", "max"}:
        raise ValueError("Pivot aggregate: sum/mean/count/min/max")
    grouped = defaultdict(list)
    key_values = {}
    for row in rows[int(header) :]:
        key = tuple(value_key(row[c]) for c in key_columns)
        key_values[key] = [row[c] for c in key_columns]
        grouped[key].append(row[value_column])
    result = book.add_sheet(name)
    target = book.sheet(result)
    headers = [display_value(rows[0][c]) if header else f"Key {c + 1}" for c in key_columns]
    headers.append(
        f"{aggregate}({display_value(rows[0][value_column]) if header else value_column + 1})"
    )
    for c, value in enumerate(headers):
        target.set_raw(
            0,
            c,
            "'" + value
            if value.startswith(("=", "'")) or not isinstance(literal(value), str)
            else value,
        )
        target.cell(0, c).style.bold = True
    for r, (key, values) in enumerate(sorted(grouped.items()), 1):
        numbers = [v for v in values if numeric(v)]
        value = (
            len([v for v in values if v is not None])
            if aggregate == "count"
            else sum(numbers)
            if aggregate == "sum"
            else statistics.mean(numbers)
            if aggregate == "mean" and numbers
            else min(numbers)
            if aggregate == "min" and numbers
            else max(numbers)
            if aggregate == "max" and numbers
            else None
        )
        for c, original in enumerate(key_values[key]):
            text = exact_text(original)
            target.set_raw(
                r,
                c,
                "'" + text
                if isinstance(original, str)
                and (text.startswith(("=", "'")) or not isinstance(literal(text), str))
                else text,
            )
        target.set_raw(r, len(key), exact_text(value))
    target.freeze_rows = 1
    return result


def deduplicate(book, sheet, region, header=True):
    span, rows = values_for(book, sheet, region)
    target = book.sheet(sheet)
    seen, originals = set(), []
    for offset, values in enumerate(rows):
        r = span.top + offset
        key = tuple(value_key(v) for v in values)
        if offset < int(header) or key not in seen:
            originals.append(
                (r, [deepcopy(target.cell(r, c, False)) for c in range(span.left, span.right + 1)])
            )
            seen.add(key)
    for r in range(span.top, span.bottom + 1):
        for c in range(span.left, span.right + 1):
            target.cells.pop((r, c), None)
    for dr, (old_row, cells) in enumerate(originals):
        for dc, cell in enumerate(cells):
            cell.raw = translate_formula(cell.raw, span.top + dr - old_row, 0)
            target.cells[(span.top + dr, span.left + dc)] = cell
    return len(rows) - len(originals)


def chart_text(book, sheet, region, kind="bar", width=36, header=True):
    span, rows = values_for(book, sheet, region)
    if span.width < 2:
        raise ValueError("Select label and numeric columns")
    if kind not in {"bar", "line"}:
        raise ValueError("Chart kind must be bar or line")
    samples = [(display_value(row[0]), row[1]) for row in rows[int(header) :] if numeric(row[1])]
    if not samples:
        raise ValueError("The chart needs numeric values")
    if len(samples) > 1000:
        raise ValueError("Chart exceeds 1000 points; aggregate first")
    title = display_value(rows[0][1]) if header else "Chart"
    maximum = max(abs(value) for _, value in samples) or 1
    lines = [title, "─" * max(10, min(72, width + 24))]
    if kind == "line":
        low, high = min(v for _, v in samples), max(v for _, v in samples)
        blocks = "▁▂▃▄▅▆▇█"
        lines.append(
            "".join(
                blocks[min(7, int((v - low) / (high - low or 1) * 7))] for _, v in samples[:100]
            )
        )
    for label, value in samples[:100]:
        length = int(abs(value) / maximum * width)
        bar = ("◀" if value < 0 else "") + "█" * length
        lines.append(f"{label[:18]:<18} {bar:<{width + 1}} {display_value(value)}")
    if len(samples) > 100:
        lines.append(f"… {len(samples) - 100} additional points")
    return "\n".join(lines)
