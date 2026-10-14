"""Native stale-session startup, concurrent panel recovery and account re-login."""
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
from backend.storage import ServiceError
from tools.game_config import ROOT,load_config
from tools.smoke_human_match import windows,wait_for


def main():
    cfg=load_config();cfg['general']['cinematics']['introductions']=False
    evidence=ROOT/'evidence/session-recovery';evidence.mkdir(parents=True,exist_ok=True)
    data=Path(os.environ.get('BOUFBOWL_SMOKE_DATA','/tmp/boufbowl-live-smoke-data'))
    nickname='SessionCheck'+str(int(time.time()))
    with tempfile.TemporaryDirectory(prefix='boufbowl-session-smoke-') as tmp:
        root=Path(tmp);state=root/'state';service=Service(root/'state.sqlite',cfg)
        expiry={'action':None};community=service.community
        def expire_on_action(body):
            if body.get('action')==expiry['action']:
                expiry['action']=None
                with service.store.transaction():
                    pid=service.store.authenticate(body['session'])
                    service.store.db.execute('UPDATE sessions SET expires=0 WHERE profile_id=?',(pid,))
                    service.store.emit(pid,{'channel':'COMMUNITY','type':'TEST_WAKE'})
                # Give the poll a chance to initiate recovery before this response arrives.
                time.sleep(.3)
            return community(body)
        service.community=expire_on_action
        class QuietHandler(Handler):
            def log_message(self,*args):pass
        server=ThreadingHTTPServer(('127.0.0.1',0),partial(QuietHandler,directory=str(ROOT)));server.service=service
        threading.Thread(target=server.serve_forever,daemon=True).start()
        env=dict(os.environ,XDG_DATA_HOME=str(data),XDG_STATE_HOME=str(state))
        trace=state/'boufbowl-tutorial/mock.log';log=(evidence/'launch.log').open('w');process=None
        def text():return trace.read_text() if trace.exists() else ''
        def count():return service.store.db.execute('SELECT COUNT(*) FROM profiles').fetchone()[0]
        def click(x,y):subprocess.run(['xdotool','mousemove',str(x),str(y),'click','1'],check=True);time.sleep(.35)
        def type_at(x,y,value):
            click(x,y);subprocess.run(['xdotool','key','ctrl+a'],check=True)
            subprocess.run(['xdotool','type','--clearmodifiers',value],check=True)
        def capture(name):subprocess.run(['import','-window','root',str(evidence/(name+'.png'))],check=True)
        def launch():
            before=windows();mark=text().count('Incoming CLUB_INFORMATION')
            proc=subprocess.Popen([sys.executable,str(ROOT/'play.py'),'--mode','server','--lang','fr','--profile',nickname,
                '--server-url',f'http://127.0.0.1:{server.server_port}'],env=env,stdout=log,stderr=subprocess.STDOUT)
            wait_for(lambda:text().count('Incoming CLUB_INFORMATION')>mark);wait_for(lambda:windows()-before);time.sleep(2)
            return proc
        def stop():
            subprocess.run([shutil.which('wineserver') or '/usr/lib/x86_64-linux-gnu/wine/wineserver','-k'],
                env=dict(env,WINEPREFIX=str(data/'boufbowl-tutorial/wine')),check=False)
            if process is not None:process.wait(timeout=15)
        try:
            process=launch();assert 'Club opened' not in text();assert count()==1;capture('initial-home')
            stop()
            service.store.db.execute('UPDATE sessions SET expires=0')
            process=launch();assert count()==2;assert 'Renewing unknown device session' in text()
            assert 'Club opened' not in text();capture('stale-session-home')
            print('Expired saved device session renewed without opening Club',flush=True)
            for action,button,label in (('wallet',(420,350),'Wallet opened'),('progression',(650,350),'Progression opened')):
                prior=count();expiry['action']=action
                click(910,60);click(*button)
                wait_for(lambda:label in text());assert count()==prior+1
                assert text().count('Club opened')==(1 if action=='wallet' else 2)
                capture(action+'-recovered')
            print('Wallet and league requests recover from expiry racing with poll',flush=True)
            click(910,60);click(824,309)
            username='sessionacct'+str(int(time.time()));password='Session-proof-12345'
            type_at(350,252,username);type_at(350,292,password);click(360,414)
            wait_for(lambda:service.store.db.execute('SELECT 1 FROM accounts WHERE username=?',(username,)).fetchone())
            wait_for(lambda:'Account linked' in text() or text().count('Incoming CLUB_INFORMATION')>=5)
            time.sleep(2);prior=count();menus=text().count('Club opened')
            service.store.db.execute("UPDATE sessions SET expires=0 WHERE kind='account'")
            wait_for(lambda:'Account session requires login' in text())
            assert count()==prior;assert text().count('Club opened')==menus;capture('expired-account-home')
            click(910,60);click(824,309)
            type_at(350,252,username);type_at(350,292,password);mark=text().count('Incoming CLUB_INFORMATION');click(190,414)
            wait_for(lambda:text().count('Incoming CLUB_INFORMATION')>mark)
            assert count()==prior;capture('account-reconnected')
            print('Expired account requires login without anonymous fallback or automatic Club popup',flush=True)
            assert 'ERROR' not in text(),text()
        except BaseException:
            capture('failure');raise
        finally:
            (evidence/'trace.log').write_text(text());stop();log.close();server.shutdown();server.server_close();service.close()


if __name__=='__main__':main()
