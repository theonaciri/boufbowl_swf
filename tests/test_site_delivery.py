"""Website delivery must be complete, current, and contain only public files."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from tools.site_delivery import PAGES, FRONTEND, delivery
from tools.build_restoration_data import homepage_assets, HEROES


class SiteDeliveryTests(unittest.TestCase):
    def fixture(self, root):
        for name in (*PAGES, *FRONTEND, 'bin/boufbowl-client-1.9.6.swf',
                     'assets/site/logo.webp', 'resources/site.json',
                     'android/build/BoufbowlOffline.apk', '.local/private.sqlite'):
            path=root/name
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text('{}' if name.endswith('.json') else name)
        for prefix, count in (('class-',14),('field-classes-',3)):
            for i in range(1,count+1):
                path=root/f'assets/site/restoration/{prefix}{i}.webp'
                path.parent.mkdir(parents=True,exist_ok=True)
                path.write_bytes(b'fixture')
        for skin in [*(cls*10+gender for cls in range(1,15) for gender in (1,2)), *(h for h,_,_ in HEROES)]:
            path=root/f'assets/site/restoration/grid-icons/{skin}.png'
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(b'fixture')
        (root/'index.html').write_text('<img src="assets/site/logo.webp">')

    def test_delivery_download_sizes_integrity_and_private_file_exclusion(self):
        with tempfile.TemporaryDirectory() as temporary, patch('tools.site_delivery.outputs', return_value={}):
            root=Path(temporary)/'source';root.mkdir();self.fixture(root)
            output=Path(temporary)/'delivery'
            result=delivery(root, output)
            self.assertTrue((output/'downloads/BoufbowlOffline.apk').is_file())
            self.assertEqual(result['downloads']['android']['size'],len('android/build/BoufbowlOffline.apk'))
            self.assertFalse((output/'.local/private.sqlite').exists())
            self.assertEqual(delivery(root,output,check=True),result)
            (output/'unexpected.txt').write_text('extra')
            with self.assertRaisesRegex(ValueError,'unexpected'):
                delivery(root,output,check=True)
            delivery(root,output)
            self.assertFalse((output/'unexpected.txt').exists())
            (output/'home.js').write_text('corrupt')
            with self.assertRaisesRegex(ValueError, 'altered'):
                delivery(root,output,check=True)
            delivery(root,output)
            (root/'assets/site/logo.webp').write_text('updated logo')
            with self.assertRaisesRegex(ValueError,'stale'):
                delivery(root,output,check=True)
            delivery(root,output)
            (root/'assets/site/logo.webp').unlink()
            self.assertFalse(next(a['available'] for a in homepage_assets(root) if a['path'].endswith('logo.webp')))
            with self.assertRaisesRegex(ValueError,'Missing homepage assets'):
                delivery(root,output)

    def test_refuses_overwriting_source_and_unrelated_directories(self):
        with tempfile.TemporaryDirectory() as temporary, patch('tools.site_delivery.outputs',return_value={}):
            root=Path(temporary)/'source';root.mkdir();self.fixture(root)
            with self.assertRaises(ValueError):delivery(root,root/'assets/output')
            unrelated=Path(temporary)/'unrelated';unrelated.mkdir()
            (unrelated/'keep.txt').write_text('keep')
            with self.assertRaises(ValueError):delivery(root,unrelated)
            self.assertEqual((unrelated/'keep.txt').read_text(),'keep')
