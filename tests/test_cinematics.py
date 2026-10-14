"""Cinematic presentation gating must not advance gameplay authority early."""
from copy import deepcopy
import json
import time
import unittest
from backend.service import Service
from backend.storage import ServiceError
from backend.turn_adapter import adapt_turn, limit_ball_cutscenes
from tests import test_backend as helpers
from tools.game_config import ROOT


class CinematicTests(unittest.TestCase):
    tearDown=helpers.BackendTests.tearDown
    command=helpers.BackendTests.command
    protocol=helpers.BackendTests.protocol
    identity=helpers.BackendTests.identity

    def setUp(self):
        helpers.BackendTests.setUp(self)
        self.config['general']['cinematics']['introductions']=True
        self.service.config['general']['cinematics']['introductions']=True

    def test_cpu_intro_waits_for_owner_then_starts_full_placement_clock(self):
        self.command(self.alice,'cpu_match',stadium=1)
        match=self.service.store.active_match(self.identity(self.alice))
        self.assertEqual(match['phase'],'introduction')
        packets=self.service.store.poll(self.identity(self.alice),0)
        self.assertFalse(any(p['type']=='FIELD_STATE' for p in packets))
        self.assertFalse(self.service.match_information(match,1)['skipIntro'])
        with self.assertRaises(ServiceError):self.protocol(self.alice,'PLACEMENT',{'turn':1,'boufbowlerPositions':[]})
        self.protocol(self.bob,'INTRODUCTION_DONE',{})
        self.assertEqual(self.service.store.match(match['id'])['phase'],'introduction')
        self.protocol(self.alice,'INTRODUCTION_DONE',{})
        placed=self.service.store.match(match['id'])
        self.assertEqual(placed['phase'],'placement')
        self.assertGreater(placed['deadline']-time.time(),placed['rules']['match']['placement_seconds']-1)
        self.protocol(self.alice,'INTRODUCTION_DONE',{})
        self.assertEqual(self.service.store.match(match['id'])['deadline'],placed['deadline'])

    def test_human_intro_requires_both_acks_and_restores_after_restart(self):
        self.command(self.alice,'queue_join');self.command(self.bob,'queue_join')
        match=self.service.store.active_match(self.identity(self.alice))
        self.protocol(self.alice,'INTRODUCTION_DONE',{})
        self.assertEqual(self.service.store.match(match['id'])['phase'],'introduction')
        self.service.close();self.service=Service(self.path,self.config)
        self.assertTrue(self.service.match_information(self.service.store.match(match["id"]),1)["skipIntro"])
        self.service.hello({'session':self.bob['session']})
        self.assertFalse(self.service.match_information(self.service.store.match(match['id']),2)['skipIntro'])
        self.protocol(self.bob,'INTRODUCTION_DONE',{})
        self.assertEqual(self.service.store.match(match['id'])['phase'],'placement')
        self.assertTrue(self.service.match_information(self.service.store.match(match['id']),1)['skipIntro'])

    def test_intro_timeout_falls_back_to_placement_without_resolving_a_turn(self):
        self.command(self.alice,'cpu_match',stadium=1)
        with self.service.store.transaction():
            match=self.service.store.active_match(self.identity(self.alice));match['deadline']=time.time()-1
            self.service.tick_match(match)
        self.assertEqual(self.service.store.match(match['id'])['phase'],'placement')
        self.assertEqual(self.service.store.db.execute('SELECT COUNT(*) FROM turns').fetchone()[0],0)

    def test_spectator_does_not_replay_or_acknowledge_owner_intro(self):
        self.command(self.alice,'cpu_match',stadium=1)
        match=self.service.store.active_match(self.identity(self.alice))
        self.service.community({'session':self.bob['session'],'action':'spectate','match':str(match['id'])})
        packet=next(p for p in self.service.store.poll(self.identity(self.bob),0) if p['type']=='MATCH_INFORMATION')
        self.assertTrue(self.service.codec.open_envelope(bytes.fromhex(packet['hex']))['payload']['skipIntro'])
        self.protocol(self.bob,'INTRODUCTION_DONE',{})
        self.assertEqual(self.service.store.match(match['id'])['intro_acks'],[])

    def test_cinematic_flags_do_not_change_authoritative_outcomes_or_legacy_records(self):
        for name in ('combat','reception','interception','rebound','goal'):
            record=json.loads((ROOT/'tests/fixtures/interactions'/f'{name}-record.json').read_text())
            expected=deepcopy(record['result'])
            old=adapt_turn(record)
            self.assertFalse(any(i['interactionDetails']['isCutscene'] for i in old['interaction']))
            record['presentation']={'interactions':True}
            animated=adapt_turn(record)
            self.assertEqual(any(i['interactionDetails']['isCutscene'] for i in animated['interaction']),name!='combat',name)
            self.assertEqual(record['result'],expected)
            record['presentation']['interactions']=False
            self.assertEqual(adapt_turn(record),old)


    def test_ball_carrier_fights_allow_one_cinematic_and_off_ball_fights_do_not_consume_it(self):
        record=json.loads((ROOT/'tests/fixtures/interactions/combat-record.json').read_text())
        record['presentation']={'interactions':True}
        without=adapt_turn(record)
        self.assertFalse(any(i['interactionDetails']['isCutscene'] for i in without['interaction']))
        actor=next(e['actor'] for e in record['result']['events'] if e['type']=='duel')
        for carrier in (actor,next(e['params']['defender'] for e in record['result']['events'] if e['type']=='duel')):
            record['initial']['ball']['holder_entity_id']=carrier
            with_ball=adapt_turn(record)
            self.assertEqual(sum(i['interactionDetails']['isCutscene'] for i in with_ball['interaction']),1)
            fight=deepcopy(with_ball['interaction'][0]);fight['interactionId']=2;fight['interactionDetails']['startTick']+=100
            combined=deepcopy(without);combined['interaction']+=with_ball['interaction']+[fight]
            for index,entry in enumerate(combined['interaction'],1):entry['interactionId']=index;entry['interactionDetails']['isCutscene']=True
            filtered=limit_ball_cutscenes(combined)
            self.assertEqual([i['interactionDetails']['isCutscene'] for i in filtered['interaction']],[False,True,False])
            for entry in combined['interaction']:entry['interactionDetails']['isCutscene']=False
            self.assertEqual(limit_ball_cutscenes(filtered),filtered)

    def test_one_per_action_type_keeps_field_playback_and_links_and_resets_each_turn(self):
        record=json.loads((ROOT/'tests/fixtures/interactions/reception-record.json').read_text())
        record['presentation']={'interactions':True};scenario=adapt_turn(record)
        scenario['interaction']+=deepcopy(scenario['interaction'])
        for index,entry in enumerate(scenario['interaction'],1):
            entry['interactionId']=index;entry['interactionDetails']['startTick']=index*100;entry['interactionDetails']['isCutscene']=True
        before=deepcopy(scenario);filtered=limit_ball_cutscenes(scenario)
        self.assertEqual([e['interactionDetails']['isCutscene'] for e in filtered['interaction']],[True,True,False,False])
        self.assertEqual(scenario,before)
        for original,changed in zip(before['interaction'],filtered['interaction']):
            changed['interactionDetails']['isCutscene']=original['interactionDetails']['isCutscene']
        self.assertEqual(filtered,before)
        scenario['turn']+=1
        self.assertEqual(sum(e['interactionDetails']['isCutscene'] for e in limit_ball_cutscenes(scenario)['interaction']),2)

    def test_goal_and_conceded_goal_share_a_slot_and_non_ball_types_stay_on_field(self):
        entries=[]
        for index,kind in enumerate((10,11,30,31,12,17,13,13,14,14,15,15,21,21),1):
            entries.append({'interactionId':index,'interactionDetails':{'type':kind,'startTick':index,'participants':[],'isCutscene':True}})
        filtered=limit_ball_cutscenes({'interaction':entries})
        self.assertEqual([e['interactionDetails']['type'] for e in filtered['interaction'] if e['interactionDetails']['isCutscene']],[12,13,14,15,21])
