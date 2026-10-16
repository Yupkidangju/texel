import pytest
from textual import events

from texel.editing import set_matrix
from texel.ui.app import TexelApp


async def command(p, key):
    await p.press("ctrl+p")
    await p.press(*key, "enter")


@pytest.mark.parametrize("size", [(80, 24), (100, 30)])
async def test_advanced_sort_filter_public_forms_and_undo(tmp_path, size):
    app = TexelApp(tmp_path / "tables.texel", language="en")
    app.session.apply(
        "seed",
        lambda w: set_matrix(w, 0, "A1", [["team", "n"], ["b", "2"], ["a", "1"], ["a", "4"]]),
    )
    async with app.run_test(size=size) as p:
        await command(p, "advanced_sort")
        assert type(app.screen).__name__ == "FormDialog"
        app.screen.query_one("#field-sort_column_2").value = "2"
        app.screen.query_one("#field-descending_2").value = True
        assert await p.click("#apply", offset=(2, 1))
        assert app.session.evaluator.value(0, 1, 1) == 4
        await command(p, "advanced_filter")
        app.screen.query_one("#field-criterion_1").value = "a"
        app.screen.query_one("#field-filter_column_2").value = "2"
        app.screen.query_one("#field-criterion_2").value = ">2"
        assert await p.click("#apply", offset=(2, 1))
        assert app.grid._filtered == {2, 3}
        await p.press("ctrl+z")
        assert app.grid._filtered == set()
        await p.press("ctrl+z")
        assert app.session.evaluator.value(0, 1, 0) == "b"


async def test_keyboard_data_navigation_selection_and_f4(tmp_path):
    app = TexelApp(tmp_path / "keys.texel")
    app.session.apply(
        "seed",
        lambda w: (set_matrix(w, 0, "A1", [["1", "2", "3"]]), set_matrix(w, 0, "G1", [["7", "8"]])),
    )
    async with app.run_test(size=(80, 24)) as p:
        await p.press("ctrl+right")
        assert app.grid.cursor == (0, 2)
        await p.press("ctrl+right", "ctrl+shift+right")
        assert str(app.grid.selection) == "G1:H1"
        await p.press("ctrl+home", "ctrl+a")
        assert str(app.grid.selection) == "A1:H1"
        await p.press("shift+space")
        assert app.grid.selection.width == 16384
        await p.press("ctrl+space")
        assert app.grid.selection.height == 1048576
        await p.press("escape", "down", "=", "A", "1", "f4")
        assert app.formula_input.value == "=$A$1"
        await p.press("enter")
        assert app.session.evaluator.value(0, 1, 0) == 1


async def test_search_across_workbook_and_formula_trace(tmp_path):
    app = TexelApp(tmp_path / "find.texel", language="en")
    app.session.apply(
        "seed", lambda w: (w.add_sheet("Other"), set_matrix(w, 1, "A1", [["=6*7", "=A1+1"]]))
    )
    async with app.run_test(size=(80, 24)) as p:
        await p.press("ctrl+f")
        app.screen.query_one("#field-query").value = "42"
        app.screen.query_one("#field-search_values").value = True
        app.screen.query_one("#field-whole_workbook").value = True
        assert await p.click("#apply", offset=(2, 1))
        assert app.sheet_index == 1 and app.grid.cursor == (0, 0)
        await p.press("right")
        await command(p, "trace_formula")
        assert type(app.screen).__name__ == "TextDialog"
        assert "Other!A1" in app.screen.content


async def test_batched_tab_typing_stays_in_intended_filter_fields(tmp_path):
    app = TexelApp(tmp_path / "tab-input.texel", language="en")
    async with app.run_test(size=(80, 24)) as p:
        await command(p, "advanced_filter")
        for key in ["tab", "tab", "tab", "a", "tab", "2", "tab", ">", "1"]:
            app.post_message(events.Key(key, key if len(key) == 1 else None))
        await p.pause(0.3)
        assert app.screen.query_one("#field-range").value == "A1"
        assert app.screen.query_one("#field-criterion_1").value == "a"
        assert app.screen.query_one("#field-filter_column_2").value == "2"
        assert app.screen.query_one("#field-criterion_2").value == ">1"
