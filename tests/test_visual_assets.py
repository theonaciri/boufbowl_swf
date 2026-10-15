import json
from pathlib import Path
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET
from tools.game_config import ROOT, load_config, startup_source
from tools.visual_assets import NS, palettes, palette_translations, palette_item_source


class VisualAssetTests(unittest.TestCase):
    def test_both_platforms_include_all_palette_choices(self):
        data=palettes()
        for filename in ('patches/StartUpApplicationCommand.as','android/patches/StartUpApplicationCommand.as'):
            source=startup_source((ROOT/filename).read_text(),load_config(),filename.startswith('android'))
            for palette in data['club_palettes']:
                self.assertIn(f"clubPalettes.addItem({palette['id']},",source)
            for palette in data['character_palettes']:
                self.assertIn(f"palettes.addItem({palette['id']},",source)
            for palette in data['class_palettes']+data['hero_palettes']:
                cls=palette.get('class_id',0);hero=palette.get('unique_character',0)
                colors=','.join('['+','.join('Color3.fromRgbUInt(0x'+c+')' for c in palette[k])+']' for k in ('hair','eyes','skin'))
                self.assertIn(f"palettes.addItem({palette['id']},new BoufbowlerPaletteItem(1,0,{palette['id']},{cls},{hero},{colors}));",source)
            self.assertNotIn('hair[0],skin[0],eyes[0]',source)
            self.assertIn('getDefaultHairColorId(0,1+i%2)',source)
            self.assertIn('getDefaultHairColorId(hero[0],hero[2])',source)
        self.assertEqual(len(data['character_colors']['skin']),10)

    def test_new_palettes_are_validated_with_the_shared_catalog(self):
        for change in ('color','duplicate','class','hero','default'):
            data=json.loads((ROOT/'resources/palettes.json').read_text())
            if change=='color': data['class_palettes'][0]['hair']=['bad']
            if change=='duplicate': data['class_palettes'][0]['id']=101
            if change=='class': data['class_palettes'][0]['class_id']=15
            if change=='hero': data['hero_palettes'][0]['unique_character']=500
            if change=='default': data['class_palettes'][0]['defaults']['female']['hair']='123456'
            with self.subTest(change=change),patch('tools.visual_assets.json.loads',return_value=data):
                with self.assertRaises(ValueError): palettes()

    def test_gender_defaults_are_independent_of_customization_swatches(self):
        data=palettes()
        source=palette_item_source((ROOT/'patches/BoufbowlerPaletteItem.as').read_text())
        for entry in data['class_palettes']:
            if 'defaults' not in entry: continue
            for method,kind in (('Hair','hair'),('Eye','eyes'),('Skin','skin')):
                male=entry[kind].index(entry['defaults']['male'][kind])
                female=entry[kind].index(entry['defaults']['female'][kind])
                body=source.split('function getDefault'+method+'ColorId',1)[1].split('public function',1)[0]
                self.assertIn(f"if(this.id == {entry['id']}) return param2 == Gender.FEMALE ? {female} : {male};",body)
                self.assertEqual(len(entry[kind]),len(set(entry[kind])))
        # Reference sheet mapping and visually different male/female appearances.
        wakfu={p['class_id']:p for p in data['class_palettes'] if p['style']=='Wakfu'}
        self.assertEqual(wakfu[1]['source'],'characters2.webp')
        self.assertEqual(wakfu[10]['source'],'characters.webp')
        self.assertEqual(wakfu[7]['defaults']['female']['skin'],'606e79')
        self.assertEqual(wakfu[7]['defaults']['male']['skin'],'60859b')
        self.assertEqual(wakfu[3]['defaults']['female']['hair'],'fef1c5')
        self.assertEqual(wakfu[3]['defaults']['male']['hair'],'4f4131')
        self.assertEqual(wakfu[6]['defaults']['male']['eyes'],'ffffff')
        for cls in (9,14): self.assertEqual(wakfu[cls]['reference_status'],'pending')

    def test_reference_heroes_have_dedicated_default_palettes(self):
        heroes={p['unique_character']:p for p in palettes()['hero_palettes']}
        for hero,palette,hair,skin in ((501,15,'ecddca','a57c5c'),
                                     (503,17,'222e2e','cc9755'),
                                     (504,18,'fffee7','3f321f'),
                                     (505,19,'fd8203','ecb141'),
                                     (506,20,'81980c','9f5621')):
            entry=heroes[hero]
            self.assertEqual(entry['id'],palette)
            self.assertEqual(entry['hair'][0],hair)
            self.assertEqual(entry['skin'][0],skin)
            for filename in ('patches/StartUpApplicationCommand.as','android/patches/StartUpApplicationCommand.as'):
                source=startup_source((ROOT/filename).read_text(),load_config(),filename.startswith('android'))
                self.assertRegex(source,rf'\[{hero},\s*\d+,\s*\d+,\s*{palette}\]')
                self.assertIn(f'new BoufbowlerPaletteItem(1,0,{palette},0,{hero},',source)

    def test_remaining_reference_heroes_have_shades_and_accent_choices(self):
        heroes={p['unique_character']:p for p in palettes()['hero_palettes']}
        ids=(21,22,23,24,25,26,27,28,34,35,36,37)
        defaults=('3b3422','f3df87','f5f4dc','cc5740','18292d','9e5500',
                  'fffaf0','f5edd2','a80503','f3f3f3','95a31b','ee7d29')
        for hero,palette,hair in zip(range(507,519),ids,defaults):
            entry=heroes[hero]
            self.assertEqual(entry['id'],palette)
            self.assertEqual(entry['hair'][0],hair)
            self.assertGreaterEqual(len(entry['hair']),6)
            self.assertGreaterEqual(len(entry['eyes']),5)
            self.assertGreaterEqual(len(entry['skin']),4)
            for kind in ('hair','eyes','skin'):
                self.assertEqual(len(entry[kind]),len(set(entry[kind])))
            for filename in ('patches/StartUpApplicationCommand.as','android/patches/StartUpApplicationCommand.as'):
                source=startup_source((ROOT/filename).read_text(),load_config(),filename.startswith('android'))
                self.assertRegex(source,rf'\[{hero},\s*\d+,\s*\d+,\s*{palette}\]')
        self.assertIn('ed59f5',heroes[517]['eyes'])
        self.assertIn('Monochrome',heroes[516]['reference_note'])

    def test_translation_generation_is_idempotent(self):
        text=(ROOT/'resources/lang.json').read_text(encoding='utf-8-sig')
        generated=palette_translations(text)
        self.assertEqual(palette_translations(generated),generated)
        for entry in palettes()['character_palettes']:
            self.assertIn('"'+str(entry['id'])+'": "'+entry['name']+'"',generated)
        for entry in palettes()['class_palettes']:
            self.assertIn('"'+str(entry['id'])+'": "'+entry['class']+' ('+entry['style']+')"',generated)

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

    def test_stadium_surface_sources_match_the_original_frame_inventory(self):
        manifest=json.loads((ROOT/'resources/stadium_art.json').read_text())
        for stadium,bitmap in manifest['frame_sources'].items():
            art=manifest['textures'][manifest['stadiums'][stadium]]
            self.assertEqual(Path(art['source']).stem,str(bitmap),stadium)
        self.assertEqual(len(set(manifest['stadiums'].values())),9)
