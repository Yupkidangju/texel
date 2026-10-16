import sys

import pytest
from mcp import Client, StdioServerParameters

from texel.mcp_server import create_server
from texel.session import Session


@pytest.mark.asyncio
async def test_mcp_in_memory_tools_conflict_and_analysis(tmp_path):
    path = tmp_path / "mcp.texel"
    server = create_server(path, tmp_path)
    async with Client(server) as client:
        listed = await client.list_tools()
        assert {"workbook_info", "read_range", "write_range", "profile_range", "pivot_table"} <= {
            t.name for t in listed.tools
        }
        info = (await client.call_tool("workbook_info", {})).structured_content
        assert info["revision"] == 0
        written = (
            await client.call_tool(
                "write_range",
                {
                    "sheet": "Sheet1",
                    "start": "A1",
                    "values": [["group", "n"], ["a", "10"], ["a", "=B2*2"]],
                    "expected_revision": 0,
                },
            )
        ).structured_content
        assert written["ok"] and written["revision"] == 1
        stale = (
            await client.call_tool(
                "write_range",
                {"sheet": "Sheet1", "start": "A1", "values": [["lost"]], "expected_revision": 0},
            )
        ).structured_content
        assert not stale["ok"] and stale["error"]["code"] == "conflict"
        profile = (
            await client.call_tool("profile_range", {"sheet": "Sheet1", "range": "A1:B3"})
        ).structured_content
        assert profile["profile"]["columns"][1]["sum"] == 30
        pivot = (
            await client.call_tool(
                "pivot_table",
                {
                    "sheet": "Sheet1",
                    "range": "A1:B3",
                    "key_columns": [0],
                    "value_column": 1,
                    "name": "Pivot",
                    "expected_revision": 1,
                },
            )
        ).structured_content
        assert pivot["ok"] and Session(path).evaluator.value(1, 1, 1) == 30
        scoped = (
            await client.call_tool("export_file", {"path": "../escape.csv"})
        ).structured_content
        assert not scoped["ok"]


@pytest.mark.asyncio
async def test_stdio_real_subprocess_and_shared_store(tmp_path):
    path = tmp_path / "stdio.texel"
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "texel", "mcp", "--workbook", str(path), "--root", str(tmp_path)],
    )
    async with Client(params) as client:
        result = await client.call_tool(
            "write_range",
            {"sheet": "Sheet1", "start": "A1", "values": [["40", "=A1+2"]], "expected_revision": 0},
        )
        assert result.structured_content["ok"]
        read = (
            await client.call_tool("read_range", {"sheet": "Sheet1", "range": "A1:B1"})
        ).structured_content
        assert read["rows"][0][1]["value"] == 42
        assert Session(path).evaluator.value(0, 0, 1) == 42
        resource = await client.read_resource("texel://workbook")
        assert "revision" in resource.contents[0].text


@pytest.mark.asyncio
async def test_paging_and_failed_batch_are_bounded(tmp_path):
    server = create_server(tmp_path / "bounds.texel", tmp_path)
    async with Client(server) as client:
        page = (
            await client.call_tool(
                "read_range", {"sheet": "Sheet1", "range": "A1:ZZ1000", "limit": 200}
            )
        ).structured_content
        assert sum(map(len, page["rows"])) <= 2000
        bad = (
            await client.call_tool(
                "write_range",
                {
                    "sheet": "Sheet1",
                    "start": "XFD1",
                    "values": [["1", "2"]],
                    "expected_revision": 0,
                },
            )
        ).structured_content
        assert not bad["ok"] and bad["revision"] == 0
