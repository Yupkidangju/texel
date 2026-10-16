# 로컬 배포물 목록

갱신: 2026-10-16. 공개 배포 현재 기준은 [0.3.1 결과](releases/0.3.1-results.md)와 [GitHub Releases](https://github.com/Yupkidangju/texel/releases)이다. 게시 전에는 결과 문서의 진행 상태를 따른다. 아래 0.3.0은 당시 로컬 검증 산출물과 유지보수 경계의 기록이다.

## 2026-10-15 당시 마지막 검증 배포본: 0.3.0

| 종류 | 프로젝트 루트 기준 경로 | 식별값 |
|---|---|---|
| wheel | `output/texel_tui-0.3.0-py3-none-any.whl` | 98,388 bytes; SHA256 `7a9e8f7dccc8f217b6f0655d5e1e3d2b19418528e45d812d29145758a6c7e41c` |
| Windows portable | `output/Texel-0.3.0-win64-20261015-154810/` | 포함된 Run.cmd / Demo.cmd / MCP.cmd로 실행 |
| Windows ZIP | `output/Texel-0.3.0-win64-20261015-154810.zip` | 33,220,311 bytes; SHA256 `db7ec7376489f4dc1162d676b69bf8d83ee1dcc523e1964f72b9dda9b11bd0a7` |

배포 당시 39도구/89함수, wheel·portable 자체 Python, Windows ConPTY 입력과 제품 Python 37개 파일 동일성을 검증했다. 정확한 당시 로그와 한계는 위 결과 문서에 있다.

**0.3.0 배포 검증 이후 유지보수 소스와의 경계:** [표기 수정](maintenance/2026-10-15-consistency.md)의 Google User-Agent와 Store 괄호/주석 및 문서 변경은 위 wheel/ZIP에 포함되지 않는다. 2026-10-15에는 버전 상수 0.3.0을 유지하고 Unreleased로 기록했으며 새 배포물을 만들지 않았다. 이 변경은 후속 0.3.1 공개 배포에 포함한다.

## 보존 중인 과거 자료

| 경로/패턴 | 용도 |
|---|---|
| `output/Texel-0.1.0-*`, `texel_tui-0.1.0-*` | 최초 구현 배포 이력 |
| `output/Texel-0.2.0-*`, `texel_tui-0.2.0-*` | 사용자 피드백 기능 배포 이력 |
| `output/Texel-0.2.1-win64-20261011-162112/` 및 ZIP | 수정 전 입력 실패 후보 보존 |
| `output/Texel-0.2.1-win64-20261011-162957/` 및 ZIP, 0.2.1 wheel | 감사 수정 최종 검증 이력 |
| `output/wheel-check*` | wheel 설치 경로 분리를 확인하는 작업 target. 배포본이 아님 |
| `output/portable-verification.json`, `SHA256SUMS.json`, preview/benchmark 파일 | 과거 작업의 공용 이름 산출물. 최신 배포본 선택 기준으로 사용하지 않음 |

보존 자료의 자세한 당시 결과는 docs/audit/remediation_results_1.md와 IMPLEMENTATION_SUMMARY.md의 각 버전 이력에 있다. 이번 목록 추가로 기존 산출물을 이동·삭제·덮어쓰지 않았다.

## 감사 스냅샷과 현재 기능

[감사 1 기능표](audit/feature_matrix_1.md)는 2026-10-11 **0.2.0 당시 MCP 30도구/69함수**를 검사한 원본이다. 현재 0.3.1의 **39도구/89함수**와 수치가 다른 것은 역사적 스냅샷의 정상적인 차이다. 원본 감사·기능표는 보존하고 현재 계약은 spec.md와 [0.3.0 기능 계획](upgrades/0.3.0-plan.md) 및 [0.3.1 배포 계획](releases/0.3.1-plan.md)을 따른다.
