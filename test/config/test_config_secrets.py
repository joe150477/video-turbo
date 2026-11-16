import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.config import config


class TestLegacyKeyringMigration(unittest.TestCase):
    """API keys are stored in config.toml (a private per-user file), not the
    OS Keychain — reading the Keychain from the unsigned packaged app hung
    startup. These tests lock in the plaintext behavior and the one-time
    migration away from the old `__keyring__` sentinel."""

    def test_sentinel_scalar_migrates_to_empty(self):
        self.assertEqual(config._migrate_legacy_scalar(config._KEYRING_SENTINEL), "")

    def test_real_scalar_value_passes_through(self):
        self.assertEqual(config._migrate_legacy_scalar("gsk_realkey"), "gsk_realkey")

    def test_sentinel_list_migrates_to_empty_list(self):
        self.assertEqual(config._migrate_legacy_list(config._KEYRING_SENTINEL), [])

    def test_real_list_value_passes_through(self):
        self.assertEqual(config._migrate_legacy_list(["key1", "key2"]), ["key1", "key2"])

    def test_save_config_writes_plaintext_keys_no_sentinel(self):
        original = dict(config.app)
        try:
            config.app["gemini_api_key"] = "plain-secret"
            with patch("builtins.open", MagicMock()), patch("toml.dumps") as fake_dumps:
                config.save_config()
            persisted_app = fake_dumps.call_args.args[0]["app"]
            # The real value is written as-is — no keyring, no sentinel.
            self.assertEqual(persisted_app["gemini_api_key"], "plain-secret")
            self.assertNotEqual(persisted_app["gemini_api_key"], config._KEYRING_SENTINEL)
        finally:
            config.app.clear()
            config.app.update(original)

    def test_config_module_never_imports_keyring(self):
        # Guard against re-introducing the blocking Keychain dependency.
        import inspect

        source = inspect.getsource(config)
        self.assertNotIn("import keyring", source)


if __name__ == "__main__":
    unittest.main()
