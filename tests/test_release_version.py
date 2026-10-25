import json,tempfile,unittest
from pathlib import Path
from tools.release_version import release,android_descriptor,record_artifact
class ReleaseTests(unittest.TestCase):
 def test_public_version_does_not_downgrade_android(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);(root/'resources').mkdir();(root/'android').mkdir()
   (root/'resources/release.json').write_text(json.dumps({'version':'0.1.0','android_build':1000001}))
   (root/'android/application.xml').write_text('<application><versionNumber>1.0.0</versionNumber></application>')
   xml=android_descriptor(root)
   self.assertIn('<versionNumber>1.0.1</versionNumber>',xml);self.assertIn('<versionLabel>0.1.0</versionLabel>',xml)
   package=root/'app.apk';package.write_bytes(b'package');record_artifact(package,root)
   receipt=json.loads((root/'app.apk.release.json').read_text());self.assertEqual(receipt['version'],'0.1.0');self.assertEqual(receipt['bytes'],7)
 def test_rejects_downgrade_and_invalid_semver(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);(root/'resources').mkdir()
   for v in [{'version':'0.1.0','android_build':1000000},{'version':'0.01.0','android_build':1000001}]:
    (root/'resources/release.json').write_text(json.dumps(v))
    with self.assertRaises(ValueError):release(root)
