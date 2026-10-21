"""Package receipts must detect changed inputs and damaged/missing artifacts."""
import os
from pathlib import Path
import tempfile
import unittest
from tools.package_cache import Inputs, Receipt, digest, sync_tree


class PackageCacheTests(unittest.TestCase):
    def test_reuse_requires_matching_inputs_and_complete_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root/'client.exe'
            output.write_bytes(b'package')
            receipt = Receipt(root, 'windows')
            self.assertFalse(receipt.current('first', [output]))
            receipt.save('first', [output])
            self.assertTrue(receipt.current('first', [output]))
            self.assertFalse(receipt.current('changed', [output]))
            output.write_bytes(b'damaged')
            self.assertFalse(receipt.current('first', [output]))
            output.unlink()
            self.assertFalse(receipt.current('first', [output]))

    def test_content_fingerprint_ignores_touch_but_detects_same_size_change(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'source'
            path.write_bytes(b'aaaa')
            first = digest(Inputs().tree(directory))
            original = path.stat()
            os.utime(path, ns=(original.st_atime_ns, original.st_mtime_ns+1000000000))
            self.assertEqual(first, digest(Inputs().tree(directory)))
            path.write_bytes(b'bbbb')
            os.utime(path, ns=(original.st_atime_ns, original.st_mtime_ns))
            self.assertNotEqual(first, digest(Inputs().tree(directory)))
            path.unlink()
            self.assertNotEqual(first, digest(Inputs().tree(directory)))

    @unittest.skipIf(os.name == 'nt', 'POSIX permissions and symlinks')
    def test_executable_permissions_and_linked_tool_inputs_are_fingerprinted(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tool = root/'external'
            tool.mkdir()
            library = tool/'tool.so'
            library.write_bytes(b'one')
            sdk = root/'sdk'
            sdk.mkdir()
            (sdk/'linked').symlink_to(tool, target_is_directory=True)
            (tool/'cycle').symlink_to(sdk, target_is_directory=True)
            first = Inputs().tree(sdk)
            self.assertIn('linked/tool.so', first)
            library.write_bytes(b'two')
            self.assertNotEqual(first, Inputs().tree(sdk))
            receipt = Receipt(root, 'linux')
            launcher = root/'client.run'
            launcher.write_bytes(b'launcher')
            launcher.chmod(0o755)
            receipt.save('key', [launcher])
            launcher.chmod(0o644)
            self.assertFalse(receipt.current('key', [launcher]))

    def test_sync_reuses_unchanged_files_and_removes_obsolete_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, target = root/'source', root/'target'
            source.mkdir()
            (source/'one').write_bytes(b'1')
            self.assertEqual(sync_tree(source, target)['copied'], 1)
            timestamp = (target/'one').stat().st_mtime_ns
            (target/'generated').write_bytes(b'generated')
            self.assertEqual(sync_tree(source, target, preserve=['generated'])['copied'], 0)
            self.assertEqual((target/'one').stat().st_mtime_ns, timestamp)
            self.assertTrue((target/'generated').is_file())
            (source/'one').unlink()
            self.assertEqual(sync_tree(source, target)['removed'], 2)
