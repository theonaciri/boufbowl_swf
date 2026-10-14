import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from tools.game_config import ROOT, STADIUMS, apply_resources, load_config
from tools.smoke_stadium_celebrations import goal_fixture
from tools.stadium_celebrations import celebrations


class StadiumCelebrationTests(unittest.TestCase):
    def test_every_stadium_has_its_available_original_animation(self):
        mapping = celebrations(ROOT)
        self.assertEqual(set(mapping), set(STADIUMS))
        self.assertEqual(mapping['BEACH']['animation'], 'Illustration_crabes_contents')
        for name in STADIUMS:
            replay = goal_fixture(name)
            self.assertEqual(replay['steps'][0]['decoded']['matchStadium'], STADIUMS.index(name) + 1)
            self.assertTrue(any(i['interactionDetails']['isCutscene'] for i in replay['steps'][2]['decoded']['interaction']))

    def test_geometry_fallback_does_not_replace_goal_celebrations(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            resources = root / 'resources'
            resources.mkdir()
            for name in ('config.json', 'stadiums.json', 'stadium_celebrations.json'):
                shutil.copyfile(ROOT / 'resources' / name, resources / name)
            (root / 'assets').symlink_to(ROOT / 'assets', target_is_directory=True)
            data = json.loads((resources / 'stadiums.json').read_text())
            for stadium in data['stadiums'].values():
                stadium['publicHappyCutsceneName'] = 'Illustration_foule_contente'
            (resources / 'stadiums.json').write_text(json.dumps(data))
            with patch('tools.visual_assets.prepare_stadiums', return_value={'BEACH': 'missing-model.dae'}):
                apply_resources(resources, load_config())
            generated = json.loads((resources / 'stadiums.json').read_text())['stadiums']
            self.assertEqual(generated['BEACH']['path'], generated['FARMSTEAD']['path'])
            for name, entry in celebrations(ROOT).items():
                self.assertEqual(generated[name]['publicHappyCutsceneName'], entry['animation'])
                self.assertEqual(generated[name]['publicHappySound'], entry['sound'])
