"""100,000셀을 한 환경에서 측정한다. 성능 보장값으로 사용하지 않는다."""

import asyncio
import json
from pathlib import Path
from time import perf_counter

from texel.analysis import profile_range
from texel.exchange import replace_workbook
from texel.model import Workbook
from texel.session import Session
from texel.ui.app import TexelApp

ROOT = Path(__file__).resolve().parents[1]


async def main():
    timings = {}
    source = Workbook()
    for r in range(10000):
        for c in range(10):
            source.sheet().set_raw(r, c, str(r * 10 + c))
    path = ROOT / ".cache/benchmark.texel"
    session = Session(path)
    started = perf_counter()
    session.apply("benchmark fixture", lambda w: replace_workbook(w, source))
    timings["native_write_seconds"] = perf_counter() - started
    started = perf_counter()
    session.reload()
    timings["native_load_seconds"] = perf_counter() - started
    started = perf_counter()
    profile = profile_range(session.workbook, 0, "A1:J10000", header=False)
    timings["profile_seconds"] = perf_counter() - started
    assert sum(column["sum"] for column in profile["columns"]) == 4999950000
    app = TexelApp(path)
    started = perf_counter()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        timings["headless_start_seconds"] = perf_counter() - started
        started = perf_counter()
        app.grid.move(9999, 9)
        await pilot.pause()
        timings["headless_jump_seconds"] = perf_counter() - started
        assert app.session.evaluator.value(0, 9999, 9) == 99999
    report = {
        "python": "3.15.0",
        "rows": 10000,
        "columns": 10,
        "stored_cells": 100000,
        "verified_sum": 4999950000,
        "timings": timings,
        "scope": "single Windows machine, synthetic numeric data, headless UI; not a human/device/soak claim",
    }
    output = ROOT / "output"
    output.mkdir(exist_ok=True)
    (output / "benchmark.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
