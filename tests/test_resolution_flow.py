from copy import deepcopy
import json
import unittest

from backend.turn_adapter import adapt_turn
from tools.flash_protocol import Codec
from tools.game_config import ROOT


class ResolutionFlowTests(unittest.TestCase):
    def test_uninvolved_runners_move_through_an_interaction_window(self):
        record = json.loads((ROOT/'tests/fixtures/movement_engine_turn.json').read_text())
        events = record['result']['events']
        index = next(i for i, event in enumerate(events) if event['tick'] == 2)
        events.insert(index, dict(tick=1, type='pickup_fail', actor=11, params={}))
        before = deepcopy(record)
        scenario = adapt_turn(record)
        interaction = scenario['interaction'][0]['interactionDetails']
        tracks = {int(t['boufbowlerId']): t for t in scenario['boufbowlerTracks']}
        runner = tracks[22]['item']
        moving = [item['movement'] for item in runner if len(item['movement']['positions']) > 1]
        self.assertTrue(any(m['startTick'] <= interaction['startTick'] and m['endTick'] >= interaction['endTick']
                            for m in moving))
        self.assertEqual([item['type'] for item in runner].count(2), 0)
        for track in tracks.values():
            previous = 0
            for item in track['item']:
                self.assertEqual(item['movement']['startTick'], previous)
                previous = item['movement']['endTick']
            final = next(e for e in record['result']['final_entity_states'] if str(e['entity_id']) == track['boufbowlerId'])
            self.assertEqual(track['item'][-1]['movement']['positions'][-1],
                             dict(x=final['position']['q'], y=final['position']['r']))
        self.assertEqual(record, before)
        Codec().encode('ResolutionScenarioMessage', scenario)

    def test_failed_catches_show_misses_and_keep_the_eventual_ball_link(self):
        record = json.loads((ROOT/'tests/fixtures/interactions/rebound-record.json').read_text())
        before = deepcopy(record)
        scenario = adapt_turn(record)
        attempts = [e for e in record['result']['events'] if e['type'] == 'catch_fail']
        misses = [i['interactionDetails'] for i in scenario['interaction']
                  if i['interactionDetails']['type'] in (14, 15)]
        self.assertGreater(len(attempts), 0)
        self.assertEqual(len(misses), len(attempts))
        self.assertTrue(all(not m['maneuverTest']['success'] and not m['isCutscene']
                            and not m['participants'][0]['hasBall'] for m in misses))
        passed = next(i['interactionDetails'] for i in scenario['interaction'] if i['interactionDetails']['type'] == 21)
        landing = next(i for i in scenario['interaction'] if i['interactionDetails']['type'] == 13)
        self.assertEqual(passed['passDetails']['nextInteractionId'], landing['interactionId'])
        self.assertTrue(all(a['interactionDetails']['endTick'] <= b['interactionDetails']['startTick']
                            for a, b in zip(scenario['interaction'], scenario['interaction'][1:])))
        self.assertEqual(record, before)
        Codec().encode('ResolutionScenarioMessage', scenario)
