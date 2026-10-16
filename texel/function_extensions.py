"""조건 집계, 문자열 정리, 업무일 계산의 추가 함수."""

import calendar
import math
import statistics
from datetime import date, timedelta
from decimal import ROUND_DOWN, Decimal, localcontext

from .criteria import criterion_matches
from .values import Error, FormulaFault, RangeValue, flattened, number, text


def matrix(value):
    rows = value.rows if isinstance(value, RangeValue) else [[value]]
    shape = (len(rows), len(rows[0]) if rows else 0)
    if any(len(row) != shape[1] for row in rows):
        raise FormulaFault("#VALUE!", "Ragged range")
    return shape, [cell for row in rows for cell in row]


def conditional_aggregate(kind, *args):
    if not args:
        raise FormulaFault("#VALUE!", "Criteria required")
    if kind == "COUNTIFS":
        pairs = args
        shape, first = matrix(args[0])
        amounts = [1] * len(first)
    else:
        shape, amounts = matrix(args[0])
        pairs = args[1:]
    if not pairs or len(pairs) % 2:
        raise FormulaFault("#VALUE!", "Range/criterion pairs required")
    tests = []
    for i in range(0, len(pairs), 2):
        other_shape, values = matrix(pairs[i])
        if other_shape != shape:
            raise FormulaFault("#VALUE!", "Criteria ranges must have the same shape")
        tests.append((values, pairs[i + 1]))
    numbers = []
    for i, value in enumerate(amounts):
        if all(criterion_matches(values[i], criterion) for values, criterion in tests):
            if isinstance(value, Error):
                raise FormulaFault(value.code, value.detail)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                numbers.append(value)
    if kind == "AVERAGEIFS":
        if not numbers:
            raise FormulaFault("#DIV/0!")
        return statistics.mean(numbers)
    if kind == "MINIFS":
        return min(numbers, default=0)
    if kind == "MAXIFS":
        return max(numbers, default=0)
    return sum(numbers)


def averageif(values, criterion, averages=None):
    return conditional_aggregate(
        "AVERAGEIFS", values if averages is None else averages, values, criterion
    )


def sumproduct(*args):
    if not args:
        raise FormulaFault("#VALUE!")
    matrices = [matrix(arg) for arg in args]
    if any(shape != matrices[0][0] for shape, _ in matrices):
        raise FormulaFault("#VALUE!", "SUMPRODUCT ranges must have the same shape")
    total = 0
    for values in zip(*(values for _, values in matrices), strict=True):
        for value in values:
            if isinstance(value, Error):
                raise FormulaFault(value.code, value.detail)
        total += math.prod(
            v if isinstance(v, (int, float)) and not isinstance(v, bool) else 0 for v in values
        )
    return total


def trunc(value, decimals=0):
    value, places = number(value), int(number(decimals))
    if not -308 <= places <= 308:
        raise FormulaFault("#NUM!")
    if isinstance(value, int) and places >= 0:
        return value
    decimal = Decimal(str(value))
    with localcontext() as context:
        context.prec = max(
            34, len(decimal.as_tuple().digits) + abs(places) + abs(decimal.adjusted()) + 2
        )
        result = decimal.quantize(Decimal(1).scaleb(-places), rounding=ROUND_DOWN)
    return int(result) if result == result.to_integral_value() else float(result)


def quotient(numerator, denominator):
    a, b = number(numerator), number(denominator)
    if isinstance(a, int) and isinstance(b, int):
        return (abs(a) // abs(b)) * (-1 if (a < 0) != (b < 0) else 1)
    return math.trunc(a / b)


def replace_text(value, start, count, replacement):
    source, replacement = text(value), text(replacement)
    start, count = int(number(start)), int(number(count))
    if start < 1 or count < 0:
        raise FormulaFault("#VALUE!")
    before, after = source[: start - 1], source[start - 1 + count :]
    if len(before) + len(replacement) + len(after) > 32767:
        raise FormulaFault("#LIMIT!")
    return before + replacement + after


def as_date(value):
    if isinstance(value, date):
        return value
    if isinstance(value, (int, float)):
        return date(1899, 12, 30) + timedelta(days=number(value))
    return date.fromisoformat(text(value))


def shifted_month(value, months, month_end=False):
    source, months = as_date(value), int(number(months))
    year, month = divmod(source.year * 12 + source.month - 1 + months, 12)
    if not 1 <= year <= 9999:
        raise FormulaFault("#NUM!")
    last = calendar.monthrange(year, month + 1)[1]
    return date(year, month + 1, last if month_end else min(last, source.day))


def holidays_set(holidays):
    return {as_date(v) for v in flattened([holidays]) if v not in (None, "")}


def networkdays(start, end, holidays=None):
    start, end = as_date(start), as_date(end)
    sign = 1 if start <= end else -1
    start, end = min(start, end), max(start, end)
    days = (end - start).days + 1
    if days > 100000:
        raise FormulaFault("#LIMIT!", "Calendar span exceeds 100000 days")
    excluded = holidays_set(holidays)
    return sign * sum(
        (d := start + timedelta(days=i)).weekday() < 5 and d not in excluded for i in range(days)
    )


def workday(start, days, holidays=None):
    current, remaining = as_date(start), int(number(days))
    if abs(remaining) > 100000:
        raise FormulaFault("#LIMIT!", "Calendar span exceeds 100000 days")
    excluded, step = holidays_set(holidays), 1 if remaining >= 0 else -1
    remaining = abs(remaining)
    for _ in range(100000):
        if remaining == 0:
            return current
        current += timedelta(days=step)
        if current.weekday() < 5 and current not in excluded:
            remaining -= 1
    if remaining == 0:
        return current
    raise FormulaFault("#LIMIT!", "Calendar span exceeds 100000 days")


EXTENDED_FUNCTIONS = {
    "AVERAGEIF": averageif,
    "AVERAGEIFS": lambda *a: conditional_aggregate("AVERAGEIFS", *a),
    "MINIFS": lambda *a: conditional_aggregate("MINIFS", *a),
    "MAXIFS": lambda *a: conditional_aggregate("MAXIFS", *a),
    "SUMPRODUCT": sumproduct,
    "ISEVEN": lambda v: int(number(v)) % 2 == 0,
    "ISODD": lambda v: int(number(v)) % 2 != 0,
    "SIGN": lambda v: (number(v) > 0) - (number(v) < 0),
    "TRUNC": trunc,
    "QUOTIENT": quotient,
    "EXACT": lambda a, b: text(a) == text(b),
    "CLEAN": lambda v: "".join(c for c in text(v) if ord(c) >= 32),
    "REPLACE": replace_text,
    "EDATE": shifted_month,
    "EOMONTH": lambda v, m: shifted_month(v, m, True),
    "NETWORKDAYS": networkdays,
    "WORKDAY": workday,
}
