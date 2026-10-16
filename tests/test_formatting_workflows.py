import pytest
from mcp import Client
from textual.widgets import Checkbox, OptionList

from texel.editing import apply_borders, merge_range, set_matrix
from texel.exchange import load_file
from texel.mcp_server import create_server
from texel.ui.app import TexelApp


@pytest.mark.asyncio
async def test_special_paste_values_formats_and_merged_copy(tmp_path):
    app = TexelApp(tmp_path / "paste.texel")
    app.session.apply(
        "seed",
        lambda w: (
            set_matrix(w, 0, "A1", [["9007199254740993", "=A1+1"]]),
            apply_borders(w, 0, "B1", "all", "thick"),
        ),
    )
    async with app.run_test(size=(100, 30)) as pilot:
        app.grid.move(0, 1)
        app.copy_selection()
        app.grid.move(2, 1)
        app.run_command("paste_special")
        await pilot.pause()
        app.screen.query_one("#field-paste_mode").value = "values"
        await pilot.click("#apply")
        assert app.session.evaluator.value(0, 2, 1) == 9007199254740994
        app.grid.move(3, 1)
        app.paste_clipboard(mode="formats")
        assert app.session.workbook.sheet().cell(3, 1).style.borders["top"].style == "thick"
        assert not app.session.workbook.sheet().cell(3, 1).raw
        app.session.apply(
            "merged", lambda w: (set_matrix(w, 0, "D1", [["heading"]]), merge_range(w, 0, "D1:F1"))
        )
        app.refresh_workbook()
        app.grid.move(0, 3)
        app.copy_selection()
        app.grid.move(4, 3)
        app.paste_clipboard()
        assert "D5:F5" in app.session.workbook.sheet().merges


@pytest.mark.asyncio
async def test_wrap_row_height_hit_testing_and_merge_confirmation(tmp_path):
    app = TexelApp(tmp_path / "wrap.texel")
    app.session.apply("seed", lambda w: set_matrix(w, 0, "A1", [["first", "second"]]))
    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.press("shift+right")
        app.run_command("merge")
        await pilot.pause()
        await pilot.click("#apply")
        assert app.session.workbook.sheet().merges == ["A1:B1"]
        assert app.session.workbook.sheet().row_heights[0] == 2
        assert "first" in app.grid.render_line(1).text
        assert "second" in app.grid.render_line(2).text
        assert app.grid.cell_at(25, 2) == (0, 0)
        app.run_command("unmerge")
        app.grid.move(0, 0)
        app.run_command("row_height")
        await pilot.pause()
        app.screen.query_one("#field-row_height").value = "3"
        await pilot.click("#apply")
        assert app.grid.cell_at(12, 4) == (1, 0)


@pytest.mark.asyncio
async def test_save_requires_overwrite_and_new_document_resets_source(tmp_path):
    app = TexelApp(tmp_path / "original.texel")
    destination = tmp_path / "existing.csv"
    destination.write_text("original")
    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.press("ctrl+s")
        app.screen.query_one("#field-path").value = str(destination)
        await pilot.click("#apply")
        assert type(app.screen).__name__ == "FileDialog"
        assert destination.read_text() == "original"
        app.screen.query_one("#overwrite", Checkbox).value = True
        await pilot.pause(0.4)
        await pilot.click("#apply")
        assert type(app.screen).__name__ == "Screen"
        assert app.source_path == destination
        app.run_command("demo")
        await pilot.pause()
        assert app.source_path is None


@pytest.mark.asyncio
async def test_context_outside_selection_and_edges(tmp_path):
    app = TexelApp(tmp_path / "edges.texel")
    async with app.run_test(size=(80, 24)) as pilot:
        await pilot.click("#grid", offset=(75, 8), button=3)
        assert app.grid.cursor[0] == 7
        box = app.screen.query_one("#context-box")
        assert box.region.right <= app.size.width and box.region.bottom <= app.size.height
        await pilot.press("escape")
        await pilot.click("#grid", offset=(2, 3), button=3)
        options = app.screen.query_one(OptionList)
        assert options.get_option_at_index(0).id == "insert_rows"


@pytest.mark.parametrize("encoding", ["utf-16", "cp949", "utf-8-sig"])
def test_csv_encodings(encoding, tmp_path):
    path = tmp_path / "한글.csv"
    path.write_text("이름,값\n서울,42\n", encoding=encoding)
    book = load_file(path)
    assert book.sheet().cell(1, 0).raw == "서울"
    assert book.sheet().cell(1, 1).raw == "42"


@pytest.mark.asyncio
async def test_mcp_borders_and_extended_format(tmp_path):
    async with Client(create_server(tmp_path / "mcp-style.texel", tmp_path)) as client:
        formatted = await client.call_tool(
            "format_range",
            {
                "sheet": "Sheet1",
                "range": "A1:B2",
                "wrap": True,
                "italic": True,
                "vertical_align": "middle",
                "expected_revision": 0,
            },
        )
        assert formatted.structured_content["ok"]
        bordered = await client.call_tool(
            "set_borders",
            {
                "sheet": "Sheet1",
                "range": "A1:B2",
                "preset": "outer",
                "border_style": "double",
                "expected_revision": 1,
            },
        )
        assert bordered.structured_content["ok"]
        read = await client.call_tool("read_range", {"sheet": "Sheet1", "range": "A1"})
        style = read.structured_content["rows"][0][0]["style"]
        assert style["wrap"] and style["italic"]
        assert style["borders"]["top"]["style"] == "double"
