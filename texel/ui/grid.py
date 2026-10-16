from __future__ import annotations

from rich.style import Style
from textual import events
from textual.message import Message
from textual.widget import Widget

from ..addresses import MAX_COLUMNS, MAX_ROWS, CellRange
from ..editing import filtered_rows
from ..functions import criterion_matches
from ..navigation import jump_target
from ..values import Error
from .grid_render import GUTTER_WIDTH, GridRenderMixin


class SpreadsheetGrid(GridRenderMixin, Widget, can_focus=True):
    DEFAULT_CSS = """
    SpreadsheetGrid { width: 1fr; height: 1fr; min-height: 5; background: $background; }
    SpreadsheetGrid:focus { border: none; }
    """

    class SelectionChanged(Message):
        pass

    class StartEdit(Message):
        def __init__(self, replacement=None):
            super().__init__()
            self.replacement = replacement

    class Pasted(Message):
        def __init__(self, text):
            super().__init__()
            self.text = text

    class ColumnResized(Message):
        def __init__(self, column, width):
            super().__init__()
            self.column, self.width = column, width

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cursor = (0, 0)
        self.anchor = (0, 0)
        self.top, self.left = 0, 0
        self._dragging = False
        self._resizing = None
        self._resize_width = None
        self._filtered = set()
        self.show_formulas = False
        self._border_rows = set()
        self._selection_override = None
        self._selection_context = None

    @property
    def sheet_index(self):
        return self.app.sheet_index

    @property
    def sheet(self):
        return self.app.session.workbook.sheet(self.sheet_index)

    @property
    def selection(self):
        r, c = self.cursor
        ar, ac = self.anchor
        span = CellRange(min(r, ar), min(c, ac), max(r, ar), max(c, ac))
        if (
            self._selection_context == (self.app.session.store.path, self.sheet_index)
            and self._selection_override is not None
        ):
            span = self._selection_override
        for _ in range(len(self.sheet.merges) + 1):
            expanded = span
            for raw in self.sheet.merges:
                merged = CellRange.parse(raw)
                if not (
                    merged.bottom < span.top
                    or merged.top > span.bottom
                    or merged.right < span.left
                    or merged.left > span.right
                ):
                    expanded = CellRange(
                        min(expanded.top, merged.top),
                        min(expanded.left, merged.left),
                        max(expanded.bottom, merged.bottom),
                        max(expanded.right, merged.right),
                    )
            if expanded == span:
                break
            span = expanded
        return span

    def update_model(self):
        self._slots_key = None
        self._border_rows = {
            r + offset
            for (r, _), cell in self.sheet.cells.items()
            for side, offset in (("top", 0), ("bottom", 1))
            if side in cell.style.borders and cell.style.borders[side].style != "none"
        }
        self._filtered = filtered_rows(
            self.app.session.workbook, self.sheet_index, self.app.session.evaluator
        )
        self.refresh()

    def visible_columns(self):
        width, x, columns = self.size.width, GUTTER_WIDTH, []

        def column_width(column):
            configured = (
                self._resize_width
                if self._resizing and self._resizing[0] == column
                else self.sheet.column_widths.get(column, 14)
            )
            return max(4, min(60, configured))

        # 동결 폭보다 스크롤 영역의 최소 폭을 먼저 예약한다.
        budget = max(0, width - GUTTER_WIDTH - 4)
        frozen = []
        used = 0
        active = self.cursor[1]
        if (
            active < self.sheet.freeze_columns
            and active not in self.sheet.hidden_columns
            and budget
        ):
            frozen.append((active, min(column_width(active), budget)))
            used = frozen[0][1]
        for column in range(self.sheet.freeze_columns):
            if column in self.sheet.hidden_columns or column == active and frozen:
                continue
            cell_width = column_width(column)
            if used + cell_width > budget:
                break
            frozen.append((column, cell_width))
            used += cell_width
        for column, cell_width in sorted(frozen):
            columns.append((column, x, cell_width))
            x += cell_width
        for column in range(max(self.left, self.sheet.freeze_columns), MAX_COLUMNS):
            if x >= width:
                break
            if column in self.sheet.hidden_columns:
                continue
            cell_width = min(column_width(column), width - x)
            columns.append((column, x, cell_width))
            x += cell_width
        return columns

    def advance(self, dr, dc, extend=False, origin=None):
        row, column = self.cursor if origin is None else origin
        merged = self.sheet.merged_range(row, column)
        if merged and not extend:
            row = merged.bottom if dr > 0 else merged.top if dr < 0 else row
            column = merged.right if dc > 0 else merged.left if dc < 0 else column
        self.move(row + dr, column + dc, extend)

    def move(self, row, column, extend=False, preserve_selection=False):
        if not preserve_selection:
            self._selection_override = None
        row, column = max(0, min(MAX_ROWS - 1, row)), max(0, min(MAX_COLUMNS - 1, column))
        hidden = self.sheet.hidden_rows | self._filtered
        delta = -1 if row < self.cursor[0] else 1
        while row in hidden and 0 <= row + delta < MAX_ROWS:
            row += delta
        delta = -1 if column < self.cursor[1] else 1
        while column in self.sheet.hidden_columns and 0 <= column + delta < MAX_COLUMNS:
            column += delta
        if not extend:
            row, column = self.sheet.merge_anchor(row, column)
        self.cursor = row, column
        if not extend:
            self.anchor = self.cursor
        if row not in self.visible_rows():
            if row < self.top:
                self.top = max(self.sheet.freeze_rows, row)
            else:
                self.top = max(
                    self.sheet.freeze_rows,
                    row - max(0, self.size.height - self.sheet.freeze_rows - 3),
                )
                if row not in self.visible_rows():
                    self.top = row
        available = next((w for c, _, w in self.visible_columns() if c == column), 0)
        if available < min(4, max(0, self.size.width - GUTTER_WIDTH)):
            self.left = max(self.sheet.freeze_columns, column)
        self.changed()

    def select_range(self, span):
        self.anchor = span.top, span.left
        self.move(span.bottom, span.right, extend=True)

    def select_extent(self, span):
        if not span.contains(*self.cursor):
            self.move(span.top, span.left)
        self._selection_override = span
        self._selection_context = (self.app.session.store.path, self.sheet_index)
        self.changed()

    def changed(self):
        self.refresh()
        self.post_message(self.SelectionChanged())

    def on_resize(self):
        if self.is_mounted:
            self.move(*self.cursor, extend=True, preserve_selection=True)

    def color_style(self, row, column):
        palette = self.app.palette
        cell = self.sheet.cell(row, column, False)
        value = self.app.session.evaluator.value(self.sheet_index, row, column)
        background = cell.style.background or (
            palette["surface"] if row % 2 == 0 else palette["background"]
        )
        foreground = cell.style.foreground or palette["text"]
        for rule in self.sheet.conditional_rules:
            if CellRange.parse(rule["range"]).contains(row, column):
                op = {
                    "greaterThan": ">",
                    "lessThan": "<",
                    "equal": "=",
                    "greaterThanOrEqual": ">=",
                }.get(rule.get("operator"), ">")
                if criterion_matches(value, op + str(rule["value"])):
                    background = rule.get("color", "#0f766e")
        if self.selection.contains(row, column):
            background, foreground = palette["selection"], palette["selection_text"]
        if self.cursor == (row, column):
            background, foreground = palette["cursor"], palette["cursor_text"]
        if isinstance(value, Error):
            foreground = palette["error"]
        return Style(
            color=foreground,
            bgcolor=background,
            bold=cell.style.bold or self.cursor == (row, column),
            underline=cell.style.underline,
            italic=cell.style.italic,
            strike=cell.style.strike,
        )

    def cell_at(self, x, y, clamp=False):
        rows, columns = self.row_slots(), self.visible_columns()
        if not rows or not columns:
            return None
        if clamp:
            y = max(1, min(len(rows), y))
            x = max(GUTTER_WIDTH, min(self.size.width - 1, x))
        if not 1 <= y <= len(rows):
            return None
        for column, start, cell_width in columns:
            if start <= x < start + cell_width:
                row = rows[y - 1].row
                return self.sheet.merge_anchor(row, column)
        return None

    def on_mouse_down(self, event: events.MouseDown):
        if event.button in {1, 3} and self.app.editing and not self.app.commit_edit():
            self.app.formula_input.screen.set_focus(self.app.formula_input, scroll_visible=False)
            event.stop()
            event.prevent_default()
            return
        if event.button == 3:
            self.screen.set_focus(self, scroll_visible=False)
            context = "cell"
            if event.y == 0:
                for column, x, width in self.visible_columns():
                    if x <= event.x < x + width:
                        self.anchor = (0, column)
                        self.move(self.sheet.used_range.bottom, column, True)
                        context = "column"
                        break
            elif event.x < GUTTER_WIDTH and 1 <= event.y <= len(self.row_slots()):
                row = self.row_slots()[event.y - 1].row
                self.anchor = (row, 0)
                self.move(row, self.sheet.used_range.right, True)
                context = "row"
            else:
                position = self.cell_at(event.x, event.y)
                if position and not self.selection.contains(*position):
                    self.move(*position)
            self.app.open_context_menu(
                event.screen_x or self.region.x + event.x,
                event.screen_y or self.region.y + event.y,
                context,
            )
            event.stop()
            event.prevent_default()
            return
        if event.button != 1:
            return
        self.screen.set_focus(self, scroll_visible=False)
        event.stop()
        if event.y == 0:
            for column, x, cell_width in self.visible_columns():
                if abs(event.x - (x + cell_width - 1)) <= 1:
                    self._resizing = column, event.x, cell_width
                    self._resize_width = cell_width
                    self.capture_mouse()
                    return
                if x <= event.x < x + cell_width:
                    self.anchor = (0, column)
                    self.move(self.sheet.used_range.bottom, column, True)
                    return
        position = self.cell_at(event.x, event.y)
        if event.x < GUTTER_WIDTH and 1 <= event.y <= len(self.row_slots()):
            row = self.row_slots()[event.y - 1].row
            self.anchor = (row, 0)
            self.move(row, self.sheet.used_range.right, True)
            return
        if position:
            self.move(*position, extend=event.shift)
            self._dragging = True
            self.capture_mouse()

    def on_mouse_move(self, event: events.MouseMove):
        if self._resizing:
            self._resize_width = max(4, min(60, self._resizing[2] + event.x - self._resizing[1]))
            self.refresh()
            event.stop()
        elif self._dragging:
            position = self.cell_at(event.x, event.y, True)
            if position:
                self.move(*position, extend=True)
            event.stop()

    def on_mouse_up(self, event: events.MouseUp):
        if self._resizing:
            column = self._resizing[0]
            width = self._resize_width
            self._resizing, self._resize_width = None, None
            self.post_message(self.ColumnResized(column, width))
        if self._dragging or self.is_mouse_over:
            self._dragging = False
        self.release_mouse()
        event.stop()

    def on_click(self, event: events.Click):
        if self.app.editing is not None:
            event.stop()
            event.prevent_default()
            return
        if event.button != 1:
            event.stop()
            return
        if event.chain == 2 and self.cell_at(event.x, event.y):
            self.app.begin_edit()
        event.stop()

    def on_mouse_scroll_down(self, event):
        if event.shift:
            self.left = min(MAX_COLUMNS - 1, self.left + 1)
        else:
            self.top = min(MAX_ROWS - 1, self.top + 3)
        self.refresh()
        event.stop()

    def on_mouse_scroll_up(self, event):
        if event.shift:
            self.left = max(self.sheet.freeze_columns, self.left - 1)
        else:
            self.top = max(self.sheet.freeze_rows, self.top - 3)
        self.refresh()
        event.stop()

    def on_paste(self, event: events.Paste):
        self.post_message(self.Pasted(event.text))
        event.stop()

    def on_key(self, event: events.Key):
        if self.screen is not self.app.screen:
            # 모달이 mount되는 동안 이전 grid에 대기 중이던 키를 새 문맥으로 보낸다.
            def deliver():
                if self.app.screen_stack:
                    self.app.post_message(events.Key(event.key, event.character))

            self.app.call_after_refresh(deliver)
            event.stop()
            event.prevent_default()
            return
        # App can already have queued several keys for the old focused widget.
        if self.app.editing is not None:
            self.app.formula_input.post_message(events.Key(event.key, event.character))
            event.stop()
            event.prevent_default()
            return
        key = event.key
        modifiers = set(key.split("+")[:-1])
        direction = key.split("+")[-1]
        if "ctrl" in modifiers and direction in {"up", "down", "left", "right"}:
            self.move(
                *jump_target(self.sheet, self.cursor, direction, self._filtered),
                extend="shift" in modifiers,
            )
            event.stop()
            event.prevent_default()
            return
        if key in {"ctrl+a", "shift+space", "ctrl+space", "ctrl+at"}:
            self.app.run_command(
                "select_all"
                if key == "ctrl+a"
                else "select_row"
                if key == "shift+space"
                else "select_column"
            )
            event.stop()
            event.prevent_default()
            return
        extend = key.startswith("shift+")
        plain = key.removeprefix("shift+")
        row, column = self.cursor
        steps = {
            "up": (-1, 0),
            "down": (1, 0),
            "left": (0, -1),
            "right": (0, 1),
            "pageup": (-max(1, self.size.height - 3), 0),
            "pagedown": (max(1, self.size.height - 3), 0),
            "tab": (0, -1 if extend else 1),
        }
        if plain in steps:
            dr, dc = steps[plain]
            self.advance(dr, dc, extend=extend and plain != "tab")
        elif plain == "home":
            self.move(row, 0, extend)
        elif plain == "end":
            self.move(row, self.sheet.used_range.right, extend)
        elif key == "ctrl+home":
            self.move(0, 0)
        elif key == "ctrl+end":
            region = self.sheet.used_range
            self.move(region.bottom, region.right)
        elif key == "escape":
            self._selection_override = None
            self.anchor = self.cursor
            self.changed()
        elif key in {"f2", "enter"}:
            self.app.begin_edit()
        elif key in {"delete", "backspace"}:
            self.app.run_command("clear")
        elif (
            event.character
            and event.character.isprintable()
            and not any(mod in key for mod in ("ctrl+", "alt+", "meta+"))
        ):
            self.app.begin_edit(event.character)
        else:
            return
        event.stop()
        event.prevent_default()
