import json
import os
from pathlib import Path
import tempfile
import unittest

from tools.website_media_cache import MediaCache


class WebsiteMediaCacheTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / 'source.png'
        self.output = self.root / 'output.avif'
        self.source.write_bytes(b'source')
        self.output.write_bytes(b'media')
        self.inputs = ['source.png']
        self.outputs = ['output.avif']
        MediaCache(self.root).save('images', self.inputs, self.outputs)

    def current(self):
        return MediaCache(self.root).current('images', self.inputs, self.outputs)

    def test_output_timestamp_change_reuses_media(self):
        stamp = self.output.stat()
        os.utime(self.output, ns=(stamp.st_atime_ns, stamp.st_mtime_ns + 1000000000))
        self.assertTrue(self.current())

    def test_same_size_output_change_with_preserved_timestamp_is_detected(self):
        stamp = self.output.stat()
        self.output.write_bytes(b'other')
        os.utime(self.output, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
        self.assertFalse(self.current())

    def test_media_input_change_is_detected(self):
        self.source.write_bytes(b'changed')
        self.assertFalse(self.current())

    def test_page_changes_reuse_media(self):
        (self.root / 'index.html').write_text('<h1>New title</h1>')
        self.assertTrue(self.current())

    def test_missing_output_is_detected(self):
        self.output.unlink()
        self.assertFalse(self.current())

    def test_legacy_receipt_is_upgraded(self):
        cache = MediaCache(self.root)
        stamp = self.output.stat()
        cache.stages['images']['outputs'] = {'output.avif': [stamp.st_size, stamp.st_mtime_ns]}
        cache.write()
        self.assertTrue(self.current())
        saved = json.loads(cache.path.read_text())
        self.assertIn('sha256', saved['images']['outputs']['output.avif'])

    def test_missing_receipt_explains_rebuild(self):
        self.assertEqual(MediaCache(self.root).reason('new-stage', self.inputs, self.outputs),
                         'no completed build record')


if __name__ == '__main__':
    unittest.main()
