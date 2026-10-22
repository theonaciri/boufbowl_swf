from copy import deepcopy
import json
from pathlib import Path
import unittest

from backend.game_measurements import record_turn
from backend.service import Service
from tests import test_backend as helpers
from tests import test_tracking as tracking_helpers


class GameMeasurementsTests(unittest.TestCase):
    setUp = helpers.BackendTests.setUp
    tearDown = helpers.BackendTests.tearDown
    identity = helpers.BackendTests.identity
    command = helpers.BackendTests.command
    protocol = helpers.BackendTests.protocol
    start = helpers.BackendTests.start
    admin = tracking_helpers.TrackingTests.admin

    def event(self, identity='frames-1', **fields):
        return dict(id=identity,kind='game_frames',phase='3d',frames=30,elapsed_ms=1000,
                    slow_frames=2,target_fps=30,max_frame_ms=100,memory_mb=64,
                    histogram=[0,0,0,28,0,0,2,0,0,0],**fields)

    def send(self, events):
        return self.service.telemetry(dict(session=self.alice['session'],client_id='measurement-test',
            client={'runtime':'ruffle','platform':'browser'},events=events))

    def test_authenticated_aggregates_are_idempotent_weighted_and_durable(self):
        event = self.event()
        self.assertEqual(self.send([event])['accepted'],1)
        self.assertEqual(self.send([event])['duplicates'],1)
        second = {**self.event('frames-2'),'frames':60,'elapsed_ms':3000,'histogram':[0,0,0,58,0,0,2,0,0,0]}
        self.send([second])
        report = self.service.metrics(self.admin())['game']
        row = report['frames'][0]
        self.assertEqual(row['samples'],2)
        self.assertEqual(row['fps'],22.5)
        self.assertEqual(row['p95_frame_ms'],34)
        self.assertAlmostEqual(row['slow_percent'],400/90)
        self.service.close();self.service=Service(self.path,self.config)
        self.assertEqual(self.service.metrics(self.admin())['game']['frames'][0]['frames'],90)

    def test_invalid_samples_are_rejected_before_any_receipt_or_aggregate(self):
        invalid = [dict(frames=True),dict(elapsed_ms=float('nan')),dict(phase='anything'),
                   dict(histogram=[30]),dict(slow_frames=31),dict(target_fps=999),dict(memory_mb=float('inf'))]
        for fields in invalid:
            with self.subTest(fields=fields), self.assertRaises(ValueError):
                self.send([{**self.event(),**fields}])
        self.assertEqual(self.service.store.db.execute('SELECT COUNT(*) FROM game_frame_measurements').fetchone()[0],0)
        self.assertEqual(self.service.store.db.execute('SELECT COUNT(*) FROM tracking_receipts').fetchone()[0],0)

    def test_authoritative_turn_counters_distinguish_passes_interceptions_and_risk(self):
        record = json.loads(Path('tests/fixtures/interactions/reception-record.json').read_text())
        before = deepcopy(record)
        events = record['result']['events']
        catcher = next(event for event in events if event['type']=='catch')['actor']
        thrower = next(event for event in events if event['type']=='throw')['actor']
        team = next(entity['team_id'] for entity in record['initial']['entities'] if entity['id']==thrower)
        events += [dict(type='movement_test',actor=thrower,params={'probability':.2}),dict(type='fall',actor=thrower)]
        snapshot = deepcopy(record)
        with self.service.store.transaction():
            record_turn(self.service.store.db,'test-match',1,record,['human',None])
            record_turn(self.service.store.db,'test-match',1,record,['human',None])
        self.assertEqual(record,snapshot)
        rows = self.service.metrics(self.admin())['game']['gameplay']
        sender = next(row for row in rows if row['controller']==('human' if team==0 else 'cpu'))
        self.assertEqual((sender['passes'],sender['completed_passes'],sender['risk_tests'],sender['falls']),(1,1,1,1))
        self.assertEqual(sum(row['team_turns'] for row in rows),2)
        record = before
        for entity in record['initial']['entities']:
            if entity['id']==catcher: entity['team_id']=1-team
        with self.service.store.transaction():
            record_turn(self.service.store.db,'intercepted',1,record,['human',None])
        rows = self.service.metrics(self.admin())['game']['gameplay']
        self.assertEqual(sum(row['interceptions'] for row in rows),1)

    def test_recording_rolls_back_with_the_game_transaction(self):
        record=json.loads(Path('tests/fixtures/interactions/rebound-record.json').read_text())
        with self.assertRaises(RuntimeError):
            with self.service.store.transaction():
                record_turn(self.service.store.db,'rollback',1,record,['human',None])
                raise RuntimeError('failed game transaction')
        self.assertEqual(self.service.store.db.execute('SELECT COUNT(*) FROM game_turn_measurements').fetchone()[0],0)

    def test_resolving_a_real_cpu_turn_records_both_teams(self):
        match = self.start()
        self.protocol(self.alice,'ORDERS',{'turn':1,'orders':[]})
        rows = self.service.store.db.execute('SELECT controller FROM game_turn_measurements WHERE match_id=?',(match['id'],)).fetchall()
        self.assertEqual(sorted(row['controller'] for row in rows),['cpu','human'])
        self.assertEqual(self.service.store.db.execute('SELECT COUNT(*) FROM turns WHERE match_id=?',(match['id'],)).fetchone()[0],1)
