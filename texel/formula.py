from __future__ import annotations

import math
import operator
import re
from dataclasses import dataclass

from .addresses import CellRange, address, parse_address
from .functions import FUNCTIONS, function_names
from .model import Workbook, literal
from .values import Error, FormulaFault, RangeValue, number, text

_TOKEN = re.compile(
    r'(?P<SPACE>\s+)|(?P<STRING>"(?:[^"]|"")*")|'
    r"(?P<SHEET>'(?:[^']|'')*')|"
    r"(?P<ERROR>\#(?:REF!|DIV/0!|VALUE!|NAME\?|N/A|NUM!|CYCLE!|LIMIT!))|"
    r"(?P<NUMBER>(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)|"
    r"(?P<REF>\$?[A-Za-z]{1,4}\$?[1-9][0-9]*(?![\w.]))|"
    r"(?P<NAME>[^\W\d][\w.]*)|(?P<OP><=|>=|<>|[+\-*/^%&=<>(),;:!])",
    re.UNICODE,
)
PRECEDENCE = {
    "=": 10,
    "<>": 10,
    "<": 10,
    ">": 10,
    "<=": 10,
    ">=": 10,
    "&": 20,
    "+": 30,
    "-": 30,
    "*": 40,
    "/": 40,
    "^": 60,
    ":": 90,
}


@dataclass(frozen=True)
class Token:
    kind: str
    value: str
    start: int
    end: int


def tokenize(source: str) -> list[Token]:
    if len(source) > 8192:
        raise FormulaFault("#LIMIT!", "Formula exceeds 8192 characters")
    result, position = [], 0
    while position < len(source):
        match = _TOKEN.match(source, position)
        if match is None:
            raise FormulaFault("#VALUE!", f"Unexpected formula character at {position}")
        kind = match.lastgroup
        if kind != "SPACE":
            result.append(Token(kind, match[0], position, match.end()))
        position = match.end()
    result.append(Token("END", "", position, position))
    return result


class Parser:
    def __init__(self, source: str):
        self.tokens = tokenize(source)
        self.index = 0
        self.depth = 0

    @property
    def current(self):
        return self.tokens[self.index]

    def take(self, value=None):
        token = self.current
        if value is not None and token.value != value:
            raise FormulaFault("#VALUE!", f"Expected {value}")
        self.index += 1
        return token

    def parse(self):
        result = self.expression()
        if self.current.kind != "END":
            raise FormulaFault("#VALUE!", "Unexpected trailing formula input")
        return result

    def expression(self, minimum=0):
        self.depth += 1
        if self.depth > 128:
            raise FormulaFault("#LIMIT!", "Formula nesting exceeds 128")
        token = self.take()
        if token.value in {"+", "-"}:
            left = ("unary", token.value, self.expression(50))
        elif token.value == "(":
            left = self.expression()
            self.take(")")
        elif token.kind == "NUMBER":
            left = ("constant", int(token.value) if token.value.isdigit() else float(token.value))
        elif token.kind == "STRING":
            left = ("constant", token.value[1:-1].replace('""', '"'))
        elif token.kind == "ERROR":
            left = ("error", token.value)
        elif token.kind in {"REF", "NAME", "SHEET"}:
            if self.current.value == "!":
                self.take("!")
                reference = self.take()
                if reference.kind != "REF":
                    raise FormulaFault("#REF!")
                sheet_name = (
                    token.value[1:-1].replace("''", "'") if token.kind == "SHEET" else token.value
                )
                left = ("ref", sheet_name, reference.value)
            elif token.kind == "REF":
                left = ("ref", None, token.value)
            elif self.current.value == "(" and token.kind == "NAME":
                self.take("(")
                args = []
                if self.current.value != ")":
                    while True:
                        args.append(self.expression())
                        if self.current.value not in {",", ";"}:
                            break
                        self.take()
                self.take(")")
                left = ("call", token.value.upper(), args)
            elif token.value.upper() in {"TRUE", "FALSE"}:
                left = ("constant", token.value.upper() == "TRUE")
            else:
                if "." in token.value:
                    raise FormulaFault("#VALUE!", "Attribute access is not formula syntax")
                left = ("name", token.value)
        else:
            raise FormulaFault("#VALUE!", "Expected a value or cell reference")
        while True:
            op = self.current.value
            if op == "%" and minimum <= 80:
                self.take()
                left = ("percent", left)
                continue
            precedence = PRECEDENCE.get(op, -1)
            if precedence < minimum:
                break
            self.take()
            right = self.expression(precedence if op == "^" else precedence + 1)
            if op == ":":
                if left[0] != "ref" or right[0] != "ref":
                    raise FormulaFault("#REF!")
                left = ("range", left, right)
            else:
                left = ("binary", op, left, right)
        self.depth -= 1
        return left


class Evaluator:
    def __init__(self, workbook: Workbook):
        self.workbook = workbook
        self.cache = {}
        self.syntax = {}
        self.visiting = set()

    def value(self, sheet: int, row: int, column: int):
        key = (sheet, row, column)
        if key in self.cache:
            return self.cache[key]
        if key in self.visiting:
            return Error("#CYCLE!", "Circular cell reference")
        if len(self.visiting) >= 128:
            return Error("#LIMIT!", "Dependency depth exceeds 128")
        self.visiting.add(key)
        try:
            raw = self.workbook.sheet(sheet).cell(row, column, False).raw
            if raw.startswith("="):
                if raw not in self.syntax:
                    self.syntax[raw] = Parser(raw[1:]).parse()
                result = self.evaluate(self.syntax[raw], sheet, row, column)
                if isinstance(result, RangeValue):
                    result = result.rows[0][0]
                if isinstance(result, complex) or (
                    isinstance(result, float) and not math.isfinite(result)
                ):
                    raise FormulaFault("#NUM!")
                if isinstance(result, str) and len(result) > 32767:
                    raise FormulaFault("#LIMIT!")
            else:
                result = literal(raw)
        except FormulaFault as exc:
            result = exc.error
        except ZeroDivisionError:
            result = Error("#DIV/0!")
        except (ValueError, TypeError, IndexError, OverflowError, ArithmeticError) as exc:
            result = Error(
                "#NUM!"
                if isinstance(exc, (OverflowError, ArithmeticError)) or "math domain" in str(exc)
                else "#VALUE!",
                str(exc),
            )
        except RecursionError:
            result = Error("#LIMIT!")
        finally:
            self.visiting.remove(key)
        self.cache[key] = result
        return result

    def resolve(self, node, current_sheet):
        try:
            sheet = current_sheet if node[1] is None else self.workbook.sheet_index(node[1])
            row, col = parse_address(node[2])
            return sheet, row, col
        except ValueError as exc:
            raise FormulaFault("#REF!", str(exc)) from exc

    def evaluate(self, node, sheet, row, column, depth=0):
        if depth >= 128:
            raise FormulaFault("#LIMIT!")

        def evaluate(child):
            return self.evaluate(child, sheet, row, column, depth + 1)

        kind = node[0]
        if kind == "constant":
            return node[1]
        if kind == "error":
            raise FormulaFault(node[1])
        if kind == "ref":
            result = self.value(*self.resolve(node, sheet))
            if isinstance(result, Error):
                raise FormulaFault(result.code, result.detail)
            return result
        if kind == "name":
            name = next(
                (n for n in self.workbook.named_ranges if n.casefold() == node[1].casefold()), None
            )
            if name is None:
                raise FormulaFault("#NAME?", node[1])
            target_sheet, span = self.workbook.named_ranges[name]
            try:
                target = self.workbook.sheet_index(target_sheet)
                region = CellRange.parse(span)
            except ValueError as exc:
                raise FormulaFault("#REF!") from exc
            return self.range_value(target, region)
        if kind == "range":
            target, r1, c1 = self.resolve(node[1], sheet)
            last = node[2]
            other, r2, c2 = self.resolve(last, target)
            if other != target:
                raise FormulaFault("#REF!")
            return self.range_value(
                target, CellRange(min(r1, r2), min(c1, c2), max(r1, r2), max(c1, c2))
            )
        if kind == "percent":
            return number(evaluate(node[1])) / 100
        if kind == "unary":
            value = number(evaluate(node[2]))
            return value if node[1] == "+" else -value
        if kind == "binary":
            op, left, right = node[1], evaluate(node[2]), evaluate(node[3])
            if op == "&":
                return text(left) + text(right)
            if op in {"=", "<>", ">", "<", ">=", "<="}:
                if isinstance(left, str) and isinstance(right, str):
                    left, right = left.casefold(), right.casefold()
                elif left is None:
                    left = 0
                elif right is None:
                    right = 0
                if type(left) is not type(right) and isinstance(left, str) != isinstance(
                    right, str
                ):
                    if op in {"=", "<>"}:
                        return op == "<>"
                    left, right = text(left), text(right)
                return {
                    "=": operator.eq,
                    "<>": operator.ne,
                    ">": operator.gt,
                    "<": operator.lt,
                    ">=": operator.ge,
                    "<=": operator.le,
                }[op](left, right)
            a, b = number(left), number(right)
            if op == "^" and abs(b) > 10000:
                raise FormulaFault("#LIMIT!")
            return {
                "+": operator.add,
                "-": operator.sub,
                "*": operator.mul,
                "/": operator.truediv,
                "^": operator.pow,
            }[op](a, b)
        if kind == "call":
            name, args = node[1], node[2]
            if name == "IFS":
                if not args or len(args) % 2:
                    raise FormulaFault("#VALUE!")
                for i in range(0, len(args), 2):
                    if evaluate(args[i]):
                        return evaluate(args[i + 1])
                raise FormulaFault("#N/A")
            if name in {"IFNA", "ISNA"}:
                if len(args) != (2 if name == "IFNA" else 1):
                    raise FormulaFault("#VALUE!")
                try:
                    result = evaluate(args[0])
                    if isinstance(result, Error):
                        raise FormulaFault(result.code, result.detail)
                    return False if name == "ISNA" else result
                except FormulaFault as exc:
                    if name == "ISNA":
                        return exc.error.code == "#N/A"
                    if exc.error.code != "#N/A":
                        raise
                    return evaluate(args[1])
                except ValueError, TypeError, ArithmeticError:
                    if name == "ISNA":
                        return False
                    raise
            if name == "IF":
                if len(args) not in {2, 3}:
                    raise FormulaFault("#VALUE!")
                return (
                    evaluate(args[1])
                    if evaluate(args[0])
                    else evaluate(args[2])
                    if len(args) == 3
                    else False
                )
            if name in {"IFERROR", "ISERROR"}:
                if len(args) != (2 if name == "IFERROR" else 1):
                    raise FormulaFault("#VALUE!")
                try:
                    result = evaluate(args[0])
                    if isinstance(result, Error):
                        raise FormulaFault(result.code)
                    return False if name == "ISERROR" else result
                except FormulaFault, ValueError, TypeError, ZeroDivisionError, ArithmeticError:
                    return True if name == "ISERROR" else evaluate(args[1])
            if name in {"ROW", "COLUMN"}:
                if not args:
                    return (row if name == "ROW" else column) + 1
                if len(args) != 1 or args[0][0] not in {"ref", "range"}:
                    raise FormulaFault("#VALUE!")
                ref = args[0][1] if args[0][0] == "range" else args[0]
                position = self.resolve(ref, sheet)
                return position[1 if name == "ROW" else 2] + 1
            if name not in FUNCTIONS:
                raise FormulaFault("#NAME?", name)
            evaluated = [evaluate(arg) for arg in args]
            try:
                return FUNCTIONS[name](*evaluated)
            except ValueError as exc:
                if name in {"SQRT", "LOG", "LN", "EXP", "POWER", "DATE"}:
                    raise FormulaFault("#NUM!", str(exc)) from exc
                raise
        raise FormulaFault("#VALUE!")

    def range_value(self, sheet, region):
        if region.size > 100000:
            raise FormulaFault("#LIMIT!", "Formula range exceeds 100000 cells")
        return RangeValue(
            [
                [self.value(sheet, r, c) for c in range(region.left, region.right + 1)]
                for r in range(region.top, region.bottom + 1)
            ]
        )


def rewrite_references(formula: str, transform) -> str:
    if not formula.startswith("="):
        return formula
    try:
        tokens = tokenize(formula[1:])
    except FormulaFault:
        return formula
    result, previous, qualifiers = "=", 0, {}
    for i, token in enumerate(tokens):
        replacement = token.value
        if token.kind == "REF":
            if i + 1 < len(tokens) and tokens[i + 1].value == "!":
                result += formula[1:][previous : token.start] + replacement
                previous = token.end
                continue
            sheet = None
            if i >= 2 and tokens[i - 1].value == "!":
                prior = tokens[i - 2]
                sheet = (
                    prior.value[1:-1].replace("''", "'") if prior.kind == "SHEET" else prior.value
                )
            elif i >= 2 and tokens[i - 1].value == ":":
                sheet = qualifiers.get(i - 2)
            qualifiers[i] = sheet
            replacement = transform(token.value, sheet)
        result += formula[1:][previous : token.start] + replacement
        previous = token.end
    return result


def translate_formula(formula: str, row_delta: int, column_delta: int) -> str:
    def move(reference, _sheet):
        try:
            row, column = parse_address(reference)
            absolute_column = reference.startswith("$")
            absolute_row = "$" in reference.lstrip("$")
            row += 0 if absolute_row else row_delta
            column += 0 if absolute_column else column_delta
            new_ref = address(row, column)
            letters = new_ref.rstrip("0123456789")
            digits = new_ref[len(letters) :]
            return (
                ("$" if absolute_column else "") + letters + ("$" if absolute_row else "") + digits
            )
        except ValueError:
            return "#REF!"

    return rewrite_references(formula, move)


__all__ = ["Evaluator", "Error", "translate_formula", "function_names"]
