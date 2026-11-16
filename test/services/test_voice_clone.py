import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.config import config
from app.services import setup, voice


class TestFishVoiceDetection(unittest.TestCase):
    def test_is_fish_voice(self):
        self.assertTrue(voice.is_fish_voice("fish:abc123:Mi voz"))
        self.assertFalse(voice.is_fish_voice("elevenlabs:x:y"))
        self.assertFalse(voice.is_fish_voice(""))

    def test_tts_dispatches_fish_voice(self):
        with patch("app.services.voice.fish_tts", return_value="SM") as fish:
            result = voice.tts(
                text="hola",
                voice_name="fish:ref123:Mi voz",
                voice_rate=1.0,
                voice_file="/tmp/out.mp3",
            )
        self.assertEqual(result, "SM")
        # reference_id extracted from the voice_name
        self.assertEqual(fish.call_args.args[1], "ref123")


class TestCreateFishVoiceClone(unittest.TestCase):
    def setUp(self):
        self.original = dict(config.app)
        config.app["fish_api_key"] = "fk-test"

    def tearDown(self):
        config.app.clear()
        config.app.update(self.original)

    def test_returns_model_id_on_success(self):
        fake = SimpleNamespace(status_code=200, json=lambda: {"_id": "model-xyz"})
        with (
            patch("app.services.voice.requests.post", return_value=fake) as post,
            patch("app.services.voice.os.path.exists", return_value=True),
            patch("builtins.open", MagicMock()),
        ):
            model_id = voice.create_fish_voice_clone("/tmp/sample.mp3", "Mi voz")
        self.assertEqual(model_id, "model-xyz")
        # Verified endpoint from Fish docs.
        self.assertEqual(post.call_args.args[0], "https://api.fish.audio/model")

    def test_returns_empty_without_api_key(self):
        config.app["fish_api_key"] = ""
        with patch("app.services.voice.os.path.exists", return_value=True):
            self.assertEqual(voice.create_fish_voice_clone("/tmp/s.mp3", "V"), "")


class TestSetupVoiceClone(unittest.TestCase):
    def setUp(self):
        self.original_app = dict(config.app)
        self.original_ui = dict(config.ui)

    def tearDown(self):
        config.app.clear()
        config.app.update(self.original_app)
        config.ui.clear()
        config.ui.update(self.original_ui)

    def test_requires_fish_key(self):
        config.app.pop("fish_api_key", None)
        result = setup.create_voice_clone("/tmp/s.mp3", "Mi voz")
        self.assertFalse(result["ok"])

    def test_success_sets_default_voice_and_stores_clone(self):
        config.app["fish_api_key"] = "fk"
        with (
            patch("app.services.voice.create_fish_voice_clone", return_value="model-1"),
            patch("app.config.config.save_config"),
        ):
            result = setup.create_voice_clone("/tmp/s.mp3", "Voz Colegio")
        self.assertTrue(result["ok"])
        self.assertEqual(result["voice_name"], "fish:model-1:Voz Colegio")
        self.assertEqual(config.ui["voice_name"], "fish:model-1:Voz Colegio")
        self.assertEqual(config.app["cloned_voices"][-1]["id"], "model-1")

    def test_failure_reports_friendly_message(self):
        config.app["fish_api_key"] = "fk"
        with (
            patch("app.services.voice.create_fish_voice_clone", return_value=""),
            patch("app.config.config.save_config"),
        ):
            result = setup.create_voice_clone("/tmp/s.mp3", "V")
        self.assertFalse(result["ok"])


class TestMimikaVoice(unittest.TestCase):
    def test_is_mimika_voice(self):
        self.assertTrue(voice.is_mimika_voice("mimika:chatterbox:MiVoz"))
        self.assertFalse(voice.is_mimika_voice("fish:x:y"))
        self.assertFalse(voice.is_mimika_voice(""))

    def test_tts_dispatches_mimika_voice_with_engine_and_name(self):
        with patch("app.services.voice.mimika_tts", return_value="SM") as m:
            result = voice.tts(
                text="hola",
                voice_name="mimika:qwen3:Voz Colegio",
                voice_rate=1.0,
                voice_file="/tmp/out.wav",
            )
        self.assertEqual(result, "SM")
        self.assertEqual(m.call_args.args[1], "Voz Colegio")  # name
        self.assertEqual(m.call_args.kwargs.get("engine"), "qwen3")

    def test_create_clone_posts_multipart_and_returns_name(self):
        fake = SimpleNamespace(status_code=200, text="ok")
        with (
            patch("app.services.voice.requests.post", return_value=fake) as post,
            patch("app.services.voice.os.path.exists", return_value=True),
            patch("builtins.open", MagicMock()),
        ):
            name = voice.create_mimika_voice_clone("/tmp/s.wav", "MiVoz", "chatterbox")
        self.assertEqual(name, "MiVoz")
        self.assertTrue(post.call_args.args[0].endswith("/api/chatterbox/voices"))

    def test_language_mapping_per_engine(self):
        with patch.dict(config.app, {"content_language": "Español (Colombia)"}, clear=False):
            self.assertEqual(voice._mimika_language_for("chatterbox"), "es")
            self.assertEqual(voice._mimika_language_for("qwen3"), "Spanish")
        with patch.dict(config.app, {"content_language": "Inglés"}, clear=False):
            self.assertEqual(voice._mimika_language_for("chatterbox"), "en")
            self.assertEqual(voice._mimika_language_for("qwen3"), "English")


class TestSetupMimikaClone(unittest.TestCase):
    def setUp(self):
        self.original_app = dict(config.app)
        self.original_ui = dict(config.ui)

    def tearDown(self):
        config.app.clear()
        config.app.update(self.original_app)
        config.ui.clear()
        config.ui.update(self.original_ui)

    def test_fails_when_mimika_not_running(self):
        with patch(
            "app.services.setup.get_mimika_status",
            return_value={"reachable": False, "engines": [], "base_url": "x"},
        ):
            result = setup.create_mimika_clone("/tmp/s.wav", "Mi voz", "chatterbox")
        self.assertFalse(result["ok"])

    def test_success_sets_default_local_voice(self):
        with (
            patch(
                "app.services.setup.get_mimika_status",
                return_value={"reachable": True, "engines": ["chatterbox"], "base_url": "x"},
            ),
            patch("app.services.voice.create_mimika_voice_clone", return_value="Voz Colegio"),
            patch("app.config.config.save_config"),
        ):
            result = setup.create_mimika_clone("/tmp/s.wav", "Voz Colegio", "chatterbox")
        self.assertTrue(result["ok"])
        self.assertEqual(result["voice_name"], "mimika:chatterbox:Voz Colegio")
        self.assertEqual(config.ui["voice_name"], "mimika:chatterbox:Voz Colegio")


class TestFishConnection(unittest.TestCase):
    def test_ok_on_200(self):
        with patch(
            "app.services.setup.requests.get",
            return_value=SimpleNamespace(status_code=200),
        ):
            self.assertTrue(setup.test_fish_connection("fk")["ok"])

    def test_invalid_key_on_401(self):
        with patch(
            "app.services.setup.requests.get",
            return_value=SimpleNamespace(status_code=401),
        ):
            self.assertFalse(setup.test_fish_connection("bad")["ok"])

    def test_empty_key_rejected(self):
        self.assertFalse(setup.test_fish_connection("")["ok"])


if __name__ == "__main__":
    unittest.main()
