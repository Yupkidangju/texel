import json
import sqlite3
import sys
from copy import deepcopy
from unittest.mock import patch

import pytest
from mcp import Client, StdioServerParameters
from textual import events
from textual.widgets import Input, OptionList

from texel.__main__ import main
from texel.addresses import CellRange
from texel.editing import (
    apply_borders,
    delete_sheet,
    fill_range,
    merge_range,
    rename_sheet,
    set_matrix,
)
from texel.exchange import export_file, load_file
from texel.model import Validation
from texel.session import Session
from texel.ui.app import TexelApp


@pytest.mark.parametrize(
    "seeds,expected",
    [
        (
            ["9007199254740993", "9007199254740994"],
            [9007199254740993, 9007199254740994, 9007199254740995],
        ),
        (
            ["-9007199254740993", "-9007199254740994"],
            [-9007199254740993, -9007199254740994, -9007199254740995],
        ),
        (
            ["0.123456789012345", "0.223456789012345"],
            [0.123456789012345, 0.223456789012345, 0.323456789012345],
        ),
        (["=6*7"], [42, 43, 44]),
    ],
)
def test_series_seeds_persistence_csv_and_history(tmp_path, seeds, expected):
    path = tmp_path / "series.texel"
    s = Session(path)
    s.apply("seed", lambda w: set_matrix(w, 0, "A1", [[v] for v in seeds]))
    s.apply("series", lambda w: fill_range(w, 0, "A1:A3", "series"))
    assert [s.workbook.sheet().cell(r, 0).raw for r in range(len(seeds))] == seeds
    assert [Session(path).evaluator.value(0, r, 0) for r in range(3)] == pytest.approx(expected)
    export_file(s.workbook, tmp_path / "series.csv")
    assert (tmp_path / "series.csv").read_text(encoding="utf-8-sig").splitlines()[-1] == str(
        expected[-1]
    )
    assert s.undo()
    assert s.workbook.sheet().cell(2, 0, False).raw == ""
    assert s.redo()
    assert [s.evaluator.value(0, r, 0) for r in range(3)] == expected


@pytest.mark.parametrize("seed", ["TRUE", "text", "2026-10-11", "=1/0"])
def test_series_rejects_non_numeric_seed_atomically(tmp_path, seed):
    s = Session(tmp_path / "seed.texel")
    s.apply("seed", lambda w: set_matrix(w, 0, "A1", [[seed]]))
    before = s.workbook.to_dict(), s.revision
    with pytest.raises(ValueError):
        s.apply("series", lambda w: fill_range(w, 0, "A1:A3", "series"))
    assert (s.workbook.to_dict(), s.revision) == before


@pytest.mark.parametrize("kind", ["zero", "empty_db", "other_db"])
def test_native_invalid_read_is_non_mutating(tmp_path, kind):
    path = tmp_path / "invalid.texel"
    if kind == "zero":
        path.write_bytes(b"")
    else:
        with sqlite3.connect(path) as db:
            if kind == "other_db":
                db.execute("CREATE TABLE other(value)")
    before = path.read_bytes()
    with pytest.raises(ValueError):
        load_file(path)
    with pytest.raises(ValueError):
        Session(path)
    assert path.read_bytes() == before
    assert not path.with_name(path.name + "-wal").exists()


@pytest.mark.parametrize(
    "field,value",
    [
        ("filter_spec", {"range": "NOPE", "column": 0, "criterion": ">0"}),
        ("filter_spec", {"range": "A1:A3", "column": 3, "criterion": ">0"}),
        ("conditional_rules", [{"range": "NOPE", "value": 1}]),
        ("conditional_rules", [{"range": "A1", "value": 1, "color": "invalid"}]),
        ("charts", [{"range": "NOPE", "kind": "bar"}]),
        ("hidden_rows", [-1]),
        ("hidden_columns", ["bad"]),
        ("column_widths", {"0": "bad"}),
        ("row_heights", {"0": 999}),
    ],
)
async def test_native_metadata_failure_preserves_ui_and_input(tmp_path, field, value):
    path = tmp_path / "bad.texel"
    s = Session(path)
    with s.store.connect() as db:
        data = json.loads(db.execute("SELECT metadata FROM texel_state").fetchone()[0])
        data["sheets"][0][field] = value
        db.execute("UPDATE texel_state SET metadata=?", (json.dumps(data),))
    before_bytes = path.read_bytes()
    app = TexelApp(tmp_path / "original.texel")
    app.session.apply("seed", lambda w: set_matrix(w, 0, "A1", [["original"]]))
    before = app.session
    async with app.run_test(size=(80, 24)) as p:
        await p.press("ctrl+o")
        await p.press(*str(path), "enter")
        assert app.session is before
        assert app.session.revision == 1
        assert app.session.evaluator.value(0, 0, 0) == "original"
        assert app.screen.query_one("#field-path", Input).value == str(path)
        assert type(app.screen).__name__ == "FileDialog"
    assert path.read_bytes() == before_bytes


@pytest.mark.parametrize("position", [0, 1, 2])
@pytest.mark.parametrize("locked", [True, False])
def test_protected_sheet_identity_and_deletion(tmp_path, position, locked):
    s = Session(tmp_path / "protected.texel")

    def seed(w):
        w.add_sheet("Middle")
        w.add_sheet("Last")
        w.sheet(position).set_raw(0, 0, "protected")
        w.sheet(position).cell(0, 0).locked = locked
        w.sheet(position).protected = True

    s.apply("seed", seed)
    before = deepcopy(s.workbook.to_dict()), s.revision
    with pytest.raises(ValueError):
        s.apply("delete", lambda w: delete_sheet(w, position))
    assert (s.workbook.to_dict(), s.revision) == before
    s.apply("rename", lambda w: rename_sheet(w, position, "Renamed"))
    other = 0 if position else 2
    s.apply("delete other", lambda w: delete_sheet(w, other))
    assert s.workbook.sheet("Renamed").cell(0, 0).raw == "protected"
    assert s.undo() and s.redo()
    s.apply("unprotect", lambda w: setattr(w.sheet("Renamed"), "protected", False))
    s.apply("delete", lambda w: delete_sheet(w, w.sheet_index("Renamed")))


@pytest.mark.parametrize("conflict", [False, True])
async def test_failed_draft_click_keeps_target_cursor_and_focus(tmp_path, conflict):
    path = tmp_path / "draft.texel"
    app = TexelApp(path)
    if not conflict:
        app.session.apply(
            "validation",
            lambda w: setattr(w.sheet().cell(0, 0), "validation", Validation(minimum=100)),
        )
    async with app.run_test(size=(100, 30)) as p:
        await p.press("4", "2")
        draft = app.editing
        if conflict:
            Session(path).apply("external", lambda w: set_matrix(w, 0, "C1", [["remote"]]))
        await p.click("#grid", offset=(26, 3))
        assert app.editing == draft
        assert app.grid.cursor == (0, 0)
        assert app.formula_input.value == "42"
        assert app.formula_input.has_focus
        await p.press("escape")


@pytest.mark.parametrize("suffix", ["csv", "tsv", "xlsx", "xls", "gsheet"])
async def test_cli_source_path_and_save_default(tmp_path, suffix):
    source = tmp_path / ("source." + suffix)
    book = Session(tmp_path / "fixture.texel").workbook
    book.sheet().set_raw(0, 0, "42")
    observed = []
    with (
        patch("texel.exchange.load_file", return_value=book),
        patch.object(TexelApp, "run", lambda self, **kwargs: observed.append(self)),
    ):
        assert main(["tui", "--workbook", str(source)]) == 0
    app = observed[0]
    assert app.source_path == source.resolve()
    async with app.run_test(size=(100, 30)) as p:
        await p.press("ctrl+s")
        expected = source.with_suffix(".xlsx") if suffix in {"xls", "gsheet"} else source
        assert app.screen.query_one("#field-path", Input).value == str(expected)


async def test_stdio_series_and_protected_delete(tmp_path):
    path = tmp_path / "mcp.texel"
    s = Session(path)
    s.apply("seed", lambda w: set_matrix(w, 0, "A1", [["9007199254740993"], ["9007199254740994"]]))
    async with Client(
        StdioServerParameters(
            command=sys.executable,
            args=["-m", "texel", "mcp", "--workbook", str(path), "--root", str(tmp_path)],
        )
    ) as client:
        result = (
            await client.call_tool(
                "fill_cells",
                {
                    "sheet": "Sheet1",
                    "range": "A1:A3",
                    "direction": "series",
                    "expected_revision": 1,
                },
            )
        ).structured_content
        assert result["ok"]
        assert Session(path).evaluator.value(0, 2, 0) == 9007199254740995
        s.reload()

        def seed_locked(w):
            w.add_sheet("Locked")
            w.sheet(1).protected = True
            w.sheet(1).cell(0, 0).locked = True

        s.apply("protect", seed_locked)
        result = (
            await client.call_tool(
                "edit_sheet",
                {"action": "delete", "sheet": "Locked", "expected_revision": s.revision},
            )
        ).structured_content
        assert not result["ok"]
        assert len(Session(path).workbook.sheets) == 2


@pytest.mark.parametrize("size", [(80, 24), (100, 30), (120, 40)])
async def test_context_tail_mouse_executes_once(tmp_path, size):
    app = TexelApp(tmp_path / "menu.texel", language="en")
    app.session.apply(
        "freeze",
        lambda w: (setattr(w.sheet(), "freeze_rows", 1), setattr(w.sheet(), "freeze_columns", 1)),
    )
    async with app.run_test(size=size) as p:
        await p.click("#grid", offset=(12, 1), button=3)
        await p.press("end")
        await p.pause()
        options = app.screen.query_one(OptionList)
        line = options._line_cache.index_to_line[options.highlighted]
        await p.click(
            offset=(
                options.content_region.x + 2,
                options.content_region.y + line - int(options.scroll_y),
            )
        )
        await p.pause()
        assert (app.grid.sheet.freeze_rows, app.grid.sheet.freeze_columns) == (0, 0)
        assert app.session.revision == 2
        assert len(app.screen_stack) == 1


@pytest.mark.parametrize("size", [(80, 24), (100, 30), (120, 40)])
async def test_problem_forms_actual_apply_and_resize_error(tmp_path, size):
    app = TexelApp(tmp_path / "forms.texel", language="en")
    app.session.apply(
        "seed", lambda w: set_matrix(w, 0, "A1", [["group", "n"], ["a", "2"], ["b", "1"]])
    )
    async with app.run_test(size=size) as p:
        for command in ("borders", "style", "validation", "sort", "filter", "pivot", "conditional"):
            app.grid.select_range(CellRange.parse("A1:B3"))
            await p.press("ctrl+p")
            await p.press(*command, "enter")
            if command == "style":
                app.screen.query_one("#field-decimals").value = "3"
            elif command == "validation":
                app.screen.query_one("#field-kind").value = "list"
                app.screen.query_one("#field-choices").value = "group,n,a,b,1,2"
            elif command == "filter":
                app.screen.query_one("#field-column").value = "2"
                app.screen.query_one("#field-criterion").value = ">=0"
            elif command == "pivot":
                app.screen.query_one("#field-name").value = "Result"
            assert await p.click("#apply", offset=(2, 1)), command
            assert type(app.screen).__name__ == "Screen", command
            assert app.session.store.revision == app.session.revision
            if command == "pivot":
                assert app.session.workbook.sheet("Result").cell(1, 1).raw == "2"
                app.sheet_index = 0
                app.refresh_workbook()
        app.run_command("borders")
        await p.pause()
        app.screen.query_one("#field-border_color").value = "bad"
        assert await p.click("#apply", offset=(2, 1))
        assert type(app.screen).__name__ == "FormDialog"
        for resized in ((120, 40), (80, 24), (100, 30)):
            await p.resize_terminal(*resized)
            await p.pause()
            button = app.screen.query_one("#apply")
            assert app.get_widget_at(button.region.x + 2, button.region.y + 1)[0] is button
        app.screen.query_one("#field-border_color").value = ""
        select = app.screen.query_one("#field-border_style")
        select.scroll_visible(animate=False)
        await p.pause()
        await p.click("#field-border_style")
        await p.press("end", "enter")
        assert await p.click("#apply", offset=(2, 1))
        assert type(app.screen).__name__ == "Screen"


@pytest.mark.parametrize("gesture", ["shift", "drag", "double", "formula"])
async def test_draft_mouse_gestures_align_input_target(tmp_path, gesture):
    app = TexelApp(tmp_path / "gesture.texel")
    async with app.run_test(size=(100, 30)) as p:
        if gesture == "formula":
            await p.click("#formula")
        await p.press("4", "2")
        if gesture == "drag":
            await p.mouse_down("#grid", offset=(26, 3))
            await p.hover("#grid", offset=(40, 4))
            await p.mouse_up("#grid", offset=(40, 4))
        else:
            await p.click(
                "#grid",
                offset=(26, 3),
                shift=gesture == "shift",
                times=2 if gesture == "double" else 1,
            )
        assert app.session.evaluator.value(0, 0, 0) == 42
        await p.press("7", "enter")
        assert (
            app.session.evaluator.value(
                0,
                *app.grid.sheet.merge_anchor(
                    2 if gesture != "drag" else 3, 1 if gesture != "drag" else 2
                ),
            )
            == 7
        )


@pytest.mark.parametrize(
    "movement,expected", [("enter", (3, 1)), ("tab", (0, 3)), ("shift+tab", (0, 0))]
)
async def test_merged_commit_movement_and_hidden_boundary(tmp_path, movement, expected):
    app = TexelApp(tmp_path / "merge.texel")

    def seed(w):
        merge_range(w, 0, "B1:C3")
        w.sheet().hidden_rows.add(3)

    app.session.apply("seed", seed)
    async with app.run_test(size=(80, 24)) as p:
        await p.press("right", "4", "2", movement)
        assert app.grid.cursor == ((4, 1) if movement == "enter" else expected)


async def test_frozen_wide_hidden_columns_cursor_resize_and_hit_test(tmp_path):
    app = TexelApp(tmp_path / "wide.texel")

    def seed(w):
        w.sheet().freeze_columns = 20
        w.sheet().column_widths = {c: 60 for c in range(20)}
        w.sheet().hidden_columns = {1, 2, 21}

    app.session.apply("seed", seed)
    async with app.run_test(size=(120, 40)) as p:
        for c in (19, 20, 22, 50):
            app.grid.move(0, c)
            for size in ((120, 40), (80, 24), (100, 30)):
                await p.resize_terminal(*size)
                await p.pause()
                columns = app.grid.visible_columns()
                column, x, width = next(entry for entry in columns if entry[0] == c)
                assert width >= 4
                assert app.grid.cell_at(x + 1, 1) == (0, column)
                assert any(cc >= 20 and ww >= 4 for cc, _, ww in columns)
        await p.press("right")
        assert app.grid.cursor[1] in [c for c, _, _ in app.grid.visible_columns()]


@pytest.mark.parametrize("style,glyph", [("thin", "│"), ("thick", "┃"), ("double", "║")])
async def test_shared_border_content_rule_joint_and_history(tmp_path, style, glyph):
    app = TexelApp(tmp_path / "edges.texel")
    app.session.apply("border", lambda w: apply_borders(w, 0, "A1:B2", "all", style))
    async with app.run_test(size=(100, 30)) as p:
        x = app.grid.visible_columns()[1][1]
        line = app.grid.render_line(2).text
        assert line[x] == glyph
        assert line[x - 1] != glyph
        assert app.grid.render_line(1).text[x] in {"┼", "╋", "╬"}
        assert app.grid.cell_at(x + 1, 2) == (0, 1)
        await p.press("ctrl+z", "ctrl+y")
        assert app.grid.render_line(2).text[x] == glyph


async def test_tui_protected_last_sheet_delete_keeps_document(tmp_path):
    app = TexelApp(tmp_path / "protected-ui.texel")

    def seed(w):
        w.add_sheet("Locked")
        w.sheet(1).protected = True

    app.session.apply("seed", seed)
    app.sheet_index = 1
    async with app.run_test(size=(80, 24)) as p:
        await p.press("ctrl+p")
        await p.press(*"delete_sheet", "enter")
        assert await p.click("#apply")
        assert type(app.screen).__name__ == "FormDialog"
        assert len(app.session.workbook.sheets) == 2
        assert app.session.revision == 1


@pytest.mark.parametrize(
    "field,value", [("active_sheet", "Sheet1"), ("freeze_rows", 1.5), ("freeze_columns", 1.5)]
)
def test_native_metadata_integer_types_rejected(tmp_path, field, value):
    path = tmp_path / "bad-type.texel"
    s = Session(path)
    with s.store.connect() as db:
        data = json.loads(db.execute("SELECT metadata FROM texel_state").fetchone()[0])
        target = data if field == "active_sheet" else data["sheets"][0]
        target[field] = value
        db.execute("UPDATE texel_state SET metadata=?", (json.dumps(data),))
    before = path.read_bytes()
    with pytest.raises(ValueError):
        load_file(path)
    assert path.read_bytes() == before


@pytest.mark.parametrize("gap", ["hidden", "frozen"])
async def test_discontinuous_visible_border_keeps_previous_right(tmp_path, gap):
    app = TexelApp(tmp_path / "gap.texel")

    def seed(w):
        apply_borders(w, 0, "A1", "right", "thick")
        apply_borders(w, 0, "D1", "top", "thin")
        if gap == "hidden":
            w.sheet().hidden_columns.add(1)
        else:
            w.sheet().freeze_columns = 1

    app.session.apply("seed", seed)
    async with app.run_test(size=(80, 24)):
        if gap == "frozen":
            app.grid.left = 2
        x = app.grid.visible_columns()[1][1]
        assert app.grid.render_line(2).text[x] == "┃"
        assert app.grid.render_line(1).text[x] == "┃"


async def test_frozen_cursor_requires_four_visible_columns(tmp_path):
    app = TexelApp(tmp_path / "last-pixel.texel")
    app.session.apply("freeze", lambda w: setattr(w.sheet(), "freeze_columns", 1))
    async with app.run_test(size=(80, 24)) as p:
        await p.press(*(["right"] * 5))
        assert next(width for c, _, width in app.grid.visible_columns() if c == 5) >= 4


async def test_queued_modal_search_keys_do_not_edit_previous_cell(tmp_path):
    app = TexelApp(tmp_path / "queued-search.texel", language="en")
    app.session.apply("seed", lambda w: set_matrix(w, 0, "A1", [["original"]]))
    async with app.run_test(size=(80, 24)) as p:
        app.action_commands()
        for char in "borders":
            app.grid.post_message(events.Key(char, char))
        app.grid.post_message(events.Key("enter", "\r"))
        await p.pause(0.5)
        assert app.session.workbook.sheet().cell(0, 0).raw == "original"
        assert app.editing is None
        assert type(app.screen).__name__ == "FormDialog"
        assert app.screen.title_text == "borders"


async def test_batched_command_shortcut_keeps_cell_raw(tmp_path):
    app = TexelApp(tmp_path / "batch-command.texel", language="en")
    app.session.apply("seed", lambda w: set_matrix(w, 0, "A1", [["original"]]))
    async with app.run_test(size=(80, 24)) as p:
        for key, char in [("ctrl+p", None), *[(c, c) for c in "borders"], ("enter", "\r")]:
            app.post_message(events.Key(key, char))
        await p.pause(0.5)
        assert app.session.workbook.sheet().cell(0, 0).raw == "original"
        assert app.session.revision == 1
        assert app.editing is None
        assert type(app.screen).__name__ == "FormDialog"
        assert app.screen.title_text == "borders"


async def test_commit_focus_does_not_reopen_stale_formula_draft(tmp_path):
    app = TexelApp(tmp_path / "focus-order.texel")
    async with app.run_test(size=(80, 24)) as p:
        app.begin_edit("7")
        assert app.screen.focused is app.formula_input
        assert app.commit_edit((1, 0))
        assert app.screen.focused is app.grid
        await p.pause(0.2)
        assert app.editing is None
        assert app.session.workbook.sheet().cell(0, 0).raw == "7"
        assert app.session.workbook.sheet().cell(1, 0).raw == ""
