"""Persisted chat, player summaries and configured local tournament services."""
import json
import time
from backend.storage import ServiceError


class Social:
    def player_summary(self, profile):
        player, club = self.store.profile(profile), self.club(profile)
        return {"nickname": player["nickname"], "club": {"clubName": club["clubName"],
                "clubFirstColor": club["firstColor"], "clubSecondColor": club["secondColor"],
                "clubPatternColor": club["patternColor"], "sigilBackground": club["sigilBackground"],
                "sigilCharge": club["sigilCharge"]}}

    def emit_chat(self, profile, name, payload):
        self.store.emit(profile, {"channel": "CHAT", "type": name,
                                 "hex": self.chat_codec.envelope(name, payload).hex()})

    def chat_configuration(self, profile):
        self.emit_chat(profile, "CHANNEL_AVAILABLE_NOTIFICATION", {"options": [
            {"channelType": channel, "subscriptionManagedByClient": False, "writable": True,
             "managedByLanguage": False, "rateLimit": 1000} for channel in (2, 3)]})

    def handle_chat(self, profile, name, payload):
        if name in ("JOIN_CHANNEL_REQUEST", "PART_CHANNEL_REQUEST"):
            return  # General and match subscriptions are managed by the service.
        if name not in ("SEND_MESSAGE_TO_CLIENT_REQUEST", "SEND_MESSAGE_TO_CHANNEL_REQUEST"):
            raise ServiceError("CHAT_POLICY", "Chat administration and reports are disabled on this local service")
        text = self.name(payload["message"], 500)
        last = self.store.db.execute("SELECT MAX(created) FROM chat_messages WHERE sender=?", (profile,)).fetchone()[0]
        if last is not None and time.time() - last < 1:
            raise ServiceError("CHAT_RATE_LIMIT", "Wait one second between messages")
        recipient, match_id = None, None
        if name == "SEND_MESSAGE_TO_CLIENT_REQUEST":
            row = self.store.db.execute("SELECT id FROM profiles WHERE nickname=?", (payload["toNickname"],)).fetchone()
            if not row:
                raise ServiceError("PLAYER_UNKNOWN", "Unknown recipient")
            recipient = row["id"]
            self.emit_chat(recipient, "RECEIVE_FROM_CLIENT", {"fromNickname": self.store.profile(profile)["nickname"], "message": text})
        else:
            channel = payload["toChannel"]
            if channel["channelType"] == 2:
                recipients = [row[0] for row in self.store.db.execute("SELECT id FROM profiles")]
            elif channel["channelType"] == 3:
                match, _ = self.profile_match(profile)
                match_id, recipients = match["id"], match["profiles"]
            else:
                raise ServiceError("CHAT_CHANNEL", "Only general and match channels are writable")
            for target in recipients:
                self.emit_chat(target, "RECEIVE_FROM_CHANNEL", {"fromChannel": channel, "message": text,
                               "fromNickname": self.store.profile(profile)["nickname"]})
        self.store.db.execute("INSERT INTO chat_messages(sender,recipient,match_id,message,created) VALUES(?,?,?,?,?)",
                              (profile, recipient, match_id, text, time.time()))

    def tournament_config(self, identity=None):
        settings = self.config["general"].get("tournament", {"enabled": False})
        if not settings["enabled"] or identity is not None and str(identity) != str(settings["id"]):
            raise ServiceError("TOURNAMENT_UNKNOWN", "This tournament is not available")
        return settings

    def tournament_entries(self, settings):
        scores = {}
        for row in self.store.db.execute("SELECT state_json,updated FROM matches"):
            match = json.loads(row["state_json"])
            if match.get("tournament") != settings["id"] or match.get("phase") != "ended":
                continue
            if not settings["start_time"] <= row["updated"] < settings["end_time"]:
                continue
            for side, profile in enumerate(match["profiles"]):
                if profile is None:
                    continue
                outcome = "draw" if match["score"][0] == match["score"][1] else "win" if match["score"][side] > match["score"][1-side] else "loss"
                scores[profile] = scores.get(profile, 0) + settings[outcome + "_points"]
        ranked = sorted(scores, key=lambda p: (-scores[p], self.store.profile(p)["nickname"].casefold()))
        return [(profile, {"player": self.player_summary(profile), "tournamentPoints": scores[profile],
                           "eliminated": False, "currentRank": rank}) for rank, profile in enumerate(ranked, 1)]

    def tournaments(self, profile):
        settings = self.config["general"].get("tournament", {"enabled": False})
        tournaments = []
        if settings["enabled"]:
            entries = self.tournament_entries(settings)
            data = {"tournamentId": str(settings["id"]), "tournamentType": 2,
                    "startTime": settings["start_time"] * 1000, "endTime": settings["end_time"] * 1000,
                    "stadium": settings["stadium"], "closed": time.time() >= settings["end_time"], "price": 0,
                    "podium": [entry for _, entry in entries[:3]], "participantCount": len(entries),
                    "participantInTheRunningCount": len(entries)}
            own = next((entry for identity, entry in entries if identity == profile), None)
            if own:
                data["ownRanking"] = own
            tournaments.append(data)
        self.emit(profile, "OUTSTANDING_TOURNAMENTS", {"tournaments": tournaments, "currentTime": time.time() * 1000})
        self.emit(profile, "PAST_TOURNAMENTS", {"tournaments": [t for t in tournaments if t["closed"]]})

    def tournament_match(self, profile, identity):
        settings = self.tournament_config(identity)
        if not settings["start_time"] <= time.time() < settings["end_time"]:
            raise ServiceError("TOURNAMENT_CLOSED", "This tournament is outside its configured time window")
        match = self.create_match(profile, None, settings["stadium"])
        match["tournament"] = settings["id"]
        self.store.save_match(match)

    def tournament_leaderboard(self, profile, identity):
        entries = self.tournament_entries(self.tournament_config(identity))
        payload = {"tournamentId": str(identity), "entries": [entry for _, entry in entries]}
        own = next((entry for target, entry in entries if target == profile), None)
        if own:
            payload["playerEntry"] = own
        self.emit(profile, "TOURNAMENT_LEADERBOARD", payload)

    def running_tournament_matches(self, profile):
        matches = []
        for row in self.store.db.execute("SELECT state_json FROM matches"):
            match = json.loads(row[0])
            if match.get("tournament") and match["phase"] != "ended":
                matches.append({"matchId": str(match["id"]), "firstPlayerNickname": match["rosters"][0]["nickname"],
                                "secondPlayerNickname": match["rosters"][1]["nickname"]})
        self.emit(profile, "RUNNING_TOURNAMENT_MATCHES", {"runningMatch": matches})

    def spectate(self, profile, payload):
        if self.store.active_match(profile):
            raise ServiceError('PLAYER_BUSY','Finish your own match before spectating')
        if 'matchId' in payload:
            match=self.store.match(int(payload['matchId']))
        else:
            row=self.store.db.execute('SELECT id FROM profiles WHERE nickname=?',(payload.get('playerNickname'),)).fetchone()
            match=self.store.active_match(row[0]) if row else None
        if not match or match['phase']=='ended':
            raise ServiceError('MATCH_UNKNOWN','No running match to spectate')
        self.store.db.execute('INSERT OR REPLACE INTO spectators VALUES(?,?)',(profile,match['id']))
        information=self.match_information(match,1)
        information.pop('side'); information.pop('placementZone')
        self.emit(profile,'MATCH_INFORMATION',information,'MATCH')
        self.emit(profile,'FIELD_STATE',self.field_state(match,2 if match['phase']=='resolution' else None),'MATCH')
        if match['phase']=='resolution': self.emit(profile,'RESOLUTION_SCENARIO',match['scenario'],'MATCH')

    def emit_ranking(self, profile):
        stats=self.store.profile(profile)['statistics']
        self.emit(profile,'RANKING_DATA',{'ranking':{key:stats[key] for key in ('wins','draws','defeats')}})
