import pytest

from texel.editing import set_matrix
from texel.ui.app import TexelApp
from texel.ui.dialogs import FormDialog, TextDialog


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "command",
    [
        "style",
        "validation",
        "conditional",
        "width",
        "sort",
        "filter",
        "pivot",
        "chart",
        "note",
        "named_range",
        "add_sheet",
        "rename_sheet",
        "duplicate_sheet",
        "export",
        "find",
        "replace",
    ],
)
async def test_commands_reachable_via_palette(command, tmp_path):
    app = TexelApp(tmp_path / f"{command}.texel", language="en")
    app.session.apply(
        "seed", lambda w: set_matrix(w, 0, "A1", [["group", "n"], ["a", "10"], ["b", "20"]])
    )
    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.press("ctrl+p")
        app.screen.query_one("#command-search").value = command
        await pilot.pause()
        await pilot.press("enter")
        assert isinstance(app.screen, FormDialog)
        assert app.screen.title_text == command
        await pilot.press("escape")
        assert app.grid.has_focus


@pytest.mark.asyncio
async def test_sheet_add_style_filter_pivot_and_chart_public_forms(tmp_path):
    app = TexelApp(tmp_path / "flows.texel")
    app.session.apply(
        "seed",
        lambda w: set_matrix(w, 0, "A1", [["group", "n"], ["a", "10"], ["a", "20"], ["b", "30"]]),
    )
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.click("#add-sheet")
        app.screen.query_one("#field-name").value = "New"
        await pilot.click("#apply")
        await pilot.pause()
        assert app.sheet_index == 1
        assert app.tabs.active == "sheet-1"
        await pilot.click("#sheet-0")
        assert app.sheet_index == 0
        app.run_command("style")
        await pilot.pause()
        app.screen.query_one("#field-number_format").value = "number"
        await pilot.click("#apply")
        assert app.session.workbook.sheet().cell(0, 0).style.number_format == "number"
        app.run_command("filter")
        await pilot.pause()
        app.screen.query_one("#field-column").value = "2"
        app.screen.query_one("#field-criterion").value = ">10"
        await pilot.click("#apply")
        assert 1 in app.grid._filtered
        app.run_command("clear_filter")
        app.run_command("pivot")
        await pilot.pause()
        await pilot.click("#apply")
        await pilot.pause()
        assert app.sheet_index == 2
        assert app.session.evaluator.value(2, 1, 1) == 30
        app.run_command("chart")
        await pilot.pause()
        await pilot.click("#apply")
        await pilot.pause()
        assert isinstance(app.screen, TextDialog)
        assert "█" in app.screen.content


@pytest.mark.asyncio
async def test_invalid_form_keeps_inputs_and_no_revision(tmp_path):
    app = TexelApp(tmp_path / "form.texel")
    async with app.run_test(size=(100, 30)) as pilot:
        app.run_command("width")
        await pilot.pause()
        app.screen.query_one("#field-width").value = "200"
        await pilot.click("#apply")
        assert isinstance(app.screen, FormDialog)
        assert app.screen.query_one("#field-width").value == "200"
        assert app.session.revision == 0


@pytest.mark.asyncio
async def test_formula_bar_mouse_and_double_click_edit(tmp_path):
    app = TexelApp(tmp_path / "mouse.texel")
    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.click("#grid", offset=(24, 3), times=2)
        assert app.editing[:3] == (0, 2, 1)
        await pilot.press("9", "enter")
        assert app.session.evaluator.value(0, 2, 1) == 9
        await pilot.click("#formula")
        app.formula_input.value = "=SUM(B3,1)"
        await pilot.click("#commit")
        assert app.session.evaluator.value(0, 3, 1) == 10
