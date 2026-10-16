# 감사 1 수정 작업 기준

작성: 2026-10-11 (Asia/Seoul). 근거: 사용자 수정 요청, audit_report_1.md, spec.md, designs.md, 실제 제품 코드 및 세 AI 표준. Git 저장소 없음. 원본 보고서와 evidence_1은 보존한다. 결과는 remediation_results_1.md와 evidence_remediation_1에 기록한다.

## 대조 및 실행 순서

11건 모두 현재 문서의 기능/데이터 보존 계약과 코드의 원인 경로가 일치한다. 아래 기대 동작을 기준으로 원본 독립 회귀 RED를 재실행하고, 제품 회귀로 편입한 동일 assertion과 추가 경계 검사를 GREEN으로 만든다.

| 순서 | finding / 계약 근거 | 원인 파일 | 수정 / 완료 기준 |
|---|---|---|---|
| 1 | DBG-F002 / 정수 보존, 공용 채우기 | editing.py | 표시 반올림을 직렬화에서 제거. 초기 숫자 raw 보존, bool/비수치/비유한 값 거부. TUI/MCP, 큰 정수·음수·소수·단일 seed, 재열기·CSV·undo/redo |
| 2 | DBG-F001 / draft 대상과 revision 캡처 | ui/grid.py, ui/app.py | 마우스 선택 변경 전에 draft 확정. 실패 시 선택/편집 대상/원문 유지하고 수식줄 포커스 복구. 클릭·Shift·드래그·더블클릭·충돌/검증 실패 |
| 2 | DBG-F003 / 실패 시 문서 보존 | model.py, ui/actions.py | filter/rule/chart/name/숨김/크기 메타데이터를 candidate에서 검증. 공개 열기 실패 시 session/path/revision/내용 보존 |
| 2 | DBG-F005 / 읽기와 생성 구별 | store.py, exchange.py | 기존 native는 읽기 전용 검사. 0바이트/빈·다른 DB/손상 입력은 오류와 bytes/schema 보존. 명시적 미존재 경로 생성 유지 |
| 2 | SEC-F001 / 잠긴 셀 삭제 차단 | session.py, editing.py | deepcopy 객체 대응으로 삭제/재배치/rename 대상 추적. 보호 시트 삭제는 보호 해제 요구. 첫/중간/마지막·다른 시트 삭제·TUI/MCP·undo/redo |
| 3 | IMP-F001 / 80×24 및 100×30 버튼 접근 | ui/dialogs.py, ui/context_menu.py | title/error/footer 높이 예약, body만 스크롤. 80×24/100×30/120×40·resize·Select·오류 상태 실제 클릭 |
| 3 | DBG-F006 / 명령 1회 실행 | ui/context_menu.py | 메뉴 외부 좌표 클릭과 목록 선택 종료 분리, 단일 dismiss. 처음/중간/끝·End/휠/Enter/Escape/외부 클릭·revision/stack |
| 4 | IMP-F002 / 병합 외곽 이동 | ui/app.py, ui/grid.py | 확정·방향키 공용 상대 이동. Enter/Tab/Shift+Tab, 숨김/필터 경계, Ctrl+Enter 유지 |
| 4 | IMP-F003 / 동결 후 탐색 | ui/grid.py | 실제 열 폭으로 동결 예산 계산, 스크롤 열 최소 4칸 확보. 넓은/숨긴 동결·resize·주소/키/휠/hit-test |
| 4 | DBG-F004 / 교환 원본 저장 기본값 | __main__.py, ui/app.py | CLI와 Ctrl+O 모두 원본 path 전달 및 같은 형식 안내. CSV/TSV/XLSX 원본 기본값, XLS/GSHEET .xlsx 변환 기본값 |
| 5 | IMP-F004 / 공유 물리 경계 | ui/grid_render.py | 열 시작 한 칸에 공유 선을 그린다. 내용/rule의 joint 좌표 일치, 마지막 외곽은 마지막 칸. 너비와 hit-test 유지. thin/thick/double·충돌·병합·숨김/동결 |

## 검증과 종료 조건

- Python: .runtime/python315/python.exe. 원본 보고서 SHA256 및 수정 전 제품 파일 manifest를 새 증거 디렉터리에 저장한다.
- RED: `-m pytest -q docs/audit/evidence_1/test_audit_regressions.py --basetemp docs/audit/evidence_remediation_1/red_tmp`.
- 각 수정 후 finding 회귀와 관련 기존 회귀를 실행하고 로그를 남긴다. 전체 `-m pytest -q`, `-m ruff check texel tests scripts`, `-m ruff format --check texel tests scripts`가 통과해야 한다.
- Windows ConPTY에서 실제 키/SGR 마우스 입력 → 셀 저장/메뉴 명령/정상 종료를 검증한다. 자동 입력과 사람의 IME/폰트/장시간 검증은 구분한다.
- 새 wheel/portable을 output/에 생성하여 현재 소스와 bytes 대조, portable 자체 Python·모듈 및 wheel 설치본 CLI/MCP stdio·수정 UI 경로를 확인한다. 기존 output artifact는 보존한다.
- 원본 보고서 hash 불변과 모든 finding의 결과/남은 한계를 기록한다. 커밋/외부 배포는 이번 범위에 없다. 기능/화면 크기/실패 assertion을 축소하지 않는다.

## 주요 결정

native schema 1은 유지한다. 시트 보호는 인증이 아닌 기존 편집 무결성 계약이다. Session의 기존 시트 객체와 복제 객체 대응은 메모리 내에서만 관리하여 저장 ID를 추가하지 않는다. 클릭 확정 정책은 기존 우클릭/주소/시트 전환 정책과 정렬한다. 수치 계산의 Python float 의미는 유지하며 표시 문자열로 값이 훼손되는 경로만 제거한다.

수정 배포 검증물은 호환성 유지 bugfix 버전 0.2.1로 구별한다. 0.2.0 wheel/portable을 덮어쓰지 않고 기존 artifact를 보존하기 위한 로컬 버전이며 외부 게시/태그/릴리스 작업은 하지 않는다.

## 검토 초점

초기 seed raw/수식 보존, 충돌 후 마우스 포커스, 삭제 후 이동한 보호 시트, 깨진 메타데이터의 예외 변환, 부모 clipping과 지연 OptionSelected 순서를 직접 회귀로 확인한다. 보고서의 특정 사용자 파일 원인·IME·다른 OS·장시간은 별도 미확정 범위다.

## 독립 코드 리뷰의 추가 경계

기존 finding 내 Important 3건을 별도 RED→GREEN으로 닫는다: DBG-F003의 active_sheet 문자열/freeze float 타입, IMP-F004의 숨김/동결 비연속 열 공유선, IMP-F003의 활성 열 가용 폭 1칸. active_sheet/freeze는 실제 int로 검증하고 비연속 가시 경계는 앞 그룹의 right와 뒤 그룹의 left 중 strongest로 resolve한다. 활성 열의 화면 폭이 4칸 미만이면 left를 이동한다. 기존 병합 outline 회귀의 고정 36좌표는 공유 경계의 가시 열 시작(37)로 동기화하며 선 존재 및 content/rule 연결 assertion을 유지한다.

공유 칸에서 가로선이 세로선과 교차하면 strongest 스타일의 joint(┼/╋/╬)를 사용하고 내용 줄은 해당 세로 glyph를 유지한다. 기존 병합 outline 회귀도 이전 분리된 선 칸 대신 같은 위치의 교차점과 내용 선을 각각 검사한다.

중간 수정의 메뉴 종료 플래그 `_closing`이 Textual MessagePump 내부 필드와 충돌해 Prune를 거부했다. async task stack으로 원인을 확인하고 제품 플래그를 `_dismiss_requested`로 구분했다. 실패 로그와 stack은 보존하며 현재 회귀 GREEN으로 확인한다.

Windows 연속 입력에서 Ctrl+P 직후 검색 문자가 모달 mount 전 이전 grid로 전달되어 셀에 입력되는 추가 경계를 관찰했다. DBG-F001의 입력 대상 일관성 관련 범위로 포함한다. 비활성 화면의 grid에 이미 대기 중인 키는 모달의 첫 layout/focus 이후 활성 위젯에 순서대로 전달하고 이전 셀을 변경하지 않는다. 결합 패킷 RED→GREEN과 native 입력을 추가한다.

최종 native 확인에서 Ctrl+P 자체의 비우선 binding 처리도 첫 문자들을 grid로 보내는 것을 확인했다. Ctrl+P를 priority binding으로 처리하고 CommandDialog가 mount/포커스 전 도착한 문자와 Enter를 첫 layout 후 검색 입력/검색 확정으로 처리한다. App 전체 입력 큐의 결합 Ctrl+P+검색 RED를 추가하며 셀 raw 불변을 완료 조건으로 둔다.

첫 portable Run.cmd 검사에서 클릭+빠른 입력 확정 후 B4에 stale Focus가 draft를 다시 만드는 현상을 관찰했다(B3=7 보존, B4 draft=7 → 다음 명령에서 B4에도 저장). 설치된 Widget.focus는 call_later이며 설계의 동기 포커스 전환과 달랐다. 편집 시작/성공/취소/실패 및 grid 마우스 포커스는 public Screen.set_focus로 동기 전환한다. begin→commit 직후 focused/editing/raw 회귀 RED→GREEN, portable native 재확인 및 소스 변경에 따른 전체 gate/새 bundle 재빌드를 수행한다. 첫 bundle/ZIP과 wheel 사본은 실패 증거로 보존한다.
