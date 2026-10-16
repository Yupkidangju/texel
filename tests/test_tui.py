import pytest
from textual import events

from texel.editing import set_matrix
from texel.session import Session
from texel.ui.app import TexelApp
from texel.ui.grid import SpreadsheetGrid


@pytest.mark.asyncio
async def test_keyboard_edit_mouse_click_and_drag(tmp_path):
    app = TexelApp(tmp_path / "ui.texel")
    async with app.run_test(size=(120, 40)) as pilot:
        grid = app.query_one("#grid", SpreadsheetGrid)
        await pilot.press("1", "2", "enter")
        assert app.session.workbook.sheet().cell(0, 0, False).raw == "12"
        assert grid.cursor == (1, 0)
        await pilot.click("#grid", offset=(24, 3))
        assert grid.cursor == (2, 1)
        await pilot.mouse_down("#grid", offset=(9, 1))
        await pilot.hover("#grid", offset=(40, 4))
        await pilot.mouse_up("#grid", offset=(40, 4))
        assert grid.selection.size > 1
        await pilot.press("ctrl+z")
        assert app.session.evaluator.value(0, 0, 0) is None


@pytest.mark.asyncio
async def test_copy_paste_formula_and_find_command(tmp_path):
    app = TexelApp(tmp_path / "copy.texel")
    app.session.apply("seed", lambda w: set_matrix(w, 0, "A1", [["10", "=A1*2"]]))
    async with app.run_test(size=(100, 30)) as pilot:
        grid = app.query_one("#grid", SpreadsheetGrid)
        await pilot.press("right", "ctrl+c", "down", "ctrl+v")
        assert app.session.workbook.sheet().cell(1, 1).raw == "=A2*2"
        await pilot.press("ctrl+p")
        await pilot.press("f", "i", "n", "d", "enter")
        assert app.screen.__class__.__name__ == "FormDialog"
        await pilot.press("escape")
        assert grid.has_focus


@pytest.mark.asyncio
async def test_external_change_during_edit_preserves_draft(tmp_path):
    path = tmp_path / "shared.texel"
    app = TexelApp(path)
    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.press("f2", "x")
        other = Session(path, source="mcp")
        other.apply("external", lambda w: set_matrix(w, 0, "A1", [["external"]]))
        app.poll_external()
        await pilot.press("enter")
        assert app.query_one("#formula").value == "x"
        assert Session(path).workbook.sheet().cell(0, 0).raw == "external"
        await pilot.press("escape")


@pytest.mark.asyncio
@pytest.mark.parametrize("size", [(80, 24), (140, 45)])
async def test_layout_and_mouse_menu(size, tmp_path):
    app = TexelApp(tmp_path / "size.texel")
    async with app.run_test(size=size) as pilot:
        assert app.query_one("#grid").size.height > 4
        await pilot.click("#menu-analysis")
        assert app.screen.__class__.__name__ == "CommandDialog"
        await pilot.press("escape")


@pytest.mark.asyncio
async def test_batched_terminal_keys_do_not_lose_edit_characters(tmp_path):
    app = TexelApp(tmp_path / "rapid.texel")
    async with app.run_test(size=(100, 30)) as pilot:
        for key, character in [("4", "4"), ("2", "2"), ("enter", "\r")]:
            app.post_message(events.Key(key, character))
        await pilot.pause()
        assert app.session.workbook.sheet().cell(0, 0, False).raw == "42"
        for key, character in [("5", "5"), ("4", "4"), ("enter", "\r")]:
            app.post_message(events.Key(key, character))
        await pilot.pause()
        assert app.session.workbook.sheet().cell(1, 0, False).raw == "54"
