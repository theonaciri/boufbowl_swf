"""Reconstructed assets require a real installed file and an explicit quality review."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from tools.character_asset_status import annotate
from tools.export_character_previews import find_preview


class CharacterAssetStatusTests(unittest.TestCase):
    def test_sprite_one_uses_its_symbol_directory_not_another_sprite_frame_one(self):
        other=Path('sprites/DefineSprite_42_other/1.png');correct=Path('sprites/DefineSprite_1_hair/1.png')
        self.assertEqual(find_preview([other,correct],1),correct)
        self.assertIsNone(find_preview([other],1))
    def test_quality_never_turns_an_absent_file_into_a_restored_asset(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);(root/'resources').mkdir();relative='assets/sprites/restoration-elements/21/cheveux.swf'
            (root/'resources/asset-restorations.json').write_text(json.dumps({'assets':{relative:{'quality':'good'}}}))
            catalog={'characters':{'cat':[{'name':'cheveux','status':'original','image':'reference.webp'}]}}
            result=annotate(catalog,[{'id':'cat','body_available':False,'body_path':'assets/sprites/skins/21.swl'}],root)
            self.assertEqual(result['characters']['cat'][0]['target_status'],'missing')
            self.assertEqual(result['characters']['cat'][0]['status'],'original')
    def test_installed_asset_quality_is_explicit_and_unreviewed_by_default(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);(root/'resources').mkdir();relative='assets/sprites/restoration-elements/21/cheveux.swf';path=root/relative;path.parent.mkdir(parents=True);path.write_bytes(b'test')
            fingerprint=hashlib.sha256(b'test'+b'part-preview-1').hexdigest();preview=root/f'assets/site/restoration/elements/previews/restored-{fingerprint[:24]}.webp';preview.parent.mkdir(parents=True);preview.write_bytes(b'cached-preview')
            for quality,state in ((None,'restored_unreviewed'),('good','restored_good'),('low','restored_low_quality')):
                (root/'resources/asset-restorations.json').write_text(json.dumps({'assets':{relative:{'quality':quality}}}))
                entry={'name':'cheveux','status':'original'};annotate({'characters':{'cat':[entry]}},[{'id':'cat','body_available':False,'body_path':'assets/sprites/skins/21.swl'}],root,check=True)
                self.assertEqual(entry['target_status'],state);self.assertEqual(entry['restored_image'],preview.relative_to(root).as_posix())
