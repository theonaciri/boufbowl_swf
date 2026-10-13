"""Export immutable recorded turns to the original-client replay harness."""
from copy import deepcopy
import json
from backend.storage import ServiceError
from backend.turn_adapter import adapt_turn


def export_replay(service, match_id, verify=False, profile=None):
    match=service.store.match(match_id)
    if profile is not None:
        service.side(match,profile)
    records=[json.loads(row[0]) for row in service.store.db.execute('SELECT record_json FROM turns WHERE match_id=? ORDER BY turn',(match_id,))]
    if not records:
        raise ServiceError('REPLAY_EMPTY','This match has no resolved turns')
    if verify:
        for record in records:
            expected=record['result']
            reproduced=service.engine.simulate(record['initial'],record['orders'],expected['turn_number'],expected['seed'],record['rules'],(False,False))['result']
            if reproduced['simulation_version']!=expected['simulation_version'] or reproduced['final_state_hash']!=expected['final_state_hash'] or reproduced['events']!=expected['events']:
                raise ServiceError('REPLAY_MISMATCH','Recorded simulation cannot be reproduced by this engine version')
    information=service.match_information(match,1)
    steps=[]
    def append(name,payload,wait=False,delay=500):
        packet=service.packet(name,payload,'MATCH'); packet.update(decoded=payload,after_ms=delay)
        if wait: packet['wait_for']='ResolutionDoneMessage'
        steps.append(packet)
    append('MATCH_INFORMATION',information,delay=0)
    snapshot=deepcopy(match); snapshot['phase']='orders'
    score=[0,0]
    for index,record in enumerate(records):
        turn=record['result']['turn_number']
        snapshot.update(world=record['initial'],turn=turn,period=(turn-1)//match['rules']['match']['turns_per_period']+1,score=score[:])
        append('FIELD_STATE',service.field_state(snapshot,2),wait=index>0)
        append('RESOLUTION_SCENARIO',adapt_turn(record),delay=2000)
        score=[a+b for a,b in zip(score,record['result']['score'])]
    snapshot.update(world=records[-1]['result']['final_world_state'],turn=records[-1]['result']['turn_number']+1)
    snapshot['score']=score
    append('FIELD_STATE',service.field_state(snapshot,2),wait=True)
    append('MATCH_END',{'id':str(match_id),'leftScore':match['score'][0],'rightScore':match['score'][1],
                      'leftRanking':{'wins':0,'draws':0,'defeats':0},'rightRanking':{'wins':0,'draws':0,'defeats':0}},delay=2000)
    return {'format_version':1,'name':f'Saved match {match_id}','rules_version':match['rules_version'],
            'description':'Recorded authoritative simulation. Export does not alter match statistics.',
            'verified':verify,'steps':steps,'records':records}
