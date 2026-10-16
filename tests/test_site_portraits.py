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

    def test_special_characters_keep_all_eighteen_distinct_pose_exports(self):
        data = manifest()
        for hero in range(513, 519):
            with self.subTest(hero=hero):
                exports = [e for e in data['exports'] if e['hero'] == hero]
                self.assertEqual({e['pose'] for e in exports}, set(POSES))
                # The old Jack exports reused the same bitmap for two actions.
                self.assertEqual(len({e['sha256'] for e in exports}), len(POSES))

    def test_cache_only_invalidates_changed_character_colors_or_renderer(self):
        from copy import deepcopy
        from tools.site_portraits import render_fingerprint
        settings=json.loads((ROOT/'resources/palettes.json').read_text())
        characters=json.loads((ROOT/'assets/site/restoration/inventory.json').read_text())['characters']
        baseline=export_plan(characters,settings)
        changed=deepcopy(settings)
        palette=changed['class_palettes'][0]
        palette.setdefault('defaults',{}).setdefault('male',{})['hair']='123456'
        updated=export_plan(characters,changed)
        inputs={'tools/site_portrait_capture.js':'renderer-one'}
        affected=[]
        for before,after in zip(baseline,updated):
            if render_fingerprint(before,inputs)!=render_fingerprint(after,inputs):affected.append(before)
        self.assertEqual(len(affected),len(POSES))
        self.assertTrue(all(t['cls']==palette['class_id'] and t['gender']==1 and not t['hero'] for t in affected))
        self.assertNotEqual(render_fingerprint(baseline[0],inputs),render_fingerprint(baseline[0],{'tools/site_portrait_capture.js':'renderer-two'}))

    def test_cache_rejects_missing_legacy_or_modified_images(self):
        import hashlib
        from pathlib import Path
        import tempfile
        from tools.site_portraits import render_fingerprint, reusable
        task={'id':'example','pose':'default'}
        inputs={'renderer':'one'}
        original=ROOT/'assets/site/restoration/cra-1-default.webp'
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary)/'portrait.webp'
            entry={**task,'render_fingerprint':render_fingerprint(task,inputs),'sha256':hashlib.sha256(original.read_bytes()).hexdigest()}
            self.assertFalse(reusable(task,entry,path,inputs))
            path.write_bytes(original.read_bytes())
            self.assertTrue(reusable(task,entry,path,inputs))
            legacy=dict(entry);legacy.pop('render_fingerprint')
            self.assertFalse(reusable(task,legacy,path,inputs))
            path.write_bytes(b'broken image')
            self.assertFalse(reusable(task,entry,path,inputs))
