"""공개 릴리스 자산 allowlist와 SHA256 목록을 생성한다."""

import argparse
import hashlib
import sys
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))
    from scripts.check_release import check_release

    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    directory = parser.parse_args().directory
    version = check_release(root)
    files = sorted(directory.iterdir())
    expected = {
        f"texel_tui-{version}-py3-none-any.whl",
        f"texel_tui-{version}.tar.gz",
    }
    names = {path.name for path in files}
    portable = [name for name in names if name.startswith(f"Texel-{version}-win64-")]
    if len(portable) != 1 or not portable[0].endswith(".zip") or names != expected | set(portable):
        raise ValueError(f"Unexpected release assets: {sorted(names)}")
    rows = []
    for path in files:
        with path.open("rb") as stream:
            rows.append(f"{hashlib.file_digest(stream, 'sha256').hexdigest()}  {path.name}\n")
    (directory / "SHA256SUMS.txt").write_text("".join(rows), encoding="ascii")


if __name__ == "__main__":
    main()
