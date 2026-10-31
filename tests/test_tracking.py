"""Durable tracking, recovered history, access controls and hot-path overhead."""
from contextlib import closing
from datetime import datetime, timezone, timedelta
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import time
import unittest
from unittest.mock import patch

from backend.service import Service
from backend.storage import ServiceError, Store
from backend.tracking import day_at, metrics_report, website_metrics_report
from tests import test_backend as helpers


class TrackingTests(unittest.TestCase):
    setUp = helpers.BackendTests.setUp
    tearDown = helpers.BackendTests.tearDown
    command = helpers.BackendTests.command
    protocol = helpers.BackendTests.protocol
    start = helpers.BackendTests.start
    identity = helpers.BackendTests.identity

    def test_website_short_periods_use_minute_aggregates_without_inventing_old_history(self):
        now=time.time()
        tracker=self.service.tracking
        for age in (30, 7200, 90000):
            with patch('backend.tracking.time.time', return_value=now-age):
                tracker._website_event('section_view','hero')
        tracker.flush(force=True)
        self.assertEqual(website_metrics_report(self.service.store, hours=1)['sections'][0]['views'],1)
        self.assertEqual(website_metrics_report(self.service.store, hours=24)['sections'][0]['views'],2)
        self.assertEqual(website_metrics_report(self.service.store, days=7)['sections'][0]['views'],3)
        self.assertIsNotNone(website_metrics_report(self.service.store, hours=1)['period']['minute_coverage_started_at'])
        with self.assertRaises(ValueError): website_metrics_report(self.service.store, hours=2)

    def admin(self):
        with self.service.store.transaction():
            self.service.store.db.execute('INSERT OR REPLACE INTO profile_roles VALUES(?,?)', (self.identity(self.alice), 'admin'))
        return {'session': self.alice['session'], 'days': 7}

    def test_statistics_require_admin_and_keep_online_name_and_grace(self):
        for role in ('player', 'moderator'):
            with self.service.store.transaction():
                self.service.store.db.execute('INSERT OR REPLACE INTO profile_roles VALUES(?,?)', (self.identity(self.alice), role))
            with self.assertRaisesRegex(ServiceError, 'administrator'):
                self.service.metrics({'session': self.alice['session']})
        body = self.admin()
        now = time.time()
        self.service.store.db.execute('UPDATE presence SET seen=? WHERE profile_id=?', (now - 40, self.identity(self.bob)))
        report = self.service.metrics(body)
        self.assertEqual(report['online'], 2)
        self.assertEqual(report['totals']['profiles'], 2)
        self.assertNotIn('recently_active', report)
        self.assertEqual(report['usage']['active_users'], 2)
        for days in (0, 366, True, '7'):
            with self.assertRaises(ValueError): self.service.metrics({**body, 'days': days})

    def test_cohorts_compare_like_periods_and_exclude_immature_returns(self):
        db = self.service.store.db
        alice, bob = self.identity(self.alice), self.identity(self.bob)
        stamp = lambda day: datetime(2026, 10, day, 12, tzinfo=timezone.utc).timestamp()
        now = stamp(28)
        db.execute("UPDATE tracking_meta SET value=? WHERE key='started_at'", (str(stamp(1)),))
        db.execute('DELETE FROM tracking_activity')
        db.execute('UPDATE profiles SET created=? WHERE id=?', (stamp(20), alice))
        db.execute('UPDATE profiles SET created=? WHERE id=?', (stamp(26), bob))
        for day, profile in [('2026-10-19', alice), ('2026-10-21', alice), ('2026-10-27', alice), ('2026-10-27', bob), ('2026-10-28', bob)]:
            db.execute('INSERT INTO tracking_activity(day,profile_id,first_seen,last_seen,observed) VALUES(?,?,?,?,1)',
                       (day, profile, now, now))
        for created, phase, given_up in [(19, 'ended', None), (20, 'ended', None), (23, 'ended', 1), (25, 'planning', None)]:
            state = {'created': stamp(created), 'phase': phase, 'ended': stamp(26) if phase == 'ended' else 0,
                     'given_up': given_up, 'profiles': [alice, bob]}
            db.execute('INSERT INTO matches(state_json,updated) VALUES(?,?)', (json.dumps(state), now))
        with patch('backend.tracking.time.time', return_value=now):
            report = metrics_report(self.service.store, 9)
        self.assertEqual(report['comparison']['start'], '2026-10-11')
        self.assertEqual(report['comparison']['end_exclusive'], '2026-10-20')
        self.assertEqual((report['comparison']['active_profiles'], report['comparison']['matches_started'], report['comparison']['new_profiles']), (1, 1, 0))
        self.assertTrue(report['comparison']['activity_complete'])
        cohort = report['match_cohort']
        self.assertEqual((cohort['started'], cohort['ended'], cohort['completed_without_surrender'], cohort['surrendered'], cohort['ongoing']), (3, 2, 1, 1, 1))
        self.assertAlmostEqual(cohort['completion_rate'], 200 / 3)
        retention = {row['day']: row for row in report['retention']['days']}
        self.assertEqual((retention[1]['eligible'], retention[1]['returned'], retention[1]['rate']), (2, 2, 100))
        self.assertEqual((retention[7]['eligible'], retention[7]['returned'], retention[7]['rate']), (1, 1, 100))
        self.assertEqual((retention[30]['eligible'], retention[30]['rate']), (0, None))

    def test_retention_excludes_partial_collection_day_and_recovered_activity(self):
        db = self.service.store.db
        alice, bob = self.identity(self.alice), self.identity(self.bob)
        stamp = lambda day: datetime(2026, 10, day, 12, tzinfo=timezone.utc).timestamp()
        db.execute("UPDATE tracking_meta SET value=? WHERE key='started_at'", (str(stamp(20)),))
        db.execute('DELETE FROM tracking_activity')
        db.execute('UPDATE profiles SET created=? WHERE id=?', (stamp(20), alice))
        db.execute('UPDATE profiles SET created=? WHERE id=?', (stamp(21), bob))
        for day, profile in [('2026-10-21', alice), ('2026-10-22', bob)]:
            db.execute('INSERT INTO tracking_activity(day,profile_id,first_seen,last_seen,observed) VALUES(?,?,?,?,0)',
                       (day, profile, stamp(22), stamp(22)))
        with patch('backend.tracking.time.time', return_value=stamp(28)):
            report = metrics_report(self.service.store, 9)
        first_day = report['retention']['days'][0]
        self.assertEqual(report['retention']['cohort_start'], '2026-10-21')
        self.assertFalse(report['comparison']['activity_complete'])
        self.assertEqual((first_day['eligible'], first_day['returned'], first_day['rate']), (1, 0, 0))

    def test_retention_thirty_day_cutoff_and_deleted_profiles(self):
        db = self.service.store.db
        alice, bob = self.identity(self.alice), self.identity(self.bob)
        now = datetime(2026, 10, 28, 12, tzinfo=timezone.utc)
        db.execute("UPDATE tracking_meta SET value=? WHERE key='started_at'", (str((now - timedelta(days=100)).timestamp()),))
        db.execute('DELETE FROM tracking_activity')
        db.execute('UPDATE profiles SET created=? WHERE id=?', ((now - timedelta(days=31)).timestamp(), alice))
        db.execute('UPDATE profiles SET created=? WHERE id=?', ((now - timedelta(days=30)).timestamp(), bob))
        db.execute('INSERT INTO profiles VALUES(?,?,?,?,?)', ('deleted-test', 'Deleted test', '{}', '{}', (now - timedelta(days=31)).timestamp()))
        for profile, day in ((alice, '2026-10-27'), (bob, '2026-10-28'), ('deleted-test', '2026-10-27')):
            db.execute('INSERT INTO tracking_activity(day,profile_id,first_seen,last_seen,observed) VALUES(?,?,?,?,1)',
                       (day, profile, now.timestamp(), now.timestamp()))
        with patch('backend.tracking.time.time', return_value=now.timestamp()):
            before = metrics_report(self.service.store, 90)
            db.execute('DELETE FROM tracking_activity WHERE profile_id=?', ('deleted-test',))
            db.execute('DELETE FROM profiles WHERE id=?', ('deleted-test',))
            after = metrics_report(self.service.store, 90)
        before30, after30 = before['retention']['days'][2], after['retention']['days'][2]
        self.assertEqual((before30['eligible'], before30['returned']), (2, 2))
        self.assertEqual((after30['eligible'], after30['returned']), (1, 1))
        plan = db.execute('EXPLAIN QUERY PLAN SELECT id FROM profiles WHERE created>=? AND created<?', (0, now.timestamp())).fetchall()
        self.assertTrue(any('tracking_profiles_created' in row['detail'] for row in plan))

    def test_polls_buffer_activity_without_writes_and_flush_survives_restart(self):
        profile = self.identity(self.alice)
        cursor = self.service.store.db.execute('SELECT MAX(seq) FROM events WHERE profile_id=?', (profile,)).fetchone()[0]
        statements = []
        self.service.store.db.set_trace_callback(statements.append)
        try:
            for _ in range(10):
                self.service.poll({'session': self.alice['session'], 'cursor': cursor, 'compact': True})
        finally:
            self.service.store.db.set_trace_callback(None)
        self.assertFalse(any(s.startswith(('BEGIN', 'INSERT', 'UPDATE')) for s in statements))
        self.assertEqual(self.service.store.db.execute('SELECT COUNT(*) FROM tracking_activity').fetchone()[0], 0)
        self.service.close()
        self.service = Service(self.path, self.config)
        with self.service.store.lock:
            report = metrics_report(self.service.store, 7)
        self.assertEqual(report['usage']['active_users'], 2)
        self.assertEqual(sum(r['requests'] for r in report['daily']), 12)

    def test_startup_metadata_is_bounded_and_platforms_count_users_not_polls(self):
        metadata = {'platform': 'android', 'runtime': 'air', 'game_version': '1.9.6', 'runtime_version': 'AND 51',
                    'reported_os': 'Android', 'host_os': 'Android', 'cpu': 'ARM', 'screen_width': 1080,
                    'screen_height': 2400, 'gpu': True, 'debugger': False, 'unknown': 'not stored'}
        self.service.hello({'session': self.alice['session'], 'client_id': 'phone', 'client': metadata})
        self.service.hello({'session': self.alice['session'], 'client_id': 'phone', 'client': metadata})
        report = self.service.metrics(self.admin())
        android = next(r for r in report['platforms'] if r['platform'] == 'android')
        self.assertEqual(android['users'], 1)
        row = next(r for r in report['diagnostics'] if r['platform'] == 'android')
        self.assertEqual(row['screen_height'], 2400)
        self.assertNotIn('unknown', row)
        self.assertNotIn('session', row)
        self.assertTrue(self.alice['telemetry'])

    def test_mobile_reconnect_reports_are_idempotent_and_do_not_change_match(self):
        match = self.start()
        deadline = self.service.store.match(match['id'])['deadline']
        event = {'id': 'metro-outage-1', 'kind': 'reconnect', 'downtime_ms': 20000}
        body = {'session': self.alice['session'], 'client_id': 'phone', 'events': [event]}
        self.assertEqual(self.service.telemetry(body)['accepted'], 1)
        self.assertEqual(self.service.telemetry(body)['duplicates'], 1)
        self.service.close(); self.service = Service(self.path, self.config)
        self.assertEqual(self.service.telemetry(body)['duplicates'], 1)
        report = self.service.metrics(self.admin())
        self.assertEqual(sum(r['reconnects'] for r in report['daily']), 1)
        recovery = next(r for r in report['performance'] if r['kind'] == 'connection')
        self.assertEqual(recovery['count'], 1)
        self.assertEqual(recovery['mean_ms'], 20000)
        self.assertEqual(self.service.store.match(match['id'])['deadline'], deadline)

    def test_error_reports_are_sanitized_deduplicated_and_limited(self):
        event = {'id': 'error-1', 'kind': 'error', 'code': 'UNCAUGHT_ERROR',
                 'message': 'Failed https://host/api?session=secret password=hunter2', 'stack': 'frame1\nframe2'}
        body = {'session': self.alice['session'], 'client_id': 'phone', 'events': [event]}
        self.service.telemetry(body); self.service.telemetry(body)
        for i in range(3):
            batch = [{**event, 'id': 'error-' + str(i * 20 + j + 2)} for j in range(20)]
            result = self.service.telemetry({**body, 'events': batch})
        self.assertEqual(result['limited'], 1)
        report = self.service.metrics(self.admin())
        error = next(e for e in report['errors'] if e['origin'] == 'client')
        self.assertEqual(error['count'], 60)
        self.assertNotIn('hunter2', error['message'])
        self.assertNotIn('secret', error['message'])
        self.assertEqual(error['stack'], 'frame1\nframe2')
        with self.assertRaises(ValueError):self.service.telemetry({**body, 'events': [event] * 21})
        with self.assertRaises(ServiceError):self.service.telemetry({**body, 'session': 'invalid-token-12345'})

    def test_performance_histograms_merge_across_flushes(self):
        self.service.tracking.observe('http', 'POST /api/command', 4)
        self.service.tracking.observe('http', 'POST /api/command', 110, True)
        self.service.tracking.flush(force=True)
        self.service.tracking.observe('http', 'POST /api/command', 10)
        report = self.service.metrics(self.admin())
        item = next(r for r in report['performance'] if r['name'] == 'POST /api/command')
        self.assertEqual(item['count'], 3)
        self.assertEqual(item['errors'], 1)
        self.assertAlmostEqual(item['mean_ms'], 124/3)
        self.assertEqual(item['p95_bucket_ms'], 250)

    def test_failed_flush_keeps_buffer_for_retry(self):
        self.service.store.db.execute("CREATE TRIGGER stop_tracking BEFORE INSERT ON tracking_activity BEGIN SELECT RAISE(ABORT,'test'); END")
        with self.assertRaises(sqlite3.IntegrityError):self.service.tracking.flush(force=True)
        self.assertTrue(self.service.tracking.activity_rows)
        self.service.store.db.execute('DROP TRIGGER stop_tracking')
        report = self.service.metrics(self.admin())
        self.assertEqual(report['usage']['active_users'], 2)
        self.assertEqual(sum(r['requests'] for r in report['daily']), 2)

    def test_observed_online_time_splits_midnight_and_does_not_double_count_devices(self):
        boundary = datetime(2026, 10, 16, tzinfo=timezone.utc).timestamp()
        profile = self.identity(self.alice)
        # Setup logs in at wall-clock time; begin a fresh observation window
        # before simulating historical timestamps so this test is date-independent.
        self.service.tracking.profile_seen.pop(profile,None)
        with patch('time.time', return_value=boundary - 10), self.service.store.lock:
            self.service.tracking.activity(profile, {'client_id': 'a'})
        with patch('time.time', return_value=boundary + 10), self.service.store.lock:
            self.service.tracking.activity(profile, {'client_id': 'a'})
            self.service.tracking.activity(profile, {'client_id': 'b'})
        with patch('time.time', return_value=boundary + 10):
            self.service.tracking.flush(force=True)
            report = metrics_report(self.service.store, 2)
        daily = {r['day']: r for r in report['daily']}
        self.assertEqual(daily['2026-10-15']['online_seconds'], 10)
        self.assertEqual(daily['2026-10-16']['online_seconds'], 10)
        self.assertEqual(daily['2026-10-16']['returning_users'], 1)

    def test_legacy_history_is_backfilled_once_without_resetting_game_data(self):
        self.start()
        self.protocol(self.alice, 'ORDERS', {'turn': 1, 'orders': []})
        self.protocol(self.alice, 'RESOLUTION_DONE', {'turn': 1})
        self.protocol(self.alice, 'ORDERS', {'turn': 2, 'orders': []})
        self.protocol(self.alice, 'RESOLUTION_DONE', {'turn': 2})
        self.service.close()
        db = sqlite3.connect(self.path)
        old = time.time() - 5 * 86400
        state = json.loads(db.execute('SELECT state_json FROM matches').fetchone()[0])
        state.update(created=old, ended=old + 120)
        db.execute('UPDATE matches SET state_json=?', (json.dumps(state),))
        db.execute('UPDATE profiles SET created=?', (old,))
        db.execute('UPDATE presence SET seen=?', (old + 30,))
        for table in ('tracking_activity', 'tracking_samples', 'tracking_clients', 'tracking_visits', 'tracking_performance', 'tracking_errors', 'tracking_meta'):
            db.execute('DELETE FROM '+table)
        db.commit(); db.close()
        self.service = Service(self.path, self.config)
        report = self.service.metrics(self.admin())
        self.assertEqual(report['totals']['profiles'], 2)
        self.assertEqual(report['totals']['turns'], 2)
        historical = next(r for r in report['daily'] if r['day'] == day_at(old))
        self.assertEqual(historical['active_users'], 2)
        self.assertEqual(historical['matches_completed'], 1)
        self.assertIsNone(historical['peak_online'])
        self.assertIsNone(historical['online_seconds'])
        before = self.service.store.db.execute('SELECT COUNT(*) FROM tracking_activity').fetchone()[0]
        self.service.close(); self.service = Service(self.path, self.config)
        self.assertEqual(self.service.store.db.execute('SELECT COUNT(*) FROM tracking_activity').fetchone()[0], before)

    def test_match_and_chat_totals_come_from_authoritative_records(self):
        self.start()
        self.command(self.alice, 'chat', hex=self.service.chat_codec.envelope('SEND_MESSAGE_TO_CLIENT_REQUEST', {'toNickname': 'Bob', 'message': 'hello'}).hex())
        self.protocol(self.alice, 'SURRENDER', {})
        report = self.service.metrics(self.admin())
        self.assertEqual(report['matches']['started'], 1)
        self.assertEqual(report['matches']['completed'], 1)
        self.assertEqual(report['matches']['surrendered'], 1)
        self.assertEqual(report['matches']['cpu'], 1)
        self.assertEqual(report['totals']['chat_messages'], 1)
        self.assertEqual(sum(r['chat_messages'] for r in report['daily']), 1)

    def test_client_round_trip_samples_exclude_poll_waits(self):
        body = {'session': self.alice['session'], 'events': [
            {'id': 'rtt-command', 'kind': 'latency', 'route': 'command', 'elapsed_ms': 250},
            {'id': 'rtt-poll', 'kind': 'latency', 'route': 'poll', 'elapsed_ms': 20000}]}
        self.service.telemetry(body)
        report = self.service.metrics(self.admin())
        timings = [r for r in report['performance'] if r['kind'] == 'client_latency']
        self.assertEqual(len(timings), 1)
        self.assertEqual(timings[0]['name'], 'command')
        self.assertEqual(timings[0]['mean_ms'], 250)

    def test_http_tracking_and_operator_dashboard_do_not_expose_private_data(self):
        from functools import partial
        from threading import Thread
        from urllib.request import Request, urlopen
        from backend.server import BackendHTTPServer, Handler
        from tools.game_config import ROOT

        class QuietHandler(Handler):
            def log_message(self, *args): pass

        server = BackendHTTPServer(('127.0.0.1', 0), partial(QuietHandler, directory=str(ROOT)))
        server.service = self.service
        thread = Thread(target=server.serve_forever, daemon=True); thread.start()
        origin = 'http://127.0.0.1:' + str(server.server_port)
        def post(route, body):
            with urlopen(Request(origin + route, data=json.dumps(body).encode(), headers={'Content-Type': 'application/json'})) as response:
                return json.load(response)
        try:
            with urlopen(origin + '/admin.html') as response:
                self.assertIn('Tableau de bord', response.read().decode())
            denied = post('/api/metrics', {'session': self.bob['session']})
            self.assertEqual(denied['code'], 'ACTIVITY_FORBIDDEN')
            accepted = post('/api/telemetry', {'session': self.alice['session'], 'events': [
                {'id': 'http-client-error', 'kind': 'error', 'code': 'TEST_ERROR', 'message': 'network error'}]})
            self.assertEqual(accepted['accepted'], 1)
            report = post('/api/metrics', self.admin())
            self.assertTrue(any(r['name'] == 'POST /api/telemetry' for r in report['performance']))
            self.assertTrue(any(r['code'] == 'TEST_ERROR' for r in report['errors']))
            text = json.dumps(report)
            self.assertNotIn(self.alice['session'], text)
            self.assertNotIn(self.bob['session'], text)
        finally:
            server.shutdown(); server.server_close(); thread.join(timeout=2)

    def test_diagnostic_retry_storage_is_bounded_per_client(self):
        now = time.time()
        body = {'session': self.alice['session'], 'client_id': 'phone'}
        for batch in range(10):
            events = [{'id': str(batch * 20 + i), 'kind': 'latency', 'route': 'command', 'elapsed_ms': 10} for i in range(20)]
            with patch('time.time', return_value=now + batch * 61):
                self.assertEqual(self.service.telemetry({**body, 'events': events})['accepted'], 20)
        count = self.service.store.db.execute('SELECT COUNT(*) FROM tracking_receipts').fetchone()[0]
        self.assertEqual(count, 128)
        self.assertEqual(self.service.telemetry({**body, 'events': events})['duplicates'], 20)

    def test_stats_cli_reads_history_without_starting_simulator(self):
        self.service.tracking.flush(force=True)
        result = subprocess.run([sys.executable, '-m', 'backend.manage', '--database', str(self.path), 'stats', '--days', '7'], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['totals']['profiles'], 2)

    def test_stats_cli_never_resets_an_older_database(self):
        other = Path(self.directory.name) / 'old.sqlite'
        with closing(sqlite3.connect(other)) as db:
            db.executescript("CREATE TABLE schema_versions(version INTEGER); INSERT INTO schema_versions VALUES(5); CREATE TABLE saved_data(value TEXT); INSERT INTO saved_data VALUES('keep me');")
            db.commit()
        result = subprocess.run([sys.executable, '-m', 'backend.manage', '--database', str(other), 'stats'], capture_output=True, text=True, timeout=10)
        self.assertNotEqual(result.returncode, 0)
        with closing(sqlite3.connect(other)) as db:
            self.assertEqual(db.execute('SELECT value FROM saved_data').fetchone()[0], 'keep me')
