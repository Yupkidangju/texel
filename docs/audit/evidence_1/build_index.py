"""저장된 감사 결과를 보고서 부록으로 정리한다. 제품 파일에는 쓰지 않는다."""
import json
import sys
from pathlib import Path
from collections import Counter
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from texel.ui.commands import COMMANDS
from texel.i18n import tr
OUT=Path(__file__).resolve().parent
def read(name):return json.loads((OUT/name).read_text(encoding='utf-8'))
commands=read('command_sweep.json');mcp=read('mcp_sweep.json');functions=read('domain_probe.json')
issues={'series':'DBG-F002','style':'IMP-F001','borders':'IMP-F001, IMP-F004','validation':'IMP-F001',
'sort':'IMP-F001','filter':'IMP-F001','pivot':'IMP-F001','conditional':'IMP-F001','freeze':'IMP-F003',
'merge':'IMP-F002','merge_center':'IMP-F002','delete_sheet':'SEC-F001','open':'DBG-F003, DBG-F005','save':'DBG-F004','unfreeze':'DBG-F006 (우클릭 경로)'}
lines=['# Texel 감사 1 기능 검증표','','작성: 2026-10-11. 기초 테스트 160개 통과. 명령표는 120×40에서 검색 → 명령 실행 → 양식 적용 → SQLite 재읽기까지의 대표 통합 경로다. 모든 경계의 정상 판정을 뜻하지 않는다. 양식 필드를 직접 설정한 사례와 물리 입력 검사를 구분한다. 일부 초기 무변경 명령은 재료가 없는 상태의 동작이며, 해당 동작의 실효 검증은 기존 테스트도 함께 참조한다.','','| 메뉴 | 명령 | 진입 → 종료 | 영속 상태 일치 | 관련 발견 |','|---|---|---|---|---|']
for c in COMMANDS:
    r=next(r for r in commands if r['command']==c.key)
    lines.append(f"| {c.menu} | {tr(c.key,'ko')} (`{c.key}`) | {r['entered']} → {r['final']} | {'확인' if r['persisted'] else '실패'} | {issues.get(c.key,'대표 경로 확인')} |")
lines+=['','## MCP 도구 30개','','메모리 전송 SDK Client로 실제 도구를 호출했다. stdio/다른 프로세스/공용 TUI 동기화는 baseline 및 portable 별도 증거다. 도구별 대표 정상 입력이며 모든 인자 조합의 보장은 아니다.','','| 도구 | 응답 | 저장 revision |','|---|---|---|']
for r in mcp['results']:lines.append(f"| `{r['tool']}` | {'ok' if r['result'].get('ok') else '실패'} | {r['persisted_revision']} |")
lines+=['','## 수식 함수 69개','','레지스트리 전부에 독립 기대값이 있는 기본 예제 하나를 계산했다. TODAY는 실행 장비 날짜와 대조했다. 전체 Excel 의미 또는 모든 오류 인자의 검증으로 확대하지 않는다. 기존 수식 오류/순환/참조/상한 회귀와 함께 해석한다.','','| 함수 | 수식 | 기대값 | 실제값 |','|---|---|---|---|']
for r in functions['functions']:lines.append(f"| {r['function']} | `{r['formula']}` | {r['expected']} | {r['actual']} |")
(OUT.parent/'feature_matrix_1.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
summary=dict(commands=len(commands),command_errors=[r for r in commands if r.get('error')],
    mcp_tools=len(mcp['inventory']),mcp_executed=mcp['executed'],mcp_missing=mcp['missing'],
    mcp_errors=[r for r in mcp['results'] if not r['result'].get('ok')],
    functions=functions['function_count'],function_failures=functions['function_failures'],
    audit_findings=11,audit_regressions_failed=11,context=read('context_tail_probe.json'),
    layout_failures={str(size):[r['command'] for r in read('layout_probe.json') if r['size']==list(size) and not r['clickable']]
        for size in [(80,24),(100,30),(120,40)]},portable=read('portable_probe.json'),parity=read('package_parity.json'),google=read('google_live.json'))
(OUT/'verification_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in summary.items() if k not in {'portable'}},ensure_ascii=False))
