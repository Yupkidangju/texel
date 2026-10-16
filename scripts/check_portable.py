"""선택한 portable 및 ZIP이 현재 제품 소스/라이선스와 같은지 검사한다."""

import argparse
import zipfile
from pathlib import Path


def check_portable(root: Path, bundle: Path) -> int:
    with zipfile.ZipFile(bundle.parent / f"{bundle.name}.zip") as archive:
        files = [*sorted((root / "texel").rglob("*.py")), root / "LICENSE", root / "NOTICE"]
        for source in files:
            relative = source.relative_to(root)
            assert (bundle / relative).read_bytes() == source.read_bytes(), relative
            assert archive.read(f"{bundle.name}/{relative.as_posix()}") == source.read_bytes()
    return len(files)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", type=Path, required=True)
    bundle = parser.parse_args().bundle.resolve()
    count = check_portable(Path(__file__).resolve().parents[1], bundle)
    print(f"Verified {count} source/license files in portable and ZIP")


if __name__ == "__main__":
    main()
