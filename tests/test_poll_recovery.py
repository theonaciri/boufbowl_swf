"""Mobile outages, selective delivery and simulation concurrency regressions."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event
import time
import unittest
from unittest.mock import patch

from backend.service import Service
from backend.storage import ServiceError
from tests import test_backend as helpers


class PollRecoveryTests(unittest.TestCase):
    setUp = helpers.BackendTests.setUp
    tearDown = helpers.BackendTests.tearDown
    command = helpers.BackendTests.command
    protocol = helpers.BackendTests.protocol
    identity = helpers.BackendTests.identity
    start = helpers.BackendTests.start

    def cursor(self, player):
        with self.service.store.lock:
            return self.service.store.db.execute('SELECT COALESCE(MAX(seq),0) FROM events WHERE profile_id=?',
                                                 (self.identity(player),)).fetchone()[0]

    def wait_for_polls(self, count):
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            with self.service.store.lock:
                if sum(n for _, n in self.service.store.waiters.values()) == count:
                    return
            time.sleep(.005)
        self.fail('Polls did not begin waiting')

    def test_only_event_recipients_wake_and_rollback_does_not_publish(self):
        store = self.service.store
        with ThreadPoolExecutor(2) as pool:
            futures = [pool.submit(self.service.poll, {'session': p['session'], 'cursor': self.cursor(p),
                                                       'wait_ms': 20000, 'compact': True})
                       for p in (self.alice, self.bob)]
            try:
                self.wait_for_polls(2)
                with patch.object(store, 'notify', wraps=store.notify) as notify:
                    with store.transaction():
                        store.db.execute('UPDATE presence SET seen=seen')
                    notify.assert_not_called()
                    with self.assertRaisesRegex(ValueError, 'rollback'):
                        with store.transaction():
                            self.service.emit(self.identity(self.alice), 'PING_RESULT', {'timestamp': 1})
                            raise ValueError('rollback')
                    notify.assert_not_called()
                    with store.transaction():
                        self.service.emit(self.identity(self.bob), 'PING_RESULT', {'timestamp': 2})
                    notify.assert_called_once_with(self.identity(self.bob))
                self.assertEqual(futures[1].result(timeout=1)['events'][0]['type'], 'PING_RESULT')
                self.assertFalse(futures[0].done())
            finally:
                with store.transaction():
                    self.service.emit(self.identity(self.alice), 'PING_RESULT', {'timestamp': 3})
                futures[0].result(timeout=1)
        self.assertEqual(store.waiters, {})

    def test_compact_empty_polls_do_not_write_or_run_maintenance(self):
        body = {'session': self.alice['session'], 'cursor': self.cursor(self.alice), 'compact': True}
        statements = []
        self.service.store.db.set_trace_callback(statements.append)
        try:
            with patch.object(self.service, 'match_queued_players') as pairing, \
                 patch.object(self.service, 'maintain_tournaments') as tournaments, \
                 patch.object(self.service, 'public_profile') as profile:
                for _ in range(20):
                    self.assertEqual(self.service.poll(body)['events'], [])
                pairing.assert_not_called()
                tournaments.assert_not_called()
                profile.assert_not_called()
        finally:
            self.service.store.db.set_trace_callback(None)
        self.assertFalse(any(s.startswith(('BEGIN', 'UPDATE', 'INSERT', 'DELETE')) for s in statements))

    def test_twenty_second_outage_keeps_queue_and_delivers_chat(self):
        self.command(self.alice, 'queue_join')
        before = self.cursor(self.alice)
        now = time.time()
        # Includes a 20s long poll followed by 20s without a network.
        with patch('time.time', return_value=now + 40):
            self.command(self.bob, 'chat', hex=self.service.chat_codec.envelope('SEND_MESSAGE_TO_CHANNEL_REQUEST', {
                'toChannel': {'channelType': 2, 'lang': 'en'}, 'message': 'still here'}).hex())
            response = self.service.poll({'session': self.alice['session'], 'cursor': before, 'compact': True})
        self.assertEqual(response['matchmaking']['status'], 'waiting')
        self.assertIn('RECEIVE_FROM_CHANNEL', [e['type'] for e in response['events']])

    def test_lost_command_response_retries_without_resolving_twice(self):
        self.start()
        before = self.cursor(self.alice)
        body = {'session': self.alice['session'], 'request_id': 'lost-response', 'operation': 'protocol',
                'hex': self.service.codec.envelope('ORDERS', {'turn': 1, 'orders': []}).hex()}
        accepted = self.service.command(body)  # Response never reaches the phone.
        self.service.resolution_queue.join()
        now = time.time()
        with patch('time.time', return_value=now + 20):
            self.assertEqual(self.service.command(body), accepted)
            events = self.service.poll({'session': self.alice['session'], 'cursor': before})['events']
        self.assertEqual([e['type'] for e in events].count('RESOLUTION_SCENARIO'), 1)
        self.assertEqual(self.service.store.db.execute('SELECT COUNT(*) FROM turns').fetchone()[0], 1)
        self.assertEqual(self.service.store.active_match(self.identity(self.alice))['phase'], 'resolution')
        # Losing the poll response also does not consume its durable events.
        replayed = self.service.poll({'session': self.alice['session'], 'cursor': before})['events']
        self.assertEqual([e['seq'] for e in replayed], [e['seq'] for e in events])
        self.assertEqual(self.service.poll({'session': self.alice['session'], 'cursor': events[-1]['seq']})['events'], [])

    def test_delayed_field_state_uses_remaining_server_deadline(self):
        self.start()
        self.protocol(self.alice, 'ORDERS', {'turn': 1, 'orders': []})
        before = self.cursor(self.alice)
        self.protocol(self.alice, 'RESOLUTION_DONE', {'turn': 1})
        now = time.time()
        with patch('time.time', return_value=now + 20):
            events = self.service.poll({'session': self.alice['session'], 'cursor': before})['events']
        packet = next(e for e in events if e['type'] == 'FIELD_STATE')
        state = self.service.codec.open_envelope(bytes.fromhex(packet['hex']))['payload']
        expected = self.config['rules']['match']['planning_seconds'] * 1000 - 20000
        self.assertAlmostEqual(state['phaseInfos']['remainingTime'], expected, delta=100)

    def test_slow_simulation_does_not_block_other_players_or_duplicate_retry(self):
        self.start()
        entered, release = Event(), Event()
        simulate = self.service.engine.simulate
        body = {'session': self.alice['session'], 'request_id': 'slow-turn', 'operation': 'protocol',
                'hex': self.service.codec.envelope('ORDERS', {'turn': 1, 'orders': []}).hex()}

        def slow(*args):
            entered.set()
            if not release.wait(3):
                raise RuntimeError('Test did not release simulation')
            return simulate(*args)

        with patch.object(self.service.engine, 'simulate', side_effect=slow) as engine, ThreadPoolExecutor(3) as pool:
            future = pool.submit(self.service.command, body)
            try:
                self.assertTrue(entered.wait(1))
                self.assertTrue(future.result(timeout=1)['ok'])
                other = pool.submit(self.service.poll, {'session': self.bob['session'], 'cursor': self.cursor(self.bob)})
                self.assertTrue(other.result(timeout=1)['ok'])
                retry = pool.submit(self.service.command, body)
                self.assertTrue(retry.result(timeout=1)['ok'])
                self.assertEqual(engine.call_count, 1)
            finally:
                release.set()
            self.assertTrue(future.result(timeout=2)['ok'])
            self.service.resolution_queue.join()
        self.assertEqual(self.service.store.active_match(self.identity(self.alice))['phase'], 'resolution')

    def test_interrupted_simulation_recovers_committed_orders_and_seed_after_restart(self):
        match = self.start()
        with self.service.store.transaction():
            self.service.resolve(match)
            # Model process death after commit, before its deferred worker runs.
            self.service.store.commit_callbacks.clear()
        seed = match['turn_seeds']['1']
        self.service.close()
        self.service = Service(self.path, self.config)
        self.service.maintain_once()
        self.service.resolution_queue.join()
        restored = self.service.store.match(match['id'])
        self.assertEqual(restored['phase'], 'resolution')
        self.assertEqual(restored['turn_seeds']['1'], seed)
        self.assertEqual(self.service.store.db.execute('SELECT COUNT(*) FROM turns').fetchone()[0], 1)

    def test_chat_returns_immediately_from_a_twenty_second_poll(self):
        before = self.cursor(self.bob)
        with ThreadPoolExecutor(1) as pool:
            future = pool.submit(self.service.poll, {'session': self.bob['session'], 'cursor': before,
                                                     'wait_ms': 20000, 'compact': True})
            self.wait_for_polls(1)
            with patch.object(self.service, 'public_profile', wraps=self.service.public_profile) as profile:
                started = time.monotonic()
                self.command(self.alice, 'chat', hex=self.service.chat_codec.envelope('SEND_MESSAGE_TO_CLIENT_REQUEST', {
                    'toNickname': 'Bob', 'message': 'instant chat'}).hex())
                response = future.result(timeout=1)
                elapsed = time.monotonic() - started
                profile.assert_called_once()  # Sender command metadata only.
            self.assertLess(elapsed, .5)
            self.assertEqual([e['type'] for e in response['events']], ['RECEIVE_FROM_CLIENT'])

    def test_surrender_during_simulation_cannot_publish_a_stale_turn(self):
        match = self.start()
        entered, release = Event(), Event()
        simulate = self.service.engine.simulate

        def slow(*args):
            entered.set()
            release.wait(3)
            return simulate(*args)

        with patch.object(self.service.engine, 'simulate', side_effect=slow):
            self.service.command({'session': self.alice['session'], 'request_id': 'pending-turn', 'operation': 'protocol',
                                  'hex': self.service.codec.envelope('ORDERS', {'turn': 1, 'orders': []}).hex()})
            try:
                self.assertTrue(entered.wait(1))
                # Use the API directly: a surrender must not wait for the job.
                response = self.service.command({'session': self.alice['session'], 'request_id': 'surrender',
                                                'operation': 'protocol',
                                                'hex': self.service.codec.envelope('SURRENDER', {}).hex()})
                self.assertTrue(response['ok'])
            finally:
                release.set()
                self.service.resolution_queue.join()
        self.assertEqual(self.service.store.match(match['id'])['phase'], 'ended')
        self.assertEqual(self.service.store.db.execute('SELECT COUNT(*) FROM turns').fetchone()[0], 0)

    def test_transient_simulation_failure_retries_the_same_seed_and_orders(self):
        match = self.start()
        simulate = self.service.engine.simulate
        with patch.object(self.service.engine, 'simulate', side_effect=ServiceError('ENGINE_TIMEOUT', 'interrupted')), \
             self.assertLogs(level='ERROR'):
            self.protocol(self.alice, 'ORDERS', {'turn': 1, 'orders': []})
        saved = self.service.store.match(match['id'])
        self.assertEqual(saved['phase'], 'orders')
        with self.service.store.transaction():
            saved['deadline'] = time.time() - 1
            self.service.store.save_match(saved)
        with patch.object(self.service.engine, 'simulate', wraps=simulate) as retried:
            self.service.maintain_once()
            self.service.resolution_queue.join()
            self.assertEqual(retried.call_args.args[3], saved['turn_seeds']['1'])
            self.assertEqual(retried.call_args.args[1][0], saved['orders']['1'])
        self.assertEqual(self.service.store.match(match['id'])['phase'], 'resolution')

    def test_poll_validates_wait_and_cursor_before_sleeping(self):
        self.assertEqual(self.alice["poll_wait_ms"], 20000)
        for extra in ({'wait_ms': 20001}, {'wait_ms': True}, {'compact': 'yes'}, {'cursor': -1}):
            with self.subTest(extra=extra), self.assertRaises(ServiceError):
                self.service.poll({'session': self.alice['session'], 'cursor': self.cursor(self.alice), **extra})
