"""Original-client application services over authenticated JSON/protobuf commands."""
from collections import Counter
from copy import deepcopy
import hashlib
import json
import secrets
import time
import threading
import logging

from backend.engine import Engine
from backend.storage import ServiceError, Store
from tools.flash_protocol import Codec, ProtocolError
from tools.game_config import CLASSES, STADIUMS, load_config, merge, resolve_stadium
from tools.movement_adapter import grid
from tools.game_config import ROOT
from backend.social import Social

CLASS_NAMES = ("Cra", "Ecaflip", "Eniripsa", "Enutrof", "Feca", "Iop", "Osamodas", "Pandawa",
               "Rogue", "Sacrier", "Sadida", "Sram", "Xelor", "Zobal")


class Service(Social):
    def __init__(self, path, config=None, engine=None):
        self.config = deepcopy(config or load_config())
        self.store = Store(path)
        self.codec = Codec()
        self.chat_codec = Codec(ROOT / "protocol/chat_contract.json", "ChatMessage")
        try:
            self.engine = engine or Engine()
        except BaseException:
            self.store.close()
            raise
        self.stopping = threading.Event()
        self.maintenance = threading.Thread(target=self.maintain, daemon=True)
        self.maintenance.start()

    def maintain(self):
        while not self.stopping.wait(1):
            try:
                with self.store.transaction():
                    for row in self.store.db.execute("SELECT state_json FROM matches").fetchall():
                        match = json.loads(row[0])
                        if match.get("phase") != "ended" and match.get("deadline", float("inf")) <= time.time():
                            self.tick_match(match)
                    for row in self.store.db.execute("SELECT * FROM challenges WHERE status='pending' AND expires<=?", (time.time(),)).fetchall():
                        self.cancel_offer(row)
            except Exception:
                logging.exception("Match deadline maintenance failed")

    def packet(self, name, payload, channel="LOBBY"):
        return {"channel": channel, "type": name, "hex": self.codec.envelope(name, payload).hex()}

    def emit(self, profile, name, payload, channel="LOBBY"):
        self.store.emit(profile, self.packet(name, payload, channel))

    def attributes(self, class_id, rules=None):
        if not isinstance(class_id, int) or isinstance(class_id, bool) or not 1 <= class_id <= 14:
            raise ServiceError("INVALID_CLASS", "Choose a known character class")
        classes = (rules or self.config["rules"])["classes"]
        values = merge(classes["defaults"], classes["overrides"].get(CLASSES[class_id - 1], {}))
        return {**{key: values[key] for key in ("earth", "air", "fire", "water")},
                "maxHitPoints": values["health"], "hitPointRegenRate": values["regeneration"]}

    @staticmethod
    def name(value, limit=30):
        if not isinstance(value, str) or not 1 <= len(value.strip()) <= limit or any(ord(x) < 32 for x in value):
            raise ServiceError("INVALID_NAME", "Choose a nonempty name without control characters")
        return value.strip()

    @staticmethod
    def color(value):
        if not isinstance(value, dict) or set(value) != {"r", "g", "b"} or any(
                not isinstance(x, int) or isinstance(x, bool) or not 0 <= x <= 255 for x in value.values()):
            raise ServiceError("INVALID_COLOR", "Colors require RGB values from 0 to 255")
        return deepcopy(value)

    def normalize_club(self, club):
        if not isinstance(club, dict):
            raise ServiceError("INVALID_CLUB", "Club data is required")
        self.codec.encode("ClubInformationMessage", club)
        normalized = deepcopy(club)
        normalized["clubName"] = self.name(club["clubName"])
        for field in ("firstColor", "secondColor", "patternColor"):
            normalized[field] = self.color(club.get(field))
        players = normalized["boufbowler"]
        if len(players) != 10 or len({p["id"] for p in players}) != 10:
            raise ServiceError("INVALID_ROSTER", "A club must contain ten distinct characters")
        for player in players:
            player["name"] = self.name(player["name"])
            class_id = player["boufbowlerClass"]
            player["attributes"] = self.attributes(class_id)
            if player["gender"] not in (1, 2):
                raise ServiceError("INVALID_GENDER", "Choose a supported gender")
            hero = player.get("uniqueCharacter", 0)
            if hero != 0 and not 501 <= hero <= 518:
                raise ServiceError("INVALID_CHARACTER", "Unknown special character")
            for field in ("hairColor", "eyeColor", "skinColor"):
                if field in player:
                    player[field] = self.color(player[field])
        normalized["isPredefinedClub"] = False
        return normalized

    def collection(self, profile):
        return self.store.profile(profile)["club"]

    def club(self, profile):
        collection = self.collection(profile)
        return deepcopy(collection["clubs"][collection["active"]])

    def rules_message(self, rules):
        ranges, match = rules["client_ranges"], rules["match"]
        return {"maxDistanceFactor": ranges["max_distance_factor"], "earthDistanceBonus": ranges["earth_distance_bonus"],
                "fireDistanceBonus": ranges["fire_distance_bonus"], "airDistanceBonus": ranges["air_distance_bonus"],
                "waterDistanceBonus": ranges["water_distance_bonus"], "placementPhaseDuration": match["placement_seconds"],
                "ordersPhaseDuration": match["planning_seconds"], "maxBoufbowlerCountPerRole": match["max_players_per_role"],
                "stadiumRules": [{"stadium": index, "matchTurnDuration": resolved["match"]["turns_per_match"],
                                  "periodTurnDuration": resolved["match"]["turns_per_period"],
                                  "classOrderUseByMatch": resolved["match"]["class_ability_uses"]}
                                 for index, stadium in enumerate(STADIUMS, 1)
                                 for resolved in [resolve_stadium(self.config, stadium)]],
                "classAttributes": [{"boufbowlerClass": index, "role": rules["classes"]["overrides"].get(name, {}).get("role", 1 + index % 4),
                                     "attributes": self.attributes(index, rules)} for index, name in enumerate(CLASSES, 1)]}

    def hello(self, body):
        with self.store.transaction():
            token = body.get("session")
            if token:
                profile = self.store.authenticate(token)
            else:
                clubs = body.get("clubs")
                if not isinstance(clubs, list) or not 1 <= len(clubs) <= 20:
                    raise ServiceError("INVALID_CLUB", "Provide initial clubs")
                normalized = {str(c["clubId"]): self.normalize_club(c) for c in clubs}
                collection = {"active": next(iter(normalized)), "clubs": normalized}
                profile, token = self.store.create_profile(body.get("nickname", "Local Player"), collection)
            cursor = self.store.db.execute("SELECT COALESCE(MAX(seq),0) FROM events WHERE profile_id=?", (profile,)).fetchone()[0]
            self.emit(profile, "RULES_CONSTANTS", self.rules_message(self.config["rules"]))
            self.emit(profile, "CLUB_INFORMATION", self.club(profile))
            self.emit_ranking(profile)
            self.chat_configuration(profile)
            match = self.store.active_match(profile)
            if match:
                side = self.side(match, profile)
                self.emit(profile, "MATCH_INFORMATION", self.match_information(match, side), "MATCH")
                self.emit(profile, "FIELD_STATE", self.field_state(match, 2 if match["phase"] == "resolution" else None), "MATCH")
                if match["phase"] == "resolution":
                    self.emit(profile, "RESOLUTION_SCENARIO", match["scenario"], "MATCH")
            return {"ok": True, "session": token, "cursor": cursor, "profile": self.public_profile(profile),
                    "abilities": (match["rules"] if match else self.config["rules"])["abilities"],
                    "current_match": str(match["id"]) if match else None,
                    "club_names": {key: club["clubName"] for key, club in self.collection(profile)["clubs"].items()}}

    def public_profile(self, profile):
        data = self.store.profile(profile)
        return {"nickname": data["nickname"], "statistics": data["statistics"]}

    def command(self, body):
        with self.store.transaction():
            profile = self.store.authenticate(body.get("session"))
            request_id = body.get("request_id")
            if not isinstance(request_id, str) or not 1 <= len(request_id) <= 100:
                raise ServiceError("REQUEST_ID", "A stable command request ID is required")
            digest = hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            previous = self.store.db.execute("SELECT * FROM commands WHERE profile_id=? AND request_id=?", (profile, request_id)).fetchone()
            if previous:
                if previous["request_hash"] != digest:
                    raise ServiceError("REQUEST_CONFLICT", "A request ID cannot be reused for another command")
                return json.loads(previous["response_json"])
            operation = body.get("operation", "protocol")
            if operation == "save_club":
                self.save_club(profile, body["club"])
            elif operation == "clubs":
                self.emit(profile, "PREDEFINED_CLUBS", {"club": [{"clubId": c["clubId"], "boufbowler": c["boufbowler"]}
                                                               for c in self.collection(profile)["clubs"].values()]})
            elif operation == "cpu_match":
                self.create_match(profile, None, body.get("stadium", 1))
            elif operation == "chat":
                data = self.chat_codec.open_envelope(bytes.fromhex(body["hex"]))
                self.handle_chat(profile, data["type"], data["payload"])
            elif operation == "protocol":
                try:
                    data = self.codec.open_envelope(bytes.fromhex(body["hex"]))
                except (ValueError, KeyError) as error:
                    raise ServiceError("PROTOCOL_INVALID", str(error)) from error
                self.handle_protocol(profile, data["type"], data["payload"])
            else:
                raise ServiceError("COMMAND_UNKNOWN", "Unknown backend operation")
            response = {"ok": True, "profile": self.public_profile(profile),
                        "current_match": str(self.store.active_match(profile)["id"]) if self.store.active_match(profile) else None,
                        "club_names": {key: club["clubName"] for key, club in self.collection(profile)["clubs"].items()}}
            active = self.store.active_match(profile)
            response["abilities"] = (active["rules"] if active else self.config["rules"])["abilities"]
            self.store.db.execute("INSERT INTO commands VALUES(?,?,?,?)", (profile, request_id, digest, json.dumps(response)))
            return response

    def save_club(self, profile, club):
        collection = self.collection(profile)
        normalized = self.normalize_club(club)
        identity = str(normalized["clubId"])
        if identity not in collection["clubs"]:
            raise ServiceError("CLUB_OWNERSHIP", "This club does not belong to your profile")
        old_ids = {p["id"] for p in collection["clubs"][identity]["boufbowler"]}
        if old_ids != {p["id"] for p in normalized["boufbowler"]}:
            raise ServiceError("PLAYER_OWNERSHIP", "Roster identities cannot be changed")
        collection["clubs"][identity] = normalized
        collection["active"] = identity
        self.store.save_club(profile, collection)
        self.emit(profile, "CLUB_INFORMATION", normalized)
        self.emit_ranking(profile)

    @staticmethod
    def side(match, profile):
        if profile not in match["profiles"]:
            raise ServiceError("MATCH_OWNERSHIP", "You are not a participant in this match")
        return match["profiles"].index(profile) + 1

    def profile_match(self, profile):
        match = self.store.active_match(profile)
        if not match:
            raise ServiceError("NO_ACTIVE_MATCH", "No active match for this profile")
        return match, self.side(match, profile)

    def create_match(self, left, right, stadium):
        if not isinstance(stadium, int) or isinstance(stadium, bool) or not 1 <= stadium <= len(STADIUMS):
            raise ServiceError("INVALID_STADIUM", "Choose an available stadium")
        key = STADIUMS[stadium - 1]
        if not self.config["stadiums"][key]["enabled"]:
            raise ServiceError("STADIUM_DISABLED", "This stadium is disabled")
        for participant in (left, right):
            if participant and self.store.active_match(participant):
                raise ServiceError("MATCH_ACTIVE", "A participant already has an active match")
        rules = resolve_stadium(self.config, key)
        left_club = self.club(left)
        right_club = self.club(right) if right else deepcopy(left_club)
        rosters = []
        for side, club in enumerate((left_club, right_club), 1):
            players = deepcopy(club["boufbowler"])
            for index, player in enumerate(players, 1):
                player["id"] = str((side - 1) * 100 + index)
                player["attributes"] = self.attributes(player["boufbowlerClass"], rules)
            rosters.append({"characters": players, "nickname": self.store.profile((left, right)[side - 1])["nickname"] if (left, right)[side - 1] else "CPU",
                            "name": club["clubName"] if side == 1 or right else "CPU team",
                            "firstColor": club["firstColor"] if side == 1 else {"r": 210, "g": 80, "b": 60},
                            "secondColor": club["secondColor"], "patternColor": club["patternColor"], "firstColorIsDark": False,
                            "ranking": {"wins": 0, "draws": 0, "defeats": 0},
                            "sigilBackground": club["sigilBackground"], "sigilCharge": club["sigilCharge"]})
        match = {"profiles": [left, right], "stadium": stadium, "rules": rules, "rules_version": self.config["rules_version"],
                 "rosters": rosters, "phase": "placement", "turn": 1, "period": 1, "score": [0, 0], "seed": secrets.randbits(32),
                 "orders": {}, "placements": {}, "acks": [], "world": self.initial_world(rosters, rules),
                 "deadline": time.time() + rules["match"]["placement_seconds"]}
        cursor = self.store.db.execute("INSERT INTO matches(state_json,updated) VALUES(?,?)", ("{}", time.time()))
        match["id"] = cursor.lastrowid
        for side, participant in enumerate((left, right), 1):
            self.store.db.execute("INSERT INTO participants VALUES(?,?,?)", (match["id"], side, participant))
        self.store.save_match(match)
        for side, participant in enumerate((left, right), 1):
            self.emit(participant, "MATCH_INFORMATION", self.match_information(match, side), "MATCH")
            self.emit(participant, "FIELD_STATE", self.field_state(match), "MATCH")
        return match

    @staticmethod
    def initial_world(rosters, rules, swapped=False):
        entities = []
        for side, roster in enumerate(rosters):
            for index, player in enumerate(roster["characters"][:5]):
                attr = player["attributes"]
                entities.append({"id": int(player["id"]), "team_id": side, "position": {"q": -7 if (side == 0) != swapped else 7, "r": index - 2},
                                 "orientation": 0, "stats": {"strength": attr["earth"], "agility": attr["fire"],
                                                            "endurance": attr["water"], "precision": attr["air"]},
                                 "hp": attr["maxHitPoints"], "max_hp": attr["maxHitPoints"],
                                 "class_name": CLASS_NAMES[player["boufbowlerClass"] - 1],
                                 "ability_uses_remaining": rules["match"]["class_ability_uses"],
                                 "elements": {"TERRE": 0, "FEU": 0, "AIR": 0, "EAU": 0},
                                 "status": {"stunned": False, "knocked_down": False, "carrying_ball": False}})
        return {"entities": entities, "ball": {"position": {"q": 0, "r": 0}, "holder_entity_id": None, "in_flight": False},
                "tick": 0, "sides_swapped": swapped}

    def match_information(self, match, side):
        centers = [(-7, 0), (-6, -3), (-8, -3), (-9, 3), (-6, 3)]
        zones = [{"type": index, "defaultCell": {"x": x, "y": y},
                  "cell": [{"x": x + dx, "y": y + dy} for dx, dy in ((0, 0), (1, 0), (0, 1), (-1, 0), (0, -1))]}
                 for index, (x, y) in enumerate(centers, 1)]
        if side == 2:
            for zone in zones:
                for cell in [zone["defaultCell"], *zone["cell"]]:
                    cell["x"], cell["y"] = -cell["x"], -cell["y"]
        return {"id": str(match["id"]), "side": side, "leftRoster": match["rosters"][0], "rightRoster": match["rosters"][1],
                "placementZone": zones, "matchStadium": match["stadium"], "skipIntro": True}

    def field_state(self, match, phase=None):
        world = match["world"]
        ball = world["ball"]
        ball_state = {"status": 2, "holderId": str(ball["holder_entity_id"])} if ball["holder_entity_id"] is not None else {"status": 1, "position": grid(ball["position"])}
        return {"phaseInfos": {"phase": phase or (1 if match["phase"] == "placement" else 2),
                               "remainingTime": max(0, int((match["deadline"] - time.time()) * 1000))},
                "boufbowlerPositions": [{"id": str(e["id"]), "position": grid(e["position"])} for e in world["entities"] if e["hp"] > 0],
                "boufballState": ball_state, "teamState": {"turn": match["turn"], "period": match["period"],
                 "leftSideScore": match["score"][0], "rightSideScore": match["score"][1],
                 "boufbowlerStates": [{"id": str(e["id"]), "status": 4 if e["hp"] <= 0 else 3 if e["status"]["knocked_down"] else 2 if e["status"]["stunned"] else 1,
                                       "currentHitPoints": e["hp"], "remainingClassOrderUses": e.get("ability_uses_remaining", 0)} for e in world["entities"]]}}

    def broadcast(self, match, name, payload):
        watchers = [row[0] for row in self.store.db.execute("SELECT profile_id FROM spectators WHERE match_id=?", (match["id"],))]
        for profile in [*match["profiles"], *watchers]:
            self.emit(profile, name, payload, "MATCH")

    def handle_protocol(self, profile, name, payload):
        if name == "MATCH_REQUEST":
            if "tournamentId" in payload:
                self.tournament_match(profile, payload["tournamentId"])
                return
            challenge = payload.get("challenge")
            if challenge and challenge["guestNickname"].strip().lower() not in ("cpu", "computer"):
                self.challenge(profile, challenge)
            else:
                self.create_match(profile, None, challenge["matchStadium"] if challenge else 1)
        elif name == "CHALLENGE_ANSWER":
            self.answer_challenge(profile, payload)
        elif name == "PREDEFINED_CLUB_SELECTION":
            collection = self.collection(profile)
            key = str(payload["clubId"])
            if key not in collection["clubs"]:
                raise ServiceError("CLUB_OWNERSHIP", "Unknown club selection")
            club = deepcopy(collection["clubs"][key])
            club.update({k: v for k, v in payload.items() if k != "firstColorIsDark"})
            self.save_club(profile, club)
        elif name in ("BOUFBOWLER_APPEARANCE_CHANGE", "BOUFBOWLER_ATTRIBUTES_CHANGE", "CLUB_APPEARANCE_CHANGE", "FULL_TEAM_CHANGE", "FORCED_FULL_TEAM_CHANGE"):
            self.customize(profile, name, payload)
        elif name == "CUSTOMISATION_SESSION_REQUEST":
            response = {"customisationType": payload["type"]}
            if "boufbowlerId" in payload:
                response["boufbowlerId"] = payload["boufbowlerId"]
            self.emit(profile, "CUSTOMISATION_SESSION_ACCEPTED", response)
        elif name == "UPDATE_PREMIUM_CONTENT":
            self.emit(profile, "PREMIUM_CONTENT_UPDATED", {})
        elif name == "CANCEL_CUSTOMISATION_SESSION":
            return
        elif name in ("LADDER_BY_LEAGUE_REQUEST", "LADDER_BY_NICK_REQUEST"):
            self.ladder(profile)
        elif name == "OUTSTANDING_TOURNAMENTS_REQUEST":
            self.tournaments(profile)
        elif name == "TOURNAMENT_LEADERBOARD_REQUEST":
            self.tournament_leaderboard(profile, payload["tournamentId"])
        elif name == "RUNNING_TOURNAMENT_MATCHES_REQUEST":
            self.running_tournament_matches(profile)
        elif name == "PING_REQUEST":
            self.emit(profile, "PING_RESULT", payload)
        elif name == "TIME_REQUEST":
            self.emit(profile, "TIME_RESULT", {"timestamp": time.time() * 1000})
        elif name == "WHOIS_REQUEST":
            row = self.store.db.execute("SELECT id FROM profiles WHERE nickname=?", (payload["nickname"],)).fetchone()
            response = {"resultType": 1 if row else 2, "nickname": payload["nickname"]}
            if row:
                response.update(clubname=self.club(row["id"])["clubName"], administrator=False, moderator=False)
            self.emit(profile, "WHOIS_RESULT", response)
        elif name == "STATS_REQUEST":
            profiles = self.store.db.execute("SELECT COUNT(*) FROM profiles").fetchone()[0]
            matches = sum(json.loads(row[0]).get("phase") != "ended" for row in self.store.db.execute("SELECT state_json FROM matches"))
            self.emit(profile, "STATS_RESULT", {"connectedClients": profiles, "currentMatchs": matches})
        elif name == "MATCH_SPECTATE_REQUEST":
            self.spectate(profile, payload)
        elif name == "STOP_SPECTATING":
            row = self.store.db.execute("SELECT match_id FROM spectators WHERE profile_id=?", (profile,)).fetchone()
            if row:
                self.broadcast(self.store.match(row[0]), "MATCH_SPECTATOR_PART_NOTIFICATION", {"nickname": self.store.profile(profile)["nickname"]})
            self.store.db.execute("DELETE FROM spectators WHERE profile_id=?", (profile,))
        elif name == "PLACEMENT":
            self.place(profile, payload)
        elif name == "ORDERS":
            self.orders(profile, payload)
        elif name == "RESOLUTION_DONE":
            if not self.store.active_match(profile) and self.store.db.execute("SELECT 1 FROM spectators WHERE profile_id=?", (profile,)).fetchone():
                return
            self.acknowledge(profile, payload)
        elif name == "INTRODUCTION_DONE":
            return
        elif name == "SURRENDER":
            match, side = self.profile_match(profile)
            match["score"][2 - side] = max(match["score"][2 - side], match["score"][side - 1] + 1)
            self.end_match(match, side)
        elif name == "CANCEL_MATCH_REQUEST":
            self.cancel_challenges(profile)
        else:
            raise ServiceError("FEATURE_UNSUPPORTED", f"Unsupported client request: {name}")

    def close(self):
        self.stopping.set()
        self.maintenance.join(timeout=35)
        self.engine.close()
        self.store.close()

    def place(self, profile, payload):
        match, side = self.profile_match(profile)
        if payload["turn"] != match["turn"] or match["phase"] != "placement":
            if payload["turn"] <= match["turn"] and match["phase"] in ("orders", "resolution"):
                return
            raise ServiceError("PHASE_CHANGED", "Placement belongs to another match phase")
        positions = payload["boufbowlerPositions"]
        owned = {p["id"]: p for p in match["rosters"][side - 1]["characters"]}
        if len(positions) != 5 or len({p["id"] for p in positions}) != 5 or any(p["id"] not in owned for p in positions):
            raise ServiceError("INVALID_PLACEMENT", "Place five different members of your own roster")
        zones = self.match_information(match, side)["placementZone"]
        used = set()
        for position in positions:
            choices = [z["type"] for z in zones if position["position"] in z["cell"] and z["type"] not in used]
            if not choices:
                raise ServiceError("INVALID_PLACEMENT", "Place one player in each placement zone")
            used.add(choices[0])
        classes = match["rules"]["classes"]
        roles = Counter(classes["overrides"].get(CLASSES[owned[p["id"]]["boufbowlerClass"] - 1], {}).get("role", 1 + owned[p["id"]]["boufbowlerClass"] % 4) for p in positions)
        if max(roles.values()) > match["rules"]["match"]["max_players_per_role"]:
            raise ServiceError("ROLE_LIMIT", "Placement exceeds the configured role limit")
        match["placements"][str(side)] = deepcopy(positions)
        if all(p is None or str(index) in match["placements"] for index, p in enumerate(match["profiles"], 1)):
            self.finish_placement(match)
        self.store.save_match(match)

    def finish_placement(self, match):
        selected_rosters = []
        all_positions = {}
        for side, roster in enumerate(match["rosters"], 1):
            selection = match["placements"].get(str(side))
            if selection is None:
                zones = self.match_information(match, side)["placementZone"]
                selection = [{"id": p["id"], "position": z["defaultCell"]} for p, z in zip(roster["characters"][:5], zones)]
            players = {p["id"]: p for p in roster["characters"]}
            selected_rosters.append({"characters": [players[p["id"]] for p in selection]})
            all_positions.update({int(p["id"]): {"q": p["position"]["x"], "r": p["position"]["y"]} for p in selection})
        previous_uses = match.setdefault("ability_uses", {})
        previous_uses.update({str(e["id"]): e.get("ability_uses_remaining", 0) for e in match["world"]["entities"]})
        match["world"] = self.initial_world(selected_rosters, match["rules"], match["period"] % 2 == 0)
        for entity in match["world"]["entities"]:
            entity["position"] = all_positions[entity["id"]]
            entity["ability_uses_remaining"] = previous_uses.get(str(entity["id"]), match["rules"]["match"]["class_ability_uses"])
        match["phase"] = "orders"
        match["orders"] = {}
        match["deadline"] = time.time() + match["rules"]["match"]["planning_seconds"]
        self.broadcast(match, "FIELD_STATE", self.field_state(match))

    def orders(self, profile, payload):
        match, side = self.profile_match(profile)
        if payload["turn"] != match["turn"] or match["phase"] != "orders":
            if payload["turn"] <= match["turn"] and match["phase"] == "resolution":
                return  # A deadline can resolve before the client's automatic submission arrives.
            raise ServiceError("PHASE_CHANGED", "Orders belong to another match phase")
        if str(side) in match["orders"]:
            raise ServiceError("ORDER_ALREADY_SUBMITTED", "Your orders are already submitted")
        if payload.get("concedeTouchdown"):
            match["score"][2 - side] += 1
            match["turn"] += 1
            if match["turn"] > match["rules"]["match"]["turns_per_match"]:
                self.end_match(match)
                return
            match["period"] = (match["turn"] - 1) // match["rules"]["match"]["turns_per_period"] + 1
            self.reset_round(match)
            self.store.save_match(match)
            return
        match["orders"][str(side)] = self.convert_orders(match, side, profile, payload["orders"])
        if all(p is None or str(index) in match["orders"] for index, p in enumerate(match["profiles"], 1)):
            self.resolve(match)
        self.store.save_match(match)

    def convert_orders(self, match, side, profile, submitted):
        if len(submitted) > 5 or len({order["boufbowlerId"] for order in submitted}) != len(submitted):
            raise ServiceError("INVALID_ORDER", "Submit at most one order per active player")
        world = match["world"]
        owned = {str(e["id"]): e for e in world["entities"] if e["team_id"] == side - 1}
        all_entities = {str(e["id"]): e for e in world["entities"]}
        actions = []
        for order in submitted:
            identity = order["boufbowlerId"]
            if identity not in owned:
                raise ServiceError("PLAYER_OWNERSHIP", "Orders can target only your own active players")
            if order.get("classOrder"):
                if "regularOrder" in order:
                    raise ServiceError("INVALID_ORDER", "Choose either a regular order or a class ability")
                actions.append({"entity_id": int(identity), "action_type": "ability", "params": {}})
                continue
            regular = order.get("regularOrder", {"elements": []})
            elements = regular["elements"]
            if len(elements) != 3 or any(e not in (1, 2, 3, 4) for e in elements):
                raise ServiceError("INVALID_ELEMENTS", "Regular orders require three valid elements")
            counts = {name: elements.count(value) for name, value in (("TERRE", 1), ("AIR", 2), ("FEU", 3), ("EAU", 4))}
            params = {"elements": counts}
            action_type = "wait"
            if "targetCell" in regular:
                target = regular["targetCell"]
                params["target_position"] = {"q": target["x"], "r": target["y"]}
                action_type = "move"
            elif "targetBoufbowler" in regular:
                target_id = regular["targetBoufbowler"]
                if target_id not in all_entities:
                    raise ServiceError("INVALID_TARGET", "Unknown target player")
                params["target_entity_id"] = int(target_id)
                action_type = "follow"
            elif regular.get("targetsBall"):
                params["target_position"] = deepcopy(world["ball"]["position"])
                action_type = "move"
            actions.append({"entity_id": int(identity), "action_type": action_type, "params": params})
            if "passTargetId" in regular:
                target_id = regular["passTargetId"]
                if target_id not in all_entities or counts["AIR"] < 1:
                    raise ServiceError("INVALID_PASS", "A pass requires AIR and a valid receiver")
                actions.append({"entity_id": int(identity), "action_type": "throw",
                                "params": {"elements": counts, "target_entity_id": int(target_id)}})
        return {"player_id": profile, "team_index": side - 1, "turn_number": match["turn"],
                "nonce": f"{match['id']}:{match['turn']}:{side}", "actions": actions}

    def resolve(self, match):
        initial = deepcopy(match["world"])
        seed = (match["seed"] ^ match["turn"] * 2654435761) & 0xffffffff
        result = self.engine.simulate(initial, [match["orders"].get("1"), match["orders"].get("2")],
                                      match["turn"], seed, match["rules"], [p is None for p in match["profiles"]])
        record = {"format_version": 1, "initial": initial, "orders": result["orders"], "result": result["result"],
                  "rules": match["rules"], "rules_version": match["rules_version"], "warnings": result["warnings"]}
        from backend.turn_adapter import adapt_turn
        scenario = adapt_turn(record)
        self.store.db.execute("INSERT INTO turns VALUES(?,?,?)", (match["id"], match["turn"], json.dumps(record)))
        match["pending"] = result["result"]
        match["scenario"] = scenario
        match["phase"] = "resolution"
        match["acks"] = []
        match["deadline"] = time.time() + 300
        self.broadcast(match, "RESOLUTION_SCENARIO", scenario)

    def acknowledge(self, profile, payload):
        match, side = self.profile_match(profile)
        if match["phase"] != "resolution" or payload["turn"] != match["turn"]:
            if payload["turn"] < match["turn"]:
                return
            raise ServiceError("PHASE_CHANGED", "Resolution acknowledgement has the wrong turn")
        if side not in match["acks"]:
            match["acks"].append(side)
        if all(p is None or index in match["acks"] for index, p in enumerate(match["profiles"], 1)):
            self.advance(match)
        self.store.save_match(match)

    def advance(self, match):
        result = match.pop("pending")
        match["world"] = result["final_world_state"]
        match["score"] = [a + b for a, b in zip(match["score"], result["score"])]
        if match["turn"] >= match["rules"]["match"]["turns_per_match"]:
            self.end_match(match)
            return
        match["turn"] += 1
        if match["rules"]["match"].get("regenerate_between_turns", False):
            players = {int(player["id"]): player for roster in match["rosters"] for player in roster["characters"]}
            for entity in match["world"]["entities"]:
                if entity["hp"] > 0:
                    entity["hp"] = min(entity["max_hp"], entity["hp"] + players[entity["id"]]["attributes"]["hitPointRegenRate"])
        period = (match["turn"] - 1) // match["rules"]["match"]["turns_per_period"] + 1
        if any(result["score"]) or period != match["period"]:
            match["period"] = period
            self.reset_round(match)
        else:
            match["phase"] = "orders"
            match["orders"] = {}
            match["deadline"] = time.time() + match["rules"]["match"]["planning_seconds"]
            self.broadcast(match, "FIELD_STATE", self.field_state(match))

    def reset_round(self, match):
        match["phase"] = "placement"
        match["placements"] = {}
        match["orders"] = {}
        match["deadline"] = time.time() + match["rules"]["match"]["placement_seconds"]
        match["world"]["ball"] = {"position": {"q": 0, "r": 0}, "holder_entity_id": None, "in_flight": False}
        for entity in match["world"]["entities"]:
            entity["hp"] = entity["max_hp"]
            entity["status"] = {"stunned": False, "knocked_down": False, "carrying_ball": False}
        self.broadcast(match, "FIELD_STATE", self.field_state(match))

    def end_match(self, match, given_up=None):
        if match["phase"] == "ended":
            return
        match["phase"] = "ended"
        payload = {"id": str(match["id"]), "leftScore": match["score"][0], "rightScore": match["score"][1]}
        if match["score"][0] != match["score"][1]:
            payload["winner"] = 1 if match["score"][0] > match["score"][1] else 2
        if given_up is not None:
            payload["givenUp"] = given_up
        for side, participant in enumerate(match["profiles"], 1):
            self.store.reward(match, side)
            stats = self.store.profile(participant)["statistics"] if participant else {"wins": 0, "draws": 0, "defeats": 0}
            payload["leftRanking" if side == 1 else "rightRanking"] = {key: stats[key] for key in ("wins", "draws", "defeats")}
        self.broadcast(match, "MATCH_END", payload)
        for profile in match["profiles"]:
            if profile:
                self.emit_ranking(profile)
        self.store.save_match(match)

    def tick(self, profile):
        match = self.store.active_match(profile)
        if match:
            self.tick_match(match)

    def tick_match(self, match):
        if match and match["deadline"] <= time.time():
            if match["phase"] == "placement":
                self.finish_placement(match)
            elif match["phase"] == "orders":
                self.resolve(match)
            elif match["phase"] == "resolution":
                self.advance(match)
            self.store.save_match(match)

    def poll(self, body):
        with self.store.transaction():
            profile = self.store.authenticate(body.get("session"))
            self.tick(profile)
            match = self.store.active_match(profile)
            return {"ok": True, "events": self.store.poll(profile, body.get("cursor", 0)), "profile": self.public_profile(profile),
                    "current_match": str(match["id"]) if match else None}

    def customize(self, profile, name, payload):
        club = self.club(profile)
        if name in ("FULL_TEAM_CHANGE", "FORCED_FULL_TEAM_CHANGE"):
            change = payload["change"]
            self.customize(profile, "CLUB_APPEARANCE_CHANGE", change["clubAppearanceChange"])
            for player in change["boufbowlerAttributesChange"]:
                self.customize(profile, "BOUFBOWLER_ATTRIBUTES_CHANGE", player)
            return
        if name == "CLUB_APPEARANCE_CHANGE":
            mapping = {"clubName": "clubName", "paletteId": "paletteId", "firstColor": "firstColor", "secondColor": "secondColor",
                       "patternColor": "patternColor", "blazonField": "sigilBackground", "blazonCharge": "sigilCharge"}
            club.update({target: payload[source] for source, target in mapping.items()})
        else:
            player = next((p for p in club["boufbowler"] if p["id"] == payload["id"]), None)
            if player is None:
                raise ServiceError("PLAYER_OWNERSHIP", "This player is not in your active club")
            player.update(payload["appearance"])
            if name == "BOUFBOWLER_ATTRIBUTES_CHANGE":
                player["boufbowlerClass"] = payload["boufbowlerClass"]
        self.save_club(profile, club)
        self.emit(profile, "CUSTOMISATION_ACCEPTED", {})

    def ladder(self, profile):
        profiles = [self.store.profile(row["id"]) for row in self.store.db.execute("SELECT id FROM profiles")]
        profiles.sort(key=lambda p: (-p["statistics"]["rating"], p["nickname"].casefold()))
        rows = []
        for index, player in enumerate(profiles, 1):
            stats = player["statistics"]
            rows.append({"index": index - 1, "rank": index, "player": self.player_summary(player["id"]),
                         "wins": stats["wins"], "draws": stats["draws"], "losses": stats["defeats"], "rating": stats["rating"]})
        own = next(row for row in rows if row["player"]["nickname"] == self.store.profile(profile)["nickname"])
        self.emit(profile, "LADDER_DATA", {"firstIndexToDisplay": 0, "rows": rows[:100], "ownData": own, "league": 1, "subLeague": 1})

    def challenge(self, profile, challenge):
        guest = self.store.db.execute("SELECT id FROM profiles WHERE nickname=?", (challenge["guestNickname"],)).fetchone()
        if not guest or guest["id"] == profile:
            raise ServiceError("PLAYER_UNKNOWN", "Choose another saved player name, or CPU")
        if self.store.active_match(profile) or self.store.active_match(guest["id"]):
            raise ServiceError("PLAYER_BUSY", "A player already has an active match")
        stadium = challenge["matchStadium"]
        if not 1 <= stadium <= 9 or not self.config["stadiums"][STADIUMS[stadium - 1]]["enabled"]:
            raise ServiceError("INVALID_STADIUM", "Choose an enabled stadium")
        cursor = self.store.db.execute("INSERT INTO challenges(host,guest,stadium,status,expires) VALUES(?,?,?,?,?)",
                                       (profile, guest["id"], stadium, "pending", time.time() + 60))
        offer = cursor.lastrowid
        self.emit(profile, "CHALLENGE_CREATED", {"offerId": offer})
        self.emit(guest["id"], "CHALLENGE_PROPOSAL", {"offerId": offer, "hostNickname": self.store.profile(profile)["nickname"], "matchStadium": stadium})

    def answer_challenge(self, profile, payload):
        row = self.store.db.execute("SELECT * FROM challenges WHERE id=?", (payload["offerId"],)).fetchone()
        if not row or profile not in (row["host"], row["guest"]) or row["status"] != "pending":
            raise ServiceError("CHALLENGE_INVALID", "This challenge is no longer available")
        if row["expires"] <= time.time():
            raise ServiceError("CHALLENGE_EXPIRED", "This challenge expired")
        if payload["answer"] == 2:
            if profile != row["guest"]:
                raise ServiceError("CHALLENGE_OWNERSHIP", "Only the challenged player can accept")
            self.create_match(row["host"], row["guest"], row["stadium"])
            self.store.db.execute("UPDATE challenges SET status='accepted' WHERE id=?", (row["id"],))
        elif payload["answer"] == 1:
            self.cancel_offer(row)
        else:
            raise ServiceError("CHALLENGE_INVALID", "Unknown challenge answer")

    def cancel_challenges(self, profile):
        for row in self.store.db.execute("SELECT * FROM challenges WHERE host=? AND status='pending'", (profile,)).fetchall():
            self.cancel_offer(row)

    def cancel_offer(self, row):
        self.store.db.execute("UPDATE challenges SET status='cancelled' WHERE id=?", (row["id"],))
        for profile in (row["host"], row["guest"]):
            self.emit(profile, "CHALLENGE_CANCELED", {"offerId": row["id"]})
