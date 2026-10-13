#!/usr/bin/env python3
"""Build an original-protocol scripted match using only available animated skins."""
from copy import deepcopy
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools.flash_protocol import Codec
from tools.game_config import ROOT, load_config
from tools.movement_adapter import adapt_movement_turn, grid


def build_fixture(engine_turn=None):
    codec = Codec()
    config = load_config()
    defaults = config["rules"]["classes"]["defaults"]
    attributes = {key: defaults[key] for key in ("earth", "fire", "air", "water")}
    attributes.update(maxHitPoints=defaults["health"], hitPointRegenRate=defaults["regeneration"])
    ranking = {"wins": 0, "draws": 0, "defeats": 0}
    # Both ten-player rosters use the supplied male Iop (61.swl), with five
    # active players per side. The end billboard requires roster captains.
    # This fixture tests
    # protocol/presentation, not whether the missing full roster is playable.
    def roster(side):
        return {"characters": [{"id": str(side * 10 + i), "name": f"Mock {'Left' if side == 1 else 'Right'} {i}",
                "attributes": deepcopy(attributes), "boufbowlerClass": 6, "gender": 1,
                "paletteId": 6, "hairColor": {"r": 230, "g": 130, "b": 30},
                "eyeColor": {"r": 30, "g": 50, "b": 80}, "skinColor": {"r": 235, "g": 195, "b": 150}}
                for i in range(1, 11)], "nickname": "Mock player", "name": f"Mock team {side}",
                "firstColor": {"r": 40 if side == 1 else 200, "g": 100, "b": 200 if side == 1 else 40},
                "secondColor": {"r": 230, "g": 230, "b": 230}, "patternColor": {"r": 40, "g": 40, "b": 40},
                "firstColorIsDark": False, "ranking": deepcopy(ranking), "sigilBackground": 1, "sigilCharge": 1}
    positions = {str(side * 10 + i): {"x": -5 if side == 1 else 5, "y": i - 3}
                 for side in (1, 2) for i in range(1, 6)}
    def field(turn, current):
        return {"phaseInfos": {"phase": 2, "remainingTime": config["rules"]["match"]["planning_seconds"] * 1000},
                "boufbowlerPositions": [{"id": identity, "position": position} for identity, position in current.items()],
                "boufballState": {"status": 1, "position": {"x": 0, "y": 0}},
                "teamState": {"boufbowlerStates": [{"id": identity, "status": 1, "currentHitPoints": defaults["health"],
                                                    "remainingClassOrderUses": 1} for identity in current],
                              "turn": turn, "leftSideScore": 0, "rightSideScore": 0, "period": 1}}
    tracks = []
    final_positions = deepcopy(positions)
    for identity, position in positions.items():
        target = deepcopy(position)
        target["x"] += 2 if int(identity) < 20 else -2
        final_positions[identity] = target
        intermediate = {"x": (position["x"] + target["x"]) // 2, "y": position["y"]}
        tracks.append({"boufbowlerId": identity,
                       "order": {"boufbowlerId": identity, "regularOrder": {"elements": [4, 4, 4], "targetCell": target}},
                       "item": [{"type": 1, "movement": {"positions": [position, intermediate, target], "startTick": 0, "endTick": 40}}],
                       "movementTest": {"success": True, "outcome": 3, "difficulty": 0,
                                        "score": {"inherentScore": 10, "finalScore": 10}}})
    payloads = [
        ("MATCH_INFORMATION", {"id": "9007199254740993", "side": 1, "leftRoster": roster(1), "rightRoster": roster(2),
                               "matchStadium": 1, "skipIntro": True}, 0, None),
        ("FIELD_STATE", field(1, positions), 1000, None),
        ("RESOLUTION_SCENARIO", {"boufbowlerTracks": tracks, "interaction": [], "turn": 1, "turnEndTick": 40}, 4000, None),
        ("FIELD_STATE", field(2, final_positions), 1000, "ResolutionDoneMessage"),
        ("MATCH_END", {"id": "9007199254740993", "leftScore": 0, "rightScore": 0,
                       "leftRanking": ranking, "rightRanking": ranking}, 3000, None),
    ]
    if engine_turn is not None:
        if {e["id"] for e in engine_turn["initial"]["entities"]} != {int(identity) for identity in positions}:
            raise ValueError("Engine probe must use the fixture's ten active identities")
        scenario = adapt_movement_turn(engine_turn)
        initial_positions = {str(e["id"]): grid(e["position"]) for e in engine_turn["initial"]["entities"]}
        final_positions = {str(e["entity_id"]): grid(e["position"]) for e in engine_turn["result"]["final_entity_states"]}
        payloads[1] = ("FIELD_STATE", field(1, initial_positions), 1000, None)
        payloads[2] = ("RESOLUTION_SCENARIO", scenario, 4000, None)
        payloads[3] = ("FIELD_STATE", field(2, final_positions), 1000, "ResolutionDoneMessage")
    steps = []
    for name, payload, delay, wait_for in payloads:
        encoded = codec.envelope(name, payload)
        decoded = codec.open_envelope(encoded)
        step = {"channel": "MATCH", "type": name, "after_ms": delay, "hex": encoded.hex(), "decoded": decoded["payload"]}
        if wait_for:
            step["wait_for"] = wait_for
        steps.append(step)
    fixture = {"format_version": 1, "name": "Movement-only scripted match", "rules_version": config["rules_version"],
            "description": "Scripted fixture; orders are predetermined, not simulated. No combat, scores, or account persistence.",
            "steps": steps}
    if engine_turn is not None:
        fixture["name"] = "Replacement-engine movement probe"
        fixture["description"] = "Movement computed by the sibling engine. Scripted lifecycle; provisional stats and movement-test display scores. No interaction support."
        fixture["engine"] = {key: engine_turn["result"][key] for key in ("simulation_version", "seed", "initial_state_hash", "final_state_hash", "tick_duration")}
    return fixture


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine-turn", type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / "resources/mock_match.json")
    args = parser.parse_args()
    output = args.output
    record = json.loads(args.engine_turn.read_text()) if args.engine_turn else None
    output.write_text(json.dumps(build_fixture(record), indent=2) + "\n")
    print("Built", output)
