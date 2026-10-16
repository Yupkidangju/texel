from __future__ import annotations

import csv
import io
import sqlite3
from copy import deepcopy
from pathlib import Path

from rich.text import Text
from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.suggester import Suggester
from textual.widgets import Button, Input, Static, Tab, Tabs

from ..addresses import CellRange, address
from ..analysis import selection_summary
from ..clipboard import read_clipboard, write_clipboard
from ..editing import set_matrix
from ..formula import function_names, translate_formula
from ..i18n import tr
from ..model import display_value
from ..navigation import cycle_reference
from ..session import ConflictError, Session
from ..values import Error, exact_text
from .actions import ActionsMixin
from .commands import COMMANDS
from .context_menu import ContextMenu
from .dialogs import CommandDialog
from .grid import SpreadsheetGrid
from .safe_text import SafeInput, safe_text

PALETTES = [
    {
        "background": "#0b1220",
        "surface": "#101b2d",
        "header": "#16233a",
        "text": "#e2e8f0",
        "muted": "#94a3b8",
        "accent": "#2dd4bf",
        "grid": "#26364e",
        "selection": "#164e63",
        "selection_text": "#ecfeff",
        "cursor": "#2dd4bf",
        "cursor_text": "#052e2b",
        "error": "#fb7185",
    },
    {
        "background": "#f8fafc",
        "surface": "#ffffff",
        "header": "#e2e8f0",
        "text": "#0f172a",
        "muted": "#475569",
        "accent": "#0f766e",
        "grid": "#cbd5e1",
        "selection": "#ccfbf1",
        "selection_text": "#134e4a",
        "cursor": "#0f766e",
        "cursor_text": "#ffffff",
        "error": "#be123c",
    },
    {
        "background": "#000000",
        "surface": "#000000",
        "header": "#171717",
        "text": "#ffffff",
        "muted": "#ffffff",
        "accent": "#ffff00",
        "grid": "#ffffff",
        "selection": "#000080",
        "selection_text": "#ffffff",
        "cursor": "#ffff00",
        "cursor_text": "#000000",
        "error": "#ff8080",
    },
]


class FormulaSuggester(Suggester):
    def __init__(self):
        super().__init__(case_sensitive=False)

    async def get_suggestion(self, value):
        if value.startswith("=") and value[1:].isalpha():
            name = next(
                (name for name in function_names() if name.startswith(value[1:].upper())), None
            )
            if name:
                return "=" + name + "("
        return None


class FormulaInput(SafeInput):
    def on_focus(self):
        if self.screen.focused is not self:
            return
        if self.app.editing is None:
            grid = self.app.grid
            self.app.editing = (self.app.sheet_index, *grid.cursor, self.app.session.revision)
            self.app.edit_selection = grid.selection
            self.app.update_status()

    def on_key(self, event):
        if event.key == "f4":
            selection = self.selection
            value, cursor = cycle_reference(
                self.value, self.cursor_position, selection.start, selection.end
            )
            self.value, self.cursor_position = value, cursor
        elif event.key == "enter":
            self.app.commit_edit((1, 0))
        elif event.key == "escape":
            self.app.cancel_edit()
        elif event.key in {"tab", "shift+tab"}:
            self.app.commit_edit((0, -1 if event.key == "shift+tab" else 1))
        elif event.key == "ctrl+enter":
            self.app.commit_edit((1, 0), fill=True)
        elif self.app.editing is None and event.character and event.character.isprintable():
            self.app.begin_edit(event.character)
        else:
            return
        event.stop()
        event.prevent_default()


class TexelApp(ActionsMixin, App):
    TITLE = "Texel"
    ENABLE_COMMAND_PALETTE = False
    CSS = """
    Screen#_default { background: $background; }
    #topbar { height: 3; background: $panel; padding: 0 1; }
    #brand { width: 12; content-align: left middle; text-style: bold; color: $accent; }
    #file-status { width: 1fr; content-align: left middle; }
    #topbar Button { min-width: 8; width: auto; border: none; height: 3; }
    #menubar { height: 3; background: $surface; }
    #menubar Button { min-width: 8; width: 1fr; height: 3; border: none; }
    #formulabar { height: 3; }
    #address { width: 17; }
    #fx { width: 4; content-align: center middle; color: $accent; text-style: bold; }
    #formula { width: 1fr; }
    #commit { width: 6; min-width: 6; }
    #sheetsbar { height: 3; background: $surface; }
    #sheet-tabs { width: 1fr; }
    #add-sheet { width: 5; min-width: 5; border: none; }
    #status { height: 1; padding: 0 1; background: $panel; color: $text-muted; }
    #hints { height: 1; padding: 0 1; background: $surface; color: $accent; }
    """
    BINDINGS = [
        Binding("shift+f10", "context_menu", "Context menu"),
        Binding("menu", "context_menu", "Context menu"),
        Binding("ctrl+p", "commands", "Commands", priority=True),
        Binding("f10", "commands", "Menu"),
        *[
            Binding(key, f"command('{command}')", command, show=False)
            for key, command in {
                "ctrl+n": "new",
                "ctrl+o": "open",
                "ctrl+s": "save",
                "ctrl+shift+s": "export",
                "ctrl+q": "quit",
                "ctrl+z": "undo",
                "ctrl+y": "redo",
                "ctrl+c": "copy",
                "ctrl+x": "cut",
                "ctrl+v": "paste",
                "ctrl+d": "fill_down",
                "ctrl+r": "fill_right",
                "ctrl+f": "find",
                "ctrl+h": "replace",
                "ctrl+g": "goto",
                "ctrl+b": "bold",
                "ctrl+i": "italic",
                "f1": "help",
                "f6": "theme",
                "ctrl+grave_accent": "formulas",
            }.items()
        ],
    ]

    def __init__(self, workbook, language="ko", source_path=None):
        super().__init__()
        self.session = Session(workbook)
        self.language = language
        self.sheet_index = self.session.workbook.active_sheet
        self.palette_index = 0
        self.editing = None
        self.edit_selection = None
        self.clipboard_data = None
        self._tabs_signature = None
        self._pending_revision = None
        self.source_path = Path(source_path).resolve() if source_path is not None else None
        self.last_folder = (self.source_path or self.session.store.path).parent
        self.theme = "textual-dark"

    @property
    def palette(self):
        return PALETTES[self.palette_index]

    def text(self, key):
        return tr(key, self.language)

    def notify(self, message, **kwargs):
        if "title" in kwargs:
            kwargs["title"] = safe_text(kwargs["title"])
        return super().notify(safe_text(message, multiline=True), **kwargs)

    def compose(self) -> ComposeResult:
        with Horizontal(id="topbar"):
            yield Static("▦ TEXEL", id="brand")
            yield Static("", id="file-status")
            yield Button("◐", id="theme-button", tooltip=self.text("theme"))
            yield Button("KO / EN", id="language-button")
        with Horizontal(id="menubar"):
            for menu in ("file", "edit", "view", "insert", "format", "data", "analysis", "help"):
                yield Button(self.text(menu), id="menu-" + menu)
        with Horizontal(id="formulabar"):
            yield SafeInput("A1", id="address", tooltip=self.text("goto"))
            yield Static("fx", id="fx")
            yield FormulaInput(id="formula", select_on_focus=False, suggester=FormulaSuggester())
            yield Button("↵", id="commit", variant="primary")
        yield SpreadsheetGrid(id="grid")
        with Horizontal(id="sheetsbar"):
            yield Tabs(id="sheet-tabs")
            yield Button("+", id="add-sheet", tooltip=self.text("add_sheet"))
        yield Static("", id="status")
        yield Static(self.text("footer_hint"), id="hints")

    def on_mount(self):
        self.grid = self.query_one("#grid", SpreadsheetGrid)
        self.formula_input = self.query_one("#formula", FormulaInput)
        self.address_input = self.query_one("#address", Input)
        self.file_status = self.query_one("#file-status", Static)
        self.status_line = self.query_one("#status", Static)
        self.hints = self.query_one("#hints", Static)
        self.tabs = self.query_one("#sheet-tabs", Tabs)
        self.refresh_workbook()
        self.grid.focus()
        self.set_interval(0.75, self.poll_external)
        self.show_import_notice()

    def refresh_workbook(self):
        self.sheet_index = min(self.sheet_index, len(self.session.workbook.sheets) - 1)
        self.grid.update_model()
        self.update_selection()
        signature = tuple(sheet.name for sheet in self.session.workbook.sheets)
        if signature != self._tabs_signature:
            self._tabs_signature = signature
            self.call_later(self.refresh_tabs)
        self.update_status()

    async def refresh_tabs(self):
        await self.tabs.clear()
        for i, sheet in enumerate(self.session.workbook.sheets):
            await self.tabs.add_tab(Tab(Text(sheet.name), id=f"sheet-{i}"))
        self.tabs.active = f"sheet-{self.sheet_index}"

    def update_selection(self):
        if self.editing is None:
            self.address_input.value = str(self.grid.selection)
            self.formula_input.value = (
                self.session.workbook.sheet(self.sheet_index)
                .cell(
                    *self.session.workbook.sheet(self.sheet_index).merge_anchor(*self.grid.cursor),
                    False,
                )
                .raw
            )
        self.update_status()

    def update_status(self):
        if not hasattr(self, "grid"):
            return
        summary = selection_summary(self.session.evaluator, self.sheet_index, self.grid.selection)
        state = (
            self.text("external_change")
            if self._pending_revision
            else self.text("editing")
            if self.editing
            else self.text("saved")
        )
        self.file_status.update(
            Text(f"{self.session.store.path.name}   ·   rev {self.session.revision}   ·   {state}")
        )
        self.status_line.update(
            Text(
                f"{self.grid.selection}   count {summary['count']:,}   sum {display_value(summary['sum'])}   avg {display_value(summary['mean'])}   |   {state}"
            )
        )
        self.hints.update(
            self.text("close_hint")
            if self.editing
            else self.text("small_screen")
            if self.size.width < 80
            else self.text("footer_hint")
        )

    @on(SpreadsheetGrid.SelectionChanged)
    def selection_changed(self):
        self.update_selection()

    @on(SpreadsheetGrid.StartEdit)
    def start_edit_message(self, event):
        self.begin_edit(event.replacement)

    def begin_edit(self, replacement=None):
        anchor = self.session.workbook.sheet(self.sheet_index).merge_anchor(*self.grid.cursor)
        self.editing = (self.sheet_index, *anchor, self.session.revision)
        self.edit_selection = self.grid.selection
        raw = self.session.workbook.sheet(self.sheet_index).cell(*anchor, False).raw
        self.formula_input.value = raw if replacement is None else replacement
        self.formula_input.screen.set_focus(self.formula_input, scroll_visible=False)
        self.formula_input.cursor_position = len(self.formula_input.value)
        self.update_status()

    @on(Input.Submitted, "#formula")
    def submitted_formula(self):
        self.commit_edit((1, 0))

    def commit_edit(self, movement=None, fill=False):
        if self.editing is None:
            return True
        sheet, row, column, revision = self.editing
        raw = self.formula_input.value

        def edit(book):
            if fill:
                for r, c in self.edit_selection.coordinates(limit=10000):
                    book.sheet(sheet).set_raw(r, c, translate_formula(raw, r - row, c - column))
            else:
                set_matrix(book, sheet, address(row, column), [[raw]])

        try:
            self.session.apply("edit cells", edit, revision)
        except ConflictError:
            self.session.reload()
            self._pending_revision = self.session.revision
            self.refresh_workbook()
            self.notify(self.text("draft_conflict"), severity="error", timeout=8)
            return False
        except (ValueError, OSError, sqlite3.DatabaseError) as exc:
            self.notify(str(exc), title=self.text("error"), severity="error", timeout=6)
            return False
        self.editing = self.edit_selection = None
        self._pending_revision = None
        self.refresh_workbook()
        self.grid.screen.set_focus(self.grid, scroll_visible=False)
        if movement:
            self.grid.advance(*movement, origin=(row, column))
        return True

    def cancel_edit(self):
        self.editing = self.edit_selection = None
        self._pending_revision = None
        self.session.sync()
        self.refresh_workbook()
        self.grid.screen.set_focus(self.grid, scroll_visible=False)

    @on(Input.Submitted, "#address")
    def address_submitted(self, event):
        try:
            span = CellRange.parse(event.value)
            if self.editing and not self.commit_edit():
                return
            self.grid.select_range(span)
            self.grid.focus()
        except ValueError as exc:
            self.notify(str(exc), severity="error")

    @on(SpreadsheetGrid.ColumnResized)
    def resize_column(self, event):
        self.mutate(
            "resize column",
            lambda w: w.sheet(self.sheet_index).column_widths.update({event.column: event.width}),
        )

    @on(SpreadsheetGrid.Pasted)
    def pasted(self, event):
        self.paste_text(event.text)

    @on(Tabs.TabActivated)
    def activated_sheet(self, event):
        if not event.tab.id or not event.tab.id.startswith("sheet-"):
            return
        new = int(event.tab.id.split("-")[-1])
        if new != self.sheet_index and new < len(self.session.workbook.sheets):
            if self.editing and not self.commit_edit():
                self.tabs.active = f"sheet-{self.sheet_index}"
                return
            self.sheet_index = new
            self.grid.top = self.grid.left = 0
            self.grid.move(0, 0)
            self.refresh_workbook()

    @on(Button.Pressed)
    def button_pressed(self, event):
        key = event.button.id or ""
        if key.startswith("menu-"):
            self.push_screen(
                CommandDialog([c for c in COMMANDS if c.menu == key[5:]], self.language, key[5:]),
                self.menu_result,
            )
        elif key == "commit":
            self.commit_edit((1, 0))
        elif key == "add-sheet":
            self.run_command("add_sheet")
        elif key == "theme-button":
            self.run_command("theme")
        elif key == "language-button":
            self.run_command("language")

    def menu_result(self, result):
        self.grid.focus()
        if result:
            self.run_command(result)

    def action_commands(self):
        self.push_screen(CommandDialog(COMMANDS, self.language), self.menu_result)

    def action_command(self, command):
        self.run_command(command)

    def open_context_menu(self, x, y, context="cell"):
        if self.editing and not self.commit_edit():
            return
        common = [
            "copy",
            "cut",
            "paste",
            "paste_special",
            "style",
            "borders",
            "merge_center",
            "merge",
            "unmerge",
            "clear",
            "clear_formats",
            "clear_all",
            "bold",
            "italic",
            "underline",
            "strike",
            "wrap",
            "note",
            "validation",
            "lock",
            "protect",
            "sort",
            "filter",
            "clear_filter",
            "fill_down",
            "fill_right",
        ]
        structural = [
            "insert_rows",
            "delete_rows",
            "insert_columns",
            "delete_columns",
            "width",
            "autofit",
            "row_height",
            "autofit_rows",
            "hide_rows",
            "hide_columns",
            "unhide",
            "freeze",
            "unfreeze",
        ]
        keys = (
            structural[:2] + common + structural[4:]
            if context == "row"
            else structural[2:4] + common + structural[4:]
            if context == "column"
            else common + structural
        )
        catalog = {c.key: c for c in COMMANDS}
        self.push_screen(
            ContextMenu([catalog[key] for key in keys], x, y, self.language), self.menu_result
        )

    def action_context_menu(self):
        position = next(
            (x for c, x, _ in self.grid.visible_columns() if c == self.grid.cursor[1]), 9
        )
        row_y = next(
            (
                i + 1
                for i, slot in enumerate(self.grid.row_slots())
                if slot.row == self.grid.cursor[0] and slot.kind == "content"
            ),
            1,
        )
        self.open_context_menu(self.grid.region.x + position, self.grid.region.y + row_y)

    def run_command(self, command):
        if self.editing and command not in {"help", "functions", "inspect", "theme", "language"}:
            if not self.commit_edit():
                return
        try:
            self.dispatch_command(command)
        except (ValueError, OSError, TypeError, ArithmeticError, sqlite3.DatabaseError) as exc:
            self.notify(str(exc), title=self.text("error"), severity="error", timeout=6)

    def mutate(self, label, mutation):
        result = self.session.apply(label, mutation)
        self.refresh_workbook()
        return result

    def poll_external(self):
        try:
            actual = self.session.store.revision
            if actual != self.session.revision:
                if self.editing:
                    self._pending_revision = actual
                    self.update_status()
                else:
                    self.session.reload()
                    self._pending_revision = None
                    self.refresh_workbook()
        except (OSError, ValueError, sqlite3.DatabaseError) as exc:
            self.notify(str(exc), severity="error")

    def copy_selection(self, cut=False):
        span = self.grid.selection
        span.coordinates(limit=10000)
        target = self.session.workbook.sheet(self.sheet_index)
        cells = [
            [deepcopy(target.cell(r, c, False)) for c in range(span.left, span.right + 1)]
            for r in range(span.top, span.bottom + 1)
        ]
        stream = io.StringIO(newline="")
        writer = csv.writer(stream, delimiter="\t", lineterminator="\n")
        for r in range(span.top, span.bottom + 1):
            writer.writerow(
                [
                    exact_text(self.session.evaluator.value(self.sheet_index, r, c))
                    for c in range(span.left, span.right + 1)
                ]
            )
        content = stream.getvalue().rstrip("\n")
        self.clipboard_data = {
            "text": content,
            "cells": cells,
            "span": span,
            "sheet": self.sheet_index,
            "cut": cut,
            "revision": self.session.revision,
            "values": [
                [
                    self.session.evaluator.value(self.sheet_index, r, c)
                    for c in range(span.left, span.right + 1)
                ]
                for r in range(span.top, span.bottom + 1)
            ],
            "row_heights": {
                r: target.row_heights.get(r, 1) for r in range(span.top, span.bottom + 1)
            },
            "merges": [
                m
                for m in target.merges
                if span.contains(CellRange.parse(m).top, CellRange.parse(m).left)
                and span.contains(CellRange.parse(m).bottom, CellRange.parse(m).right)
            ],
        }
        if not self.is_headless:
            if not write_clipboard(content):
                self.copy_to_clipboard(content)
        self.notify(self.text("cut_ready" if cut else "copied"))

    def paste_text(self, content, transpose=False):
        rows = list(csv.reader(io.StringIO(content, newline=""), delimiter="\t"))
        if transpose and rows:
            width = max(map(len, rows))
            rows = [[row[c] if c < len(row) else "" for row in rows] for c in range(width)]
        self.mutate(
            "paste", lambda w: set_matrix(w, self.sheet_index, address(*self.grid.cursor), rows)
        )

    def paste_clipboard(self, transpose=False, mode="all"):
        if mode not in {"all", "values", "formulas", "formats", "transpose"}:
            raise ValueError("Unknown paste mode")
        transpose = transpose or mode == "transpose"
        content = None if self.is_headless else read_clipboard()
        copied = self.clipboard_data
        if copied and (content is None or content == copied["text"]):
            r0, c0 = self.grid.cursor

            def paste(book):
                if copied["cut"]:
                    if mode not in {"all", "transpose"}:
                        raise ValueError(
                            "Cut selection supports complete move or transpose; use Copy for paste special"
                        )
                    if (
                        copied["revision"] != self.session.revision
                        or copied["sheet"] != self.sheet_index
                    ):
                        raise ValueError("Cut source changed; copy it again before moving")
                    from ..editing import copy_range

                    copy_range(
                        book,
                        self.sheet_index,
                        str(copied["span"]),
                        address(r0, c0),
                        transpose,
                        True,
                    )
                    return
                target = book.sheet(self.sheet_index)
                height, width = len(copied["cells"]), max(map(len, copied["cells"]), default=0)
                destination = CellRange(
                    r0,
                    c0,
                    r0 + (width if transpose else height) - 1,
                    c0 + (height if transpose else width) - 1,
                )
                if mode in {"all", "transpose"}:
                    for merge in list(target.merges):
                        span = CellRange.parse(merge)
                        if not (
                            span.bottom < destination.top
                            or span.top > destination.bottom
                            or span.right < destination.left
                            or span.left > destination.right
                        ):
                            if not (
                                destination.contains(span.top, span.left)
                                and destination.contains(span.bottom, span.right)
                            ):
                                raise ValueError(
                                    "Paste must cover the complete destination merged region"
                                )
                            target.merges.remove(merge)
                for dr, row in enumerate(copied["cells"]):
                    for dc, original in enumerate(row):
                        rr, cc = r0 + (dc if transpose else dr), c0 + (dr if transpose else dc)
                        cell = deepcopy(original)
                        cell.raw = translate_formula(
                            cell.raw, rr - copied["span"].top - dr, cc - copied["span"].left - dc
                        )
                        address(rr, cc)
                        if mode == "formats":
                            target.cell(rr, cc).style = deepcopy(cell.style)
                        elif mode == "values":
                            value = copied["values"][dr][dc]
                            target.set_raw(
                                rr,
                                cc,
                                "'" + value
                                if isinstance(value, str)
                                else "=" + value.code
                                if isinstance(value, Error)
                                else exact_text(value),
                            )
                        elif mode == "formulas":
                            target.set_raw(rr, cc, cell.raw)
                        else:
                            target.cells[(rr, cc)] = cell
                if mode in {"all", "transpose"}:
                    for raw in copied["merges"]:
                        span = CellRange.parse(raw)
                        origin = copied["span"]
                        translated = CellRange(
                            r0 + (span.left - origin.left if transpose else span.top - origin.top),
                            c0 + (span.top - origin.top if transpose else span.left - origin.left),
                            r0
                            + (span.right - origin.left if transpose else span.bottom - origin.top),
                            c0
                            + (span.bottom - origin.top if transpose else span.right - origin.left),
                        )
                        target.merges.append(str(translated))
                    for rr in range(destination.top, destination.bottom + 1):
                        heights = copied["row_heights"]
                        target.row_heights[rr] = (
                            max(heights.values())
                            if transpose
                            else heights[copied["span"].top + rr - r0]
                        )

            self.mutate("paste cells", paste)
            if copied["cut"]:
                self.clipboard_data = None
        elif content:
            if mode == "formats":
                raise ValueError("Copy a range in Texel to paste cell formatting")
            self.paste_text(content, transpose)
        else:
            self.notify(self.text("clipboard_empty"), severity="warning")
