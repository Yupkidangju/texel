import json
import sys

from mcp import Client, StdioServerParameters

from texel.mcp_server import create_server
from texel.session import Session
from texel.ui.app import TexelApp


async def test_new_tool_schema_preview_partial_format_and_multi_read(tmp_path):
    path = tmp_path / "tools.texel"
    async with Client(create_server(path, tmp_path)) as client:
        tools = (await client.list_tools()).tools
        assert len(tools) == 39
        resource = await client.read_resource("texel://capabilities")
        assert json.loads(resource.contents[0].text)["limits"]["batch_operations"] == 50
        prompt = await client.get_prompt("plan_changes", {"sheet": "Sheet1", "range": "A1:B2"})
        assert "preview_operations" in prompt.messages[0].content.text
        lookup = {t.name: t for t in tools}
        assert lookup["preview_operations"].annotations.read_only_hint
        assert lookup["apply_operations"].annotations.destructive_hint
        schema = lookup["apply_operations"].input_schema
        assert "expected_revision" in schema["required"]
        operations = [
            {
                "op": "write",
                "sheet": "Sheet1",
                "start": "A1",
                "values": [["team", "n"], ["a", "2"], ["b", "3"]],
            }
        ]
        preview = (
            await client.call_tool(
                "preview_operations", {"operations": operations, "expected_revision": 0}
            )
        ).structured_content
        assert preview["ok"] and preview["revision"] == 0 and preview["changed_cells"] == 6
        assert Session(path).revision == 0
        written = (
            await client.call_tool(
                "apply_operations", {"operations": operations, "expected_revision": 0}
            )
        ).structured_content
        assert written["ok"] and written["revision"] == 1
        formatted = (
            await client.call_tool(
                "patch_format",
                {
                    "sheet": "Sheet1",
                    "range": "A1:B1",
                    "style": {"bold": True, "background": "#123456"},
                    "expected_revision": 1,
                },
            )
        ).structured_content
        assert formatted["ok"]
        formatted = (
            await client.call_tool(
                "patch_format",
                {
                    "sheet": "Sheet1",
                    "range": "A1:B1",
                    "style": {"italic": True},
                    "expected_revision": 2,
                },
            )
        ).structured_content
        assert formatted["ok"]
        read = (
            await client.call_tool(
                "read_ranges",
                {
                    "requests": [
                        {"sheet": "Sheet1", "range": "A1:B1"},
                        {"sheet": "Sheet1", "range": "B2:B3"},
                    ]
                },
            )
        ).structured_content
        assert read["ok"] and read["revision"] == 3 and read["cell_count"] == 4
        assert read["ranges"][0]["rows"][0][0]["style"]["bold"]
        bad = (
            await client.call_tool(
                "read_ranges",
                {
                    "requests": [
                        {"sheet": "Sheet1", "range": "A1:B2000", "limit": 2000},
                        {"sheet": "Sheet1", "range": "A1"},
                    ]
                },
            )
        ).structured_content
        assert not bad["ok"]
        result = (
            await client.call_tool(
                "evaluate_formula", {"sheet": "Sheet1", "formula": "=SUMPRODUCT(B2:B3,B2:B3)"}
            )
        ).structured_content
        assert result["ok"] and result["value"] == 13 and result["revision"] == 3
        search = (
            await client.call_tool("search_cells", {"query": "a", "whole_cell": True})
        ).structured_content
        assert search["total"] == 1


async def test_stdio_batch_sort_filter_diagnostics_and_tui_observation(tmp_path):
    path = tmp_path / "shared.texel"
    app = TexelApp(path)
    async with app.run_test(size=(80, 24)) as pilot:
        async with Client(
            StdioServerParameters(
                command=sys.executable,
                args=["-m", "texel", "mcp", "--workbook", str(path), "--root", str(tmp_path)],
            )
        ) as client:
            ops = [
                {
                    "op": "write",
                    "sheet": "Sheet1",
                    "start": "A1",
                    "values": [["team", "n", "calc"], ["b", "2", "=B2*2"], ["a", "3", "=B3*2"]],
                },
                {"op": "sort", "sheet": "Sheet1", "range": "A1:C3", "keys": [{"column": 0}]},
            ]
            result = (
                await client.call_tool(
                    "apply_operations", {"operations": ops, "expected_revision": 0}
                )
            ).structured_content
            assert result["ok"] and result["revision"] == 1
            app.poll_external()
            await pilot.pause()
            assert app.session.evaluator.value(0, 1, 0) == "a"
            assert app.session.evaluator.value(0, 1, 2) == 6
            trace = (
                await client.call_tool("trace_dependencies", {"sheet": "Sheet1", "cell": "C2"})
            ).structured_content
            assert trace["precedents"] == [{"sheet": "Sheet1", "range": "B2"}]
            filtered = (
                await client.call_tool(
                    "filter_table",
                    {
                        "sheet": "Sheet1",
                        "range": "A1:C3",
                        "conditions": [{"column": 1, "criterion": ">2"}],
                        "expected_revision": 1,
                    },
                )
            ).structured_content
            assert filtered["ok"]
            app.poll_external()
            await pilot.pause()
            assert 2 in app.grid._filtered
            conflict = (
                await client.call_tool(
                    "apply_operations", {"operations": ops, "expected_revision": 0}
                )
            ).structured_content
            assert not conflict["ok"] and conflict["error"]["code"] == "conflict"
            assert (await client.call_tool("undo", {"expected_revision": 2})).structured_content[
                "ok"
            ]
            assert (await client.call_tool("undo", {"expected_revision": 3})).structured_content[
                "ok"
            ]
            assert Session(path).workbook.sheet().cell(0, 0).raw == ""


async def test_invalid_batch_schema_and_failure_location(tmp_path):
    path = tmp_path / "failure.texel"
    async with Client(create_server(path, tmp_path)) as client:
        result = (
            await client.call_tool(
                "apply_operations",
                {
                    "operations": [
                        {"op": "write", "sheet": "Sheet1", "start": "A1", "values": [["first"]]},
                        {"op": "clear", "sheet": "Missing", "range": "A1"},
                    ],
                    "expected_revision": 0,
                },
            )
        ).structured_content
        assert not result["ok"] and result["error"]["operation_index"] == 1
        assert Session(path).revision == 0
        invalid = await client.call_tool(
            "apply_operations",
            {"operations": [{"op": "shell", "sheet": "Sheet1"}], "expected_revision": 0},
        )
        assert invalid.is_error
        assert Session(path).revision == 0
