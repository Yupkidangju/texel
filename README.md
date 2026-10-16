# Texel

현재 버전: **0.3.1**. `-Demo`의 **서식 예제** 시트에서 병합·테두리·줄바꿈을 바로 확인할 수 있습니다.

[GitHub](https://github.com/Yupkidangju/texel) · [릴리스](https://github.com/Yupkidangju/texel/releases) · [CI](https://github.com/Yupkidangju/texel/actions/workflows/ci.yml)

Python 3.15 기반 로컬 TUI 스프레드시트와 데이터 분석용 MCP 서버입니다. 사람이 터미널에서 편집하는 같은 `.texel` 문서를 AI가 도구로 읽고 분석하고 수정할 수 있습니다.

## 실행

Windows x64, Linux·macOS x64/ARM64에서 **Python 3.14 이상**을 설치한 뒤 릴리스의 공통 wheel을 설치합니다. **Windows11 ARM64는 x64 Python 에뮬레이션에서 공통 wheel**을 검증했습니다. Windows ARM64 네이티브는 의존성 wheel 제약으로 지원 범위에 포함하지 않습니다. portable ZIP의 실행 검증 대상은 Windows x64입니다.

```sh
python -m pip install texel_tui-0.3.1-py3-none-any.whl
texel tui --demo
```

CI와 같은 전이 의존성 버전을 재현하려면 해당 태그의 잠금 파일을 적용합니다: `python -m pip install -c https://raw.githubusercontent.com/Yupkidangju/texel/v0.3.1/requirements-runtime.lock texel_tui-0.3.1-py3-none-any.whl`. 일반 설치는 pyproject의 직접 의존성만 고정합니다.

Windows x64 portable ZIP은 Python을 포함하며 Run.cmd/Demo.cmd로 실행합니다. 다른 OS/CPU에는 Python 런타임이 필요합니다. 최초 의존성 설치에는 인터넷이 필요하고 로컬 문서는 설치 후 오프라인 동작합니다. Python 3.14에서 6개 OS/CPU 조합, Ubuntu x64의 Python 3.15를 CI 대상으로 지정했습니다. 실제 호스팅 검증 결과와 장비 검증 한계는 [공개 배포 기록](docs/releases/0.3.1-results.md)에 기록합니다.

| 실행 환경 | Python 아키텍처 | 배포 형태 |
|---|---|---|
| Windows x64 | x64 | 공통 wheel / 런타임 포함 portable |
| Windows11 ARM64 | x64 에뮬레이션 | 공통 wheel |
| Linux x64 | x64 네이티브 | 공통 wheel |
| Linux ARM64 | ARM64 네이티브 | 공통 wheel |
| macOS Intel | x64 네이티브 | 공통 wheel |
| macOS Apple Silicon | ARM64 네이티브 | 공통 wheel |

macOS Intel에서는 현재 고정 의존성 cryptography의 소스 빌드가 필요합니다. Xcode Command Line Tools와 Rust/OpenSSL을 준비하세요: `xcode-select --install`, `brew install rust openssl@3`. [공식 빌드 안내](https://cryptography.io/en/latest/installation/#building-cryptography-on-macos)를 따르며 설치 오류가 나면 `OPENSSL_DIR="$(brew --prefix openssl@3)" python -m pip install <wheel>`로 OpenSSL 위치를 지정합니다. CI에서도 이 의존성을 실제 컴파일해 검증했습니다.

Windows 소스 개발 환경:

```powershell
.\prepare.ps1
.\run.ps1
.\run.ps1 -Demo
.\run.ps1 -Workbook .\data\analysis.texel
```

배포 폴더의 `Run.cmd` 또는 `Demo.cmd`로도 실행할 수 있습니다. Python과 런타임 의존성이 portable 폴더에 포함되어 있어 배포 후 오프라인으로 사용합니다. 100×30 이상 Windows Terminal을 권장하며 80×24에서도 동작합니다.

마지막 검증 배포본의 경로·해시와 수정 후 소스의 차이는 [배포 목록](docs/distributions.md)을 참고하세요. 과거 ZIP/검증 폴더는 이력으로 보존합니다.

## 기능

- 키보드 이동/범위 선택, 마우스 클릭·더블클릭·드래그·휠, 열 너비 드래그.
- 셀 편집, 수식줄/주소 이동, TSV 클립보드, 복사/잘라내기/전치, 값·수식·서식 선택하여 붙여넣기, 채우기/숫자 연속 채우기.
- 다중 시트, 행/열 삽입·삭제, 상대/절대/혼합/다른 시트 참조, 이름 범위.
- 수학·통계·논리·조건 집계·문자열·날짜·조회 함수 89개. AVERAGEIFS/MINIFS/MAXIFS/SUMPRODUCT, IFNA/IFS, EDATE/EOMONTH/WORKDAY/NETWORKDAYS 등 실무 함수를 포함합니다.
- 숫자/퍼센트/통화/날짜 서식, 색/굵게/기울임/취소선/밑줄/가로·세로 정렬, 줄바꿈/행 높이, 메모, 실제 영역 병합/분할, 유효성 검사, 셀 잠금/시트 보호, 조건부 강조.
- 얇은/중간/굵은/이중/파선/점선 테두리, 전체/바깥/안쪽/방향별 적용과 색. 서식과 병합은 복사·undo·native·XLSX에서 보존합니다.
- 정렬/필터/찾기/바꾸기/중복 제거, 선택 통계, 데이터 프로파일, 피벗 테이블, Unicode 막대/선 차트와 XLSX 차트 내보내기.
- SQLite 자동 저장, 트랜잭션, 재시작 후에도 실행 취소/다시 실행, 백업, TUI/MCP revision 충돌 감지.
- CSV/TSV/XLSX 교환, 구버전 XLS 및 공개 Google Sheets의 GSHEET 바로가기 가져오기, 한국어/영어 UI, 어두운/밝은/고대비 테마, 명령 검색.
- 셀/행/열 우클릭 메뉴와 Shift+F10: 복사·잘라내기·붙여넣기·테두리·셀 서식·병합/분할·삽입/삭제·크기·숨김·정렬·필터.
- 다중 열 안정 정렬, AND/OR 복합 필터, 통합 문서 전체 원문/계산값 검색과 전체 셀 일치 바꾸기. 데이터 메뉴에서 직접 선택합니다.
- 수식의 직접 선행 범위·후행 셀 진단과 MCP 임시 수식 계산. MCP는 39개 도구와 미리보기·원자적 일괄 적용·다중 범위 조회·부분 서식 변경을 제공합니다.

Apache License 2.0으로 제공합니다. **Copyright 2026 yupkidangju@gmail.com**. [LICENSE](LICENSE)와 [NOTICE](NOTICE)를 참고하세요.

열기/저장 창은 드라이브 선택, 상위/홈/루트, 폴더 경로 이동, 파일 트리와 전체 경로 직접 입력을 지원합니다. `data` 아래에 제한되지 않습니다. Ctrl+S도 실제 저장 창을 열며, 기존 파일을 교체하려면 덮어쓰기 허용을 선택합니다. native 파일의 자동 저장은 계속 유지됩니다.

`F2`/Enter/더블클릭으로 편집, Enter 확정, Esc 취소, Ctrl+Enter 선택 범위 채우기입니다. 방향키/Shift+방향키로 선택하며 Ctrl+P에서 모든 명령을 검색할 수 있습니다. Ctrl+C/V는 그리드에서는 범위, 수식 입력창에서는 문자열을 다룹니다. 터미널 자체 텍스트 선택은 Windows Terminal의 Shift+마우스 등 터미널 설정을 이용하세요.

편집 중 다른 셀을 클릭하면 기존 입력을 먼저 확정합니다. 검증/보호/동기화 충돌로 확정하지 못하면 기존 편집 대상과 원문을 유지합니다. 병합 편집의 Enter/Tab은 병합 영역 밖으로 이동합니다. 숫자 연속 채우기는 초기 숫자 원문을 유지하고 표시 반올림을 저장에 사용하지 않습니다. 보호된 시트는 보호를 해제한 뒤 삭제할 수 있습니다.

Ctrl+방향키는 연속 데이터 끝/다음 데이터로 이동하고 Ctrl+Shift+방향키로 선택을 확장합니다. Ctrl+A는 사용 영역, Shift+Space는 전체 행, Ctrl+Space는 전체 열을 선택합니다. 수식 입력 중 F4는 커서 또는 선택 영역의 참조를 `A1 → $A$1 → A$1 → $A1`로 전환합니다. 셀 변경의 10,000셀 상한은 전체 행/열 선택에도 적용됩니다.

CLI/Run.ps1로 가져온 파일도 Ctrl+S에서 원본 경로를 기본값으로 사용합니다. XLS/GSHEET는 .xlsx 변환 경로가 기본값입니다. 기존 native 파일 열기는 읽기 전용으로 형식과 메타데이터를 검증하며 실패 시 입력 파일과 현재 작업 문서를 보존합니다.

## MCP

```powershell
.\run.ps1 -Mcp -Workbook .\data\analysis.texel -Root .\data
```

MCP 클라이언트에는 프로젝트 내부 Python 실행 파일과 아래 인자를 등록합니다. 앱의 **도움말 → MCP 연결 안내**에서 현재 통합 문서에 맞는 JSON을 확인할 수 있습니다. 서버는 stdio만 사용하며 API 키를 요구하거나 AI 모델을 직접 호출하지 않습니다.

```json
{
  "mcpServers": {
    "texel": {
      "command": "C:\\LocalDev\\python\\Texel\\.runtime\\python315\\python.exe",
      "args": ["-m", "texel", "mcp", "--workbook", "C:\\LocalDev\\python\\Texel\\data\\analysis.texel", "--root", "C:\\LocalDev\\python\\Texel\\data"]
    }
  }
}
```

AI 사용 순서: `workbook_info` → 페이지 단위 `read_range` → `profile_range` → `pivot_table`/`chart_range`. 변경 도구는 직전에 읽은 `expected_revision`을 전달합니다. 충돌 응답이면 최신 revision과 데이터를 다시 읽으세요. 내보내기/백업 경로는 `--root` 내부로 제한합니다. 실제 도구/인자는 [MCP_GUIDE.md](MCP_GUIDE.md)를 참고하세요.

## 호환 범위

`.xls`는 원본 수식 코드 대신 저장된 계산값과 기본 서식을 읽습니다. 이후 `.xlsx`, `.csv`, `.tsv`, `.texel`로 저장합니다. `.gsheet`는 공개/링크 접근이 허용된 Google Sheets 바로가기 파일이며, 인터넷으로 내려받은 내용을 가져옵니다. 원격 Google 문서를 수정하거나 계정 쿠키/토큰을 사용하지 않습니다. 로그인/권한이 필요한 문서는 공개 다운로드 권한을 설정하거나 XLSX로 내려받아 열어야 합니다.

Excel의 모든 기능과 동일한 제품으로 주장하지 않습니다. XLSX는 셀·수식·기본 서식·메모·시트·너비·숨김·동결·병합을 교환합니다. 매크로/외부 연결/이미지/Excel 전용 객체는 보존하지 않습니다. 지원하지 않는 수식은 원문을 유지하고 오류로 표시합니다. 중요한 원본은 `.texel` 백업과 함께 보존하세요.

CSV/TSV 기본 내보내기는 계산값이며 문자열 수식 주입을 작은따옴표로 보호합니다. 수식 원문 내보내기는 명시적으로 선택합니다. 주소 상한은 Excel 크기지만 저장된 셀은 200,000개, 한 변경 요청은 10,000셀입니다. 큰 영역의 처리/파일 상한은 [spec.md](spec.md)에 명시되어 있습니다.

검증은 [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md), 설치/빌드는 [BUILD_GUIDE.md](BUILD_GUIDE.md)에 기록합니다. 실제 터미널 자동 검증과 사람의 한글 IME/화면/다른 OS 확인은 구분합니다.
