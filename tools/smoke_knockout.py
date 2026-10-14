"""Observe original qualification, elimination, round and podium artwork on a live server."""
import os,json,subprocess,sys,tempfile,time,threading,shutil
from pathlib import Path
from functools import partial
from http.server import ThreadingHTTPServer
from backend.service import Service
from backend.server import Handler
from tools.game_config import ROOT,load_config
from tools.smoke_human_match import windows,wait_for,initial_club


def main():
    cfg=load_config();cfg['general']['cinematics']['introductions']=False
    start=int(time.time())-10
    cfg['general']['tournament'].update(format='elimination',id=1,start_time=start,end_time=start+46,repeat_seconds=0,
        qualification_seconds=30,qualifying_top=4,round_count=2,round_seconds=8,stadium_rotation=[3])
    evidence=ROOT/'evidence/knockout';evidence.mkdir(parents=True,exist_ok=True)
    data=Path('/tmp/boufbowl-live-smoke-data');nickname='KnockoutWatcher'+str(int(time.time()))
    with tempfile.TemporaryDirectory(prefix='boufbowl-knockout-smoke-') as tmp:
        root=Path(tmp);service=Service(root/'state.sqlite',cfg)
        class QuietHandler(Handler):
            def log_message(self,*args):pass
        server=ThreadingHTTPServer(('127.0.0.1',0),partial(QuietHandler,directory=str(ROOT)));server.service=service
        threading.Thread(target=server.serve_forever,daemon=True).start()
        env=dict(os.environ,XDG_DATA_HOME=str(data),XDG_STATE_HOME=str(root/'state'));before=windows()
        log=(evidence/'launch.log').open('w');process=subprocess.Popen([sys.executable,str(ROOT/'play.py'),'--mode','server','--lang','en','--profile',nickname,
            '--server-url',f'http://127.0.0.1:{server.server_port}'],env=env,stdout=log,stderr=subprocess.STDOUT)
        trace=root/'state/boufbowl-tutorial/mock.log'
        def text():return trace.read_text() if trace.exists() else ''
        def capture(name):time.sleep(.4);subprocess.run(['import','-window','root',str(evidence/(name+'.png'))],check=True)
        def win(profile):
            with service.store.transaction():
                match=service.store.active_match(profile);match['score']=[0,0];match['score'][match['profiles'].index(profile)]=1;service.end_match(match)
        try:
            wait_for(lambda:'Incoming CLUB_INFORMATION' in text());wait_for(lambda:windows()-before);time.sleep(2)
            viewer=service.store.db.execute('SELECT id FROM profiles WHERE nickname=?',(nickname,)).fetchone()[0]
            players={n:service.hello({'nickname':n,'clubs':[initial_club()]}) for n in ('Alice','Bob','Carol','Dave')}
            ids={n:service.store.authenticate(p['session']) for n,p in players.items()}
            with service.store.transaction():
                service.register_tournament(viewer,service.tournament_config(1))
                for n in players:service.tournament_match(ids[n],1)
            win(ids['Alice']);win(ids['Carol'])
            subprocess.run(['xdotool','mousemove','315','605','click','1'],check=True)
            wait_for(lambda:'Incoming PAST_TOURNAMENTS' in text());capture('qualification')
            wait_for(lambda:service.round_state(1)[0]['round']==1)
            capture('round-1-eliminated-viewer')
            with service.store.transaction():
                for n in ('Alice','Dave','Carol','Bob'):service.tournament_match(ids[n],1)
            win(ids['Alice']);win(ids['Carol'])
            wait_for(lambda:service.round_state(1)[0]['round']==2)
            capture('round-2')
            with service.store.transaction():
                service.tournament_match(ids['Alice'],1);service.tournament_match(ids['Carol'],1)
            win(ids['Alice']);wait_for(lambda:'Incoming TOURNAMENT_CLOSED' in text())
            capture('final-podium')
            entries=dict(service.tournament_entries(service.tournament_config(1)))
            assert entries[ids['Alice']]['currentRank']==1 and entries[viewer]['eliminated']
            assert service.store.db.execute('SELECT COUNT(*) FROM tournament_rewards').fetchone()[0]==4
            if 'ERROR' in text():raise RuntimeError(text())
            print('Native qualification timer, round countdowns, eliminated state and final podium verified',flush=True)
        except BaseException:capture('failure');raise
        finally:
            if trace.exists():(evidence/'trace.log').write_text(text())
            wine_log=root/'state/boufbowl-tutorial/wine.log'
            if wine_log.exists():(evidence/'wine.log').write_text(wine_log.read_text(errors='replace'))
            wineserver=shutil.which('wineserver') or '/usr/lib/x86_64-linux-gnu/wine/wineserver'
            subprocess.run([wineserver,'-k'],env=dict(env,WINEPREFIX=str(data/'boufbowl-tutorial/wine')),check=False)
            process.wait(timeout=10);log.close();server.shutdown();server.server_close();service.close()


if __name__=='__main__':main()
