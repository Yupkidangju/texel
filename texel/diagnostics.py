"""문서 변경 없이 수식 결과와 직접 참조를 조사한다."""

import math
from datetime import date

from .addresses import CellRange, address, parse_address
from .formula import Evaluator, Parser
from .values import Error, FormulaFault, RangeValue


def value_payload(value):
    kind = (
        "error"
        if isinstance(value, Error)
        else "blank"
        if value is None
        else "boolean"
        if isinstance(value, bool)
        else "number"
        if isinstance(value, (int, float))
        else "date"
        if isinstance(value, date)
        else "text"
    )
    return {
        "value": value.isoformat()
        if isinstance(value, date)
        else str(value)
        if isinstance(value, Error)
        else value,
        "value_type": kind,
        "error": {"code": value.code, "message": value.detail}
        if isinstance(value, Error)
        else None,
    }


def evaluate_formula(book, sheet, formula, at="A1"):
    if not formula.startswith("="):
        raise ValueError("A formula begins with =")
    index = book.sheet_index(sheet) if isinstance(sheet, str) else sheet
    row, column = parse_address(at)
    target = book.sheet(index)
    try:
        value = Evaluator(book).evaluate(Parser(formula[1:]).parse(), index, row, column)
        if isinstance(value, RangeValue):
            value = value.rows[0][0]
        if isinstance(value, complex) or isinstance(value, float) and not math.isfinite(value):
            raise FormulaFault("#NUM!")
        if isinstance(value, str) and len(value) > 32767:
            raise FormulaFault("#LIMIT!")
    except FormulaFault as exc:
        value = exc.error
    except ZeroDivisionError:
        value = Error("#DIV/0!")
    except ArithmeticError as exc:
        value = Error("#NUM!", str(exc))
    except (ValueError, TypeError, IndexError) as exc:
        value = Error("#VALUE!", str(exc))
    except RecursionError:
        value = Error("#LIMIT!")
    return {
        "sheet": target.name,
        "cell": address(row, column),
        "formula": formula,
        **value_payload(value),
    }


def formula_references(book, index, raw):
    references, unresolved = [], []
    if not raw.startswith("="):
        return references, unresolved
    try:
        tree = Parser(raw[1:]).parse()
    except FormulaFault as exc:
        return references, [str(exc)]

    def resolve(node, default):
        target = default if node[1] is None else book.sheet_index(node[1])
        return target, *parse_address(node[2])

    def add(target, span):
        item = (book.sheet(target).name, str(span))
        if item not in references:
            references.append(item)

    def visit(node):
        kind = node[0]
        try:
            if kind == "ref":
                target, r, c = resolve(node, index)
                add(target, CellRange(r, c, r, c))
            elif kind == "range":
                target, r, c = resolve(node[1], index)
                other, rr, cc = resolve(node[2], target)
                if target != other:
                    raise ValueError("Range crosses sheets")
                add(target, CellRange(min(r, rr), min(c, cc), max(r, rr), max(c, cc)))
            elif kind == "name":
                name = next(
                    (n for n in book.named_ranges if n.casefold() == node[1].casefold()), None
                )
                if name is None:
                    raise ValueError(f"Unknown range name: {node[1]}")
                sheet_name, region = book.named_ranges[name]
                add(book.sheet_index(sheet_name), CellRange.parse(region))
            elif kind == "call":
                for arg in node[2]:
                    visit(arg)
            elif kind == "binary":
                visit(node[2])
                visit(node[3])
            elif kind in {"unary", "percent"}:
                visit(node[-1])
        except (ValueError, TypeError) as exc:
            unresolved.append(str(exc))

    visit(tree)
    return references, unresolved


def trace_dependencies(book, sheet, cell, limit=200):
    if type(limit) is not int or not 1 <= limit <= 200:
        raise ValueError("Dependency limit must be 1..200")
    index = book.sheet_index(sheet) if isinstance(sheet, str) else sheet
    target, (row, col) = book.sheet(index), parse_address(cell)
    refs, unresolved = formula_references(book, index, target.cell(row, col, False).raw)
    dependents, scanned, truncated = [], 0, len(refs) > limit
    for other_index, other in enumerate(book.sheets):
        for (r, c), content in sorted(other.cells.items()):
            if not content.raw.startswith("="):
                continue
            if scanned >= 10000:
                truncated = True
                break
            scanned += 1
            dependencies, _ = formula_references(book, other_index, content.raw)
            if any(
                name == target.name and CellRange.parse(region).contains(row, col)
                for name, region in dependencies
            ):
                if len(dependents) < limit:
                    dependents.append({"sheet": other.name, "cell": address(r, c)})
                else:
                    truncated = True
    return {
        "sheet": target.name,
        "cell": address(row, col),
        "precedents": [{"sheet": s, "range": r} for s, r in refs[:limit]],
        "dependents": dependents,
        "unresolved": unresolved[:limit],
        "truncated": truncated or len(unresolved) > limit,
        "scanned_formulas": scanned,
        "scope": "direct_static",
    }
