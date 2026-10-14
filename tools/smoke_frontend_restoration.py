"""Native wallet/news/moderation/league panels and replay controls against a live server."""
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
from tools.smoke_human_match import windows,wait_for,initial_club


def main():
    cfg=load_config();cfg['general']['cinematics']['introductions']=False
    cfg['general']['economy']['free_customization']=False
    cfg['rules']['match'].update(turns_per_match=2,turns_per_period=2)
    language=os.environ.get('BOUFBOWL_SMOKE_LANG','en')
    evidence=ROOT/('evidence/frontend-restoration'+('-'+language if language!='en' else ''));evidence.mkdir(parents=True,exist_ok=True)
    data=Path(os.environ.get('BOUFBOWL_SMOKE_DATA','/tmp/boufbowl-live-smoke-data'))
    nickname='FrontendRestore'+str(int(time.time()))
    with tempfile.TemporaryDirectory(prefix='boufbowl-restoration-smoke-') as tmp:
        root=Path(tmp);state=root/'state';service=Service(root/'state.sqlite',cfg)
        class QuietHandler(Handler):
            def log_message(self,*args):pass
        server=ThreadingHTTPServer(('127.0.0.1',0),partial(QuietHandler,directory=str(ROOT)));server.service=service
        threading.Thread(target=server.serve_forever,daemon=True).start()
        env=dict(os.environ,XDG_DATA_HOME=str(data),XDG_STATE_HOME=str(state))
        before=windows();log=(evidence/'launch.log').open('w')
        process=subprocess.Popen([sys.executable,str(ROOT/'play.py'),'--mode','server','--lang',language,'--profile',nickname,
            '--server-url',f'http://127.0.0.1:{server.server_port}'],env=env,stdout=log,stderr=subprocess.STDOUT)
        trace=state/'boufbowl-tutorial/mock.log'
        def text():return trace.read_text() if trace.exists() else ''
        def click(x,y):subprocess.run(['xdotool','mousemove',str(x),str(y),'click','1'],check=True);time.sleep(.35)
        def type_at(x,y,value):
            click(x,y);subprocess.run(['xdotool','key','ctrl+a'],check=True);subprocess.run(['xdotool','type','--clearmodifiers',value],check=True)
        def capture(name):subprocess.run(['import','-window','root',str(evidence/(name+'.png'))],check=True)
        def menu():click(910,60)
        try:
            wait_for(lambda:'Incoming CLUB_INFORMATION' in text());wait_for(lambda:windows()-before);time.sleep(3)
            actor=service.store.db.execute('SELECT id FROM profiles WHERE nickname=?',(nickname,)).fetchone()[0]
            subprocess.run([sys.executable,'-m','backend.manage','--database',str(root/'state.sqlite'),'role',nickname,'moderator'],cwd=ROOT,check=True)
            with service.store.transaction():
                stats=service.store.profile(actor)['statistics'];stats.update(wins=3,rating=1400,tournament_wallet={'glory':0,'influence':0,'coins':30})
                service.store.db.execute('UPDATE profiles SET statistics_json=? WHERE id=?',(json.dumps(stats),actor));service.emit_ranking(actor)
            time.sleep(1);capture('home-qualified')
            menu();capture('menu');click(420,350)
            wait_for(lambda:'Wallet opened' in text());capture('wallet');click(740,266)
            wait_for(lambda:service.store.db.execute('SELECT COUNT(*) FROM economy_ledger WHERE profile_id=?',(actor,)).fetchone()[0]==1)
            assert service.store.profile(actor)['statistics']['tournament_wallet']['coins']==10
            capture('wallet-purchased');print('Native wallet and cosmetic purchase verified',flush=True)
            menu();click(650,350);wait_for(lambda:'Progression opened' in text());capture('progression')
            menu();click(190,395);wait_for(lambda:'News opened' in text());capture('news');print('League and original news artwork rendered',flush=True)
            peer=service.hello({'nickname':'ModeratedPeer','clubs':[initial_club()]})
            menu();click(420,395);wait_for(lambda:'Moderation opened' in text());capture('moderation')
            type_at(360,185,'ModeratedPeer');type_at(350,225,'Native test');click(500,315)
            wait_for(lambda:service.store.db.execute("SELECT 1 FROM sanctions WHERE kind='mute'").fetchone())
            capture('moderation-muted');print('Native moderator action and operator role provisioning verified',flush=True)
            maker=service.hello({'nickname':'ReplayMaker','clubs':[initial_club()]})
            with service.store.transaction():
                match=service.create_match(service.store.authenticate(maker['session']),None,1)
                service.finish_placement(match)
                for _ in range(2):
                    service.resolve(match);service.advance(match);service.store.save_match(match)
                service.store.db.execute('INSERT INTO replay_access VALUES(?,?)',(actor,match['id']))
            menu();click(190,350);click(430,207);time.sleep(.5)
            type_at(230,472,str(match['id']));click(215,515)
            wait_for(lambda:'Playback script built' in text(),120)
            click(80,595);wait_for(lambda:'Replay paused' in text());capture('replay-paused')
            count=text().count('Outgoing ResolutionDoneMessage');time.sleep(3)
            assert text().count('Outgoing ResolutionDoneMessage')==count
            click(80,595);wait_for(lambda:'Replay resumed' in text())
            click(200,595);wait_for(lambda:'Replay speed 2' in text());capture('replay-speed')
            click(465,595);wait_for(lambda:'Replay seeking turn 2' in text());capture('replay-seek')
            wait_for(lambda:'Incoming MATCH_END' in text(),120);capture('replay-result')
            assert service.store.db.execute('SELECT COUNT(*) FROM turns').fetchone()[0]==2
            assert service.store.profile(actor)['statistics']['wins']==3
            print('Native replay pause/resume, speed, turn snapshot selection and result verified',flush=True)
            if 'ERROR' in text():raise RuntimeError(text())
        except BaseException:
            capture('failure');raise
        finally:
            if trace.exists():(evidence/'trace.log').write_text(text())
            wine_log=state/'boufbowl-tutorial/wine.log'
            if wine_log.exists():(evidence/'wine.log').write_text(wine_log.read_text(errors='replace'))
            wineserver=shutil.which('wineserver') or '/usr/lib/x86_64-linux-gnu/wine/wineserver'
            subprocess.run([wineserver,'-k'],env=dict(env,WINEPREFIX=str(data/'boufbowl-tutorial/wine')),check=False)
            process.wait(timeout=10);log.close();server.shutdown();server.server_close();service.close()


if __name__=='__main__':main()
