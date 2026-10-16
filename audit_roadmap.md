# 검증 로드맵

현재 작업(2026-10-15): `docs/upgrades/0.3.0-plan.md` F1~F5 / S1~S8. 계산·표·진단·batch/preview·MCP·TUI의 단계별 RED→GREEN 후 전체 회귀/Ruff, Windows ConPTY, 새 0.3.0 wheel/portable 실행 및 소스 동일성을 확인한다. 결과와 한계는 `docs/upgrades/0.3.0-results.md`에 기록한다. 과거 감사·0.2.1 증거는 당시 상태의 기록으로 유지한다.

2026-10-10. 기준: spec.md, implementation_plan.md, 실제 코드/테스트. 이는 체크포인트 기록이며 전면 감사 PASS 보고서가 아니다.

| 단계 | 완료 기준 | 현재 증거 |
|---|---|---|
| 도메인/수식 | 참조/오류/순환/문자열/숫자/날짜 안전성 | pytest 및 리뷰 회귀 |
| 편집/저장 | 원자성/검증/보호/undo/redo/revision | 재실행·충돌·구조 변경 테스트 |
| 교환/분석 | CSV/XLSX 왕복과 계산값 집계 | 왕복·정밀 숫자·피벗·중복 테스트 |
| TUI | 공개 키/마우스/모달 경로 | Pilot + Windows 실제 PTY |
| MCP | 도구 호출→저장→TUI 관찰 | 실제 stdio client/subprocess |
| 배포 | wheel/portable에서 실행 | 빌드 + portable stdio/PTY |

최종 실행 명령/결과/성능/리뷰 수정은 IMPLEMENTATION_SUMMARY.md에 있다. 코드 변경이 없으면 이미 유효한 native 입력 증거를 반복하지 않는다. 해당 경로의 변경/새 실패가 생기면 관련 테스트와 native 증거를 갱신한다.

후속 장비 검증: 한국어 IME 조합과 취소, Windows Terminal 설정별 마우스/폰트, 화면 확대/접근성, 장시간 문서 작업, Linux/macOS 터미널, 실제 AI 호스트 등록. 수행 전에는 해당 항목을 완료로 표시하지 않는다.

감사 1 수정 작업 (2026-10-11): 원본 docs/audit/audit_report_1.md의 HOLD는 감사 당시 기록으로 보존한다. 수정 계약과 finding별 완료 조건은 docs/audit/remediation_plan_1.md, 실행 결과는 docs/audit/remediation_results_1.md를 기준으로 한다. 독립 회귀 11건과 추가 데이터/입력/화면 경계, 전체 pytest/Ruff, Windows ConPTY 및 0.2.1 wheel/portable 소스 일치·자체 실행을 수정 작업 종료 gate로 적용한다.
