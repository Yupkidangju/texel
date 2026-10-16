from __future__ import annotations

import math
import statistics
from datetime import date, timedelta
from decimal import ROUND_DOWN, ROUND_HALF_UP, ROUND_UP, Decimal

from .criteria import criterion_matches
from .function_extensions import EXTENDED_FUNCTIONS, as_date, conditional_aggregate
from .values import Error, FormulaFault, RangeValue, flattened, number, text


def numeric_args(args):
    values = []
    for arg in args:
        if isinstance(arg, RangeValue):
            for value in arg.flat():
                if isinstance(value, Error):
                    raise FormulaFault(value.code, value.detail)
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    values.append(value)
        elif arg is not None:
            values.append(number(arg))
    return values


def average(*args):
    values = numeric_args(args)
    if not values:
        raise FormulaFault("#DIV/0!")
    return statistics.mean(values)


def rounded(value, decimals=0, mode=ROUND_HALF_UP):
    places = int(number(decimals))
    if not -308 <= places <= 308:
        raise FormulaFault("#NUM!")
    result = Decimal(str(number(value))).quantize(Decimal(1).scaleb(-places), rounding=mode)
    return float(result)


def countif(values, criterion):
    return sum(criterion_matches(v, criterion) for v in flattened([values]))


def sumif(values, criterion, sums=None):
    return conditional_aggregate("SUMIFS", values if sums is None else sums, values, criterion)


def index(values, row, column=1):
    rows = values.rows if isinstance(values, RangeValue) else [[values]]
    r, c = int(number(row)) - 1, int(number(column)) - 1
    if r < 0 or c < 0 or r >= len(rows) or c >= len(rows[r]):
        raise FormulaFault("#REF!")
    return rows[r][c]


def match(lookup, values, match_type=1):
    candidates = list(flattened([values]))
    mode = int(number(match_type))
    if mode not in {-1, 0, 1}:
        raise FormulaFault("#VALUE!")
    best = None
    for i, candidate in enumerate(candidates):
        if criterion_matches(candidate, lookup):
            return i + 1
        if mode:
            try:
                if (mode == 1 and candidate <= lookup) or (mode == -1 and candidate >= lookup):
                    if (
                        best is None
                        or (mode == 1 and candidate > candidates[best])
                        or (mode == -1 and candidate < candidates[best])
                    ):
                        best = i
            except TypeError:
                pass
    if best is None:
        raise FormulaFault("#N/A")
    return best + 1


def vlookup(lookup, table, column, approximate=True):
    if not isinstance(table, RangeValue):
        raise FormulaFault("#VALUE!")
    first = RangeValue([[row[0]] for row in table.rows])
    return index(table, match(lookup, first, 1 if approximate else 0), column)


NOT_FOUND = Error("#N/A")


def xlookup(lookup, lookup_values, return_values, fallback=NOT_FOUND):
    targets, amounts = list(flattened([lookup_values])), list(flattened([return_values]))
    if len(targets) != len(amounts):
        raise FormulaFault("#VALUE!")
    for key, value in zip(targets, amounts, strict=True):
        if criterion_matches(key, lookup):
            return value
    return fallback


def make_date(year, month, day):
    year, month, day = int(number(year)), int(number(month)), int(number(day))
    if 0 <= year < 1900:
        year += 1900
    year += (month - 1) // 12
    month = (month - 1) % 12 + 1
    return date(year, month, 1) + timedelta(days=day - 1)


def substitute(value, old, new, occurrence=None):
    source, old, new = text(value), text(old), text(new)
    if occurrence is None:
        count = source.count(old) if old else len(source) + 1
        if len(source) + count * (len(new) - len(old)) > 32767:
            raise FormulaFault("#LIMIT!")
        return source.replace(old, new)
    n = int(number(occurrence))
    if n < 1 or not old:
        raise FormulaFault("#VALUE!")
    chunks = source.split(old)
    if n >= len(chunks):
        return source
    if len(source) - len(old) + len(new) > 32767:
        raise FormulaFault("#LIMIT!")
    return old.join(chunks[:n]) + new + old.join(chunks[n:])


def repeat(value, repetitions):
    value, repetitions = text(value), int(number(repetitions))
    if repetitions < 0:
        raise FormulaFault("#VALUE!")
    if len(value) * repetitions > 32767:
        raise FormulaFault("#LIMIT!")
    return value * repetitions


def concatenate(*args, delimiter="", skip_blank=False):
    pieces, length = [], 0
    for value in flattened(args):
        if skip_blank and value in (None, ""):
            continue
        piece = text(value)
        length += len(piece) + (len(delimiter) if pieces else 0)
        if length > 32767:
            raise FormulaFault("#LIMIT!")
        pieces.append(piece)
    return delimiter.join(pieces)


def find(needle, value, start=1, case_sensitive=True):
    needle, source = text(needle), text(value)
    if not case_sensitive:
        needle, source = needle.casefold(), source.casefold()
    start = int(number(start))
    if start < 1:
        raise FormulaFault("#VALUE!")
    position = source.find(needle, start - 1)
    if position < 0:
        raise FormulaFault("#VALUE!")
    return position + 1


def sliced(value, count=1, right=False):
    count = int(number(count))
    if count < 0:
        raise FormulaFault("#VALUE!")
    return text(value)[-count:] if right and count else text(value)[:count]


def mid(value, start, count):
    start, count = int(number(start)), int(number(count))
    if start < 1 or count < 0:
        raise FormulaFault("#VALUE!")
    return text(value)[start - 1 : start - 1 + count]


def standard_deviation(*args):
    values = numeric_args(args)
    if len(values) < 2:
        raise FormulaFault("#DIV/0!")
    return statistics.stdev(values)


# 함수 목록은 도움말과 MCP가 그대로 소비하는 단일 레지스트리다.
FUNCTIONS = {
    "SUM": lambda *a: sum(numeric_args(a)),
    "AVERAGE": average,
    "MIN": lambda *a: min(numeric_args(a), default=0),
    "MAX": lambda *a: max(numeric_args(a), default=0),
    "COUNT": lambda *a: sum(
        isinstance(v, (int, float)) and not isinstance(v, bool) for v in flattened(a)
    ),
    "COUNTA": lambda *a: sum(v is not None and v != "" for v in flattened(a)),
    "COUNTBLANK": lambda *a: sum(v is None or v == "" for v in flattened(a)),
    "MEDIAN": lambda *a: statistics.median(numeric_args(a)),
    "STDEV": standard_deviation,
    "STDEV.S": standard_deviation,
    "STDEV.P": lambda *a: statistics.pstdev(numeric_args(a)),
    "VAR.S": lambda *a: statistics.variance(numeric_args(a)),
    "PRODUCT": lambda *a: math.prod(numeric_args(a)),
    "SUMSQ": lambda *a: sum(v * v for v in numeric_args(a)),
    "ABS": lambda v: abs(number(v)),
    "ROUND": rounded,
    "ROUNDUP": lambda v, n=0: rounded(v, n, ROUND_UP),
    "ROUNDDOWN": lambda v, n=0: rounded(v, n, ROUND_DOWN),
    "INT": lambda v: math.floor(number(v)),
    "MOD": lambda a, b: number(a) % number(b),
    "POWER": lambda a, b: number(a) ** number(b),
    "SQRT": lambda v: math.sqrt(number(v)),
    "CEILING": lambda v, s=1: math.ceil(number(v) / number(s)) * number(s),
    "FLOOR": lambda v, s=1: math.floor(number(v) / number(s)) * number(s),
    "LOG": lambda v, base=10: math.log(number(v), number(base)),
    "LN": lambda v: math.log(number(v)),
    "EXP": lambda v: math.exp(number(v)),
    "AND": lambda *a: all(bool(v) for v in flattened(a)),
    "OR": lambda *a: any(bool(v) for v in flattened(a)),
    "NOT": lambda v: not bool(v),
    "ISBLANK": lambda v: v is None or v == "",
    "ISNUMBER": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "ISTEXT": lambda v: isinstance(v, str),
    "SUMIF": sumif,
    "COUNTIF": countif,
    "SUMIFS": lambda *a: conditional_aggregate("SUMIFS", *a),
    "COUNTIFS": lambda *a: conditional_aggregate("COUNTIFS", *a),
    "LEFT": sliced,
    "RIGHT": lambda v, n=1: sliced(v, n, True),
    "MID": mid,
    "LEN": lambda v: len(text(v)),
    "TRIM": lambda v: " ".join(text(v).split()),
    "UPPER": lambda v: text(v).upper(),
    "LOWER": lambda v: text(v).lower(),
    "PROPER": lambda v: text(v).title(),
    "CONCAT": concatenate,
    "CONCATENATE": concatenate,
    "TEXTJOIN": lambda delim, skip, *a: concatenate(*a, delimiter=text(delim), skip_blank=skip),
    "SUBSTITUTE": substitute,
    "FIND": find,
    "SEARCH": lambda n, v, s=1: find(n, v, s, False),
    "VALUE": number,
    "REPT": repeat,
    "DATE": make_date,
    "TODAY": date.today,
    "YEAR": lambda v: as_date(v).year,
    "MONTH": lambda v: as_date(v).month,
    "DAY": lambda v: as_date(v).day,
    "DAYS": lambda end, start: (as_date(end) - as_date(start)).days,
    "WEEKDAY": lambda v: (as_date(v).weekday() + 1) % 7 + 1,
    "INDEX": index,
    "MATCH": match,
    "VLOOKUP": vlookup,
    "XLOOKUP": xlookup,
}

FUNCTIONS.update(EXTENDED_FUNCTIONS)

SPECIAL_FUNCTIONS = {"IF", "IFERROR", "ISERROR", "ROW", "COLUMN", "IFNA", "IFS", "ISNA"}


def function_names():
    return sorted(set(FUNCTIONS) | SPECIAL_FUNCTIONS)
