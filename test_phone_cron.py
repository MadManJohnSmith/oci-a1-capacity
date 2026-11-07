import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import phone_cron


class PhoneCronTests(unittest.TestCase):
    @patch('phone_cron.subprocess.Popen')
    def test_starts_and_records_exit(self, popen):
        with tempfile.TemporaryDirectory() as tmpdir, patch('phone_cron.HOME', Path(tmpdir)), \
                patch('phone_cron.EXIT', Path(tmpdir) / 'last-exit'), \
                patch('phone_cron.PAUSED', Path(tmpdir) / 'paused'):
            popen.return_value.wait.return_value = 2
            self.assertEqual(phone_cron.main(), 0)
            self.assertEqual((Path(tmpdir) / 'last-exit').read_text(), '2\n')
            self.assertEqual(phone_cron.main(), 0)
            popen.assert_called_once()

    @patch('phone_cron.subprocess.Popen')
    def test_paused_never_starts(self, popen):
        with tempfile.TemporaryDirectory() as tmpdir, patch('phone_cron.PAUSED', Path(tmpdir) / 'paused'):
            (Path(tmpdir) / 'paused').touch()
            self.assertEqual(phone_cron.main(), 0)
            popen.assert_not_called()


if __name__ == '__main__':
    unittest.main()
