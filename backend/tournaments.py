"""Durable scheduled free tournaments using the original client lifecycle."""
from copy import deepcopy
from datetime import datetime, timedelta
import json
import math
import time
from zoneinfo import ZoneInfo
from backend.results import result_kind
from backend.storage import ServiceError
from tools.game_config import STADIUMS, resolve_stadium

# Original G/I/C reward artwork; currencies are local to this replacement.
REWARD_BALANCES = {1: (20,10,10), 2: (10,10,10), 3: (0,5,10), 4: (0,0,10)}


def calendar_weekly(settings):
    return settings.get('repeat_seconds') == 604800 and bool(settings.get('timezone'))


def occurrence_window(settings, number):
    """Keep weekly wall-clock times stable through daylight saving changes."""
    if calendar_weekly(settings):
        zone = ZoneInfo(settings['timezone'])
        return tuple(int((datetime.fromtimestamp(settings[key], zone) + timedelta(weeks=number)).timestamp())
                     for key in ('start_time', 'end_time'))
    offset = number * settings.get('repeat_seconds', 0)
    return settings['start_time'] + offset, settings['end_time'] + offset


class Tournaments:
    def public_tournaments(self, body=None):
        """Public schedule and scores; website RSVPs never enter matchmaking."""
        body = body or {}
        action = body.get('action', 'list')
        if action not in ('list', 'participate', 'logout'):
            raise ServiceError('TOURNAMENT_ACTION', 'Action de tournoi inconnue.')
        with self.store.transaction():
            profile = self.store.authenticate(body['session']) if body.get('session') else None
            if action == 'logout' and profile:
                self.store.db.execute('DELETE FROM sessions WHERE token_hash=?', (self.store.digest(body['session']),))
                profile = None
            self.maintain_tournaments()
            enabled = self.tournament_settings()['enabled']
            if action == 'participate':
                if profile is None:
                    raise ServiceError('SESSION_INVALID', 'Connectez-vous avec votre compte de jeu.')
                attending = body.get('participating')
                if not isinstance(attending, bool):
                    raise ServiceError('TOURNAMENT_INPUT', 'Une confirmation de participation est requise.')
                if body.get('tournament_id') is None:
                    raise ServiceError('TOURNAMENT_UNKNOWN', 'Choisissez un tournoi.')
                settings = self.tournament_config(body['tournament_id'])
                if not enabled or not time.time() < settings['end_time']:
                    raise ServiceError('TOURNAMENT_CLOSED', 'Les confirmations sont closes pour ce tournoi.')
                if attending:
                    rating = self.store.profile(profile)['statistics']['rating']
                    if not settings.get('min_rating', 0) <= rating <= settings.get('max_rating', 100000):
                        raise ServiceError('TOURNAMENT_RATING', 'Votre cote ne correspond pas aux limites de ce tournoi.')
                    self.store.db.execute('INSERT OR IGNORE INTO tournament_intentions VALUES(?,?,?)',
                                          (settings['id'], profile, time.time()))
                else:
                    self.store.db.execute('DELETE FROM tournament_intentions WHERE tournament_id=? AND profile_id=?',
                                          (settings['id'], profile))
            events = []
            rows = []
            if enabled:
                current = self.store.db.execute("SELECT * FROM tournaments WHERE phase IN ('open','closing') ORDER BY CASE phase WHEN 'open' THEN 0 ELSE 1 END,json_extract(settings_json,'$.start_time') LIMIT 1").fetchone()
                upcoming = self.store.db.execute("SELECT * FROM tournaments WHERE phase='upcoming' ORDER BY json_extract(settings_json,'$.start_time') LIMIT 1").fetchone()
                rows = [row for row in (current, upcoming) if row is not None]
            for row in rows:
                cfg = json.loads(row['settings_json'])
                entries = self.tournament_entries(cfg) if row['phase'] != 'upcoming' else []
                match_rules = resolve_stadium(self.config, STADIUMS[cfg['stadium'] - 1])['match']
                match_rules.update(cfg.get('match_rules', {}))
                intentions = self.store.db.execute('SELECT COUNT(*),MAX(profile_id=?) FROM tournament_intentions WHERE tournament_id=?',
                                                   (profile, row['id'])).fetchone()
                events.append({
                    'id': str(row['id']), 'name': cfg.get('name') or 'Coupe du Boufbowl',
                    'phase': row['phase'], 'start_time': cfg['start_time'], 'end_time': cfg['end_time'],
                    'stadium': STADIUMS[cfg['stadium'] - 1], 'format': cfg.get('format', 'league'),
                    'min_rating': cfg.get('min_rating', 0), 'max_rating': cfg.get('max_rating', 100000),
                    'points': {key: cfg[key + '_points'] for key in ('win', 'draw', 'loss')},
                    'match_rules': {key: match_rules[key] for key in ('turns_per_match', 'turns_per_period', 'planning_seconds',
                                    'placement_seconds', 'class_ability_uses', 'regenerate_between_turns')},
                    'qualification_seconds': cfg.get('qualification_seconds'), 'qualifying_top': cfg.get('qualifying_top'),
                    'rounds': self.admin_rounds(cfg), 'participants': len(entries),
                    'interested': intentions[0], 'participating': bool(intentions[1]),
                    'standings': [{'rank': entry['currentRank'], 'nickname': entry['player']['nickname'],
                                   'club': entry['player']['club']['clubName'], 'points': entry['tournamentPoints'],
                                   'eliminated': entry['eliminated']} for _, entry in entries[:10]],
                })
            return {'ok': True, 'tournaments': events, 'generated_at': time.time(),
                    'viewer': {'nickname': self.store.profile(profile)['nickname']} if profile else None}

    def schedule_tournaments(self):
        cfg = self.tournament_settings()
        if not cfg['enabled']: return
        now = time.time(); repeat = cfg.get('repeat_seconds',0)
        if calendar_weekly(cfg):
            zone = ZoneInfo(cfg['timezone'])
            index = max(0, (datetime.fromtimestamp(now, zone).date() -
                            datetime.fromtimestamp(cfg['start_time'], zone).date()).days // 7)
        else:
            index = max(0, int((now-cfg['start_time'])//repeat)) if repeat else 0
        indices = range(index,index+cfg.get('upcoming_count',2)+1) if repeat else (0,)
        rotation = cfg.get('stadium_rotation', [cfg['stadium']])
        rotation = [n for n in rotation if self.config['stadiums'][STADIUMS[n-1]]['enabled']]
        if not rotation: return
        for number in indices:
            settings = deepcopy(cfg)
            start, end = occurrence_window(cfg, number)
            settings.update(id=cfg['id']+number, start_time=start,
                            end_time=end, stadium=rotation[number%len(rotation)])
            previous=self.store.db.execute('SELECT settings_json FROM tournaments WHERE id<? ORDER BY id DESC LIMIT 1',(settings['id'],)).fetchone()
            if previous and repeat and not calendar_weekly(cfg):
                previous=json.loads(previous[0]);gap=repeat-(cfg['end_time']-cfg['start_time'])
                same_series=previous.get('series_id')==settings.get('series_id')
                start=max(settings['start_time'],previous['end_time']+(gap if same_series else 0))
                settings.update(start_time=start,end_time=start+(cfg['end_time']-cfg['start_time']))
            phase = 'upcoming' if now < settings['start_time'] else 'open' if now < settings['end_time'] else 'closing'
            self.store.db.execute('INSERT OR IGNORE INTO tournaments(id,settings_json,phase) VALUES(?,?,?)',
                                  (settings['id'],json.dumps(settings),phase))

    def tournament_config(self, identity=None):
        if identity is not None and (isinstance(identity,bool) or not isinstance(identity,(int,str)) or
                not str(identity).isdigit() or not 0 <= int(identity) <= 9223372036854775807):
            raise ServiceError('TOURNAMENT_UNKNOWN','Invalid tournament identifier')
        self.schedule_tournaments()
        if identity is None:
            row = self.store.db.execute("SELECT settings_json FROM tournaments WHERE phase='open' ORDER BY id LIMIT 1").fetchone()
        else:
            row = self.store.db.execute('SELECT settings_json FROM tournaments WHERE id=?',(str(identity),)).fetchone()
        if not row: raise ServiceError('TOURNAMENT_UNKNOWN','This tournament is not available')
        return json.loads(row[0])

    def current_tournament_id(self):
        if not self.tournament_settings()['enabled']: return None
        now=time.time()
        row=self.store.db.execute("SELECT id FROM tournaments WHERE phase='open' AND json_extract(settings_json,'$.start_time')<=? AND json_extract(settings_json,'$.end_time')>? ORDER BY id LIMIT 1",(now,now)).fetchone()
        return str(row[0]) if row else None

    def tournament_entries(self, settings):
        row=self.store.db.execute('SELECT final_entries_json FROM tournaments WHERE id=?',(settings['id'],)).fetchone()
        if row and row[0] is not None: return [(p,e) for p,e in json.loads(row[0])]
        scores={r[0]:0 for r in self.store.db.execute('SELECT profile_id FROM tournament_participants WHERE tournament_id=?',(settings['id'],))}
        for row in self.store.db.execute('SELECT state_json FROM matches'):
            match=json.loads(row[0])
            if (match.get('tournament')!=settings['id'] or match['phase']!='ended' or
                    result_kind(match)!='ranked' or match.get('source')!='tournament'): continue
            if not settings['start_time'] <= match['created'] < settings['end_time']: continue
            for side,profile in enumerate(match['profiles']):
                outcome='draw' if match['score'][0]==match['score'][1] else 'win' if match['score'][side]>match['score'][1-side] else 'loss'
                scores[profile]=scores.get(profile,0)+settings[outcome+'_points']
        ranked=sorted(scores,key=lambda p:(-scores[p],self.store.profile(p)['nickname'].casefold(),p))
        return self.knockout_order(settings,[(p,{'player':self.player_summary(p),'tournamentPoints':scores[p], 'eliminated':False,'currentRank':rank}) for rank,p in enumerate(ranked,1)])

    def tournament_packet(self, row, profile):
        settings=json.loads(row['settings_json']);entries=self.tournament_entries(settings)
        data={'tournamentId':str(settings['id']),'tournamentType':settings.get('type',2),
              'startTime':settings['start_time']*1000,'endTime':settings['end_time']*1000,
              'stadium':settings['stadium'],'closed':row['phase']=='ended','price':0,
              'rewards':settings.get('rewards',[]),'rounds':self.round_slots(settings),'podium':[e for _,e in entries[:3]],
              'participantCount':len(entries),'participantInTheRunningCount':sum(not e['eliminated'] for _,e in entries)}
        own=next((e for p,e in entries if p==profile),None)
        if own: data['ownRanking']=own
        rewarded=[e for _,e in entries if 'reward' in e]
        if rewarded: data['lastRewarded']=rewarded[-1]
        return data

    def tournaments(self, profile):
        self.maintain_tournaments()
        self.store.db.execute('INSERT OR IGNORE INTO tournament_watchers VALUES(?)',(profile,))
        self.send_tournaments(profile)

    def send_tournaments(self, profile):
        rows=self.store.db.execute('SELECT * FROM tournaments ORDER BY id DESC').fetchall()
        outstanding=[self.tournament_packet(r,profile) for r in reversed(rows) if r['phase'] in ('upcoming','open')]
        past=[self.tournament_packet(r,profile) for r in rows if r['phase'] in ('closing','ended')][:self.tournament_settings().get('past_count',10)]
        packet=self.packet('OUTSTANDING_TOURNAMENTS',{'tournaments':outstanding,'currentTime':time.time()*1000})
        packet['round_states']=self.tournament_round_metadata(profile,rows)
        self.store.emit(profile,packet)
        self.emit(profile,'PAST_TOURNAMENTS',{'tournaments':past})

    def tournament_match(self, profile, identity=None):
        self.maintain_tournaments()
        if not self.tournament_settings()['enabled']:
            raise ServiceError('TOURNAMENT_CLOSED','Tournament entry is disabled')
        if identity is None and self.current_tournament_id() is None:
            raise ServiceError('TOURNAMENT_CLOSED','No tournament is running yet')
        settings=self.tournament_config(identity)
        if not settings['start_time'] <= time.time() < settings['end_time']:
            raise ServiceError('TOURNAMENT_CLOSED','This tournament is outside its entry window')
        self.knockout_eligible(profile,settings)
        self.join_queue(profile,[settings['stadium']],tournament=settings['id'])

    def register_tournament(self, profile, settings):
        row,data=self.round_state(settings['id'])
        if row and row['round']>0 and profile not in data.get('entered',[]):
            data.setdefault('entered',[]).append(profile)
            self.store.db.execute('UPDATE tournament_rounds SET eligible_json=? WHERE tournament_id=? AND round=?',(json.dumps(data),settings['id'],row['round']))
        self.store.db.execute('INSERT OR IGNORE INTO tournament_participants VALUES(?,?,?)',(settings['id'],profile,time.time()))
        self.store.db.execute('INSERT OR IGNORE INTO tournament_watchers VALUES(?)',(profile,))

    def tournament_leaderboard(self, profile, identity):
        self.maintain_tournaments()
        entries=self.tournament_entries(self.tournament_config(identity))
        payload={'tournamentId':str(identity),'entries':[e for _,e in entries]}
        own=next((e for p,e in entries if p==profile),None)
        if own: payload['playerEntry']=own
        self.emit(profile,'TOURNAMENT_LEADERBOARD',payload)

    def finalize_tournament(self, row):
        settings=json.loads(row['settings_json']);entries=self.tournament_entries(settings)
        # Searching alone earns no reward; a completed tournament game is required.
        played=set()
        for match_row in self.store.db.execute('SELECT state_json FROM matches'):
            match=json.loads(match_row[0])
            if (match.get('tournament')==settings['id'] and match['phase']=='ended' and result_kind(match)=='ranked'
                    and match.get('source')=='tournament' and settings['start_time']<=match['created']<settings['end_time']):
                played.update(match['profiles'])
        if settings.get('format')=='elimination':
            _,bracket=self.round_state(settings['id'])
            if not bracket.get('champions'):played=set()
        rewards=settings.get('rewards',[])
        for profile,entry in entries:
            rank=entry['currentRank'];threshold=0 if rank==1 else 1 if rank<=3 else 2 if rank<=10 else 3 if rank<=math.ceil(len(entries)/3) else None
            if profile not in played or threshold is None or len(rewards)<=threshold: continue
            reward=rewards[threshold];entry['reward']=reward
            balances=dict(zip(('glory','influence','coins'),REWARD_BALANCES[reward]))
            if rank==1 and 'prizes' in settings: balances=settings['prizes']
            added=self.store.db.execute('INSERT OR IGNORE INTO tournament_rewards VALUES(?,?,?,?,?)',(settings['id'],profile,reward,json.dumps(balances),time.time())).rowcount
            if added:
                stats=self.store.profile(profile)['statistics'];wallet=stats.setdefault('tournament_wallet',{'glory':0,'influence':0,'coins':0})
                for key,value in balances.items():wallet[key]+=value
                self.store.db.execute('UPDATE profiles SET statistics_json=? WHERE id=?',(json.dumps(stats),profile))
        self.store.db.execute("UPDATE tournaments SET phase='ended',final_entries_json=?,finalized=? WHERE id=?",(json.dumps(entries),time.time(),settings['id']))

    def maintain_tournaments(self):
        self.schedule_tournaments();now=time.time();changed=False
        for row in self.store.db.execute("SELECT * FROM tournaments WHERE phase!='ended' ORDER BY id").fetchall():
            row=self.store.db.execute('SELECT * FROM tournaments WHERE id=?',(row['id'],)).fetchone()
            settings=json.loads(row['settings_json']);old=row['phase']
            round_before=self.round_state(settings['id'])[0]
            finished=self.update_tournament_rounds(settings)
            settings=json.loads(self.store.db.execute('SELECT settings_json FROM tournaments WHERE id=?',(settings['id'],)).fetchone()[0])
            if json.dumps(settings)!=row['settings_json']:changed=True
            round_after=self.round_state(settings['id'])[0]
            if (tuple(round_before) if round_before else None)!=(tuple(round_after) if round_after else None):changed=True
            phase='upcoming' if now<settings['start_time'] else 'open' if now<settings['end_time'] else 'closing'
            if finished:phase='closing'
            if phase=='closing':
                queued=self.store.db.execute('SELECT profile_id FROM matchmaking_queue WHERE tournament_id=?',(str(settings['id']),)).fetchall()
                self.store.db.execute('DELETE FROM matchmaking_queue WHERE tournament_id=?',(str(settings['id']),))
                for p in queued:self.emit(p[0],'TOURNAMENT_OFFER_CANCELED',{})
                active=any(json.loads(m[0]).get('tournament')==settings['id'] and json.loads(m[0])['phase']!='ended' for m in self.store.db.execute('SELECT state_json FROM matches'))
                if not active:
                    self.finalize_tournament(row);phase='ended'
                else:
                    self.store.db.execute('UPDATE tournaments SET phase=? WHERE id=?',(phase,settings['id']))
                    self.shift_upcoming_tournaments(settings['id'],max(now+60,settings['end_time']))
            elif phase!=old:self.store.db.execute('UPDATE tournaments SET phase=? WHERE id=?',(phase,settings['id']))
            if phase!=old:
                changed=True
                if phase=='ended':
                    for p in self.store.db.execute('SELECT profile_id FROM tournament_watchers').fetchall():
                        self.emit(p[0],'TOURNAMENT_CLOSED',{'tournamentId':str(settings['id']),'tournamentType':settings.get('type',2),'startTime':settings['start_time']*1000})
        if changed:
            for p in self.store.db.execute('SELECT profile_id FROM tournament_watchers').fetchall():self.send_tournaments(p[0])

    def running_tournament_matches(self, profile):
        matches=[]
        for row in self.store.db.execute('SELECT state_json FROM matches'):
            match=json.loads(row[0])
            if match.get('tournament') is not None and match['phase']!='ended':
                matches.append({'matchId':str(match['id']),'firstPlayerNickname':match['rosters'][0]['nickname'],'secondPlayerNickname':match['rosters'][1]['nickname']})
        self.emit(profile,'RUNNING_TOURNAMENT_MATCHES',{'runningMatch':matches})
