"""Authenticated community, history, presence and ranking queries for the client."""
import json
import hashlib
import time
from backend.storage import ServiceError

LANGUAGES = ('fr', 'en', 'de', 'es')


class Community:
    def touch(self, profile, language=None):
        if language is not None and language not in LANGUAGES:
            raise ServiceError('CHAT_CHANNEL', 'Choose fr, en, de or es')
        row = self.store.db.execute('SELECT language FROM presence WHERE profile_id=?', (profile,)).fetchone()
        fresh = row is None
        language = language or (row[0] if row else 'en')
        self.store.db.execute('INSERT INTO presence VALUES(?,?,?) ON CONFLICT(profile_id) DO UPDATE SET seen=excluded.seen,language=excluded.language',
                              (profile, time.time(), language))
        # Preserve an existing selection of channels across restarts and logins.
        if fresh:
            self.store.db.execute('INSERT INTO chat_subscriptions VALUES(?,?)', (profile, language))

    def channel_state(self, profile):
        row=self.store.db.execute('SELECT language FROM presence WHERE profile_id=?',(profile,)).fetchone()
        return {'language':row[0] if row else 'en', 'subscriptions':[r[0] for r in self.store.db.execute('SELECT language FROM chat_subscriptions WHERE profile_id=? ORDER BY language',(profile,))]}

    def blocked(self, first, second):
        return bool(second and self.store.db.execute('SELECT 1 FROM blocks WHERE (owner=? AND target=?) OR (owner=? AND target=?)',
                                                     (first, second, second, first)).fetchone())

    def target_player(self, nickname, profile=None):
        row = self.store.db.execute('SELECT id FROM profiles WHERE nickname=?', (self.name(nickname),)).fetchone()
        if not row or row[0] == profile:
            raise ServiceError('PLAYER_UNKNOWN', 'Choose another player nickname')
        return row[0]

    def spectator_match(self, profile):
        row = self.store.db.execute('SELECT match_id FROM spectators WHERE profile_id=?', (profile,)).fetchone()
        if row:
            match = self.store.match(row[0])
            if match['phase'] != 'ended':
                return match
        return None

    def presence_data(self, target):
        row = self.store.db.execute('SELECT seen FROM presence WHERE profile_id=?', (target,)).fetchone()
        online = bool(row and row[0] > time.time() - 30)
        match = self.store.active_match(target) if online else None
        return {'nickname': self.store.profile(target)['nickname'], 'online': online,
                'match': str(match['id']) if match else None}

    def friends_data(self, profile):
        friends, incoming, outgoing = [], [], []
        for row in self.store.db.execute('SELECT * FROM friendships WHERE requester=? OR target=? ORDER BY created', (profile, profile)):
            target = row['target'] if row['requester'] == profile else row['requester']
            data = self.presence_data(target)
            if row['status'] == 'accepted': friends.append(data)
            elif row['target'] == profile: incoming.append(data)
            else: outgoing.append(data)
        blocked = [self.presence_data(row[0]) for row in self.store.db.execute('SELECT target FROM blocks WHERE owner=? ORDER BY created', (profile,))]
        return {'friends': friends, 'incoming': incoming, 'outgoing': outgoing, 'blocked': blocked}

    def friend_action(self, profile, action, nickname):
        target = self.target_player(nickname, profile)
        pair = (profile, target, target, profile)
        if action == 'block':
            self.store.db.execute('INSERT OR IGNORE INTO blocks VALUES(?,?,?)', (profile, target, time.time()))
            self.store.db.execute('DELETE FROM friendships WHERE (requester=? AND target=?) OR (requester=? AND target=?)', pair)
            for offer in self.store.db.execute("SELECT * FROM challenges WHERE status='pending' AND ((host=? AND guest=?) OR (host=? AND guest=?))", pair).fetchall():
                self.cancel_offer(offer)
            # A newly blocked spectator leaves the room immediately.
            for spectator, player in ((profile, target), (target, profile)):
                room = self.spectator_match(spectator)
                if room and player in room['profiles']: self.stop_spectating(spectator)
        elif action == 'unblock':
            self.store.db.execute('DELETE FROM blocks WHERE owner=? AND target=?', (profile, target))
        elif action in ('remove', 'reject', 'cancel'):
            if action == 'remove':
                self.store.db.execute('DELETE FROM friendships WHERE (requester=? AND target=?) OR (requester=? AND target=?)', pair)
            else:
                requester, recipient = (target, profile) if action == 'reject' else (profile, target)
                self.store.db.execute("DELETE FROM friendships WHERE requester=? AND target=? AND status='pending'", (requester, recipient))
        elif action in ('add', 'accept'):
            if self.blocked(profile, target): raise ServiceError('PLAYER_UNAVAILABLE', 'This player is unavailable')
            incoming = self.store.db.execute('SELECT status FROM friendships WHERE requester=? AND target=?', (target, profile)).fetchone()
            if incoming:
                self.store.db.execute("UPDATE friendships SET status='accepted' WHERE requester=? AND target=?", (target, profile))
            elif action == 'accept': raise ServiceError('FRIEND_REQUEST', 'No incoming request from this player')
            else:
                exists=self.store.db.execute('SELECT 1 FROM friendships WHERE requester=? AND target=?',(profile,target)).fetchone()
                for participant in (profile,target):
                    count = self.store.db.execute('SELECT COUNT(*) FROM friendships WHERE requester=? OR target=?', (participant,participant)).fetchone()[0]
                    if not exists and count >= 200: raise ServiceError('FRIEND_LIMIT', 'Friend list limit reached')
                self.store.db.execute("INSERT OR IGNORE INTO friendships VALUES(?,?,'pending',?)", (profile, target, time.time()))
        else: raise ServiceError('FRIEND_ACTION', 'Unknown friend action')
        return self.friends_data(profile)

    def rankings(self):
        players = [self.store.profile(row[0]) for row in self.store.db.execute('SELECT id FROM profiles')]
        players.sort(key=lambda p: (-p['statistics']['rating'], p['nickname'].casefold(), p['id']))
        return [{'index': i, 'rank': i+1, 'player': self.player_summary(p['id']),
                 'wins': p['statistics']['wins'], 'draws': p['statistics']['draws'],
                 'losses': p['statistics']['defeats'], 'rating': p['statistics']['rating']} for i,p in enumerate(players)]

    @staticmethod
    def page(body):
        value = body.get('offset', 0)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ServiceError('PAGE_INVALID', 'Offset must be a nonnegative integer')
        return value

    def history(self, profile, offset=0):
        rows = self.store.db.execute('SELECT m.state_json,m.updated FROM matches m WHERE m.id IN (SELECT match_id FROM participants WHERE profile_id=? UNION SELECT match_id FROM replay_access WHERE profile_id=?) ORDER BY m.id DESC LIMIT 21 OFFSET ?', (profile,profile,offset)).fetchall()
        result = []
        for row in rows[:20]:
            match = json.loads(row[0]); side = self.side(match,profile) if profile in match['profiles'] else None
            turns = self.store.db.execute('SELECT COUNT(*) FROM turns WHERE match_id=?', (match['id'],)).fetchone()[0]
            result.append({'id': str(match['id']), 'players': [r['nickname'] for r in match['rosters']],
                           'stadium': match['stadium'], 'score': match['score'], 'phase': match['phase'],
                           'side': side, 'created': match.get('created'), 'ended': match.get('ended',row[1] if match['phase']=='ended' else None),
                           'given_up': match.get('given_up'), 'turns': turns, 'replay_available': turns>0 and match['phase']=='ended'})
        return {'matches': result, 'offset': offset, 'more': len(rows)>20}

    def community(self, body):
        with self.store.transaction():
            profile = self.store.authenticate(body.get('session'))
            self.touch(profile)
            action = body.get('action','overview'); result = {}
            receipt = body.get('request_id') if action in ('friend','spectate','stop_spectating','channels','message','report') else None
            digest = None
            if receipt is not None:
                if not isinstance(receipt,str) or not 1<=len(receipt)<=100: raise ServiceError('REQUEST_ID','Invalid community request ID')
                receipt='community:'+receipt
                digest=hashlib.sha256(json.dumps(body,sort_keys=True,separators=(',',':')).encode()).hexdigest()
                previous=self.store.db.execute('SELECT * FROM commands WHERE profile_id=? AND request_id=?',(profile,receipt)).fetchone()
                if previous:
                    if previous['request_hash']!=digest: raise ServiceError('REQUEST_CONFLICT','A request ID cannot be reused for another action')
                    return json.loads(previous['response_json'])
            if action == 'overview':
                result = self.friends_data(profile)
                result['channels'] = [r[0] for r in self.store.db.execute('SELECT language FROM chat_subscriptions WHERE profile_id=? ORDER BY language', (profile,))]
                result['language'] = self.store.db.execute('SELECT language FROM presence WHERE profile_id=?', (profile,)).fetchone()[0]
                result['spectating'] = str(self.spectator_match(profile)['id']) if self.spectator_match(profile) else None
            elif action == 'friend': result = self.friend_action(profile,body['verb'],body['nickname'])
            elif action == 'rankings':
                offset = self.page(body); rows = self.rankings()
                target = body.get('nickname')
                if target:
                    target = self.name(target)
                    index = next((i for i,r in enumerate(rows) if r['player']['nickname'].casefold()==target.casefold()), None)
                    if index is None: raise ServiceError('PLAYER_UNKNOWN', 'Unknown ranked player')
                    offset = (index//20)*20
                result = {'rows': rows[offset:offset+20], 'offset': offset, 'total':len(rows), 'more': offset+20<len(rows)}
            elif action == 'history': result = self.history(profile,self.page(body))
            elif action == 'live':
                result['matches'] = []
                for row in self.store.db.execute('SELECT state_json FROM matches ORDER BY id DESC'):
                    match=json.loads(row[0])
                    if match['phase']=='ended' or any(self.blocked(profile,p) for p in match['profiles']): continue
                    result['matches'].append({'id':str(match['id']),'players':[r['nickname'] for r in match['rosters']], 'stadium':match['stadium'],'score':match['score'],'turn':match['turn']})
                offset=self.page(body); entries=result['matches']; result.update(matches=entries[offset:offset+20],offset=offset,more=offset+20<len(entries))
            elif action == 'spectate':
                self.spectate(profile,{'matchId':body['match']} if body.get('match') else {'playerNickname':body['nickname']})
            elif action == 'stop_spectating': self.stop_spectating(profile)
            elif action == 'channels':
                languages = body.get('languages')
                if not isinstance(languages,list) or not languages or any(l not in LANGUAGES for l in languages):
                    raise ServiceError('CHAT_CHANNEL','Select one or more supported languages')
                preferred=body.get('language',languages[0])
                if preferred not in languages: raise ServiceError('CHAT_CHANNEL','Preferred language must be subscribed')
                self.touch(profile,preferred)
                self.store.db.execute('DELETE FROM chat_subscriptions WHERE profile_id=?',(profile,))
                self.store.db.executemany('INSERT INTO chat_subscriptions VALUES(?,?)',[(profile,l) for l in sorted(set(languages))])
                self.chat_configuration(profile)
                result.update(self.channel_state(profile))
            elif action == 'message':
                self.handle_chat(profile,'SEND_MESSAGE_TO_CLIENT_REQUEST',{'toNickname':body['nickname'],'message':body['message']})
            elif action == 'messages':
                target=self.target_player(body['nickname'],profile)
                if self.blocked(profile,target): raise ServiceError('PLAYER_UNAVAILABLE','This player is unavailable')
                before=body.get('before',2**63-1)
                if not isinstance(before,int) or isinstance(before,bool) or before<=0 or before>2**63-1: raise ServiceError('PAGE_INVALID','Invalid message cursor')
                rows=self.store.db.execute('SELECT * FROM chat_messages WHERE id<? AND ((sender=? AND recipient=?) OR (sender=? AND recipient=?)) ORDER BY id DESC LIMIT 50',(before,profile,target,target,profile)).fetchall()
                result['messages']=[{'id':r['id'],'from':self.store.profile(r['sender'])['nickname'],'message':r['message'],'created':r['created']} for r in reversed(rows)]
                result['before']=rows[-1]['id'] if rows else None
            elif action == 'report': self.save_report(profile,body['nickname'],body['reason'])
            else: raise ServiceError('COMMUNITY_ACTION','Unknown community action')
            response={'ok':True,**result}
            if receipt: self.store.db.execute('INSERT INTO commands VALUES(?,?,?,?)',(profile,receipt,digest,json.dumps(response)))
            return response

    def save_report(self, profile, nickname, reason):
        target=self.target_player(nickname,profile); reason=self.name(reason,500)
        last=self.store.db.execute('SELECT MAX(created) FROM reports WHERE reporter=?',(profile,)).fetchone()[0]
        if last and time.time()-last<60: raise ServiceError('REPORT_RATE_LIMIT','Wait one minute between reports')
        self.store.db.execute('INSERT INTO reports(reporter,target,reason,created) VALUES(?,?,?,?)',(profile,target,reason,time.time()))
