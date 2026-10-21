"""Website delivery must be complete, current, and contain only public files."""
import json
from pathlib import Path
import tempfile
import unittest
from tools.site_delivery import PAGES, FRONTEND, delivery
from tools.build_restoration_data import homepage_assets, HEROES
from backend.server import site_manifest


class SiteDeliveryTests(unittest.TestCase):
    def fixture(self, root):
        for name in (*PAGES, *FRONTEND, 'bin/boufbowl-client-1.9.6.swf',
                     'assets/site/logo.avif', 'resources/site.json',
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
        (root/'assets/site/logo-small.avif').write_bytes(b'small image')
        (root/'index.html').write_text('<link rel="stylesheet" href="home.css"><img src="assets/site/logo.avif" srcset="assets/site/logo-small.avif 120w, assets/site/logo.avif 630w" sizes="200px"><script src="home.js" defer></script>')
        (root/'home.css').write_text('body { background: url("assets/site/logo.avif"); color: red; }')
        (root/'home.js').write_text('window.siteReady = true;')

    def test_delivery_download_sizes_integrity_and_private_file_exclusion(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)/'source';root.mkdir();self.fixture(root)
            output=Path(temporary)/'delivery'
            sources={name:(root/name).read_bytes() for name in (*PAGES,*FRONTEND)}
            result=delivery(root, output)
            self.assertEqual(result['downloads'],site_manifest(root)['downloads'])
            self.assertEqual(sources,{name:(root/name).read_bytes() for name in sources})
            html=(output/'index.html').read_text()
            self.assertIn('<style>',html)
            self.assertNotIn('rel="stylesheet"',html)
            self.assertIn('?v='+result['asset_revision'],html)
            self.assertIn(f'srcset="assets/site/logo-small.avif?v={result["asset_revision"]} 120w, assets/site/logo.avif?v={result["asset_revision"]} 630w"',html)
            self.assertRegex(html,r'js/home\.[a-z0-9]+\.js')
            self.assertFalse((output/'home.css').exists())
            self.assertTrue(output.stat().st_mode & 0o005)
            self.assertTrue((output/'downloads/BoufbowlOffline.apk').is_file())
            self.assertTrue((output/'website-activity.html').is_file())
            self.assertIn('url=website-activity.html',(output/'website-tracking.html').read_text())
            self.assertEqual(result['downloads']['android']['size'],len('android/build/BoufbowlOffline.apk'))
            self.assertFalse((output/'.local/private.sqlite').exists())
            self.assertEqual(delivery(root,output,check=True),result)
            (output/'unexpected.txt').write_text('extra')
            with self.assertRaisesRegex(ValueError,'unexpected'):
                delivery(root,output,check=True)
            delivery(root,output)
            self.assertFalse((output/'unexpected.txt').exists())
            bundle=next((output/'js').glob('home.*.js'))
            bundle.write_text('corrupt')
            with self.assertRaisesRegex(ValueError, 'stale'):
                delivery(root,output,check=True)
            updated=delivery(root,output)
            self.assertEqual(updated['asset_revision'],result['asset_revision'])
            (root/'assets/site/logo.avif').write_text('updated logo')
            with self.assertRaisesRegex(ValueError,'stale'):
                delivery(root,output,check=True)
            updated=delivery(root,output)
            self.assertNotEqual(updated['asset_revision'],result['asset_revision'])
            (root/'assets/site/logo.avif').unlink()
            self.assertFalse(next(a['available'] for a in homepage_assets(root) if a['path'].endswith('logo.avif')))
            with self.assertRaisesRegex(ValueError,'Missing homepage assets'):
                delivery(root,output)

    def test_refuses_overwriting_source_and_unrelated_directories(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)/'source';root.mkdir();self.fixture(root)
            with self.assertRaises(ValueError):delivery(root,root/'assets/output')
            unrelated=Path(temporary)/'unrelated';unrelated.mkdir()
            (unrelated/'keep.txt').write_text('keep')
            with self.assertRaises(ValueError):delivery(root,unrelated)
            self.assertEqual((unrelated/'keep.txt').read_text(),'keep')
            package=root/'android/build/BoufbowlOffline.apk'
            package.unlink()
            package.symlink_to(root/'.local/private.sqlite')
            result=delivery(root,Path(temporary)/'safe-output')
            self.assertIsNone(result['downloads']['android']['url'])
            self.assertFalse((Path(temporary)/'safe-output/downloads/BoufbowlOffline.apk').exists())

    def test_source_script_changes_generate_a_new_bundle_name(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)/'source';root.mkdir();self.fixture(root)
            output=Path(temporary)/'delivery'
            first=delivery(root,output)
            (root/'home.js').write_text('window.siteReady = "updated";')
            second=delivery(root,output)
            first_scripts={name for name in first['files'] if name.startswith('js/')}
            second_scripts={name for name in second['files'] if name.startswith('js/')}
            self.assertNotEqual(first_scripts,second_scripts)
            self.assertEqual((root/'home.js').read_text(),'window.siteReady = "updated";')
