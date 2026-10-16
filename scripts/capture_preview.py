"""색상 지원 헤드리스 화면의 SVG를 만든다. 실제 화면/IME 검증과 구분한다."""

import asyncio
import os
from pathlib import Path

from texel.demo import demo_workbook
from texel.exchange import replace_workbook
from texel.session import Session
from texel.ui.app import TexelApp

ROOT = Path(__file__).resolve().parents[1]


async def main():
    os.environ.pop("NO_COLOR", None)
    output = ROOT / "output"
    output.mkdir(exist_ok=True)
    path = ROOT / ".cache/preview.texel"
    session = Session(path)
    session.apply("preview fixture", lambda w: replace_workbook(w, demo_workbook()))
    app = TexelApp(path)
    async with app.run_test(size=(120, 36)) as pilot:
        await pilot.pause()
        app.grid.move(1, 5)
        for mode in ("dark", "light", "contrast"):
            await pilot.pause()
            (output / f"preview-{mode}.svg").write_text(
                app.export_screenshot(title=f"Texel · {mode}"), encoding="utf-8"
            )
            app.run_command("theme")
        app.sheet_index = 2
        app.grid.cursor = app.grid.anchor = (0, 0)
        app.grid.top = app.grid.left = 0
        app.refresh_workbook()
        await pilot.pause()
        app.tabs.active = "sheet-2"
        (output / "preview-formatting.svg").write_text(
            app.export_screenshot(title="Texel · cell formatting"), encoding="utf-8"
        )
        await pilot.click("#grid", offset=(12, 2), button=3)
        await pilot.pause()
        (output / "preview-context.svg").write_text(
            app.export_screenshot(title="Texel · context menu"), encoding="utf-8"
        )
    print("Color-enabled headless SVG previews saved to output/preview-*.svg")


if __name__ == "__main__":
    asyncio.run(main())
