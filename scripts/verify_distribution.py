"""선택한 설치본의 모듈, 공개 UI 및 실제 MCP stdio 경로를 검증한다."""

import argparse
import asyncio
import json
import sys
from pathlib import Path
from unittest.mock import patch


async def verify(root, evidence):
    sys.path.insert(0, str(root))
    from mcp import Client, StdioServerParameters
    from textual.widgets import Input, OptionList

    import texel
    from texel.__main__ import main
    from texel.editing import merge_range, set_matrix
    from texel.exchange import load_file
    from texel.session import Session
    from texel.ui.app import TexelApp

    assert Path(texel.__file__).resolve().is_relative_to(root)
    evidence.mkdir(parents=True, exist_ok=False)
    results = {"python": sys.executable, "module": texel.__file__, "version": texel.__version__}
    source = evidence / "input.csv"
    source.write_text("n,42\n", encoding="utf-8")
    apps = []
    with patch.object(TexelApp, "run", lambda self, **kwargs: apps.append(self)):
        assert main(["tui", "--workbook", str(source)]) == 0
    app = apps[0]
    assert app.source_path == source
    async with app.run_test(size=(80, 24)) as p:
        await p.press("ctrl+s")
        assert app.screen.query_one("#field-path", Input).value == str(source)
        await p.press("escape")
    results["cli_csv_source_and_save_default"] = True
    app = TexelApp(evidence / "ui.texel", language="en")
    async with app.run_test(size=(80, 24)) as p:
        await p.press("4", "2")
        await p.click("#grid", offset=(26, 3))
        await p.press("7", "enter")
        assert app.session.evaluator.value(0, 0, 0) == 42
        assert app.session.evaluator.value(0, 2, 1) == 7
        results["draft_click"] = {"A1": 42, "B3": 7}
        await p.press("ctrl+p")
        await p.press(*"borders", "enter")
        (evidence / "borders-80.svg").write_text(app.export_screenshot(), encoding="utf-8")
        assert await p.click("#apply", offset=(2, 1))
        assert type(app.screen).__name__ == "Screen"
        assert app.grid.sheet.cell(3, 1).style.borders["top"].style == "thin"
        results["borders_actual_apply_80x24"] = True
        app.session.apply(
            "freeze",
            lambda w: (
                setattr(w.sheet(), "freeze_rows", 1),
                setattr(w.sheet(), "freeze_columns", 1),
            ),
        )
        app.refresh_workbook()
        revision = app.session.revision
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
        assert app.grid.sheet.freeze_columns == app.grid.sheet.freeze_rows == 0
        assert app.session.revision == revision + 1
        assert len(app.screen_stack) == 1
        results["context_tail_mouse_once"] = True
        app.session.apply("merge", lambda w: merge_range(w, 0, "A1:B3", contents="combine"))
        app.refresh_workbook()
        app.grid.move(0, 0)
        await p.press("4", "2", "enter")
        assert app.grid.cursor == (3, 0)
        results["merged_enter"] = "A4"
    invalid = evidence / "zero.texel"
    invalid.write_bytes(b"")
    try:
        load_file(invalid)
    except ValueError:
        pass
    else:
        raise AssertionError("Empty native input was accepted")
    assert invalid.read_bytes() == b""
    results["native_invalid_read_preserved"] = True
    advanced = TexelApp(evidence / "advanced.texel", language="en")
    advanced.session.apply(
        "seed",
        lambda w: set_matrix(w, 0, "A1", [["team", "n"], ["b", "2"], ["a", "1"], ["a", "4"]]),
    )
    async with advanced.run_test(size=(80, 24)) as p:
        await p.press("ctrl+p")
        await p.press(*"advanced_sort", "enter")
        advanced.screen.query_one("#field-sort_column_2").value = "2"
        advanced.screen.query_one("#field-descending_2").value = True
        (evidence / "advanced-sort-80.svg").write_text(
            advanced.export_screenshot(), encoding="utf-8"
        )
        assert await p.click("#apply", offset=(2, 1))
        assert advanced.session.evaluator.value(0, 1, 1) == 4
        await p.press("ctrl+p")
        await p.press(*"advanced_filter", "enter")
        advanced.screen.query_one("#field-criterion_1").value = "a"
        advanced.screen.query_one("#field-filter_column_2").value = "2"
        advanced.screen.query_one("#field-criterion_2").value = ">2"
        assert await p.click("#apply", offset=(2, 1))
        assert advanced.grid._filtered == {2, 3}
        await p.press("ctrl+z")
        assert not advanced.grid._filtered
        advanced.grid.move(0, 2)
        await p.press("=", "A", "1", "f4", "enter")
        assert advanced.session.workbook.sheet().cell(0, 2).raw == "=$A$1"
    results["advanced_sort_filter_f4"] = True
    path = evidence / "mcp.texel"
    arguments = [
        "-c",
        f"import sys; sys.path.insert(0, {str(root)!r}); from texel.__main__ import main; raise SystemExit(main())",
        "mcp",
        "--workbook",
        str(path),
        "--root",
        str(evidence),
    ]
    async with Client(
        StdioServerParameters(command=sys.executable, args=arguments, cwd=str(root))
    ) as client:
        results["mcp_tools"] = len((await client.list_tools()).tools)
        assert results["mcp_tools"] == 39
        written = (
            await client.call_tool(
                "write_range",
                {
                    "sheet": "Sheet1",
                    "start": "A1",
                    "values": [["9007199254740993"], ["9007199254740994"]],
                    "expected_revision": 0,
                },
            )
        ).structured_content
        assert written["ok"]
        filled = (
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
        assert filled["ok"]
        assert Session(path).evaluator.value(0, 2, 0) == 9007199254740995
        undone = (await client.call_tool("undo", {"expected_revision": 2})).structured_content
        assert undone["ok"]
        assert Session(path).evaluator.value(0, 2, 0) is None
        redone = (await client.call_tool("redo", {"expected_revision": 3})).structured_content
        assert redone["ok"]
        results["mcp_series_reopened"] = Session(path).evaluator.value(0, 2, 0)
        s = Session(path)

        def protect(w):
            w.add_sheet("Locked")
            w.sheet(1).protected = True
            set_matrix(w, 1, "A1", [["protected"]])
            w.sheet(1).cell(0, 0).locked = True

        s.apply("seed protected", protect)
        deleted = (
            await client.call_tool(
                "edit_sheet",
                {"action": "delete", "sheet": "Locked", "expected_revision": s.revision},
            )
        ).structured_content
        assert not deleted["ok"]
        assert Session(path).revision == s.revision
        assert Session(path).workbook.sheet("Locked").cell(0, 0).raw == "protected"
        results["mcp_protected_delete_rejected"] = True
        operations = [
            {"op": "format", "sheet": "Sheet1", "range": "A1", "style": {"bold": True}},
            {"op": "note", "sheet": "Sheet1", "cell": "A1", "note": "batch note"},
        ]
        revision = s.revision
        preview = (
            await client.call_tool(
                "preview_operations", {"operations": operations, "expected_revision": revision}
            )
        ).structured_content
        assert preview["ok"] and preview["revision"] == revision and preview["changed_cells"] == 1
        assert Session(path).workbook.sheet().cell(0, 0).note == ""
        applied = (
            await client.call_tool(
                "apply_operations", {"operations": operations, "expected_revision": revision}
            )
        ).structured_content
        assert applied["ok"] and applied["revision"] == revision + 1
        pages = (
            await client.call_tool(
                "read_ranges",
                {
                    "requests": [
                        {"sheet": "Sheet1", "range": "A1"},
                        {"sheet": "Locked", "range": "A1"},
                    ]
                },
            )
        ).structured_content
        assert pages["cell_count"] == 2 and pages["ranges"][0]["rows"][0][0]["note"] == "batch note"
        calculated = (
            await client.call_tool(
                "evaluate_formula", {"sheet": "Sheet1", "formula": "=SUMPRODUCT(A1:A2,A1:A2)"}
            )
        ).structured_content
        assert calculated["value"] == 9007199254740993**2 + 9007199254740994**2
        capabilities = json.loads(
            (await client.read_resource("texel://capabilities")).contents[0].text
        )
        assert capabilities["limits"]["batch_operations"] == 50
        assert len(capabilities["functions"]) == 89
        assert (
            await client.call_tool("undo", {"expected_revision": revision + 1})
        ).structured_content["ok"]
        assert Session(path).workbook.sheet().cell(0, 0).note == ""
        results["mcp_batch_preview_apply_undo"] = True
        results["mcp_read_ranges_and_formula"] = True
        results["formula_functions"] = len(capabilities["functions"])
    (evidence / "result.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(results, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--package-root", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()
    asyncio.run(verify(args.package_root.resolve(), args.evidence.resolve()))


if __name__ == "__main__":
    main()
