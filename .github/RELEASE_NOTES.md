Texel is a local terminal spreadsheet and MCP server: 89 formula functions and 39 revision-safe MCP tools.

Install Python 3.14 or newer, then install this release's `texel_tui-<version>-py3-none-any.whl` asset with `python -m pip install <wheel>`. Run `texel tui --demo` or configure `texel mcp --workbook <file.texel> --root <folder>` in your MCP host.

The common wheel is tested on Windows x64 and Linux/macOS x64 and ARM64. Windows 11 ARM64 is tested with x64 Python under OS emulation; native Windows ARM64 is not supported because a required dependency has no native wheel. The Windows x64 portable ZIP also includes Python and runtime dependencies; extract it and run Run.cmd or Demo.cmd. The other platforms require an installed Python runtime. Initial dependency installation requires internet; local workbooks operate offline afterward.

Changes for this version are listed in CHANGELOG.md at the release tag. Licensed under Apache-2.0. Copyright 2026 yupkidangju@gmail.com.

SHA256SUMS.txt covers the wheel, source distribution and portable ZIP. Human IME/font/accessibility hardware and long-duration testing remain outside the automated CI evidence. See README and CHANGELOG for scope and limitations.
