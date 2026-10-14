"""Native original blason selectors, last-page choices, save and restoration."""
import os,sys,subprocess,tempfile,threading,time,shutil,json
from pathlib import Path
from functools import partial
from http.server import ThreadingHTTPServer
from backend.server import Handler
from backend.service import Service
from tools.game_config import ROOT,load_config
from tools.smoke_human_match import windows,wait_for
cfg=load_config();cfg['general']['cinematics']['introductions']=False
evidence=ROOT/'evidence/heraldry';evidence.mkdir(parents=True,exist_ok=True)
with tempfile.TemporaryDirectory(prefix='heraldry-check-') as tmp:
 root=Path(tmp);state=root/'state';data=Path('/tmp/boufbowl-live-smoke-data');service=Service(root/'state.sqlite',cfg)
 class Quiet(Handler):
  def log_message(self,*a):pass
 server=ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=str(ROOT)));server.service=service
 threading.Thread(target=server.serve_forever,daemon=True).start()
 env=dict(os.environ,XDG_DATA_HOME=str(data),XDG_STATE_HOME=str(state));log=(evidence/'launch.log').open('w')
 nickname='Heraldry'+str(int(time.time()));trace=state/'boufbowl-tutorial/mock.log'
 process=subprocess.Popen([sys.executable,str(ROOT/'play.py'),'--mode','server','--lang','fr','--profile',nickname,'--server-url',f'http://127.0.0.1:{server.server_port}'],env=env,stdout=log,stderr=subprocess.STDOUT)
 try:
  wait_for(lambda:trace.exists() and 'Incoming CLUB_INFORMATION' in trace.read_text());time.sleep(2)
  pid=service.store.db.execute('SELECT id FROM profiles WHERE nickname=?',(nickname,)).fetchone()[0]
  with service.store.transaction():
   club=service.club(pid);club.update(sigilBackground=31,sigilCharge=27);service.save_club(pid,club);service.emit(pid,'CLUB_INFORMATION',club)
  time.sleep(1);subprocess.run(['xdotool','mousemove','730','201','click','1'],check=True);time.sleep(2)
  subprocess.run(['import','-window','root',str(evidence/'editor.png')],check=True)
  def click(x,y):
   subprocess.run(['xdotool','mousemove',str(x),str(y),'click','1'],check=True);time.sleep(.5)
  def drag(x,y,target):
   subprocess.run(['xdotool','mousemove',str(x),str(y),'mousedown','1','mousemove',str(x),str(target),'mouseup','1'],check=True);time.sleep(.5)
  def capture(name):subprocess.run(['import','-window','root',str(evidence/(name+'.png'))],check=True)
  click(735,295);capture('background-selector');drag(725,342,512);capture('backgrounds-last-page')
  click(553,481);click(735,243);capture('charge-selector');drag(725,300,458);capture('charges-last-page')
  click(590,455);click(853,543);capture('save-confirmation')
  mark=trace.read_text().count('Incoming CLUB_INFORMATION');click(410,379)
  wait_for(lambda:service.club(pid)['sigilBackground']==32)
  wait_for(lambda:trace.read_text().count('Incoming CLUB_INFORMATION')>mark);time.sleep(3)
  capture('saved-heraldry')
  mark=trace.read_text().count('Incoming CUSTOMISATION_SESSION_ACCEPTED');click(730,201)
  wait_for(lambda:trace.read_text().count('Incoming CUSTOMISATION_SESSION_ACCEPTED')>mark);time.sleep(2)
  capture('restored-heraldry')
  club=service.club(pid);assert (club['sigilBackground'],club['sigilCharge'])==(32,27),club
  assert 'ERROR' not in trace.read_text(),trace.read_text()
  print('Native high-ID heraldry selection saved; all selector artwork initialized without errors',flush=True)
 finally:
  if trace.exists():(evidence/'trace.log').write_text(trace.read_text())
  subprocess.run([shutil.which('wineserver') or '/usr/lib/x86_64-linux-gnu/wine/wineserver','-k'],env=dict(env,WINEPREFIX=str(data/'boufbowl-tutorial/wine')),check=False)
  process.wait(timeout=15);server.shutdown();server.server_close();service.close();log.close()
