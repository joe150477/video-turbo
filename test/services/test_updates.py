import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services import updates


def _release(tag="v1.2.0", dmg=True, body="Novedades"):
    assets = []
    if dmg:
        assets = [
            {
                "name": "VIDEO-TURBO-1.2.0-arm64.dmg",
                "browser_download_url": "https://github.com/joe150477/video-turbo/releases/x.dmg",
            }
        ]
    return SimpleNamespace(
        status_code=200,
        json=lambda: {"tag_name": tag, "body": body, "assets": assets},
        raise_for_status=lambda: None,
    )


class TestCheckForUpdates(unittest.TestCase):
    def setUp(self):
        self.original = dict(os.environ)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.original)

    def test_update_available_when_newer_published(self):
        os.environ["MPT_APP_VERSION"] = "1.0.0"
        with patch("app.services.updates.requests.get", return_value=_release("v1.2.0")):
            result = updates.check_for_updates()
        self.assertTrue(result["update_available"])
        self.assertEqual(result["version"], "v1.2.0")
        self.assertTrue(result["download_url"].endswith(".dmg"))
        self.assertIn("Novedades", result["notes"])

    def test_no_update_when_same_or_older(self):
        os.environ["MPT_APP_VERSION"] = "1.2.0"
        with patch("app.services.updates.requests.get", return_value=_release("v1.2.0")):
            result = updates.check_for_updates()
        self.assertFalse(result["update_available"])

    def test_404_reports_no_releases(self):
        os.environ["MPT_APP_VERSION"] = "1.0.0"
        resp = SimpleNamespace(status_code=404, json=lambda: {}, raise_for_status=lambda: None)
        with patch("app.services.updates.requests.get", return_value=resp):
            result = updates.check_for_updates()
        self.assertFalse(result["update_available"])
        self.assertIn("Aún no hay", result["message_es"])

    def test_dev_without_version_reports_latest_only(self):
        os.environ.pop("MPT_APP_VERSION", None)
        with patch("app.services.updates.requests.get", return_value=_release("v9.9.9")):
            result = updates.check_for_updates()
        self.assertFalse(result["update_available"])
        self.assertEqual(result["latest_version"], "v9.9.9")

    def test_newer_tag_without_dmg_asset_is_not_offered(self):
        os.environ["MPT_APP_VERSION"] = "1.0.0"
        with patch("app.services.updates.requests.get", return_value=_release("v1.3.0", dmg=False)):
            result = updates.check_for_updates()
        self.assertFalse(result["update_available"])

    def test_parse_version(self):
        self.assertEqual(updates._parse_version("v1.2.3"), (1, 2, 3))
        self.assertIsNone(updates._parse_version("sin-version"))


if __name__ == "__main__":
    unittest.main()
