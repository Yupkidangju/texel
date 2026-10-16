from __future__ import annotations

import json
import re
import sys
from copy import deepcopy
from pathlib import Path
from uuid import uuid4

from rich.cells import cell_len

from ..addresses import CellRange, address, parse_address
from ..analysis import chart_text, deduplicate, pivot_table, profile_range
from ..demo import demo_workbook
from ..editing import (
    apply_borders,
    clear_formats,
    clear_range,
    delete_sheet,
    fill_range,
    format_range,
    merge_range,
    rename_sheet,
    shift_axis,
    sort_range,
)
from ..exchange import XLSX_NOTICE, export_file, load_file, replace_workbook
from ..formula import function_names
from ..model import Validation, Workbook, display_value
from ..session import ConflictError, Session
from .advanced import ADVANCED_COMMANDS, AdvancedActionsMixin
from .dialogs import Field, FormDialog, TextDialog
from .file_dialog import FileDialog


class ActionsMixin(AdvancedActionsMixin):
    def form(self, command, fields, submit, notice="", browse=None):
        captured_revision = self.session.revision
        captured_path = self.session.store.path

        def guarded_submit(values):
            if command not in {"new", "open", "export", "backup", "find"}:
                if self.session.store.path != captured_path:
                    raise ValueError(
                        "The workbook changed while this form was open; reopen the command"
                    )
                actual = self.session.store.revision
                if actual != captured_revision:
                    raise ConflictError(captured_revision, actual)
            return submit(values)

        self.push_screen(
            FormDialog(command, fields, guarded_submit, self.language, notice, browse),
            lambda _result: self.grid.focus(),
        )

    def show_text(self, command, content):
        self.push_screen(
            TextDialog(command, content, self.language), lambda _result: self.grid.focus()
        )

    def file_form(self, command, submit, path="", saving=False, notice=""):
        captured_revision, captured_path = self.session.revision, self.session.store.path

        def guarded(values):
            if command in {"save", "export", "backup"}:
                actual = self.session.store.revision
                if self.session.store.path != captured_path or actual != captured_revision:
                    raise ConflictError(captured_revision, actual)
            result = submit(values)
            self.last_folder = Path(values["path"]).parent
            return result

        self.push_screen(
            FileDialog(command, guarded, self.last_folder, path, self.language, saving, notice),
            lambda _: self.grid.focus(),
        )

    def data_region(self):
        span = self.grid.selection
        return str(
            self.session.workbook.sheet(self.sheet_index).used_range if span.size == 1 else span
        )

    def switch_workbook(self, session):
        self.session = session
        self.source_path = None
        self.sheet_index = session.workbook.active_sheet
        self.clipboard_data = None
        self.grid.top = self.grid.left = 0
        self.grid.cursor = self.grid.anchor = (0, 0)
        self.refresh_workbook()

    def fresh_path(self, stem="Untitled"):
        directory = self.session.store.path.parent
        return directory / f"{stem}-{uuid4().hex[:8]}.texel"

    def show_import_notice(self):
        suffix = self.source_path.suffix.lower() if self.source_path else ""
        if suffix == ".xlsx":
            self.notify(XLSX_NOTICE, timeout=10)
        elif suffix == ".xls":
            from ..legacy_excel import XLS_NOTICE

            self.notify(XLS_NOTICE, timeout=12)
        elif suffix == ".gsheet":
            from ..google_sheets import GSHEET_NOTICE

            self.notify(GSHEET_NOTICE, timeout=12)

    def dispatch_command(self, command):
        if command in ADVANCED_COMMANDS:
            self.advanced_command(command)
            return
        sheet = self.sheet_index
        span = self.grid.selection
        target = self.session.workbook.sheet(sheet)
        region = str(span)
        row, column = self.grid.cursor
        if command == "new":

            def create(v):
                path = Path(v["path"]).expanduser().resolve()
                if path.exists():
                    raise FileExistsError(self.text("native_exists"))
                if path.suffix.lower() == ".texel":
                    self.switch_workbook(Session(path))
                else:
                    export_file(Workbook(), path)
                    self.switch_workbook(Session(self.fresh_path(path.stem)))
                    self.source_path = path

            self.file_form(command, create, self.fresh_path(), saving=True)
        elif command == "open":

            def open_document(v):
                path = Path(v["path"]).expanduser().resolve()
                imported = load_file(path, v.get("encoding", "auto"))
                if path.suffix.lower() == ".texel":
                    session = Session(path)
                else:
                    session = Session(self.fresh_path(path.stem))
                    session.apply("import file", lambda w: replace_workbook(w, imported))
                self.switch_workbook(session)
                self.source_path = path
                self.show_import_notice()

            self.file_form(command, open_document)
        elif command in {"save", "export"}:

            def save_document(v):
                path = Path(v["path"]).resolve()
                if path == self.session.store.path:
                    self.notify(self.text("saved_notice"))
                    return
                if path.exists() and not v["overwrite"]:
                    raise FileExistsError(self.text("overwrite_required"))
                book = deepcopy(self.session.workbook)
                book.active_sheet = self.sheet_index
                export_file(book, path, self.sheet_index, v["formulas"])
                if command == "save":
                    if path.suffix.lower() == ".texel":
                        self.switch_workbook(Session(path))
                    self.source_path = path
                self.notify(str(path))

            default = (
                self.source_path or self.session.store.path
                if command == "save"
                else (self.last_folder / (self.session.store.path.stem + ".xlsx"))
            )
            if Path(default).suffix.lower() in {".xls", ".gsheet"}:
                default = Path(default).with_suffix(".xlsx")
            self.file_form(command, save_document, default, saving=True, notice=XLSX_NOTICE)
        elif command == "backup":

            def backup(v):
                if Path(v["path"]).suffix.lower() != ".texel":
                    raise ValueError("Backup must use the native .texel extension")
                self.session.store.backup(v["path"])

            self.file_form(
                command,
                backup,
                self.fresh_path("backup"),
                saving=True,
            )
        elif command == "demo":
            session = Session(self.fresh_path("Demo"))
            session.apply("demo", lambda w: replace_workbook(w, demo_workbook()))
            self.switch_workbook(session)
        elif command == "quit":
            self.exit()
        elif command in {"undo", "redo"}:
            getattr(self.session, command)()
            self.refresh_workbook()
        elif command in {"copy", "cut"}:
            self.copy_selection(command == "cut")
        elif command in {"paste", "transpose"}:
            self.paste_clipboard(command == "transpose")
        elif command == "paste_special":
            self.form(
                command,
                [Field("paste_mode", "all", ["all", "values", "formulas", "formats", "transpose"])],
                lambda v: self.paste_clipboard(mode=v["paste_mode"]),
            )
        elif command == "clear":
            self.mutate(command, lambda w: clear_range(w, sheet, region))
        elif command == "clear_all":
            self.mutate(command, lambda w: clear_range(w, sheet, region, True))
        elif command == "clear_formats":
            self.mutate(command, lambda w: clear_formats(w, sheet, region))
        elif command in {"fill_down", "fill_right", "series"}:
            self.mutate(
                command,
                lambda w: fill_range(
                    w,
                    sheet,
                    region,
                    {"fill_down": "down", "fill_right": "right", "series": "series"}[command],
                ),
            )
        elif command == "goto":
            self.address_input.focus()
            self.address_input.select_all()
        elif command in {"freeze", "unfreeze"}:

            def freeze(w):
                w.sheet(sheet).freeze_rows = row if command == "freeze" else 0
                w.sheet(sheet).freeze_columns = column if command == "freeze" else 0

            self.mutate(command, freeze)
        elif command in {"hide_rows", "hide_columns", "unhide"}:

            def hide(w):
                current = w.sheet(sheet)
                if command == "unhide":
                    current.hidden_rows.clear()
                    current.hidden_columns.clear()
                elif command == "hide_rows":
                    if span.height > 10000:
                        raise ValueError("Hide at most 10000 rows")
                    current.hidden_rows.update(range(span.top, span.bottom + 1))
                else:
                    current.hidden_columns.update(range(span.left, span.right + 1))

            self.mutate(command, hide)
            self.grid.move(row, column)
        elif command == "width":

            def resize(v):
                value = int(v["width"])
                if not 4 <= value <= 60:
                    raise ValueError("Column width: 4..60")
                self.mutate(
                    command,
                    lambda w: w.sheet(sheet).column_widths.update(
                        {c: value for c in range(span.left, span.right + 1)}
                    ),
                )

            self.form(command, [Field("width", target.column_widths.get(column, 14))], resize)
        elif command == "row_height":

            def height(v):
                value = int(v["row_height"])
                if not 1 <= value <= 12:
                    raise ValueError("Row height: 1..12 terminal lines")
                self.mutate(
                    command,
                    lambda w: w.sheet(sheet).row_heights.update(
                        {r: value for r in range(span.top, span.bottom + 1)}
                    ),
                )

            self.form(command, [Field("row_height", target.row_heights.get(row, 1))], height)
        elif command == "autofit_rows":
            from rich.text import Text

            from .safe_text import safe_text

            heights = {}
            for r, c in span.coordinates(limit=10000):
                merged = target.merged_range(r, c)
                if merged and (r, c) != (merged.top, merged.left):
                    continue
                cell = target.cell(r, c, False)
                text = safe_text(
                    display_value(self.session.evaluator.value(sheet, r, c)), multiline=True
                )
                width = (
                    sum(
                        target.column_widths.get(col, 14)
                        for col in range(merged.left, merged.right + 1)
                    )
                    if merged
                    else target.column_widths.get(c, 14)
                )
                lines = Text(text).wrap(self.console, max(1, width - 2), overflow="fold")
                heights[r] = min(12, max(heights.get(r, 1), len(lines)))
            self.mutate(command, lambda w: w.sheet(sheet).row_heights.update(heights))
        elif command == "autofit":
            widths = {}
            for c in range(span.left, span.right + 1):
                texts = [
                    display_value(self.session.evaluator.value(sheet, r, c), cell.style)
                    for (r, cc), cell in target.cells.items()
                    if cc == c
                ]
                widths[c] = min(
                    60,
                    max(
                        6,
                        max(
                            (cell_len(value.splitlines()[0]) if value else 0 for value in texts),
                            default=6,
                        )
                        + 2,
                    ),
                )
            self.mutate(command, lambda w: w.sheet(sheet).column_widths.update(widths))
        elif command == "formulas":
            self.grid.show_formulas = not self.grid.show_formulas
            self.grid.refresh()
        elif command == "theme":
            self.palette_index = (self.palette_index + 1) % 3
            self.theme = "textual-light" if self.palette_index == 1 else "textual-dark"
            self.grid.refresh()
        elif command == "language":
            self.language = "en" if self.language == "ko" else "ko"
            from textual.widgets import Button

            for menu in ("file", "edit", "view", "insert", "format", "data", "analysis", "help"):
                self.query_one("#menu-" + menu, Button).label = self.text(menu)
            self.update_status()
        elif command in {"add_sheet", "rename_sheet", "duplicate_sheet"}:

            def change_sheet(v):
                name = v["name"]

                def mutation(w):
                    if command == "rename_sheet":
                        rename_sheet(w, sheet, name)
                        return sheet
                    new = w.add_sheet(name)
                    if command == "duplicate_sheet":
                        w.sheets[new] = deepcopy(w.sheet(sheet))
                        w.sheets[new].name = name
                    return new

                new = self.mutate(command, mutation)
                self.sheet_index = new
                self.grid.cursor = self.grid.anchor = (0, 0)
                self.refresh_workbook()

            name = (
                target.name
                if command == "rename_sheet"
                else f"Sheet{len(self.session.workbook.sheets) + 1}"
            )
            self.form(command, [Field("name", name)], change_sheet)
        elif command == "delete_sheet":

            def remove(v):
                if v["name"] != target.name:
                    raise ValueError("Type the sheet name to delete it")
                self.mutate(command, lambda w: delete_sheet(w, sheet))

            self.form(
                command, [Field("name", target.name)], remove, notice=self.text("confirm_delete")
            )
        elif command in {"insert_rows", "delete_rows", "insert_columns", "delete_columns"}:
            axis = "row" if command.endswith("rows") else "column"
            self.form(
                command,
                [Field("count", span.height if axis == "row" else span.width)],
                lambda v: self.mutate(
                    command,
                    lambda w: shift_axis(
                        w,
                        sheet,
                        axis,
                        span.top if axis == "row" else span.left,
                        int(v["count"]),
                        command.startswith("delete"),
                    ),
                ),
            )
        elif command == "named_range":

            def define(v):
                name = v["name"]
                if not re.fullmatch(r"[^\W\d]\w*", name):
                    raise ValueError("Name must start with a letter or underscore")
                try:
                    parse_address(name)
                except ValueError:
                    pass
                else:
                    raise ValueError("Range name cannot be a cell address")
                selection = str(CellRange.parse(v["range"]))
                self.mutate(
                    command, lambda w: w.named_ranges.update({name: (target.name, selection)})
                )

            self.form(command, [Field("name"), Field("range", region)], define)
        elif command == "names":
            self.show_text(
                command,
                "\n".join(
                    f"{name}  →  {s}!{r}"
                    for name, (s, r) in self.session.workbook.named_ranges.items()
                )
                or "—",
            )
        elif command == "style":
            style = target.cell(row, column, False).style
            fields = [
                Field(
                    "number_format",
                    style.number_format,
                    ["general", "number", "percent", "currency", "date"],
                ),
                Field("decimals", style.decimals),
                Field("align", style.align, ["auto", "left", "center", "right"]),
                Field("bold", style.bold),
                Field("italic", style.italic),
                Field("strike", style.strike),
                Field("wrap", style.wrap),
                Field("vertical_align", style.vertical_align, ["top", "middle", "bottom"]),
                Field("underline", style.underline),
                Field("foreground", style.foreground),
                Field("background", style.background),
            ]

            def styling(v):
                v["decimals"] = int(v["decimals"])
                for key in ("foreground", "background"):
                    if v[key] and not re.fullmatch(r"#[0-9a-fA-F]{6}", v[key]):
                        raise ValueError("Color must be #RRGGBB or blank")
                self.mutate(command, lambda w: format_range(w, sheet, region, **v))

            self.form(command, fields, styling)
        elif command == "borders":
            self.form(
                command,
                [
                    Field(
                        "border_preset",
                        "all",
                        ["all", "outer", "inner", "top", "bottom", "left", "right", "none"],
                    ),
                    Field(
                        "border_style",
                        "thin",
                        ["thin", "medium", "thick", "double", "dashed", "dotted"],
                    ),
                    Field("border_color", ""),
                ],
                lambda v: self.mutate(
                    command,
                    lambda w: apply_borders(
                        w, sheet, region, v["border_preset"], v["border_style"], v["border_color"]
                    ),
                ),
            )
        elif command in {"bold", "underline", "italic", "strike", "wrap"}:
            value = not getattr(target.cell(row, column, False).style, command)
            self.mutate(command, lambda w: format_range(w, sheet, region, **{command: value}))
        elif command == "note":
            self.form(
                command,
                [Field("note", target.cell(row, column, False).note)],
                lambda v: self.mutate(
                    command, lambda w: setattr(w.sheet(sheet).cell(row, column), "note", v["note"])
                ),
            )
        elif command in {"merge", "merge_center", "unmerge"}:

            def merging(contents="strict"):
                def operation(w):
                    merge_range(w, sheet, region, command == "unmerge", contents)
                    if command == "merge_center":
                        format_range(w, sheet, region, align="center", vertical_align="middle")

                self.mutate(command, operation)
                self.grid.move(span.top, span.left)

            populated = any(
                target.cell(r, c, False).raw or target.cell(r, c, False).note
                for r, c in span.coordinates(limit=10000)
                if (r, c) != (span.top, span.left)
            )
            if command != "unmerge" and populated:
                self.form(
                    command,
                    [Field("merge_contents", "combine", ["combine", "first"])],
                    lambda v: merging(v["merge_contents"]),
                    notice=self.text("merge_notice"),
                )
            else:
                merging()
        elif command in {"validation", "clear_validation"}:
            if command == "clear_validation":
                self.mutate(
                    command,
                    lambda w: [
                        setattr(w.sheet(sheet).cell(r, c), "validation", None)
                        for r, c in span.coordinates(limit=10000)
                    ],
                )
            else:

                def rule(v):
                    validation = Validation(
                        v["kind"],
                        [x.strip() for x in v["choices"].split(",")],
                        float(v["minimum"]) if v["minimum"] else None,
                        float(v["maximum"]) if v["maximum"] else None,
                        v["allow_blank"],
                    )
                    self.mutate(
                        command,
                        lambda w: [
                            setattr(w.sheet(sheet).cell(r, c), "validation", deepcopy(validation))
                            for r, c in span.coordinates(limit=10000)
                        ],
                    )

                self.form(
                    command,
                    [
                        Field("kind", "number", ["number", "list"]),
                        Field("choices"),
                        Field("minimum"),
                        Field("maximum"),
                        Field("allow_blank", True),
                    ],
                    rule,
                )
        elif command in {"conditional", "clear_conditional"}:
            if command == "clear_conditional":
                self.mutate(command, lambda w: w.sheet(sheet).conditional_rules.clear())
            else:

                def conditional(v):
                    if not re.fullmatch(r"#[0-9a-fA-F]{6}", v["background"]):
                        raise ValueError("Color must be #RRGGBB")
                    rule = {
                        "range": str(CellRange.parse(v["range"])),
                        "operator": v["operator"],
                        "value": float(v["value"]),
                        "color": v["background"],
                    }
                    self.mutate(command, lambda w: w.sheet(sheet).conditional_rules.append(rule))

                self.form(
                    command,
                    [
                        Field("range", region),
                        Field(
                            "operator",
                            "greaterThan",
                            ["greaterThan", "lessThan", "equal", "greaterThanOrEqual"],
                        ),
                        Field("value", "0"),
                        Field("background", "#0f766e"),
                    ],
                    conditional,
                )
        elif command == "lock":
            value = not target.cell(row, column, False).locked
            self.mutate(
                command,
                lambda w: [
                    setattr(w.sheet(sheet).cell(r, c), "locked", value)
                    for r, c in span.coordinates(limit=10000)
                ],
            )
        elif command == "protect":
            self.mutate(
                command, lambda w: setattr(w.sheet(sheet), "protected", not target.protected)
            )
        elif command == "sort":
            self.form(
                command,
                [
                    Field("range", self.data_region()),
                    Field("column", "1"),
                    Field("descending", False),
                    Field("header", True),
                ],
                lambda v: self.mutate(
                    command,
                    lambda w: sort_range(
                        w, sheet, v["range"], int(v["column"]) - 1, v["descending"], v["header"]
                    ),
                ),
            )
        elif command == "filter":

            def filter_data(v):
                selected = CellRange.parse(v["range"])
                c = int(v["column"]) - 1
                if not 0 <= c < selected.width or selected.height > 200000:
                    raise ValueError("Filter column/range outside limits")
                spec = {
                    "range": str(selected),
                    "column": c,
                    "criterion": v["criterion"],
                    "header": v["header"],
                }
                self.mutate(command, lambda w: setattr(w.sheet(sheet), "filter_spec", spec))

            self.form(
                command,
                [
                    Field("range", self.data_region()),
                    Field("column", "1"),
                    Field("criterion"),
                    Field("header", True),
                ],
                filter_data,
            )
        elif command == "clear_filter":
            self.mutate(command, lambda w: setattr(w.sheet(sheet), "filter_spec", None))
        elif command == "deduplicate":
            self.form(
                command,
                [Field("range", self.data_region()), Field("header", True)],
                lambda v: self.mutate(
                    command, lambda w: deduplicate(w, sheet, v["range"], v["header"])
                ),
            )
        elif command == "profile":
            report = profile_range(self.session.workbook, sheet, self.data_region())
            lines = [f"{report['range']}  ·  {report['rows']} rows", ""]
            for item in report["columns"]:
                lines.extend(
                    [
                        f"{item['name']}",
                        f"  count={item['count']}  missing={item['missing']}  unique={item['unique']}  errors={item['errors']}",
                        f"  sum={display_value(item['sum'])}  mean={display_value(item['mean'])}  median={display_value(item['median'])}",
                        f"  min={display_value(item['min'])}  max={display_value(item['max'])}  std={display_value(item['std'])}",
                        "  " + ", ".join(f"{v['value']} ({v['count']})" for v in item["top"]),
                        "",
                    ]
                )
            self.show_text(command, "\n".join(lines))
        elif command == "pivot":

            def pivot(v):
                keys = [int(c.strip()) - 1 for c in v["keys"].split(",")]
                index = self.mutate(
                    command,
                    lambda w: pivot_table(
                        w,
                        sheet,
                        v["range"],
                        keys,
                        int(v["value_column"]) - 1,
                        v["aggregate"],
                        v["name"],
                        v["header"],
                    ),
                )
                self.sheet_index = index
                self.grid.cursor = self.grid.anchor = (0, 0)
                self.refresh_workbook()

            self.form(
                command,
                [
                    Field("range", self.data_region()),
                    Field("keys", "1"),
                    Field("value_column", "2"),
                    Field("aggregate", "sum", ["sum", "mean", "count", "min", "max"]),
                    Field("name", f"Pivot{len(self.session.workbook.sheets)}"),
                    Field("header", True),
                ],
                pivot,
            )
        elif command == "chart":

            def chart(v):
                content = chart_text(
                    self.session.workbook, sheet, v["range"], v["kind"], header=v["header"]
                )
                self.mutate(
                    command,
                    lambda w: w.sheet(sheet).charts.append(
                        {
                            "range": str(CellRange.parse(v["range"])),
                            "kind": v["kind"],
                            "title": target.name,
                        }
                    ),
                )
                self.call_later(self.show_text, command, content)

            self.form(
                command,
                [
                    Field("range", self.data_region()),
                    Field("kind", "bar", ["bar", "line"]),
                    Field("header", True),
                ],
                chart,
            )
        elif command == "functions":
            self.show_text(
                command,
                "\n".join(function_names())
                + '\n\n=SUM(A1:A10)\n=IF(B2>0,B2,0)\n=SUMIF(A2:A20,"영업",D2:D20)\n=VLOOKUP(A2,Sheet2!A1:D10,3,FALSE)',
            )
        elif command == "history":
            records = self.session.store.history()
            self.show_text(
                command,
                "\n".join(
                    f"{'●' if r['applied'] else '○'} {r['id']:>4}  {r['created']}  {r['source']}  {r['label']}"
                    for r in records
                )
                or self.text("empty_history"),
            )
        elif command == "inspect":
            cell = target.cell(row, column, False)
            value = self.session.evaluator.value(sheet, row, column)
            self.show_text(
                command,
                f"{target.name}!{address(row, column)}\n\nRAW\n{cell.raw}\n\nVALUE\n{display_value(value)}\n\nNOTE\n{cell.note}\n\n{json.dumps(cell.to_dict(), ensure_ascii=False, indent=2)}",
            )
        elif command == "mcp_info":
            config = {
                "mcpServers": {
                    "texel": {
                        "command": sys.executable,
                        "args": [
                            "-m",
                            "texel",
                            "mcp",
                            "--workbook",
                            str(self.session.store.path),
                            "--root",
                            str(self.session.store.path.parent),
                        ],
                        "cwd": str(Path(__file__).resolve().parents[2]),
                    }
                }
            }
            self.show_text(
                command,
                json.dumps(config, ensure_ascii=False, indent=2)
                + "\n\nLocal stdio · no API key required · expected_revision required for mutations.",
            )
        elif command == "help":
            from .commands import COMMANDS

            commands = "\n".join(f"{self.text(c.key):<28} {c.shortcut}" for c in COMMANDS)
            self.show_text(
                command,
                "TEXEL\n\n"
                + self.text("footer_hint")
                + "\n\n"
                + self.text("close_hint")
                + "\n\nMouse: click / double-click / drag / Shift+click / wheel / column-edge resize.\nArrow keys, Shift+arrow, PageUp/Down, Home/End, Ctrl+Home/End, Tab.\n\n"
                + commands
                + "\n\n"
                + XLSX_NOTICE,
            )
        else:
            raise ValueError(f"Unknown command: {command}")
