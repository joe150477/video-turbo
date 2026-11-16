import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services import branding


class _FakeClip:
    def __init__(self, size=(1080, 1920), duration=10.0):
        self.size = size
        self.duration = duration


def _params(**kwargs):
    base = {"logo_path": "", "logo_position": "bottom-right", "logo_size": 12}
    base.update(kwargs)
    return SimpleNamespace(**base)


class TestApplyLogoOverlay(unittest.TestCase):
    def test_no_op_when_no_logo_configured(self):
        clip = _FakeClip()
        result = branding.apply_logo_overlay(clip, _params(logo_path=""))
        self.assertIs(result, clip)

    def test_no_op_when_logo_file_missing(self):
        clip = _FakeClip()
        with patch("app.services.branding.resolve_logo_path", return_value=None):
            result = branding.apply_logo_overlay(clip, _params(logo_path="logo.png"))
        self.assertIs(result, clip)

    def test_composites_logo_when_configured(self):
        clip = _FakeClip()
        fake_logo = MagicMock()
        fake_logo.size = (200, 100)
        fake_logo.with_duration.return_value = fake_logo
        fake_logo.resized.return_value = fake_logo
        fake_logo.with_position.return_value = fake_logo

        with (
            patch("app.services.branding.resolve_logo_path", return_value="/tmp/logo.png"),
            patch("app.services.branding.ImageClip", return_value=fake_logo),
            patch("app.services.branding.CompositeVideoClip", return_value="composited") as comp,
        ):
            result = branding.apply_logo_overlay(clip, _params(logo_path="logo.png"))

        self.assertEqual(result, "composited")
        comp.assert_called_once()

    def test_failure_returns_original_clip(self):
        # A broken logo must never fail the whole video render.
        clip = _FakeClip()
        with (
            patch("app.services.branding.resolve_logo_path", return_value="/tmp/logo.png"),
            patch("app.services.branding.ImageClip", side_effect=RuntimeError("bad image")),
        ):
            result = branding.apply_logo_overlay(clip, _params(logo_path="logo.png"))
        self.assertIs(result, clip)


class TestPositionFor(unittest.TestCase):
    def test_all_corners_are_within_frame(self):
        for position in ["top-left", "top-right", "bottom-left", "bottom-right"]:
            pos = branding._position_for(position, 1080, 1920, 120, 60)
            self.assertIsInstance(pos, tuple)
            self.assertGreaterEqual(pos[0], 0)
            self.assertGreaterEqual(pos[1], 0)

    def test_center_uses_keyword(self):
        self.assertEqual(
            branding._position_for("center", 1080, 1920, 120, 60), ("center", "center")
        )

    def test_unknown_position_falls_back_to_bottom_right(self):
        unknown = branding._position_for("nowhere", 1080, 1920, 120, 60)
        bottom_right = branding._position_for("bottom-right", 1080, 1920, 120, 60)
        self.assertEqual(unknown, bottom_right)


class TestResolveLogoPath(unittest.TestCase):
    def test_returns_none_for_empty_name(self):
        self.assertIsNone(branding.resolve_logo_path(""))

    def test_rejects_path_traversal(self):
        self.assertIsNone(branding.resolve_logo_path("../../etc/passwd"))

    def test_resolves_existing_logo(self):
        with tempfile.TemporaryDirectory() as tmp:
            logo = os.path.join(tmp, "logo.png")
            with open(logo, "wb") as f:
                f.write(b"fake")
            with patch("app.services.branding.logo_dir", return_value=tmp):
                # The security helper returns a realpath; on macOS /var is a
                # symlink to /private/var, so compare against the realpath.
                self.assertEqual(branding.resolve_logo_path("logo.png"), os.path.realpath(logo))


if __name__ == "__main__":
    unittest.main()
