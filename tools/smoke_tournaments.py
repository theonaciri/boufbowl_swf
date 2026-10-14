"""Verify original tournament future/running/closing/past panels against a live server."""
import os
import argparse
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
from tools.smoke_human_match import windows, wait_for, click, initial_club


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--play-only',action='store_true');args=parser.parse_args()
    cfg=load_config();cfg['general']['cinematics']['introductions']=False
    start=int(time.time())-5 if args.play_only else int(time.time())+35
    cfg['general']['tournament'].update(format='league',id=1,start_time=start,end_time=start+15,repeat_seconds=60,stadium_rotation=[3,5])
    if args.play_only: cfg['general']['tournament'].update(end_time=start+120,repeat_seconds=0)
    cfg['rules']['match'].update(turns_per_match=1,turns_per_period=1,placement_seconds=3,planning_seconds=3)
    evidence=ROOT/'evidence/tournament-lifecycle';evidence.mkdir(parents=True,exist_ok=True)
    data=Path(os.environ.get('BOUFBOWL_SMOKE_DATA','/tmp/boufbowl-live-smoke-data'))
    with tempfile.TemporaryDirectory(prefix='boufbowl-tournament-smoke-') as tmp:
        root=Path(tmp);state=root/'state';service=Service(root/'state.sqlite',cfg)
        class QuietHandler(Handler):
            def log_message(self,*args):pass
        server=ThreadingHTTPServer(('127.0.0.1',0),partial(QuietHandler,directory=str(ROOT)));server.service=service
        threading.Thread(target=server.serve_forever,daemon=True).start()
        env=dict(os.environ,XDG_DATA_HOME=str(data),XDG_STATE_HOME=str(state))
        before=windows();log=(evidence/'launch.log').open('w')
        process=subprocess.Popen([sys.executable,str(ROOT/'play.py'),'--mode','server','--lang','en',
            '--profile','TournamentObserver'+str(int(time.time())),'--server-url',f'http://127.0.0.1:{server.server_port}'],env=env,stdout=log,stderr=subprocess.STDOUT)
        trace=state/'boufbowl-tutorial/mock.log'
        def capture(name):
            time.sleep(.6);subprocess.run(['import','-window','root',str(evidence/(name+'.png'))],check=True)
        try:
            wait_for(lambda:trace.exists() and 'Incoming CLUB_INFORMATION' in trace.read_text());wait_for(lambda:windows()-before)
            window=sorted(windows()-before)[-1];time.sleep(3)
            capture("home")
            subprocess.run(["xdotool","mousemove","315","605","click","1"],check=True)
            capture("selected")
            wait_for(lambda:'Incoming PAST_TOURNAMENTS' in trace.read_text(),15)
            tournament_id=1 if args.play_only else 2
            match_id=1 if args.play_only else 2
            if not args.play_only:
                capture('future');print('Future schedule/countdown rendered',flush=True)
                wait_for(lambda:service.current_tournament_id()=='1')
                time.sleep(1);capture('running');print('Running tournament/rewards/timer rendered',flush=True)
                players=[service.hello({'nickname':n,'clubs':[initial_club()]}) for n in ('TournamentAlice','TournamentBob')]
                with service.store.transaction():
                    for p in players:service.tournament_match(service.store.authenticate(p['session']),1)
                    match=service.store.active_match(service.store.authenticate(players[0]['session']))
                    match['deadline']=time.time()+600;service.store.save_match(match)
                wait_for(lambda:service.store.db.execute('SELECT phase FROM tournaments WHERE id=1').fetchone()[0]=='closing')
                capture('closing');print('Entry closed while started match continues',flush=True)
                match['score']=[2,1]
                with service.store.transaction():service.end_match(match)
                wait_for(lambda:'Incoming TOURNAMENT_CLOSED' in trace.read_text())
                capture('past');print('Final podium/rewards and closed notification rendered',flush=True)
                click(window,90,445);capture('next');print('Next tournament countdown rendered',flush=True)
                assert service.store.db.execute('SELECT COUNT(*) FROM tournament_rewards').fetchone()[0]==2
                wait_for(lambda:service.current_tournament_id()=='2')
            time.sleep(1)
            subprocess.run(['xdotool','mousemove','515','565','click','1'],check=True)
            wait_for(lambda:'Outgoing MatchRequestMessage' in trace.read_text())
            wait_for(lambda:service.store.db.execute('SELECT COUNT(*) FROM matchmaking_queue').fetchone()[0]==1)
            peer=service.hello({'nickname':'TournamentPeer','clubs':[initial_club()]})
            with service.store.transaction():service.tournament_match(service.store.authenticate(peer['session']),tournament_id)
            wait_for(lambda:'Incoming MATCH_INFORMATION' in trace.read_text())
            wait_for(lambda:'Outgoing ResolutionDoneMessage' in trace.read_text(),120)
            wait_for(lambda:len(service.store.match(match_id)['acks'])==1)
            service.command({'session':peer['session'],'request_id':'peer-ack','operation':'protocol','hex':service.codec.envelope('RESOLUTION_DONE',{'turn':1}).hex()})
            wait_for(lambda:'Incoming MATCH_END' in trace.read_text(),30)
            capture('played-match')
            assert service.store.db.execute('SELECT COUNT(*) FROM turns').fetchone()[0]==1
            actual=service.store.match(match_id)
            assert actual['source']=='tournament' and actual['tournament']==tournament_id and all(actual['profiles'])
            print('Original Register and Play paired two humans and completed a native turn',flush=True)
            text=trace.read_text()
            if 'ERROR:' in text:raise RuntimeError(text)
            (evidence/('play-trace.log' if args.play_only else 'trace.log')).write_text(text)
            print('Verified native tournament lifecycle',flush=True)
        finally:
            if trace.exists():(evidence/('play-trace.log' if args.play_only else 'trace.log')).write_text(trace.read_text())
            wine_log=state/'boufbowl-tutorial/wine.log'
            if wine_log.exists():(evidence/'wine.log').write_text(wine_log.read_text(errors='replace'))
            wineserver=shutil.which('wineserver') or '/usr/lib/x86_64-linux-gnu/wine/wineserver'
            subprocess.run([wineserver,'-k'],env=dict(env,WINEPREFIX=str(data/'boufbowl-tutorial/wine')),check=False)
            process.wait(timeout=10);log.close();server.shutdown();server.server_close();service.close()


if __name__=='__main__':main()
