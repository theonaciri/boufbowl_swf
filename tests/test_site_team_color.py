"""Website-only kit override must not recolor other characters."""
import json
import unittest
from tools.build_restoration_data import audit
from tools.site_portraits import ROOT, POSES, export_plan, capture_source


class TeamColorTests(unittest.TestCase):
    def test_only_evangelyne_gets_black_kit_in_every_pose(self):
        tasks = export_plan(audit()['characters'], json.loads((ROOT/'resources/palettes.json').read_text()))
        overridden = [task for task in tasks if 'team_color' in task]
        self.assertEqual(len(overridden), len(POSES))
        self.assertEqual({task['hero'] for task in overridden}, {508})
        self.assertEqual({task['team_color'] for task in overridden}, {'000000'})
        source = capture_source()
        self.assertEqual(source.count('Color3.fromRgbUInt(hero==508 ? 0x000000 : (0x3578cf))'), 2)
