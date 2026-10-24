"""Public tournament schedule, private confirmations, and HTTP access."""
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from urllib.request import Request, urlopen
from unittest.mock import patch

from backend.server import BackendHTTPServer, Handler
from backend.service import Service
from backend.storage import ServiceError
from tests.test_backend import initial_club
from tools.game_config import load_config


class PublicTournamentTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name) / 'state.sqlite'
        self.now = int(time.time())
        self.clock = patch('backend.tournaments.time.time', side_effect=lambda: self.now)
        self.clock.start()
        self.config = load_config()
        self.config['general']['tournament'].update(
            enabled=True, id=1, format='league', start_time=self.now + 60,
            end_time=self.now + 660, repeat_seconds=3600, stadium_rotation=[3, 4])
        self.config['general']['cinematics']['introductions'] = False
        self.service = self.start_service()
        self.alice = self.service.hello({'nickname': 'Alice', 'clubs': [initial_club()]})
        self.bob = self.service.hello({'nickname': 'Bob', 'clubs': [initial_club()]})

    def start_service(self):
        service = Service(self.path, self.config)
        service.stopping.set()
        service.maintenance.join()
        return service

    def tearDown(self):
        self.service.close()
        self.clock.stop()
        self.directory.cleanup()

    def confirm(self, player, participating=True, **fields):
        return self.service.public_tournaments({'action': 'participate', 'session': player['session'],
                                               'tournament_id': '1', 'participating': participating, **fields})

    def test_public_schedule_rules_stadium_ids_and_anonymous_privacy(self):
        result = self.service.public_tournaments()
        self.assertIsNone(result['viewer'])
        event = result['tournaments'][0]
        self.assertEqual(event['stadium'], 'BEACH')
        self.assertEqual(len(result['tournaments']), 1)
        self.assertEqual(event['start_time'], self.now + 60)
        self.assertEqual(event['match_rules']['turns_per_match'], self.config['rules']['match']['turns_per_match'])
        self.assertEqual(event['points'], {'win': 3, 'draw': 1, 'loss': 0})
        self.assertFalse(event['participating'])
        self.assertNotIn('settings', event)
        self.assertNotIn('session', result)

    def test_only_current_and_next_tournaments_are_exposed(self):
        self.now += 60
        result = self.service.public_tournaments()
        self.assertEqual([(e['id'], e['phase']) for e in result['tournaments']], [('1', 'open'), ('2', 'upcoming')])
        self.assertEqual(result['tournaments'][1]['stadium'], 'BONTA')
        self.assertGreater(self.service.store.db.execute('SELECT COUNT(*) FROM tournaments').fetchone()[0], 2)

    def test_confirmation_is_private_idempotent_persistent_and_not_competitive_entry(self):
        for _ in range(2):
            result = self.confirm(self.alice)
        event = result['tournaments'][0]
        self.assertTrue(event['participating'])
        self.assertEqual(event['interested'], 1)
        self.assertEqual(event['participants'], 0)
        for table in ('tournament_participants', 'matchmaking_queue', 'tournament_rewards'):
            self.assertEqual(self.service.store.db.execute('SELECT COUNT(*) FROM ' + table).fetchone()[0], 0)
        self.assertFalse(self.service.public_tournaments()['tournaments'][0]['participating'])
        self.assertFalse(self.service.public_tournaments({'session': self.bob['session']})['tournaments'][0]['participating'])
        self.service.close()
        self.service = self.start_service()
        self.assertTrue(self.service.public_tournaments({'session': self.alice['session']})['tournaments'][0]['participating'])
        self.assertEqual(self.confirm(self.alice, False)['tournaments'][0]['interested'], 0)

    def test_authentication_validation_rating_and_closed_events(self):
        with self.assertRaises(ServiceError):
            self.service.public_tournaments({'action': 'participate', 'tournament_id': '1', 'participating': True})
        for fields in ({'participating': 'yes'}, {'tournament_id': None}, {'tournament_id': True}, {'tournament_id': -1}):
            with self.assertRaises(ServiceError):
                self.confirm(self.alice, **fields)
        cfg = self.service.tournament_config(1)
        cfg['min_rating'] = 100000
        self.service.store.db.execute('UPDATE tournaments SET settings_json=? WHERE id=1', (json.dumps(cfg),))
        with self.assertRaises(ServiceError) as error:
            self.confirm(self.alice)
        self.assertEqual(error.exception.code, 'TOURNAMENT_RATING')
        self.now += 661
        with self.assertRaises(ServiceError) as error:
            self.confirm(self.alice)
        self.assertEqual(error.exception.code, 'TOURNAMENT_CLOSED')

    def test_top_ten_excludes_private_profile_ids_and_respects_actual_ranks(self):
        self.now += 60
        self.service.public_tournaments()
        cfg = self.service.tournament_config(1)
        profiles = []
        for i in range(12):
            profile, _ = self.service.create_device({'nickname': f'Player {i:02d}', 'clubs': [initial_club()]})
            profiles.append(profile)
            self.service.register_tournament(profile, cfg)
        match = {'profiles': [profiles[-1], profiles[0]], 'tournament': 1, 'created': self.now,
                 'phase': 'ended', 'score': [2, 0], 'mode': 'ranked', 'source': 'tournament', 'result_policy_version': 1}
        self.service.store.db.execute('INSERT INTO matches(state_json,updated) VALUES(?,?)', (json.dumps(match), self.now))
        event = self.service.public_tournaments()['tournaments'][0]
        self.assertEqual(event['participants'], 12)
        self.assertEqual(len(event['standings']), 10)
        self.assertEqual([e['rank'] for e in event['standings']], list(range(1, 11)))
        self.assertEqual(event['standings'][0]['nickname'], 'Player 11')
        self.assertEqual(event['standings'][0]['points'], 3)
        self.assertEqual(set(event['standings'][0]), {'rank', 'nickname', 'club', 'points', 'eliminated'})

    def test_disabled_tournaments_and_replaced_schedule_remove_confirmations_safely(self):
        self.confirm(self.alice)
        self.service.store.db.execute('DELETE FROM tournaments WHERE id=1')
        self.assertEqual(self.service.store.db.execute('SELECT COUNT(*) FROM tournament_intentions').fetchone()[0], 0)
        self.config['general']['tournament']['enabled'] = False
        self.service.config['general']['tournament']['enabled'] = False
        self.assertEqual(self.service.public_tournaments()['tournaments'], [])

    def test_public_rules_include_tournament_overrides_and_elimination_round_times(self):
        cfg = self.service.tournament_config(1)
        cfg.update(format='elimination', qualification_seconds=120, qualifying_top=4,
                   round_count=2, round_seconds=120, match_rules={'planning_seconds': 17})
        self.service.store.db.execute('UPDATE tournaments SET settings_json=? WHERE id=1', (json.dumps(cfg),))
        event = self.service.public_tournaments()['tournaments'][0]
        self.assertEqual(event['match_rules']['planning_seconds'], 17)
        self.assertEqual(event['rounds'][0]['startTime'], cfg['start_time'] * 1000)
        self.assertEqual(len(event['rounds']), 3)
        self.assertEqual(event['qualifying_top'], 4)

    def test_logout_revokes_only_website_session_without_leaving_game_queue(self):
        profile = self.service.store.authenticate(self.alice['session'])
        website_token = self.service.store.issue_session(profile, 'account')
        self.now += 60
        self.service.tournament_match(profile, 1)
        self.service.public_tournaments({'action': 'logout', 'session': website_token})
        self.assertEqual(self.service.matchmaking_status(profile)['status'], 'waiting')
        self.assertEqual(self.service.store.authenticate(self.alice['session']), profile)
        with self.assertRaises(ServiceError):
            self.service.store.authenticate(website_token)

    def test_http_get_and_authenticated_post(self):
        server = BackendHTTPServer(('127.0.0.1', 0), Handler)
        server.service = self.service
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            url = f'http://127.0.0.1:{server.server_port}/api/tournaments'
            with urlopen(url) as response:
                self.assertEqual(response.headers['Cache-Control'], 'no-store')
                self.assertTrue(json.load(response)['ok'])
            request = Request(url, json.dumps({'action': 'participate', 'session': self.alice['session'],
                              'tournament_id': '1', 'participating': True}).encode(), {'Content-Type': 'application/json'})
            with urlopen(request) as response:
                self.assertTrue(json.load(response)['tournaments'][0]['participating'])
        finally:
            server.shutdown()
            server.server_close()
            thread.join()
