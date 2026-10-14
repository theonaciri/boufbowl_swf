"""Build an authored Kara comparison match: 14 turns, halftime and a 0:2 finish.

The reference exposes selected planning frames, not both players' complete orders
or random seeds. This is a similar reproducible match, not an exact reconstruction.
"""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import time
from backend.service import Service
from backend.replay import export_replay
from tools.build_mock_fixture import build_fixture
from tools.game_config import load_config


def build():
    config=load_config();config['general']['cinematics']['introductions']=False
    template=build_fixture()['steps'][0]['decoded']
    class_ids={'Rogue':9,'Sacrier':10,'Sram':12,'Sadida':11,'Iop':6,'Eniripsa':3}
    teams=[('Les Atlantes',[("Bemby","Rogue",2),("Crif","Sacrier",1),("Kivette","Sram",2),("Pall","Sacrier",1),("Jack","Sram",1)]),
           ('Les Ferrari Brumairiennes',[("Agre","Sadida",1),("Fero","Sadida",1),("Passer","Rogue",1),("Defender","Iop",1),("Support","Eniripsa",2)])]
    colors=[{'r':150,'g':117,'b':23},{'r':116,'g':24,'b':24}]
    with tempfile.TemporaryDirectory() as folder:
        service=Service(Path(folder)/'comparison.sqlite',config)
        try:
            profiles=[]
            for side,(name,players) in enumerate(teams):
                roster=deepcopy(template['leftRoster']['characters'])
                for i,p in enumerate(roster):
                    n,cls,gender=players[i%5];p.update(name=n if i<5 else n+' reserve',boufbowlerClass=class_ids[cls],gender=gender)
                club={'clubId':'1','clubName':name,'boufbowler':roster,'paletteId':1,'firstColor':colors[side],
                      'secondColor':{'r':220,'g':220,'b':220},'patternColor':{'r':30,'g':30,'b':30},'sigilBackground':1,'sigilCharge':1,'isPredefinedClub':False}
                profiles.append(service.store.authenticate(service.hello({'nickname':name,'clubs':[club]})['session']))
            with service.store.transaction():
                match=service.create_match(*profiles,6)
                for turn in range(1,15):
                    if match['phase']=='placement':
                        service.finish_placement(match)
                        positions={1:(-7,-8),2:(-10,-7),3:(-11,6),4:(-7,-5),5:(-12,8),
                                   101:(4,0),102:(4,2),103:(10,-8),104:(-5,-5),105:(9,7)}
                        if turn>=8:positions={identity:(-q-r,r) for identity,(q,r) in positions.items()}
                        for e in match['world']['entities']:e['position']=dict(zip(('q','r'),positions[e['id']]))
                    match['deadline']=time.time()+600
                    actions={0:[],1:[]}
                    for e in match['world']['entities']:
                        params={'elements':{'TERRE':0,'FEU':0,'AIR':0,'EAU':3}};kind='wait'
                        identity=e['id']
                        if identity==3 and turn==1:
                            kind='move';params.update(target_position={'q':-4,'r':6},elements={'TERRE':3,'FEU':0,'AIR':0,'EAU':0})
                        if identity==2 and turn==2:kind='ability';params={}
                        if identity==4 and turn==3:kind='move';params['target_position']={'q':-6,'r':-5}
                        if turn==4 and identity in (4,104):
                            kind='move';params['target_position']={'q':-7 if identity==4 else -3,'r':-5}
                        if identity==101 and turn in (1,6,8):
                            kind='move';params.update(target_position={'q':0,'r':0},elements={'TERRE':0,'FEU':1,'AIR':0,'EAU':2})
                        if identity==102 and turn in (1,6,8):
                            kind='move';params.update(target_position={'q':0,'r':2},elements={'TERRE':0,'FEU':0,'AIR':1,'EAU':2})
                        if identity==101 and turn in (2,7,9):
                            kind='throw';params.update(target_entity_id=102,elements={'TERRE':0,'FEU':0,'AIR':3,'EAU':0})
                        if identity==102 and turn in (2,7,9):params['elements']={'TERRE':0,'FEU':0,'AIR':1,'EAU':2}
                        targets={3:-6,4:-10,5:-14,10:4,11:7,12:8,13:10,14:12}
                        if identity==102 and turn in targets:kind='move';params['target_position']={'q':targets[turn],'r':2}
                        actions[e['team_id']].append({'entity_id':identity,'action_type':kind,'params':params})
                    orders=[{'player_id':profiles[side],'turn_number':turn,'team_index':side,'nonce':'reference-'+str(turn), 'actions':actions[side]} for side in (0,1)]
                    # Choose documented deterministic probe seeds for the authored events.
                    def wanted(result):
                        events=result['events']
                        if turn in (2,7,9):return any(e['type']=='catch' and e['actor']==102 for e in events)
                        if turn==3:return any(e['type']=='damage' and e['actor']==4 and e['params']['hp']==11 for e in events)
                        return True
                    for seed in range(1,257):
                        result=service.engine.simulate(match['world'],orders,turn,seed,match['rules'],(False,False))['result']
                        if wanted(result):break
                    else:raise RuntimeError('Cannot reproduce authored event on turn '+str(turn))
                    match['orders']={str(side+1):order for side,order in enumerate(orders)}
                    match['turn_seeds'][str(turn)]=seed
                    service.resolve(match);service.store.save_match(match)
                    service.advance(match);service.store.save_match(match)
                if match['score']!=[0,2]:raise RuntimeError('Comparison score differs: '+str(match['score']))
                replay=export_replay(service,match['id'],True,profiles[0])
                replay.update(name='Kara reference comparison — authored similar match',
                    description='14 turns; right-team goals on turns 5/14, halftime after turn 7. Positions/orders are authored, not recovered from the video.')
                for step in replay['steps']:
                    step['after_ms']=300 if step['type']!='RESOLUTION_SCENARIO' else 1200
                replay['steps'][0]['after_ms']=0
                return replay
        finally:service.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    replay=build();args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(replay,indent=2)+'\n')
    print('Verified',len(replay['records']),'turns; score',replay['steps'][-1]['decoded']['leftScore'],replay['steps'][-1]['decoded']['rightScore'])
