"""Verify native match introduction/versus and subsequent authoritative turns."""
import json
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
from tools.game_config import ROOT,load_config
from tools.smoke_human_match import windows,wait_for,click


def main():
    cfg=load_config();cfg['rules']['match'].update(turns_per_match=1,turns_per_period=1,placement_seconds=3,planning_seconds=3)
    evidence=ROOT/'evidence';data=Path(os.environ.get('BOUFBOWL_SMOKE_DATA',Path.home()/'.cache/boufbowl-live-smoke'))
    with tempfile.TemporaryDirectory(prefix='boufbowl-cinematics-') as tmp:
        root=Path(tmp);state=root/'state';service=Service(root/'state.sqlite',cfg)
        class QuietHandler(Handler):
            def log_message(self,*args):pass
        server=ThreadingHTTPServer(('127.0.0.1',0),partial(QuietHandler,directory=str(ROOT)));server.service=service
        threading.Thread(target=server.serve_forever,daemon=True).start()
        env=dict(os.environ,XDG_DATA_HOME=str(data),XDG_STATE_HOME=str(state))
        before=windows();log=(evidence/'cinematics-launch.log').open('w')
        process=subprocess.Popen([sys.executable,str(ROOT/'play.py'),'--mode','server','--lang','en',
            '--profile','Cinematics'+str(int(time.time())),'--server-url',f'http://127.0.0.1:{server.server_port}'],env=env,stdout=log,stderr=subprocess.STDOUT)
        trace=state/'boufbowl-tutorial/mock.log'
        try:
            wait_for(lambda:trace.exists() and 'Incoming CLUB_INFORMATION' in trace.read_text());wait_for(lambda:windows()-before)
            window=sorted(windows()-before)[-1];time.sleep(1)
            click(window,650,30);time.sleep(.3);click(window,380,255)
            wait_for(lambda:'Match introduction started' in trace.read_text())
            print('Native introduction running.',flush=True)
            assert 'Incoming FIELD_STATE' not in trace.read_text()
            time.sleep(1)
            subprocess.run(['import','-window','root',str(evidence/'cinematic-stadium-intro.png')],check=True)
            wait_for(lambda:'Versus cinematic started' in trace.read_text())
            print('Native versus cinematic rendered.',flush=True)
            time.sleep(.5)
            subprocess.run(['import','-window','root',str(evidence/'cinematic-versus.png')],check=True)
            wait_for(lambda:'Outgoing IntroductionDoneMessage' in trace.read_text())
            wait_for(lambda:'Incoming FIELD_STATE' in trace.read_text())
            wait_for(lambda:'Incoming MATCH_END' in trace.read_text(),180)
            assert trace.read_text().count('Outgoing ResolutionDoneMessage')==1
            assert service.store.db.execute('SELECT COUNT(*) FROM match_results').fetchone()[0]==1
            for row in service.store.db.execute('SELECT record_json FROM turns'):
                record=json.loads(row[0]);assert record['presentation']['interactions']
            print('Native stadium/versus introduction, introduction acknowledgement, turn completion and one result verified.')
        finally:
            if trace.exists():(evidence/'cinematics-trace.log').write_text(trace.read_text())
            wine_log=state/'boufbowl-tutorial/wine.log'
            if wine_log.exists():(evidence/'cinematics-wine.log').write_text(wine_log.read_text(errors='replace'))
            wineserver=shutil.which('wineserver') or '/usr/lib/x86_64-linux-gnu/wine/wineserver'
            subprocess.run([wineserver,'-k'],env=dict(env,WINEPREFIX=str(data/'boufbowl-tutorial/wine')),check=False)
            process.wait(timeout=10);log.close();server.shutdown();server.server_close();service.close()


if __name__=='__main__':main()
