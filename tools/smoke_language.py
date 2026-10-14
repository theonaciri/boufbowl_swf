"""Native gear language selection, persistence and launcher override regression."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from functools import partial
from http.server import ThreadingHTTPServer
from backend.server import Handler
from backend.service import Service
from tools.game_config import ROOT, load_config
from tools.smoke_human_match import click, wait_for, windows


def main():
    data=Path(os.environ.get('BOUFBOWL_SMOKE_DATA',Path.home()/'.cache/boufbowl-live-smoke'))
    prefix=data/'boufbowl-tutorial/wine'
    evidence=ROOT/'evidence';evidence.mkdir(exist_ok=True)
    preferences={p:p.read_bytes() for p in prefix.rglob('BoufbowlPreferences.sol')}
    for p in preferences:p.unlink()
    languages=[]
    class RecordingService(Service):
        def hello(self,body):
            languages.append(body.get('language'))
            return super().hello(body)
    with tempfile.TemporaryDirectory(prefix='boufbowl-language-smoke-') as tmp:
        root=Path(tmp);service=RecordingService(root/'state.sqlite',load_config())
        class QuietHandler(Handler):
            def log_message(self,*args):pass
        server=ThreadingHTTPServer(('127.0.0.1',0),partial(QuietHandler,directory=str(ROOT)));server.service=service
        threading.Thread(target=server.serve_forever,daemon=True).start()
        profile='LanguageSmoke'+str(int(time.time()))
        process=None
        try:
            for index,(override,expected) in enumerate((('en','en'),(None,'fr'),('en','en'),(None,'fr'))):
                state=root/str(index);env=dict(os.environ,XDG_DATA_HOME=str(data),XDG_STATE_HOME=str(state))
                before=windows();previous=len(languages)
                command=[sys.executable,str(ROOT/'play.py'),'--mode','server','--profile',profile,
                         '--server-url',f'http://127.0.0.1:{server.server_port}']
                if override:command.extend(['--lang',override])
                with (evidence/f'language-launch-{index}.log').open('w') as log:
                    process=subprocess.Popen(command,env=env,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
                    trace=state/'boufbowl-tutorial/mock.log'
                    wait_for(lambda:trace.exists() and 'Incoming CLUB_INFORMATION' in trace.read_text())
                    wait_for(lambda:bool(windows()-before));window=sorted(windows()-before)[-1];time.sleep(1)
                    assert languages[previous:]==[expected],languages
                    subprocess.run(['import','-window','root',str(evidence/f'language-home-{expected}-{index}.png')],check=True)
                    click(window,1015,26);time.sleep(.5)
                    if index==0:
                        for code in ('de','es','fr'):
                            click(window,500,310);time.sleep(.2)
                            subprocess.run(['import','-window','root',str(evidence/f'language-selected-{code}.png')],check=True)
                    subprocess.run(['import','-window','root',str(evidence/f'language-settings-{index}.png')],check=True)
                    click(window,749,185);time.sleep(.3)
                    click(window,925,30);process.wait(timeout=15);process=None
            assert service.store.db.execute('SELECT COUNT(*) FROM profiles').fetchone()[0]==1
            print('Native language selector: all four choices, saved French restart, one-launch English override and unchanged profile verified.')
        finally:
            wineserver=shutil.which('wineserver') or '/usr/lib/x86_64-linux-gnu/wine/wineserver'
            subprocess.run([wineserver,'-k'],env=dict(os.environ,WINEPREFIX=str(prefix)),check=False)
            if process:
                try:process.wait(timeout=10)
                except subprocess.TimeoutExpired:process.kill();process.wait()
            server.shutdown();server.server_close();service.close()
            for p in prefix.rglob('BoufbowlPreferences.sol'):
                if p not in preferences:p.unlink()
            for p,content in preferences.items():p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(content)


if __name__=='__main__':main()
