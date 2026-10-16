from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Error:
    code: str
    detail: str = ""

    def __str__(self):
        return self.code


class FormulaFault(Exception):
    def __init__(self, code: str, detail: str = ""):
        self.error = Error(code, detail)
        super().__init__(detail or code)


@dataclass
class RangeValue:
    rows: list[list]

    def flat(self):
        return [value for row in self.rows for value in row]


def number(value) -> float | int:
    if isinstance(value, Error):
        raise FormulaFault(value.code, value.detail)
    if value is None or value == "":
        return 0
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, date):
        return (value - date(1899, 12, 30)).days
    try:
        return float(value)
    except (ValueError, TypeError) as exc:
        raise FormulaFault("#VALUE!", "Numeric value required") from exc


def text(value) -> str:
    if isinstance(value, Error):
        raise FormulaFault(value.code, value.detail)
    if value is None:
        return ""
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def flattened(args):
    for arg in args:
        if isinstance(arg, RangeValue):
            yield from arg.flat()
        else:
            yield arg


def value_key(value):
    """표시 반올림과 독립적인 분석용 동일성 키."""
    if value is None:
        return "blank", ""
    if isinstance(value, bool):
        return "boolean", value
    if isinstance(value, (int, float)):
        return "number", value
    if isinstance(value, date):
        return "date", value.isoformat()
    if isinstance(value, Error):
        return "error", value.code
    return "text", value


def exact_text(value):
    return text(value) if not isinstance(value, Error) else value.code
