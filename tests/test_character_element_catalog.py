"""Character membership follows native frame labels, not guessed class names."""
import struct
import unittest
from tools.character_element_catalog import frames, inspect, memberships, is_common, puppet_entries, loading_profile, ROOT


def place(depth,identity):return (26,b'\x02'+struct.pack('<HH',depth,identity))


class CharacterElementCatalogTests(unittest.TestCase):
    def test_workshop_contains_runtime_puppet_parts_not_fullscreen_artwork(self):
        from tools.build_restoration_data import audit
        characters=audit()['characters'];entries=puppet_entries(characters)
        for parts in entries.values():
            self.assertTrue(parts)
            for entry in parts:
                self.assertTrue(entry['source'].startswith('assets/sprites/skins/'))
                self.assertIn(entry['kind'],('body','archive'))
                self.assertNotEqual(entry['name'],'colorGray_4_poulet_corps')
                self.assertFalse(entry['name'].lower().startswith('anim'))
        hair=next(e for e in entries['iop-1'] if e['name']=='cheveux_d')
        self.assertEqual(hair['source'],'assets/sprites/skins/61.swl')
        self.assertTrue(any(e['scope']=='shared' for e in entries['iop-1']))
        missing=[e for e in entries['ecaflip-1'] if e['scope']=='class']
        self.assertTrue(missing);self.assertTrue(all(e['status']=='missing' and 'image' not in e for e in missing))
        for character in characters:
            expected=[e for e in entries[character['id']] if e.get('status')=='missing']
            self.assertEqual(bool(expected),not character['body_available'])
        self.assertFalse(any(e['name']=='natte_2b' for e in entries['ecaflip-1']))
        missing_iop=[e for e in entries['iop-2'] if e.get('status')=='missing']
        self.assertEqual([e['name'] for e in missing_iop],['62.swl'])
        self.assertEqual(missing_iop[0]['kind'],'archive')
        self.assertFalse(missing_iop[0]['required_for_runtime'])
    def test_loading_requirements_follow_runtime_fallback_not_other_class_symbols(self):
        from tools.build_restoration_data import audit
        characters={c['id']:c for c in audit()['characters']}
        ecaflip=loading_profile(characters['ecaflip-1'])
        self.assertEqual([e['path'] for e in ecaflip['runtime_archives']],[f'assets/sprites/skins/{i}.swl' for i in (0,1,11)])
        self.assertTrue(ecaflip['fallback']);self.assertFalse(ecaflip['original_symbol_inventory_known'])
        self.assertFalse(ecaflip['individual_symbol_requirements_known'])
        iop=loading_profile(characters['iop-1'])
        self.assertFalse(iop['fallback']);self.assertEqual(iop['rendered_skin'],61)
        for character in characters.values():
            profile=loading_profile(character)
            self.assertTrue(all(e['present'] for e in profile['runtime_archives']))
            self.assertFalse(profile['individual_symbol_requirements_known'])
    def test_named_class_and_costume_parts_are_not_generic_shared_elements(self):
        everyone={i*10+g for i in range(1,15) for g in (1,2)}|{501,517}
        for name in ('colorGray_4_Sadida_slip_canar','colorGray_4_poupee_sadida','colorGray_4_build06_bras2_ironman','colorGray_4_Ballotin_meuf_jupe','colorGray_4_symbole54543','cheveux_f','AnimStatique_d'):
            with self.subTest(name=name):self.assertFalse(is_common(name,everyone))
        for name in ('tete_expression09_2B','colorGray_2_build02_pupille','colorGray_3_build01_bras1'):
            with self.subTest(name=name):self.assertTrue(is_common(name,everyone))
        self.assertFalse(is_common('colorGray_3_build01_bras1',{111,112,517}))
    def test_frame_depth_replacements_removals_and_nested_symbols(self):
        names={1:'first_class',2:'second_class',3:'nested_first',4:'shared',10:'boufbowler1_posing01'}
        timeline=[(43,b'cg_11\0'),place(1,1),place(2,4),(1,b''),(43,b'cg_21\0'),place(1,2),(1,b''),(28,struct.pack('<H',2)),(1,b'')]
        self.assertEqual(list(frames(timeline)),[('cg_11',{1,4}),('cg_21',{2,4}),('cg_21',{2})])
        result=memberships(names,{10:timeline,1:[place(1,3),(1,b'')]})
        self.assertEqual(result[11],{'first_class','nested_first','shared'})
        self.assertEqual(result[21],{'second_class','shared'})
        scenery=memberships({**names,10:'forest_colorizable'},{10:timeline,1:[place(1,3),(1,b'')]})
        self.assertFalse(scenery)
    def test_native_classes_and_legends_have_separate_original_elements(self):
        source=ROOT/'assets/artworks/cutscene-boufbowler-repository.swf'
        if not source.is_file():self.skipTest('Original archive unavailable')
        names,sprites=inspect(source);members=memberships(names,sprites)
        for identity in (11,12,21,22,61,62,141,142,501,513,518):self.assertTrue(members[identity])
        self.assertTrue(any('ecaflip' in n for n in members[22]));self.assertFalse(any('_cra_' in n for n in members[22]))
        self.assertTrue(any('zobal' in n for n in members[142]));self.assertFalse(any('brumen' in n for n in members[513]))
        names,sprites=inspect(ROOT/'assets/artworks/cutscene-illustration.swf');action=memberships(names,sprites)
        self.assertTrue(action[11]);self.assertFalse(any('colorGray_4_Sadida_slip_canar' in parts for parts in action.values()))
