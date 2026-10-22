"""Translate authoritative engine outcomes into the original resolution contract.

Presentation ticks reserve time for original interaction animations. Only their
participants stop; other runners spread their next step across that time.
Authority, probability draws and final states remain in the recorded result.
"""
from copy import deepcopy
import math

from tools.flash_protocol import ProtocolError


def cell(position):
    q, r = position["q"], position["r"]
    if not all(isinstance(v, (int, float)) and math.isfinite(v) for v in (q, r)):
        raise ProtocolError("Invalid axial position")
    x, y, z = round(q), round(r), round(-q - r)
    differences = abs(x - q), abs(y - r), abs(z + q + r)
    if differences[0] > differences[1] and differences[0] > differences[2]:
        x = -y - z
    elif differences[1] > differences[2]:
        y = -x - z
    return {"x": int(x), "y": int(y)}


def distance(a, b):
    x, y = a["x"] - b["x"], a["y"] - b["y"]
    return max(abs(x), abs(y), abs(x + y))


def path(a, b):
    current, result = deepcopy(a), [deepcopy(a)]
    for _ in range(100):
        if current == b:
            return result
        choices = [{"x": current["x"] + x, "y": current["y"] + y}
                   for x, y in ((1, 0), (0, 1), (-1, 1), (-1, 0), (0, -1), (1, -1))]
        current = min(choices, key=lambda c: distance(c, b))
        result.append(current)
    raise ProtocolError("Movement path exceeds pitch limits")


def maneuver(success=True, score=10):
    return {"success": bool(success), "outcome": 3, "difficulty": 0,
            "score": {"inherentScore": int(score), "finalScore": int(score)}}


def limit_ball_cutscenes(scenario):
    """Only the first eligible ball action of each type may use a fullscreen sequence.

    Keep disabled flags disabled and leave track timing, interaction links and
    simulation data untouched. Off-ball fights do not consume the fight slot.
    """
    scenario = deepcopy(scenario)
    shown = set()
    entries = sorted(scenario['interaction'], key=lambda entry: (
        entry['interactionDetails']['startTick'], entry['interactionId']))
    for entry in entries:
        details = entry['interactionDetails']
        kind = details['type']
        ball_action = kind in (12, 13, 14, 15, 17, 21) or (
            kind == 20 and any(p.get('hasBall', False) for p in details['participants']))
        category = 12 if kind == 17 else kind
        enabled = bool(details.get('isCutscene') and ball_action and category not in shown)
        details['isCutscene'] = enabled
        if enabled:
            shown.add(category)
    return scenario


def adapt_turn(record):
    initial, result = record["initial"], record["result"]
    events = result["events"]
    allowed = {"ability", "move", "stand_up", "pickup", "pickup_fail", "dodge", "duel", "damage", "ko", "ball_drop",
               "throw", "ball_move", "catch", "catch_fail", "ball_land", "goal", "final_state", "fall", "movement_test"}
    unknown = {e["type"] for e in events} - allowed
    if unknown:
        raise ProtocolError(f"Unmapped simulation events: {sorted(unknown)}")
    entities = {e["id"]: deepcopy(e) for e in initial["entities"] if e["hp"] > 0}
    actions = {}
    for order in record["orders"]:
        for action in order["actions"]:
            actions.setdefault(action["entity_id"], []).append(action)
    tracks = {}
    clocks = {identity: 0 for identity in entities}
    positions = {identity: cell(e["position"]) for identity, e in entities.items()}
    for identity, entity in entities.items():
        actor_actions = actions.get(identity, [])
        activated = any(a["action_type"] == "ability" for a in actor_actions)
        order = {"boufbowlerId": str(identity)}
        if activated:
            order["classOrder"] = True
            mask = next((a["params"].get("zobal_mask") for a in actor_actions if a["action_type"] == "ability"), None)
            if mask is not None: order["zobalMask"] = mask
        else:
            allocation = next((a["params"].get("elements") for a in actor_actions if a["params"].get("elements")), {})
            selected = [value for name, value in (("TERRE", 1), ("AIR", 2), ("FEU", 3), ("EAU", 4))
                        for _ in range(allocation.get(name, 0))]
            regular = {"elements": selected, "targetCell": cell(entity["position"])}
            for action in actor_actions:
                if action["action_type"] == "move":
                    regular["targetCell"] = cell(action["params"]["target_position"])
                elif action["action_type"] == "follow":
                    regular["targetBoufbowler"] = str(action["params"]["target_entity_id"])
                elif action["action_type"] == "throw" and action["params"].get("target_entity_id") is not None:
                    regular["passTargetId"] = str(action["params"]["target_entity_id"])
            order["regularOrder"] = regular
        tracks[identity] = {"boufbowlerId": str(identity), "order": order, "item": [], "movementTest": maneuver()}
    interactions, abilities, pending_passes = [], [], []
    holder = initial["ball"]["holder_entity_id"]
    ball_position = cell(initial["ball"]["position"])
    offset = 1
    factor = result["tick_duration"] * 1000 / 50

    def move(identity, end, target=None):
        if identity not in tracks:
            raise ProtocolError("Scenario references an unavailable actor")
        target = deepcopy(target if target is not None else positions[identity])
        if end <= clocks[identity]:
            return
        tracks[identity]["item"].append({"type": 1, "movement": {"positions": path(positions[identity], target),
                                                                "startTick": clocks[identity], "endTick": end}})
        positions[identity] = target
        clocks[identity] = end

    def participant(identity, role=1, has_ball=None, damage=0, status=None):
        entity = entities[identity]
        return {"boufbowlerId": str(identity), "role": role, "hasBall": holder == identity if has_ball is None else has_ball,
                "status": status if status is not None else 4 if entity["hp"] <= 0 else 3 if entity["status"]["knocked_down"] else 1,
                "damageTaken": max(0, int(damage))}

    def interaction(kind, start, duration, participants, **details):
        nonlocal offset
        start = max(start, max(clocks.values(), default=0))
        end = start + duration
        identity = len(interactions) + 1
        for actor_data in participants:
            actor = int(actor_data["boufbowlerId"])
            move(actor, start)
            tracks[actor]["item"].append({"type": 2, "interactionId": identity,
                                         "movement": {"positions": [deepcopy(positions[actor])], "startTick": start, "endTick": end}})
            clocks[actor] = end
        entry = {"interactionId": identity, "interactionDetails": {"type": kind, "startTick": start, "endTick": end,
                 "isCutscene": bool(record.get("presentation",{}).get("interactions",False) and kind in (12,13,14,15,20,21)), "participants": participants, **details}}
        interactions.append(entry)
        offset += duration
        return entry

    for index, event in enumerate(events):
        kind, tick, actor, params = event["type"], event["tick"], event.get("actor"), event["params"]
        start = max(1, round(tick * factor) + offset)
        if kind == "move":
            target = cell(params["position"])
            if actor in tracks and target != positions[actor]:
                move(actor, max(start + max(1, round(factor)), clocks[actor] + 1), target)
        elif kind == "ability":
            targets = []
            for target in params["targets"]:
                if target not in tracks:
                    continue
                entity = entities[target]
                delta = params.get("hp_deltas", {}).get(str(target), params.get("hp_deltas", {}).get(target))
                healed = max(0, min(entity["max_hp"], entity["hp"] + (int(delta) if delta is not None else int(params.get("heal", 0)))))
                hp_delta = healed - entity["hp"]
                display = [hp_delta] if hp_delta else []
                target_data = {"boufbowlerId": str(target)}
                if hp_delta: target_data['preResolutionHitPointsDelta'] = hp_delta
                targets.append(target_data)
                entity["hp"] = healed
                for element, amount in params.get("elements", {}).items():
                    stat = {"TERRE": "strength", "FEU": "agility", "AIR": "precision", "EAU": "endurance"}[element]
                    before = entity["stats"][stat]
                    entity["stats"][stat] = max(0, before + amount)
                    if entity["stats"][stat] != before: display.append(entity["stats"][stat] - before)
                entity["attack_bonus"] = entity.get("attack_bonus", 0) + params.get("attack", 0)
                display.extend(params[key] for key in ('range','attack') if params.get(key))
                if not params.get('elements') and params.get('element') and params.get('bonus'):
                    display.append(params['bonus'])
                if display: target_data['effectDeltas'] = list(dict.fromkeys(display))
            ability = {"boufbowlerId": str(actor), "target": targets}
            if "zobal_mask" in params: ability["zobalMask"] = params["zobal_mask"]
            abilities.append(ability)
        elif kind == "movement_test":
            if actor in tracks:
                test = maneuver(params['success'], params.get('inherent_score', 0))
                test['difficulty'] = round(params['probability'] * 100)
                test['score']['finalScore'] = round(params['random_draw'] * 100) if params['random_draw'] is not None else 100
                tracks[actor]['movementTest'] = test
        elif kind == "fall":
            move(actor,max(start,clocks[actor]+1),cell(params['position']))
            details = {'ballDispersion':cell(params['position'])} if params.get('has_ball') else {}
            interaction(10,start,24,[participant(actor,has_ball=params.get('has_ball',False),status=3)],fallDetails=details)
            entities[actor]['status']['knocked_down'] = True
            if params.get('has_ball'):
                holder = None
                ball_position = cell(params['position'])
        elif kind == "stand_up":
            entities[actor]["status"]["knocked_down"] = False
        elif kind in ("pickup", "pickup_fail"):
            interaction(11, start, 14, [participant(actor, has_ball=False)], maneuverTest=maneuver(kind == "pickup"),
                        pickupDetails={"ballPosition": deepcopy(ball_position)})
            if kind == "pickup":
                holder = actor
                ball_position = deepcopy(positions[actor])
        elif kind in ("duel", "dodge"):
            defender = params["defender"]
            damage, knocked = {}, set()
            dispersion = None
            for auxiliary in events[index + 1:]:
                if auxiliary["tick"] != tick or auxiliary["type"] not in {"damage", "ko", "ball_drop"}:
                    break
                victim = auxiliary.get("actor")
                if auxiliary["type"] == "damage":
                    damage[victim] = damage.get(victim, 0) + auxiliary["params"]["damage"]
                elif auxiliary["type"] == "ko":
                    knocked.add(victim)
                else:
                    dispersion = cell(auxiliary["params"]["position"])
            statuses = {}
            for victim in (actor, defender):
                future_hp = entities[victim]["hp"] - damage.get(victim, 0)
                statuses[victim] = 4 if future_hp <= 0 else 3 if victim in knocked else 1
            scores = []
            for victim in (actor, defender):
                inherent = entities[victim]["stats"]["strength"]
                allocation = next((a["params"].get("elements", {}) for a in actions.get(victim, []) if "elements" in a["params"]), {})
                attack = inherent + allocation.get("TERRE", 0) * record.get("rules", {}).get("simulation", {}).get("actions", {}).get("element_effects", {}).get("terre", {}).get("attack_bonus_per", 1) + entities[victim].get("attack_bonus", 0)
                scores.append({"inherentScore": inherent, "finalScore": max(0, attack)})
            fight_details = {"ballDispersion": dispersion} if dispersion else {}
            interaction(20, start, 30, [participant(actor, 4, damage=damage.get(actor, 0), status=statuses[actor]),
                                       participant(defender, 5, damage=damage.get(defender, 0), status=statuses[defender])],
                        fightTest={"winner": 5 if kind == "dodge" else 4, "outcome": 3,
                                   "type": 4 if kind == "dodge" else 1, "score": scores}, fightDetails=fight_details)
        elif kind == "damage":
            if actor in entities:
                entities[actor]["hp"] = params["hp"]
        elif kind == "ko":
            if actor in entities:
                entities[actor]["status"]["knocked_down"] = True
        elif kind == "ball_drop":
            holder = None
            ball_position = cell(params["position"])
        elif kind == "throw":
            target = params.get("target_entity_id")
            destination = cell(params["target_position"])
            if target not in tracks or target == actor:
                candidates = [e for e in tracks if e != actor]
                target = min(candidates, key=lambda e: distance(positions[e], destination))
            entry = interaction(21, start, 15, [participant(actor, 2, has_ball=True), participant(target, 3, has_ball=False)],
                                maneuverTest=maneuver(params["success"], entities[actor]["stats"]["precision"]),
                                passDetails={"receptionScoreEstimate": entities[target]["stats"]["precision"], "ballTarget": destination,
                                             "nextInteractionId": 0, "targetId": str(target)})
            pending_passes.append({"entry": entry, "thrower": actor, "target": target,
                                   "origin": deepcopy(positions[actor]), "destination": destination})
            holder = None
        elif kind == "catch_fail":
            # Show each failed attempt without consuming the pending flight or
            # granting possession. Its pass still links to the eventual catch/land.
            origin = pending_passes[0]["origin"] if pending_passes else deepcopy(ball_position)
            intercepted = params.get("interception", False)
            details = {"interceptionDetails" if intercepted else "receptionDetails":
                       {"ballOriginPosition": origin}}
            entry = interaction(15 if intercepted else 14, start, 12,
                                [participant(actor, has_ball=False)], maneuverTest=maneuver(False), **details)
            entry["interactionDetails"]["isCutscene"] = False
        elif kind in ("catch", "ball_land"):
            flight = pending_passes.pop(0) if pending_passes else None
            if kind == "catch":
                origin = flight["origin"] if flight else deepcopy(ball_position)
                same_team = flight and entities[flight["thrower"]]["team_id"] == entities[actor]["team_id"]
                if not params.get("interception", not same_team):
                    entry = interaction(14, start, 15, [participant(actor, has_ball=False)], maneuverTest=maneuver(),
                                        receptionDetails={"ballOriginPosition": origin})
                else:
                    entry = interaction(15, start, 15, [participant(actor, has_ball=False)], maneuverTest=maneuver(),
                                        interceptionDetails={"ballOriginPosition": origin})
                holder = actor
                ball_position = deepcopy(positions[actor])
            else:
                landing = cell(params["position"])
                entry = interaction(13, start, 12, [], onGroundDetails={"ballOriginPosition": flight["origin"] if flight else deepcopy(ball_position),
                                                                       "groundPosition": landing})
                holder = None
                ball_position = landing
            if flight:
                flight["entry"]["interactionDetails"]["passDetails"]["nextInteractionId"] = entry["interactionId"]
        elif kind == "goal":
            interaction(12, start, 40, [participant(actor, has_ball=True)], touchdownDetails={"touchdownDuringRun": True})
            holder = None
        # ball_move is expressed by the original pass arc.
    for flight in pending_passes:
        entry = interaction(13, max(clocks.values()), 12, [], onGroundDetails={"ballOriginPosition": flight["origin"],
                                                                            "groundPosition": flight["destination"]})
        flight["entry"]["interactionDetails"]["passDetails"]["nextInteractionId"] = entry["interactionId"]
    finals = {e["entity_id"]: e for e in result["final_entity_states"]}
    end = max(max(clocks.values(), default=1), round(max(e["tick"] for e in events) * factor) + offset + 1)
    for identity in tracks:
        target = cell(finals[identity]["position"])
        if positions[identity] != target:
            move(identity, end, target)
        else:
            move(identity, end)
        if not tracks[identity]["item"]:
            move(identity, end + 1)
    scenario = {"boufbowlerTracks": list(tracks.values()), "interaction": interactions, "classOrder": abilities,
                "turn": result["turn_number"], "turnEndTick": max(clocks.values(), default=1)}
    limits = record.get('rules',{}).get('match',{})
    turn, total, period = result['turn_number'], limits.get('turns_per_match',0), limits.get('turns_per_period',0)
    if record.get('presentation',{}).get('interactions') and period > 0 and turn < total:
        if turn % period == 0: scenario['periodInformations'] = {'status':2,'remainingPeriodTurns':0}
        elif turn == total-2: scenario['periodInformations'] = {'status':3,'remainingPeriodTurns':2}
        elif period-turn%period == 2: scenario['periodInformations'] = {'status':1,'remainingPeriodTurns':2}
    return limit_ball_cutscenes(scenario)
