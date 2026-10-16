from __future__ import annotations

import re
from dataclasses import dataclass

MAX_ROWS = 1_048_576
MAX_COLUMNS = 16_384
_ADDRESS = re.compile(r"\$?([A-Za-z]{1,3})\$?([1-9][0-9]*)\Z")


def column_name(column: int) -> str:
    if not 0 <= column < MAX_COLUMNS:
        raise ValueError("Column outside A:XFD")
    result = ""
    column += 1
    while column:
        column, remainder = divmod(column - 1, 26)
        result = chr(65 + remainder) + result
    return result


def parse_address(reference: str) -> tuple[int, int]:
    match = _ADDRESS.fullmatch(reference.strip())
    if match is None:
        raise ValueError(f"Invalid cell address: {reference}")
    column = 0
    for letter in match[1].upper():
        column = column * 26 + ord(letter) - 64
    row = int(match[2])
    if row > MAX_ROWS or column > MAX_COLUMNS:
        raise ValueError(f"Cell address outside worksheet: {reference}")
    return row - 1, column - 1


def address(row: int, column: int) -> str:
    if not 0 <= row < MAX_ROWS:
        raise ValueError("Row outside worksheet")
    return f"{column_name(column)}{row + 1}"


@dataclass(frozen=True)
class CellRange:
    top: int
    left: int
    bottom: int
    right: int

    def __post_init__(self):
        if not (
            0 <= self.top <= self.bottom < MAX_ROWS and 0 <= self.left <= self.right < MAX_COLUMNS
        ):
            raise ValueError("Invalid cell range")

    @classmethod
    def parse(cls, text: str) -> CellRange:
        parts = text.strip().split(":")
        if len(parts) > 2:
            raise ValueError("Expected A1 or A1:B2")
        r1, c1 = parse_address(parts[0])
        r2, c2 = parse_address(parts[-1])
        return cls(min(r1, r2), min(c1, c2), max(r1, r2), max(c1, c2))

    @property
    def size(self) -> int:
        return self.height * self.width

    @property
    def height(self) -> int:
        return self.bottom - self.top + 1

    @property
    def width(self) -> int:
        return self.right - self.left + 1

    def coordinates(self, limit: int = 100_000):
        if self.size > limit:
            raise ValueError(f"Range exceeds {limit:,} cells")
        return (
            (r, c)
            for r in range(self.top, self.bottom + 1)
            for c in range(self.left, self.right + 1)
        )

    def contains(self, row: int, column: int) -> bool:
        return self.top <= row <= self.bottom and self.left <= column <= self.right

    def __str__(self) -> str:
        first, last = address(self.top, self.left), address(self.bottom, self.right)
        return first if first == last else f"{first}:{last}"
