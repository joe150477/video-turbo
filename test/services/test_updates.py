import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services import updates


def _fake_response(payload):
    return SimpleNamespace(json=lambda: payload, raise_for_status=lambda: None)


class TestCheckForUpdates(unittest.TestCase):
    def test_reports_no_update_when_version_cannot_be_determined(self):
        with (
            patch("app.services.updates._is_git_checkout", return_value=False),
            patch("app.services.updates._baked_build_commit", return_value=None),
        ):
            result = updates.check_for_updates()
        self.assertFalse(result["update_available"])
        self.assertIn("versión instalada", result["message_es"])

    def test_packaged_app_uses_baked_commit_and_guides_to_installer(self):
        # In the frozen app (no .git) an update can be detected but not
        # self-applied: the user is pointed to the installer instead.
        responses = [
            _fake_response({"sha": "remote999"}),
            _fake_response(
                {
                    "ahead_by": 1,
                    "commits": [{"commit": {"message": "New release"}}],
                    "files": [{"filename": "app/router.py"}],
                }
            ),
        ]
        with (
            patch("app.services.updates._is_git_checkout", return_value=False),
            patch("app.services.updates._baked_build_commit", return_value="baked111"),
            patch("app.services.updates.requests.get", side_effect=responses),
        ):
            result = updates.check_for_updates()

        self.assertTrue(result["update_available"])
        self.assertFalse(result["can_auto_apply"])
        self.assertIn("instalador", result["message_es"])

    def test_reports_up_to_date_when_commits_match(self):
        with (
            patch("app.services.updates._is_git_checkout", return_value=True),
            patch("app.services.updates.get_local_commit", return_value="abc123"),
            patch(
                "app.services.updates.requests.get",
                return_value=_fake_response({"sha": "abc123"}),
            ),
        ):
            result = updates.check_for_updates()
        self.assertFalse(result["update_available"])
        self.assertIn("más reciente", result["message_es"])

    def test_reports_available_and_compatible_update(self):
        responses = [
            _fake_response({"sha": "remote999"}),
            _fake_response(
                {
                    "ahead_by": 2,
                    "commits": [
                        {"commit": {"message": "Fix bug\n\ndetails"}},
                        {"commit": {"message": "Add feature"}},
                    ],
                    "files": [{"filename": "app/services/llm.py"}],
                }
            ),
        ]
        with (
            patch("app.services.updates._is_git_checkout", return_value=True),
            patch("app.services.updates.get_local_commit", return_value="local111"),
            patch("app.services.updates.requests.get", side_effect=responses),
        ):
            result = updates.check_for_updates()

        self.assertTrue(result["update_available"])
        self.assertTrue(result["can_auto_apply"])
        self.assertTrue(result["compatible"])
        self.assertEqual(result["changes"], ["Fix bug", "Add feature"])
        self.assertEqual(result["affected_custom_files"], [])

    def test_flags_incompatibility_when_a_customized_core_file_changes(self):
        responses = [
            _fake_response({"sha": "remote999"}),
            _fake_response(
                {
                    "ahead_by": 1,
                    "commits": [{"commit": {"message": "Refactor router"}}],
                    "files": [
                        {"filename": "app/router.py"},
                        {"filename": "README.md"},
                    ],
                }
            ),
        ]
        with (
            patch("app.services.updates._is_git_checkout", return_value=True),
            patch("app.services.updates.get_local_commit", return_value="local111"),
            patch("app.services.updates.requests.get", side_effect=responses),
        ):
            result = updates.check_for_updates()

        self.assertTrue(result["update_available"])
        self.assertFalse(result["compatible"])
        self.assertIn("app/router.py", result["affected_custom_files"])

    def test_network_error_is_translated_not_raised(self):
        with (
            patch("app.services.updates._is_git_checkout", return_value=True),
            patch("app.services.updates.get_local_commit", return_value="local111"),
            patch(
                "app.services.updates.requests.get",
                side_effect=ConnectionError("no network"),
            ),
        ):
            result = updates.check_for_updates()
        self.assertFalse(result["update_available"])
        self.assertIn("internet", result["message_es"].lower())


class TestGetLocalCommit(unittest.TestCase):
    def test_reads_baked_commit_when_not_a_git_checkout(
        self,
    ):
        with (
            patch("app.services.updates._is_git_checkout", return_value=False),
            patch("app.services.updates._baked_build_commit", return_value="baked999"),
        ):
            self.assertEqual(updates.get_local_commit(), "baked999")

    def test_returns_none_when_no_git_and_no_baked_commit(self):
        with (
            patch("app.services.updates._is_git_checkout", return_value=False),
            patch("app.services.updates._baked_build_commit", return_value=None),
        ):
            self.assertIsNone(updates.get_local_commit())


class TestApplyUpdate(unittest.TestCase):
    def test_refuses_when_not_a_git_checkout(self):
        with patch("app.services.updates._is_git_checkout", return_value=False):
            result = updates.apply_update()
        self.assertFalse(result["ok"])

    def test_restores_backup_when_merge_fails(self):
        import subprocess

        def fake_git(args):
            if args[:1] == ["merge"] and "--abort" not in args:
                raise subprocess.CalledProcessError(1, ["git", *args])
            return SimpleNamespace(stdout="", stderr="")

        with (
            patch("app.services.updates._is_git_checkout", return_value=True),
            patch("app.services.updates.create_backup", return_value="/tmp/fake-backup"),
            patch("app.services.updates._run_git", side_effect=fake_git),
            patch("app.services.updates._restore_backup") as restore,
        ):
            result = updates.apply_update()

        self.assertFalse(result["ok"])
        restore.assert_called_once_with("/tmp/fake-backup")
        self.assertIn("restauró", result["message_es"])

    def test_reports_success_when_merge_succeeds(self):
        with (
            patch("app.services.updates._is_git_checkout", return_value=True),
            patch("app.services.updates.create_backup", return_value="/tmp/fake-backup"),
            patch(
                "app.services.updates._run_git",
                return_value=SimpleNamespace(stdout="", stderr=""),
            ),
        ):
            result = updates.apply_update()

        self.assertTrue(result["ok"])
        self.assertIn("correctamente", result["message_es"])

    def test_aborts_cleanly_when_backup_cannot_be_created(self):
        with (
            patch("app.services.updates._is_git_checkout", return_value=True),
            patch("app.services.updates.create_backup", side_effect=OSError("disk full")),
            patch("app.services.updates._run_git") as run_git,
        ):
            result = updates.apply_update()

        self.assertFalse(result["ok"])
        self.assertIn("copia de seguridad", result["message_es"])
        run_git.assert_not_called()


if __name__ == "__main__":
    unittest.main()
