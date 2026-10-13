import json
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET
from tools.game_config import ROOT, load_config, startup_source
from tools.visual_assets import NS, palettes, palette_translations


class VisualAssetTests(unittest.TestCase):
    def test_both_platforms_include_all_palette_choices(self):
        data=palettes()
        for filename in ('patches/StartUpApplicationCommand.as','android/patches/StartUpApplicationCommand.as'):
            source=startup_source((ROOT/filename).read_text(),load_config(),filename.startswith('android'))
            for palette in data['club_palettes']:
                self.assertIn(f"clubPalettes.addItem({palette['id']},",source)
            for palette in data['character_palettes']:
                self.assertIn(f"palettes.addItem({palette['id']},",source)
        self.assertEqual(len(data['character_colors']['skin']),10)

    def test_translation_generation_is_idempotent(self):
        text=(ROOT/'resources/lang.json').read_text(encoding='utf-8-sig')
        generated=palette_translations(text)
        self.assertEqual(palette_translations(generated),generated)
        for entry in palettes()['character_palettes']:
            self.assertIn('"'+str(entry['id'])+'": "'+entry['name']+'"',generated)

    def test_stadium_models_have_valid_texture_paths_and_separate_ground_uvs(self):
        config=json.loads((ROOT/'resources/stadiums.json').read_text())
        distinct=set()
        for stadium in config['stadiums'].values():
            path=ROOT/'assets/models/stadiums'/stadium['path']
            document=ET.parse(path)
            for image in document.findall('.//c:library_images/c:image',NS):
                texture=(path.parent/image.find('c:init_from',NS).text).resolve()
                self.assertTrue(texture.is_file(),texture)
                if image.get('id')=='terrain_jpg': distinct.add(texture)
            if 'theme_' in stadium['path']:
                mesh=document.find('.//c:geometry[@id="geom-colline"]/c:mesh',NS)
                uv=mesh.find('c:source[@id="geom-colline-map1"]/c:float_array',NS)
                original=ET.parse(ROOT/'assets/models/stadiums/006_prairies/model.dae').find(
                    './/c:source[@id="geom-colline-map1"]/c:float_array',NS)
                old=list(map(float,original.text.split()))
                new=list(map(float,uv.text.split()))
                ground=mesh.find('c:triangles[@material="terrainjeu_1"]/c:p',NS)
                indices=set(map(int,ground.text.split()[2::3]))
                for i,(a,b) in enumerate(zip(old,new)):
                    if i//3 not in indices: self.assertAlmostEqual(a,b,places=6)
                self.assertNotEqual(old,new)
                coordinates=list(map(float,uv.text.split()))
                self.assertTrue(all(0<=v<=1 for v in coordinates))
        self.assertEqual(len(distinct),9)
