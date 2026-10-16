"""태그와 패키지 메타데이터 불일치의 공개 배포 차단을 검증한다."""

import shutil
import zipfile
from pathlib import Path

import pytest

from scripts.check_portable import check_portable
from scripts.check_release import check_release


@pytest.fixture
def release_tree(tmp_path):
    root = Path(__file__).resolve().parents[1]
    for name in ["pyproject.toml", "texel/__init__.py", "LICENSE", "NOTICE"]:
        destination = tmp_path / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / name, destination)
    return tmp_path


def test_release_accepts_matching_tag(release_tree):
    version = check_release(release_tree)
    assert check_release(release_tree, f"v{version}") == version


def test_release_rejects_wrong_tag(release_tree):
    with pytest.raises(ValueError, match="tag"):
        check_release(release_tree, "v999.0.0")


def test_release_rejects_package_version_drift(release_tree):
    (release_tree / "texel/__init__.py").write_text('__version__ = "999.0.0"\n')
    with pytest.raises(ValueError, match="version"):
        check_release(release_tree)


def test_release_rejects_missing_copyright_notice(release_tree):
    (release_tree / "NOTICE").write_text("Texel\n")
    with pytest.raises(ValueError, match="copyright"):
        check_release(release_tree)


def test_portable_checks_versioned_zip_full_filename(tmp_path):
    root, bundle = tmp_path / "source", tmp_path / "Texel-0.3.1-win64-stamp"
    (root / "texel").mkdir(parents=True)
    (root / "texel/__init__.py").write_text('__version__ = "0.3.1"\n')
    (root / "LICENSE").write_text("license")
    (root / "NOTICE").write_text("notice")
    shutil.copytree(root, bundle)
    with zipfile.ZipFile(tmp_path / f"{bundle.name}.zip", "w") as archive:
        for path in bundle.rglob("*"):
            if path.is_file():
                archive.write(path, path.relative_to(tmp_path))
    assert check_portable(root, bundle) == 3
    (bundle / "texel/__init__.py").write_text("stale source")
    with pytest.raises(AssertionError):
        check_portable(root, bundle)
