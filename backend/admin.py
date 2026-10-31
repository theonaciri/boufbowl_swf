"""Authenticated administrator console: chat review and durable tournament schedules."""
from copy import deepcopy
import json
import time
from backend.storage import ServiceError
from backend.tracking import website_metrics_report
from tools.game_config import STADIUMS, check_rules, resolve_stadium


def integer(value, low, high, label):
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        raise ServiceError('ADMIN_INPUT', f'{label} must be an integer between {low} and {high}')
    return value


class Admin:
    def admin(self, body):
        with self.store.transaction():
            actor = self.store.authenticate(body.get('session'))
            self.require_moderator(actor)
            action = body.get('action', 'messages')
            if action in ('assets','asset_decision'):
                if self.role(actor)!='admin':raise ServiceError('ADMIN_FORBIDDEN','Administrator role required')
                manager=getattr(self,'asset_contributions',None)
                if manager is None:raise ServiceError('ASSET_UNAVAILABLE','Asset review is not configured')
                if action=='asset_decision':
                    result=manager.decision(body.get('id'),body.get('decision'),actor)
                else:result=manager.listing(body.get('state',''))
            elif action == 'messages':
                result = self.admin_messages(body)
            elif action == 'moderation':
                result = self.moderation_data(actor)
                result['players'] = [dict(r) for r in self.store.db.execute(
                    'SELECT p.id,p.nickname,a.username FROM profiles p LEFT JOIN accounts a ON a.profile_id=p.id ORDER BY p.nickname')]
            elif action == 'suspend':
                duration = body.get('duration')
                if duration not in (86400, 604800, 0) or isinstance(duration, bool):
                    raise ServiceError('ADMIN_INPUT', 'Choose one day, seven days or indefinite')
                target = self.target_player(body.get('nickname'), actor)
                if target == actor:
                    raise ServiceError('ADMIN_INPUT', 'You cannot suspend yourself')
                result = self.moderate(actor, {**body, 'verb': 'ban', 'duration': duration})
            elif action == 'unsuspend':
                result = self.moderate(actor, {**body, 'verb': 'unban'})
            elif action in ('tournaments', 'schedule', 'edit_tournament'):
                if self.role(actor) != 'admin':
                    raise ServiceError('ADMIN_FORBIDDEN', 'Administrator role required')
                if action == 'schedule':
                    self.admin_schedule(actor, body)
                if action == 'edit_tournament':
                    self.maintain_tournaments()
                    self.admin_edit_tournament(actor, body)
                self.maintain_tournaments()
                if action in ('schedule', 'edit_tournament'):
                    for watcher in self.store.db.execute('SELECT profile_id FROM tournament_watchers').fetchall():
                        self.send_tournaments(watcher[0])
                result = self.admin_tournaments()
            elif action in ('website_activity', 'website_analytics', 'website_tracking'):
                if self.role(actor) != 'admin':
                    raise ServiceError('ADMIN_FORBIDDEN', 'Administrator role required')
                result = website_metrics_report(self.store, body.get('days', 30), body.get('hours'))
            else:
                raise ServiceError('ADMIN_ACTION', 'Unknown administrator action')
            return {'ok': True, 'role': self.role(actor), **result}

    def admin_messages(self, body):
        clauses, args = [], []
        before = integer(body.get('before', 9223372036854775807), 1, 9223372036854775807, 'Message cursor')
        clauses.append('m.id<?'); args.append(before)
        kind = body.get('kind', '')
        if kind not in ('', 'public', 'private', 'match'):
            raise ServiceError('ADMIN_INPUT', 'Unknown channel filter')
        if kind == 'private': clauses.append('m.recipient IS NOT NULL')
        if kind == 'match': clauses.append('m.match_id IS NOT NULL')
        if kind == 'public': clauses.append('m.recipient IS NULL AND m.match_id IS NULL')
        for key, sql in [('search', 'instr(lower(m.message),lower(?))>0'),
                         ('player', '(instr(lower(p.nickname),lower(?))>0 OR instr(lower(COALESCE(q.nickname,\'\')),lower(?))>0)'),
                         ('language', 'm.language=?')]:
            value = body.get(key, '')
            if not isinstance(value, str) or len(value) > 500:
                raise ServiceError('ADMIN_INPUT', 'Invalid text filter')
            if value:
                clauses.append(sql); args.extend([value] * sql.count('?'))
        focus = body.get('focus')
        if focus is not None:
            identity = integer(focus, 1, 9223372036854775807, 'Conversation message')
            row = self.store.db.execute('SELECT * FROM chat_messages WHERE id=?', (identity,)).fetchone()
            if not row: raise ServiceError('ADMIN_INPUT', 'Conversation message no longer exists')
            # Context deliberately replaces the channel/search filters, retaining pagination.
            clauses, args = ['m.id<?'], [before]
            if row['recipient']:
                clauses.append('((m.sender=? AND m.recipient=?) OR (m.sender=? AND m.recipient=?))')
                args.extend([row['sender'], row['recipient'], row['recipient'], row['sender']])
            elif row['match_id']:
                clauses.append('m.match_id=?'); args.append(row['match_id'])
            else: raise ServiceError('ADMIN_INPUT', 'Select a private or match message for context')
        rows = self.store.db.execute('''SELECT m.*,p.nickname AS sender_name,q.nickname AS recipient_name
            FROM chat_messages m JOIN profiles p ON p.id=m.sender LEFT JOIN profiles q ON q.id=m.recipient
            WHERE ''' + ' AND '.join(clauses) + ' ORDER BY m.id DESC LIMIT 101', args).fetchall()
        counts = self.store.db.execute('''SELECT COUNT(*) AS total,
            COALESCE(SUM(recipient IS NOT NULL),0) AS private,
            COALESCE(SUM(match_id IS NOT NULL),0) AS match,
            COUNT(DISTINCT sender) AS senders FROM chat_messages WHERE created>?''', (time.time()-86400,)).fetchone()
        activity = [dict(r) for r in self.store.db.execute('''SELECT CAST(created/3600 AS INTEGER)*3600 AS hour,
            COUNT(*) AS count FROM chat_messages WHERE created>? GROUP BY hour ORDER BY hour''', (time.time()-86400,))]
        return {'messages': [dict(r) for r in rows[:100]], 'has_more': len(rows)>100,
                'counts': dict(counts), 'activity': activity, 'generated_at': time.time()}

    def tournament_settings(self):
        row = self.store.db.execute("SELECT value FROM admin_settings WHERE key='tournament'").fetchone()
        return json.loads(row[0]) if row else self.config['general']['tournament']

    def admin_edit_tournament(self, actor, body):
        identity = integer(body.get('tournament_id'), 1, 9223372036854775807, 'Tournament ID')
        row = self.store.db.execute('SELECT * FROM tournaments WHERE id=?', (identity,)).fetchone()
        if not row or row['phase'] not in ('upcoming', 'open'):
            raise ServiceError('ADMIN_INPUT', 'Only upcoming or running tournaments can be edited')
        cfg = json.loads(row['settings_json']); supplied = body.get('settings')
        if not isinstance(supplied, dict) or set(supplied) != {'name', 'start_time', 'end_time', 'stadium'}:
            raise ServiceError('ADMIN_INPUT', 'Tournament name, dates and stadium are required')
        now = time.time(); start = integer(supplied['start_time'], 1, 4102444800, 'Start time')
        end = integer(supplied['end_time'], int(now)+1, 4102444800, 'End time')
        stadium = integer(supplied['stadium'], 1, len(STADIUMS), 'Stadium')
        if not self.config['stadiums'][STADIUMS[stadium-1]]['enabled']:
            raise ServiceError('ADMIN_INPUT', 'This stadium is disabled')
        if row['phase'] == 'open' and (start != cfg['start_time'] or stadium != cfg['stadium']):
            raise ServiceError('ADMIN_INPUT', 'The start time and stadium cannot change after the tournament starts')
        if row['phase'] == 'upcoming' and start <= now:
            raise ServiceError('ADMIN_INPUT', 'An upcoming tournament must start in the future')
        if end-start < 300 or end-start > 604800:
            raise ServiceError('ADMIN_INPUT', 'Duration must be between five minutes and seven days')
        if cfg.get('format') == 'elimination' and cfg['qualification_seconds']+cfg['round_count']*cfg['round_seconds'] > end-start:
            raise ServiceError('ADMIN_INPUT', 'The qualification and rounds must fit the tournament duration')
        if row['phase'] == 'open' and cfg.get('format') == 'elimination':
            _, state = self.round_state(identity)
            if state and end < state['slot']['end']:
                raise ServiceError('ADMIN_INPUT', 'The end cannot precede the current round')
        if any(json.loads(other[0])['start_time'] < end and json.loads(other[0])['end_time'] > start for other in self.store.db.execute("SELECT settings_json FROM tournaments WHERE id<>? AND phase IN ('upcoming','open','closing')", (identity,))):
            raise ServiceError('ADMIN_INPUT', 'Tournament dates overlap another scheduled event')
        if row['phase'] == 'upcoming' and start != cfg['start_time']:
            self.store.db.execute('DELETE FROM tournament_rounds WHERE tournament_id=?', (identity,))
        cfg.update(name=self.name(supplied['name'],80), start_time=start, end_time=end, stadium=stadium)
        self.store.db.execute('UPDATE tournaments SET settings_json=? WHERE id=?', (json.dumps(cfg), identity))
        self.store.db.execute('INSERT INTO admin_events(actor,action,details,created) VALUES(?,?,?,?)', (actor,'edit_tournament',json.dumps({'id':identity,'settings':supplied}),now))

    def admin_schedule(self, actor, body):
        supplied = body.get('settings')
        if not isinstance(supplied, dict): raise ServiceError('ADMIN_INPUT', 'Tournament settings required')
        cfg = deepcopy(self.config['general']['tournament'])
        cfg.update(enabled=True, upcoming_count=3, rewards=[1,2,3,4])
        cfg['name'] = self.name(supplied.get('name'), 80)
        now = time.time()
        cfg['start_time'] = integer(supplied.get('start_time'), int(now)+1, 4102444800, 'Start time')
        duration = integer(supplied.get('duration_seconds'), 300, 604800, 'Duration')
        cfg['end_time'] = cfg['start_time'] + duration
        cfg['repeat_seconds'] = integer(supplied.get('repeat_seconds', 0), 0, 31536000, 'Recurrence')
        if cfg['repeat_seconds'] and cfg['repeat_seconds'] < duration:
            raise ServiceError('ADMIN_INPUT', 'Recurrence must be at least the event duration')
        cfg['stadium'] = integer(supplied.get('stadium'), 1, len(STADIUMS), 'Stadium')
        if not self.config['stadiums'][STADIUMS[cfg['stadium']-1]]['enabled']:
            raise ServiceError('ADMIN_INPUT', 'This stadium is disabled')
        cfg['stadium_rotation'] = [cfg['stadium']]
        cfg['format'] = supplied.get('format', 'league')
        if cfg['format'] not in ('league', 'elimination'): raise ServiceError('ADMIN_INPUT', 'Unknown tournament format')
        for key, default, low, high in [('min_rating',0,0,100000), ('max_rating',100000,0,100000),
                ('win_points',3,0,100), ('draw_points',1,0,100), ('loss_points',0,0,100),
                ('qualification_seconds',900,60,604800), ('qualifying_top',4,2,64),
                ('round_count',2,1,6), ('round_seconds',900,60,86400)]:
            cfg[key] = integer(supplied.get(key, default), low, high, key.replace('_', ' '))
        if cfg['min_rating'] > cfg['max_rating']: raise ServiceError('ADMIN_INPUT', 'Minimum rating exceeds maximum')
        if cfg['format'] == 'elimination' and (cfg['qualification_seconds']+cfg['round_count']*cfg['round_seconds'] > duration or cfg['qualifying_top'] > 2**cfg['round_count']):
            raise ServiceError('ADMIN_INPUT', 'Qualification and rounds must fit the duration and bracket capacity')
        rules = supplied.get('match_rules', {})
        if not isinstance(rules, dict) or set(rules)-{'turns_per_match','turns_per_period','planning_seconds','placement_seconds','class_ability_uses','regenerate_between_turns'}:
            raise ServiceError('ADMIN_INPUT', 'Unknown match rule')
        for key, value in rules.items():
            if key == 'regenerate_between_turns':
                if not isinstance(value, bool): raise ServiceError('ADMIN_INPUT', 'Regeneration must be true or false')
            else: integer(value, 0 if key=='class_ability_uses' else 1, 300 if key.endswith('seconds') else 100, key)
        merged = resolve_stadium(self.config, STADIUMS[cfg['stadium']-1])
        merged['match'].update(rules)
        try: check_rules(merged, 'tournament')
        except ValueError as error: raise ServiceError('ADMIN_INPUT', str(error)) from error
        cfg['match_rules'] = rules
        prizes = supplied.get('prizes', {})
        if not isinstance(prizes, dict) or set(prizes)-{'glory','influence','coins'}:
            raise ServiceError('ADMIN_INPUT', 'Prizes require glory, influence and coins')
        cfg['prizes'] = {key: integer(prizes.get(key, 0), 0, 1000000, key+' prize') for key in ('glory','influence','coins')}
        # Preserve running and completed events; only replace unstarted occurrences.
        active = self.store.db.execute("SELECT settings_json FROM tournaments WHERE phase IN ('open','closing')").fetchall()
        if any(json.loads(r[0])['end_time'] > cfg['start_time'] for r in active):
            raise ServiceError('ADMIN_INPUT', 'Start after the current tournament ends; running events are preserved')
        maximum = self.store.db.execute('SELECT COALESCE(MAX(id),0) FROM tournaments').fetchone()[0]
        cfg['id'] = maximum + 1
        cfg['series_id'] = cfg['id']
        upcoming = [r[0] for r in self.store.db.execute("SELECT id FROM tournaments WHERE phase='upcoming'")]
        for identity in upcoming:
            self.store.db.execute('DELETE FROM tournament_rounds WHERE tournament_id=?', (identity,))
            self.store.db.execute('DELETE FROM tournaments WHERE id=?', (identity,))
        self.store.db.execute("INSERT INTO admin_settings VALUES('tournament',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (json.dumps(cfg),))
        self.store.db.execute('INSERT INTO admin_events(actor,action,details,created) VALUES(?,?,?,?)',
                              (actor, 'schedule', json.dumps(cfg), now))

    def admin_tournaments(self):
        events = []
        active_by_tournament = {}
        for match_row in self.store.db.execute('SELECT state_json FROM matches'):
            match = json.loads(match_row[0])
            if match.get('tournament') is not None and match['phase'] != 'ended':
                active_by_tournament.setdefault(match['tournament'], []).append({
                    'id': match['id'], 'players': [r['nickname'] for r in match['rosters']], 'score': match['score']})
        for row in self.store.db.execute('SELECT * FROM tournaments ORDER BY json_extract(settings_json,\'$.start_time\') DESC LIMIT 100'):
            cfg = json.loads(row['settings_json'])
            entries = self.tournament_entries(cfg)
            events.append({'id': row['id'], 'settings': cfg, 'phase': row['phase'],
                           'interested': self.store.db.execute('SELECT COUNT(*) FROM tournament_intentions WHERE tournament_id=?', (row['id'],)).fetchone()[0],
                           'matches': self.store.db.execute("SELECT COUNT(*) FROM matches WHERE json_extract(state_json,'$.tournament')=?", (row['id'],)).fetchone()[0],
                           'participants': len(entries), 'standings': [e for _,e in entries[:20]],
                           'rounds': self.admin_rounds(cfg), 'active_matches': active_by_tournament.get(row['id'], [])})
        return {'tournaments': events, 'schedule': self.tournament_settings(),
                'stadiums': [{'id': i, 'name': name} for i,name in enumerate(STADIUMS,1) if self.config['stadiums'][name]['enabled']],
                'generated_at': time.time()}

    def admin_rounds(self, cfg):
        if cfg.get('format') != 'elimination':
            return []
        rounds = [{'label': 'Qualification', 'startTime': cfg['start_time']*1000,
                   'endTime': (cfg['start_time']+cfg['qualification_seconds'])*1000}]
        slots = self.round_slots(cfg)
        if not slots:
            for i in range(cfg['round_count']):
                start = cfg['start_time']+cfg['qualification_seconds']+i*cfg['round_seconds']
                slots.append({'startTime': start*1000, 'endTime': (start+cfg['round_seconds'])*1000})
        return rounds + [dict(slot, label='Round '+str(i)) for i,slot in enumerate(slots, 1)]
