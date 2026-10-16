# Texel 구현 계획

기준: spec.md, designs.md. 작성: 2026-10-10. 실행 방식: 현재 세션에서 순차 구현. 프로젝트 정책에 따라 별도 계획 승인/커밋을 추가하지 않는다.

## 전역 기준

Python 3.15 대상, 3.14 이상 문법. 모든 작업 파일/런타임은 프로젝트 내부. `.texel` schema_version=1. 도메인은 UI/MCP에서 공용. 주소 상한 1,048,576×16,384, 저장 셀 상한 200,000, 범위 응답 2000셀, 변경 요청 10000셀. 사용자 데이터/기존 규칙 문서는 덮어쓰지 않는다.

## 검토 초점

편집 중 외부 revision 변경과 draft 손실; 문자열 안의 A1이 참조로 바뀌는 오류; 구조 변경/복사의 절대 참조; 실패한 가져오기/저장의 원본 보존; 한글 폭과 마우스 좌표 불일치. 해당 동작의 테스트를 각 단계에 넣는다.

## 작업 순서

- [x] 1. 도메인/수식: `texel/model.py`, `addresses.py`, `formula.py`, `functions.py`; `tests/test_formula.py`, `test_model.py`의 정상/오류/참조/안전성 기대값을 먼저 작성하고 실패 확인 후 구현.
- [x] 2. 편집/영속성: `editing.py`, `store.py`, `session.py`; 편집/복사/구조변경/검증/저장/undo/redo/경쟁 테스트를 실패→성공으로 검증. `Session.apply(label, mutation, expected_revision)` 인터페이스 고정.
- [x] 3. 교환/분석: `exchange.py`, `analysis.py`; CSV/XLSX 왕복 및 기술통계/정렬/필터/중복/피벗/차트 테스트. 안전한 임시 파일 교체와 경로 경계 확인.
- [x] 4. TUI: `ui/app.py`, `ui/grid.py`, `ui/dialogs.py`, `i18n.py`; Pilot에서 공개 키/클릭/드래그/메뉴 경로 테스트. 80×24, 120×40, resize, 외부 수정 중 편집 검증.
- [x] 5. MCP: `mcp_server.py`, CLI; 실제 subprocess stdio 연결, 도구 호출, revision/페이지/경로/오류 검사와 TUI/새 Session 가시성 테스트.
- [x] 6. 실행/검증/패키징: `run.ps1`, `test.ps1`, `build.ps1`; 실제 Python 버전, 전체 테스트/정적 검사, PTY, wheel/portable root output 실행. README/BUILD_GUIDE/CHANGELOG/IMPLEMENTATION_SUMMARY에 결과와 미검증 사항 기록.

## 단계별 계약

모델 `Workbook.to_dict/from_dict` ↔ Store 직렬화; 수식 `Evaluator.value(sheet, row, col)` ↔ 모든 소비자; 편집 함수는 Workbook만 변경하며 I/O 없음; Session이 변경의 검증/원자성을 소유; 파일/분석은 도메인을 통해 계산; UI/MCP는 Session만 통해 변경한다.

각 단계에서 테스트를 실제 실행하고 결과를 `IMPLEMENTATION_SUMMARY.md`에 기록한다. 빌드/헤드리스 UI/프로토콜/실제 터미널/사람의 IME 확인은 서로 다른 증거다. 새 실패나 변경 없이 닫힌 검증을 반복하지 않는다.

## 독립 리뷰 수정 작업 단위

별도 reviewer가 현재 소스에서 재현한 8개 Important finding과 행 머리글 좌표 문제를 한 수정 작업 단위로 처리한다. 각각 테스트 RED를 확인한 뒤 수정하고 전체 검증을 수행한다.

- R1: 표시 문자열을 분석의 동일성 키로 사용하지 않는다. 큰 인접 숫자의 고유값/중복/피벗 그룹을 보존한다.
- R2/R3: 참조처럼 생긴 시트 이름과 역순 범위를 구조 변경/복사 시 보존한다.
- R4/R5: 외부 시트 삭제 및 오래 열린 변경 모달에서 입력/revision 충돌을 보존하고 예외로 종료하지 않는다.
- R6: REPT/연결/치환은 결과 길이를 할당 전 검사한다.
- R7: 셀/수식줄/메모/오류/다이얼로그의 터미널 제어 문자는 가시 문자로 출력하고 저장 원문은 보존한다.
- R8: 잘못된 SQLite/XLSX 입력은 현재 통합 문서와 모달을 보존하는 사용자 오류로 변환한다.
- R9: 최대 행 번호의 머리글 너비와 마우스 좌표 기준을 동일하게 고정한다. 편집 대상이 달라지는 영향 때문에 Important로 재분류한다.

확인: `pytest tests/test_review_fixes.py tests/test_review_tui.py -q` → 전체 test.ps1 → 새 portable 빌드/stdio/TUI 실행. 사용자 정책에 따라 리뷰를 위해 자동 Git 커밋/외부 작업공간은 만들지 않았다.

## 0.2.0 사용자 피드백 구현

실제 재현: .cache/turn2-repro.json. 병합 렌더 내부 선/방향키 막힘, border 필드 없음, 열기 트리 단일 root, 저장 모달 없음, 우클릭 화면 전환 없음.

- [x] T2-1: BorderEdge/확장 CellStyle/row_heights, 테두리 프리셋·행 높이·서식 삭제·병합 copy/transpose/undo. Native/XLSX 왕복 테스트를 먼저 작성.
- [x] T2-2: 가상 행 슬롯/병합 화면/클릭/방향키/테두리/wrap 렌더. 좌표·문자열·선 굵기 테스트.
- [x] T2-3: FileDialog 드라이브/상위/직접 경로/파일선택/형식/인코딩/덮어쓰기, 실제 open/save/import/export. data 밖 fixture와 손상/권한/충돌 실패 보존 테스트.
- [x] T2-4: 우클릭 ContextMenu 및 셀/행/열 문맥 명령, 확장 Cell Format/Borders/Paste Special/병합 확인. 메뉴에서 실제 데이터를 수정하는 Pilot 테스트.
- [x] T2-5: 기존 명세·명령 카탈로그의 동작 누락 점검, MCP 서식/테두리, 전체 회귀/정적 검사/별도 리뷰/PTY/0.2.0 배포 산출물.
- [x] T2-6: .xls 및 사용자 확인된 공개 .gsheet 가져오기, 호스트/다운로드 경계, 열기/MCP 연결, 변환 저장/의존성/안내 동기화.

독립 리뷰 수정: 내부 paste values의 문자열 타입/결합 정밀도, New/Backup 형식, row height 복사, 동결 viewport, 드라이브 표시, 병합 테두리 중간 선 유지. 근거 .cache/turn2-review/*.py. 각 동작 RED→GREEN 뒤 전체 검증한다.

범위: 승인된 로컬 업무/분석용 기능의 사용 경로 완성. 데이터 손실 방지, 기존 schema 1 읽기, MCP root 보존. 전역 설정/커밋/외부 배포 없이 진행한다.
