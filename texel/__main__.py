from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path
from uuid import uuid4

from . import __version__


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="texel", description="Texel terminal spreadsheet and MCP analysis tools"
    )
    parser.add_argument("--version", action="version", version=f"Texel {__version__}")
    subparsers = parser.add_subparsers(dest="mode")
    tui = subparsers.add_parser("tui", help="Run the terminal spreadsheet")
    tui.add_argument("--workbook", type=Path, default=Path("data/Workbook.texel"))
    tui.add_argument("--language", choices=["ko", "en"], default="ko")
    tui.add_argument("--demo", action="store_true")
    mcp = subparsers.add_parser("mcp", help="Run a local stdio MCP server")
    mcp.add_argument("--workbook", type=Path, required=True)
    mcp.add_argument("--root", type=Path, required=True)
    arguments = parser.parse_args(argv)
    try:
        if arguments.mode == "mcp":
            from .mcp_server import create_server

            create_server(arguments.workbook.resolve(), arguments.root.resolve()).run(
                transport="stdio"
            )
            return 0
        from .demo import demo_workbook
        from .exchange import load_file, replace_workbook
        from .session import Session
        from .ui.app import TexelApp

        path = arguments.workbook if arguments.mode == "tui" else Path("data/Workbook.texel")
        language = arguments.language if arguments.mode == "tui" else "ko"
        source_path = None
        if arguments.mode == "tui" and arguments.demo:
            path = path.parent / f"Demo-{uuid4().hex[:8]}.texel"
            Session(path).apply("demo", lambda w: replace_workbook(w, demo_workbook()))
        elif path.suffix.lower() != ".texel":
            imported = load_file(path)
            source_path = path.resolve()
            path = path.parent / f"{path.stem}-{uuid4().hex[:8]}.texel"
            Session(path).apply("import", lambda w: replace_workbook(w, imported))
        TexelApp(path, language, source_path=source_path).run(mouse=True)
        return 0
    except (ValueError, OSError, sqlite3.DatabaseError) as exc:
        print(f"Texel: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
