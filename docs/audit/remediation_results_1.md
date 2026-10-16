# 감사 1 수정 및 검증 결과

작성: 2026-10-11 (Asia/Seoul). 대상: Texel 0.2.1, Windows x64 / 프로젝트 Python 3.15.0. 기준: 사용자 코딩 요청, 원본 audit_report_1.md, spec.md / designs.md / DESIGN_DECISIONS.md, remediation_plan_1.md와 실제 코드. 원본 감사 보고서는 보존한다. 이 문서는 수정 실행 기록이며 별도 정식 감사의 PASS 판정을 대신하지 않는다.

**결과: 원본 finding 11건 모두 Fixed / Verified (아래 실제 검증 범위). 전체 232개 테스트, Ruff, 소스·portable Windows 입력, 새 wheel/portable 설치본 검증을 통과했다.**

## finding별 문서·코드 대조 및 변경

원본 11건 모두 기존 제품 계약과 실제 원인 경로가 일치했다. 원본 독립 회귀는 수정 전 **11 failed / 13.33초**, 수정 후 동일 원본 파일에서 **11 passed / 14.73초**였다. 원본 회귀를 포맷만 정리해 tests/test_audit_1_regressions.py에도 편입했다. 화면 크기·기능·실패 assertion을 삭제하거나 기준을 낮추지 않았다.

| ID / 우선순위 | 기준과 원인 | 최종 수정 및 검증 |
|---|---|---|
| DBG-F002 / Critical, 1 | spec 정수 보존·공용 채우기; editing.fill_range가 display_value(.12g)를 저장에 사용 | exact_text 저장, 숫자 seed raw 유지, bool/비수치/비유한 시작값 거부. 큰 양·음 정수/소수/수식 단일 seed, native 재열기·CSV·undo/redo, TUI·MCP 실제 stdio |
| DBG-F001 / Major, 2 | designs draft 대상/revision 캡처; grid 클릭은 선택만 바꾸고 이전 draft 유지 | 마우스 변경 전에 확정, 실패 시 cursor/draft/포커스 보존. 클릭·Shift·드래그·더블클릭·수식줄, validation/conflict. Windows에서 발견한 모달/Focus 지연도 아래 추가 회귀로 수정 |
| DBG-F003 / Major, 2 | spec 가져오기 실패 시 현재 문서 보존; Workbook.validate의 UI 소비 메타데이터 누락 | filter/rule/chart/name/숨김/크기 및 active_sheet/freeze 정수 타입 검증. 손상 candidate의 읽기/Session 단계 실패, 공개 Ctrl+O에서 내용/path/revision/모달 입력 및 입력 bytes 유지 |
| DBG-F005 / Major, 2 | spec 기존 입력 보존; exchange가 생성 가능한 Store를 읽기에 호출 | read_only Store와 SQLite mode=ro, 기존 파일은 쓰기 연결 전에 검증. 0바이트/빈 DB/다른 DB 오류 및 bytes 보존, 정상 native 읽기·미존재 경로 생성은 기존 전체 회귀 |
| SEC-F001 / Major, 2 | spec 잠긴 셀 삭제·보호 경계; candidate에 남은 index만 비교 | deepcopy 객체 대응으로 동일 보호 시트 추적, 보호 시트 삭제는 해제 요구. 첫/중간/마지막·locked 유무·rename·다른 시트 삭제·해제 후 삭제·undo/redo·TUI 및 stdio MCP |
| IMP-F001 / Major, 3 | spec 80×24·100×30 버튼 접근; auto body가 footer 공간 소비 | 높이가 제한된 box에 body=1fr, title/error/footer 예약. 세 크기에서 문제 양식 7개 실제 적용, 오류 상태 resize·Select·적용 좌표. FileDialog 기존 회귀 유지 |
| DBG-F006 / Major, 3 | spec 메뉴 명령 실제 실행; Click와 OptionSelected 중복 dismiss | box 화면 좌표로 외부 클릭 구별, 독립 단일 종료 플래그, 목록 실제 가용 높이/resize. 세 크기 End→끝 항목 실제 클릭·revision 1회·stack 1개, Windows SGR unfreeze·정상 종료 |
| IMP-F002 / Major, 4 | designs Enter 아래/Tab 오른쪽/Shift+Tab 왼쪽; 확정은 앵커+1로 복귀 | grid.advance 공용 병합 외곽 계산. Enter/Tab/Shift+Tab·일반 이동·숨김 행 및 기존 Ctrl+Enter 회귀. 설치본 Enter=A4 |
| IMP-F003 / Major, 4 | spec 동결 후 탐색; frozen 열이 먼저 전체 폭을 소비 | 실제 폭 예산, 비동결 최소 4칸, 활성 동결 열 포함, 활성 열 표시 폭 4칸 미만이면 left 보정. 넓은/숨긴 열·resize·가시 셀 hit-test·끝 1칸 회귀 |
| DBG-F004 / Major, 4 | spec 교환 원본 저장 기본값; CLI가 source_path 누락 | TexelApp source_path 전달과 공용 형식 안내. CSV/TSV/XLSX 원본, XLS/GSHEET .xlsx 기본값. 실제 CSV CLI 가져오기→Ctrl+S 및 기존 실제 XLS/GSHEET/파일 경로 회귀 |
| IMP-F004 / Minor, 5 | designs 공용 layout·선 연결; 양 셀의 세로선 두 칸 렌더링 | content/rule에서 공유 경계 한 칸, 비연속 가시 열의 양쪽 strongest 선, 교차점 strongest glyph. thin/thick/double·숨김/동결·병합·hit-test·undo/redo. 기존 outline test도 공유 좌표의 joint와 content를 동시에 검사 |

## 추가 발견과 중간 실패의 처리

- 독립 읽기 전용 리뷰의 Important 3건(메타데이터 타입 / 숨김 열 오른쪽 선 / 활성 열 폭 1칸)은 **6 failed → 6 passed**. review.md, review_red.log, review_green.log에 근거를 남겼다. 후속 독립 재리뷰를 수행했다고 주장하지 않는다.
- Ctrl+P와 검색을 한 native 패킷으로 보냈을 때 첫 문자가 셀에 저장되는 문제를 재현했다. priority binding, 비활성 grid 키 전달, CommandDialog 첫 layout 전 키 큐로 수정했다. 전체 App 키 큐와 이전 grid 큐 각각의 회귀, native_batch_red.json → 현재 native 입력에서 raw 불변으로 확인했다.
- 첫 portable에서 Widget.focus의 call_later 때문에 확정 후 다음 셀에 stale draft가 다시 생겼다. Screen.set_focus로 편집 시작/성공/취소/실패/마우스 전환을 동기화했다. **focus 회귀 RED → 관련 9 passed**, portable_native_initial.json의 B4=7 실패를 보존한다. 이 코드 변경 때문에 전체 검사와 배포본을 다시 생성했다.
- 중간 종료 플래그 `_closing`이 Textual 내부 필드와 충돌한 수정 오류는 async task stack으로 확인하여 `_dismiss_requested`로 분리했다. debug_context_*.log와 중단된 실행 로그를 보존했다.
- 양식 추가 harness의 필터가 데이터 행을 숨겨 빈 행까지 선택된 경우는 명시적 숫자 필터로 fixture를 교정했다. 모달 mount 전에 query한 NoMatches는 harness 대기 누락으로 교정했다. 기존 outline의 두 칸 선 좌표 assertion은 새 단일 공유 칸의 joint/content로 강화했다. full_initial.log의 **219 passed / 4 failed**는 최종 통과 증거가 아니다.

## 검증 결과

| 검증 | 최종 결과 | 증거 |
|---|---|---|
| 원본 독립 회귀 | 11 failed → 11 passed / 14.73초 | red.log, immutable_green.log |
| 전체 pytest | **232 passed / 168.72초**, exit 0 | full_focus.log. 기존 160 + 원본 편입 11 + 추가 경계 61 |
| Ruff check / format | **All checks passed / 51 files already formatted** | ruff_check.log, ruff_format.log |
| Windows 소스 ConPTY | 80×24; draft 클릭 저장, 빠른 모달 전환 2회 raw 보존, B4/B5 thin 적용, 마지막 unfreeze 1회, **exit 0** | native_source_final.json |
| Windows portable Run.cmd | 동일 실제 입력: A1=42/B3=7/B4=8/B5 빈 값, 최종 freeze=(0,0)/revision=7, **exit 0** | native_portable_final.json. 첫 stale Focus 재현과 같은 패턴을 포함 |
| 새 빌드 | build.ps1 -SkipTests **exit 0** | build_final.log. 같은 최종 소스 전체 suite 완료 후 사용 |
| wheel 설치본 | 실제 CSV CLI 원본 저장 기본값, 80×24 UI, stdio 30도구, 큰 정수 9007199254740995 재열기/undo/redo, 보호 삭제 거부 **통과** | wheel_final_install.log, wheel_final_check/result.json |
| portable 자체 Python·모듈 | 위와 같은 검증 **통과**, 모듈/실행 파일 경로가 bundle 내부 | portable_final_check/result.json |
| 소스 일치 | 제품 Python **28/28**: 소스 = wheel ZIP 내용 = wheel 설치본 = portable 폴더 = portable ZIP | package_parity_final.json |
| 원본 감사 보고서 보존 | SHA256 **불변** | original_report_hash.json / package_parity_final.json |

최종 artifact:

- `output/texel_tui-0.2.1-py3-none-any.whl` (79,879 bytes), SHA256 `588282a68c39193b313053c5de427643caa415487a6c35a96132c8acfdbea5d8`.
- `output/Texel-0.2.1-win64-20261011-162957/` 및 같은 이름 `.zip` (33,197,860 bytes), ZIP SHA256 `9fe9698ae5408b33cdea1f32534f1dd4dc8b4fd61fe169c3dc260a3a201d3959`.
- 원본 보고서 SHA256: `6fda0e5ba285a55201cc67b296f2be3b220c724848dd2ac0f67b18436acc64d1`.

설치본 확인 명령:

```powershell
& .\output\Texel-0.2.1-win64-20261011-162957\python\python.exe scripts\verify_distribution.py --package-root output\Texel-0.2.1-win64-20261011-162957 --evidence docs\audit\evidence_remediation_1\portable_recheck_new
```

검증된 현재 자료는 이 결과 문서, 수정 계약, full_focus/Ruff/final package 및 native JSON이다. 원본 감사/evidence_1과 초기·중간 실패 로그는 당시 상태를 재현하는 기록이다. 16:21:12의 첫 0.2.1 bundle/ZIP·wheel 사본은 stale Focus 수정 전 artifact이고 최종 설치본으로 사용하지 않는다. 새로운 형식/기능을 추가하거나 의존성/schema를 바꾸지 않았다.

제품 변경: `texel/{__init__,__main__,editing,exchange,model,session,store}.py`, `texel/ui/{actions,app,context_menu,dialogs,grid,grid_render}.py` 13개 모듈. `tests/test_audit_1_regressions.py`, `tests/test_audit_1_boundaries.py` 추가, 기존 `tests/test_turn2_review_fixes.py` 공유선 assertion 동기화, `scripts/verify_distribution.py` 추가, `pyproject.toml` 버전 갱신. spec/designs/설계 결정/README/CHANGELOG/BUILD_GUIDE/IMPLEMENTATION_SUMMARY/audit_roadmap과 수정 계획/결과를 동기화했다. 최종 소스 diff는 source_diff.patch에 기록했다.

## 증거와 재현

모든 새 증거: docs/audit/evidence_remediation_1/. 원본 evidence_1의 결과 JSON/log를 덮어쓰지 않았다. 새 fixture와 초기 실패 기록을 삭제하지 않았다. 첫 0.2.1 bundle/ZIP은 중간 검증본이며 `wheel_initial_0.2.1.whl`도 사본으로 보존한다. 기존 0.1.0/0.2.0 artifact는 그대로 둔다.

2026-10-16 추적 정리 보충: 위 문단은 당시 보존 상태다. 재생성 입력/pytest 임시물 및 wheel_initial_0.2.1.whl은 현재 Git 트리에서 제외했고 결과 JSON/log/화면 및 생성 코드는 유지했다. 기존 파일은 c5235b9의 같은 경로에서 복구할 수 있다. 상세 목록·해시·검증은 docs/maintenance/2026-10-16-repo-hygiene.md와 removal_manifest_20261016.json을 따른다.

```powershell
& .\.runtime\python315\python.exe -m pytest -q --basetemp docs/audit/evidence_remediation_1/recheck_new
& .\.runtime\python315\python.exe -m pytest -q docs/audit/evidence_1/test_audit_regressions.py --basetemp docs/audit/evidence_remediation_1/original_recheck_new
& .\.runtime\python315\python.exe -m ruff check texel tests scripts
& .\.runtime\python315\python.exe -m ruff format --check texel tests scripts
.\build.ps1
```

Windows 기록의 x/y는 ConPTY 80×24에서 SGR 마우스 좌표다. 자동 키/마우스 escape와 저장 assertion/exit code를 검증했으며 사람의 직접 입력/화면 승인으로 확대하지 않는다. ANSI 출력 청크는 보존하지만 전체 프레임 무손실 녹화라고 주장하지 않는다.

버전 의존 동작은 설치된 Textual 8.2.8 소스 및 [Textual 레이아웃](https://textual.textualize.io/guide/layout/), [Screen API](https://textual.textualize.io/api/screen/), [Python sqlite3 URI](https://docs.python.org/3/library/sqlite3.html#how-to-work-with-sqlite-uris)를 대조했다. 최종 근거는 로컬 실행 결과다.

## 남은 한계

한국어 IME 조합/취소, 실제 터미널·폰트·접근성 장비별 사람의 조작, 장시간/다중 작성자 soak, Linux/macOS 실제 터미널, 실제 AI 호스트 등록은 미검증이다. 신고된 특정 사용자 파일은 제공되지 않아 그 원인을 확정하지 않았다. Python float 산술 자체, Excel 전용 객체 무손실 왕복, 비공개 Google 계정/원격 쓰기는 기존 계약 범위와 한계를 유지한다. 이번 수정은 의존성을 변경하지 않아 알려진 advisory 검사를 새 실행 결과로 주장하지 않는다.

Git 저장소가 없으며 커밋/푸시/태그/외부 배포/계정 설정 작업을 수행하지 않았다. 0.2.1은 로컬 수정·검증 artifact 버전이다. 원본 감사 HOLD는 당시 기록으로 보존한다.
