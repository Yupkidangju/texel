from pathlib import Path

import pytest

from texel.editing import apply_borders, copy_range, merge_range, set_matrix
from texel.exchange import load_file
from texel.model import Workbook
from texel.ui.app import TexelApp
from texel.ui.file_dialog import drive_roots


@pytest.mark.asyncio
async def test_value_paste_keeps_literal_string_types(tmp_path):
    app = TexelApp(tmp_path / "types.texel")
    app.session.apply(
        "seed", lambda w: set_matrix(w, 0, "A1", [["'00123", "'TRUE", "'2026-10-10"]])
    )
    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.press("shift+right", "shift+right")
        app.copy_selection()
        app.grid.move(2, 0)
        app.paste_clipboard(mode="values")
        assert [app.session.evaluator.value(0, 2, c) for c in range(3)] == [
            "00123",
            "TRUE",
            "2026-10-10",
        ]


def test_merge_combine_preserves_exact_large_values():
    w = Workbook()
    set_matrix(w, 0, "A1", [["9007199254740993", "9007199254740994"]])
    merge_range(w, 0, "A1:B1", contents="combine")
    assert w.sheet().cell(0, 0).raw == "'9007199254740993\n9007199254740994"


def test_domain_copy_preserves_row_heights_and_transpose_policy():
    w = Workbook()
    set_matrix(w, 0, "A1", [["'one\ntwo\nthree"]])
    w.sheet().cell(0, 0).style.wrap = True
    w.sheet().row_heights[0] = 3
    merge_range(w, 0, "A1:B1")
    copy_range(w, 0, "A1:B1", "A4")
    assert w.sheet().row_heights[3] == 3
    copy_range(w, 0, "A1:B1", "D4", transpose=True)
    assert w.sheet().row_heights[3] == w.sheet().row_heights[4] == 3


@pytest.mark.asyncio
async def test_clipboard_merge_keeps_height(tmp_path):
    app = TexelApp(tmp_path / "height-copy.texel")

    def seed(w):
        set_matrix(w, 0, "A1", [["'one\ntwo\nthree"]])
        w.sheet().row_heights[0] = 3
        w.sheet().cell(0, 0).style.wrap = True
        merge_range(w, 0, "A1:B1")

    app.session.apply("seed", seed)
    async with app.run_test(size=(100, 30)):
        app.copy_selection()
        app.grid.move(3, 0)
        app.paste_clipboard()
        assert app.session.workbook.sheet().row_heights[3] == 3


@pytest.mark.asyncio
async def test_new_xlsx_is_real_xlsx_and_backup_rejects_other_suffix(tmp_path):
    app = TexelApp(tmp_path / "initial.texel")
    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.press("ctrl+n")
        app.screen.query_one("#file-type").value = ".xlsx"
        destination = tmp_path / "new.xlsx"
        app.screen.query_one("#field-path").value = str(destination)
        await pilot.click("#apply")
        assert load_file(destination).sheets
        app.run_command("backup")
        await pilot.pause()
        bad = tmp_path / "bad-backup.xlsx"
        app.screen.query_one("#field-path").value = str(bad)
        await pilot.click("#apply")
        assert not bad.exists()
        assert type(app.screen).__name__ == "FileDialog"


@pytest.mark.asyncio
async def test_frozen_tall_header_leaves_scrollable_content(tmp_path):
    app = TexelApp(tmp_path / "frozen.texel")

    def seed(w):
        w.sheet().freeze_rows = 1
        w.sheet().row_heights[0] = 12

    app.session.apply("seed", seed)
    async with app.run_test(size=(80, 24)) as pilot:
        await pilot.press("down")
        assert app.grid.cursor == (1, 0)
        assert 1 in app.grid.visible_rows()


@pytest.mark.asyncio
async def test_merged_outline_continues_on_other_column_rule_row(tmp_path):
    app = TexelApp(tmp_path / "outline.texel")

    def seed(w):
        merge_range(w, 0, "A1:B3")
        apply_borders(w, 0, "A1:B3", "outer", "thick")
        apply_borders(w, 0, "C2", "top", "thin")

    app.session.apply("seed", seed)
    async with app.run_test(size=(100, 30)):
        y = next(
            i + 1
            for i, slot in enumerate(app.grid.row_slots())
            if slot.row == 1 and slot.kind == "rule"
        )
        assert app.grid.render_line(y).text[9] == "┃"
        boundary = next(x for c, x, _ in app.grid.visible_columns() if c == 2)
        assert app.grid.render_line(y).text[boundary] == "╋"
        content_y = next(
            i + 1
            for i, slot in enumerate(app.grid.row_slots())
            if slot.row == 1 and slot.kind == "content"
        )
        assert app.grid.render_line(content_y).text[boundary] == "┃"


@pytest.mark.asyncio
async def test_drive_selection_tracks_direct_folder_navigation(tmp_path):
    app = TexelApp(tmp_path / "drive.texel")
    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.press("ctrl+o")
        roots = [Path(r) for r in drive_roots(tmp_path) if Path(r).is_dir()]
        other = next((p for p in roots if p.anchor != tmp_path.anchor), roots[0])
        app.screen.query_one("#folder-path").value = str(other)
        app.screen.query_one("#folder-go").scroll_visible(animate=False)
        await pilot.pause()
        await pilot.click("#folder-go")
        assert Path(app.screen.query_one("#drive").value).anchor == other.anchor
        app.screen.query_one("#drive").value = tmp_path.anchor
        await pilot.pause()
        assert app.screen.folder.anchor == tmp_path.anchor


@pytest.mark.asyncio
async def test_border_clear_updates_existing_shared_neighbor_edges(tmp_path):
    app = TexelApp(tmp_path / "shared-border.texel")
    app.session.apply("border", lambda w: apply_borders(w, 0, "A1:B1", "all", "thick"))
    async with app.run_test(size=(100, 30)):
        app.mutate("thin", lambda w: apply_borders(w, 0, "B1", "all", "thin"))
        assert app.grid.vertical_edge(0, 1).style == "thin"
        app.mutate("remove", lambda w: apply_borders(w, 0, "B1", "none"))
        assert app.grid.vertical_edge(0, 1) is None
