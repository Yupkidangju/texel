# Texel 감사 1 기능 검증표

작성: 2026-10-11. 기초 테스트 160개 통과. 명령표는 120×40에서 검색 → 명령 실행 → 양식 적용 → SQLite 재읽기까지의 대표 통합 경로다. 모든 경계의 정상 판정을 뜻하지 않는다. 양식 필드를 직접 설정한 사례와 물리 입력 검사를 구분한다. 일부 초기 무변경 명령은 재료가 없는 상태의 동작이며, 해당 동작의 실효 검증은 기존 테스트도 함께 참조한다.

| 메뉴 | 명령 | 진입 → 종료 | 영속 상태 일치 | 관련 발견 |
|---|---|---|---|---|
| file | 새 통합 문서 (`new`) | FileDialog → Screen | 확인 | 대표 경로 확인 |
| file | 열기 / 가져오기 (`open`) | FileDialog → Screen | 확인 | DBG-F003, DBG-F005 |
| file | 저장 (`save`) | FileDialog → Screen | 확인 | DBG-F004 |
| file | 다른 이름으로 저장 / 내보내기 (`export`) | FileDialog → Screen | 확인 | 대표 경로 확인 |
| file | 백업 (`backup`) | FileDialog → Screen | 확인 | 대표 경로 확인 |
| file | 분석 예제 열기 (`demo`) | Screen → Screen | 확인 | 대표 경로 확인 |
| file | 종료 (`quit`) | Screen → Screen | 확인 | 대표 경로 확인 |
| edit | 실행 취소 (`undo`) | Screen → Screen | 확인 | 대표 경로 확인 |
| edit | 다시 실행 (`redo`) | Screen → Screen | 확인 | 대표 경로 확인 |
| edit | 복사 (`copy`) | Screen → Screen | 확인 | 대표 경로 확인 |
| edit | 잘라내기 (`cut`) | Screen → Screen | 확인 | 대표 경로 확인 |
| edit | 붙여넣기 (`paste`) | Screen → Screen | 확인 | 대표 경로 확인 |
| edit | 전치 붙여넣기 (`transpose`) | Screen → Screen | 확인 | 대표 경로 확인 |
| edit | 선택하여 붙여넣기 (`paste_special`) | FormDialog → Screen | 확인 | 대표 경로 확인 |
| edit | 내용 지우기 (`clear`) | Screen → Screen | 확인 | 대표 경로 확인 |
| edit | 내용과 서식 지우기 (`clear_all`) | Screen → Screen | 확인 | 대표 경로 확인 |
| edit | 서식 지우기 (`clear_formats`) | Screen → Screen | 확인 | 대표 경로 확인 |
| edit | 아래로 채우기 (`fill_down`) | Screen → Screen | 확인 | 대표 경로 확인 |
| edit | 오른쪽으로 채우기 (`fill_right`) | Screen → Screen | 확인 | 대표 경로 확인 |
| edit | 연속 숫자 채우기 (`series`) | Screen → Screen | 확인 | DBG-F002 |
| edit | 찾기 (`find`) | FormDialog → Screen | 확인 | 대표 경로 확인 |
| edit | 모두 바꾸기 (`replace`) | FormDialog → Screen | 확인 | 대표 경로 확인 |
| view | 주소 / 범위 이동 (`goto`) | Screen → Screen | 확인 | 대표 경로 확인 |
| view | 틀 고정 (`freeze`) | Screen → Screen | 확인 | IMP-F003 |
| view | 틀 고정 해제 (`unfreeze`) | Screen → Screen | 확인 | DBG-F006 (우클릭 경로) |
| view | 행 숨기기 (`hide_rows`) | Screen → Screen | 확인 | 대표 경로 확인 |
| view | 열 숨기기 (`hide_columns`) | Screen → Screen | 확인 | 대표 경로 확인 |
| view | 숨김 모두 해제 (`unhide`) | Screen → Screen | 확인 | 대표 경로 확인 |
| view | 열 너비 (`width`) | FormDialog → Screen | 확인 | 대표 경로 확인 |
| view | 열 자동 맞춤 (`autofit`) | Screen → Screen | 확인 | 대표 경로 확인 |
| view | 행 높이 (`row_height`) | FormDialog → Screen | 확인 | 대표 경로 확인 |
| view | 행 높이 자동 맞춤 (`autofit_rows`) | Screen → Screen | 확인 | 대표 경로 확인 |
| view | 수식 원문 표시 (`formulas`) | Screen → Screen | 확인 | 대표 경로 확인 |
| view | 테마 (`theme`) | Screen → Screen | 확인 | 대표 경로 확인 |
| view | 언어 (`language`) | Screen → Screen | 확인 | 대표 경로 확인 |
| insert | 시트 추가 (`add_sheet`) | FormDialog → Screen | 확인 | 대표 경로 확인 |
| insert | 시트 이름 바꾸기 (`rename_sheet`) | FormDialog → Screen | 확인 | 대표 경로 확인 |
| insert | 시트 복제 (`duplicate_sheet`) | FormDialog → Screen | 확인 | 대표 경로 확인 |
| insert | 시트 삭제 (`delete_sheet`) | FormDialog → Screen | 확인 | SEC-F001 |
| insert | 행 삽입 (`insert_rows`) | FormDialog → Screen | 확인 | 대표 경로 확인 |
| insert | 행 삭제 (`delete_rows`) | FormDialog → Screen | 확인 | 대표 경로 확인 |
| insert | 열 삽입 (`insert_columns`) | FormDialog → Screen | 확인 | 대표 경로 확인 |
| insert | 열 삭제 (`delete_columns`) | FormDialog → Screen | 확인 | 대표 경로 확인 |
| insert | 이름 범위 정의 (`named_range`) | FormDialog → Screen | 확인 | 대표 경로 확인 |
| insert | 이름 범위 목록 (`names`) | TextDialog → TextDialog | 확인 | 대표 경로 확인 |
| format | 셀 서식 (`style`) | FormDialog → Screen | 확인 | IMP-F001 |
| format | 테두리 / 선 굵기 (`borders`) | FormDialog → Screen | 확인 | IMP-F001, IMP-F004 |
| format | 굵게 (`bold`) | Screen → Screen | 확인 | 대표 경로 확인 |
| format | 기울임 (`italic`) | Screen → Screen | 확인 | 대표 경로 확인 |
| format | 취소선 (`strike`) | Screen → Screen | 확인 | 대표 경로 확인 |
| format | 셀 내용 줄바꿈 (`wrap`) | Screen → Screen | 확인 | 대표 경로 확인 |
| format | 밑줄 (`underline`) | Screen → Screen | 확인 | 대표 경로 확인 |
| format | 셀 메모 (`note`) | FormDialog → Screen | 확인 | 대표 경로 확인 |
| format | 셀 병합 (`merge`) | FormDialog → Screen | 확인 | IMP-F002 |
| format | 병합하고 가운데 맞춤 (`merge_center`) | FormDialog → Screen | 확인 | IMP-F002 |
| format | 셀 분할 (병합 해제) (`unmerge`) | Screen → Screen | 확인 | 대표 경로 확인 |
| format | 입력 유효성 검사 (`validation`) | FormDialog → Screen | 확인 | IMP-F001 |
| format | 유효성 검사 해제 (`clear_validation`) | Screen → Screen | 확인 | 대표 경로 확인 |
| format | 조건부 강조 (`conditional`) | FormDialog → Screen | 확인 | IMP-F001 |
| format | 조건부 강조 해제 (`clear_conditional`) | Screen → Screen | 확인 | 대표 경로 확인 |
| format | 선택 셀 잠금 전환 (`lock`) | Screen → Screen | 확인 | 대표 경로 확인 |
| format | 시트 보호 전환 (`protect`) | Screen → Screen | 확인 | 대표 경로 확인 |
| data | 정렬 (`sort`) | FormDialog → Screen | 확인 | IMP-F001 |
| data | 필터 (`filter`) | FormDialog → Screen | 확인 | IMP-F001 |
| data | 필터 해제 (`clear_filter`) | Screen → Screen | 확인 | 대표 경로 확인 |
| data | 중복 제거 (`deduplicate`) | FormDialog → Screen | 확인 | 대표 경로 확인 |
| analysis | 데이터 프로파일 / 통계 (`profile`) | TextDialog → TextDialog | 확인 | 대표 경로 확인 |
| analysis | 피벗 테이블 (`pivot`) | FormDialog → Screen | 확인 | IMP-F001 |
| analysis | 차트 (`chart`) | FormDialog → TextDialog | 확인 | 대표 경로 확인 |
| help | 도움말 (`help`) | TextDialog → TextDialog | 확인 | 대표 경로 확인 |
| help | 함수 목록 (`functions`) | TextDialog → TextDialog | 확인 | 대표 경로 확인 |
| help | 변경 이력 (`history`) | TextDialog → TextDialog | 확인 | 대표 경로 확인 |
| help | 셀 원문 / 메모 검사 (`inspect`) | TextDialog → TextDialog | 확인 | 대표 경로 확인 |
| help | MCP 연결 안내 (`mcp_info`) | TextDialog → TextDialog | 확인 | 대표 경로 확인 |

## MCP 도구 30개

메모리 전송 SDK Client로 실제 도구를 호출했다. stdio/다른 프로세스/공용 TUI 동기화는 baseline 및 portable 별도 증거다. 도구별 대표 정상 입력이며 모든 인자 조합의 보장은 아니다.

| 도구 | 응답 | 저장 revision |
|---|---|---|
| `workbook_info` | ok | 1 |
| `read_range` | ok | 1 |
| `write_range` | ok | 2 |
| `fill_formula` | ok | 2 |
| `clear_range` | ok | 2 |
| `copy_range` | ok | 2 |
| `fill_cells` | ok | 1 |
| `format_range` | ok | 2 |
| `set_borders` | ok | 2 |
| `set_row_height` | ok | 2 |
| `edit_sheet` | ok | 2 |
| `change_structure` | ok | 2 |
| `sort_range` | ok | 2 |
| `filter_range` | ok | 2 |
| `find` | ok | 1 |
| `replace` | ok | 2 |
| `profile_range` | ok | 1 |
| `pivot_table` | ok | 2 |
| `chart_range` | ok | 1 |
| `create_chart` | ok | 2 |
| `deduplicate` | ok | 1 |
| `set_note` | ok | 2 |
| `set_validation` | ok | 2 |
| `merge_range` | ok | 2 |
| `define_name` | ok | 2 |
| `undo` | ok | 2 |
| `redo` | ok | 3 |
| `import_file` | ok | 2 |
| `export_file` | ok | 1 |
| `backup` | ok | 1 |

## 수식 함수 69개

레지스트리 전부에 독립 기대값이 있는 기본 예제 하나를 계산했다. TODAY는 실행 장비 날짜와 대조했다. 전체 Excel 의미 또는 모든 오류 인자의 검증으로 확대하지 않는다. 기존 수식 오류/순환/참조/상한 회귀와 함께 해석한다.

| 함수 | 수식 | 기대값 | 실제값 |
|---|---|---|---|
| ABS | `=ABS(-3)` | 3 | 3 |
| AND | `=AND(TRUE,FALSE)` | False | False |
| AVERAGE | `=AVERAGE(2,4)` | 3 | 3 |
| CEILING | `=CEILING(3,2)` | 4 | 4 |
| COLUMN | `=COLUMN(B1)` | 2 | 2 |
| CONCAT | `=CONCAT("a","b")` | ab | ab |
| CONCATENATE | `=CONCATENATE("a","b")` | ab | ab |
| COUNT | `=COUNT(1,2,"x")` | 2 | 2 |
| COUNTA | `=COUNTA(1,"x")` | 2 | 2 |
| COUNTBLANK | `=COUNTBLANK(A5:A6)` | 2 | 2 |
| COUNTIF | `=COUNTIF(A1:A3,">1")` | 2 | 2 |
| COUNTIFS | `=COUNTIFS(A1:A3,">1",B1:B3,"<30")` | 1 | 1 |
| DATE | `=DATE(2026,10,11)` | 2026-10-11 | 2026-10-11 |
| DAY | `=DAY(DATE(2026,10,11))` | 11 | 11 |
| DAYS | `=DAYS(DATE(2026,10,11),DATE(2026,10,10))` | 1 | 1 |
| EXP | `=EXP(0)` | 1 | 1.0 |
| FIND | `=FIND("b","abc")` | 2 | 2 |
| FLOOR | `=FLOOR(3,2)` | 2 | 2 |
| IF | `=IF(TRUE,7,1/0)` | 7 | 7 |
| IFERROR | `=IFERROR(1/0,9)` | 9 | 9 |
| INDEX | `=INDEX(A1:B3,2,2)` | 20 | 20 |
| INT | `=INT(-1.2)` | -2 | -2 |
| ISBLANK | `=ISBLANK(A5)` | True | True |
| ISERROR | `=ISERROR(1/0)` | True | True |
| ISNUMBER | `=ISNUMBER(2)` | True | True |
| ISTEXT | `=ISTEXT("x")` | True | True |
| LEFT | `=LEFT("abc",2)` | ab | ab |
| LEN | `=LEN("한국")` | 2 | 2 |
| LN | `=LN(1)` | 0 | 0.0 |
| LOG | `=LOG(100)` | 2 | 2.0 |
| LOWER | `=LOWER("AB")` | ab | ab |
| MATCH | `=MATCH(2,A1:A3,0)` | 2 | 2 |
| MAX | `=MAX(1,2)` | 2 | 2 |
| MEDIAN | `=MEDIAN(1,3,2)` | 2 | 2 |
| MID | `=MID("abc",2,1)` | b | b |
| MIN | `=MIN(1,2)` | 1 | 1 |
| MOD | `=MOD(7,3)` | 1 | 1 |
| MONTH | `=MONTH(DATE(2026,10,11))` | 10 | 10 |
| NOT | `=NOT(TRUE)` | False | False |
| OR | `=OR(TRUE,FALSE)` | True | True |
| POWER | `=POWER(2,3)` | 8 | 8 |
| PRODUCT | `=PRODUCT(2,3)` | 6 | 6 |
| PROPER | `=PROPER("hello world")` | Hello World | Hello World |
| REPT | `=REPT("a",2)` | aa | aa |
| RIGHT | `=RIGHT("abc",2)` | bc | bc |
| ROUND | `=ROUND(2.675,2)` | 2.68 | 2.68 |
| ROUNDDOWN | `=ROUNDDOWN(-1.29,1)` | -1.2 | -1.2 |
| ROUNDUP | `=ROUNDUP(-1.21,1)` | -1.3 | -1.3 |
| ROW | `=ROW(A3)` | 3 | 3 |
| SEARCH | `=SEARCH("B","abc")` | 2 | 2 |
| SQRT | `=SQRT(4)` | 2 | 2.0 |
| STDEV | `=STDEV(1,2,3)` | 1 | 1.0 |
| STDEV.P | `=STDEV.P(1,2,3)` | 0.816496580927726 | 0.816496580927726 |
| STDEV.S | `=STDEV.S(1,2,3)` | 1 | 1.0 |
| SUBSTITUTE | `=SUBSTITUTE("aba","a","x")` | xbx | xbx |
| SUM | `=SUM(1,2)` | 3 | 3 |
| SUMIF | `=SUMIF(A1:A3,">1")` | 5 | 5 |
| SUMIFS | `=SUMIFS(B1:B3,A1:A3,">1")` | 50 | 50 |
| SUMSQ | `=SUMSQ(2,3)` | 13 | 13 |
| TEXTJOIN | `=TEXTJOIN("-",TRUE,"a","b")` | a-b | a-b |
| TODAY | `=TODAY()` | 2026-10-11 | 2026-10-11 |
| TRIM | `=TRIM("  a  b ")` | a b | a b |
| UPPER | `=UPPER("ab")` | AB | AB |
| VALUE | `=VALUE("12")` | 12 | 12.0 |
| VAR.S | `=VAR.S(1,2,3)` | 1 | 1 |
| VLOOKUP | `=VLOOKUP(2,A1:B3,2,FALSE)` | 20 | 20 |
| WEEKDAY | `=WEEKDAY(DATE(2026,10,11))` | 1 | 1 |
| XLOOKUP | `=XLOOKUP(2,A1:A3,B1:B3)` | 20 | 20 |
| YEAR | `=YEAR(DATE(2026,10,11))` | 2026 | 2026 |
