"""카탈로그 전체의 검색→실행→저장 결과를 기록한다. 필드 입력은 테스트용 직접 설정."""
import asyncio
import json
import sys
import traceback
from pathlib import Path
from uuid import uuid4

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from texel.ui.app import TexelApp
from texel.ui.commands import COMMANDS
from texel.ui.dialogs import FormDialog
from texel.session import Session
from texel.editing import set_matrix,format_range,apply_borders
from texel.addresses import CellRange
from texel.exchange import export_file
from texel.model import Workbook,Validation

OUT=Path(__file__).resolve().parent
RUN=OUT/('sweep-'+uuid4().hex[:8]);RUN.mkdir()

async def one(command):
    app=TexelApp(RUN/(command+'.texel'),language='en')
    def seed(w):
        set_matrix(w,0,'A1',[['group','value'],['a','10'],['a','20'],['b','30']])
        w.add_sheet('Other')
        w.sheet().cell(1,0).note='audit note'
    app.session.apply('seed',seed)
    source=RUN/'open.csv'
    if not source.exists():source.write_text('loaded,77\n',encoding='utf-8')
    async with app.run_test(size=(120,40)) as p:
        if command in {'paste','paste_special','transpose','cut','copy'}:
            app.grid.select_range(CellRange.parse('A2:B3'));app.copy_selection()
            app.grid.move(5,0)
        elif command in {'fill_down','fill_right','series','merge','merge_center','unmerge','borders'}:
            app.grid.select_range(CellRange.parse('B2:B4'))
        elif command in {'freeze','unfreeze'}:app.grid.move(1,1)
        elif command=='undo':app.session.apply('extra',lambda w:set_matrix(w,0,'D1',[['99']]))
        elif command=='redo':
            app.session.apply('extra',lambda w:set_matrix(w,0,'D1',[['99']]))
            app.session.undo()
        revision=app.session.revision
        await p.press('ctrl+p')
        app.screen.query_one('#command-search').value=command
        await p.pause()
        options=app.screen.query_one('#command-list')
        index=options.get_option_index(command)
        # 화면의 키 조작으로 검색 결과 중 정확한 명령을 선택한다.
        if index:await p.press('down',*(['down']*index))
        await p.press('enter');await p.pause()
        entered=type(app.screen).__name__
        fields={
          'new':{'path':str(RUN/'created.xlsx')},'open':{'path':str(source)},
          'save':{'path':str(RUN/'saved.xlsx')},'export':{'path':str(RUN/'export.xlsx')},
          'backup':{'path':str(RUN/'backup-destination.texel')},
          'find':{'query':'b'},'replace':{'query':'a','replacement':'changed'},
          'width':{'width':'20'},'row_height':{'row_height':'3'},
          'add_sheet':{'name':'Added'},'rename_sheet':{'name':'Renamed'},
          'duplicate_sheet':{'name':'Duplicate'},'delete_sheet':{'name':'Sheet1'},
          'named_range':{'name':'AuditRange','range':'B2:B4'},
          'style':{'number_format':'number','bold':True},'note':{'note':'updated note'},
          'filter':{'column':'2','criterion':'>10'},'sort':{'column':'2','descending':True},
          'validation':{'kind':'list','choices':'group,other'},
          'conditional':{'range':'B2:B4','value':'15'},'borders':{'border_style':'double'},
        }.get(command,{})
        if isinstance(app.screen,FormDialog):
            for key,value in fields.items():
                app.screen.query_one('#field-'+key).value=value
            await p.click('#apply',offset=(2,1));await p.pause()
        final=type(app.screen).__name__
        error=str(app.screen.query_one('#form-error').render()) if isinstance(app.screen,FormDialog) else ''
        app.session.workbook.validate()
        same=Session(app.session.store.path).workbook.to_dict()==app.session.workbook.to_dict()
        return dict(command=command,menu=next(c.menu for c in COMMANDS if c.key==command),entered=entered,
          final=final,error=error,revision_before=revision,revision_after=app.session.revision,
          persisted=same,active_sheet=app.sheet_index,sheets=[s.name for s in app.session.workbook.sheets],
          files=[f.name for f in RUN.glob('*.xlsx')])

async def main():
    results=[]
    for c in COMMANDS:
        if len(sys.argv)>1 and c.key not in sys.argv[1:]:continue
        try:result=await one(c.key)
        except Exception as exc:result=dict(command=c.key,error=repr(exc),traceback=traceback.format_exc())
        results.append(result);print(json.dumps(result,ensure_ascii=False),flush=True)
        (OUT/'command_sweep.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
if __name__=='__main__':asyncio.run(main())
