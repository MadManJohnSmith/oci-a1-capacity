import json
import tempfile
import time
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import phone_status


class PhoneStatusTests(unittest.TestCase):
    def test_snapshot_projects_only_allowed_fields_and_stale(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / 'status.json').write_text(json.dumps({
                'result': 'capacity', 'last_result_time': datetime.fromtimestamp(1000).astimezone().isoformat(),
                'next_attempt_epoch': 1050, 'next_attempt': 'soon',
                'instance_id': 'private', 'operations': ['private'],
            }))
            (root / 'runner-state.json').write_text(json.dumps({'capacity_streak': 4, 'launch_pending': False,
                                                                  'token': 'private'}))
            with patch('phone_status.CACHE', root), patch('phone_status.HOME', root), \
                    patch('phone_status.runner_alive', return_value=True):
                data = phone_status.snapshot(1010)
                self.assertEqual(data['service'], 'running')
                self.assertEqual(data['next_attempt'], 'soon')
                self.assertNotIn('token', data)
                self.assertNotIn('instance_id', data)
                self.assertNotIn('operations', data)
                self.assertTrue(phone_status.snapshot(2000)['stale'])

    def test_snapshot_reports_attempts_only_when_numeric(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            state = root / 'runner-state.json'
            state.write_text(json.dumps({'attempts': 63982, 'capacity_streak': 4}))
            with patch('phone_status.CACHE', root), patch('phone_status.HOME', root), \
                    patch('phone_status.runner_alive', return_value=True):
                self.assertEqual(phone_status.snapshot(1010)['attempts'], 63982)
            state.write_text(json.dumps({'attempts': 'many'}))
            with patch('phone_status.CACHE', root), patch('phone_status.HOME', root), \
                    patch('phone_status.runner_alive', return_value=True):
                self.assertIsNone(phone_status.snapshot(1010)['attempts'])

    def test_daily_deduplicates_and_retries_failed_delivery(self):
        with tempfile.TemporaryDirectory() as tmpdir, patch('phone_status.HOME', Path(tmpdir)), \
                patch('phone_status.summary', return_value='daily'), patch('local_runner.notify') as send:
            send.side_effect = [False, True]
            self.assertFalse(phone_status.send_daily())
            self.assertFalse((Path(tmpdir) / 'daily-sent').exists())
            self.assertTrue(phone_status.send_daily())
            self.assertTrue(phone_status.send_daily())
            self.assertEqual(send.call_count, 2)

    def test_counts_recent_cycles_only(self):
        with tempfile.TemporaryDirectory() as tmpdir, patch('phone_status.CACHE', Path(tmpdir)):
            now = datetime.now().astimezone()
            (Path(tmpdir) / 'runner.log').write_text(
                f'{now:%Y-%m-%d %H:%M:%S},000 INFO Attempt={{"result":"capacity"}}\n'
                '2000-01-01 01:00:00,000 INFO Attempt={"result":"accepted"}\n')
            counts = phone_status.counts_since(now.replace(hour=0, minute=0, second=0))
            self.assertEqual(counts['capacity'], 1)
            self.assertEqual(counts['accepted'], 0)


if __name__ == '__main__':
    unittest.main()
