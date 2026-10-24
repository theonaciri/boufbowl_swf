"""Anonymous ladder pagination uses the game's ordering and public fields."""
import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.request import urlopen

from backend.server import BackendHTTPServer, Handler
from backend.service import Service
from backend.storage import ServiceError
from tests.test_backend import initial_club
from tools.game_config import load_config


class PublicLadderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        config = load_config()
        config['general']['tournament']['enabled'] = False
        self.service = Service(Path(self.tmp.name) / 'state.sqlite', config)
        self.service.stopping.set()
        self.service.maintenance.join()

    def tearDown(self):
        self.service.close()
        self.tmp.cleanup()

    def seed(self, count):
        for i in range(count):
            profile, _ = self.service.create_device({'nickname': f'Joueur {i:02d}', 'clubs': [initial_club()]})
            stats = self.service.store.profile(profile)['statistics']
            stats.update(rating=1000 + i // 3 * 20, wins=i % 5, draws=i % 3, defeats=i % 4)
            self.service.store.db.execute('UPDATE profiles SET statistics_json=? WHERE id=?', (json.dumps(stats), profile))

    def test_three_pages_reuse_game_order_and_absolute_ranks_without_duplicates(self):
        self.seed(23)
        pages = [self.service.public_ladder(i) for i in (1, 2, 3)]
        self.assertEqual([len(p['players']) for p in pages], [10, 10, 3])
        self.assertEqual([p['page'] for p in pages], [1, 2, 3])
        self.assertTrue(all(p['pages'] == 3 and p['total'] == 23 and p['page_size'] == 10 for p in pages))
        players = [p for page in pages for p in page['players']]
        expected = self.service.rankings()
        self.assertEqual([p['nickname'] for p in players], [r['player']['nickname'] for r in expected])
        self.assertEqual([p['rank'] for p in players], list(range(1, 24)))
        self.assertEqual([p['rating'] for p in players], [r['rating'] for r in expected])
        self.assertEqual(len(set(p['nickname'] for p in players)), 23)
        self.assertEqual(set(players[0]), {'rank', 'nickname', 'club', 'rating', 'wins', 'draws', 'losses', 'league', 'qualified'})
        self.assertNotIn('session', pages[0])

    def test_empty_ladder_and_out_of_range_page_are_safe(self):
        empty = self.service.public_ladder()
        self.assertEqual((empty['page'], empty['pages'], empty['total'], empty['players']), (1, 1, 0, []))
        self.seed(11)
        last = self.service.public_ladder(500)
        self.assertEqual((last['page'], len(last['players']), last['players'][0]['rank']), (2, 1, 11))

    def test_invalid_pages_are_rejected(self):
        for page in (True, False, None, 0, -1, 1.5, '', 'abc', '1.0', '١', '9' * 100, 2147483648):
            with self.subTest(page=page), self.assertRaises(ServiceError):
                self.service.public_ladder(page)
        self.assertEqual(self.service.public_ladder('1')['page'], 1)

    def test_http_pagination_and_errors_require_no_session(self):
        self.seed(11)
        server = BackendHTTPServer(('127.0.0.1', 0), Handler)
        server.service = self.service
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            url = f'http://127.0.0.1:{server.server_port}/api/ladder'
            with urlopen(url + '?page=2') as response:
                self.assertEqual(response.headers['Cache-Control'], 'no-store')
                page = json.load(response)
                self.assertTrue(page['ok'])
                self.assertEqual(page['players'][0]['rank'], 11)
            for query in ('?page=no', '?page=0', '?page=', '?page=1&page=2'):
                with urlopen(url + query) as response:
                    result = json.load(response)
                    self.assertFalse(result['ok'])
                    self.assertEqual(result['code'], 'PAGE_INVALID')
        finally:
            server.shutdown()
            server.server_close()
            thread.join()
