"""Character membership follows native frame labels, not guessed class names."""
import struct
import unittest
from tools.character_element_catalog import frames, inspect, memberships, ROOT


def place(depth,identity):return (26,b'\x02'+struct.pack('<HH',depth,identity))


class CharacterElementCatalogTests(unittest.TestCase):
    def test_frame_depth_replacements_removals_and_nested_symbols(self):
        names={1:'first_class',2:'second_class',3:'nested_first',4:'shared'}
        timeline=[(43,b'cg_11\0'),place(1,1),place(2,4),(1,b''),(43,b'cg_21\0'),place(1,2),(1,b''),(28,struct.pack('<H',2)),(1,b'')]
        self.assertEqual(list(frames(timeline)),[('cg_11',{1,4}),('cg_21',{2,4}),('cg_21',{2})])
        result=memberships(names,{10:timeline,1:[place(1,3),(1,b'')]})
        self.assertEqual(result[11],{'first_class','nested_first','shared'})
        self.assertEqual(result[21],{'second_class','shared'})
    def test_native_classes_and_legends_have_separate_original_elements(self):
        source=ROOT/'assets/artworks/cutscene-boufbowler-repository.swf'
        if not source.is_file():self.skipTest('Original archive unavailable')
        names,sprites=inspect(source);members=memberships(names,sprites)
        for identity in (11,12,21,22,61,62,141,142,501,513,518):self.assertTrue(members[identity])
        self.assertTrue(any('ecaflip' in n for n in members[22]));self.assertFalse(any('_cra_' in n for n in members[22]))
        self.assertTrue(any('zobal' in n for n in members[142]));self.assertFalse(any('brumen' in n for n in members[513]))
