import hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
report=OUT.parent/'audit_report_1.md';text=report.read_text(encoding='utf-8')
missing=[]
for target in re.findall(r'\]\(([^)]+)\)',text):
    if target.startswith(('https://','http://')):continue
    path=Path(target)
    if not path.is_absolute():path=report.parent/path
    if not path.exists():missing.append(str(path))
hashes=json.loads((OUT/'product_hashes_before.json').read_text(encoding='utf-8-sig'))
changed=[r['Path'] for r in hashes if hashlib.sha256(Path(r['Path']).read_bytes()).hexdigest().upper()!=r['Hash']]
ids=re.findall(r'^### ((?:IMP|DBG|SEC)-F\d+) —',text,re.M)
log=(OUT/'audit_regressions.log').read_text(encoding='utf-8')
result=dict(report_exists=report.exists(),finding_ids=ids,findings=len(ids),critical=text.count('**Severity: Critical'),
  major=text.count('**Severity: Major'),minor=text.count('**Severity: Minor'),missing_links=missing,
  product_files=len(hashes),changed_product_files=changed,baseline_160='160 passed' in (OUT/'baseline_pytest.log').read_text(encoding='utf-8'),
  audit_11_failures='11 failed in 13.45s' in log,native_exit=json.loads((OUT/'native_final.json').read_text(encoding='utf-8'))['exit_code'])
(OUT/'closure_validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False))
assert not missing and not changed and len(ids)==11 and result['audit_11_failures']
