import asyncio,json,sys
from pathlib import Path
from uuid import uuid4
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from texel.ui.app import TexelApp
from texel.editing import set_matrix
OUT=Path(__file__).resolve().parent;RUN=OUT/('layout-'+uuid4().hex[:8]);RUN.mkdir()
async def main():
    results=[]
    for size in [(80,24),(100,30),(120,40)]:
        app=TexelApp(RUN/f'{size[0]}.texel',language='en')
        app.session.apply('seed',lambda w:set_matrix(w,0,'A1',[['group','n'],['a','1']]))
        async with app.run_test(size=size) as p:
            for command in ['open','save','new','backup','borders','style','validation','sort','filter','pivot','chart','conditional','note','width','row_height','find','replace','named_range']:
                app.run_command(command);await p.pause()
                b=app.screen.query_one('#apply');r=b.region
                center=(r.x+r.width//2,r.y+r.height//2)
                hit=app.get_widget_at(*center)[0] if center[0]<size[0] and center[1]<size[1] else None
                visible=hit is b
                results.append(dict(size=size,command=command,apply_region=str(r),center=center,
                    hit=str(hit),clickable=bool(visible)))
                if command in ['open','style','borders']:
                    (OUT/f'layout-{command}-{size[0]}.svg').write_text(app.export_screenshot(),encoding='utf-8')
                await p.press('escape');await p.pause()
        (OUT/'layout_probe.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
    print(json.dumps(results))
if __name__=='__main__':asyncio.run(main())
