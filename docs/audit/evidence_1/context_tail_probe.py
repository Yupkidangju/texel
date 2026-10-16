import asyncio,json,sys,traceback
from pathlib import Path
from uuid import uuid4
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from texel.ui.app import TexelApp
from textual.widgets import OptionList
OUT=Path(__file__).resolve().parent
async def main():
    results=[]
    for size,mode in [((80,24),'mouse'),((100,30),'mouse'),((80,24),'keyboard'),((100,30),'keyboard')]:
        observation={'size':size,'mode':mode}
        app=TexelApp(OUT/('context-tail-'+uuid4().hex[:8]+'.texel'),language='en')
        app.session.apply('freeze',lambda w:(setattr(w.sheet(),'freeze_rows',1),setattr(w.sheet(),'freeze_columns',1)))
        try:
            async with app.run_test(size=size) as p:
                await p.click('#grid',offset=(12,1),button=3)
                await p.press('end');await p.pause(0.6)
                opt=app.screen.query_one(OptionList)
                index=opt.highlighted
                line=opt._line_cache.index_to_line[index]
                x=opt.content_region.x+2;y=opt.content_region.y+line-int(opt.scroll_y)
                hit=app.get_widget_at(x,y)[0] if 0<=y<size[1] else None
                chosen=opt.get_option_at_index(index).id
                observation.update(last=chosen,point=[x,y],hit=str(hit),options_region=str(opt.region),scroll_y=opt.scroll_y)
                if mode=='mouse':await p.click(offset=(x,y))
                else:await p.press('enter')
                await p.pause()
                observation['mouse_final']=type(app.screen).__name__
                observation['freeze_after']=[app.grid.sheet.freeze_rows,app.grid.sheet.freeze_columns]
        except Exception as exc:
            observation.update(error=repr(exc),traceback=traceback.format_exc())
        results.append(observation)
    (OUT/'context_tail_probe.json').write_text(json.dumps(results,indent=2),encoding='utf-8');print(json.dumps(results))
if __name__=='__main__':asyncio.run(main())
