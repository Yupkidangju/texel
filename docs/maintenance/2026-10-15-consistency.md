# 문서·버전 표기 점검 및 수정

작성: 2026-10-15. 근거: 사용자 제보 7항목, spec.md, IMPLEMENTATION_SUMMARY.md, 실제 소스·배포물. 기존 제품 버전 0.3.0을 유지하는 작은 유지보수 작업이다.

## 판정과 작업 기준

| 항목 | 실제 상태 | 처리 |
|---|---|---|
| 1 현재 버전 모순 | 확인: summary의 현재 0.2.0 문구가 0.3.0 소스와 충돌 | 현재 기준을 0.3.0으로 통일하고 과거 절을 명시 |
| 2 0.1.0 수치 | 당시 69함수/64명령/28도구는 이력이며 현재 수치가 아님 | 역사 절과 각 수치에 0.1.0 당시임을 명시 |
| 3 감사 기능표 | 2026-10-11의 0.2.0 스냅샷: 30도구/69함수 | 원본은 보존. 별도 안내에서 현재 39도구/89함수와 구분 |
| 4 Store 조건식 | Python 우선순위상 제보의 해석이 맞음. 기능 오류 증거 없음 | 기존 의미를 유지하며 괄호와 신규 DB 테이블 목록의 이유를 명시 |
| 5 Google User-Agent | 확인: Texel/0.2 하드코딩 | 패키지 __version__을 참조. 실제 Request 헤더를 검사하는 오프라인 회귀 추가 |
| 6 Git 부재 | 확인: 상위 저장소도 없음 | 로컬 main 저장소 초기화 완료. 첫 커밋 전의 이력 부재는 남음. 원격/푸시/과거 이력 복원은 수행하지 않음 |
| 7 output 혼재 | 확인: 여러 버전·검증 target·중간 후보 공존. 보존 자체는 문제 아님 | 원본 산출물을 유지하고 마지막 검증 배포본의 경로·해시 및 소스와의 관계를 별도 목록으로 안내 |

작업 순서: 기준 기록 → 원본 해시/수정 전 파일 보존 → UA 회귀 RED → 문서/코드 수정 → 회귀·전체 테스트/Ruff → 보존·버전·배포 목록 검증 → 결과 기록.

완료 기준: UA는 중앙 버전과 일치, Store 신규 생성/기존 열기/손상 파일 거부의 기존 검증 유지, 현재/과거 문구 구분, 감사 원본과 기존 wheel/ZIP 해시 불변, 배포 목록의 경로·해시 일치, Git 상태 조회 가능. Git 이력은 첫 커밋 전까지 존재하지 않음을 명시한다.

이번 수정은 네트워크 헤더와 의미 보존 조건식 변경이다. Windows TUI 입력/배포본 실제 입력은 0.3.0 당시 증거로 보존하며 이번 작업에서 재실행한 것으로 주장하지 않는다. 기존 0.3.0 배포물은 수정 전 검증본이므로 수정 후 소스와의 동일성을 주장하지 않는다. 재빌드/버전 증가/외부 배포는 이번 범위에 포함하지 않는다.

Python 3.14+ except 문법, TODO 부재, 미검증 IME/폰트/접근성/장시간/다른 OS 및 계약 밖 Excel 기능은 새 결함으로 취급하지 않는다. 원본 감사 보고서·기능표·기존 검증 결과는 덮어쓰지 않는다.

## 검증 결과

완료: 2026-10-15 (Asia/Seoul). Python 3.15.0, 제품 버전 0.3.0 유지. 아래 명령은 프로젝트 루트에서 실행했다. 로그는 [evidence_consistency_20261015](evidence_consistency_20261015/)에 보존한다.

| 검증 | 결과 | 증거 |
|---|---|---|
| UA 회귀 RED | 실제 Request의 Texel/0.2 ≠ Texel/0.3.0으로 1 failed | ua_red.log |
| UA/Google/Store/native 경계 회귀 | 76 passed / 128.37초 | focused_green.log |
| 전체 suite | **299 passed / 184.47초**, exit 0 | full.log |
| Ruff check | All checks passed, exit 0 | ruff_check.log |
| Ruff format --check | **68 files already formatted**, exit 0 | ruff_format.log |
| 현재 계약·기능 수 | pyproject와 패키지 0.3.0 일치, 실행한 MCP 서버 목록 39개, 계산 registry 89개 | preservation_and_metadata.json |
| 문서 | 현재 제품 0.2.0 문구 제거, 0.1.0 당시 수치 명시, 배포 경로/크기/해시와 로컬 링크 확인 | document_checks.json |
| 원본·배포물 보존 | audit_report_1/feature_matrix_1 및 기존 0.3.0 wheel/ZIP SHA256 불변 | baseline.json, preservation_and_metadata.json |
| 배포본과 수정 소스 구분 | wheel/ZIP 각각 37모듈 중 35개 동일. google_sheets.py/store.py만 이번 수정으로 다름 | source_vs_last_release.json |
| Git | 루트 C:/LocalDev/python/Texel, main, 원격 없음, 커밋 없음. status와 runtime/output/.env/cache ignore 확인 | git_status.log, preservation_and_metadata.json |

```powershell
& .\.runtime\python315\python.exe -m pytest tests/test_version_metadata.py tests/test_legacy_import.py tests/test_store.py tests/test_audit_1_boundaries.py -q --basetemp .cache/pytest-consistency-focused
& .\.runtime\python315\python.exe -m pytest -q --basetemp .cache/pytest-consistency-full
& .\.runtime\python315\python.exe -m ruff check texel tests scripts
& .\.runtime\python315\python.exe -m ruff format --check texel tests scripts
```

수정 파일: IMPLEMENTATION_SUMMARY.md, spec.md, README.md, BUILD_GUIDE.md, CHANGELOG.md, texel/google_sheets.py, texel/store.py. 추가: tests/test_version_metadata.py, docs/distributions.md, 이 작업 기록/증거, output/README.md와 로컬 .git 메타데이터. 수정 전 summary/제품 2파일과 diff는 before/ 및 changes.patch에 보존한다. 원래 감사 기능표의 30도구/69함수는 당시 값이므로 고치지 않았다.

잔여 범위: Git 첫 커밋이 없어 파일은 아직 untracked이며 과거 이력/되돌리기는 생기지 않았다. AGENTS.md의 명시적 커밋 요청 경계에 따라 커밋은 수행하지 않았다. 이번 수정은 Unreleased이며 재빌드/새 버전/외부 배포를 수행하지 않았다. 기존 Windows 실제 입력·portable 실행 증거는 0.3.0 배포 시점 기록이고 이번 수정 후 재실행 결과가 아니다. 사람의 IME/폰트/접근성/장시간, Linux/macOS 실제 터미널 한계는 그대로다. 과거 이력과 미검증 항목을 완료로 승격하지 않는다.
