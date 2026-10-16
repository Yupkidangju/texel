"""제품/패키지/태그/라이선스의 공개 배포 기준을 검사한다."""

import argparse
import ast
import os
import re
import tomllib
from pathlib import Path

COPYRIGHT = "Copyright 2026 yupkidangju@gmail.com"


def check_release(root: Path, tag: str | None = None) -> str:
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    version = project["version"]
    tree = ast.parse((root / "texel/__init__.py").read_text(encoding="utf-8"))
    versions = [
        ast.literal_eval(node.value)
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(isinstance(name, ast.Name) and name.id == "__version__" for name in node.targets)
    ]
    if not re.fullmatch(r"\d+\.\d+\.\d+", version) or versions != [version]:
        raise ValueError("Product and package version mismatch")
    if tag is not None and tag != f"v{version}":
        raise ValueError(f"Release tag must be v{version}, received {tag}")
    if project.get("license") != "Apache-2.0":
        raise ValueError("Expected Apache-2.0 package license")
    for name in ("LICENSE", "NOTICE"):
        if COPYRIGHT not in (root / name).read_text(encoding="utf-8"):
            raise ValueError(f"Missing copyright in {name}")
    return version


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag")
    args = parser.parse_args()
    tag = args.tag
    if tag is None and os.environ.get("GITHUB_REF_TYPE") == "tag":
        tag = os.environ["GITHUB_REF_NAME"]
    print(check_release(Path(__file__).resolve().parents[1], tag))


if __name__ == "__main__":
    main()
