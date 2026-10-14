"""Qualification and knockout rounds, with persisted eligibility and late finish handling."""
import json
import math
import time
from backend.storage import ServiceError
from backend.results import result_kind


class TournamentRounds:
    def round_matches(self, identity, number):
        return [m for r in self.store.db.execute('SELECT state_json FROM matches')
                if (m:=json.loads(r[0])).get('tournament')==identity and m.get('tournament_round',0)==number and m.get('source')=='tournament' and result_kind(m)=='ranked']

    def round_state(self, identity):
        row=self.store.db.execute('SELECT * FROM tournament_rounds WHERE tournament_id=? ORDER BY round DESC LIMIT 1',(identity,)).fetchone()
        return (row,json.loads(row['eligible_json'])) if row else (None,{})

    def knockout_eligible(self, profile, settings):
        if settings.get('format','league')!='elimination':return
        self.update_tournament_rounds(settings)
        row,data=self.round_state(settings['id']);now=time.time()
        if not row or row['phase']!='open':raise ServiceError('TOURNAMENT_ROUND_WAIT','Wait for the next tournament round')
        slot=data['slot']
        if not slot['start']<=now<slot['end']:raise ServiceError('TOURNAMENT_ROUND_WAIT','This round is not accepting matches')
        if row['round']==0:return
        if profile not in data['eligible']:raise ServiceError('TOURNAMENT_ELIMINATED','You did not qualify or were eliminated')
        if profile in data.get('byes',[]):raise ServiceError('TOURNAMENT_BYE','You advance automatically; wait for the next round')
        if any(profile in m['profiles'] for m in self.round_matches(settings['id'],row['round'])):
            raise ServiceError('TOURNAMENT_ROUND_PLAYED','Your match for this round is already recorded')

    def knockout_pair_allowed(self, identity, first, second):
        settings=self.tournament_config(identity)
        if settings.get('format','league')!='elimination':return True
        row,data=self.round_state(settings['id'])
        if not row or row['phase']!='open' or not data['slot']['start']<=time.time()<data['slot']['end']:return False
        return row['round']==0 or any(set(pair)=={first,second} for pair in data['pairs'])

    def round_winner(self, match, priority):
        if match['score'][0]!=match['score'][1]:return match['profiles'][0 if match['score'][0]>match['score'][1] else 1]
        # Public documented tie rule: qualification seed, then stable profile ID.
        return min(match['profiles'],key=lambda p:(priority.index(p) if p in priority else len(priority),p))

    def update_tournament_rounds(self, settings):
        if settings.get('format','league')!='elimination':return False
        identity=settings['id'];now=time.time();row,data=self.round_state(identity)
        if not row:
            data={'slot':{'start':settings['start_time'],'end':settings['start_time']+settings['qualification_seconds']},'eligible':[],'eliminated':{},'pairs':[],'byes':[],'seed_order':[]}
            self.store.db.execute("INSERT INTO tournament_rounds VALUES(?,0,'open',?)",(identity,json.dumps(data)))
            row,data=self.round_state(identity)
        if row['phase']=='finished':return True
        number=row['round'];matches=self.round_matches(identity,number)
        if now<data['slot']['start']:return False
        if now<data['slot']['end']:return False
        queued=[r[0] for r in self.store.db.execute('SELECT profile_id FROM matchmaking_queue WHERE tournament_id=?',(str(identity),))]
        self.store.db.execute('DELETE FROM matchmaking_queue WHERE tournament_id=?',(str(identity),))
        for profile in queued:self.emit(profile,'TOURNAMENT_OFFER_CANCELED',{})
        if any(m['phase']!='ended' for m in matches):
            projection=math.ceil(now/60)*60+(settings['round_count']-number)*settings['round_seconds']
            if projection>settings['end_time']:
                settings.setdefault('scheduled_end_time',settings['end_time'])
                settings['end_time']=projection
                self.store.db.execute('UPDATE tournaments SET settings_json=? WHERE id=?',(json.dumps(settings),identity))
                self.shift_upcoming_tournaments(identity,projection)
            if row['phase']!='closing':self.store.db.execute("UPDATE tournament_rounds SET phase='closing' WHERE tournament_id=? AND round=?",(identity,number))
            return False
        if number==0:
            entries=self.tournament_entries(settings);played={p for m in matches for p in m['profiles']}
            eligible=[p for p,_ in entries if p in played][:settings['qualifying_top']]
            data['seed_order']=eligible[:]
            data['eliminated']={p:0 for p,_ in entries if p not in eligible}
        else:
            eligible=list(data['byes'])
            for pair in data['pairs']:
                completed=next((m for m in matches if set(m['profiles'])==set(pair)),None)
                if completed:winner=self.round_winner(completed,data['seed_order']);eligible.append(winner)
                else:
                    # No played match means no advancement; entering once alone at cutoff earns a walkover.
                    ready=[p for p in pair if p in queued and self.store.db.execute('SELECT 1 FROM presence WHERE profile_id=? AND seen>?',(p,now-30)).fetchone()]
                    winner=ready[0] if len(ready)==1 else None
                    if winner:eligible.append(winner)
                for p in pair:
                    if p not in eligible:data['eliminated'][p]=number
        data['eligible']=eligible
        if len(eligible)<=1 or number>=settings['round_count']:
            data['champions']=eligible
            self.store.db.execute("UPDATE tournament_rounds SET phase='finished',eligible_json=? WHERE tournament_id=? AND round=?",(json.dumps(data),identity,number))
            return True
        self.store.db.execute("UPDATE tournament_rounds SET phase='complete',eligible_json=? WHERE tournament_id=? AND round=?",(json.dumps(data),identity,number))
        next_number=number+1;planned=settings['start_time']+settings['qualification_seconds']+(next_number-1)*settings['round_seconds']
        start=max(now,planned);end=start+settings['round_seconds']
        priority=data['seed_order'];eligible.sort(key=lambda p:priority.index(p))
        pairs=[[eligible[i],eligible[-1-i]] for i in range(len(eligible)//2)]
        byes=[eligible[len(eligible)//2]] if len(eligible)%2 else []
        next_data={**data,'slot':{'start':start,'end':end},'pairs':pairs,'byes':byes,'entered':[]}
        self.store.db.execute("INSERT INTO tournament_rounds VALUES(?,?,'open',?)",(identity,next_number,json.dumps(next_data)))
        # Shift remaining times when a preceding round's matches overrun its entry window.
        new_end=end+(settings['round_count']-next_number)*settings['round_seconds']
        settings['end_time']=max(settings.get('scheduled_end_time',settings['end_time']),math.ceil(new_end))
        self.store.db.execute('UPDATE tournaments SET settings_json=? WHERE id=?',(json.dumps(settings),identity))
        self.shift_upcoming_tournaments(identity,settings['end_time'])
        return False

    def shift_upcoming_tournaments(self, identity, end):
        cfg=self.config['general']['tournament'];gap=max(0,cfg.get('repeat_seconds',0)-(cfg['end_time']-cfg['start_time']))
        for row in self.store.db.execute("SELECT * FROM tournaments WHERE id>? AND phase='upcoming' ORDER BY id",(identity,)).fetchall():
            settings=json.loads(row['settings_json']);duration=settings['end_time']-settings['start_time'];start=max(settings['start_time'],end+gap)
            settings.update(start_time=start,end_time=start+duration);end=settings['end_time']
            self.store.db.execute('UPDATE tournaments SET settings_json=? WHERE id=?',(json.dumps(settings),settings['id']))

    def knockout_order(self, settings, entries):
        if settings.get('format','league')!='elimination':return entries
        row,data=self.round_state(settings['id'])
        if not row or row['round']==0 and row['phase']=='open':return entries
        alive=set(data.get('eligible',[]));champions=set(data.get('champions',[]));eliminated=data.get('eliminated',{})
        entries.sort(key=lambda pe:(0 if pe[0] in champions else 1 if pe[0] in alive else 2,-eliminated.get(pe[0],-1),-pe[1]['tournamentPoints'],pe[1]['player']['nickname'].casefold()))
        for rank,(p,e) in enumerate(entries,1):e.update(currentRank=rank,eliminated=p in eliminated)
        return entries

    def round_slots(self, settings):
        if settings.get('format','league')!='elimination':return []
        row,data=self.round_state(settings['id']);slots=[]
        if not row or row['round']==0:return []
        records={r['round']:json.loads(r['eligible_json'])['slot'] for r in self.store.db.execute('SELECT * FROM tournament_rounds WHERE tournament_id=?',(settings['id'],))}
        for number in range(1,settings['round_count']+1):
            planned=settings['start_time']+settings['qualification_seconds']+(number-1)*settings['round_seconds']
            slot=records.get(number,{'start':planned,'end':planned+settings['round_seconds']})
            slots.append({'startTime':slot['start']*1000,'endTime':slot['end']*1000})
        return slots

    def tournament_round_metadata(self, profile, rows):
        result={}
        for tournament in rows:
            settings=json.loads(tournament['settings_json'])
            if settings.get('format','league')!='elimination':continue
            row,data=self.round_state(settings['id'])
            if not row:continue
            pair=next((pair for pair in data.get('pairs',[]) if profile in pair),[])
            opponent=next((p for p in pair if p!=profile),None)
            result[str(settings['id'])]={'round':row['round'],'phase':row['phase'],'start':data['slot']['start'],'end':data['slot']['end'],
                'played':any(profile in m['profiles'] for m in self.round_matches(settings['id'],row['round'])) if row['round'] else False,
                'bye':profile in data.get('byes',[]),'opponent':self.store.profile(opponent)['nickname'] if opponent else None}
        return result
