# 구현 및 검증 기록

2026-10-10 시작. 기준: spec.md, designs.md, implementation_plan.md.

## 현재 상태

현재 제품은 **Texel 0.3.1**이며 **89개 함수 / MCP 39개 도구**를 제공한다. 공개 저장소·라이선스·교차 플랫폼 CI·태그 릴리스는 [0.3.1 계획](docs/releases/0.3.1-plan.md)과 [결과](docs/releases/0.3.1-results.md)를 따른다. 현재 배포 경로는 [배포 목록](docs/distributions.md)에 구분한다.

공개 GitHub Yupkidangju/texel 및 Apache-2.0, v0.3.1 자동 릴리스 완료. 태그 CI7환경 각각304개와 Windows portable 자체 Python3.15 전체304개/Ruff·설치본 검증을 통과했다. 공개 파일 다운로드 해시 및 제품37개 Git 태그 bytes 일치, 실제 Windows 공개 portable ConPTY42+Enter 저장/정상 종료를 확인했다. Windows ARM64는 x64 Python wheel 에뮬레이션, Mac Intel은 Xcode/Rust/OpenSSL 전제를 명시한다. 자세한 범위와 NOTICE 개행 차이는 위 결과를 따른다.

0.3.0 배포 후 2026-10-15 유지보수 당시 검증은 전체 **299 passed / 184.47초**, Ruff check/format **68 files already formatted**였다. 당시 원본 감사·기능표·기존 wheel/ZIP 해시를 보존했고 Git 첫 커밋/재빌드는 수행하지 않았다. 그 시점의 원본 기록은 [유지보수 결과](docs/maintenance/2026-10-15-consistency.md)에 보존한다. 이후 0.3.1의 새 커밋/빌드/게시 결과는 위 공개 배포 결과 문서를 기준으로 한다.

### 0.3.0 기본 기능 고도화 — 2026-10-15

기능 구현 기준은 `docs/upgrades/0.3.0-plan.md` F1~F5, 0.3.0 배포 시점 결과는 `docs/upgrades/0.3.0-results.md`이다. 아래 0.2.x 기록은 당시 이력으로 보존한다.

- 계산 함수20개 추가(89개), 정밀 조건 비교/shape·오류 정책, 다중 키 정렬·복합 필터·통합 검색, 직접 수식 진단과 읽기 전용 표현식 평가.
- MCP9개 추가(39개), typed 입력/부분 서식/단일 스냅샷 다중 조회, 같은 Session 후보 검증을 사용하는 preview/apply. 최대50작업/10,000셀, 하나의 revision·undo, 실패 전체 원복.
- TUI 다중 정렬/복합 필터/검색·진단 모달, Ctrl 데이터 경계 이동·선택, F4 참조 전환, 전체 행/열 선택. 빠른 Tab 필드 전환도 실제 입력에서 검증했다. 데모에 ‘업무 함수’ 시트를 추가했다.
- 0.3.0 배포 당시 전체 **298 passed / 187.37초**, Ruff check/format **67 files already formatted**. 로그: `docs/upgrades/evidence_0_3_0/full_verified.log`, `ruff_check.log`, `ruff_format.log`.
- 소스 ConPTY80×24: Ctrl+Right→D1, F4 원문 `=$B$2`, SUMPRODUCT110, 실제 마우스 정렬 적용, 두 조건 AND 필터 입력/적용·숨김{1,3}, 각각 undo·정상 종료 exit0. 자동 입력과 사람의 IME/폰트/장시간은 구분한다.
- 별도 읽기 전용 리뷰3건을4개 RED회귀와 관련89개 GREEN으로 수정했다. 이후 표현식 문맥/실제 Tab 입력에서 드러난 경계는 추가 회귀와 실제 입력으로 닫았다. 재리뷰/독립 정식 감사 PASS를 주장하지 않는다.
- 새 제품 모듈: criteria/function_extensions/tables/diagnostics/navigation/operations/query/mcp_extensions/ui.advanced. 기존 Session/Store의 CAS·보호·검증·이력 경계와 native schema1/기존30개 MCP 호출을 보존했다. 0.3.0 새 wheel/portable 설치본과 파일 동일성 결과는 현재 결과 문서에 기록한다.

0.3.0 배포 당시 최종 검증 완료: `output/texel_tui-0.3.0-py3-none-any.whl`, `output/Texel-0.3.0-win64-20261015-154810/` 및 ZIP. wheel과 portable 자체 Python에서 39도구/89함수·신규 UI·원자적 batch/preview/undo 검증이 통과했다. Run.cmd ConPTY80×24에서도 다중 정렬·복합 필터·F4·각각 undo·exit0을 확인했다. 당시 제품37개 Python 파일은 소스/wheel/설치본/portable/ZIP 모두 bytes 동일했고 기존 테스트와 원본 감사 SHA256도 불변이었다. 해시·정확한 입력·남은 한계는 `docs/upgrades/0.3.0-results.md`를 참고한다. 이후 유지보수 소스와의 동일성은 별도 검증 대상이다.

아래 0.2.0·0.1.0·0.2.1 절은 각각 당시 구현과 검증 이력이다. 수치·도구 수·테스트 수·배포 파일 동일성은 해당 시점의 값이며 현재 소스의 검증 결과로 읽지 않는다. 감사 1 기능표도 2026-10-11의 0.2.0 스냅샷(30도구/69함수)으로 보존한다.

## 0.2.0 피드백 대응 이력 (2026-10-10)

근거: 병합/테두리 미완성, 자유 드라이브/폴더 열기·저장, 우클릭 메뉴 및 후속 XLS/공개 GSHEET 읽기 요청. 원본 규칙 문서와 0.1.0 배포물을 보존했다.

- 병합을 실제 가로/세로 영역으로 렌더링하고 내부 선/방향키 막힘을 수정했다. 분할(병합 해제), 병합하고 가운데 맞춤, 복수 내용 결합/확인, 병합 범위 copy/cut/transpose와 row height 보존을 연결했다.
- BorderEdge와 italic/strike/wrap/vertical_align, row_heights를 기본값 호환 방식으로 추가했다. thin/medium/thick/double/dashed/dotted, 전체/바깥/안쪽/방향/없음/색, 서식 지우기·행 자동맞춤·선택하여 붙여넣기를 구현했다. native/undo/XLSX/MCP 공용 경로로 저장한다.
- FileDialog: 드라이브/상위/홈/루트/직접 경로/트리, 파일 형식/인코딩/덮어쓰기. 실제 저장 창을 Ctrl+S에 연결했다. 원본/현재 문서는 실패 시 보존하고 data 밖 파일도 가져온다. New는 올바른 선택 형식을 만들고 Backup은 native만 허용한다.
- 셀/행/열 우클릭 및 Shift+F10, 화면 경계 보정, 선택 보존. 74개 명령 카탈로그에서 문맥 메뉴가 같은 dispatch 경로를 이용한다. 전역 Screen 배경이 모달 기본 스타일을 덮어 표를 가리던 문제도 시각 QA로 재현/수정했다.
- Legacy XLS: xlrd 2.0.2, 실제 BIFF fixture에서 한국어/숫자/날짜/폰트/테두리/병합/행열 크기 읽기와 XLSX 변환 확인. 저장된 수식 계산값만 제공하는 라이브러리 한계를 안내한다. xlwt 1.3.0은 개발 fixture 전용이다.
- GSHEET: 공개 링크 사용자 확인 후 url/doc_id → 허용된 Google HTTPS export → XLSX/CSV 가져오기. 허용 호스트/리디렉션/크기/권한 실패를 검사한다. 쿠키/토큰/계정 설정/Google 원격 문서 쓰기 없음.
- MCP: 30개 도구. set_borders/set_row_height, 확장 format_range, read_range의 style/locked, merge contents 정책 및 XLS/GSHEET import를 연결했다. 파일 --root 경계는 유지했다.

### 0.2.0 당시 실제 증거

- `./test.ps1`: **160 passed**, Ruff check/format PASS, 48 Python 파일. `.cache/turn2-release-verification.log`. 초기 재현/RED는 `.cache/turn2-repro.json`, `turn2-red.log`, `turn2-review-red.log`, `legacy-red.log`에 보존했다.
- 독립 read-only 리뷰의 7개 발견 및 공유 테두리 문제를 9개 테스트로 RED→GREEN: 문자열 타입, 결합 정밀도, New/Backup 형식, 높이 copy, 동결 viewport, 드라이브 선택, 병합 선 유지, 공유 선 지우기. 후속 별도 재리뷰를 주장하지 않는다.
- 실제 Windows PTY 80×24: `ESC[<2;12;11M/m`으로 우클릭 메뉴 열기 → 테두리 메뉴 → 적용 → native DB revision=1/A1 네 방향 thin 선 확인. Ctrl+O로 초기 폴더 밖 XLSX 읽기 → Ctrl+S로 다른 경로 저장 → 저장 B1=42 재확인 → Ctrl+Q exit0. 굵은/이중 선과 병합 모양은 별도의 Pilot/렌더 QA로 확인했다.
- Google의 공식 Python quickstart 공개 샘플(1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms)을 실제 익명 HTTPS로 가져왔다: 1시트, 저장 셀 202개, A1:V31. `.cache/google-public-live.json`. 사용자 개인 문서나 비공개 계정 접근을 검증했다고 주장하지 않는다.
- `pip-audit -r requirements.lock --no-deps --disable-pip`: No known vulnerabilities found. 53개 개발/제품 고정 의존성. 알려진 advisory 검사 범위다.
- 헤드리스 SVG→PNG 시각 QA: `output/preview-formatting.*`, `preview-context.*`; 실제 병합 폭, 내부 선 제거, 선 굵기/이중 선, wrap, 우클릭 뒤 표 유지 확인. 사람의 실제 폰트/IME 장비 QA와 구분한다.
- 최신 100,000셀 합성 benchmark: 저장 7.15초, 읽기 1.68초, profile 0.84초, 헤드리스 시작 0.21초/마지막 셀 이동 0.053초, 합계 4,999,950,000 확인. 전체 테스트와 병렬 실행했으므로 부하 영향이 있으며 성능 보장값이 아니다. `output/benchmark.json`.
- 최신 portable/wheel의 경로/해시/stdio/실행 확인은 `output/portable-verification.json`, `SHA256SUMS.json`에 기록한다.

## 0.1.0 최초 구현 이력 (2026-10-10)

이 절은 Texel 0.1.0 당시 기록이다. 로컬 업무용/데이터 분석용 TUI 및 MCP 구현을 완료했다. 기존 폴더에는 AGENTS.md와 세 표준 문서만 있었으며 당시 Git 저장소는 없었다. 기존 Python 3.14 설치를 변경하지 않고 프로젝트 내부 공식 embeddable Python 3.15.0을 사용했다. 이름/버전/언어는 당시 spec.md에 명시한 Assumption이며, 기술 검증과 사람이 확인하는 범위는 아래처럼 구분했다.

### 0.1.0 당시 구조와 변경 파일

`addresses/model/values` → `formula/functions` → `editing/store/session` → `exchange/analysis` → `ui` 및 `mcp_server` → `__main__` 순서다. Session은 UI/MCP 변경의 공용 트랜잭션 경계이며 Store의 revision CAS가 외부 덮어쓰기를 거부한다.

- 도메인: 희소 셀, 다중 시트, 0.1.0 당시 69개 함수, 참조 이동, 구조 변경, 서식/메모/병합/검증/보호.
- 저장: `.texel` schema 1, SQLite 트랜잭션, 100개 영속 undo/redo, 백업.
- 교환/분석: CSV/TSV/XLSX, 단일 영역 이름 범위, 통계/필터/정렬/중복 제거/피벗/Unicode 차트.
- UI: `ui/app.py`, `grid.py`, `actions.py`, `dialogs.py`, `safe_text.py`, `commands.py`, `i18n.py`; 0.1.0 당시 64개 명령과 마우스/키보드 경로.
- MCP: 0.1.0 당시 28개 도구, `texel://workbook` 리소스, `analyze_data` 프롬프트, 로컬 stdio.
- 실행/빌드: prepare/run/test/build.ps1, scripts/package.py, 잠금 파일, root output/의 wheel/portable ZIP/화면 SVG/성능 JSON.

### 0.1.0 당시 실제 증거

- `.runtime/python315/python.exe --version`: Python 3.15.0.
- 공식 Windows embeddable ZIP SHA256: a6999bcbcbe56f937159ef79c2630260eca99f65f7860bc5cd20430324079a44. Python 공식 릴리스 페이지의 해시와 일치.
- Textual 8.2.8, openpyxl 3.1.5, MCP 2.3.0 및 실제 CPython 3.15용 의존성 설치. requirements.lock에 51개 개발/제품 의존성 고정.
- 수식/모델 초기 RED: 미구현 모듈 수집 실패. 최초 구현 후 42/44, 두 행동 실패를 재현했다. Python 3.15의 sqrt 오류 메시지가 `math domain`이 아니므로 메시지 비교 대신 함수 경계에서 #NUM!로 분류; `A1.__class__`는 NAME 토큰이 되므로 속성 접근 구문을 거부. 최종 `pytest tests/test_formula.py tests/test_model.py -q`: 44 passed.
- 편집/저장 RED: 미구현 모듈 수집 실패. 구현 후 `pytest tests/test_editing.py tests/test_store.py -q`: 9 passed. 재실행 undo/redo, stale revision 거부, 검증 실패 원자성, 교차 시트 구조 참조, 삭제 범위 축소, 정렬 수식, 병합 데이터 손실 거부, 100개 이력 상한 검증.
- 최종 `./test.ps1`: **112 passed**, Ruff check PASS, Ruff format check PASS (38개 파일). `.cache/completion-verification.log`에 명령 출력 보존.
- UI: Pilot 키보드/좌표 클릭/드래그/더블클릭/복사/메뉴/모달/시트/정렬/필터/피벗/차트/80×24·140×45 검증. 테스트는 실제 Textual 메시지 경로와 저장 결과를 확인한다.
- MCP: in-memory와 **별도 stdio subprocess**의 도구 호출, 오류/충돌/페이지 경계, 읽기→쓰기→계산→피벗, 리소스, 실행 중 TUI 반영 검증. 출력 채널은 구조화된 JSON이다. 초기 bare dict 반환이 structured_content를 생성하지 않는 문제를 dict[str, Any]로 수정하고 실제 클라이언트로 검증했다.
- Windows 실제 PTY: 소스/portable 실행. 연속 `42\r54\r` → A1=42/A2=54, SGR 마우스 클릭 `ESC[<0;25;13M`/`...m` 후 `99\r` → B3=99, Ctrl+Q → exit 0. 초기 입력 손실을 실제 경로로 재현하고 지연된 키/포커스 메시지를 안전하게 처리하는 회귀 테스트로 수정했다. NO_COLOR=1 환경의 표시 정책을 존중했다.
- 독립 read-only 리뷰: 8개 Important 및 큰 행 번호의 좌표 문제를 재현했다. R1..R9 수정 및 정수/CSV 직렬화 확장 회귀 **15개 RED→GREEN**. 표시 반올림으로 수치를 합치는 오류, 시트 이름/역순 범위 참조, 외부 삭제/오래 열린 모달 충돌, 할당 전 문자열 상한, 터미널 제어문자 안전 표시, 손상된 파일의 사용자 오류 변환을 검증했다. 리뷰 기준의 모든 발견 사항은 수정했으며 후속 독립 재리뷰를 수행했다고 주장하지 않는다.
- 의존성: `uv --cache-dir .cache/uv tool run --python C:\Python314\python.exe pip-audit -r requirements.lock --no-deps --disable-pip`: **No known vulnerabilities found**. 알려진 advisory 조회 결과이며 모든 공급망 위험의 부재를 증명하지 않는다.
- 렌더링: 색상을 켠 헤드리스 dark/light/contrast SVG. dark SVG를 Chrome headless PNG로 변환해 직접 시각 검사. 실제 사용자 터미널/폰트/IME 검증과 별개의 증거이다.
- 배포: `./build.ps1 -SkipTests`로 실제 wheel/Windows portable 생성. 초기 portable 자체 Python 프로세스에서 MCP 28개 도구/분석 프롬프트/수식42 확인 및 실제 PTY 입력/마우스/종료 검증. 최종 소스/문서 동기화 빌드의 경로/프로토콜 결과는 output/portable-verification.json에 기록한다.

### 0.1.0 당시 최종 성능 측정

리뷰 수정이 분석/렌더링 경로를 변경했으므로 최종 소스로 같은 fixture를 다시 측정했다. `python scripts/benchmark.py`: 10,000행×10열=100,000셀, 합계 4,999,950,000 확인. 저장 3.27초, 재열기 0.69초, 범위 프로파일 0.37초, 헤드리스 시작 0.13초, 마지막 셀 이동 0.033초. output/benchmark.json에 원값 보존. 한 Windows 장비의 합성 데이터 결과이며 성능 보장/장시간 안정성 검증이 아니다.

### 0.1.0 당시 남은 검증과 호환 범위

- 사람이 직접 조작하는 한국어 IME 조합/여러 터미널·폰트/실제 접근성 기기/장시간 soak는 미검증.
- Linux/macOS 실제 터미널, 특정 AI 호스트의 사용자 설정 등록/실사용은 미검증. 연결 JSON과 SDK stdio 경로까지 제공/검증했다.
- 전체 Excel 함수/VBA/외부 연결/동적 배열 spill/Excel 전용 객체 무손실 보존은 계약 밖이다. 0.2.0은 완전한 병합 범위 복사를 지원하고 부분 병합을 자르는 변경은 거부한다.
- 계산의 일반 소수는 부동소수점이다. 정수 값/분석 키/CSV 출력은 표시용 반올림과 분리해 보존한다.
- 새 문서에는 source 수집 오류를 포함한 초기 RED와 실제 행동 회귀를 구분해 기록했다. 초기 미구현 모듈 수집 실패를 개별 동작의 실패 증거로 확대하지 않는다.

### 0.1.0 당시 참조

당시 기준: spec.md, designs.md, DESIGN_DECISIONS.md, implementation_plan.md. 기존 AI_IMPLEMENTATION_DOC_STANDARD.md/AI_CODING_STANDARD.md를 읽고 적용했다. AI_AUDIT_DOC_STANDARD.md는 별도 전면 감사 요청 전에는 전체 적용하지 않았다.

기존 AGENTS.md/표준 문서는 수정하지 않았다. 스킬의 승인/커밋 요구보다 사용자의 명시적 프로젝트 정책을 우선했으며 자동 Git 생성·커밋·푸시·전역 MCP 등록·외부 배포를 수행하지 않았다. `.cache`의 재현/실패 증거와 output의 실제 배포/검증 산출물을 임의로 삭제하지 않았다.

## 0.2.1 감사 1 수정 이력 (2026-10-11)

당시 계약은 spec.md의 감사 1 수정 계약과 docs/audit/remediation_plan_1.md이다. 원본 docs/audit/audit_report_1.md와 evidence_1은 보존했다. 원본 독립 회귀 11 failed → 11 passed (14.73초), 초기 추가 경계 26 failed/11 passed → 48 passed, 독립 리뷰 Important 3건의 6개 회귀 RED→GREEN을 기록했다. 당시 전체 suite는 **232 passed / 168.72초**, Ruff check 및 format **51 files already formatted**이다. 로그는 docs/audit/evidence_remediation_1/에 있다.

수정: 정확한 series 직렬화/seed 보존, 선택 전 draft 확정과 실패 포커스 유지, native 읽기 전용 형식/메타데이터 검증, 삭제/이동/rename 대상 보호, 작은 화면 양식 footer 및 우클릭 목록 높이, 메뉴 단일 종료, 병합 상대 이동, 동결 열 폭/활성 셀 가시성, CLI 원본 저장 기본값, 공유 테두리/joint. Windows에서 추가로 발견한 Ctrl+P 연속 입력은 우선 binding과 첫 layout 전 검색 키 큐로 처리한다.

Windows 소스 ConPTY 80×24: 미확정 42 → SGR B3 클릭 → 7 Enter로 A1=42/B3=7; 빠른 Ctrl+P+borders+Enter 후 B4 raw 빈 값/revision=2 보존; SGR 적용 버튼으로 B4 thin 테두리 revision=3; freeze=(3,1) revision=4; 우클릭 End→마우스 마지막 unfreeze로 (0,0) revision=5; Ctrl+Q exit 0. native_source_green.json에 입력/출력과 저장 assertion을 기록했다. 자동 입력이며 사람의 IME/폰트/장시간 검증을 뜻하지 않는다.

portable에서 추가로 발견한 지연 Focus의 다음 셀 stale draft를 Screen.set_focus 동기 전환으로 수정했다. 관련 9개 회귀와 최신 전체 suite가 통과했다. 마지막 source native는 A1=42/B3=7/B4=8/B5 빈 값, 빠른 모달 전환 2회에서 다음 셀 원문 보존, B4/B5 thin 적용, 마지막 unfreeze revision=7, exit 0을 확인했다(native_source_final.json). 첫 배포본과 실패 기록은 보존하고 수정된 소스로 새 bundle을 생성한다.

scripts/verify_distribution.py는 선택 설치본의 경로, CLI CSV 원본 저장 기본값, 80×24 draft/테두리/메뉴·병합, 0바이트 native 보존, 실제 MCP stdio 30도구·큰 정수 채우기·재열기·undo/redo·보호 삭제 거부를 확인한다. 최종 소스 설치본 실행은 통과했다. 새 0.2.1 wheel/portable 빌드·설치본 검증 결과와 정확한 artifact 경로는 docs/audit/remediation_results_1.md에 기록한다.

기존 소스 28개 중 13개 모듈 수정, 회귀 2개 파일 추가, 기존 병합 outline 회귀를 단일 공유 경계의 content/rule 좌표 assertion으로 동기화, 설치본 검증 스크립트 추가. 의존성/schema/MCP root 범위는 유지한다. 수정 결과 기록은 독립 정식 재감사 PASS 판정과 구별한다.

최종 배포 검증 완료: output/texel_tui-0.2.1-py3-none-any.whl 및 output/Texel-0.2.1-win64-20261011-162957 폴더/ZIP. 최종 wheel 설치본과 portable 자체 Python에서 검증 스크립트 통과, Run.cmd Windows ConPTY 입력도 A1=42/B3=7/B4=8/B5 빈 값·빠른 모달 2회·thin 테두리·unfreeze revision=7·exit 0으로 통과했다. 제품 28개 Python 파일은 소스/wheel/설치본/portable/ZIP 모두 bytes 동일하다. 원본 감사 SHA256도 불변이다. 정확한 hash·로그·남은 장비 검증은 docs/audit/remediation_results_1.md를 참고한다. 첫 0.2.1 배포물은 수정 전 실패 증거로 보존했다.
