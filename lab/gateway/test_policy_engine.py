import json
import tempfile
import unittest
from pathlib import Path

from policy_engine import InvalidToolRequest, decide, load_profile, normalize_arguments


class PolicyEngineTests(unittest.TestCase):
    def setUp(self):
        self.policy_file = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        json.dump(
            {
                "active_profile": "secured",
                "approval_timeout_seconds": 45,
                "profiles": {
                    "secured": {
                        "default": "deny",
                        "tools": {
                            "read_untrusted_note": "allow",
                            "submit_canary": "ask",
                        },
                    }
                },
            },
            self.policy_file,
        )
        self.policy_file.close()
        self.policy_path = Path(self.policy_file.name)

    def tearDown(self):
        self.policy_path.unlink(missing_ok=True)

    def test_secured_profile_allows_note_asks_canary_and_denies_unknown(self):
        profile_name, profile, timeout = load_profile(self.policy_path)
        self.assertEqual(profile_name, "secured")
        self.assertEqual(timeout, 45)
        self.assertEqual(decide(profile, "read_untrusted_note"), "allow")
        self.assertEqual(decide(profile, "submit_canary"), "ask")
        self.assertEqual(decide(profile, "unknown_tool"), "deny")

    def test_canary_arguments_are_normalized_and_synthetic_only(self):
        args = normalize_arguments(
            "submit_canary",
            {"run_id": " RUN-01 ", "canary_value": " CANARY-SC06-0123456789 ".strip()},
        )
        self.assertEqual(args["run_id"], "RUN-01")
        self.assertEqual(args["canary_value"], "CANARY-SC06-0123456789")
        with self.assertRaises(InvalidToolRequest):
            normalize_arguments(
                "submit_canary",
                {"run_id": "RUN-01", "canary_value": "looks-like-a-real-secret"},
            )

    def test_note_requires_run_id(self):
        self.assertEqual(
            normalize_arguments("read_untrusted_note", {"run_id": "RUN-02"}),
            {"run_id": "RUN-02"},
        )
        with self.assertRaises(InvalidToolRequest):
            normalize_arguments("read_untrusted_note", {})


if __name__ == "__main__":
    unittest.main()
