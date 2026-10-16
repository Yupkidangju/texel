Texel is a local terminal spreadsheet and MCP server: 89 formula functions and 39 revision-safe MCP tools.

Install Python 3.14 or newer, then install this release's `texel_tui-<version>-py3-none-any.whl` asset with `python -m pip install <wheel>`. Run `texel tui --demo` or configure `texel mcp --workbook <file.texel> --root <folder>` in your MCP host.

Use `requirements-runtime.lock` from this release tag as pip constraints (`python -m pip install -c requirements-runtime.lock <wheel>`) to reproduce the transitive dependency versions tested in CI.

The common wheel is tested on Windows x64 and Linux/macOS x64 and ARM64. Windows 11 ARM64 is tested with x64 Python under OS emulation; native Windows ARM64 is not supported because a required dependency has no native wheel. The Windows x64 portable ZIP also includes Python and runtime dependencies; extract it and run Run.cmd or Demo.cmd. The other platforms require an installed Python runtime. Initial dependency installation requires internet; local workbooks operate offline afterward.

Changes for this version are listed in CHANGELOG.md at the release tag. Licensed under Apache-2.0. Copyright 2026 yupkidangju@gmail.com.

macOS Intel requires building the pinned cryptography dependency from source. Install Xcode Command Line Tools, Rust and OpenSSL first (`xcode-select --install`, `brew install rust openssl@3`). Set `OPENSSL_DIR` to `brew --prefix openssl@3` if needed. The Intel CI runner built this dependency before running the full tests. See https://cryptography.io/en/latest/installation/#building-cryptography-on-macos.

SHA256SUMS.txt covers the wheel, source distribution and portable ZIP. Human IME/font/accessibility hardware and long-duration testing remain outside the automated CI evidence. See README and CHANGELOG for scope and limitations.

The portable ZIP is validated on Windows x64. Windows ARM64 validation covers the common wheel running in x64 Python emulation.
