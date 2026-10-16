import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from texel.ui.app import TexelApp
from textual.widgets import OptionList


async def main():
    async def watchdog():
        await asyncio.sleep(5)
        for task in asyncio.all_tasks():
            print(task, flush=True)
            task.print_stack(limit=3)
            coro = task.get_coro()
            while coro is not None:
                print("AWAIT", repr(coro), flush=True)
                coro = getattr(coro, "cr_await", getattr(coro, "gi_yieldfrom", None))
    asyncio.create_task(watchdog())
    app = TexelApp(Path(__file__).parent / "debug_context.texel", language="en")
    app.session.apply("freeze", lambda w: (setattr(w.sheet(), "freeze_rows", 1), setattr(w.sheet(), "freeze_columns", 1)))
    print("start", flush=True)
    async with app.run_test(size=(80, 24)) as p:
        print("mounted", flush=True)
        await p.click("#grid", offset=(12, 1), button=3)
        print("clicked", flush=True)
        await p.press("end")
        print("end", flush=True)
        await p.pause()
        options = app.screen.query_one(OptionList)
        print(options.region, options.scroll_y, options.highlighted, flush=True)
        line = options._line_cache.index_to_line[options.highlighted]
        await p.click(offset=(options.content_region.x + 2, options.content_region.y + line - int(options.scroll_y)))
        print("selected", type(app.screen).__name__, flush=True)
    print("done", flush=True)


asyncio.run(asyncio.wait_for(main(), 15))
