"""Bounded client timing aggregates and authoritative per-turn game counters."""
from collections import Counter
from datetime import datetime, timezone
import json
import math
import time

FRAME_BUCKETS = (8, 17, 25, 34, 50, 67, 100, 250, 1000, 60000)
COUNTERS = ('moves', 'risk_tests', 'falls', 'passes', 'completed_passes', 'interceptions', 'goals')


def init_schema(db):
    db.executescript('''
      CREATE TABLE IF NOT EXISTS game_frame_measurements(
        day TEXT NOT NULL,runtime TEXT NOT NULL,platform TEXT NOT NULL,phase TEXT NOT NULL,
        samples INTEGER NOT NULL,frames INTEGER NOT NULL,elapsed_ms REAL NOT NULL,
        slow_frames INTEGER NOT NULL,target_total REAL NOT NULL,max_frame_ms REAL NOT NULL,
        memory_max_mb REAL,histogram_json TEXT NOT NULL,PRIMARY KEY(day,runtime,platform,phase));
      CREATE TABLE IF NOT EXISTS game_turn_measurements(
        match_id TEXT NOT NULL,turn INTEGER NOT NULL,team INTEGER NOT NULL,day TEXT NOT NULL,
        controller TEXT NOT NULL,counters_json TEXT NOT NULL,strategy TEXT,
        PRIMARY KEY(match_id,turn,team));
      CREATE INDEX IF NOT EXISTS game_turn_measurements_day ON game_turn_measurements(day);
    ''')
    db.execute("INSERT OR IGNORE INTO tracking_meta VALUES('game_measurements_started_at',?)", (str(time.time()),))


def finite_number(value, minimum, maximum):
    return type(value) in (int, float) and math.isfinite(value) and minimum <= value <= maximum


def validate_event(event):
    if event['kind'] == 'game_startup':
        if not finite_number(event.get('elapsed_ms'), 0, 3600000):
            raise ValueError('Invalid game startup timing')
        return
    if event.get('phase') not in ('ui','3d'):
        raise ValueError('Unknown game measurement phase')
    frames = event.get('frames')
    if type(frames) is not int or not 1 <= frames <= 30000:
        raise ValueError('Invalid measured frame count')
    for name, low, high in [('elapsed_ms',1,120000),('target_fps',1,240),('max_frame_ms',0,60000)]:
        if not finite_number(event.get(name),low,high):
            raise ValueError('Invalid game measurement: '+name)
    histogram = event.get('histogram')
    if (not isinstance(histogram,list) or len(histogram) != len(FRAME_BUCKETS)
            or any(type(n) is not int or n < 0 for n in histogram) or sum(histogram) != frames):
        raise ValueError('Invalid frame histogram')
    slow = event.get('slow_frames')
    if type(slow) is not int or not 0 <= slow <= frames:
        raise ValueError('Invalid slow frame count')
    if event.get('memory_mb') is not None and not finite_number(event['memory_mb'],0,65536):
        raise ValueError('Invalid reported runtime memory')


def record_client(db, day, metadata, event):
    runtime = metadata.get('runtime','unknown')
    if runtime not in ('ruffle','flash','air'): runtime = 'unknown'
    platform = metadata.get('platform','unknown')
    if platform not in ('browser','windows','linux','android','macos'): platform = 'unknown'
    key = (day,runtime,platform,event['phase'])
    old = db.execute('SELECT * FROM game_frame_measurements WHERE day=? AND runtime=? AND platform=? AND phase=?',key).fetchone()
    histogram = event['histogram'] if old is None else [a+b for a,b in zip(json.loads(old['histogram_json']),event['histogram'])]
    memory = event.get('memory_mb')
    if old and old['memory_max_mb'] is not None:
        memory = max(memory or 0,old['memory_max_mb'])
    db.execute('INSERT OR REPLACE INTO game_frame_measurements VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
               (*key,1+(old['samples'] if old else 0),event['frames']+(old['frames'] if old else 0),
                event['elapsed_ms']+(old['elapsed_ms'] if old else 0),event['slow_frames']+(old['slow_frames'] if old else 0),
                event['target_fps']*event['frames']+(old['target_total'] if old else 0),
                max(event['max_frame_ms'],old['max_frame_ms'] if old else 0),memory,json.dumps(histogram)))


def record_turn(db, match_id, turn, record, profiles):
    day = datetime.now(timezone.utc).date().isoformat()
    teams = {entity['id']:entity['team_id'] for entity in record['initial']['entities']}
    counts = [Counter(),Counter()]
    flight = None
    for event in record['result']['events']:
        kind, actor, params = event['type'],event.get('actor'),event.get('params',{})
        team = teams.get(actor)
        if team in (0,1):
            counter = counts[team]
            if kind == 'move': counter['moves'] += 1
            elif kind == 'movement_test' and params.get('probability',0) > 0: counter['risk_tests'] += 1
            elif kind == 'fall': counter['falls'] += 1
            elif kind == 'throw': counter['passes'] += 1; flight = team
            elif kind == 'goal': counter['goals'] += 1
            elif kind == 'catch' and flight is not None:
                if flight == team: counter['completed_passes'] += 1
                else: counter['interceptions'] += 1
                flight = None
        if kind in ('ball_land','ball_drop','goal'): flight = None
    for team, counters in enumerate(counts):
        order = record.get('orders',[{},{}])[team] or {}
        strategy = order.get('cpu_plan',{}).get('strategy') if profiles[team] is None else None
        db.execute('INSERT OR IGNORE INTO game_turn_measurements VALUES(?,?,?,?,?,?,?)',
                   (match_id,turn,team,day,'cpu' if profiles[team] is None else 'human',
                    json.dumps({key:counters[key] for key in COUNTERS}),str(strategy)[:40] if strategy else None))


def report(db, start):
    frames, groups = [], {}
    for row in db.execute('SELECT * FROM game_frame_measurements WHERE day>=? ORDER BY day,runtime,platform,phase',(start,)):
        item = dict(row)
        histogram = json.loads(item.pop('histogram_json'))
        item['fps'] = item['frames']*1000/item['elapsed_ms']
        item['slow_percent'] = 100*item['slow_frames']/item['frames']
        item['target_fps'] = item.pop('target_total')/item['frames']
        cumulative = 0
        for bound, count in zip(FRAME_BUCKETS,histogram):
            cumulative += count
            if cumulative >= math.ceil(item['frames']*.95):
                item['p95_frame_ms'] = bound
                break
        frames.append(item)
    for row in db.execute('SELECT day,controller,counters_json,strategy FROM game_turn_measurements WHERE day>=?',(start,)):
        key = (row['day'],row['controller'])
        item = groups.setdefault(key,{'day':key[0],'controller':key[1],'team_turns':0,'strategies':Counter(),**dict.fromkeys(COUNTERS,0)})
        item['team_turns'] += 1
        for name, value in json.loads(row['counters_json']).items(): item[name] += value
        if row['strategy']: item['strategies'][row['strategy']] += 1
    for item in groups.values():
        item['fall_percent'] = 100*item['falls']/item['risk_tests'] if item['risk_tests'] else None
        item['pass_percent'] = 100*item['completed_passes']/item['passes'] if item['passes'] else None
    started = db.execute("SELECT value FROM tracking_meta WHERE key='game_measurements_started_at'").fetchone()
    return {'started_at':float(started[0]),'frames':frames,'gameplay':sorted(groups.values(),key=lambda item:(item['day'],item['controller'])),
            'coverage':'Frame timing is client-reported ENTER_FRAME timing, not GPU presentation FPS. Hidden/inactive windows and gaps over 60 seconds are excluded. Slow frames exceed twice the selected FPS budget. Memory is reported runtime allocation, not process/GPU memory. Gameplay counts cover newly saved authoritative turns only; moves are simulation steps, and pass completion means a teammate caught the flight. Small samples can be misleading.'}
