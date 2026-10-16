"""프로젝트 내부에만 새 portable 배포 폴더를 만든다."""

import hashlib
import json
import shutil
import subprocess
import zipfile
from datetime import datetime
from pathlib import Path

from texel import __version__

ROOT = Path(__file__).resolve().parents[1]


def main():
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    output = ROOT / "output"
    output.mkdir(exist_ok=True)
    bundle = output / f"Texel-{__version__}-win64-{stamp}"
    bundle.mkdir()  # 기존 디렉터리를 덮어쓰지 않는다.
    runtime = bundle / "python"
    archive = ROOT / ".runtime/downloads/python-3.15.0-embed-amd64.zip"
    with zipfile.ZipFile(archive) as source:
        for name in source.namelist():
            if not (runtime / name).resolve().is_relative_to(runtime.resolve()):
                raise ValueError("Archive path escapes runtime")
        source.extractall(runtime)
    (runtime / "python315._pth").write_text(
        "python315.zip\n.\nLib/site-packages\n..\nimport site\n", encoding="ascii"
    )
    uv = shutil.which("uv")
    if uv is None:
        raise RuntimeError("uv is required for the portable build")
    subprocess.run(
        [
            uv,
            "--cache-dir",
            str(ROOT / ".cache/uv"),
            "pip",
            "install",
            "--python",
            str(runtime / "python.exe"),
            "--target",
            str(runtime / "Lib/site-packages"),
            "--only-binary",
            ":all:",
            "-r",
            str(ROOT / "requirements-runtime.lock"),
        ],
        check=True,
    )
    shutil.copytree(
        ROOT / "texel", bundle / "texel", ignore=shutil.ignore_patterns("__pycache__", "*.pyc")
    )
    for name in (
        "README.md",
        "BUILD_GUIDE.md",
        "CHANGELOG.md",
        "MCP_GUIDE.md",
        "IMPLEMENTATION_SUMMARY.md",
        "spec.md",
        "requirements-runtime.lock",
        "LICENSE",
        "NOTICE",
    ):
        shutil.copy2(ROOT / name, bundle / name)
    (bundle / "Run.cmd").write_text(
        '@echo off\r\ncd /d "%~dp0"\r\n"python\\python.exe" -m texel tui %*\r\n', encoding="ascii"
    )
    (bundle / "Demo.cmd").write_text(
        '@echo off\r\ncd /d "%~dp0"\r\n"python\\python.exe" -m texel tui --demo %*\r\n',
        encoding="ascii",
    )
    (bundle / "MCP.cmd").write_text(
        '@echo off\r\ncd /d "%~dp0"\r\n"python\\python.exe" -m texel mcp %*\r\n', encoding="ascii"
    )
    metadata = {
        "version": __version__,
        "python": "3.15.0",
        "built": stamp,
        "runtime_lock_sha256": hashlib.sha256(
            (ROOT / "requirements-runtime.lock").read_bytes()
        ).hexdigest(),
    }
    (bundle / "build.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    subprocess.run(
        [str(runtime / "python.exe"), "-m", "texel", "--version"], cwd=bundle, check=True
    )
    destination = output / f"{bundle.name}.zip"
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in bundle.rglob("*"):
            if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc":
                archive.write(path, path.relative_to(output))
    print(f"Portable: {bundle}")
    print(f"ZIP: {destination} ({destination.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
