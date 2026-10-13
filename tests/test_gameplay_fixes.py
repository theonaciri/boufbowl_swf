from copy import deepcopy
import json
from pathlib import Path
import unittest

from backend.engine import Engine
from backend.placement import placement_zones
from tools.game_config import ROOT, load_config


class GameplayFixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = Engine()
        cls.rules = load_config()['rules']
        cls.baseline = json.loads((ROOT/'tests/fixtures/movement_engine_turn.json').read_text())['initial']

    @classmethod
    def tearDownClass(cls):
        cls.engine.close()

    def simulate(self, world, actions=None, rules=None):
        orders = [{'player_id':str(t),'turn_number':1,'team_index':t,'nonce':'probe',
                   'actions':(actions or []) if t == 0 else []} for t in (0,1)]
        return self.engine.simulate(world, orders, 1, 12345, rules or self.rules, (False,False))['result']

    def test_air_enables_reception_and_feu_alone_does_not(self):
        record = json.loads((ROOT/'tests/fixtures/interactions/reception-record.json').read_text())
        # Force probabilities to isolate eligibility from the random catch draw.
        rules = deepcopy(self.rules)
        rules['simulation']['simulation'].update(probability_min=1, probability_max=1)
        for air in (0,1):
            with self.subTest(air=air):
                actions = deepcopy(record['orders'][0]['actions'])
                receiver = next(a for a in actions if a['entity_id']==12)
                receiver['params']['elements'] = {'TERRE':0,'FEU':3-air,'AIR':air,'EAU':0}
                result = self.simulate(deepcopy(record['initial']), actions, rules)
                catches = [e for e in result['events'] if e['type']=='catch' and e['actor']==12]
                self.assertEqual(bool(catches), bool(air))

    def test_air_reception_can_still_fail_probability(self):
        record = json.loads((ROOT/'tests/fixtures/interactions/rebound-record.json').read_text())
        result = self.simulate(record['initial'], record['orders'][0]['actions'], record['rules'])
        self.assertIn('catch_fail', [e['type'] for e in result['events']])
        self.assertNotIn('catch', [e['type'] for e in result['events']])

    def test_goals_use_vertical_line_both_sides_and_halftime(self):
        for team in (0,1):
            for swapped in (False,True):
                for row in (-3,-2,2,3):
                    right = (team == 0) != swapped
                    for past in (False,True):
                        # Logical x is q+r/2; choose either side of 12.5 on each row.
                        q = (13 if past else 12) - row//2
                        if not right: q = -q-row
                        with self.subTest(team=team,swapped=swapped,row=row,past=past):
                            world = deepcopy(self.baseline)
                            actor = next(e for e in world['entities'] if e['team_id']==team)
                            actor['position'] = {'q':q,'r':row}
                            world['sides_swapped'] = swapped
                            world['ball'].update(holder_entity_id=actor['id'],position=deepcopy(actor['position']))
                            actor['status']['carrying_ball']=True
                            events = self.simulate(world)['events']
                            goals = [e for e in events if e['type']=='goal']
                            # On odd rows q+row/2 equals 12.5 for the nearer sample.
                            expected = abs(q+row/2) >= 12.5
                            self.assertEqual(bool(goals),expected)
                            if goals: self.assertEqual(goals[0]['params']['team'],team)

    def test_crossing_without_ball_or_crossing_own_line_does_not_score(self):
        world = deepcopy(self.baseline)
        actor = world['entities'][0]; actor['position']={'q':13,'r':0}
        self.assertNotIn('goal',[e['type'] for e in self.simulate(world)['events']])
        actor['position']={'q':-13,'r':0}
        world['ball'].update(holder_entity_id=actor['id'],position=deepcopy(actor['position']))
        actor['status']['carrying_ball']=True
        self.assertNotIn('goal',[e['type'] for e in self.simulate(world)['events']])

    def test_cpu_receivers_assign_air(self):
        record = json.loads((ROOT/'tests/fixtures/interactions/reception-record.json').read_text())
        response = self.engine.simulate(record['initial'], [None, None], 1, 12345, self.rules, (True, False))
        actions = response['orders'][0]['actions']
        throw = next(a for a in actions if a['action_type']=='throw')
        receiver = next(a for a in actions if a['entity_id']==throw['params']['target_entity_id'])
        self.assertGreaterEqual(receiver['params']['elements']['AIR'],1)

    def test_goal_line_configuration_changes_scoring(self):
        world = deepcopy(self.baseline)
        actor=world['entities'][0]; actor['position']={'q':11,'r':0}
        world['ball'].update(holder_entity_id=actor['id'],position=deepcopy(actor['position']))
        actor['status']['carrying_ball']=True
        self.assertNotIn('goal',[e['type'] for e in self.simulate(world)['events']])
        rules=deepcopy(self.rules);rules['simulation']['ball']['goal_line_half_width']=10
        self.assertIn('goal',[e['type'] for e in self.simulate(world,rules=rules)['events']])

    def test_placement_matches_reference_and_reflects_without_rotating(self):
        right = placement_zones(2)
        left = placement_zones(1)
        all_cells = set()
        for rz,lz in zip(right,left):
            self.assertIn(rz['defaultCell'],rz['cell'])
            cells={(c['x'],c['y']) for c in rz['cell']}
            self.assertFalse(cells & all_cells); all_cells |= cells
            self.assertEqual({(-x-y,y) for x,y in cells}, {(c['x'],c['y']) for c in lz['cell']})
        self.assertEqual(len(right[1]['cell']),48)
        self.assertEqual(len(right[3]['cell']),40)
        self.assertEqual(placement_zones(1,2),right)
        self.assertEqual(placement_zones(2,2),left)
        self.assertTrue(all(c['y']>0 for c in right[1]['cell']))
        self.assertTrue(all(c['y']<0 for c in right[4]['cell']))
