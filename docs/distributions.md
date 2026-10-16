# 배포물 목록

갱신: 2026-10-16. 현재 공개판은 [v0.3.1](https://github.com/Yupkidangju/texel/releases/tag/v0.3.1)이다. [검증 결과](releases/0.3.1-results.md)에 자동 릴리스와 다운로드 대조를 기록했다. 아래 0.3.0은 당시 로컬 검증 산출물과 유지보수 경계의 기록이다.

## 현재 공개판: 0.3.1

| 공개 파일 | bytes | SHA256 |
|---|---:|---|
| texel_tui-0.3.1-py3-none-any.whl | 103,104 | 6724b15fa61219c65dcb4fc28c0b28231d602252e3d59dd0bd7700b72d957307 |
| texel_tui-0.3.1.tar.gz | 1,158,564 | addd519ca488bb70e7e34fd15886e10b0f6daeb75d9feec6d9bb4570cda6dce7 |
| Texel-0.3.1-win64-20261016-051942.zip | 33,227,964 | 9292cbfa79072d65d71be6948724a55cbdeb3ee21295aafeaf09016f3b32f0cf |

SHA256SUMS.txt와 위 파일은 Release에서 제공하며 다운로드 검증본은 output/github-release-v0.3.1/에 있다. Python3.14+ 공통 wheel, Windows x64만 런타임 포함 portable이다. Windows ARM64는 x64 Python wheel 에뮬레이션, Mac Intel은 Xcode/Rust/OpenSSL 설치 전제가 있다. ZIP 이름 시각은 GitHub UTC이다.

root output/의 0.3.1 wheel/sdist 및 Texel-0.3.1-win64-20261016-140238는 로컬 사전 빌드이며 공개 자산과 구분한다. 공개판은 위 해시와 Release 경로로 선택한다. 기존 자료는 삭제하지 않았다.

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
