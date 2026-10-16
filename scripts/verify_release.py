"""wheel/sdist의 라이선스와 별도 설치본의 공개 경로를 검사한다."""

import argparse
import email
import importlib.util
import json
import shutil
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    sys.path.insert(0, str(ROOT))
    from scripts.check_release import check_release

    parser = argparse.ArgumentParser()
    parser.add_argument("--artifacts", type=Path, default=ROOT / "output")
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()
    version = check_release(ROOT)
    wheel = args.artifacts / f"texel_tui-{version}-py3-none-any.whl"
    sdist = args.artifacts / f"texel_tui-{version}.tar.gz"
    evidence = args.evidence.resolve()
    evidence.mkdir(parents=True, exist_ok=False)
    with zipfile.ZipFile(wheel) as archive:
        prefix = f"texel_tui-{version}.dist-info/"
        metadata = email.message_from_bytes(archive.read(prefix + "METADATA"))
        assert metadata["Version"] == version
        assert metadata["License-Expression"] == "Apache-2.0"
        for name in ("LICENSE", "NOTICE"):
            assert archive.read(prefix + "licenses/" + name) == (ROOT / name).read_bytes()
        for source in (ROOT / "texel").rglob("*.py"):
            assert archive.read(source.relative_to(ROOT).as_posix()) == source.read_bytes()
    with tarfile.open(sdist) as archive:
        for name in ("LICENSE", "NOTICE"):
            member = archive.extractfile(f"texel_tui-{version}/{name}")
            assert member is not None and member.read() == (ROOT / name).read_bytes()
    installed = evidence / "installed"
    if importlib.util.find_spec("pip"):
        installer = [sys.executable, "-m", "pip", "install", "--no-compile"]
    elif uv := shutil.which("uv"):
        installer = [uv, "pip", "install", "--python", sys.executable]
    else:
        raise RuntimeError("Wheel verification requires pip or uv")
    subprocess.run(
        [*installer, "--no-deps", "--target", str(installed), str(wheel.resolve())], check=True
    )
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/verify_distribution.py"),
            "--package-root",
            str(installed),
            "--evidence",
            str(evidence / "public_paths"),
        ],
        check=True,
    )
    (evidence / "package.json").write_text(
        json.dumps({"version": version, "wheel": wheel.name, "sdist": sdist.name}),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
