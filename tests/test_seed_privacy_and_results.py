from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from backend.replay import export_replay
from backend.service import Service
from backend.storage import ServiceError
from tests.test_backend import initial_club
from tools.game_config import load_config


class SeedAndResultTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory();self.path=Path(self.directory.name)/'state.sqlite'
        self.config=load_config();self.config["general"]["tournament"].update(start_time=0,end_time=4102444800,repeat_seconds=0,stadium_rotation=[1],format='league');self.config['general']['cinematics']['introductions']=False
        self.config['rules']['match'].update(turns_per_match=2,turns_per_period=2)
        self.service=Service(self.path,self.config)
        self.alice=self.service.hello({'nickname':'Alice','clubs':[initial_club()]})
        self.bob=self.service.hello({'nickname':'Bob','clubs':[initial_club()]})
        self.seq=0

    def tearDown(self):
        self.service.close();self.directory.cleanup()

    def pid(self,player):return self.service.store.authenticate(player['session'])

    def command(self,player,operation,**body):
        self.seq+=1
        return self.service.command(dict(session=player['session'],request_id=str(self.seq),operation=operation,**body))

    def protocol(self,player,name,payload):
        return self.command(player,'protocol',hex=self.service.codec.envelope(name,payload).hex())

    def start(self,kind='practice'):
        if kind=='practice':self.command(self.alice,'cpu_match',stadium=1,mode='ranked',source='matchmaking')
        elif kind=='casual':
            self.command(self.alice,'challenge',nickname='Bob',stadium=1,mode='ranked',source='matchmaking')
            offer=self.service.store.db.execute('SELECT MAX(id) FROM challenges').fetchone()[0]
            self.protocol(self.bob,'CHALLENGE_ANSWER',{'offerId':offer,'answer':2})
        else:
            for player in (self.alice,self.bob):
                self.command(player,'tournament_match',tournament_id=1) if kind=='tournament' else self.command(player,'queue_join')
        return self.service.store.active_match(self.pid(self.alice))

    def finish(self,match,score):
        with self.service.store.transaction():
            match['score']=score
            self.service.end_match(match)
            # Both end-match retries and duplicate reward delivery remain harmless.
            self.service.end_match(match)
            self.service.store.reward(match,1)

    def ready(self,match):
        with self.service.store.transaction():
            self.service.finish_placement(match);self.service.store.save_match(match)

    def assert_private(self,export):
        self.assertFalse(export['completed']);self.assertFalse(export['audit_available'])
        self.assertFalse(export['verified']);self.assertEqual(export['records'],[])
        def walk(value):
            if isinstance(value,dict):
                self.assertFalse(set(value)&{'seed','turn_seeds','initial_state_hash','final_state_hash','random_draw','final_world_state'})
                for child in value.values():walk(child)
            elif isinstance(value,list):
                for child in value:walk(child)
        walk(export)
        for step in export['steps']:
            decoded=self.service.codec.open_envelope(bytes.fromhex(step['hex']))
            self.assertEqual(self.service.codec.envelope(step['type'],decoded['payload']).hex(),step['hex'])
            walk(decoded)

    def test_live_exports_redact_audits_for_players_and_spectators_then_unlock_on_finish(self):
        match=self.start();self.ready(match)
        self.protocol(self.bob,'MATCH_SPECTATE_REQUEST',{'playerNickname':'Alice'})
        self.protocol(self.alice,'ORDERS',{'turn':1,'orders':[]})
        for player in (self.alice,self.bob):
            self.assert_private(export_replay(self.service,match['id'],False,self.pid(player)))
            with self.assertRaises(ServiceError) as error:
                export_replay(self.service,match['id'],True,self.pid(player))
            self.assertEqual(error.exception.code,'REPLAY_ACTIVE')
        record=json.loads(self.service.store.db.execute('SELECT record_json FROM turns').fetchone()[0])
        self.finish(self.service.store.match(match['id']),[1,0])
        for player in (self.alice,self.bob):
            replay=export_replay(self.service,match['id'],True,self.pid(player))
            self.assertTrue(replay['audit_available']);self.assertTrue(replay['verified'])
            self.assertEqual(replay['records'][0]['result'],record['result'])

    def test_new_and_unfinished_legacy_matches_use_independent_persisted_turn_seeds(self):
        match=self.start();self.assertNotIn('seed',match);self.ready(match)
        # Model an old match whose shared seed was previously disclosed.
        match['seed']=12345;match.pop('turn_seeds',None);match.pop('seed_policy',None)
        with self.service.store.transaction():self.service.store.save_match(match)
        selected=[0x1a2b3c4d,0x5e6f7890]
        with patch('backend.service.secrets.randbits',side_effect=selected) as draw:
            for turn in (1,2):
                self.protocol(self.alice,'ORDERS',{'turn':turn,'orders':[]})
                active=self.service.store.active_match(self.pid(self.alice))
                self.assertEqual(active['turn_seeds'][str(turn)],selected[turn-1])
                self.assertEqual(active['seed_policy'],'independent-turn-v1')
                self.protocol(self.alice,'RESOLUTION_DONE',{'turn':turn})
            self.assertEqual(draw.call_count,2)
        replay=export_replay(self.service,match['id'],True,self.pid(self.alice))
        self.assertEqual([record['result']['seed'] for record in replay['records']],selected)

    def test_unsubmitted_opponent_orders_never_appear_in_live_export(self):
        match=self.start('ranked');self.ready(match)
        for player in (self.alice,self.bob):self.protocol(player,'ORDERS',{'turn':1,'orders':[]})
        for player in (self.alice,self.bob):self.protocol(player,'RESOLUTION_DONE',{'turn':1})
        active=self.service.store.active_match(self.pid(self.alice))
        identity=str(next(e['id'] for e in active['world']['entities'] if e['team_id']==0))
        pending={'boufbowlerId':identity,'regularOrder':{'elements':[1,1,1]}}
        self.protocol(self.alice,'ORDERS',{'turn':2,'orders':[pending]})
        export=export_replay(self.service,match['id'],False,self.pid(self.bob))
        self.assert_private(export)
        scenarios=[s['decoded'] for s in export['steps'] if s['type']=='RESOLUTION_SCENARIO']
        self.assertEqual([s['turn'] for s in scenarios],[1])
        self.assertEqual(self.service.store.active_match(self.pid(self.alice))['orders']['1']['turn_number'],2)

    def test_replay_chapters_select_pre_turn_snapshots_and_restore_masks(self):
        self.service.config['rules']['match']['turns_per_period']=1
        match=self.start();self.ready(match)
        for turn in (1,2):
            active=self.service.store.active_match(self.pid(self.alice))
            if active['phase']=='placement':self.ready(active)
            self.protocol(self.alice,'ORDERS',{'turn':turn,'orders':[]})
            self.protocol(self.alice,'RESOLUTION_DONE',{'turn':turn})
        row=self.service.store.db.execute('SELECT record_json FROM turns WHERE turn=2').fetchone()
        record=json.loads(row[0]);entity=record['initial']['entities'][0];entity['zobal_mask']=2
        self.service.store.db.execute('UPDATE turns SET record_json=? WHERE turn=2',(json.dumps(record),))
        replay=export_replay(self.service,match['id'],profile=self.pid(self.alice))
        self.assertEqual([c['turn'] for c in replay['chapters']],[1,2])
        self.assertEqual([c['period'] for c in replay['chapters']],[1,2])
        self.assertEqual(replay['chapters'][1]['zobal_masks'],{str(entity['id']):2})
        for chapter in replay['chapters']:
            index=chapter['field_step']
            self.assertEqual(replay['steps'][index]['type'],'FIELD_STATE')
            self.assertEqual(replay['steps'][index]['decoded']['teamState']['turn'],chapter['turn'])
            self.assertEqual(replay['steps'][index+1]['type'],'RESOLUTION_SCENARIO')

    def test_cpu_and_challenges_keep_history_without_changing_ranked_counters(self):
        for kind in ('practice','casual'):
            match=self.start(kind);self.assertEqual(match['mode'],kind)
            self.finish(match,[1,0])
            stats=self.service.store.profile(self.pid(self.alice))['statistics']
            self.assertEqual(stats['rating'],1000);self.assertEqual(stats['wins'],0)
            self.assertEqual(stats[kind]['wins'],1)
            self.assertEqual(self.service.history(self.pid(self.alice))['matches'][0]['result_kind'],kind)
        bob=self.service.store.profile(self.pid(self.bob))['statistics']
        self.assertEqual(bob['rating'],1000);self.assertEqual(bob['casual']['defeats'],1)

    def test_only_human_queue_wins_losses_and_draws_change_ranked_statistics(self):
        match=self.start('ranked');self.assertEqual(match['source'],'matchmaking')
        self.finish(match,[1,0])
        for player,rating,outcome in ((self.alice,1020,'wins'),(self.bob,980,'defeats')):
            stats=self.service.store.profile(self.pid(player))['statistics']
            self.assertEqual(stats['rating'],rating);self.assertEqual(stats[outcome],1)
        self.finish(self.start('ranked'),[0,0])
        self.assertEqual(self.service.store.profile(self.pid(self.alice))['statistics']['rating'],1020)
        self.assertEqual(self.service.store.profile(self.pid(self.alice))['statistics']['draws'],1)

    def test_tournament_points_require_ranked_tournament_queue_provenance(self):
        for kind in ('practice','casual','ranked'):
            match=self.start(kind);match['tournament']=1;self.finish(match,[1,0])
        self.assertEqual(self.service.tournament_entries(self.config['general']['tournament']),[])
        match=self.start('tournament');self.assertEqual(match['mode'],'ranked')
        self.finish(match,[1,0])
        entries=dict(self.service.tournament_entries(self.config['general']['tournament']))
        self.assertEqual(entries[self.pid(self.alice)]['tournamentPoints'],3)

    def test_outdated_development_database_is_reset_without_archive(self):
        self.finish(self.start('practice'),[1,0])
        with self.service.store.transaction():
            self.service.store.db.execute('DELETE FROM schema_versions')
            self.service.store.db.execute('INSERT INTO schema_versions VALUES(5)')
        self.service.close();self.service=Service(self.path,self.config)
        for table in ('profiles','accounts','matches','turns','match_results','participants','commands','events'):
            self.assertEqual(self.service.store.db.execute('SELECT COUNT(*) FROM '+table).fetchone()[0],0)
        self.alice=self.service.hello({'nickname':'Alice','clubs':[initial_club()]})
        self.bob=self.service.hello({'nickname':'Bob','clubs':[initial_club()]})
        self.finish(self.start('ranked'),[1,0])
        stats=self.service.store.profile(self.pid(self.alice))['statistics']
        self.assertNotIn('legacy_statistics',stats)
        self.assertEqual(stats['rating'],1020)
        self.service.close();self.service=Service(self.path,self.config)
        self.assertEqual(stats,self.service.store.profile(self.pid(self.alice))['statistics'])

    def test_unversioned_development_database_is_reset(self):
        self.finish(self.start('practice'),[1,0])
        self.service.store.db.execute('DROP TABLE schema_versions')
        self.service.close();self.service=Service(self.path,self.config)
        self.assertEqual(self.service.store.db.execute('SELECT COUNT(*) FROM matches').fetchone()[0],0)
        self.assertEqual(self.service.store.db.execute('SELECT COUNT(*) FROM profiles').fetchone()[0],0)
        self.assertEqual(self.service.store.db.execute('SELECT MAX(version) FROM schema_versions').fetchone()[0],8)
