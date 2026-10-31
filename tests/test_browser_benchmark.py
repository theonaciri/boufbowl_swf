"""Protocol benchmark fixture is isolated, deterministic and never uses real accounts."""
import unittest
from tools.flash_protocol import Codec
from tools.browser_benchmark import create_fixture

class FixtureTests(unittest.TestCase):
    def test_protocol_roundtrip_and_ten_actors(self):
        fixture=create_fixture()
        for step in fixture['steps']:
            self.assertEqual(Codec().open_envelope(bytes.fromhex(step['hex']))['payload'],step['decoded'])
        tracks=fixture['steps'][2]['decoded']['boufbowlerTracks']
        self.assertEqual(len(tracks),10)
        self.assertEqual(len({t['boufbowlerId'] for t in tracks}),10)
        self.assertEqual(fixture,create_fixture())
        self.assertEqual(fixture['steps'][2]['after_ms'],3600000)
        self.assertEqual(fixture['steps'][2]['decoded']['turnEndTick'],800)
        self.assertEqual(fixture['steps'][3]['wait_for'],'ResolutionDoneMessage')
        for track in tracks:
            route=track['item'][0]['movement']
            self.assertEqual(route['positions'][0],route['positions'][-1])
            self.assertEqual(route['endTick'],800)
        self.assertEqual(fixture['steps'][1]['decoded']['boufbowlerPositions'],fixture['steps'][3]['decoded']['boufbowlerPositions'])

if __name__=='__main__': unittest.main()
