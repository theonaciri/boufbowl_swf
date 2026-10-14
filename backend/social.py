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
        options = [{"channelType": 2, "lang": lang, "subscriptionManagedByClient": True,
                    "writable": True, "managedByLanguage": True, "rateLimit": 1}
                   for lang in ("fr", "en", "de", "es")]
        if self.store.active_match(profile) or self.spectator_match(profile):
            options.append({"channelType": 3, "subscriptionManagedByClient": False,
                            "writable": True, "managedByLanguage": False, "rateLimit": 1})
        self.emit_chat(profile, "CHANNEL_AVAILABLE_NOTIFICATION", {"options": options})

    def handle_chat(self, profile, name, payload):
        if name in ("JOIN_CHANNEL_REQUEST", "PART_CHANNEL_REQUEST"):
            channels = payload.get('channel', [])
            if not isinstance(channels,list): channels=[channels]
            for channel in channels:
                if channel.get('channelType') == 2 and channel.get('lang') in ('fr','en','de','es'):
                    language = channel['lang']
                    if name == 'JOIN_CHANNEL_REQUEST':
                        self.store.db.execute('INSERT OR IGNORE INTO chat_subscriptions VALUES(?,?)',(profile,language))
                    else:
                        self.store.db.execute('DELETE FROM chat_subscriptions WHERE profile_id=? AND language=?',(profile,language))
                elif channel.get('channelType') != 3 or not (self.store.active_match(profile) or self.spectator_match(profile)):
                    raise ServiceError('CHAT_CHANNEL','Unknown or unavailable chat channel')
            return
        if name == 'REPORT_REQUEST':
            self.save_report(profile,payload['nickname'],'Reported through original chat')
            if payload.get('reportResult'): self.emit_chat(profile,'REPORT_SUCCESS',{'nickname':payload['nickname']})
            return
        if name not in ("SEND_MESSAGE_TO_CLIENT_REQUEST", "SEND_MESSAGE_TO_CHANNEL_REQUEST"):
            raise ServiceError("CHAT_POLICY", "Use Community to report or block a player")
        self.require_can_chat(profile)
        text = self.name(payload["message"], 500)
        last = self.store.db.execute("SELECT MAX(created) FROM chat_messages WHERE sender=?", (profile,)).fetchone()[0]
        if last is not None and time.time() - last < 1:
            raise ServiceError("CHAT_RATE_LIMIT", "Wait one second between messages")
        recipient, match_id, language = None, None, None
        if name == "SEND_MESSAGE_TO_CLIENT_REQUEST":
            recipient = self.target_player(payload['toNickname'], profile)
            if self.blocked(profile,recipient): raise ServiceError('PLAYER_UNAVAILABLE','This player is unavailable')
            self.emit_chat(recipient, "RECEIVE_FROM_CLIENT", {"fromNickname": self.store.profile(profile)["nickname"], "message": text})
        else:
            channel = dict(payload["toChannel"])
            if channel["channelType"] == 2:
                language = channel.get('lang') or self.store.db.execute('SELECT language FROM presence WHERE profile_id=?',(profile,)).fetchone()[0]
                if language not in ('fr','en','de','es'):
                    raise ServiceError("CHAT_CHANNEL", "Unsupported general chat language")
                channel['lang'] = language
                if not self.store.db.execute('SELECT 1 FROM chat_subscriptions WHERE profile_id=? AND language=?',(profile,language)).fetchone():
                    raise ServiceError('CHAT_CHANNEL','Join this language channel before sending')
                recipients = [r[0] for r in self.store.db.execute('SELECT s.profile_id FROM chat_subscriptions s JOIN presence p ON p.profile_id=s.profile_id WHERE s.language=? AND p.seen>?',(language,time.time()-30))]
            elif channel["channelType"] == 3:
                match = self.store.active_match(profile) or self.spectator_match(profile)
                if not match: raise ServiceError('CHAT_CHANNEL','Join a match before using its channel')
                match_id = match['id']
                recipients = [*match['profiles'], *[r[0] for r in self.store.db.execute('SELECT profile_id FROM spectators WHERE match_id=?',(match_id,))]]
            else:
                raise ServiceError("CHAT_CHANNEL", "Only general and match channels are writable")
            for target in recipients:
                if target and not self.blocked(profile,target):
                    self.emit_chat(target, "RECEIVE_FROM_CHANNEL", {"fromChannel": channel, "message": text,
                                   "fromNickname": self.store.profile(profile)["nickname"]})
        self.store.db.execute("INSERT INTO chat_messages(sender,recipient,match_id,message,created,language) VALUES(?,?,?,?,?,?)",
                              (profile, recipient, match_id, text, time.time(), language))

    def restore_spectating(self, profile, match):
        information=self.match_information(match,1)
        information.pop('side'); information.pop('placementZone'); information['skipIntro']=True
        self.emit(profile,'MATCH_INFORMATION',information,'MATCH')
        self.emit(profile,'FIELD_STATE',self.field_state(match,2 if match['phase']=='resolution' else None),'MATCH')
        if match['phase']=='resolution': self.emit(profile,'RESOLUTION_SCENARIO',match['scenario'],'MATCH')

    def stop_spectating(self, profile):
        row=self.store.db.execute('SELECT match_id FROM spectators WHERE profile_id=?',(profile,)).fetchone()
        if row:
            self.broadcast(self.store.match(row[0]), 'MATCH_SPECTATOR_PART_NOTIFICATION', {'nickname': self.store.profile(profile)['nickname']})
            self.store.db.execute('DELETE FROM spectators WHERE profile_id=?',(profile,))
            self.emit_chat(profile,'CHANNEL_UNAVAILABLE_NOTIFICATION',{'channels':[{'channelType':3}]})
            self.store.emit(profile,{'channel':'COMMUNITY','type':'SPECTATING_STOPPED'})

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
        if any(self.blocked(profile,p) for p in match['profiles']):
            raise ServiceError('PLAYER_UNAVAILABLE','This match is unavailable')
        self.leave_queue(profile)
        self.cancel_challenges(profile)
        previous=self.spectator_match(profile)
        if previous and previous['id']!=match['id']: self.stop_spectating(profile)
        self.store.db.execute('INSERT OR REPLACE INTO spectators VALUES(?,?)',(profile,match['id']))
        self.store.db.execute('INSERT OR IGNORE INTO replay_access VALUES(?,?)',(profile,match['id']))
        self.chat_configuration(profile)
        self.restore_spectating(profile,match)
        if not previous or previous['id']!=match['id']:
            self.broadcast(match,'MATCH_SPECTATOR_JOIN_NOTIFICATION',{'nickname':self.store.profile(profile)['nickname']})

    def emit_ranking(self, profile):
        self.emit(profile,'RANKING_DATA',{'ranking':self.ranking_info(profile)})
