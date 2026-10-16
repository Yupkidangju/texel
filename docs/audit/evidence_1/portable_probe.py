import asyncio,json,sys
from pathlib import Path
from uuid import uuid4
OUT=Path(__file__).resolve().parent
BUNDLE=Path(sys.argv[1]).resolve()
sys.path.insert(0,str(BUNDLE))
from texel.ui.app import TexelApp
from texel.editing import set_matrix
from texel.session import Session
from mcp import Client,StdioServerParameters
import texel
RUN=OUT/('portable-'+uuid4().hex[:8]);RUN.mkdir()
async def main():
    app=TexelApp(RUN/'ui.texel',language='en');results={
        'python':sys.executable,'package':texel.__file__,'version':texel.__version__}
    async with app.run_test(size=(80,24)) as p:
        await p.press('4','2');await p.click('#grid',offset=(26,3));await p.press('7','enter')
        results['draft_click']=dict(A1=app.session.evaluator.value(0,0,0),B3=app.session.evaluator.value(0,2,1))
        await p.press('ctrl+p');await p.press(*'borders','enter');await p.pause()
        results['border_apply_clicked']=await p.click('#apply',offset=(2,1))
        results['border_screen']=type(app.screen).__name__
        await p.press('escape')
        source=RUN/'input.csv';source.write_text('n,42\n',encoding='utf-8')
        await p.press('ctrl+o');await p.press(*str(source),'enter')
        results['csv_value']=app.session.evaluator.value(0,0,1)
    params=StdioServerParameters(command=sys.executable,args=['-m','texel','mcp','--workbook',str(RUN/'mcp.texel'),'--root',str(RUN)],cwd=str(BUNDLE))
    async with Client(params) as c:
        results['mcp_tools']=len((await c.list_tools()).tools)
        write=(await c.call_tool('write_range',{'sheet':'Sheet1','start':'A1','values':[['=6*7']],'expected_revision':0})).structured_content
        results['mcp_write']=write
        results['mcp_saved_value']=Session(RUN/'mcp.texel').evaluator.value(0,0,0)
    (OUT/'portable_probe.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
    print(json.dumps(results))
if __name__=='__main__':asyncio.run(main())
