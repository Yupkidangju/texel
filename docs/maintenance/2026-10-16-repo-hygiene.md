# 저장소 위생 및 검증 스코프 교정

작성: 2026-10-16 (Asia/Seoul). 기준 커밋: c5235b9c31d5b06a6a02f4f5d6270911f2bd1aba. 사용자 handoff를 실제 추적 파일/문서/생성 스크립트/도구 설정에 대조했다. 제품 버전0.3.1과 기존 공개 태그/릴리스/Git 이력은 유지한다.

## 판정 및 작업 기준

- Task1 타당: 추적된 pytest 임시 입력280개, 일회성 probe/sweep 입력48개, 설치 검증 생성 입력10개, 구버전 wheel1개를 현재 Git 트리에서 제거한다. Task2 before 복사본3개도 제거한다. 합계342파일/591,761 bytes, 내용 SHA256은101종이다. 이는 저장소 추적 문제이며 제품 코드 결함으로 확대하지 않는다.
- Task3 부분 타당: Ruff 기본 탐색88파일은 제품/테스트/스크립트 Python73 + 문서용 Python14 + 루트 pyproject.toml1이며 문서용 코드에서203개 진단이 발생한다. CI의 명시적 Ruff 명령은 이미73개만 대상으로 한다. pytest 기본 testpaths=[tests]는 이미304개만 수집하여 문서 혼입이 재현되지 않는다. 기본 탐색과 명시적 인자에 따른 범위를 구분한다.
- 기존 생성 probe는 uuid 실행 디렉터리와 입력을 코드로 만들며 제품/테스트/배포 스크립트는 삭제 대상 docs 입력을 사용하지 않는다. 추가 정리 대상 폴더의 직접 서술 문서 참조는 없다. 기존 wheel 보존 문구와 before 경로는 현재 복구 경로를 안내하도록 보완한다.
- 제거는 파일별 경로/해시 목록을 확정한 뒤 Git 추적 파일만 git rm한다. 정규화된 절대 경로가 프로젝트 안인지, symlink/junction/reparse point가 아닌지 확인한다. 사용자 데이터·추적되지 않은 파일·.cache·기존 output은 삭제하지 않는다.
- 원본 audit_report_1.md/feature_matrix_1.md와 결과 JSON/log, 실제 화면 SVG/PNG, 생성 코드 및 변경 patch는 보존한다. *_check 전체를 지우지 않고 CSV/XLSX 등 재생성 입력만 제거한다.
- 삭제 파일은 기존 커밋에서 텍스트를 `git show c5235b9:<기존 경로>`로 조회하거나, 필요한 파일만 `git restore --source=c5235b9 --worktree -- <기존 경로>`로 bytes를 보존해 복구할 수 있다. Git 이력 재작성/기존 v0.3.1 자산 교체는 하지 않는다. 현재 트리의 수정 전 소스 중복은 changes.patch로 단일화한다.
- .gitignore는 요청한 pytest_temp/*_tmp/*_temp/*.whl 및 docs 일회성 생성 폴더/before/검증 입력 재유입을 차단한다.
- Ruff는 texel/tests/scripts의 Python 파일을 include로 고정하고 docs를 force-exclude한다. pytest는 testpaths=[tests]를 유지하고 기존 norecursedirs 기본값에 docs/output을 추가한다. 제품/기존 테스트73파일을 변경하거나 테스트를 skip하지 않는다.

## 순서 및 완료 게이트

1. 파일 목록/기준 해시/복구 커밋 및 현재 Ruff·pytest 수집 결과 기록.
2. ignore/도구 설정·문서 갱신 후 검증된342파일만 제거.
3. git ls-files docs에서 대상0건, 제품/테스트/스크립트73파일 SHA 불변, 원본 감사/화면/결과 보존 확인.
4. Ruff 기본 탐색과 명시 texel/tests/scripts 모두 같은73파일/exit0. pytest 기본 및 루트 명시 수집304개/문서0건, pytest -q 전체 통과. 기본 시스템 임시 위치를 사용한다.
5. 기존 배포물과 별도 output/hygiene-20261016/에 새 로컬 wheel/sdist를 빌드한다. `verify_release.py --artifacts <새 빌드> --evidence <.cache의 새 경로>`와 `verify_distribution.py --package-root <설치본> --evidence <.cache의 새 경로>`를 실행한다. 사용자 지시의 인자 없는 명령은 argparse 필수 인자 누락으로 실행할 수 없으므로 실제 명령을 기록한다.
6. 앞서 승인된 저장소 커밋/푸시 범위에서 교정을 main에 반영하고 기존 CI 결과를 확인한다. 새 버전/태그/릴리스는 만들지 않는다.

새 증거는 명령·종료코드·수집/보존 결과의 요약만 이 문서에 기록하고 작업 로그/설치본/pytest 입력은 .cache 또는 시스템 임시에 둔다. 원본과 개별 제거 파일의 해시는 removal_manifest_20261016.json에 남긴다.

도구 기준: [Ruff include/force-exclude](https://docs.astral.sh/ruff/settings/), [pytest 수집 설정](https://docs.pytest.org/en/stable/reference/reference.html#confval-norecursedirs). pytest norecursedirs를 지정하면 기본값을 대체하므로 기존 기본 패턴을 유지한 채 docs/output을 추가했다.

## 결과

로컬 교정/검증 완료: 2026-10-16. 제품/기존 테스트/배포 스크립트 합계73개 Python 파일의 bytes는 변경하지 않았다. 테스트 파일을 삭제·skip하거나 Ruff 규칙을 완화하지 않았다.

| 검증 | 실제 결과 |
|---|---|
| 제거/ignore | manifest의342파일 모두 현재 추적0건. 모든 제거 경로가 ignore 규칙에 일치. *_tmp/*_temp/pytest_temp/*.whl/before/texel 추적0건 |
| 보존 | 제품/테스트/스크립트73개 포함 기존325파일 SHA256 불변. 기존 서술 문서2개만 복구 안내 추가. 원본 audit_report_1/feature_matrix_1 SHA 불변 |
| Ruff 기본/명시 대상 | 둘 다 동일한 Python73파일. check/format --check 모두 exit0, 73 files already formatted |
| pytest 수집 | 기본 및 루트 명시 모두304 tests, docs 노드0건 |
| pytest -q | **304 passed / 202.32초**, exit0. --basetemp 없이 시스템 임시 경로 사용 |
| 새 로컬 패키지 | output/hygiene-20261016/ wheel/sdist 빌드 exit0. sdist에 old wheel/before/임시 디렉터리0건 |
| verify_distribution | 소스 루트에서 CLI/80×24 UI/MCP stdio,39도구/89함수·batch/undo/보호 경계 통과, exit0 |
| verify_release | 새 wheel/sdist 라이선스·제품 bytes 및 별도 target 설치본의 같은 공개 경로 검사 통과, exit0 |
| 기존 공개판 | v0.3.1 공개 자산4개의 digest가 기존 배포 기록과 동일. 태그/자산/과거 Git 이력은 변경하지 않음 |

```powershell
git status --short
git ls-files docs/
& .\.runtime\python315\python.exe -m ruff check
& .\.runtime\python315\python.exe -m ruff format --check
& .\.runtime\python315\python.exe -m ruff check texel tests scripts
& .\.runtime\python315\python.exe -m ruff format --check texel tests scripts
& .\.runtime\python315\python.exe -m pytest --collect-only -q
& .\.runtime\python315\python.exe -m pytest . --collect-only -q
& .\.runtime\python315\python.exe -m pytest -q
& .\.runtime\python315\python.exe -m hatchling build -d output/hygiene-20261016
& .\.runtime\python315\python.exe scripts/verify_distribution.py --package-root . --evidence .cache/hygiene-source-check
& .\.runtime\python315\python.exe scripts/verify_release.py --artifacts output/hygiene-20261016 --evidence .cache/hygiene-release-check
```

evidence 인자는 실행 시 아직 없는 새 폴더를 사용한다. 위 설치 검증 로그는 .cache/hygiene-source-check.log / hygiene-release-check.log, 전체 테스트와 수집/Ruff/추적 목록은 .cache/hygiene-*.log/txt에 있다. `verify_release`는 내부에서도 별도 설치본을 인자로 verify_distribution을 실행했다. 새 입력/설치본/작업 로그를 docs에 복제하지 않았다.

반영 위치는 main이며 원격 검증 정의는 [.github/workflows/ci.yml](https://github.com/Yupkidangju/texel/blob/main/.github/workflows/ci.yml)이다. 변경 커밋별 원격 결과는 [GitHub CI/Checks](https://github.com/Yupkidangju/texel/actions/workflows/ci.yml)가 원본이며 이 문서의 로컬 결과와 구분한다. 현재 기능/호환성 검증에 새 조건을 추가하지 않았고 별도 버전/태그/릴리스를 만들지 않는다. 기존 공개 태그·소스 배포본 및 과거 커밋에는 당시 파일이 남아 있다. 이는 이력 보존이며 전체 Git 히스토리의 저장 용량을 줄였다는 뜻이 아니다. 무시된 기존 로컬 파일과 사용자 데이터는 건드리지 않았다.
