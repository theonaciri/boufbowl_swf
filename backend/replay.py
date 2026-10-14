"""Export immutable recorded turns to the original-client replay harness."""
from copy import deepcopy
import json
from backend.storage import ServiceError
from backend.results import result_kind
from backend.turn_adapter import adapt_turn


def export_replay(service, match_id, verify=False, profile=None):
    match=service.store.match(match_id)
    if profile is not None:
        if profile not in match["profiles"] and not service.store.db.execute("SELECT 1 FROM replay_access WHERE profile_id=? AND match_id=?", (profile,match_id)).fetchone():
            raise ServiceError("MATCH_OWNERSHIP", "Replay is available to participants and registered spectators")
        if profile not in match["profiles"] and any(service.blocked(profile,p) for p in match["profiles"]):
            raise ServiceError("PLAYER_UNAVAILABLE", "This replay is unavailable")
    records=[json.loads(row[0]) for row in service.store.db.execute('SELECT record_json FROM turns WHERE match_id=? ORDER BY turn',(match_id,))]
    if not records:
        raise ServiceError('REPLAY_EMPTY','This match has no resolved turns')
    completed = match['phase'] == 'ended'
    if verify and not completed:
        raise ServiceError('REPLAY_ACTIVE', 'Full replay verification is available after the match ends')
    if verify:
        for record in records:
            expected=record['result']
            reproduced=service.engine.simulate(record['initial'],record['orders'],expected['turn_number'],expected['seed'],record['rules'],(False,False))['result']
            if reproduced['simulation_version']!=expected['simulation_version'] or reproduced['final_state_hash']!=expected['final_state_hash'] or reproduced['events']!=expected['events']:
                raise ServiceError('REPLAY_MISMATCH','Recorded simulation cannot be reproduced by this engine version')
    initial_match=deepcopy(match); initial_match["period"]=1
    information=service.match_information(initial_match,1)
    information.pop("side"); information.pop("placementZone"); information["skipIntro"]=True
    steps=[];chapters=[]
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
        chapters.append({'turn':turn,'period':snapshot['period'],'field_step':len(steps),'zobal_masks':{str(e['id']):e['zobal_mask'] for e in record['initial']['entities'] if 'zobal_mask' in e}})
        append('FIELD_STATE',service.field_state(snapshot,2),wait=index>0)
        append('RESOLUTION_SCENARIO',record.get('scenario') or adapt_turn(record),delay=2000)
        score=[a+b for a,b in zip(score,record['result']['score'])]
    snapshot.update(world=records[-1]['result']['final_world_state'],turn=records[-1]['result']['turn_number']+1)
    snapshot['score']=score
    snapshot['period']=(snapshot['turn']-1)//match['rules']['match']['turns_per_period']+1
    append('FIELD_STATE',service.field_state(snapshot,2),wait=True)
    ending=match.get('end_payload') or {'id':str(match_id),'leftScore':match['score'][0],'rightScore':match['score'][1],
                                      'leftRanking':{'wins':0,'draws':0,'defeats':0},'rightRanking':{'wins':0,'draws':0,'defeats':0}}
    if match['phase']!='ended':
        ending.update(leftScore=score[0],rightScore=score[1])
    append('MATCH_END',ending,delay=2000)
    return {'format_version':1,'completed':match['phase']=='ended','name':f'Saved match {match_id}' if match['phase']=='ended' else f'Active match {match_id} snapshot','rules_version':match['rules_version'],
            'chapters':chapters,'description':'Recorded authoritative simulation. Export does not alter match statistics.',
            'result_kind':result_kind(match),'verified':verify,'audit_available':completed,'steps':steps,'records':records if completed else []}
