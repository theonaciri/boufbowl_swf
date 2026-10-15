"""The restoration dashboard must distinguish recovered files from placeholders."""
import json
from pathlib import Path
import tempfile
import unittest
from tools.build_restoration_data import audit, ROOT

class RestorationInventoryTests(unittest.TestCase):
    def test_known_bodies_and_shared_stadium_models_are_not_overstated(self):
        data=audit()
        recovered={c['id'] for c in data['characters'] if c['body_available'] and not c['hero']}
        self.assertEqual(recovered,{'cra-1','cra-2','eniripsa-2','enutrof-2','iop-1'})
        self.assertEqual(data['summary']['geometry_found'],1)
        self.assertEqual({t['file'] for s in data['stadiums'] for t in s['tracks'] if t['restored_low_quality']},
                         {f'music/music_resolution_loop_{i:02d}.mp3' for i in range(1,4)})
        self.assertTrue(all(s['surface_available'] for s in data['stadiums']))
        self.assertTrue(all(not s['original_geometry_available'] for s in data['stadiums'] if s['id']!='FARMSTEAD'))
        self.assertEqual(next(c['name'] for c in data['characters'] if c['hero']==511),'Kabrok')

    def test_audio_deduplicates_references_includes_unreferenced_files_and_rejects_escape(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            def write(path,value):
                p=root/path;p.parent.mkdir(parents=True,exist_ok=True)
                p.write_text(json.dumps(value) if not isinstance(value,str) else value)
            write('resources/sound.json',{'one':'interface/click.mp3','alias':'interface/click.mp3','absent':'interactions/missing.mp3','escape':'../secret.mp3'})
            write('resources/stadiums.json',{'stadiums':{'FARMSTEAD':{'path':'theme/model.dae','strategicMusics':['music/one.mp3'],'resolutionMusics':['music/one.mp3']}}})
            write('resources/stadium_art.json',{'template':'assets/model.dae','stadiums':{'FARMSTEAD':'grass'},'textures':{'grass':{'path':'assets/grass.png'}}})
            write('resources/offline_characters.json',{'special_characters':[]})
            write('assets/sounds/interface/click.mp3','sound')
            write('assets/sounds/tuto/voice.mp3','voice')
            write('assets/sounds/music/one.mp3','music')
            write('assets/grass.png','image')
            write('assets/model.dae','geometry')
            data=audit(root);audio=data['audio']
            self.assertEqual(len(audio),3)
            self.assertEqual(data['summary']['audio_found'],3)
            self.assertEqual(data['summary']['audio_expected'],4)
            self.assertEqual(len(audio),3)  # The FX workshop keeps its own scope.
            click=next(a for a in audio if a['file']=='interface/click.mp3')
            self.assertEqual(click['aliases'],['one','alias'])
            self.assertFalse(next(a for a in audio if a['file']=='interactions/missing.mp3')['available'])
            self.assertFalse(next(a for a in audio if a['file']=='tuto/voice.mp3')['referenced'])
            self.assertFalse(any('..' in a['path'] for a in audio))
            with tempfile.NamedTemporaryFile() as external:
                external.write(b'not part of the checkout');external.flush()
                (root/'assets/sounds/interface/click.mp3').unlink()
                (root/'assets/sounds/interface/click.mp3').symlink_to(external.name)
                self.assertFalse(next(a for a in audit(root)['audio'] if a['file']=='interface/click.mp3')['available'])

if __name__=='__main__':unittest.main()
