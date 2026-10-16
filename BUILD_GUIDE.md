# 설치와 빌드

## 공통 설치와 자동 배포

Windows11 ARM64는 x64 Python/portable 에뮬레이션 경로를 사용합니다. Windows ARM64 네이티브는 cryptography의 공식 wheel 부재로 지원하지 않습니다. Linux/macOS ARM64는 네이티브 CI 대상입니다.

Python 3.14+가 있는 Windows/Linux/macOS x64·ARM64에서는 Release의 공통 wheel을 `python -m pip install <wheel>`로 설치합니다. Windows x64 portable만 Python 런타임을 포함합니다. 잠금 파일은 pywin32를 Windows로 제한하며 제품/개발 버전은 동일하게 고정합니다. 소스 개발은 `python -m pip install -r requirements.lock`, `python -m pytest -q`, `python -m ruff check texel tests scripts`, `python -m hatchling build`로 수행할 수 있습니다.

main push/PR은 .github/workflows/ci.yml의 7환경 검증을 실행합니다. 버전 상수·pyproject·CHANGELOG를 동기화하고 `vX.Y.Z` 태그를 push하면 release.yml이 동일 CI와 Windows portable의 전체 검사/설치본 검증을 거쳐 wheel/sdist/portable/SHA256SUMS.txt를 GitHub Release에 게시합니다. PyPI 게시나 추가 비밀 키는 필요하지 않습니다. 태그 버전이 패키지와 다르면 차단하며 기존 태그/릴리스를 덮어쓰지 않습니다. 실패 시 로그를 확인해 수정한 뒤 새 검증을 수행합니다. 정확한 결과는 docs/releases/0.3.1-results.md를 참고하세요.

## Windows 개발 환경

Windows x64, PowerShell, uv가 필요합니다. 기존 Python 설치를 변경하지 않고 공식 Python 3.15.0 embeddable ZIP을 `.runtime/python315`에 압축 해제합니다. 배포 ZIP SHA256은 prepare.ps1에서 검증합니다. 최초 준비에는 Python/PyPI 다운로드를 위한 네트워크가 필요합니다.

```powershell
.\prepare.ps1 -Dev
.\test.ps1
.\run.ps1 -Demo
.\build.ps1
```

`requirements.lock`은 개발+제품, `requirements-runtime.lock`은 배포용 고정 의존성입니다. `prepare.ps1`은 Lib/site-packages에 설치해 Python site 모듈이 pywin32의 .pth를 정상 처리하도록 합니다. 이 규칙을 바꾸면 Windows MCP의 pywintypes import가 실패할 수 있습니다.

`test.ps1`은 Python 3.15에서 pytest와 Ruff 검사/형식 확인을 실행합니다. `build.ps1`은 기본적으로 검증한 뒤 root `output/`에 wheel 및 타임스탬프가 붙은 Windows x64 portable 폴더/ZIP을 만듭니다. 기존 배포 폴더를 삭제하거나 덮어쓰지 않습니다. 검증을 이미 수행한 작업 단위에서만 `-SkipTests`를 사용합니다.

0.2.1 감사 수정 검증은 `tests/test_audit_1_regressions.py`, `tests/test_audit_1_boundaries.py`를 전체 suite에 포함합니다. 설치본의 경로/80×24 UI/실제 MCP stdio 검증은 다음과 같이 실행할 수 있습니다. evidence는 아직 없는 새 폴더를 지정합니다.

```powershell
& .\output\Texel-0.2.1-win64-<timestamp>\python\python.exe scripts\verify_distribution.py --package-root .\output\Texel-0.2.1-win64-<timestamp> --evidence .\docs\audit\evidence_remediation_1\portable_check
```

실행한 정확한 경로·결과와 Windows ConPTY 입력 기록은 `docs/audit/remediation_results_1.md`를 참고하세요. 설치본 검증과 사람의 IME/화면/장시간 검증은 구분합니다.

## 배포와 MCP

마지막 검증 배포본은 [배포 목록](docs/distributions.md)의 명시적 경로와 해시로 식별합니다. `output/`의 최신 수정 시각이나 공용 JSON 파일만으로 선택하지 마세요. 과거 배포물·실패 후보·wheel-check 설치 폴더를 보존하며, 배포 후 유지보수 소스는 재빌드 전까지 기존 배포물과 같다고 간주하지 않습니다.

0.3.0은 입력 스키마에 기존 runtime lock의 Pydantic 2.14.0을 직접 사용합니다. 추가 다운로드 버전 변경 없이 pyproject의 직접 의존성으로 명시했습니다. `scripts/verify_distribution.py`는 39개 도구, 원자적 batch/preview·다중 범위·추가 함수까지 검사합니다. 0.3.0의 현재 검증 기록은 `docs/upgrades/0.3.0-results.md`입니다.

Portable 폴더: `python/python.exe`, `texel/`, `Run.cmd`, `Demo.cmd`, `MCP.cmd`, 문서, build.json. `Run.cmd`는 기본 data/Workbook.texel을 생성하고, `Demo.cmd`는 기존 데이터를 바꾸지 않는 새 예제 문서를 만듭니다.

```powershell
.\python\python.exe -m texel --version
.\python\python.exe -m texel mcp --workbook .\data\analysis.texel --root .\data
```

MCP 호스트의 command는 portable 폴더의 Python 절대 경로, args는 위 인자로 설정합니다. 통합 문서/루트는 절대 경로를 권장합니다. MCP 등록 파일을 사용자의 전역 설정에 자동으로 쓰지 않습니다.

## 일반 Python 설치

Python 3.14 이상에서 `python -m pip install .` 후 `texel tui` / `texel mcp ...`로 실행할 수도 있습니다. Linux/macOS는 wheel의 동일 코드로 사용할 수 있으나 Windows에서 수행한 검증을 해당 OS의 실제 터미널 검증으로 간주하지 않습니다.

## 변경 이력 관리

2026-10-15에 프로젝트 루트의 로컬 Git 저장소를 main 브랜치로 초기화했습니다. 첫 커밋과 원격은 없으므로 현재 파일은 아직 추적되지 않으며 과거 이력 조회·되돌리기를 제공하지 않습니다. 커밋/푸시/태그는 사용자의 명시적 요청에 따라 수행합니다. 기존 .gitignore가 runtime/cache/output/data/.env를 제외합니다. 이번 수정 전 파일·diff·보존 해시는 docs/maintenance/evidence_consistency_20261015/에 있습니다.

## 복구

0.2.0은 xlrd 2.0.2로 XLS를 읽습니다. 개발 fixture 생성용 xlwt 1.3.0은 portable 런타임에 포함하지 않습니다. Google 공개 GSHEET 가져오기는 Python 표준 HTTPS 클라이언트로 수행하고 docs.google.com/Google 다운로드 호스트만 허용합니다. 별도 API 키/Google 로그인을 설치하지 않습니다. 오프라인에서는 내려받은 XLSX/CSV를 이용하세요.

`.texel`은 SQLite입니다. 실행 중 파일을 임의로 복사하거나 같은 경로로 교체하지 말고 앱/MCP 백업을 이용하세요. CSV/XLSX 가져오기는 원본을 바꾸지 않고 native 파일을 만듭니다. 오류 시 모달 입력/수식 draft를 보존하고 revision 충돌 시 최신 데이터를 다시 확인합니다. 미확정 수식 draft는 자동 저장 대상이 아니며 Enter로 확정합니다.
