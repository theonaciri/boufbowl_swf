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


def maneuver(success=True, score=10, evidence=None):
    # A boolean probability test has no historical severity information. Only
    # forward a tier when the authoritative provider explicitly recorded one.
    evidence = evidence or {}
    outcome = {'normal': 3, 'wide': 2, 'critical': 1}.get(evidence.get('tier'), 3)
    return {"success": bool(success), "outcome": outcome,
            "difficulty": int(evidence.get('difficulty', 0)),
            "score": {"inherentScore": int(evidence.get('inherent_score', score)),
                      "finalScore": int(evidence.get('final_score', score))}}


def bonus_wire(value):
    # Original protocol declares UINT32, but ParticipantData consumes int.
    # Keep the signed two's-complement bit pattern for negative feedback.
    value = int(value)
    if not -(1 << 31) <= value < 1 << 31:
        raise ProtocolError('Bonus/malus exceeds original signed presentation range')
    return value & 0xffffffff


def fight_animation(kind, params, actions, actor, defender):
    """Original presentation families; this never selects the winner or damage."""
    if kind == 'dodge':
        return 4
    winner = params.get('winner', actor)
    loser = defender if winner == actor else actor
    targeted = params.get('branch') == 'targeted' or any(
        action['action_type'] == 'follow' and action['params'].get('target_entity_id') == loser
        for action in actions.get(winner, []))
    if not targeted:
        return 2  # Incidental hit, including directional running shoulder checks.
    elements = next((a['params']['elements'] for a in actions.get(loser, [])
                     if 'elements' in a['params']), {})
    # BoufbowlerBaseInformation.isDodging: Fire present, Earth absent.
    return 3 if elements.get('FEU', 0) > 0 and not elements.get('TERRE', 0) else 1


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
               "throw", "ball_move", "catch", "catch_fail", "ball_land", "goal", "final_state", "fall", "movement_test",
               "throw_cancelled", "stun", "stun_end", "protection_expired", "movement_bonus"}
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
    consumed_moves, event_times, stun_spans = set(), {}, []

    def continuation(identity):
        # Borrow only the next recorded step before another interaction. No
        # invented displacement, extra movement budget or new simulation order.
        barriers = {'ability', 'fall', 'pickup', 'pickup_fail', 'duel', 'dodge',
                    'throw', 'catch', 'catch_fail', 'goal'}
        for cursor in range(index + 1, len(events)):
            later = events[cursor]
            if later['type'] in barriers:
                involved = identity in (later.get('actor'), later['params'].get('defender'),
                                       later['params'].get('target_entity_id'))
                if involved or later['type'] == 'goal' or identity in later['params'].get('targets', []):
                    break
            if later.get('actor') == identity:
                if later['type'] in {'ko', 'stun', 'stand_up', 'stun_end'}:
                    break
                if later['type'] == 'move':
                    target = cell(later['params']['position'])
                    if cursor not in consumed_moves and distance(positions[identity], target) == 1:
                        consumed_moves.add(cursor)
                        return target
                    break
        return None

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
                "status": status if status is not None else 4 if entity["hp"] <= 0 else 3 if entity["status"]["knocked_down"] else 2 if entity["status"]["stunned"] else 1,
                "damageTaken": max(0, int(damage))}

    def maneuver_participant(identity, role=1, has_ball=False):
        data = participant(identity, role, has_ball=has_ball)
        if params.get('maneuver_bonus_malus'):
            data['maneuverBonusMalus'] = bonus_wire(params['maneuver_bonus_malus'])
        # Preserve authoritative consequences when a future recovered scoring
        # provider supplies a critical maneuver. FX must not invent knockdowns.
        for auxiliary in events[index + 1:]:
            if auxiliary['tick'] != tick or auxiliary['type'] not in {'damage', 'ko', 'stun', 'ball_drop'}:
                break
            if auxiliary.get('actor') != identity:
                continue
            if auxiliary['type'] == 'damage':
                data['damageTaken'] += max(0, int(auxiliary['params']['damage']))
                if auxiliary['params']['hp'] <= 0:
                    data['status'] = 4
            elif auxiliary['type'] == 'ko' and data['status'] != 4:
                data['status'] = 3
            elif auxiliary['type'] == 'stun' and data['status'] not in (3, 4):
                data['status'] = 2
                stun_spans.append((data, index, tick, max(start, max(clocks.values())),
                                   auxiliary['params'].get('until_tick', tick)))
        failed = kind in {'pickup_fail', 'catch_fail'} or kind == 'throw' and not params.get('success')
        if failed and params.get('tier') == 'critical':
            expected = (2, 3, 4) if kind == 'throw' else (3, 4)
            if data['status'] not in expected:
                raise ProtocolError('Critical maneuver lacks authoritative stun/down consequences')
        return data

    def interaction(kind, start, duration, participants, **details):
        nonlocal offset
        start = max(start, max(clocks.values(), default=0))
        end = start + duration
        identity = len(interactions) + 1
        for actor_data in participants:
            actor = int(actor_data["boufbowlerId"])
            move(actor, start)
            trajectory = [deepcopy(positions[actor])]
            if kind in (11, 14, 15, 20, 21) and actor_data['status'] == 1:
                target = continuation(actor)
                if target is not None:
                    trajectory.append(target)
                    positions[actor] = deepcopy(target)
            tracks[actor]["item"].append({"type": 2, "interactionId": identity,
                                         "movement": {"positions": trajectory, "startTick": start, "endTick": end}})
            clocks[actor] = end
        entry = {"interactionId": identity, "interactionDetails": {"type": kind, "startTick": start, "endTick": end,
                 "isCutscene": bool(record.get("presentation",{}).get("interactions",False) and kind in (12,13,14,15,20,21)), "participants": participants, **details}}
        if kind == 20 and details['fightTest']['type'] == 2:
            # HitAndRun has no fullscreen branch; don't consume the later
            # ball fight's cinematic slot for a flag the original script ignores.
            entry['interactionDetails']['isCutscene'] = False
        interactions.append(entry)
        offset += duration
        return entry

    for index, event in enumerate(events):
        kind, tick, actor, params = event["type"], event["tick"], event.get("actor"), event["params"]
        start = max(1, round(tick * factor) + offset)
        event_times[index] = start
        if kind == "move":
            if index in consumed_moves:
                continue
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
                display.extend(params[key] for key in ('shield','temporary_hp') if params.get(key))
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
                display.extend(params[key] for key in ('range','attack','combat_damage') if params.get(key))
                if not params.get('elements') and params.get('element') and params.get('bonus'):
                    display.append(params['bonus'])
                if display: target_data['effectDeltas'] = list(dict.fromkeys(display))
            ability = {"boufbowlerId": str(actor), "target": targets}
            if "zobal_mask" in params: ability["zobalMask"] = params["zobal_mask"]
            abilities.append(ability)
        elif kind == "movement_test":
            if actor in tracks:
                test = maneuver(params['success'], params.get('inherent_score', 0), params)
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
        elif kind == "stun_end":
            entities[actor]["status"]["stunned"] = False
        elif kind in ("pickup", "pickup_fail"):
            data = maneuver_participant(actor)
            interaction(11, start, 14, [data], maneuverTest=maneuver(kind == "pickup", evidence=params),
                        pickupDetails={"ballPosition": deepcopy(ball_position)})
            if kind == "pickup":
                holder = actor
                ball_position = deepcopy(positions[actor])
        elif kind in ("duel", "dodge"):
            defender = params["defender"]
            damage, knocked, stunned, stun_until = {}, set(), set(), {}
            dispersion = None
            for auxiliary in events[index + 1:]:
                if auxiliary["tick"] != tick or auxiliary["type"] not in {"damage", "ko", "stun", "ball_drop"}:
                    break
                victim = auxiliary.get("actor")
                if auxiliary["type"] == "damage":
                    damage[victim] = damage.get(victim, 0) + auxiliary["params"]["damage"]
                elif auxiliary["type"] == "ko":
                    knocked.add(victim)
                elif auxiliary["type"] == "stun":
                    stunned.add(victim)
                    stun_until[victim] = auxiliary['params'].get('until_tick', tick)
                else:
                    dispersion = cell(auxiliary["params"]["position"])
            statuses = {}
            for victim in (actor, defender):
                future_hp = entities[victim]["hp"] - damage.get(victim, 0)
                statuses[victim] = 4 if future_hp <= 0 else 3 if victim in knocked else 2 if victim in stunned else 1
            scores = []
            for victim in (actor, defender):
                fields = params.get('stat_fields', {})
                inherent = entities[victim]["stats"][fields.get(str(victim), fields.get(victim, 'strength'))]
                allocation = next((a["params"].get("elements", {}) for a in actions.get(victim, []) if "elements" in a["params"]), {})
                attack = inherent + allocation.get("TERRE", 0) * record.get("rules", {}).get("simulation", {}).get("actions", {}).get("element_effects", {}).get("terre", {}).get("attack_bonus_per", 1) + entities[victim].get("attack_bonus", 0)
                values = params.get('score_values', {})
                final_score = values.get(str(victim), values.get(victim, attack))
                scores.append({"inherentScore": inherent, "finalScore": round(max(0, final_score))})
            fight_details = {"ballDispersion": dispersion} if dispersion else {}
            fighters = [participant(actor, 4, damage=damage.get(actor, 0), status=statuses[actor]),
                        participant(defender, 5, damage=damage.get(defender, 0), status=statuses[defender])]
            for data in fighters:
                victim = int(data['boufbowlerId'])
                if victim == params.get('winner') and params.get('granted_bonus'):
                    data['fightBonusMalus'] = bonus_wire(params['granted_bonus'])
                if victim in stun_until and statuses[victim] == 2:
                    stun_spans.append((data, index, tick, max(start, max(clocks.values())), stun_until[victim]))
            interaction(20, start, 30, fighters,
                        fightTest={"winner": (4 if params['winner'] == actor else 5) if 'winner' in params else 5 if kind == "dodge" else 4,
                                   "outcome": {'normal':3,'wide':2,'critical':1}.get(params.get('tier'),3),
                                   "type": fight_animation(kind, params, actions, actor, defender), "score": scores}, fightDetails=fight_details)
        elif kind == "damage":
            if actor in entities:
                entities[actor]["hp"] = params["hp"]
        elif kind == "ko":
            if actor in entities:
                entities[actor]["status"]["knocked_down"] = True
        elif kind == "stun":
            if actor in entities:
                entities[actor]["status"]["stunned"] = True
        elif kind == "ball_drop":
            holder = None
            ball_position = cell(params["position"])
        elif kind == "throw":
            origin = cell(params['start_position']) if 'start_position' in params else deepcopy(positions[actor])
            target = params.get("target_entity_id")
            destination = cell(params["target_position"])
            if target not in tracks or target == actor:
                candidates = [e for e in tracks if e != actor]
                target = min(candidates, key=lambda e: distance(positions[e], destination))
            entry = interaction(21, start, 15, [maneuver_participant(actor, 2, has_ball=True), participant(target, 3, has_ball=False)],
                                maneuverTest=maneuver(params["success"], entities[actor]["stats"]["precision"], params),
                                passDetails={"receptionScoreEstimate": entities[target]["stats"]["precision"], "ballTarget": destination,
                                             "nextInteractionId": 0, "targetId": str(target)})
            pending_passes.append({"entry": entry, "thrower": actor, "target": target,
                                   "origin": origin, "destination": destination})
            holder = None
        elif kind == "catch_fail":
            # Show each failed attempt without consuming the pending flight or
            # granting possession. Its pass still links to the eventual catch/land.
            origin = pending_passes[0]["origin"] if pending_passes else deepcopy(ball_position)
            intercepted = params.get("interception", False)
            details = {"interceptionDetails" if intercepted else "receptionDetails":
                       {"ballOriginPosition": origin}}
            entry = interaction(15 if intercepted else 14, start, 12,
                                [maneuver_participant(actor)], maneuverTest=maneuver(False, evidence=params), **details)
            if params.get('tier') != 'critical':
                entry["interactionDetails"]["isCutscene"] = False
            elif intercepted:
                # A failed interception can knock down the interceptor without
                # ending the flight or stealing the intended receiver's link.
                pass
            elif pending_passes:
                # The throw must see HITS_RECEIVER rather than a plain landing;
                # a critical reception then links to its rebound separately.
                pending_passes[0]['failed_reception'] = entry
                pending_passes[0]['rebound_origin'] = cell(params['position']) if 'position' in params else deepcopy(positions[actor])
                pending_passes[0]['entry']['interactionDetails']['passDetails']['nextInteractionId'] = entry['interactionId']
            else:
                raise ProtocolError('Critical reception lacks an authoritative flight/rebound')
        elif kind in ("catch", "ball_land"):
            flight = pending_passes.pop(0) if pending_passes else None
            if kind == "catch":
                origin = flight["origin"] if flight else deepcopy(ball_position)
                same_team = flight and entities[flight["thrower"]]["team_id"] == entities[actor]["team_id"]
                if not params.get("interception", not same_team):
                    entry = interaction(14, start, 15, [maneuver_participant(actor)], maneuverTest=maneuver(evidence=params),
                                        receptionDetails={"ballOriginPosition": origin})
                else:
                    entry = interaction(15, start, 15, [maneuver_participant(actor)], maneuverTest=maneuver(evidence=params),
                                        interceptionDetails={"ballOriginPosition": origin})
                holder = actor
                ball_position = deepcopy(positions[actor])
            else:
                landing = cell(params["position"])
                if flight and flight.get('failed_reception'):
                    offset += 4
                    start += 4
                entry = interaction(13, start, 12, [], onGroundDetails={"ballOriginPosition": flight.get('rebound_origin', flight['origin']) if flight else deepcopy(ball_position),
                                                                       "groundPosition": landing})
                holder = None
                ball_position = landing
            if flight:
                failed = flight.get('failed_reception')
                if failed:
                    if kind != 'ball_land':
                        raise ProtocolError('Critical reception must resolve to an authoritative rebound')
                    if failed['interactionDetails']['type'] == 14:
                        failed['interactionDetails']['receptionDetails']['nextInteractionId'] = entry['interactionId']
                else:
                    flight["entry"]["interactionDetails"]["passDetails"]["nextInteractionId"] = entry["interactionId"]
        elif kind == "goal":
            interaction(12, start, 40, [participant(actor, has_ball=True)], touchdownDetails={"touchdownDuringRun": True})
            holder = None
        # ball_move is expressed by the original pass arc.
    for flight in pending_passes:
        entry = interaction(13, max(clocks.values()), 12, [], onGroundDetails={"ballOriginPosition": flight["origin"],
                                                                            "groundPosition": flight["destination"]})
        failed = flight.get('failed_reception')
        if failed and failed['interactionDetails']['type'] == 14:
            failed['interactionDetails']['receptionDetails']['nextInteractionId'] = entry['interactionId']
        elif not failed:
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
    for data, source, tick, start, until in stun_spans:
        recovery = next((event_times[cursor] for cursor in range(source + 1, len(events))
                         if events[cursor]['type'] == 'stun_end'
                         and str(events[cursor].get('actor')) == data['boufbowlerId']), None)
        # Include presentation slots inserted before recovery; raw simulation
        # ticks alone can expire the original star FX before the hit lands.
        if recovery is None:
            recovery = end + max(0, round((until - max(e['tick'] for e in events)) * factor))
        data['stunDuration'] = max(1, recovery - start)
    limits = record.get('rules',{}).get('match',{})
    turn, total, period = result['turn_number'], limits.get('turns_per_match',0), limits.get('turns_per_period',0)
    if record.get('presentation',{}).get('interactions') and period > 0 and turn < total:
        if turn % period == 0: scenario['periodInformations'] = {'status':2,'remainingPeriodTurns':0}
        elif turn == total-2: scenario['periodInformations'] = {'status':3,'remainingPeriodTurns':2}
        elif period-turn%period == 2: scenario['periodInformations'] = {'status':1,'remainingPeriodTurns':2}
    return limit_ball_cutscenes(scenario)
