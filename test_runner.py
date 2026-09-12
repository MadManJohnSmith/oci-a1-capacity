import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

import oci
import local_runner


class RunnerTests(unittest.TestCase):
    def test_retry_after_seconds_none_or_missing(self):
        self.assertIsNone(local_runner.retry_after_seconds(None))
        self.assertIsNone(local_runner.retry_after_seconds({}))
        self.assertIsNone(local_runner.retry_after_seconds({'Content-Type': 'application/json'}))

    def test_retry_after_seconds_integer(self):
        self.assertEqual(local_runner.retry_after_seconds({'Retry-After': '120'}), 120)
        self.assertEqual(local_runner.retry_after_seconds({'retry-after': ' 45 '}), 45)

    def test_retry_after_seconds_http_date(self):
        future = 'Wed, 21 Oct 2099 07:28:00 GMT'
        res = local_runner.retry_after_seconds({'Retry-After': future})
        self.assertIsNotNone(res)
        self.assertGreater(res, 0)

    def test_retry_after_seconds_invalid(self):
        self.assertIsNone(local_runner.retry_after_seconds({'Retry-After': 'invalid-date'}))

    @patch('urllib.request.urlopen')
    @patch('subprocess.run')
    def test_notify_with_webhook(self, mock_subproc, mock_urlopen):
        with patch.dict('os.environ', {'OCI_NOTIFY_WEBHOOK': 'https://example.com/hook'}):
            local_runner.notify('test-alert')
            mock_subproc.assert_called_once()
            mock_urlopen.assert_called_once()
            req = mock_urlopen.call_args[0][0]
            self.assertEqual(req.full_url, 'https://example.com/hook')
            self.assertEqual(req.data, b'{"text": "test-alert"}')

    @patch('urllib.request.urlopen')
    @patch('subprocess.run')
    def test_notify_rejects_insecure_webhook(self, mock_subproc, mock_urlopen):
        with patch.dict('os.environ', {'OCI_NOTIFY_WEBHOOK': 'http://example.com/hook'}, clear=True):
            local_runner.notify('test-alert')
            mock_urlopen.assert_not_called()

    @patch('urllib.request.urlopen')
    @patch('subprocess.run')
    def test_notify_without_webhook(self, mock_subproc, mock_urlopen):
        with patch.dict('os.environ', {}, clear=True):
            local_runner.notify('test-alert')
            mock_subproc.assert_called_once()
            mock_urlopen.assert_not_called()

    @patch('local_runner.clients')
    def test_network_error_handled_gracefully(self, mock_clients):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir)
            with patch('local_runner.CACHE', cache_path), \
                 patch('sys.argv', ['local_runner.py']), \
                 patch('local_runner.STOP') as mock_stop:
                mock_stop.is_set.side_effect = [False, True]
                mock_stop.wait.return_value = False
                compute, block, network = Mock(), Mock(), Mock()
                mock_clients.return_value = (compute, block, network)
                block.get_boot_volume.__name__ = 'get_boot_volume'
                block.get_boot_volume.side_effect = oci.exceptions.RequestException(Exception("connection failed"))

                exit_code = local_runner.main()
                self.assertEqual(exit_code, 2)
                status_file = cache_path / 'status.json'
                self.assertTrue(status_file.exists())
                status = json.loads(status_file.read_text())
                self.assertEqual(status['result'], 'reconcile_required')
                self.assertEqual(status['response_category'], 'ambiguous')

    @patch('local_runner.clients')
    def test_token_rotation_when_idle(self, mock_clients):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir)
            state_file = cache_path / 'runner-state.json'
            old_token = '0' * 32
            old_time = time.time() - (24 * 3600)
            state_file.write_text(json.dumps({'token': old_token, 'token_created': old_time}))

            with patch('local_runner.CACHE', cache_path), \
                 patch('sys.argv', ['local_runner.py']), \
                 patch('local_runner.STOP') as mock_stop:
                mock_stop.is_set.side_effect = [False, False, True]
                mock_stop.wait.return_value = False
                compute, block, network = Mock(), Mock(), Mock()
                compute.list_boot_volume_attachments.__name__ = 'list_boot_volume_attachments'
                mock_clients.return_value = (compute, block, network)

                volume = SimpleNamespace(availability_domain=local_runner.AD, compartment_id=local_runner.TENANCY, lifecycle_state='AVAILABLE')
                block.get_boot_volume.return_value = SimpleNamespace(data=volume, status=200)
                block.get_boot_volume.__name__ = 'get_boot_volume'
                with patch('local_runner.oci.pagination.list_call_get_all_results') as mock_pages:
                    mock_pages.return_value = SimpleNamespace(data=[], status=200)
                    compute.launch_instance.side_effect = oci.exceptions.ServiceError(500, 'InternalError', {}, 'Out of host capacity.')
                    compute.launch_instance.__name__ = 'launch_instance'

                    exit_code = local_runner.main()
                    self.assertEqual(exit_code, 0)
                    new_state = json.loads(state_file.read_text())
                    self.assertNotEqual(new_state['token'], old_token)
                    self.assertGreater(new_state['token_created'], old_time)

    @patch('local_runner.clients')
    def test_token_fails_closed_when_pending_across_expiry(self, mock_clients):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir)
            state_file = cache_path / 'runner-state.json'
            old_token = '0' * 32
            old_time = time.time() - (24 * 3600)
            state_file.write_text(json.dumps({'token': old_token, 'token_created': old_time, 'launch_pending': True}))

            with patch('local_runner.CACHE', cache_path), \
                 patch('sys.argv', ['local_runner.py']), \
                 patch('local_runner.STOP') as mock_stop:
                mock_stop.is_set.side_effect = [False, False, True]
                mock_stop.wait.return_value = False
                compute, block, network = Mock(), Mock(), Mock()
                compute.list_boot_volume_attachments.__name__ = 'list_boot_volume_attachments'
                mock_clients.return_value = (compute, block, network)

                volume = SimpleNamespace(availability_domain=local_runner.AD, compartment_id=local_runner.TENANCY, lifecycle_state='AVAILABLE')
                block.get_boot_volume.return_value = SimpleNamespace(data=volume, status=200)
                block.get_boot_volume.__name__ = 'get_boot_volume'
                with patch('local_runner.oci.pagination.list_call_get_all_results') as mock_pages:
                    mock_pages.return_value = SimpleNamespace(data=[], status=200)
                    exit_code = local_runner.main()
                    self.assertEqual(exit_code, 2)
                    status_file = cache_path / 'status.json'
                    status = json.loads(status_file.read_text())
                    self.assertEqual(status['result'], 'reconcile_required')
                    self.assertEqual(status['response_category'], 'reconcile_required')

    def test_status_flag_when_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir)
            with patch('local_runner.CACHE', cache_path), \
                 patch('sys.argv', ['local_runner.py', '--status']), \
                 patch('builtins.print') as mock_print:
                ret = local_runner.main()
                self.assertEqual(ret, 0)
                mock_print.assert_called_with('No status available (runner has not executed).')

    def test_status_flag_when_present(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir)
            status_file = cache_path / 'status.json'
            status_file.write_text(json.dumps({
                'result': 'capacity',
                'last_result_time': '2026-09-11T12:00:00+00:00',
                'next_attempt_epoch': time.time() + 30,
                'delay_seconds': 60.5,
                'jitter_seconds': 0.5,
                'capacity_streak': 5
            }))
            with patch('local_runner.CACHE', cache_path), \
                 patch('sys.argv', ['local_runner.py', '--status']), \
                 patch('builtins.print') as mock_print:
                ret = local_runner.main()
                self.assertEqual(ret, 0)
                printed = mock_print.call_args[0][0]
                self.assertIn('Status: capacity', printed)
                self.assertIn('Delay: 60.5s', printed)
                self.assertIn('Streak: 5', printed)

    @patch('local_runner.clients')
    def test_jitter_and_capacity_max_delay(self, mock_clients):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir)
            with patch('local_runner.CACHE', cache_path), \
                 patch('sys.argv', ['local_runner.py']), \
                 patch.dict('os.environ', {'OCI_CAPACITY_DELAY': '20', 'OCI_CAPACITY_MAX_DELAY': '30'}), \
                 patch('local_runner.STOP') as mock_stop:
                mock_stop.is_set.side_effect = [False, False, True]
                mock_stop.wait.return_value = False
                compute, block, network = Mock(), Mock(), Mock()
                compute.list_boot_volume_attachments.__name__ = 'list_boot_volume_attachments'
                mock_clients.return_value = (compute, block, network)

                volume = SimpleNamespace(availability_domain=local_runner.AD, compartment_id=local_runner.TENANCY, lifecycle_state='AVAILABLE')
                block.get_boot_volume.return_value = SimpleNamespace(data=volume, status=200)
                block.get_boot_volume.__name__ = 'get_boot_volume'
                with patch('local_runner.oci.pagination.list_call_get_all_results') as mock_pages:
                    mock_pages.return_value = SimpleNamespace(data=[], status=200)
                    compute.launch_instance.side_effect = oci.exceptions.ServiceError(500, 'InternalError', {}, 'Out of host capacity.')
                    compute.launch_instance.__name__ = 'launch_instance'

                    ret = local_runner.main()
                    self.assertEqual(ret, 0)
                    status_file = cache_path / 'status.json'
                    self.assertTrue(status_file.exists())
                    status = json.loads(status_file.read_text())
                    self.assertEqual(status['result'], 'capacity')
                    self.assertIn('jitter_seconds', status)
                    self.assertIn('base_delay_seconds', status)
                    self.assertEqual(status['base_delay_seconds'], 20)
                    self.assertTrue(10 <= status['delay_seconds'] <= 23.5)


if __name__ == '__main__':
    unittest.main()
