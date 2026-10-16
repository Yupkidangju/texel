"""같은 가상 행 슬롯을 화면 렌더링과 마우스 좌표에 사용한다."""

from dataclasses import dataclass

from rich.segment import Segment
from rich.style import Style
from rich.text import Text
from textual.strip import Strip

from ..addresses import MAX_ROWS, address, column_name
from ..model import display_value
from .safe_text import safe_text

GUTTER_WIDTH = 9
WEIGHT = {"none": 0, "dotted": 1, "dashed": 1, "thin": 1, "medium": 2, "thick": 3, "double": 4}
HORIZONTAL = {"thin": "─", "medium": "━", "thick": "━", "double": "═", "dashed": "╌", "dotted": "┄"}
VERTICAL = {"thin": "│", "medium": "┃", "thick": "┃", "double": "║", "dashed": "╎", "dotted": "┆"}


@dataclass(frozen=True)
class RowSlot:
    row: int
    kind: str = "content"
    line: int = 0


def strongest(*edges):
    edges = [e for e in edges if e and e.style != "none"]
    return max(edges, key=lambda e: WEIGHT[e.style], default=None)


class GridRenderMixin:
    def row_slots(self):
        key = (self.app.session.revision, self.sheet_index, self.top, self.left, self.size.height)
        if getattr(self, "_slots_key", None) == key:
            return self._slots
        height = max(1, self.size.height - 2)
        hidden = self.sheet.hidden_rows | self._filtered
        frozen = [r for r in range(min(self.sheet.freeze_rows, height - 1)) if r not in hidden]
        slots = []

        def append(row):
            if row in self._border_rows:
                slots.append(RowSlot(row, "rule"))
            slots.extend(RowSlot(row, line=i) for i in range(self.sheet.row_heights.get(row, 1)))

        for row in frozen:
            append(row)
        slots = slots[: max(0, height - min(2, height - 1))]
        row = max(self.top, self.sheet.freeze_rows)
        while len(slots) < height and row < MAX_ROWS:
            if row not in hidden:
                append(row)
            row += 1
        self._slots_key, self._slots = key, slots[:height]
        return self._slots

    def visible_rows(self):
        return list(dict.fromkeys(slot.row for slot in self.row_slots() if slot.kind == "content"))

    def horizontal_edge(self, row, column):
        merged = self.sheet.merged_range(row, column)
        above = self.sheet.merged_range(row - 1, column) if row else None
        if merged and above and merged == above:
            return None
        current = self.sheet.cell(row, column, False).style.borders.get("top")
        previous = (
            self.sheet.cell(row - 1, column, False).style.borders.get("bottom") if row else None
        )
        return strongest(current, previous)

    def vertical_edge(self, row, column):
        if column < 0:
            return None
        merged = self.sheet.merged_range(row, column)
        before = self.sheet.merged_range(row, column - 1) if column else None
        if merged and before and merged == before:
            return None
        current = self.sheet.cell(row, column, False).style.borders.get("left")
        previous = (
            self.sheet.cell(row, column - 1, False).style.borders.get("right") if column else None
        )
        return strongest(current, previous)

    def content_groups(self, row):
        groups = []
        for column, x, width in self.visible_columns():
            merged = self.sheet.merged_range(row, column)
            if merged and groups and groups[-1][3] == merged:
                old_col, old_x, old_width, old_merge, old_end = groups.pop()
                groups.append((old_col, old_x, old_width + width, old_merge, column))
            else:
                groups.append((column, x, width, merged, column))
        return groups

    def render_line(self, y):
        width, palette = self.size.width, self.app.palette
        base = Style(color=palette["text"], bgcolor=palette["background"])
        header = Style(color=palette["muted"], bgcolor=palette["header"], bold=True)
        segments = []
        columns, slots = self.visible_columns(), self.row_slots()
        if y == 0:
            segments.append(Segment("      ▦  ", header))
            for column, _, cell_width in columns:
                style = Style(
                    color=palette["accent"]
                    if self.selection.left <= column <= self.selection.right
                    else palette["muted"],
                    bgcolor=palette["header"],
                    bold=True,
                )
                label = Text(" " + column_name(column))
                label.truncate(cell_width - 1, overflow="crop", pad=True)
                segments.extend(Segment.apply_style(label.render(self.app.console), style))
                segments.append(Segment("│", header))
        elif y == self.size.height - 1:
            label = Text(
                f"  ↕ {self.top + 1:,}   ↔ {column_name(self.left)}   {self.sheet.name}   {address(*self.cursor)}"
            )
            label.truncate(width, overflow="ellipsis", pad=True)
            segments.extend(Segment.apply_style(label.render(self.app.console), header))
        elif 0 < y <= len(slots):
            slot = slots[y - 1]
            row = slot.row
            gutter = (
                " " * GUTTER_WIDTH
                if slot.kind == "rule" or slot.line
                else f"{row + 1:>7} {'▸' if row == self.cursor[0] else ' '}"
            )
            segments.append(Segment(gutter, header))
            if slot.kind == "rule":
                self.render_rule(row, columns, segments, base)
            else:
                groups = self.content_groups(row)
                previous_right = None
                for i, (column, _, cell_width, merged, last_column) in enumerate(groups):
                    anchor = (merged.top, merged.left) if merged else (row, column)
                    cell = self.sheet.cell(*anchor, False)
                    value = self.app.session.evaluator.value(self.sheet_index, *anchor)
                    content = cell.raw if self.show_formulas else display_value(value, cell.style)
                    content = safe_text(content, multiline=cell.style.wrap).replace("␉", "⇥")
                    if cell.note:
                        content += " ◦"
                    style = self.color_style(*anchor if merged else (row, column))
                    align = (
                        cell.style.align
                        if cell.style.align != "auto"
                        else "right"
                        if isinstance(value, (int, float)) and not isinstance(value, bool)
                        else "left"
                    )
                    final = i == len(groups) - 1 and cell_width > 1
                    available = max(0, cell_width - 1 - int(final))
                    text = Text(content)
                    lines = (
                        text.wrap(self.app.console, available, overflow="fold")
                        if cell.style.wrap
                        else [text]
                    )
                    height = (
                        sum(
                            self.sheet.row_heights.get(r, 1)
                            for r in range(merged.top, merged.bottom + 1)
                        )
                        if merged
                        else self.sheet.row_heights.get(row, 1)
                    )
                    offset = (
                        sum(self.sheet.row_heights.get(r, 1) for r in range(merged.top, row))
                        if merged
                        else 0
                    )
                    index = offset + slot.line
                    extra = max(0, height - len(lines))
                    index -= (
                        extra // 2
                        if cell.style.vertical_align == "middle"
                        else extra
                        if cell.style.vertical_align == "bottom"
                        else 0
                    )
                    line = lines[index].copy() if 0 <= index < len(lines) else Text("")
                    line.truncate(available, overflow="ellipsis")
                    line.align(align, available)
                    left_edge = strongest(previous_right, self.vertical_edge(row, column))
                    right_edge = self.vertical_edge(row, last_column + 1)
                    previous_right = right_edge
                    segments.append(
                        Segment(
                            VERTICAL[left_edge.style] if left_edge else "│" if i else " ",
                            Style(color=left_edge.color or palette["text"], bgcolor=style.bgcolor)
                            if left_edge
                            else Style(color=palette["grid"], bgcolor=style.bgcolor)
                            if i
                            else style,
                        )
                    )
                    segments.extend(Segment.apply_style(line.render(self.app.console), style))
                    if final:
                        segments.append(
                            Segment(
                                VERTICAL[right_edge.style] if right_edge else "│",
                                Style(
                                    color=right_edge.color or palette["text"]
                                    if right_edge
                                    else palette["grid"],
                                    bgcolor=style.bgcolor,
                                ),
                            )
                        )
        return Strip(segments).adjust_cell_length(width, base).crop(0, width)

    def render_rule(self, row, columns, segments, base):
        previous_right = None
        for i, (column, _, width) in enumerate(columns):
            final = i == len(columns) - 1 and width > 1
            edge = self.horizontal_edge(row, column)
            style = (
                Style(color=edge.color or self.app.palette["text"], bgcolor=base.bgcolor)
                if edge
                else base
            )
            merged = self.sheet.merged_range(row, column)
            above = self.sheet.merged_range(row - 1, column) if row else None
            internal_left = bool(
                i
                and (
                    (merged and merged.contains(row, columns[i - 1][0]))
                    or (above and above.contains(row - 1, columns[i - 1][0]))
                )
            )
            if edge:
                glyph = HORIZONTAL[edge.style]
                joint_edge = strongest(edge, previous_right, self.vertical_edge(row, column))
                joint = (
                    glyph
                    if internal_left
                    else "╬"
                    if joint_edge.style == "double"
                    else "╋"
                    if WEIGHT[joint_edge.style] >= 2
                    else "┼"
                )
                segments.append(Segment(joint + glyph * (width - 1 - int(final)), style))
                if final:
                    segments.append(Segment(joint, style))
            else:
                left = strongest(previous_right, self.vertical_edge(row, column))
                right = self.vertical_edge(row, column + 1)
                left_style = (
                    Style(color=left.color or self.app.palette["text"], bgcolor=base.bgcolor)
                    if left
                    else style
                )
                right_style = (
                    Style(color=right.color or self.app.palette["text"], bgcolor=base.bgcolor)
                    if right
                    else style
                )
                segments.append(Segment(VERTICAL[left.style] if left else " ", left_style))
                segments.append(Segment(" " * (width - 1 - int(final)), style))
                if final:
                    segments.append(Segment(VERTICAL[right.style] if right else " ", right_style))
            previous_right = self.vertical_edge(row, column + 1)
