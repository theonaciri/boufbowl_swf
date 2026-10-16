"""Native portrait exports must follow the editor defaults and retain 2× detail."""
import json
import unittest
from tools.site_portraits import ROOT, POSES, export_plan, manifest


class SitePortraitTests(unittest.TestCase):
    def test_default_palette_priority_gender_and_special_character_colors(self):
        characters = [
            {'id': 'class-f', 'class_id': 1, 'gender': 2, 'hero': 0},
            {'id': 'hero', 'class_id': 1, 'gender': 2, 'hero': 502},
        ]
        settings = {
            'class_palettes': [
                {'id': 1, 'class_id': 1, 'style': 'Dofus',
                 'hair': ['111111', '222222'], 'eyes': ['333333', '444444'], 'skin': ['555555', '666666'],
                 'defaults': {'female': {'hair': '111111', 'eyes': '444444', 'skin': '555555'}}},
                {'id': 2, 'class_id': 1, 'style': 'Wakfu',
                 'hair': ['aaaaaa'], 'eyes': ['bbbbbb'], 'skin': ['cccccc']},
            ],
            'hero_palettes': [{'id': 16, 'unique_character': 502,
                               'hair': ['192747'], 'eyes': ['793e94'], 'skin': ['e7b98c']}],
        }
        plan = export_plan(characters, settings)
        self.assertEqual(len(plan), 2 * len(POSES))
        self.assertEqual(plan[0]['id'], 'class-f-default')
        self.assertEqual(plan[0]['palette'], 1)
        self.assertEqual(plan[0]['colors'], {'hair': '111111', 'eyes': '444444', 'skin': '555555'})
        self.assertTrue(all(t['palette'] == 16 for t in plan if t['hero']))
        self.assertTrue(all(t['colors']['eyes'] == '793e94' for t in plan if t['hero']))

    def test_all_characters_have_all_native_poses_at_double_resolution(self):
        data = manifest()
        characters = json.loads((ROOT/'assets/site/restoration/inventory.json').read_text())['characters']
        self.assertEqual(len(data['exports']), len(characters)*len(POSES))
        self.assertEqual(len({p['path'] for p in data['exports']}), len(data['exports']))
        for portrait in data['exports']:
            self.assertEqual(portrait['height'], 2*data['render']['previous_canvas_height'])
            self.assertGreater(portrait['width'], 80)
            self.assertGreater((ROOT/portrait['path']).stat().st_size, 1024)
