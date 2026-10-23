"""Original-client application services over authenticated JSON/protobuf commands."""
from collections import Counter
from copy import deepcopy
import hashlib
import json
import secrets
import time
import threading
import logging
import queue

from backend.admin import Admin
from backend.engine import Engine
from backend.storage import ServiceError, Store
from backend.tracking import Tracking, metrics_report
from tools.flash_protocol import Codec, ProtocolError
from tools.game_config import CLASSES, STADIUMS, load_config, merge, resolve_stadium
from tools.movement_adapter import grid
from tools.game_config import ROOT
from backend.social import Social
from backend.tournaments import Tournaments
from backend.moderation import Moderation
from backend.progression import Progression
from backend.economy import Economy
from backend.tournament_rounds import TournamentRounds
from backend.community import Community
from backend.accounts import Accounts
from backend.matchmaking import Matchmaking
from tools.power_descriptions import client_abilities
from backend.results import POLICY_VERSION, result_kind
from backend.placement import placement_zones
from backend.cpu_team import default_cpu_club
from backend.rulebook import rulebook_snapshot

CLASS_NAMES = ("Cra", "Ecaflip", "Eniripsa", "Enutrof", "Feca", "Iop", "Osamodas", "Pandawa",
               "Rogue", "Sacrier", "Sadida", "Sram", "Xelor", "Zobal")


class Service(Admin, TournamentRounds, Economy, Progression, Moderation, Tournaments, Social, Accounts, Matchmaking, Community):
    def __init__(self, path, config=None, engine=None):
        self.config = deepcopy(config or load_config())
        self.store = Store(path)
        self.tracking = Tracking(self.store)
        self.resolution_lock = threading.Lock()
        self.codec = Codec()
        self.chat_codec = Codec(ROOT / "protocol/chat_contract.json", "ChatMessage")
        try:
            self.engine = engine or Engine()
            self.tracking.engine = self.engine
        except BaseException:
            self.store.close()
            raise
        with self.store.transaction():
            self.maintain_progression();self.maintain_tournaments()
            for row in self.store.db.execute("SELECT state_json FROM matches").fetchall():
                match = json.loads(row[0])
                if match.get("phase") == "simulating":
                    match["phase"] = "orders"
                    match["deadline"] = time.time()
                    self.store.save_match(match)
        self.stopping = threading.Event()
        self.resolution_queue = queue.Queue()
        self.resolution_worker = threading.Thread(target=self.process_resolutions, daemon=True)
        self.resolution_worker.start()
        self.maintenance = threading.Thread(target=self.maintain, daemon=True)
        self.maintenance.start()

    def maintain(self):
        while not self.stopping.wait(1):
            try:
                self.maintain_once()
            except Exception:
                logging.exception("Match deadline maintenance failed")

    def maintain_once(self):
        with self.store.transaction():
            self.maintain_progression()
            self.maintain_tournaments()
            self.match_queued_players()
            for row in self.store.db.execute("SELECT state_json FROM matches").fetchall():
                match = json.loads(row[0])
                if match.get("phase") != "ended":
                    if not self.check_reconnections(match) and match.get("deadline", float("inf")) <= time.time():
                        self.tick_match(match)
            for row in self.store.db.execute("SELECT * FROM challenges WHERE status='pending' AND expires<=?", (time.time(),)).fetchall():
                self.cancel_offer(row)
        self.tracking.sample()
        self.tracking.flush()

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

    def normalize_club(self, club, *, check_roles=True):
        if not isinstance(club, dict):
            raise ServiceError("INVALID_CLUB", "Club data is required")
        for field,enum in (("sigilBackground","SigilBackground"),("sigilCharge","SigilCharge")):
            value=club.get(field)
            if not isinstance(value,int) or isinstance(value,bool) or value not in self.codec.contract['enums'][enum].values():
                raise ServiceError("INVALID_SIGIL","Choose an available blason design")
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
        if check_roles:
            self.validate_roster_roles(players, self.config["rules"])
        normalized["isPredefinedClub"] = False
        return normalized

    @staticmethod
    def validate_roster_roles(players, rules):
        # P10 (1.0.7): the limit applies to the ten-player roster by ROLE,
        # not independently to each class or only to the five field players.
        limit = rules["match"].get("roster_role_limit")
        if limit is None:
            return  # Preserve saved/custom pre-role rule snapshots.
        overrides = rules["classes"]["overrides"]
        roles = Counter(overrides.get(CLASSES[p["boufbowlerClass"] - 1], {}).get(
            "role", 1 + p["boufbowlerClass"] % 4) for p in players)
        if max(roles.values(), default=0) > limit:
            raise ServiceError("ROSTER_ROLE_LIMIT", f"A ten-player roster may contain at most {limit} players of each role")

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

    def create_device(self, body):
        clubs = body.get("clubs")
        if not isinstance(clubs, list) or not 1 <= len(clubs) <= 20:
            raise ServiceError("INVALID_CLUB", "Provide initial clubs")
        # Older clients submit every gallery/template on first login. Preserve
        # inactive templates for editing even when their old composition is no
        # longer playable. The active club and all match entries must be legal.
        normalized = {str(c["clubId"]): self.normalize_club(c, check_roles=index == 0)
                      for index, c in enumerate(clubs)}
        collection = {"active": next(iter(normalized)), "clubs": normalized}
        if not self.economy_settings()['free_customization']:
            for club in collection['clubs'].values():
                club['paletteId']=1
                for player in club['boufbowler']:
                    if player.get('paletteId') in (101,102,103):player['paletteId']=player['boufbowlerClass']
        return self.store.create_profile(body.get("nickname", "Local Player"), collection)

    def hello(self, body):
        with self.store.transaction():
            token = body.get("session")
            if token:
                profile = self.store.authenticate(token)
            else:
                profile, token = self.create_device(body)
            self.maintain_progression()
            self.connection_heartbeat(profile, body.get("language") if not self.store.db.execute("SELECT 1 FROM presence WHERE profile_id=?", (profile,)).fetchone() else None)
            cursor = self.store.db.execute("SELECT COALESCE(MAX(seq),0) FROM events WHERE profile_id=?", (profile,)).fetchone()[0]
            self.emit(profile, "RULES_CONSTANTS", self.rules_message(self.config["rules"]))
            self.emit(profile, "CLUB_INFORMATION", self.club(profile))
            self.emit_ranking(profile)
            self.chat_configuration(profile)
            for offer in self.store.db.execute("SELECT * FROM challenges WHERE guest=? AND status='pending' AND expires>?", (profile,time.time())).fetchall():
                self.emit(profile, "CHALLENGE_PROPOSAL", {"offerId": offer["id"], "hostNickname": self.store.profile(offer["host"])["nickname"], "matchStadium": offer["stadium"]})
            match = self.store.active_match(profile)
            if match:
                side = self.side(match, profile)
                self.emit(profile, "MATCH_INFORMATION", self.match_information(match, side), "MATCH")
                if match["phase"]!="introduction": self.emit(profile, "FIELD_STATE", self.field_state(match, 2 if match["phase"] == "resolution" else None), "MATCH")
                if match["phase"] == "resolution":
                    self.emit(profile, "RESOLUTION_SCENARIO", match["scenario"], "MATCH")
            elif self.spectator_match(profile):
                self.restore_spectating(profile, self.spectator_match(profile))
            self.tracking.activity(profile, body, login=True)
            return {"ok": True, "poll_wait_ms": 20000, "telemetry": True, **self.channel_state(profile), "spectating": str(self.spectator_match(profile)["id"]) if self.spectator_match(profile) else None, "session": token, "cursor": cursor, "profile": self.public_profile(profile),
                    "auth_mode": self.store.session_kind(token), "matchmaking": self.matchmaking_status(profile),
                    "abilities": client_abilities((match or self.spectator_match(profile))["rules"] if (match or self.spectator_match(profile)) else self.config["rules"]),
                    "zobal_masks": self.match_masks(match or self.spectator_match(profile)),
                    "current_match": str(match["id"]) if match else None,
                    "tournament_id": self.current_tournament_id(),
                    "club_names": {key: club["clubName"] for key, club in self.collection(profile)["clubs"].items()}}

    @staticmethod
    def match_masks(match):
        return {str(e["id"]): e.get("zobal_mask", 1) for e in match["world"]["entities"] if e["class_name"] == "Zobal"} if match else {}

    def public_profile(self, profile):
        data = self.store.profile(profile)
        account=self.store.db.execute('SELECT username FROM accounts WHERE profile_id=?',(profile,)).fetchone()
        return {"nickname": data["nickname"], "statistics": data["statistics"],
                "club_id":data["club"]["active"], "club_name":self.club(profile)["clubName"],
                "account_username": account['username'] if account else None, "role":self.role(profile)}

    def command(self, body):
        with self.store.transaction():
            profile = self.store.authenticate(body.get("session"))
            self.connection_heartbeat(profile)
            self.tracking.activity(profile, body)
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
            if operation in ("queue_join","cpu_match","tournament_match","challenge") and body.get("club_id") is not None:
                self.select_club(profile, body["club_id"])
            if operation == "select_club":
                self.select_club(profile, body["club_id"])
            elif operation == "tournament_match":
                self.tournament_match(profile, body.get("tournament_id"))
            elif operation == "save_club":
                self.save_club(profile, body["club"])
            elif operation == "clubs":
                self.emit(profile, "PREDEFINED_CLUBS", {"club": [{"clubId": c["clubId"], "boufbowler": c["boufbowler"]}
                                                               for c in self.collection(profile)["clubs"].values()]})
            elif operation == "challenge":
                self.challenge(profile, {"guestNickname": body["nickname"], "matchStadium": body.get("stadium",1)})
            elif operation == "queue_join":
                self.join_queue(profile, body.get("stadiums"))
            elif operation == "queue_leave":
                self.leave_queue(profile)
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
            response = {"ok": True, **self.channel_state(profile), "profile": self.public_profile(profile), "matchmaking": self.matchmaking_status(profile),
                        "current_match": str(self.store.active_match(profile)["id"]) if self.store.active_match(profile) else None,
                        "tournament_id": self.current_tournament_id(),
                    "club_names": {key: club["clubName"] for key, club in self.collection(profile)["clubs"].items()}}
            active = self.store.active_match(profile) or self.spectator_match(profile)
            response["zobal_masks"] = self.match_masks(active)
            response["abilities"] = client_abilities(active["rules"] if active else self.config["rules"])
            self.store.db.execute("INSERT INTO commands VALUES(?,?,?,?)", (profile, request_id, digest, json.dumps(response)))
            return response

    def select_club(self, profile, identity):
        if self.store.active_match(profile):
            raise ServiceError("MATCH_ACTIVE", "Finish your current match before selecting a team")
        collection=self.collection(profile)
        key=str(identity)
        if key not in collection['clubs']:
            raise ServiceError("CLUB_OWNERSHIP", "This club does not belong to your profile")
        collection['active']=key
        self.store.save_club(profile,collection)
        self.emit(profile,"CLUB_INFORMATION",self.club(profile))
        self.emit_ranking(profile)

    def save_club(self, profile, club):
        collection = self.collection(profile)
        normalized = self.normalize_club(club)
        self.enforce_cosmetics(profile,normalized)
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

    def cinematic_settings(self):
        return {"introductions":True,"interactions":True,"introduction_timeout_seconds":90,
                **self.config["general"].get("cinematics",{})}

    def acknowledge_introduction(self, profile):
        match=self.store.active_match(profile)
        if not match or match['phase']!='introduction': return
        side=str(self.side(match,profile))
        if side not in match['intro_acks']: match['intro_acks'].append(side)
        if all(p is None or str(i) in match['intro_acks'] for i,p in enumerate(match['profiles'],1)):
            self.begin_placement(match)
        self.store.save_match(match)

    def begin_placement(self, match):
        match['phase']='placement'
        match['deadline']=time.time()+match['rules']['match']['placement_seconds']
        self.broadcast(match,'FIELD_STATE',self.field_state(match))

    def create_match(self, left, right, stadium, tournament=None, source=None):
        if not isinstance(stadium, int) or isinstance(stadium, bool) or not 1 <= stadium <= len(STADIUMS):
            raise ServiceError("INVALID_STADIUM", "Choose an available stadium")
        source = source or ("cpu" if right is None else "challenge")
        if source not in ("cpu", "challenge", "matchmaking", "tournament"):
            raise ServiceError("MATCH_SOURCE", "Unknown server match source")
        key = STADIUMS[stadium - 1]
        if not self.config["stadiums"][key]["enabled"]:
            raise ServiceError("STADIUM_DISABLED", "This stadium is disabled")
        if right and self.blocked(left, right):
            raise ServiceError("PLAYER_UNAVAILABLE", "This player is unavailable")
        for participant in (left, right):
            if participant and self.spectator_match(participant):
                raise ServiceError("PLAYER_BUSY", "Stop spectating before playing")
            if participant and self.store.active_match(participant):
                raise ServiceError("MATCH_ACTIVE", "A participant already has an active match")
        for participant in (left, right):
            if participant:
                self.leave_queue(participant)
                for offer in self.store.db.execute("SELECT * FROM challenges WHERE (host=? OR guest=?) AND status='pending'",(participant,participant)).fetchall():
                    self.cancel_offer(offer)
        rules = resolve_stadium(self.config, key)
        if tournament is not None:
            rules["match"].update(self.tournament_config(tournament).get("match_rules", {}))
        left_club = self.club(left)
        right_club = self.club(right) if right else default_cpu_club(left_club['firstColor'])
        for club in (left_club, right_club):
            self.validate_roster_roles(club["boufbowler"], rules)
        team_colors = [deepcopy(left_club['firstColor']), deepcopy(right_club['firstColor'])]
        difference = lambda a,b: sum(abs(a[k]-b[k]) for k in ('r','g','b'))
        if difference(*team_colors)<90:
            team_colors[1]=deepcopy(right_club['secondColor'])
            if difference(*team_colors)<90:
                bright=sum(team_colors[0].values())>382
                team_colors[1]={k:0 if bright else 255 for k in ('r','g','b')}
        rosters = []
        for side, club in enumerate((left_club, right_club), 1):
            players = deepcopy(club["boufbowler"])
            for index, player in enumerate(players, 1):
                player["id"] = str((side - 1) * 100 + index)
                player["attributes"] = self.attributes(player["boufbowlerClass"], rules)
            rosters.append({"characters": players, "nickname": self.store.profile((left, right)[side - 1])["nickname"] if (left, right)[side - 1] else "CPU",
                            "name": club["clubName"] if side == 1 or right else "CPU team",
                            "firstColor": team_colors[side-1],
                            "secondColor": club["secondColor"], "patternColor": club["patternColor"], "firstColorIsDark": sum((299,587,114)[i]*c for i,c in enumerate((team_colors[side-1][k] for k in ("r","g","b")))) < 128000,
                            "ranking": {k:self.store.profile((left,right)[side-1])["statistics"][k] if (left,right)[side-1] else 0 for k in ("wins","draws","defeats")},
                            "sigilBackground": club["sigilBackground"], "sigilCharge": club["sigilCharge"]})
        match = {"profiles": [left, right], "stadium": stadium, "rules": rules, "rules_version": self.config["rules_version"],
                 "created": time.time(), "rosters": rosters, "phase": "placement", "turn": 1, "period": 1, "score": [0, 0], "seed_policy": "independent-turn-v1", "turn_seeds": {},
                 "season_id":self.current_season(), "source": source, "mode": "ranked" if source in ("matchmaking", "tournament") and right else "practice" if right is None else "casual",
                 "result_policy_version": POLICY_VERSION,
                 "orders": {}, "placements": {}, "acks": [], "world": self.initial_world(rosters, rules),
                 "deadline": time.time() + rules["match"]["placement_seconds"]}
        match['presentation']=deepcopy(self.cinematic_settings())
        if rules.get('simulation', {}).get('rulebook'):
            match['rulebook'] = rulebook_snapshot(rules)
        if match['presentation']['introductions']:
            match['phase']='introduction'
            match['intro_acks']=[]
            match['deadline']=time.time()+match['presentation']['introduction_timeout_seconds']
        if tournament is not None:
            match["tournament"] = tournament
            round_row,_=self.round_state(tournament)
            match["tournament_round"]=round_row["round"] if round_row else 0
        cursor = self.store.db.execute("INSERT INTO matches(state_json,updated) VALUES(?,?)", ("{}", time.time()))
        match["id"] = cursor.lastrowid
        for side, participant in enumerate((left, right), 1):
            self.store.db.execute("INSERT INTO participants VALUES(?,?,?)", (match["id"], side, participant))
        self.store.save_match(match)
        for side, participant in enumerate((left, right), 1):
            if participant: self.chat_configuration(participant)
            self.emit(participant, "MATCH_INFORMATION", self.match_information(match, side), "MATCH")
            if match["phase"]!="introduction": self.emit(participant, "FIELD_STATE", self.field_state(match), "MATCH")
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
                                 **({"zobal_mask": 1} if CLASS_NAMES[player["boufbowlerClass"] - 1] == "Zobal" else {}),
                                 "elements": {"TERRE": 0, "FEU": 0, "AIR": 0, "EAU": 0},
                                 "status": {"stunned": False, "knocked_down": False, "carrying_ball": False}})
        return {"entities": entities, "ball": {"position": {"q": 0, "r": 0}, "holder_entity_id": None, "in_flight": False},
                "tick": 0, "sides_swapped": swapped}

    def match_information(self, match, side):
        zones = placement_zones(side, match["period"],
                                match["rules"]["simulation"]["placement"]["ball_exclusion_radius_cells"])
        return {"id": str(match["id"]), "side": side, "leftRoster": match["rosters"][0], "rightRoster": match["rosters"][1],
                "placementZone": zones, "matchStadium": match["stadium"], "skipIntro": match["phase"] != "introduction" or str(side) in match.get("intro_acks",[])}

    def field_state(self, match, phase=None):
        world = match["world"]
        ball = world["ball"]
        ball_state = {"status": 2, "holderId": str(ball["holder_entity_id"])} if ball["holder_entity_id"] is not None else {"status": 1, "position": grid(ball["position"])}
        if match["phase"] == "placement" and match.get("restart_side") is not None:
            ball_state = {"status": 4}
        return {"phaseInfos": {"phase": phase or (1 if match["phase"] in ("placement","introduction") else 2),
                               "remainingTime": max(0, int((match["deadline"] - time.time()) * 1000))},
                "boufbowlerPositions": [{"id": str(e["id"]), "position": grid(e["position"])} for e in world["entities"] if e["hp"] > 0],
                "boufballState": ball_state, "teamState": {**({"placementBoufballSide": match["restart_side"]} if match["phase"] == "placement" and match.get("restart_side") is not None else {}), "turn": match["turn"], "period": match["period"],
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
                if challenge:
                    self.create_match(profile, None, challenge["matchStadium"])
                else:
                    self.join_queue(profile)
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
            self.ladder(profile, name, payload)
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
        elif name == "MODERATION_REQUEST":
            self.moderation_protocol(profile,payload)
        elif name == "WHOIS_REQUEST":
            row = self.store.db.execute("SELECT id FROM profiles WHERE nickname=?", (payload["nickname"],)).fetchone()
            response = {"resultType": 1 if row else 2, "nickname": payload["nickname"]}
            if row:
                response.update(clubname=self.club(row["id"])["clubName"], administrator=self.role(row["id"])=="admin", moderator=self.role(row["id"]) in ("moderator","admin"))
            self.emit(profile, "WHOIS_RESULT", response)
        elif name == "STATS_REQUEST":
            profiles = self.store.db.execute("SELECT COUNT(*) FROM presence WHERE seen>?", (time.time()-90,)).fetchone()[0]
            matches = sum(json.loads(row[0]).get("phase") != "ended" for row in self.store.db.execute("SELECT state_json FROM matches"))
            self.emit(profile, "STATS_RESULT", {"connectedClients": profiles, "currentMatchs": matches})
        elif name == "MATCH_SPECTATE_REQUEST":
            self.spectate(profile, payload)
        elif name == "STOP_SPECTATING":
            self.stop_spectating(profile)
        elif name == "PLACEMENT":
            self.place(profile, payload)
        elif name == "ORDERS":
            self.orders(profile, payload)
        elif name == "RESOLUTION_DONE":
            if not self.store.active_match(profile):
                return
            self.acknowledge(profile, payload)
        elif name == "INTRODUCTION_DONE":
            self.acknowledge_introduction(profile)
        elif name == "SURRENDER":
            match, side = self.profile_match(profile)
            match["score"][2 - side] = max(match["score"][2 - side], match["score"][side - 1] + 1)
            self.end_match(match, side)
        elif name == "CANCEL_MATCH_REQUEST":
            self.leave_queue(profile)
            self.cancel_challenges(profile)
        else:
            raise ServiceError("FEATURE_UNSUPPORTED", f"Unsupported client request: {name}")

    def stop(self):
        self.stopping.set()
        self.store.wake_all()

    def close(self):
        self.stop()
        self.maintenance.join(timeout=35)
        self.resolution_queue.put(None)
        self.resolution_worker.join(timeout=35)
        with self.resolution_lock:
            self.engine.close()
            if not self.store.closed:
                self.tracking.sample()
                self.tracking.flush(force=True)
            self.store.close()

    def place(self, profile, payload):
        match, side = self.profile_match(profile)
        if payload["turn"] != match["turn"] or match["phase"] != "placement":
            if payload["turn"] <= match["turn"] and match["phase"] in ("orders", "simulating", "resolution"):
                return
            raise ServiceError("PHASE_CHANGED", "Placement belongs to another match phase")
        if str(side) in match["placements"]:
            return  # Confirmed placement cannot be edited while waiting.
        positions = payload["boufbowlerPositions"]
        if not positions:
            # The client submits an empty list on placement timeout when no
            # player was dragged. Use the same defaults as deadline maintenance.
            zones = self.match_information(match, side)["placementZone"]
            positions = [{"id": p["id"], "position": z["defaultCell"]}
                         for p, z in zip(match["rosters"][side-1]["characters"][:5], zones)]
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
        previous_masks = match.setdefault("zobal_masks", {})
        previous_masks.update(self.match_masks(match))
        previous_uses = match.setdefault("ability_uses", {})
        previous_uses.update({str(e["id"]): e.get("ability_uses_remaining", 0) for e in match["world"]["entities"]})
        # M02: only reserves rested during the preceding action. Rebuilding the
        # field must not heal returning players (or resurrect a dead player).
        previous_hp = {e["id"]: e["hp"] for e in match["world"]["entities"]}
        roster_health = match.setdefault("roster_health", {})
        roster_health.update({str(identity): hp for identity, hp in previous_hp.items()})
        match["world"] = self.initial_world(selected_rosters, match["rules"], match["period"] % 2 == 0)
        for entity in match["world"]["entities"]:
            entity["position"] = all_positions[entity["id"]]
            if match["rules"]["match"].get("restart_recovery") == "reserves":
                entity["hp"] = previous_hp.get(entity["id"], entity["max_hp"])
                # Full revival rules are unknown; resting must not implicitly
                # resurrect a dead reserve. Keep death distinct from knockdown.
                if roster_health.get(str(entity["id"])) == 0:
                    entity["hp"] = 0
                entity["status"]["knocked_down"] = entity["hp"] <= 0
            if entity["class_name"] == "Zobal": entity["zobal_mask"] = previous_masks.get(str(entity["id"]), 1)
            entity["ability_uses_remaining"] = previous_uses.get(str(entity["id"]), match["rules"]["match"]["class_ability_uses"])
        receiving_side = match.get("restart_side")
        if receiving_side is not None:
            center = next(z for z in self.match_information(match, receiving_side)["placementZone"] if z["type"] == 1)
            receiver = next(e for e in match["world"]["entities"]
                            if e["team_id"] == receiving_side - 1 and grid(e["position"]) in center["cell"])
            match["world"]["ball"]["position"] = deepcopy(receiver["position"])
            if receiver["hp"] > 0:
                receiver["status"]["carrying_ball"] = True
                match["world"]["ball"]["holder_entity_id"] = receiver["id"]
        match["phase"] = "orders"
        match["orders"] = {}
        match["deadline"] = time.time() + match["rules"]["match"]["planning_seconds"]
        self.broadcast(match, "FIELD_STATE", self.field_state(match))

    def orders(self, profile, payload):
        match, side = self.profile_match(profile)
        if payload["turn"] != match["turn"] or match["phase"] != "orders":
            if payload["turn"] <= match["turn"] and match["phase"] in ("simulating", "resolution"):
                return  # A deadline can resolve before the client's automatic submission arrives.
            raise ServiceError("PHASE_CHANGED", "Orders belong to another match phase")
        if str(side) in match["orders"]:
            return  # First submission is immutable, including reconnect retries.
        if payload.get("concedeTouchdown"):
            match["score"][2 - side] += 1
            match["turn"] += 1
            if match["turn"] > match["rules"]["match"]["turns_per_match"]:
                self.end_match(match)
                return
            match["period"] = (match["turn"] - 1) // match["rules"]["match"]["turns_per_period"] + 1
            self.reset_round(match, side)
            self.store.save_match(match)
            return
        match["orders"][str(side)] = self.convert_orders(match, side, profile, payload["orders"])
        if all(p is None or str(index) in match["orders"] for index, p in enumerate(match["profiles"], 1)):
            self.resolve(match)
        self.store.save_match(match)

    def convert_orders(self, match, side, profile, submitted):
        if len(submitted) > 5 or len({order["boufbowlerId"] for order in submitted}) != len(submitted):
            raise ServiceError("INVALID_ORDER", "Submit at most one order per active player")
        if sum(bool(order.get("classOrder")) for order in submitted) > 1:
            raise ServiceError("INVALID_ORDER", "Only one class power per team per turn")
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
                caster = owned[identity]
                if caster["hp"] <= 0 or caster["status"]["knocked_down"] or caster["status"]["stunned"] or caster.get("ability_uses_remaining", 0) <= 0:
                    raise ServiceError("POWER_UNAVAILABLE", "This character cannot use its class power")
                if caster["class_name"] not in match["rules"]["abilities"]:
                    raise ServiceError("POWER_UNAVAILABLE", "No power is configured for this character")
                params = {}
                if caster["class_name"] == "Zobal":
                    mask = order.get("zobalMask")
                    if mask not in (1, 2, 3) or mask == caster.get("zobal_mask", 1):
                        raise ServiceError("INVALID_MASK", "Choose a different Zobal mask")
                    params["zobal_mask"] = mask
                elif "zobalMask" in order:
                    raise ServiceError("INVALID_MASK", "Only Zobal can change mask")
                actions.append({"entity_id": int(identity), "action_type": "ability", "params": params})
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
        if match["phase"] == "simulating":
            return
        # Commit immutable inputs and the private seed before releasing the lock.
        # Retried commands see the saved receipt, not a second simulation.
        turn_key = str(match["turn"])
        seeds = match.setdefault("turn_seeds", {})
        if turn_key not in seeds:
            seeds[turn_key] = secrets.randbits(32)
        match["seed_policy"] = "independent-turn-v1"
        match["phase"] = "simulating"
        match["deadline"] = time.time() + 300
        snapshot = deepcopy(match)
        self.store.save_match(match)
        self.store.after_commit(lambda: self.resolution_queue.put(snapshot))

    def process_resolutions(self):
        while True:
            snapshot = self.resolution_queue.get()
            try:
                if snapshot is None:
                    return
                self.complete_resolution(snapshot)
            finally:
                self.resolution_queue.task_done()

    def complete_resolution(self, snapshot):
        with self.resolution_lock:
            if not self.stopping.is_set():
                self.run_resolution(snapshot)

    def run_resolution(self, snapshot):
        simulation_started = time.perf_counter()
        simulation_observed = False
        try:
            initial = snapshot["world"]
            result = self.engine.simulate(initial, [snapshot["orders"].get("1"), snapshot["orders"].get("2")],
                                          snapshot["turn"], snapshot["turn_seeds"][str(snapshot["turn"])],
                                          snapshot["rules"], [p is None for p in snapshot["profiles"]])
            self.tracking.observe("simulation", "turn", (time.perf_counter() - simulation_started) * 1000)
            simulation_observed = True
            record = {"format_version": 1, "initial": initial, "orders": result["orders"], "result": result["result"],
                      "rules": snapshot["rules"], "rules_version": snapshot["rules_version"],
                      "seed_policy": snapshot["seed_policy"], "warnings": result["warnings"],
                      "presentation": snapshot.get("presentation", self.cinematic_settings())}
            if snapshot.get('rulebook'):
                record['rulebook'] = {key:snapshot['rulebook'][key] for key in ('id','sha256','evidence_revision')}
            from backend.turn_adapter import adapt_turn
            scenario = adapt_turn(record)
            record["scenario"] = deepcopy(scenario)
            with self.store.transaction():
                match = self.store.match(snapshot["id"])
                # A surrender may have ended the match during simulation.
                if match["phase"] != "simulating" or match["turn"] != snapshot["turn"]:
                    return
                self.store.db.execute("INSERT INTO turns VALUES(?,?,?)", (match["id"], match["turn"], json.dumps(record)))
                from backend.game_measurements import record_turn
                record_turn(self.store.db,match["id"],match["turn"],record,match["profiles"])
                match["pending"] = result["result"]
                match["scenario"] = scenario
                match["phase"] = "resolution"
                match["acks"] = []
                match["deadline"] = time.time() + 300
                self.broadcast(match, "RESOLUTION_SCENARIO", scenario)
                self.store.save_match(match)
        except Exception as error:
            if not simulation_observed:
                self.tracking.observe("simulation", "turn", (time.perf_counter() - simulation_started) * 1000, error=True)
            self.tracking.error("server", getattr(error, "code", "SIMULATION_ERROR"), str(error))
            logging.exception("Turn simulation failed; keeping inputs for retry")
            with self.store.transaction():
                match = self.store.match(snapshot["id"])
                if match["phase"] == "simulating" and match["turn"] == snapshot["turn"]:
                    match["phase"] = "orders"
                    match["deadline"] = time.time() + 5
                    self.store.save_match(match)

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
                    interval = players[entity["id"]]["attributes"]["hitPointRegenRate"]
                    if interval > 0 and (match["turn"] - 1) % interval == 0:
                        entity["hp"] = min(entity["max_hp"], entity["hp"] + 1)
        period = (match["turn"] - 1) // match["rules"]["match"]["turns_per_period"] + 1
        if any(result["score"]) or period != match["period"]:
            match["period"] = period
            receiving_side = 2 if result["score"][0] else 1 if result["score"][1] else None
            self.reset_round(match, receiving_side)
        else:
            match["phase"] = "orders"
            match["orders"] = {}
            match["deadline"] = time.time() + match["rules"]["match"]["planning_seconds"]
            self.broadcast(match, "FIELD_STATE", self.field_state(match))

    def reset_round(self, match, receiving_side=None):
        match["restart_side"] = receiving_side
        match["phase"] = "placement"
        match["placements"] = {}
        match["orders"] = {}
        match["deadline"] = time.time() + match["rules"]["match"]["placement_seconds"]
        match["world"]["ball"] = {"position": {"q": 0, "r": 0}, "holder_entity_id": None, "in_flight": False}
        for entity in match["world"]["entities"]:
            if match["rules"]["match"].get("restart_recovery") != "reserves":
                entity["hp"] = entity["max_hp"]
            entity["status"] = {"stunned": False, "knocked_down": entity["hp"] <= 0, "carrying_ball": False}
        self.broadcast(match, "FIELD_STATE", self.field_state(match))

    def end_match(self, match, given_up=None):
        if match["phase"] == "ended":
            return
        match["phase"] = "ended"
        match["ended"] = time.time()
        match["given_up"] = given_up
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
        watchers = [r[0] for r in self.store.db.execute("SELECT profile_id FROM spectators WHERE match_id=?", (match["id"],))]
        for profile in [*match["profiles"], *watchers]:
            if profile:
                self.emit_chat(profile, "CHANNEL_UNAVAILABLE_NOTIFICATION", {"channels": [{"channelType": 3}]})
                self.emit_ranking(profile)
        match["end_payload"] = payload
        self.store.save_match(match)
        self.store.db.execute("DELETE FROM spectators WHERE match_id=?", (match["id"],))
        if match.get("tournament") is not None: self.maintain_tournaments()

    def tick(self, profile):
        match = self.store.active_match(profile)
        if match:
            self.tick_match(match)

    def tick_match(self, match):
        if self.check_reconnections(match):
            return
        if match and match["deadline"] <= time.time():
            if match["phase"] == "introduction":
                self.begin_placement(match)
            elif match["phase"] == "placement":
                self.finish_placement(match)
            elif match["phase"] == "orders":
                self.resolve(match)
            elif match["phase"] == "resolution":
                self.advance(match)
            self.store.save_match(match)

    def connection_heartbeat(self, profile, language=None):
        match = self.store.active_match(profile)
        if match:
            self.check_reconnections(match)
        self.touch(profile, language)
        if match and match['phase'] != 'ended':
            self.check_reconnections(match)

    def check_reconnections(self, match):
        """P11 grace, with explicit heartbeat/boundary/both-offline policy."""
        policy = match.get('rules', {}).get('simulation', {}).get('rulebook', {}).get('connection')
        if not policy or match.get('phase') == 'ended':
            return match.get('phase') == 'ended'
        now = time.time()
        disconnected = match.setdefault('disconnected', {})
        expired = []
        changed = False
        for side, profile in enumerate(match['profiles'], 1):
            if profile is None:
                continue
            row = self.store.db.execute('SELECT seen FROM presence WHERE profile_id=?', (profile,)).fetchone()
            seen = max(match['created'], row[0] if row else match['created'])
            key = str(side)
            offline_at = disconnected.get(key, seen + policy['heartbeat_timeout'])
            if seen >= offline_at and key in disconnected and seen < offline_at + policy['grace_seconds']:
                del disconnected[key]
                changed = True
                opponent = match['profiles'][2-side]
                if opponent:
                    self.emit(opponent, 'OPPONENT_RECONNECTED', {}, 'MATCH')
            elif now >= offline_at:
                if key not in disconnected:
                    disconnected[key] = offline_at
                    changed = True
                    opponent = match['profiles'][2-side]
                    if opponent:
                        self.emit(opponent, 'OPPONENT_DISCONNECTED', {}, 'MATCH')
                if now >= offline_at + policy['grace_seconds']:
                    expired.append(side)
        if expired:
            match['end_reason'] = 'both_disconnected' if len(expired) == 2 else 'disconnect_timeout'
            # Both absent: retain score and existing result policy. This is an
            # explicit restoration choice; no historical winner is asserted.
            given_up = expired[0] if len(expired) == 1 else None
            if given_up:
                match['score'][2-given_up] = max(match['score'][2-given_up], match['score'][given_up-1]+1)
            self.end_match(match, given_up)
            return True
        if changed:
            self.store.save_match(match)
        return False

    def poll(self, body):
        wait_ms = body.get("wait_ms", 0)
        if not isinstance(wait_ms, int) or isinstance(wait_ms, bool) or not 0 <= wait_ms <= 20000:
            raise ServiceError("POLL_WAIT", "Poll wait must be 0–20000 milliseconds")
        if not isinstance(body.get("compact", False), bool):
            raise ServiceError("POLL_COMPACT", "Compact polling must be a boolean")
        deadline = time.monotonic() + wait_ms / 1000
        with self.store.lock:
            if self.stopping.is_set():
                raise ServiceError("SERVICE_STOPPING", "Server is shutting down")
            profile = self.store.authenticate(body.get("session"))
            self.poll_heartbeat(profile)
            self.tracking.activity(profile, body)
            with self.store.watch(profile) as condition:
                while True:
                    if self.stopping.is_set():
                        raise ServiceError("SERVICE_STOPPING", "Server is shutting down")
                    events = self.store.poll(profile, body.get("cursor", 0))
                    remaining = deadline - time.monotonic()
                    if events or remaining <= 0:
                        break
                    condition.wait(remaining)
                    if self.stopping.is_set():
                        raise ServiceError("SERVICE_STOPPING", "Server is shutting down")
                    self.store.authenticate(body.get("session"))
            # A waiting connection is not proof of continued connectivity. Only
            # receipt of a new request updates its heartbeat.
            return self.poll_response(profile, events, body.get("compact", False))

    def poll_heartbeat(self, profile):
        now = time.time()
        presence = self.store.db.execute("SELECT seen FROM presence WHERE profile_id=?", (profile,)).fetchone()
        queue = self.store.db.execute("SELECT heartbeat,tournament_id FROM matchmaking_queue WHERE profile_id=?", (profile,)).fetchone()
        if presence and presence[0] > now - 10 and (not queue or queue[0] > now - 10):
            return
        with self.store.transaction():
            self.connection_heartbeat(profile)
            if queue:
                # An already-expired queue entry must not be resurrected.
                if queue[0] < now - self.matchmaking_settings()["heartbeat_timeout"]:
                    if queue["tournament_id"] is not None:
                        self.emit(profile, "TOURNAMENT_OFFER_CANCELED", {})
                    self.leave_queue(profile)
                else:
                    self.store.db.execute("UPDATE matchmaking_queue SET heartbeat=? WHERE profile_id=?", (now, profile))

    def metrics(self, body):
        with self.store.lock:
            profile = self.store.authenticate(body.get('session'))
            if self.role(profile) != 'admin':
                raise ServiceError('ACTIVITY_FORBIDDEN', 'Server administrator access required')
            self.tracking.sample()
            self.tracking.flush(force=True)
            result = metrics_report(self.store, body.get('days', 30))
            result['resources'] = self.tracking.resources()
            return result

    def website_events(self, body):
        return self.tracking.website_events(body)

    def live_presence(self, body=None):
        now = time.time()
        with self.store.lock:
            online = self.store.db.execute('SELECT COUNT(*) FROM presence WHERE seen>?', (now - 90,)).fetchone()[0]
            in_game = self.store.db.execute('''SELECT COUNT(DISTINCT p.profile_id) FROM presence p
                JOIN participants pt ON pt.profile_id=p.profile_id
                JOIN matches m ON m.id=pt.match_id
                WHERE p.seen>? AND json_extract(m.state_json,'$.phase')!='ended' ''', (now - 90,)).fetchone()[0]
        in_game = min(int(online), int(in_game))
        return {'ok': True, 'total': int(online), 'lobby': int(online) - in_game, 'in_game': in_game,
                'generated_at': now, 'grace_seconds': 90}

    def telemetry(self, body):
        with self.store.transaction():
            profile = self.store.authenticate(body.get('session'))
            self.tracking.activity(profile, body)
            return self.tracking.telemetry(profile, body)

    def poll_once(self, body):
        return self.poll({**body, "wait_ms": 0})

    def poll_response(self, profile, events, compact):
        # Correct phase clocks when packets spent time waiting for a mobile
        # client to reconnect; never restart a full planning timer on delivery.
        for event in events:
            if event["type"] == "FIELD_STATE" and "created_at" in event:
                payload = self.codec.open_envelope(bytes.fromhex(event["hex"]))["payload"]
                elapsed = max(0, int((time.time() - event["created_at"]) * 1000))
                payload["phaseInfos"]["remainingTime"] = max(0, payload["phaseInfos"]["remainingTime"] - elapsed)
                event["hex"] = self.codec.envelope("FIELD_STATE", payload).hex()
        chat_messages = {"RECEIVE_FROM_CHANNEL", "RECEIVE_FROM_CLIENT", "RECEIVE_FROM_SERVER"}
        if compact and all(event["channel"] == "CHAT" and event["type"] in chat_messages for event in events):
            return {"ok": True, "events": events, "matchmaking": self.matchmaking_status(profile),
                    "tournament_id": self.current_tournament_id()}
        match = self.store.active_match(profile)
        spectator = self.spectator_match(profile)
        metadata = {}
        if any(event["type"] in ("MATCH_INFORMATION", "MATCH_END") for event in events):
            active = match or spectator
            metadata = {"abilities": client_abilities(active["rules"] if active else self.config["rules"]),
                        "zobal_masks": self.match_masks(active)}
        return {"ok": True, "tournament_id": self.current_tournament_id(), **metadata, **self.channel_state(profile),
                "events": events, "profile": self.public_profile(profile), "matchmaking": self.matchmaking_status(profile),
                "spectating": str(spectator["id"]) if spectator else None,
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

    def challenge(self, profile, challenge):
        guest = self.store.db.execute("SELECT id FROM profiles WHERE nickname=?", (challenge["guestNickname"],)).fetchone()
        if not guest or guest["id"] == profile:
            raise ServiceError("PLAYER_UNKNOWN", "Choose another saved player name, or CPU")
        if self.blocked(profile, guest["id"]):
            raise ServiceError("PLAYER_UNAVAILABLE", "This player is unavailable")
        if self.store.active_match(profile) or self.store.active_match(guest["id"]):
            raise ServiceError("PLAYER_BUSY", "A player already has an active match")
        stadium = challenge["matchStadium"]
        if not 1 <= stadium <= 9 or not self.config["stadiums"][STADIUMS[stadium - 1]]["enabled"]:
            raise ServiceError("INVALID_STADIUM", "Choose an enabled stadium")
        self.leave_queue(profile)
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
            self.store.db.execute("UPDATE challenges SET status='accepted' WHERE id=?", (row["id"],))
            self.create_match(row["host"], row["guest"], row["stadium"])
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
