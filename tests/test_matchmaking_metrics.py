from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from backend.matchmaking_metrics import report
from backend.service import Service
from backend.tracking import metrics_report
from tests.test_backend import initial_club
from tools.game_config import load_config


class MatchmakingMetricsTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        config = load_config()
        config['general']['cinematics']['introductions'] = False
        self.service = Service(Path(self.directory.name) / 'test.sqlite', config)
        self.players = [self.service.hello({'nickname': name, 'clubs': [initial_club()]}) for name in ('Aaa', 'Bbb')]
        self.ids = [self.service.store.authenticate(player['session']) for player in self.players]

    def tearDown(self):
        self.service.close(); self.directory.cleanup()

    def test_match_cancellation_expiry_and_no_duplicate_exits(self):
        service = self.service
        with service.store.transaction():
            with patch.object(service, 'match_queued_players'):
                service.join_queue(self.ids[0], [1])
                service.store.db.execute('UPDATE matchmaking_queue SET joined=joined-12 WHERE profile_id=?', (self.ids[0],))
                service.join_queue(self.ids[0], [1, 2])  # Same search; do not count twice.
            service.leave_queue(self.ids[0], 'cancelled')
            service.leave_queue(self.ids[0], 'cancelled')
            with patch.object(service, 'match_queued_players'):
                service.join_queue(self.ids[1], [1])
            service.store.db.execute('UPDATE matchmaking_queue SET joined=joined-180,heartbeat=heartbeat-120 WHERE profile_id=?', (self.ids[1],))
            service.match_queued_players()
        rows = report(service.store.db, '2000-01-01')['rows']
        by_outcome = {row['outcome']: row for row in rows}
        self.assertEqual(set(by_outcome), {'cancelled', 'expired'})
        self.assertEqual(by_outcome['cancelled']['count'], 1)
        self.assertGreaterEqual(by_outcome['cancelled']['mean_seconds'], 12)
        self.assertEqual(by_outcome['cancelled']['p50_upper_seconds'], 15)
        self.assertEqual(by_outcome['expired']['count'], 1)
        # The recorded expiry is the deadline, not the later sweep time.
        self.assertAlmostEqual(by_outcome['expired']['mean_seconds'], 150, delta=1)
        self.assertNotIn('profile_id', [row['name'] for row in service.store.db.execute('PRAGMA table_info(matchmaking_exit_metrics)')])

    def test_matchmaking_records_both_players_and_rolls_back(self):
        service = self.service
        with self.assertRaises(RuntimeError):
            with service.store.transaction():
                service.join_queue(self.ids[0], [1])
                service.leave_queue(self.ids[0], 'cancelled')
                raise RuntimeError('rollback')
        self.assertEqual(report(service.store.db, '2000-01-01')['rows'], [])
        with service.store.transaction():
            service.join_queue(self.ids[0], [1])
            service.join_queue(self.ids[1], [1])
        rows = report(service.store.db, '2000-01-01')['rows']
        self.assertEqual([(row['kind'], row['outcome'], row['count']) for row in rows], [('regular', 'matched', 2)])
        self.assertEqual(metrics_report(service.store, 7)['queue_waits']['rows'], rows)

    def test_prunes_old_aggregates_and_reports_overflow_as_unknown_bound(self):
        db = self.service.store.db
        day = datetime.now(timezone.utc).date()
        db.execute('INSERT INTO matchmaking_exit_metrics VALUES(?,?,?,?,?,?)', (str(day - timedelta(days=401)), 'regular', 'other', 5, 1, 1))
        db.execute('INSERT INTO matchmaking_queue VALUES(?,?,?,?,NULL)', (self.ids[0], '[1]', time.time()-4000, time.time()))
        self.service.leave_queue(self.ids[0], 'other')
        rows = report(db, '2000-01-01')['rows']
        self.assertEqual(len(rows), 1)
        self.assertIsNone(rows[0]['p95_upper_seconds'])

    def test_switching_queues_records_replaced_without_losing_new_search(self):
        service = self.service
        with service.store.transaction():
            service.store.db.execute('INSERT INTO matchmaking_queue VALUES(?,?,?,?,?)',
                                     (self.ids[0], '[1]', time.time()-20, time.time(), '42'))
            with patch.object(service, 'match_queued_players'):
                service.join_queue(self.ids[0], [1])
            current = service.store.db.execute('SELECT tournament_id FROM matchmaking_queue WHERE profile_id=?', (self.ids[0],)).fetchone()
        self.assertIsNone(current['tournament_id'])
        rows = report(service.store.db, '2000-01-01')['rows']
        self.assertEqual([(row['kind'], row['outcome'], row['count']) for row in rows], [('tournament', 'replaced', 1)])


if __name__ == '__main__': unittest.main()
