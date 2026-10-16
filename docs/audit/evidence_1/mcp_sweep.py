import asyncio,json,sys
from pathlib import Path
from uuid import uuid4
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from mcp import Client
from texel.mcp_server import create_server
from texel.session import Session
from texel.editing import set_matrix
OUT=Path(__file__).resolve().parent;RUN=OUT/('mcp-'+uuid4().hex[:8]);RUN.mkdir()
CASES={
'workbook_info':{},'read_range':{'sheet':'Sheet1','range':'A1:B4'},
'write_range':{'sheet':'Sheet1','start':'D1','values':[['=6*7']]},
'fill_formula':{'sheet':'Sheet1','range':'C2:C4','formula':'=B2*2'},
'clear_range':{'sheet':'Sheet1','range':'A4:B4'},
'copy_range':{'sheet':'Sheet1','range':'A2:B3','destination':'A6'},
'fill_cells':{'sheet':'Sheet1','range':'B2:B4','direction':'series'},
'format_range':{'sheet':'Sheet1','range':'B2:B4','number_format':'number','bold':True},
'set_borders':{'sheet':'Sheet1','range':'A1:B4','border_style':'double'},
'set_row_height':{'sheet':'Sheet1','range':'A1:B4','height':3},
'edit_sheet':{'action':'add','name':'Added'},
'change_structure':{'sheet':'Sheet1','axis':'row','at':1},
'sort_range':{'sheet':'Sheet1','range':'A1:B4','column':1,'descending':True},
'filter_range':{'sheet':'Sheet1','range':'A1:B4','column':1,'criterion':'>10'},
'find':{'sheet':'Sheet1','query':'a'},'replace':{'sheet':'Sheet1','query':'a','replacement':'x'},
'profile_range':{'sheet':'Sheet1','range':'A1:B4'},
'pivot_table':{'sheet':'Sheet1','range':'A1:B4','key_columns':[0],'value_column':1,'name':'Pivot'},
'chart_range':{'sheet':'Sheet1','range':'A1:B4'},
'create_chart':{'sheet':'Sheet1','range':'A1:B4'},
'deduplicate':{'sheet':'Sheet1','range':'A1:B4'},
'set_note':{'sheet':'Sheet1','cell':'B2','note':'audit'},
'set_validation':{'sheet':'Sheet1','range':'B2:B4','minimum':0,'maximum':100},
'merge_range':{'sheet':'Sheet1','range':'A6:B6'},
'define_name':{'sheet':'Sheet1','range':'B2:B4','name':'Revenue'},
'undo':{},'redo':{},'import_file':{'path':'input.csv'},'export_file':{'path':'export.xlsx'},'backup':{'path':'backup.texel'}}
async def main():
    inventory=[];results=[]
    for name,args in CASES.items():
        folder=RUN/name;folder.mkdir();path=folder/'document.texel';s=Session(path)
        s.apply('seed',lambda w:set_matrix(w,0,'A1',[['group','n'],['a','10'],['a','20'],['b','30']]))
        (folder/'input.csv').write_text('imported,42\n',encoding='utf-8')
        if name=='redo':s.undo()
        async with Client(create_server(path,folder)) as c:
            tools=(await c.list_tools()).tools
            inventory=[t.name for t in tools]
            schema=next(t.input_schema for t in tools if t.name==name)
            actual=dict(args)
            if 'expected_revision' in schema.get('properties',{}):actual['expected_revision']=s.revision
            result=(await c.call_tool(name,actual)).structured_content
            results.append(dict(tool=name,args=actual,result=result,persisted_revision=Session(path).revision))
    # 누락된 도구가 있으면 성공으로 확대하지 않는다.
    output=dict(inventory=inventory,executed=len(results),missing=sorted(set(inventory)-set(CASES)),results=results)
    (OUT/'mcp_sweep.json').write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(output,ensure_ascii=False))
if __name__=='__main__':asyncio.run(main())
