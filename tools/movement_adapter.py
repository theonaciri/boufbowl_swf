"""First engine-to-Flash adapter: isolated movement turns only.

Unsupported outcomes fail rather than disappearing from the original replay.
"""
from copy import deepcopy
from decimal import Decimal

from tools.flash_protocol import ProtocolError


def grid(position):
    if set(position) != {"q", "r"} or any(not isinstance(x, int) or isinstance(x, bool) for x in position.values()):
        raise ProtocolError("Movement probe requires integral axial positions")
    return {"x": position["q"], "y": position["r"]}


def adapt_movement_turn(record):
    if record.get("format_version") != 1:
        raise ProtocolError("Unsupported engine probe format")
    initial, result = record["initial"], record["result"]
    unsupported = sorted({event["type"] for event in result["events"]} - {"move", "final_state"})
    if unsupported:
        raise ProtocolError(f"Movement adapter cannot present interactions: {unsupported}")
    if result["score"] != [0, 0] or result["final_ball_state"] != initial["ball"]:
        raise ProtocolError("Movement adapter cannot present score or ball-state changes")
    ratio = Decimal(str(result["tick_duration"])) * 1000 / 50
    if ratio <= 0 or ratio != ratio.to_integral_value():
        raise ProtocolError("Engine tick duration must be a positive multiple of 50 ms")
    factor = int(ratio)
    entities = {e["id"]: e for e in initial["entities"]}
    finals = {e["entity_id"]: e for e in result["final_entity_states"]}
    actions = {a["entity_id"]: a for order in record["orders"] for a in order["actions"]}
    if len(entities) != len(initial["entities"]) or set(entities) != set(finals) or set(actions) != set(entities):
        raise ProtocolError("Movement probe identity sets disagree")
    for event in result["events"]:
        if not isinstance(event["tick"], int) or isinstance(event["tick"], bool) or event["tick"] < 0:
            raise ProtocolError("Invalid simulation event tick")
        if event["type"] == "move" and event.get("actor") not in entities:
            raise ProtocolError("Movement sample references an unknown actor")
    tracks = []
    for identity, entity in sorted(entities.items()):
        final = finals[identity]
        if final["hp"] != entity["hp"] or final["status"] != entity["status"]:
            raise ProtocolError("Movement adapter cannot present health/status changes")
        action = actions[identity]
        if action["action_type"] != "move":
            raise ProtocolError("Movement adapter accepts move orders only")
        elements = action["params"]["elements"]
        selected = [value for name, value in (("TERRE", 1), ("AIR", 2), ("FEU", 3), ("EAU", 4))
                    for _ in range(elements[name])]
        if len(selected) != 3:
            raise ProtocolError("Flash regular orders require three selected elements in this probe")
        start = grid(entity["position"])
        current = deepcopy(start)
        last_tick = 0
        items = []
        for event in result["events"]:
            if event["type"] != "move" or event.get("actor") != identity:
                continue
            target = grid(event["params"]["position"])
            if target == current:
                continue
            tick = (event["tick"] + 1) * factor
            if tick <= last_tick:
                raise ProtocolError("Movement samples are not strictly ordered")
            if max(abs(target["x"] - current["x"]), abs(target["y"] - current["y"]),
                   abs(target["x"] - current["x"] + target["y"] - current["y"])) != 1:
                raise ProtocolError("Movement sample skips a hex; explicit path recovery required")
            items.append({"type": 1, "movement": {"positions": [current, target], "startTick": last_tick, "endTick": tick}})
            current = target
            last_tick = tick
        if current != grid(final["position"]):
            raise ProtocolError("Movement samples do not reach the authoritative final cell")
        tracks.append({"boufbowlerId": str(identity), "order": {"boufbowlerId": str(identity),
                       "regularOrder": {"elements": selected, "targetCell": grid(action["params"]["target_position"])}},
                       "item": items, "movementTest": {"success": True, "outcome": 3, "difficulty": 0,
                                                        "score": {"inherentScore": 10, "finalScore": 10}}})
    return {"boufbowlerTracks": tracks, "interaction": [], "turn": result["turn_number"],
            "turnEndTick": (max(event["tick"] for event in result["events"]) + 1) * factor}
