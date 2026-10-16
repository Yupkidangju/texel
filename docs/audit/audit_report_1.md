# Texel 전체 기능 감사 보고서 1

생성일: **2026-10-11 (Asia/Seoul)**. 대상: `C:\LocalDev\python\Texel`, **0.2.0**. 기준 사용자 요청: 선 그리기·우클릭 메뉴·파일 읽기 등 모든 기능을 재점검하여 코더에게 전달할 리포트 작성. 감사 기준: `AI_AUDIT_DOC_STANDARD.md`. 작업 기준: [audit_plan_1.md](audit_plan_1.md).

**최종 판정: HOLD.** 확인된 발견 11건: **Critical 1 / Major 9 / Minor 1**, 모두 `Needs Fix`. 기존 테스트 160개는 통과했으나 독립 감사 회귀 11개는 실제 기대 동작을 만족하지 못했다. 제품 소스·기존 테스트·스크립트 48개 SHA256은 감사 전후 동일하다. 이번 작업은 수정이나 배포가 아니라 감사이며, 코더에게 실제 메시지를 보내지 않았다.

## 1. 감사 범위와 근거

### 환경 및 입력 자료

- Windows, PowerShell, 프로젝트 내부 Python **3.15.0**. Textual **8.2.8**, openpyxl **3.1.5**, xlrd **2.0.2**, MCP **2.3.0**, pytest **9.1.1**, Ruff **0.17.0**을 실제 설치 메타데이터로 확인했다.
- 문서: 사용자 제공 AGENTS.md, spec.md, designs.md, DESIGN_DECISIONS.md, README.md, BUILD_GUIDE.md, implementation_plan.md의 기준과 IMPLEMENTATION_SUMMARY.md의 검증 주장, CHANGELOG.md, audit_roadmap.md 및 세 AI 표준. 기존 문서는 변경하지 않았다.
- 제품 범위: `texel/`의 도메인/계산/편집/교환/저장/분석/MCP/UI, `tests/` 전체 실행, `scripts/`와 루트 실행/검증/패키징 경로. 주요 근거 코드는 각 finding에 명시하고 [source_anchors.txt](evidence_1/source_anchors.txt)에 발췌했다.
- 배포: `output/Texel-0.2.0-win64-20261010-215605`와 `output/texel_tui-0.2.0-py3-none-any.whl`. 제품 Python 28개 파일이 현재 소스와 byte 단위로 동일하다. portable의 자체 Python·자체 Texel 모듈을 이용해 UI와 실제 MCP stdio를 실행했다.
- Git 저장소는 없다. `git status --short`가 `not a git repository`로 종료한 것은 상태 확인 결과이며 제품 실패로 분류하지 않았다. 별도 CI/ADR/보안 전용 문서는 확인하지 못했으며, 기존 spec/설계 결정/로컬 검증을 기준으로 삼았다.

### 검증 결과

| 검증 | 이번 실행 결과 | 증거와 해석 |
|---|---|---|
| 기존 전체 pytest | **160 passed / 41.11초** | [baseline_pytest.log](evidence_1/baseline_pytest.log), 제품 기본 회귀 통과 |
| Ruff check / format | 통과 / 48 files already formatted | [ruff_check.log](evidence_1/ruff_check.log), [ruff_format.log](evidence_1/ruff_format.log) |
| 전체 명령 카탈로그 | **74/74 대표 통합 경로 실행**, 최종 오류 없음 | [command_sweep.json](evidence_1/command_sweep.json). 120×40, 검색→실행→양식→저장 재읽기. 일부 필드는 직접 설정했으며 모든 경계의 정상 증거는 아님 |
| 수식 레지스트리 | **69/69 기본 예제 기대값 일치** | [domain_probe.json](evidence_1/domain_probe.json). 함수당 기본 예제 1개; 모든 Excel 의미나 모든 인자 조합을 뜻하지 않음 |
| MCP 도구 | **30/30 대표 호출 ok**, 누락 없음 | [mcp_sweep.json](evidence_1/mcp_sweep.json), SDK 메모리 전송. 기존 suite는 실제 stdio·revision 충돌·공용 TUI 관찰도 실행 |
| UI 화면 크기 | 80×24: 7개 양식 / 100×30: 4개 양식 적용 버튼 접근 실패 | [layout_probe.json](evidence_1/layout_probe.json). 점검한 18개 양식의 120×40 적용 버튼은 모두 접근 가능 |
| 실제 Windows 터미널 | 42 입력 저장, SGR 우클릭→테두리 창, 버튼 누락 출력, 명시적 Escape→Ctrl+Q **exit 0** | [native_final.json](evidence_1/native_final.json). 80×24 ConPTY 자동 입력; 사람의 화면/IME 검증 아님 |
| portable 자체 런타임 | 잘못된 draft 저장·80×24 테두리 버튼 실패도 동일 재현. CSV 값 42, MCP 도구 30개·stdio 쓰기·영속 값 42 확인 | [portable_probe.json](evidence_1/portable_probe.json) |
| wheel/portable 소스 대조 | 제품 Python 28개 모두 동일 | [package_parity.json](evidence_1/package_parity.json). 신규 빌드 성공으로 확대하지 않음 |
| 공개 Google Sheets | 이번 라이브 다운로드 성공, 1시트/202셀 | [google_live.json](evidence_1/google_live.json). 프로젝트가 기존에 사용한 공개 샘플 하나만 확인 |
| 의존성 advisory | 런타임 lock 전 항목 **No known vulnerabilities found** | [dependency_audit.log](evidence_1/dependency_audit.log). 조회 시점의 알려진 취약점만 평가 |
| 신규 발견 회귀 | **11 failed / 13.45초**, 최종 pytest는 동작 assertion 실패. 독립 우클릭 probe는 stack 예외도 재현 | [audit_regressions.log](evidence_1/audit_regressions.log), [test_audit_regressions.py](evidence_1/test_audit_regressions.py) |
| 제품 보존 | 소스/기존 테스트/스크립트 **48개 동일** | [product_preservation.json](evidence_1/product_preservation.json) |

전체 명령/도구/함수 개별 매핑은 [feature_matrix_1.md](feature_matrix_1.md), 집계 원값은 [verification_summary.json](evidence_1/verification_summary.json)에 있다.

### 주요 기능군 판정

| 기능군 | 실제 확인 범위 | 남은 실패 또는 한계 |
|---|---|---|
| 계산/참조/오류 | 69함수 기본값, 기존 순환·lazy IF·참조 이동·상한 회귀 | 전체 Excel 호환은 계약 밖. 연속 채우기 정밀도는 별도 실패 |
| 입력/이동/선택 | 키보드, 마우스 클릭/더블클릭/드래그/휠, 주소, 포커스, draft 충돌 | DBG-F001, IMP-F002, IMP-F003 |
| 복사/잘라내기/붙여넣기 | 값/수식/서식/전치, 병합 구조, 행 높이, 보호/실패 회귀 | 대표 조합 검증. 실 OS 클립보드와 모든 앱 간 교환은 별도 미검증 |
| 행열/시트 | 삽입/삭제, 이름/복제/추가, 너비/높이, 숨김, 동결 | IMP-F003, SEC-F001 |
| 서식/테두리/병합 | 공개 우클릭→마우스 메뉴→키보드 선 종류→적용, native/undo/XLSX 기존 회귀 | IMP-F001, IMP-F002, IMP-F004, DBG-F006 |
| 정렬/필터/검색/분석 | 공개 명령, 저장, 피벗 새 시트, 차트 텍스트, 기존 계산값 검증 | IMP-F001이 작은 화면의 정렬/필터/분석 양식에도 영향 |
| 파일 | native/CSV/TSV/XLSX/XLS 기존 회귀, 외부 폴더, 인코딩, 직접 경로/트리 키 선택, 덮어쓰기 실패 보존 | DBG-F003, DBG-F004, DBG-F005. 신고한 특정 실제 파일은 제공되지 않아 그 파일의 원인은 미확정 |
| Google | 주소/호스트/리디렉션/크기/오류 stub 회귀 + 공개 샘플 라이브 | 모든 공유 정책·비공개 계정은 미검증 |
| 저장/이력/공용 MCP | 원자성/revision/undo/redo/재실행, 모든 도구 기본 호출, stdio 쓰기→저장→TUI | 데이터 보호 삭제 경계 SEC-F001; 장시간 동시 작업은 미검증 |
| 도움말/언어/테마/배포 | 카탈로그 접근, 함수 목록, 연결 정보, 테마/언어 명령, 소스 대조/portable 실행 | 실제 접근성/폰트/IME와 신규 빌드는 미검증 |

## 2. 제외 및 미검증 범위

- `.runtime/`, dependency cache 및 portable vendor의 모든 내부 구현 전수 감사는 제외했다. 설치 버전/lock/advisory 및 실제 사용 경로는 확인했다.
- 0.1.0 배포물, 과거 `.cache`의 모든 개발 기록/벤치마크/스크린샷은 재감사하지 않았다. 현재 0.2.0 배포물만 대조했다. 공개 샘플 바로가기를 재사용한 것 외에는 과거 로그를 현재 통과 근거로 사용하지 않았다.
- 새 패키지 빌드를 실행하지 않았다. 현재 artifact의 소스 동일성과 실행을 확인했으며, 수정 후 재빌드는 코더 완료 조건이다.
- 한국어 IME 조합/취소, Windows Terminal 설정·폰트별 사람의 직접 조작, 접근성 기기, 장시간 문서 작업/soak, Linux/macOS 실제 터미널, 실제 AI 호스트 설정 등록은 미검증이다.
- 비공개 Google 인증/쿠키/토큰/원격 쓰기, Excel 전체 함수/VBA/그림/전용 객체 무손실 왕복은 기존 계약 밖이다.
- 자동 생성 PNG의 한글 글꼴 누락은 감사용 변환 환경의 한계이며 제품의 실제 한국어 폰트 실패로 보고하지 않는다. 모달 clipping은 위젯 hit-test·SVG·ConPTY 출력으로 각각 대조했다.
- 함수와 명령을 모두 목록화하고 대표 실행했지만 모든 인자·파일·터미널 조합이 정상이라는 의미는 아니다. 사용자 신고의 특정 파일/화면 설정을 보지 못한 부분은 원인 미확정으로 남긴다.

## 3. Pass 1 — 구현 적합성

### IMP-F001 — 작은 화면에서 양식 적용 버튼과 우클릭 메뉴 끝 항목이 가려진다

- **Severity: Major / Status: Needs Fix / Owner: Coder.** Pattern: IMP-001, TEST-001. 영역: 공용 FormDialog 레이아웃.
- **재현:** 80×24에서 Ctrl+P → `borders` → Enter → 적용 버튼 클릭. 버튼의 중심 (65,22)은 Button이 아니라 Vertical에 닿으며 적용되지 않는다. 100×30에서도 `style`, `validation`, `pivot`, `conditional`의 적용 버튼이 화면 밖 또는 clipping 영역에 있다.
- **기대/실제:** 명세상 80×24에서도 입력/메뉴와 중요한 버튼을 사용할 수 있어야 한다. 실제로 80×24에서는 테두리/셀 서식/유효성/정렬/필터/피벗/조건부 7개 양식, 100×30에서는 4개 양식의 적용 버튼이 마우스로 접근 불가다. 파일 전용 FileDialog의 버튼은 두 크기에서 접근 가능했다.
- **우클릭 추가 재현:** 80×24에서 셀 우클릭 → End로 마지막 `unfreeze` 명령까지 스크롤. 명령의 화면 좌표 (18,22)는 OptionList가 아니라 `context-box`에 닿는다. 100×30에서는 같은 마지막 명령의 hit-test가 OptionList에 닿지만 실제 마우스 명령은 DBG-F006처럼 실패한다. 메뉴 닫힘만으로 성공이라고 판단하지 않았다. `context_tail_probe.json` 및 `test_DBG_F006_context_*`로 분리 재현했다.
- **원인/코드:** `texel/ui/dialogs.py:37-42`. 외곽은 `max-height:92%`인데 body가 `height:auto; max-height:24`를 차지하고 title/padding/error/footer 공간을 예약하지 않는다. 창 존재나 필드 값 변경만 확인하는 테스트로는 놓친다.
- 우클릭은 `texel/ui/context_menu.py:14-17,38-49`에서 box의 `max-height:90%`와 실제 높이, OptionList `max-height:20`의 공간 예산이 어긋난다. End가 OptionList 기준으로 스크롤되더라도 부모의 잘린 영역을 고려하지 못한다.
- **증거:** layout_probe.json, portable_probe.json, native_final.json, 회귀 `test_IMP_F001_*`.
- **영향:** 사용자가 우클릭으로 테두리를 열어도 적용하지 못해 선 그리기나 메뉴 명령이 고장 난 것으로 보인다. 권장 크기 100×30에서도 주요 서식 양식이 막힌다.
- **수정 방향:** 공용 모달에 footer 공간을 고정 예약하고, 가변 body만 남은 높이에서 스크롤되도록 한다. ContextMenu도 제목/테두리를 제외한 실제 가용 높이에 목록을 맞춘다. 오류 문구가 표시된 상태도 포함한다. FileDialog의 동작을 유지한다.
- **재감사:** 80×24/100×30/120×40 및 화면 resize, Select overlay, 오류 메시지 상태에서 모든 해당 양식을 마우스/키보드로 끝까지 적용하고 우클릭 처음/중간/끝 항목도 클릭한다. 테두리 변경은 revision·저장·화면 선·undo까지 확인한다.

![80×24 테두리 양식: 적용/취소 버튼이 보이지 않음](C:/LocalDev/python/Texel/docs/audit/evidence_1/layout-borders-80.png)

### IMP-F002 — 병합 셀 편집 후 Enter/Tab이 병합 밖으로 이동하지 않는다

- **Severity: Major / Status: Needs Fix / Owner: Coder.** Pattern: IMP-001. 영역: 편집 확정 후 이동.
- **재현:** A1:B3 병합 → A1에서 `42` → Enter. 값은 저장되지만 cursor는 A1에 남는다. 이후 Down을 누르면 A4로 정상 이동한다.
- **기대/실제:** Enter는 편집 확정 후 아래 셀로 이동하는 계약이다. 병합에서 아래/오른쪽 이동은 병합 외곽을 넘어야 한다. 실제 확정 경로는 앵커+1을 계산하고 merge_anchor가 다시 A1로 되돌린다. Tab도 가로 병합에 같은 구조가 있다(Enter는 실행 재현, Tab은 코드 추적).
- **코드/증거:** `texel/ui/app.py:339-340`과 `texel/ui/grid.py:129` 및 on_key의 병합 보정. probe_ui_second.json `merged_edit_enter`, 회귀 `test_IMP_F002_*`.
- **수정 방향:** 확정 후 이동과 일반 방향키 이동이 병합 외곽 계산을 공유하도록 한다. Shift+Tab과 Ctrl+Enter 선택 채우기는 별도 계약을 유지한다.
- **재감사:** 가로/세로/복합 병합에서 Enter/Tab/Shift+Tab, 일반 셀, 숨김/필터 경계를 실제 키 입력으로 검증한다.

### IMP-F003 — 동결 열이 화면을 채우면 스크롤 영역과 활성 셀이 사라진다

- **Severity: Major / Status: Needs Fix / Owner: Coder.** Pattern: IMP-001. 영역: 가상 열 레이아웃.
- **재현:** 80×24 → Ctrl+G로 G2 이동 → `freeze` 실행 → Right 두 번. cursor=I2, left=8이지만 가시 열은 A:F뿐이다.
- **기대/실제:** 동결을 사용해도 나머지 영역을 탐색할 수 있어야 한다. 실제 frozen 목록을 먼저 출력하다 화면 폭이 끝나므로 left를 바꿔도 I열이 표시되지 않는다. 행에 구현한 최소 스크롤 공간 정책과 열이 비대칭이다.
- **코드/증거:** `texel/ui/grid.py:98-127`. probe_ui_second.json `frozen_columns`, 회귀 `test_IMP_F003_*`.
- **수정 방향:** 동결 열의 실제 폭을 예산화해 스크롤 열을 표시할 공간을 확보한다. 임의 열 개수 제한만으로 해결하지 말고 넓은 열·숨긴 열·resize도 처리한다.
- **재감사:** 세 화면 크기에서 많은/넓은 동결 열을 만든 후 이동·주소·휠·마우스 hit-test의 활성 셀 가시성을 확인한다.

### IMP-F004 — 인접 셀의 공유 세로 테두리가 두 번 그려진다

- **Severity: Minor / Status: Needs Fix / Owner: Coder.** Pattern: IMP-001. 영역: 테두리 시각 결과.
- **재현:** A1:B2 전체 테두리 `thick` 적용. 내용 줄의 A/B 공유 경계가 `┃┃`로 출력된다. horizontal rule의 joint와 내용 줄의 경계도 한 칸 차이를 보인다.
- **기대/실제:** 하나의 셀 경계에 한 가지 선 스타일을 표시해야 한다. 실제 A의 right edge와 B의 left edge를 각각 인접한 두 terminal 칸에 그려 얇은/굵은 선도 이중 경계처럼 보인다. 저장된 BorderEdge와 XLSX 종류 자체는 정상이다.
- **코드/증거:** `texel/ui/grid_render.py:182-200`. probe_ui.json `border_mouse_and_dropdown`, border-after.svg, 회귀 `test_IMP_F004_*`.
- **수정 방향:** 셀의 양쪽 edge와 공용 경계가 한 출력 위치를 사용하도록 rendering/width/joint 정책을 정리한다. 터미널의 medium/thick 동일 glyph는 명시된 기존 설계이므로 그 자체를 버그로 바꾸지 않는다.
- **재감사:** thin/thick/double, 이웃 스타일 충돌, 병합, 숨김/동결에서 내용 줄과 rule 줄의 경계 및 hit-test를 비교한다.

## 4. Pass 2 — 디버그/엔지니어링 품질

### DBG-F001 — 편집 중 다른 셀을 클릭한 뒤 입력하면 원래 셀에 이어 저장된다

- **Severity: Major / Status: Needs Fix / Owner: Coder.** Pattern: DBG-002, TEST-001. 영역: draft/선택/포커스 상태.
- **재현:** A1에서 `4`, `2` 입력(미확정) → B3를 한 번 클릭 → `7`, Enter. 실제 A1=427, B3=빈 값. portable에서도 동일하다.
- **기대/실제:** 클릭으로 선택/입력 문맥이 달라진 것을 사용자가 명확히 알 수 있어야 한다. 현재는 cursor/선택은 B3이고 포커스는 grid인데, 다음 키는 숨은 A1 draft로 전달된다. 기존 문서의 'draft 대상 캡처'는 다른 셀에 조용히 저장하지 않기 위한 장치이지만 현재 선택과 입력 문맥의 불일치를 해결하지 못한다.
- **코드/원인:** `texel/ui/grid.py:246-268`은 편집 확정 없이 이동하고, `:322-326`은 editing이 남아 있으면 모든 키를 formula_input으로 전달한다. `texel/ui/app.py:314-322`는 캡처된 A1에 저장한다.
- **증거:** probe_ui_second.json `click_during_draft`, portable_probe.json, 회귀 `test_DBG_F001_*`. 반대로 편집 중 우클릭은 기존 draft를 42로 확정해 정상 처리했다.
- **수정 방향:** 선택을 바꾸기 전 draft를 확정하거나, 충돌 시 이동을 거부하고 기존 포커스를 유지하는 등 한 가지 정책으로 상태를 정렬한다. 취소/유지 정책을 택해도 활성 편집 대상이 분명해야 한다. 첨부 회귀는 '기존 42 확정→B3=7' 정책을 사용하며 코더가 문서에 확정할 사항이다.
- **재감사:** 클릭/Shift+클릭/드래그/더블클릭, 수식줄 편집, invalid validation/revision 충돌에서 raw·editing 대상·cursor·focus·화면을 함께 확인한다. 기존 연속 키 입력 누락 회귀도 유지한다.

### DBG-F002 — 숫자 연속 채우기가 기존 큰 정수까지 반올림해 저장한다

- **Severity: Critical / Status: Needs Fix / Owner: Coder.** Pattern: TEST-001. 영역: 수치 편집/자동 저장.
- **재현:** A1=9007199254740993, A2=9007199254740994 → A1:A3 선택 → `series`. 기대 A3=9007199254740995이며 A1/A2는 보존해야 한다. 실제 세 셀이 모두 **9007199254740000**이 되고 raw도 모두 `9.00719925474e+15`가 된다.
- **원인:** `texel/editing.py:137`이 도메인 직렬화에 표시용 `display_value(.12g)`를 사용한다. 정수 계산 자체는 정확하지만 저장 직전 정밀도를 잃는다. TUI와 MCP `fill_cells(direction="series")`가 같은 함수를 사용한다.
- **증거:** probe_ui_second.json `series_precision`, 회귀 `test_DBG_F002_*`. 기존 exact integer/CSV/paste 회귀는 이 연속 채우기 경로를 다루지 않아 baseline이 통과했다.
- **영향:** 사용자가 선택한 원본 숫자가 조용히 바뀌고 자동 저장된다. 표의 ID·금액·정수 집계 신뢰성을 훼손한다. undo 가능성은 데이터 변조 발생 사실을 없애지 않는다.
- **수정 방향:** 표시용 반올림을 저장에서 분리하고 정확한 수치 직렬화 규칙을 사용한다. bool, float, 날짜/오류 시작값의 허용 조건도 기존 명세에 맞게 확인한다.
- **재감사:** 큰 정수/음수/작은 소수/단일 초기값, TUI·MCP 각각 실제 실행 후 raw와 계산값, native 재열기, CSV, undo/redo를 검증한다.

### DBG-F003 — 손상된 native 파일 열기 실패가 현재 문서를 교체한 뒤 발생한다

- **Severity: Major / Status: Needs Fix / Owner: Coder.** Pattern: DBG-001, TEST-001. 영역: native 메타데이터 검증/열기 원자성.
- **재현:** Texel SQLite의 sheet `filter_spec.range`를 `NOPE`로 바꾼 감사 fixture를 준비한다. A1='original' 문서에서 Ctrl+O로 해당 파일을 연다. 모달은 `Invalid cell address: NOPE`를 표시하고 남지만, app.session은 이미 bad.texel로 바뀌고 A1은 빈 값이 된다. 원래 파일의 디스크 데이터는 남아 있다.
- **기대/실제:** 명세는 가져오기 실패 시 현재 통합 문서와 입력을 보존하도록 정한다. 실제 load_file/Workbook.validate가 filter 메타데이터를 통과시킨 뒤 switch_workbook이 session을 먼저 교체하고 refresh의 filtered_rows에서 실패한다.
- **코드:** `texel/model.py:217-281`, `texel/ui/actions.py:121-130`, `:86-93`, `texel/ui/grid.py:85-95`, `texel/editing.py:filtered_rows`.
- **증거:** extra_probe.json `invalid_native_open`, domain_probe.json `native_invalid_filter_accepted`, 회귀 `test_DBG_F003_*`.
- **수정 방향:** 현재 UI가 소비할 메타데이터를 candidate 단계에서 검증하고, 성공이 확정된 뒤 세션/시트/선택/원본 경로를 전환한다. 단순히 예외만 삼키지 말고 이전 작업 상태를 보존한다. conditional_rules/charts/named_ranges/hidden/width 등 같은 검증 누락 패턴도 관련 범위에서 확인한다.
- **재감사:** 정상 파일 + filter/rule/name/차트 메타데이터 손상 fixture를 공개 Ctrl+O 경로로 열어 실패 시 session path·내용·draft·revision·모달 입력·원본 파일을 비교한다. 이 finding은 특정 metadata 실패이며 모든 파일 읽기가 실패한다는 주장은 아니다.

### DBG-F004 — CLI/Run.ps1로 교환 파일을 열면 원본 저장 기본 경로를 잃는다

- **Severity: Major / Status: Needs Fix / Owner: Coder.** Pattern: DBG-001, IMP-001. 영역: CLI→TUI 시작 경로.
- **재현:** `python -m texel tui --workbook source.csv`의 실제 main을 호출하고 UI 실행 직전 상태를 관찰한다. 값 42는 정상 가져오지만 source_path=None이고 새 `source-<random>.texel`만 전달된다. run.ps1 -Workbook 역시 같은 경로다.
- **기대/실제:** 가져온 XLSX/CSV 원본 경로를 저장 기본값으로 기억하는 계약이다. Ctrl+O 경로는 source_path를 설정하지만 CLI 경로는 잊어 Ctrl+S 기본값이 원본 대신 랜덤 native 경로가 된다. XLS/GSHEET 변환 .xlsx 기본값과 안내도 동일 진입 경로에서 대조해야 한다.
- **코드/증거:** `texel/__main__.py:44-48`, `texel/ui/app.py:186`, `texel/ui/actions.py:save/export default`. extra_probe.json `cli_import_source`, 회귀 `test_DBG_F004_*`.
- **검증 한계:** CLI main의 실제 가져오기/구성은 실행했고 UI .run만 캡처했다. 이 케이스 자체를 사람이 연 창을 조작한 증거로 표시하지 않는다.
- **수정 방향/재감사:** 가져오기 결과와 원본 경로를 공용 시작 경로로 전달하고, CSV/TSV/XLSX/XLS/GSHEET를 CLI 및 Ctrl+O 양쪽에서 연 후 Ctrl+S 기본값·확장자·안내·저장 결과를 대조한다. native 자동 저장은 유지한다.

### DBG-F005 — 읽기 요청이 0바이트 native 입력 파일에 새 DB를 쓴다

- **Severity: Major / Status: Needs Fix / Owner: Coder.** Pattern: DBG-001, SEC-004. 영역: 열기와 새 문서 생성의 혼용.
- **재현:** 기존 0바이트 `zero.texel`에 load_file을 실행한다. 오류 없이 빈 workbook을 반환하고 원본 파일 크기를 **0→24,576바이트**로 변경한다.
- **기대/실제:** 기존 파일의 import/open은 파일 형식을 검사하고 원본을 보존해야 한다. 실제 exchange의 읽기 경로가 Store 생성자를 호출하고, texel_state가 없으면 CREATE TABLE/INSERT 및 WAL 변경을 실행한다. 존재하지 않는 문서 생성 계약과 구별되지 않는다.
- **코드/증거:** `texel/exchange.py:50-53`, `texel/store.py:49-78`. probe_ui_second.json `empty_native_input`, 회귀 `test_DBG_F005_*`.
- **영향:** 빈 파일만으로 내용 손실을 주장하지 않는다. 그러나 읽기/import가 기존 입력을 초기화하는 경계 위반이며 정상 native를 검사할 때도 write-capable 연결을 사용한다. 읽기 권한만 있는 입력은 별도 직접 미검증이다.
- **수정 방향/재감사:** 기존 native의 검증/읽기와 명시적 새 문서 생성을 분리한다. 0바이트/빈 SQLite/타 애플리케이션 DB/손상된 metadata/정상 native에서 읽기 전후 bytes·schema 및 현재 작업 문서 보존을 확인한다. 새 native 생성 경로도 유지한다.

### DBG-F006 — 우클릭 메뉴 끝 항목의 마우스 선택이 명령을 놓치거나 화면 stack 예외를 낸다

- **Severity: Major / Status: Needs Fix / Owner: Coder.** Pattern: DBG-002, TEST-001. 관련: IMP-F001의 ContextMenu clipping.
- **재현:** 동결 행/열 각각 1인 문서 → 셀 우클릭 → End → 마지막 `unfreeze` 항목의 실제 표시 좌표 클릭. **80×24와 100×30에서 모두** 메뉴는 닫히지만 freeze=(1,1)이 남아 명령이 실행되지 않는다. 독립 probe에서는 뒤이어 `ScreenStackError: Can't pop screen; there must be at least one screen on the stack`도 재현했다. 80×24에는 clipping도 있으나 100×30에도 실패하므로 clipping만 고치면 해결된다고 단정하지 않는다.
- **기대/실제:** 마우스 명령 선택은 해당 명령을 한 번 실행하고 메뉴를 한 번 닫아야 한다. 실제 마우스 click과 지연된 OptionSelected 처리에서 문맥 메뉴가 이미 pop된 뒤 `selected`가 다시 dismiss를 시도한다. 키보드 Enter는 별도 대조 경로이며 결과는 context_tail_probe.json에서 mode별로 구분한다.
- **코드/증거:** `texel/ui/context_menu.py:50-56`의 selected/on_click 두 종료 경로, 같은 파일의 높이/offset과 OptionList clipping. context_tail_probe.json/log, context_regression.log, 회귀 `test_DBG_F006_*`. 단순히 화면이 닫혔다는 assertion은 명령 성공을 증명하지 못한다는 점도 확인했다.
- **수정 방향:** 선택과 외부 클릭의 종료 경로를 분리해 한 번만 dismiss하고 선택한 명령을 전달하도록 한다. 닫힌 화면의 지연 선택 메시지 처리도 안전하게 정리하며 작은 화면의 가시 영역도 바로잡는다. 예외만 숨겨도 명령이 유실되면 수정 완료가 아니다.
- **재감사:** 80×24/100×30의 처음/끝 항목, pointer click/End→click/휠→click/Enter/Escape/외부 클릭과 빠른 입력에서 실제 변경·revision·메뉴 stack을 확인한다. 지원 터미널의 native 마우스 경로도 갱신한다.

## 5. Pass 3 — 보안/데이터 무결성

### SEC-F001 — protected 마지막 시트를 삭제하면 잠긴 셀 검사가 생략된다

- **Severity: Major / Status: Needs Fix / Owner: Coder.** Pattern: SEC-005, TEST-001. 영역: 공용 보호/삭제 경계.
- **재현:** Sheet1 + Locked 두 시트. Locked!A1에 값을 넣고 locked=True, protected=True 설정. Session.apply→delete_sheet(index=1)를 실행하면 오류 없이 Locked가 삭제되고 revision은 1→2가 된다.
- **기대/실제:** 잠긴 셀 삭제 경로도 차단하는 계약이고 행열 구조 변경은 보호 해제를 요구한다. 실제 보호 검사가 candidate에 남은 시트만 순회하므로 삭제된 마지막 시트를 검사하지 않는다. 위치 index로 old/new를 비교하는 구조는 다른 삭제·시트 재배치에서도 관련 검토가 필요하다.
- **코드/증거:** `texel/session.py:34-39`, `texel/editing.py:341`, `texel/model.py:delete_sheet`. domain_probe.json `delete_protected_last_sheet`, 회귀 `test_SEC_F001_*`. TUI 삭제와 MCP edit_sheet(delete)가 동일 함수를 사용함을 추적했다; 두 공개 UI/프로토콜 삭제 케이스의 직접 재현은 코더 재감사에 포함한다.
- **영향:** 사용자 데이터 보호 계약을 우회한다. 원격 인증 또는 OS 권한 탈취로 확대하지 않는다. 보호는 인증 시스템이 아닌 편집 무결성 경계다.
- **수정 방향:** 삭제 전 보호 상태/잠긴 데이터를 평가하고 old/new 시트가 같은 대상을 의미하는지 확인하도록 한다. 기존 저장 schema를 불필요하게 변경하지 않는다.
- **재감사:** 보호된 첫/중간/마지막 시트, 잠긴/비잠긴 셀, 보호 해제 후 삭제, rename/duplicate/다른 시트 삭제, undo/redo 및 TUI/MCP 공용 경로를 검증한다.

### 그 밖의 보안 확인

- 수식은 직접 parser/등록 함수로 평가하며 eval/exec/임의 셸·파일·네트워크 호출 경로가 없다. 기존 임의 함수/attribute 접근 거부, 큰 문자열 사전 상한, 파일 크기/압축 크기, 터미널 제어문자 표시 안전 회귀를 이번 suite로 확인했다.
- MCP는 stdio이며 root 정규화/is_relative_to로 경로 탈출을 거부한다. 기존 path-scope 실패와 원자적 변경/revision 충돌 회귀는 통과했다. 실제 NTFS link/reparse를 새로 생성해 전 종류를 검증한 것은 아니다.
- CSV export의 formula injection 보호 및 XLSX 강제 문자열 보존 회귀는 통과했다. CSV가 typed schema를 보존하는 계약은 아니므로, '00123'이 재읽기에서 숫자로 추론되는 관찰은 별도 실패 finding으로 올리지 않았다.
- GSHEET는 명시된 Google HTTPS 주소/리디렉션 제한을 사용하고 계정 키/쿠키를 읽지 않는다. 공개 샘플과 기존 악성 주소/다운로드 상한 회귀는 통과했다.
- 런타임 lock의 알려진 advisory는 발견되지 않았다. 패키지의 무결성·향후 취약점·모든 공급망 위험이 없다는 판정은 아니다.

## 6. Cross-pass — XPF-F001: 테스트 통과와 사용자 정상 조작 판정의 차이

- 관련: IMP-F001, DBG-F001, DBG-F002, DBG-F003, DBG-F006, SEC-F001.
- baseline 160 통과와 74/69/30 대표 경로 확인은 실제 근거다. 그러나 창을 열거나 내부 필드를 직접 설정하는 검사는 버튼의 가시성·물리 입력·자료형 정밀도·삭제된 대상 검증까지 증명하지 못한다.
- **해결:** 개별 통과 결과를 유지하되 전체 판정은 HOLD. 신규 11개 회귀의 RED와 공개 경로 검증을 gate에 추가한다. 명세의 80×24/100×30 범위를 축소하거나 실패 assertion을 지워 PASS를 만들지 않는다.
- 초기 감사 스크립트의 좌표 한 칸 오류, CellStyle.to_dict 잘못된 호출, widget API 이름 및 MCP inputSchema/input_schema 혼동, backup fixture가 현재 파일과 같았던 오류는 **감사 harness 오류**로 분류해 교정했다. initial 로그는 보존했고 최종 finding의 근거로 사용하지 않았다. 트리도 보이지 않는 위치 클릭 실패를 제품 버그로 보고하지 않았으며, 포커스 이동 후 실제 키 선택/열기 값 77을 확인했다.
- native의 legacy Escape 전달 시도와 명시적 CSI Escape를 구분했다. 최종 명시적 Escape→Ctrl+Q exit 0만 정상 종료 증거로 사용한다.
- native_final.json은 도구가 반환한 출력 청크를 보존한 기록이며 일부 청크에는 도구 출력 길이 제한 표시가 있다. 전체 프레임의 무손실 녹화라고 주장하지 않는다. 입력 저장값/메뉴 출력/exit code와 별도 Pilot의 좌표 증거를 함께 사용한다.

## 7. PASS 이전 수정 순서

| 순서 | 발견 | 완료 조건 |
|---|---|---|
| 1 | DBG-F002 | 숫자 데이터 변조 제거. TUI/MCP 저장·재열기·undo 증거 |
| 2 | DBG-F001, DBG-F003, DBG-F005, SEC-F001 | 입력 대상/문서 전환/파일 읽기/보호 경계 일관성. 실패 원본·작업 상태 보존 |
| 3 | IMP-F001, DBG-F006 | 작은 화면과 권장 화면에서 모든 문제 양식·우클릭 처음/끝 명령의 실제 적용 가능. stack 예외와 명령 유실 제거 |
| 4 | IMP-F002, IMP-F003, DBG-F004 | 병합 이동·동결 가시성·CLI 저장 기본 경로 공개 실행 검증 |
| 5 | IMP-F004 | 선 연결/중복 표시 개선 및 관련 좌표 회귀. 완료되지 않으면 별도 Known Issue로 명시 |

이번 감사에서 사용자에게 위험을 수용받은 항목은 없다. Critical/Major를 임의 Accepted Risk로 처리하지 않는다. Major까지 해결되지 않으면 PASS는 불가하다.

## 8. 명세 확인 및 기존 허용 범위

- DBG-F001의 클릭 시 draft를 확정/취소/유지할 세부 정책은 문서에 명확히 정리할 필요가 있다. 상태 불일치 자체는 수정 대상이며 첨부 테스트는 확정 정책의 기준 사례다. 코더는 사용자 요청과 기존 draft 보존 계약을 함께 대조한다.
- medium/thick이 TUI에서 같은 굵은 Unicode glyph로 보이는 것은 designs.md의 기존 한계다. XLSX에는 다른 종류로 저장되므로 이번 감사의 별도 실패 항목으로 올리지 않았다.
- CSV의 추론된 타입, XLS 원본 수식 미보존, GSHEET 공개 snapshot, Excel 전용 객체 미보존은 문서화된 형식/범위다. 추가 제품 요구로 바꾸려면 명세를 먼저 정리한다.
- 신고된 특정 파일의 실제 실패는 재현 파일/오류/진입 경로가 없어 원인 미확정이다. 확인된 DBG-F003~005를 특정 사용자 파일의 확정 원인이라고 단정하지 않는다.

## 9. 재현 및 재감사 명령

프로젝트 루트 PowerShell에서 실행한다. 제품 변경 전에는 신규 회귀의 **exit 1 / 11 failed**가 현재 보고서와 일치하는 결과다.

```powershell
& .\.runtime\python315\python.exe -m pytest -q --basetemp docs/audit/evidence_1/pytest_recheck
& .\.runtime\python315\python.exe -m pytest -q docs/audit/evidence_1/test_audit_regressions.py --basetemp docs/audit/evidence_1/regression_recheck
& .\.runtime\python315\python.exe -m ruff check texel tests scripts
& .\.runtime\python315\python.exe -m ruff format --check texel tests scripts
```

독립 관찰 도구: `probe_ui.py`, `layout_probe.py`, `domain_probe.py`, `extra_probe.py`, `command_sweep.py`, `mcp_sweep.py`, `portable_probe.py` (마지막은 bundle 경로 인자 필요). 각 실행은 감사 폴더에 새 fixture 디렉터리를 만든다. JSON과 log를 덮어쓰는 도구가 있으므로 현재 증거를 별도 보존하거나 새로운 evidence 디렉터리를 사용한다. 원본 fixture와 initial/final 로그를 임의 삭제하지 않는다.

코더 재감사는 원래 finding ID를 유지한다. 문서 기준→회귀 RED→수정→GREEN→관련 회귀를 기록하고, 제품 변경 후 새 output 패키지를 만들어 현재 소스·wheel·portable 일치와 Windows 공개 입력을 확인한다. 유효한 과거 증거를 이유 없이 전부 복제할 필요는 없지만 수정된 경로는 갱신한다.

공식 참조: [Textual 테스트와 실제 클릭](https://textual.textualize.io/guide/testing/), [Select 동작](https://textual.textualize.io/widgets/select/), [Python sqlite3 연결](https://docs.python.org/3/library/sqlite3.html#sqlite3.connect). 최신 설명은 보조 자료이며 최종 원인은 설치된 Textual 8.2.8 코드 및 제품의 실행 결과로 판단했다.

## 10. 최종 판정 및 코더 인계

**HOLD — 기능 정상 판정 불가.** 감사 작업 자체는 완료했다. 정상 대표 경로와 실패 재현을 구분했고, 수정은 수행하지 않았다. 11건의 우선순위·원인·코드 위치·재감사 조건과 실행 자료를 제공한다. 최종 인계 파일은 `C:\LocalDev\python\Texel\docs\audit\audit_report_1.md`이며 개별 목록은 `feature_matrix_1.md`에 있다.

```text
C:\LocalDev\python\Texel\docs\audit\audit_report_1.md와 feature_matrix_1.md를 읽고, 각 finding을 현재 사용자 요청·프로젝트 문서·실제 코드와 대조해 검증한 뒤 우선순위대로 필요한 수정을 진행하세요. 계약/설계/로드맵을 먼저 동기화하고 원본 감사 보고서는 수정하지 마세요. evidence_1/test_audit_regressions.py의 RED를 재현한 뒤 GREEN과 관련 전체 테스트·Ruff·Windows 공개 입력·새 wheel/portable 검증을 기록하세요. 기존 사용자 파일과 미검증 범위를 보존하고, 기능 삭제나 기준 축소로 통과시키지 마세요. 커밋·푸시·외부 배포는 별도 사용자 요청 없이는 하지 마세요.
```
