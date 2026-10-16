"""수식과 표 필터가 공유하는 정밀한 조건 비교."""

import fnmatch
import operator
import re

from .addresses import CellRange
from .values import Error, text


def validate_filter(spec):
    if spec is None:
        return
    span = CellRange.parse(spec["range"])
    if span.height > 200000 or type(spec.get("header", True)) is not bool:
        raise ValueError("Invalid filter range or header")
    conditions = spec.get(
        "conditions", [{"column": spec["column"], "criterion": spec["criterion"]}]
    )
    if not isinstance(conditions, list) or not 1 <= len(conditions) <= 8:
        raise ValueError("Filters require 1..8 conditions")
    if spec.get("match", "all") not in {"all", "any"}:
        raise ValueError("Filter match must be all or any")
    for condition in conditions:
        column, criterion = condition["column"], condition["criterion"]
        if type(column) is not int or not 0 <= column < span.width:
            raise ValueError("Filter column outside range")
        if not isinstance(criterion, str) or len(criterion) > 32767:
            raise ValueError("Invalid filter criterion")


def criterion_matches(value, criterion):
    if isinstance(value, Error):
        return False
    if not isinstance(criterion, str):
        return value == criterion
    match = re.fullmatch(r"(>=|<=|<>|>|<|=)?(.*)", criterion, re.DOTALL)
    op, operand = match[1] or "=", match[2]
    try:
        operand = int(operand) if re.fullmatch(r"[+-]?\d+", operand) else float(operand)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return op == "<>"
    except ValueError:
        if op in {"=", "<>"}:
            pattern, i = [], 0
            while i < len(operand):
                character = operand[i]
                if character == "~" and i + 1 < len(operand):
                    i += 1
                    literal = operand[i]
                    pattern.append({"*": "[*]", "?": "[?]", "[": "[[]"}.get(literal, literal))
                else:
                    pattern.append("[[]" if character == "[" else character)
                i += 1
            equal = fnmatch.fnmatchcase(text(value).casefold(), "".join(pattern).casefold())
            return equal if op == "=" else not equal
        value, operand = text(value).casefold(), operand.casefold()
    return {
        "=": operator.eq,
        "<>": operator.ne,
        ">": operator.gt,
        "<": operator.lt,
        ">=": operator.ge,
        "<=": operator.le,
    }[op](value, operand)
