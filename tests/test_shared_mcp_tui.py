import sys

import pytest
from mcp import Client, StdioServerParameters

from texel.ui.app import TexelApp


@pytest.mark.asyncio
async def test_actual_mcp_write_becomes_visible_in_running_tui(tmp_path):
    path = tmp_path / "both.texel"
    app = TexelApp(path)
    async with app.run_test(size=(100, 30)) as pilot:
        async with Client(
            StdioServerParameters(
                command=sys.executable,
                args=["-m", "texel", "mcp", "--workbook", str(path), "--root", str(tmp_path)],
            )
        ) as client:
            result = await client.call_tool(
                "write_range",
                {"sheet": "Sheet1", "start": "A1", "values": [["=6*7"]], "expected_revision": 0},
            )
            assert result.structured_content["ok"]
            app.poll_external()
            await pilot.pause()
            assert app.formula_input.value == "=6*7"
            assert app.session.evaluator.value(0, 0, 0) == 42
            assert "42" in app.grid.render_line(1).text
