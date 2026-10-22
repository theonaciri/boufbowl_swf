"""Build deterministic engine probes and original-player interaction fixtures."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
from backend.engine import Engine
from backend.turn_adapter import adapt_turn, cell
from tools.build_mock_fixture import build_fixture
from tools.flash_protocol import Codec
from tools.game_config import load_config, ROOT


def records():
    config=load_config(); baseline=json.loads((ROOT/'tests/fixtures/movement_engine_turn.json').read_text())['initial']
    engine=Engine()
    try:
        for name in ('pickup','combat','reception','interception','rebound','ability','goal'):
            world=deepcopy(baseline); entities={e['id']:e for e in world['entities']}
            actor,receiver,enemy=entities[11],entities[12],entities[21]
            actor['position']={'q':0,'r':0}
            receiver['position']={'q':3,'r':0}
            selected=[]
            if name=='pickup': selected=[{'entity_id':11,'action_type':'pickup','params':{'elements':{'TERRE':0,'FEU':1,'AIR':0,'EAU':2}}}]
            elif name=='combat':
                enemy['position']={'q':1,'r':0}; actor['stats']['strength']=100; enemy['stats']['agility']=0
                selected=[{'entity_id':11,'action_type':'move','params':{'target_position':{'q':1,'r':0},'elements':{'TERRE':1,'FEU':0,'AIR':0,'EAU':2}}}]
            elif name=='ability': selected=[{'entity_id':11,'action_type':'ability','params':{}}]
            elif name=='goal':
                actor['position']={'q':15,'r':0}
                selected=[{'entity_id':11,'action_type':'move','params':{'target_position':{'q':16,'r':0},'elements':{'TERRE':0,'FEU':0,'AIR':0,'EAU':3}}}]
            else:
                actor['stats']['precision']=100; receiver['stats']['precision']=100; receiver['stats']['agility']=100
                if name=='interception':
                    enemy['position']={'q':3,'r':0}; enemy['stats']['precision']=100; enemy['stats']['agility']=100
                    receiver['position']={'q':-5,'r':-1}
                elif name=='rebound':
                    receiver['stats']['precision']=0; receiver['stats']['agility']=0
                target=21 if name=='interception' else 12
                selected=[{'entity_id':11,'action_type':'throw','params':{'target_entity_id':target,'elements':{'TERRE':0,'FEU':0,'AIR':3,'EAU':0}}}]
            if name in ('reception','interception','rebound','goal'):
                world['ball'].update(holder_entity_id=11,position=deepcopy(actor['position']))
                actor['status']['carrying_ball']=True
            if name in ('reception','rebound'):
                selected.append({'entity_id':12,'action_type':'wait','params':{'elements':{'TERRE':0,'FEU':0,'AIR':3,'EAU':0}}})
            orders=[{'player_id':str(team),'turn_number':1,'team_index':team,'nonce':name+str(team),'actions':selected if team==0 else []} for team in (0,1)]
            if name=='interception': orders[1]['actions']=[{'entity_id':21,'action_type':'wait','params':{'elements':{'TERRE':0,'FEU':0,'AIR':3,'EAU':0}}}]
            rules=deepcopy(config['rules'])
            if name=='rebound': rules['simulation']['simulation'].update(catch_base=0,catch_stat=0,catch_feu=0,catch_air=0,probability_min=0)
            simulated=engine.simulate(world,orders,1,12345,rules,(False,False))
            record={'format_version':1,'initial':world,'orders':simulated['orders'],'result':simulated['result'],'rules':rules,'rules_version':config['rules_version']}
            yield name,record
    finally: engine.close()


def fixture(name,record):
    base=build_fixture(); codec=Codec(); steps=base['steps']; hp={e['id']:e['hp'] for e in record['initial']['entities']}
    def state(world):
        payload=deepcopy(steps[1]['decoded']); payload['boufbowlerPositions']=[{'id':str(e['id']),'position':cell(e['position'])} for e in world['entities'] if e['hp']>0]
        payload['teamState']['boufbowlerStates']=[{'id':str(e['id']),'status':4 if e['hp']<=0 else 3 if e['status']['knocked_down'] else 1,'currentHitPoints':e['hp'],'remainingClassOrderUses':e['ability_uses_remaining']} for e in world['entities']]
        ball=world['ball']; payload['boufballState']={'status':2,'holderId':str(ball['holder_entity_id'])} if ball['holder_entity_id'] is not None else {'status':1,'position':cell(ball['position'])}
        return payload
    def assign(index,payload): steps[index].update(decoded=payload,hex=codec.envelope(steps[index]['type'],payload).hex())
    assign(1,state(record['initial'])); assign(2,adapt_turn(record)); final=state(record['result']['final_world_state']); final['teamState']['turn']=2; assign(3,final)
    base.update(name=name+' engine interaction probe',description='Authoritative engine result rendered through the original client.')
    return base


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cinematics',action='store_true',help='Enable full-screen interaction cinematics in generated scenarios')
    parser.add_argument('--output',type=Path,default=ROOT/'tests/fixtures/interactions')
    args=parser.parse_args()
    directory=args.output; directory.mkdir(parents=True,exist_ok=True)
    for name,record in records():
        if args.cinematics: record['presentation']={'interactions':True}
        (directory/(name+'-record.json')).write_text(json.dumps(record,indent=2)+'\n')
        (directory/(name+'.json')).write_text(json.dumps(fixture(name,record),indent=2)+'\n')
        print(name,sorted({e['type'] for e in record['result']['events']}))
