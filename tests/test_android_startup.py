import unittest

from android.build import runtime_options


class AndroidDiagnosticStartupTests(unittest.TestCase):
    def test_release_has_no_debugger_connection(self):
        self.assertEqual(runtime_options(), ['-target', 'apk'])

    def test_user_diagnostics_start_without_a_debugger(self):
        options = runtime_options(diagnostic=True)
        self.assertEqual(options, ['-target', 'apk'])
        self.assertNotIn('-listen', options)
        self.assertNotIn('-connect', options)

    def test_developer_debugging_explicitly_waits_for_usb_debugger(self):
        self.assertEqual(runtime_options(debug=True),
                         ['-target', 'apk-debug', '-listen', '7936'])

    def test_conflicting_modes_are_rejected(self):
        with self.assertRaises(ValueError):
            runtime_options(debug=True, diagnostic=True)


if __name__ == '__main__':
    unittest.main()
