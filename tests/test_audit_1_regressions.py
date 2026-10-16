"""감사 발견의 기대 동작. 현 제품의 실패를 보존하며 기존 테스트와 분리한다."""

import json
from unittest.mock import patch

import pytest
from textual.widgets import OptionList

from texel.__main__ import main as cli_main
from texel.editing import apply_borders, delete_sheet, merge_range, set_matrix
from texel.exchange import load_file
from texel.session import Session
from texel.ui.app import TexelApp


async def command(p, app, key):
    await p.press("ctrl+p")
    await p.press(*key, "enter")
    await p.pause()


async def test_IMP_F001_border_apply_reachable_at_80x24(tmp_path):
    app = TexelApp(tmp_path / "doc.texel")
    async with app.run_test(size=(80, 24)) as p:
        await command(p, app, "borders")
        assert await p.click("#apply", offset=(2, 1)), "적용 버튼이 다른 위젯에 가려짐"
        assert type(app.screen).__name__ == "Screen"
        assert app.session.revision == 1


async def test_DBG_F006_context_last_command_clickable_at_80x24(tmp_path):
    app = TexelApp(tmp_path / "doc.texel", language="en")
    app.session.apply(
        "freeze",
        lambda w: (setattr(w.sheet(), "freeze_rows", 1), setattr(w.sheet(), "freeze_columns", 1)),
    )
    async with app.run_test(size=(80, 24)) as p:
        await p.click("#grid", offset=(12, 1), button=3)
        await p.press("end")
        await p.pause(0.6)
        options = app.screen.query_one(OptionList)
        line = options._line_cache.index_to_line[options.highlighted]
        x = options.content_region.x + 2
        y = options.content_region.y + line - int(options.scroll_y)
        await p.click(offset=(x, y))
        assert type(app.screen).__name__ == "Screen", "마지막 우클릭 명령이 메뉴 박스에 가려짐"
        assert (app.grid.sheet.freeze_rows, app.grid.sheet.freeze_columns) == (0, 0)


async def test_DBG_F001_clicking_new_cell_closes_old_draft(tmp_path):
    app = TexelApp(tmp_path / "doc.texel")
    async with app.run_test(size=(100, 30)) as p:
        await p.press("4", "2")
        await p.click("#grid", offset=(26, 3))
        await p.press("7", "enter")
        assert app.session.evaluator.value(0, 0, 0) == 42
        assert app.session.evaluator.value(0, 2, 1) == 7


async def test_DBG_F002_series_preserves_exact_integer_values(tmp_path):
    app = TexelApp(tmp_path / "doc.texel")
    app.session.apply(
        "seed", lambda w: set_matrix(w, 0, "A1", [["9007199254740993"], ["9007199254740994"]])
    )
    async with app.run_test(size=(100, 30)) as p:
        await p.press("shift+down", "shift+down")
        await command(p, app, "series")
        assert [app.session.evaluator.value(0, r, 0) for r in range(3)] == [
            9007199254740993,
            9007199254740994,
            9007199254740995,
        ]


async def test_IMP_F002_enter_advances_beyond_merged_cell(tmp_path):
    app = TexelApp(tmp_path / "doc.texel")
    app.session.apply("merge", lambda w: merge_range(w, 0, "A1:B3"))
    async with app.run_test(size=(100, 30)) as p:
        await p.press("4", "2", "enter")
        assert app.grid.cursor == (3, 0)


async def test_IMP_F003_frozen_columns_leave_cursor_visible(tmp_path):
    app = TexelApp(tmp_path / "doc.texel")
    async with app.run_test(size=(80, 24)) as p:
        await p.press("ctrl+g")
        await p.press(*"G2", "enter")
        await command(p, app, "freeze")
        await p.press("right", "right")
        assert app.grid.cursor[1] in [c for c, _, _ in app.grid.visible_columns()]


async def test_DBG_F003_failed_open_keeps_current_workbook(tmp_path):
    path = tmp_path / "bad.texel"
    s = Session(path)
    with s.store.connect() as db:
        m = json.loads(db.execute("SELECT metadata FROM texel_state").fetchone()[0])
        m["sheets"][0]["filter_spec"] = {"range": "NOPE", "column": 0, "criterion": ">0"}
        db.execute("UPDATE texel_state SET metadata=?", (json.dumps(m),))
    app = TexelApp(tmp_path / "original.texel")
    before = app.session.store.path
    app.session.apply("seed", lambda w: set_matrix(w, 0, "A1", [["original"]]))
    async with app.run_test(size=(120, 40)) as p:
        await p.press("ctrl+o")
        await p.press(*str(path), "enter")
        assert app.session.store.path == before
        assert app.session.evaluator.value(0, 0, 0) == "original"


def test_SEC_F001_protected_sheet_cannot_be_deleted(tmp_path):
    s = Session(tmp_path / "doc.texel")

    def seed(w):
        w.add_sheet("Locked")
        w.sheet(1).set_raw(0, 0, "protected")
        w.sheet(1).cell(0, 0).locked = True
        w.sheet(1).protected = True

    s.apply("seed", seed)
    with pytest.raises(ValueError):
        s.apply("delete", lambda w: delete_sheet(w, 1))


def test_DBG_F004_cli_import_retains_original_save_path(tmp_path):
    source = tmp_path / "source.csv"
    source.write_text("a,42\n", encoding="utf-8")
    observed = []

    def capture(self, **kwargs):
        observed.append(self.source_path)

    with patch.object(TexelApp, "run", capture):
        assert cli_main(["tui", "--workbook", str(source)]) == 0
    assert observed == [source.resolve()]


def test_DBG_F005_open_empty_native_does_not_mutate_input(tmp_path):
    source = tmp_path / "zero.texel"
    source.write_bytes(b"")
    try:
        load_file(source)
    except ValueError:
        pass
    assert source.read_bytes() == b""


async def test_IMP_F004_adjacent_cell_borders_use_one_boundary(tmp_path):
    app = TexelApp(tmp_path / "doc.texel")
    app.session.apply("border", lambda w: apply_borders(w, 0, "A1:B2", "all", "thick"))
    async with app.run_test(size=(100, 30)):
        assert "┃┃" not in app.grid.render_line(2).text
