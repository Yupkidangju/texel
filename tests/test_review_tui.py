import pytest

from texel.editing import delete_sheet, set_matrix
from texel.session import Session
from texel.ui.app import TexelApp
from texel.ui.dialogs import FormDialog


@pytest.mark.asyncio
async def test_deleted_sheet_conflict_preserves_draft(tmp_path):
    path = tmp_path / "deleted.texel"
    app = TexelApp(path)
    app.session.apply("add", lambda w: w.add_sheet("Other"))
    async with app.run_test(size=(100, 30)) as pilot:
        app.sheet_index = 1
        app.refresh_workbook()
        app.begin_edit("draft")
        other = Session(path)
        other.apply("delete", lambda w: delete_sheet(w, 1))
        app.poll_external()
        assert not app.commit_edit()
        assert app.formula_input.value == "draft"
        assert len(app.session.workbook.sheets) == 1
        await pilot.press("escape")
        assert app.editing is None


@pytest.mark.asyncio
async def test_mutating_form_keeps_captured_revision(tmp_path):
    path = tmp_path / "form-conflict.texel"
    app = TexelApp(path)
    app.session.apply("initial", lambda w: set_matrix(w, 0, "A1", [["old"]]))
    async with app.run_test(size=(100, 30)) as pilot:
        app.run_command("replace")
        await pilot.pause()
        app.screen.query_one("#field-query").value = "old"
        app.screen.query_one("#field-replacement").value = "new"
        other = Session(path)
        other.apply("external", lambda w: set_matrix(w, 0, "A2", [["old external"]]))
        app.poll_external()
        await pilot.click("#apply")
        assert isinstance(app.screen, FormDialog)
        assert app.screen.query_one("#field-query").value == "old"
        assert Session(path).workbook.sheet().cell(1, 0).raw == "old external"


@pytest.mark.asyncio
async def test_terminal_controls_remain_data_in_all_ui_paths(tmp_path):
    app = TexelApp(tmp_path / "controls.texel")
    payload = "\x1b[2JX\x1b]52;c;dGVzdA==\x07"
    app.session.apply("untrusted", lambda w: set_matrix(w, 0, "A1", [["'" + payload]]))
    async with app.run_test(size=(100, 30)) as pilot:
        assert "\x1b" not in app.grid.render_line(1).text
        app.begin_edit()
        await pilot.pause()
        assert "\x1b" not in app.formula_input.render_line(1).text
        assert app.formula_input.value == "'" + payload
        await pilot.press("escape")
        app.run_command("inspect")
        await pilot.pause()
        assert "\x1b" not in app.screen.query_one("VerticalScroll > Static").render().plain
        assert app.session.workbook.sheet().cell(0, 0).raw == "'" + payload


@pytest.mark.asyncio
@pytest.mark.parametrize("extension", [".texel", ".xlsx"])
async def test_malformed_open_retains_document_and_form(extension, tmp_path):
    app = TexelApp(tmp_path / "original.texel")
    bad = tmp_path / ("bad" + extension)
    bad.write_text("not this format")
    async with app.run_test(size=(100, 30)) as pilot:
        app.run_command("open")
        await pilot.pause()
        app.screen.query_one("#field-path").value = str(bad)
        await pilot.click("#apply")
        assert isinstance(app.screen, FormDialog)
        assert app.session.store.path.name == "original.texel"
        assert app.screen.query_one("#field-path").value == str(bad)


@pytest.mark.asyncio
async def test_max_row_header_matches_pointer_coordinates(tmp_path):
    app = TexelApp(tmp_path / "last-row.texel")
    async with app.run_test(size=(100, 30)) as pilot:
        app.grid.top = 999999
        app.grid.refresh()
        await pilot.pause()
        line = app.grid.render_line(1).text
        divider = line.index("│")
        expected_column = app.grid.cell_at(divider - 1, 1)[1]
        assert expected_column == 0
