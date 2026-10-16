import asyncio,json,sys,traceback
from pathlib import Path
from uuid import uuid4
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from texel.ui.app import TexelApp
from texel.session import Session
from texel.editing import set_matrix
from texel.__main__ import main as cli_main
OUT=Path(__file__).resolve().parent;RUN=OUT/('extra-'+uuid4().hex[:8]);RUN.mkdir()
async def invalid_open():
    bad=RUN/'bad.texel';s=Session(bad)
    with s.store.connect() as db:
        metadata=json.loads(db.execute('SELECT metadata FROM texel_state').fetchone()[0])
        metadata['sheets'][0]['filter_spec']={'range':'NOPE','column':0,'criterion':'>0'}
        db.execute('UPDATE texel_state SET metadata=?',(json.dumps(metadata),))
    app=TexelApp(RUN/'original.texel');app.session.apply('seed',lambda w:set_matrix(w,0,'A1',[['original']]))
    before=str(app.session.store.path)
    async with app.run_test(size=(120,40)) as p:
        await p.press('ctrl+o');await p.press(*str(bad),'enter');await p.pause()
        return dict(before=before,after=str(app.session.store.path),screen=type(app.screen).__name__,
          value=app.session.evaluator.value(0,0,0),error=str(app.screen.query_one('#form-error').render()))
def cli_import():
    p=RUN/'source.csv';p.write_text('a,42\n',encoding='utf-8');observed={}
    def capture(self,**kwargs):observed.update(source_path=str(self.source_path),workbook=str(self.session.store.path),value=self.session.evaluator.value(0,0,1))
    with patch.object(TexelApp,'run',capture):
        exit_code=cli_main(['tui','--workbook',str(p)])
    return dict(exit_code=exit_code,**observed)
async def main():
    results=[dict(case='cli_import_source',result=cli_import())]
    try:results.append(dict(case='invalid_native_open',result=await invalid_open()))
    except Exception as exc:results.append(dict(case='invalid_native_open',error=repr(exc),traceback=traceback.format_exc()))
    (OUT/'extra_probe.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(results,ensure_ascii=False))
if __name__=='__main__':asyncio.run(main())
