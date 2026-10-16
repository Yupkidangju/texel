import pytest
from textual.widgets import DirectoryTree, OptionList

from texel.editing import merge_range, set_matrix
from texel.exchange import export_file
from texel.model import Workbook
from texel.ui.app import TexelApp


@pytest.mark.asyncio
async def test_merge_is_visibly_spanning_and_navigation_skips_it(tmp_path):
    app = TexelApp(tmp_path / "merged.texel")
    app.session.apply(
        "merge",
        lambda w: (
            set_matrix(w, 0, "A1", [["a complete merged heading"]]),
            merge_range(w, 0, "A1:C1"),
        ),
    )
    async with app.run_test(size=(100, 30)) as pilot:
        assert "a complete merged heading" in app.grid.render_line(1).text
        assert app.grid.selection.width == 3
        await pilot.press("right")
        assert app.grid.cursor == (0, 3)
        await pilot.press("left")
        assert app.grid.cursor == (0, 0)
        await pilot.click("#grid", offset=(40, 1))
        assert app.grid.cursor == (0, 0)


@pytest.mark.asyncio
async def test_right_click_preserves_range_and_runs_border_command(tmp_path):
    app = TexelApp(tmp_path / "context.texel")
    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.press("shift+right", "shift+down")
        selected = str(app.grid.selection)
        await pilot.click("#grid", offset=(12, 1), button=3)
        assert type(app.screen).__name__ == "ContextMenu"
        assert app.screen.styles.background.a < 1
        assert "TEXEL" in app.export_screenshot()
        assert str(app.grid.selection) == selected
        options = app.screen.query_one(OptionList)
        assert {"copy", "cut", "paste", "borders", "merge", "unmerge", "style"} <= {
            options.get_option_at_index(i).id for i in range(options.option_count)
        }
        options.highlighted = options.get_option_index("borders")
        await pilot.press("enter")
        await pilot.pause()
        app.screen.query_one("#field-border_style").value = "thick"
        await pilot.click("#apply")
        assert app.session.workbook.sheet().cell(0, 0).style.borders["top"].style == "thick"
        assert any("━" in app.grid.render_line(y).text for y in range(1, app.grid.size.height - 1))


@pytest.mark.asyncio
@pytest.mark.parametrize("extension", [".csv", ".xlsx"])
async def test_open_and_save_outside_initial_folder(extension, tmp_path):
    start = tmp_path / "data"
    elsewhere = tmp_path / "outside"
    start.mkdir()
    elsewhere.mkdir()
    w = Workbook()
    set_matrix(w, 0, "A1", [["항목", "금액"], ["테스트", "42"]])
    source = elsewhere / ("source" + extension)
    export_file(w, source)
    app = TexelApp(start / "work.texel")
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.press("ctrl+o")
        assert type(app.screen).__name__ == "FileDialog"
        await pilot.click("#folder-up")
        await pilot.pause()
        assert app.screen.query_one(DirectoryTree).path == tmp_path
        app.screen.query_one("#folder-path").value = str(elsewhere)
        await pilot.click("#folder-go")
        await pilot.pause()
        assert app.screen.query_one(DirectoryTree).path == elsewhere
        app.screen.query_one("#field-path").value = str(source)
        await pilot.click("#apply")
        assert app.session.evaluator.value(0, 1, 1) == 42
        await pilot.press("ctrl+s")
        assert type(app.screen).__name__ == "FileDialog"
        destination = elsewhere / ("saved" + extension)
        app.screen.query_one("#field-path").value = str(destination)
        await pilot.click("#apply")
        assert destination.exists()


@pytest.mark.asyncio
async def test_merged_vertical_down_and_split_context(tmp_path):
    app = TexelApp(tmp_path / "vertical.texel")
    app.session.apply("merge", lambda w: merge_range(w, 0, "A1:A3"))
    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.press("down")
        assert app.grid.cursor == (3, 0)
        app.grid.move(0, 0)
        await pilot.press("shift+f10")
        assert type(app.screen).__name__ == "ContextMenu"
        options = app.screen.query_one(OptionList)
        options.highlighted = options.get_option_index("unmerge")
        await pilot.press("enter")
        assert not app.session.workbook.sheet().merges
