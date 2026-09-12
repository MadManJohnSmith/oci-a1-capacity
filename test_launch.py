import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import oci
import launch


class LaunchTests(unittest.TestCase):
    def setUp(self):
        self.compute = Mock()
        self.block = Mock()
        self.volume = SimpleNamespace(
            availability_domain=launch.AD,
            compartment_id="compartment", lifecycle_state="AVAILABLE",
        )
        self.block.get_boot_volume.return_value.data = self.volume
        self.pages = patch("launch.oci.pagination.list_call_get_all_results").start()
        self.addCleanup(patch.stopall)
        self.pages.return_value.data = []

    def attempt(self, **kwargs):
        return launch.attempt(self.compute, self.block, "owner/repo", **kwargs)

    def test_launched_and_stable_token(self):
        self.assertEqual(self.attempt(), "launched")
        call = self.compute.launch_instance.call_args
        details = call.args[0]
        self.assertEqual(details.source_details.boot_volume_id, launch.BOOT)
        self.assertEqual(details.shape, "VM.Standard.A1.Flex")
        self.assertEqual(details.shape_config.ocpus, 2)
        self.assertEqual(details.shape_config.memory_in_gbs, 12)
        self.assertIsNone(details.metadata)
        self.assertEqual(details.compartment_id, "compartment")
        self.attempt()
        self.assertEqual(call.kwargs["opc_retry_token"],
                         self.compute.launch_instance.call_args.kwargs["opc_retry_token"])
        self.assertEqual(len(call.kwargs["opc_retry_token"]), 64)

    def test_attached_skip(self):
        for state in ("ATTACHED", "ATTACHING", "DETACHING", "UNKNOWN"):
            self.pages.return_value.data = [SimpleNamespace(lifecycle_state=state)]
            self.assertEqual(self.attempt(), "attached")
        self.compute.launch_instance.assert_not_called()

    def test_unavailable_skip(self):
        self.volume.lifecycle_state = "RESTORING"
        self.assertEqual(self.attempt(), "unavailable")
        self.compute.launch_instance.assert_not_called()

    def test_check_read_only(self):
        self.assertEqual(self.attempt(check=True), "ready")
        self.compute.launch_instance.assert_not_called()

    def test_capacity(self):
        self.compute.launch_instance.side_effect = oci.exceptions.ServiceError(
            500, "InternalError", {}, "Out of host capacity.")
        self.assertEqual(self.attempt(), "capacity")
        self.compute.launch_instance.assert_called_once()

    def test_fatal(self):
        for status, code, message in (
            (401, "NotAuthenticated", "bad credentials"),
            (400, "InvalidParameter", "bad config"),
            (500, "InternalError", "unrelated failure"),
            (400, "LimitExceeded", "quota"),
        ):
            self.compute.launch_instance.side_effect = oci.exceptions.ServiceError(
                status, code, {}, message)
            with self.assertRaises(oci.exceptions.ServiceError):
                self.attempt()

    def test_ambiguous_retry_uses_same_token(self):
        self.compute.launch_instance.side_effect = TimeoutError("ambiguous")
        with self.assertRaises(TimeoutError):
            self.attempt()
        token = self.compute.launch_instance.call_args.kwargs["opc_retry_token"]
        self.compute.launch_instance.side_effect = None
        self.assertEqual(self.attempt(), "launched")
        self.assertEqual(token, self.compute.launch_instance.call_args.kwargs["opc_retry_token"])

    def test_invalid_ad(self):
        self.volume.availability_domain = "wrong"
        with self.assertRaises(ValueError):
            self.attempt()
        self.compute.launch_instance.assert_not_called()

    def test_invalid_resources_rejected(self):
        with patch.dict("os.environ", {"OCI_OCPUS": "4", "OCI_MEMORY_GB": "1"}):
            with self.assertRaises(ValueError):
                self.attempt()
        self.compute.launch_instance.assert_not_called()

    def test_invalid_repository_rejected(self):
        with self.assertRaises(ValueError):
            launch.repository_name("owner/repo\nmalicious")
        self.compute.launch_instance.assert_not_called()

    def test_config_replaces_local_key_path(self):
        config = (f"[DEFAULT]\ntenancy={launch.TENANCY}\n"
                  "user=user\nfingerprint=fingerprint\nkey_file=/missing/key.pem\n")
        with patch.dict("os.environ", {
            "GITHUB_REPOSITORY": "owner/repo", "OCI_CONFIG": config,
            "OCI_API_KEY": "test-key", "GITHUB_OUTPUT": "",
        }), patch("sys.argv", ["launch.py", "--check"]), \
                patch("launch.oci.config.validate_config"), \
                patch("launch.oci.core.ComputeClient"), \
                patch("launch.oci.core.BlockstorageClient"), \
                patch("launch.attempt", return_value="ready") as attempt, \
                patch("builtins.print"):
            self.assertEqual(launch.main(), 0)
            self.assertTrue(attempt.call_args.args[3])

    def test_no_secret_in_fatal_output(self):
        with patch.dict("os.environ", {"GITHUB_REPOSITORY": "owner/repo"}), \
                patch("launch.tempfile.TemporaryDirectory", side_effect=ValueError("SECRET")), \
                patch("sys.argv", ["launch.py"]), patch("builtins.print") as output:
            self.assertEqual(launch.main(), 1)
            self.assertNotIn("SECRET", str(output.call_args))


if __name__ == "__main__":
    unittest.main()
