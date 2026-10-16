"""제품을 수정하지 않는 공개 입력/경계 관찰. 프로젝트 루트에서 실행한다."""
import asyncio
import json
import sys
import traceback
from dataclasses import asdict
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from texel.ui.app import TexelApp
from texel.editing import set_matrix, merge_range
from texel.model import Workbook
from texel.exchange import export_file, load_file
from texel.session import Session
from textual.widgets import Select, OptionList, DirectoryTree

OUT = Path(__file__).resolve().parent
RUN = OUT / ('fixtures-' + uuid4().hex[:8])
RUN.mkdir()
RESULTS = []

async def palette(pilot, command):
    await pilot.press('ctrl+p')
    await pilot.press(*command)
    await pilot.press('enter')
    await pilot.pause()

def screen(app, name):
    (OUT / (name + '.svg')).write_text(app.export_screenshot(), encoding='utf-8')

async def border_click():
    app = TexelApp(RUN / 'border.texel')
    async with app.run_test(size=(100,30)) as p:
        await p.press('shift+right','shift+down')
        await p.click('#grid', offset=(12,1), button=3)
        opt = app.screen.query_one(OptionList)
        region = str(opt.region)
        screen(app,'context-before')
        clicked = await p.click('#context-options', offset=(3,6))
        await p.pause()
        before = type(app.screen).__name__
        if before == 'FormDialog':
            await p.click('#field-border_style')
            await p.press('down','down','enter')
            chosen = app.screen.query_one('#field-border_style',Select).value
            await p.click('#apply')
            await p.pause()
            screen(app,'border-after')
            return dict(click=clicked,options_region=region,screen_before=before,chosen=chosen,revision=app.session.revision,
                border=asdict(app.session.workbook.sheet().cell(0,0).style),
                lines=[app.grid.render_line(i).text for i in range(app.grid.size.height)])
        return dict(click=clicked,screen=before,options_region=region)

async def dropdown(size):
    app=TexelApp(RUN/f'drop-{size[0]}.texel')
    async with app.run_test(size=size) as p:
        await palette(p,'borders')
        field=app.screen.query_one('#field-border_preset',Select)
        await p.click('#field-border_preset')
        await p.press('down','down','enter')
        screen(app,f'dropdown-{size[0]}')
        value=field.value
        apply_button=app.screen.query_one('#apply')
        geometry=str(apply_button.region)
        clicked=await p.click('#apply')
        return dict(value=value,apply_region=geometry,apply_click=clicked,screen=type(app.screen).__name__,revision=app.session.revision)

async def file_enter(size):
    source=RUN/f'input-{size[0]}.csv'
    source.write_text('name,value\na,42\n',encoding='utf-8')
    app=TexelApp(RUN/f'open-{size[0]}.texel')
    async with app.run_test(size=size) as p:
        await p.press('ctrl+o')
        await p.press(*str(source))
        await p.press('enter')
        await p.pause()
        screen(app,f'open-{size[0]}')
        return dict(screen=type(app.screen).__name__,value=app.session.evaluator.value(0,1,1),source=str(app.source_path))

async def tree_open():
    source=RUN/'tree.csv';source.write_text('tree,77\n',encoding='utf-8')
    app=TexelApp(RUN/'tree-start.texel')
    async with app.run_test(size=(100,30)) as p:
        await p.press('ctrl+o')
        tree=app.screen.query_one(DirectoryTree)
        await p.pause(0.7)
        nodes=[dict(label=str(n.label),path=str(n.data.path)) for n in tree.root.children]
        # 실제 트리의 키 조작으로 목적 노드까지 이동한다.
        await p.press('shift+tab')
        await p.press('home')
        for _ in range(len(nodes)+3):
            node=tree.cursor_node
            if node and node.data and node.data.path==source:
                break
            await p.press('down')
        cursor_before=str(tree.cursor_node)
        focused=str(app.focused)
        await p.press('enter')
        await p.pause()
        path=app.screen.query_one('#field-path').value
        await p.click('#apply')
        return dict(nodes=nodes,cursor_before=cursor_before,focused=focused,path=path,screen=type(app.screen).__name__,value=app.session.evaluator.value(0,0,1))

async def context_edit_draft():
    app=TexelApp(RUN/'draft.texel')
    async with app.run_test(size=(100,30)) as p:
        await p.press('4','2')
        before=list(app.editing)
        await p.click('#grid',offset=(26,3),button=3)
        await p.pause()
        saved=app.session.evaluator.value(0,0,0)
        rev=app.session.revision
        await p.press('escape')
        return dict(edit_before=before,saved_A1=saved,revision=rev,cursor=app.grid.cursor,selection=str(app.grid.selection))

async def edit_click_draft():
    app=TexelApp(RUN/'draft-click.texel')
    async with app.run_test(size=(100,30)) as p:
        await p.press('4','2')
        await p.click('#grid',offset=(26,3))
        await p.press('7','enter')
        return dict(A1=app.session.evaluator.value(0,0,0),B3=app.session.evaluator.value(0,2,1),cursor=app.grid.cursor)

async def merged_enter():
    app=TexelApp(RUN/'merged-enter.texel')
    app.session.apply('seed',lambda w:merge_range(w,0,'A1:B3'))
    async with app.run_test(size=(100,30)) as p:
        await p.press('4','2','enter')
        after_enter=app.grid.cursor
        await p.press('down')
        return dict(after_enter=after_enter,after_down=app.grid.cursor,value=app.session.evaluator.value(0,0,0))

async def frozen_columns():
    app=TexelApp(RUN/'frozen.texel')
    async with app.run_test(size=(80,24)) as p:
        await p.press('ctrl+g');await p.press(*'G2','enter')
        await palette(p,'freeze')
        await p.press('right','right')
        return dict(cursor=app.grid.cursor,freeze_columns=app.grid.sheet.freeze_columns,
                    visible=[c for c,_,_ in app.grid.visible_columns()],left=app.grid.left)

async def backup_overwrite():
    destination=RUN/'existing-backup.texel'
    Session(destination).apply('original',lambda w:set_matrix(w,0,'A1',[['original']]))
    app=TexelApp(RUN/'backup-start.texel')
    app.session.apply('seed',lambda w:set_matrix(w,0,'A1',[['replacement']]))
    async with app.run_test(size=(100,30)) as p:
        await palette(p,'backup')
        await p.press('ctrl+a',*str(destination),'enter')
        return dict(screen=type(app.screen).__name__,destination_A1=Session(destination).evaluator.value(0,0,0))

async def empty_native():
    path=RUN/'zero.texel';path.write_bytes(b'')
    size_before=path.stat().st_size
    loaded=load_file(path)
    return dict(size_before=size_before,size_after=path.stat().st_size,sheets=len(loaded.sheets))

async def number_series():
    app=TexelApp(RUN/'series.texel')
    app.session.apply('seed',lambda w:set_matrix(w,0,'A1',[['9007199254740993'],['9007199254740994']]))
    async with app.run_test(size=(100,30)) as p:
        await p.press('shift+down','shift+down')
        await palette(p,'series')
        return dict(values=[app.session.evaluator.value(0,r,0) for r in range(3)],raw=[app.grid.sheet.cell(r,0).raw for r in range(3)])

async def bottom_border():
    app=TexelApp(RUN/'bottom.texel')
    async with app.run_test(size=(100,30)) as p:
        await palette(p,'borders')
        await p.click('#field-border_preset');await p.press('end','up','up','up','enter')
        chosen=app.screen.query_one('#field-border_preset',Select).value
        await p.click('#apply')
        screen(app,'bottom-border')
        return dict(chosen=chosen,lines=[app.grid.render_line(i).text for i in range(1,6)])

async def main():
    cases=[('border_mouse_and_dropdown',border_click),
      ('dropdown_100x30',lambda:dropdown((100,30))),('dropdown_80x24',lambda:dropdown((80,24))),
      ('file_path_enter_100x30',lambda:file_enter((100,30))),('file_path_enter_80x24',lambda:file_enter((80,24))),
      ('file_tree_open',tree_open),('context_during_draft',context_edit_draft),('click_during_draft',edit_click_draft),
      ('merged_edit_enter',merged_enter),('frozen_columns',frozen_columns),('backup_overwrite',backup_overwrite),
      ('empty_native_input',empty_native),('series_precision',number_series),('bottom_border_dropdown',bottom_border)]
    for name,call in cases:
        if len(sys.argv)>1 and name not in sys.argv[1:]:
            continue
        try:
            value=await call()
            RESULTS.append(dict(case=name,result=value))
        except Exception as exc:
            RESULTS.append(dict(case=name,error=repr(exc),traceback=traceback.format_exc()))
        print(json.dumps(RESULTS[-1],ensure_ascii=False),flush=True)
        (OUT/'probe_ui.json').write_text(json.dumps(RESULTS,ensure_ascii=False,indent=2),encoding='utf-8')

if __name__=='__main__':
    asyncio.run(main())
