"""Aggregates used by the private admin charts; no new identifiers are stored."""
from collections import defaultdict
from datetime import datetime, timedelta, timezone
import json


def charts(db, start, today, collection_start):
    availability = [dict(row) for row in db.execute("""SELECT CAST(strftime('%w',minute*60,'unixepoch') AS INTEGER) AS weekday,
        CAST(strftime('%H',minute*60,'unixepoch') AS INTEGER) AS hour, AVG(online) AS online,
        AVG(queued) AS queued, COUNT(*) AS samples FROM tracking_samples WHERE day>=?
        GROUP BY 1,2 ORDER BY 1,2""", (str(start),))]
    weeks = defaultdict(lambda: {'started': 0, 'ongoing': 0, 'surrendered': 0, 'ended': 0})
    for row in db.execute("SELECT state_json FROM matches WHERE json_extract(state_json,'$.created')>=?", (datetime.combine(start, datetime.min.time(), timezone.utc).timestamp(),)):
        match = json.loads(row[0]); day = datetime.fromtimestamp(match['created'], timezone.utc).date()
        if day > today: continue
        week = str(day - timedelta(days=day.weekday())); item = weeks[week]; item['started'] += 1
        item['ongoing' if match['phase'] != 'ended' else 'surrendered' if match.get('given_up') is not None else 'ended'] += 1
    cohorts = defaultdict(lambda: {str(day): {'eligible': 0, 'returned': 0} for day in (1,7,30)})
    if collection_start is not None:
        first = max(start, collection_start)
        for row in db.execute('SELECT id,created FROM profiles WHERE created>=?', (datetime.combine(first, datetime.min.time(), timezone.utc).timestamp(),)):
            created = datetime.fromtimestamp(row['created'], timezone.utc).date()
            if created >= today: continue
            week = str(created - timedelta(days=created.weekday()))
            for day in (1,7,30):
                if created + timedelta(days=day) >= today: continue
                item = cohorts[week][str(day)]; item['eligible'] += 1
                if db.execute('SELECT 1 FROM tracking_activity WHERE profile_id=? AND day=? AND observed=1', (row['id'],str(created+timedelta(days=day)))).fetchone(): item['returned'] += 1
    return {'availability': availability, 'matches_by_week': [{'week':k, **v} for k,v in sorted(weeks.items())],
            'retention_by_week': [{'week':k, 'days':v} for k,v in sorted(cohorts.items())]}
