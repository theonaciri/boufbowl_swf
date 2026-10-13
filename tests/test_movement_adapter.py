from copy import deepcopy
import json
from pathlib import Path
import unittest

from tools.flash_protocol import Codec, ProtocolError
from tools.movement_adapter import adapt_movement_turn


class MovementAdapterTests(unittest.TestCase):
    def setUp(self):
        self.record = json.loads((Path(__file__).parent / "fixtures/movement_engine_turn.json").read_text())

    def test_engine_cells_and_tick_conversion_reach_authoritative_state(self):
        before = deepcopy(self.record)
        scenario = adapt_movement_turn(self.record)
        final = {str(e["entity_id"]): e["position"] for e in self.record["result"]["final_entity_states"]}
        for track in scenario["boufbowlerTracks"]:
            target = final[track["boufbowlerId"]]
            self.assertEqual(track["item"][-1]["movement"]["positions"][-1], {"x": target["q"], "y": target["r"]})
        self.assertEqual(scenario["turnEndTick"], 10)  # Five 100 ms engine ticks -> ten 50 ms display ticks.
        codec = Codec()
        self.assertEqual(codec.open_envelope(codec.envelope("RESOLUTION_SCENARIO", scenario))["payload"]["turn"], 1)
        self.assertEqual(self.record, before)

    def test_combat_events_are_rejected_instead_of_dropped(self):
        self.record["result"]["events"].append({"tick": 4, "type": "duel", "actor": 11, "params": {}})
        with self.assertRaisesRegex(ProtocolError, "cannot present interactions"):
            adapt_movement_turn(self.record)

    def test_ball_and_health_changes_require_a_richer_adapter(self):
        self.record["result"]["final_ball_state"]["holder_entity_id"] = 11
        with self.assertRaisesRegex(ProtocolError, "ball-state"):
            adapt_movement_turn(self.record)
        self.setUp()
        self.record["result"]["final_entity_states"][0]["hp"] -= 1
        with self.assertRaisesRegex(ProtocolError, "health/status"):
            adapt_movement_turn(self.record)

    def test_unrepresentable_ticks_and_inconsistent_final_cells_fail(self):
        self.record["result"]["tick_duration"] = 0.075
        with self.assertRaisesRegex(ProtocolError, "50 ms"):
            adapt_movement_turn(self.record)
        self.setUp()
        self.record["result"]["final_entity_states"][0]["position"]["q"] += 1
        with self.assertRaisesRegex(ProtocolError, "authoritative final cell"):
            adapt_movement_turn(self.record)

    def test_unknown_actor_is_rejected_instead_of_dropped(self):
        self.record["result"]["events"][0]["actor"] = 999
        with self.assertRaisesRegex(ProtocolError, "unknown actor"):
            adapt_movement_turn(self.record)


if __name__ == "__main__":
    unittest.main()
