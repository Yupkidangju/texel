"""수식 레지스트리와 보호/파일 경계의 독립 감사 관찰."""
import json,sys,math,sqlite3,hashlib
from pathlib import Path
from datetime import date
from uuid import uuid4
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from texel.model import Workbook
from texel.formula import Evaluator,function_names
from texel.editing import set_matrix,delete_sheet,apply_borders
from texel.exchange import load_file,export_file
from texel.session import Session
OUT=Path(__file__).resolve().parent;RUN=OUT/('domain-'+uuid4().hex[:8]);RUN.mkdir()
SAMPLES={
'SUM':('SUM(1,2)',3),'AVERAGE':('AVERAGE(2,4)',3),'MIN':('MIN(1,2)',1),'MAX':('MAX(1,2)',2),
'COUNT':('COUNT(1,2,"x")',2),'COUNTA':('COUNTA(1,"x")',2),'COUNTBLANK':('COUNTBLANK(A5:A6)',2),
'MEDIAN':('MEDIAN(1,3,2)',2),'STDEV':('STDEV(1,2,3)',1),'STDEV.S':('STDEV.S(1,2,3)',1),
'STDEV.P':('STDEV.P(1,2,3)',math.sqrt(2/3)),'VAR.S':('VAR.S(1,2,3)',1),
'PRODUCT':('PRODUCT(2,3)',6),'SUMSQ':('SUMSQ(2,3)',13),'ABS':('ABS(-3)',3),
'ROUND':('ROUND(2.675,2)',2.68),'ROUNDUP':('ROUNDUP(-1.21,1)',-1.3),'ROUNDDOWN':('ROUNDDOWN(-1.29,1)',-1.2),
'INT':('INT(-1.2)',-2),'MOD':('MOD(7,3)',1),'POWER':('POWER(2,3)',8),'SQRT':('SQRT(4)',2),
'CEILING':('CEILING(3,2)',4),'FLOOR':('FLOOR(3,2)',2),'LOG':('LOG(100)',2),'LN':('LN(1)',0),'EXP':('EXP(0)',1),
'AND':('AND(TRUE,FALSE)',False),'OR':('OR(TRUE,FALSE)',True),'NOT':('NOT(TRUE)',False),
'ISBLANK':('ISBLANK(A5)',True),'ISNUMBER':('ISNUMBER(2)',True),'ISTEXT':('ISTEXT("x")',True),
'SUMIF':('SUMIF(A1:A3,">1")',5),'COUNTIF':('COUNTIF(A1:A3,">1")',2),
'SUMIFS':('SUMIFS(B1:B3,A1:A3,">1")',50),'COUNTIFS':('COUNTIFS(A1:A3,">1",B1:B3,"<30")',1),
'LEFT':('LEFT("abc",2)','ab'),'RIGHT':('RIGHT("abc",2)','bc'),'MID':('MID("abc",2,1)','b'),
'LEN':('LEN("한국")',2),'TRIM':('TRIM("  a  b ")','a b'),'UPPER':('UPPER("ab")','AB'),'LOWER':('LOWER("AB")','ab'),
'PROPER':('PROPER("hello world")','Hello World'),'CONCAT':('CONCAT("a","b")','ab'),
'CONCATENATE':('CONCATENATE("a","b")','ab'),'TEXTJOIN':('TEXTJOIN("-",TRUE,"a","b")','a-b'),
'SUBSTITUTE':('SUBSTITUTE("aba","a","x")','xbx'),'FIND':('FIND("b","abc")',2),'SEARCH':('SEARCH("B","abc")',2),
'VALUE':('VALUE("12")',12),'REPT':('REPT("a",2)','aa'),'DATE':('DATE(2026,10,11)',date(2026,10,11)),
'TODAY':('TODAY()',date.today()),'YEAR':('YEAR(DATE(2026,10,11))',2026),'MONTH':('MONTH(DATE(2026,10,11))',10),
'DAY':('DAY(DATE(2026,10,11))',11),'DAYS':('DAYS(DATE(2026,10,11),DATE(2026,10,10))',1),
'WEEKDAY':('WEEKDAY(DATE(2026,10,11))',1),'INDEX':('INDEX(A1:B3,2,2)',20),'MATCH':('MATCH(2,A1:A3,0)',2),
'VLOOKUP':('VLOOKUP(2,A1:B3,2,FALSE)',20),'XLOOKUP':('XLOOKUP(2,A1:A3,B1:B3)',20),
'IF':('IF(TRUE,7,1/0)',7),'IFERROR':('IFERROR(1/0,9)',9),'ISERROR':('ISERROR(1/0)',True),
'ROW':('ROW(A3)',3),'COLUMN':('COLUMN(B1)',2)}
results=[]
for name in function_names():
    formula,expected=SAMPLES[name]
    w=Workbook();set_matrix(w,0,'A1',[['1','10'],['2','20'],['3','30']]);w.sheet().set_raw(0,3,'='+formula)
    value=Evaluator(w).value(0,0,3)
    ok=math.isclose(value,expected,rel_tol=1e-12) if isinstance(expected,float) and isinstance(value,(int,float)) else value==expected
    results.append(dict(function=name,formula='='+formula,expected=str(expected),actual=str(value),ok=ok))
boundaries=[]
def observe(name,call):
    try:r=call();boundaries.append(dict(case=name,result=r))
    except Exception as exc:boundaries.append(dict(case=name,error=repr(exc)))
def protected_delete():
    s=Session(RUN/'protected.texel')
    def seed(w):
        w.add_sheet('Locked');w.sheet(1).set_raw(0,0,'secret');w.sheet(1).cell(0,0).locked=True;w.sheet(1).protected=True
    s.apply('seed',seed);before=s.revision;s.apply('delete',lambda w:delete_sheet(w,1))
    return dict(before_revision=before,after_revision=s.revision,remaining=[w.name for w in s.workbook.sheets])
observe('delete_protected_last_sheet',protected_delete)
def numeric_string_csv():
    w=Workbook();set_matrix(w,0,'A1',[["'00123","'TRUE","'2026-10-11"]]);p=RUN/'types.csv';export_file(w,p)
    back=load_file(p);return dict(original=[str(Evaluator(w).value(0,0,c)) for c in range(3)],loaded=[str(Evaluator(back).value(0,0,c)) for c in range(3)])
observe('csv_numeric_string_roundtrip',numeric_string_csv)
def merged_xlsx_border():
    w=Workbook();from texel.editing import merge_range
    merge_range(w,0,'A1:C2');apply_borders(w,0,'A1:C2','outer','double');p=RUN/'merged.xlsx';export_file(w,p);back=load_file(p)
    return dict(merges=back.sheet().merges,cells={f'{r},{c}':v.to_dict() for (r,c),v in back.sheet().cells.items()})
observe('merged_xlsx_border',merged_xlsx_border)
def malformed_metadata():
    p=RUN/'bad-filter.texel';s=Session(p)
    with s.store.connect() as db:
        raw=json.loads(db.execute('SELECT metadata FROM texel_state').fetchone()[0]);raw['sheets'][0]['filter_spec']={'range':'NOPE','column':0,'criterion':'>0'}
        db.execute('UPDATE texel_state SET metadata=?',(json.dumps(raw),))
    w=load_file(p)
    return dict(accepted=w.sheet().filter_spec,path=str(p))
observe('native_invalid_filter_accepted',malformed_metadata)
output=dict(function_count=len(results),function_failures=[r for r in results if not r['ok']],functions=results,boundaries=boundaries)
(OUT/'domain_probe.json').write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(output,ensure_ascii=False))
