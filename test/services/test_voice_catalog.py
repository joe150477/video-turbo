import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.config import config
from app.services import voice_catalog


class TestParseEdgeVoice(unittest.TestCase):
    def test_spanish_voice_gets_country_and_gender_label(self):
        friendly = voice_catalog._parse_edge_voice("es-CO-SalomeNeural-Female")
        assert friendly is not None
        self.assertEqual(friendly.label_es, "Español (Colombia) — Mujer")
        self.assertEqual(friendly.gender, "Female")

    def test_english_voice_gets_country_and_gender_label(self):
        friendly = voice_catalog._parse_edge_voice("en-AU-NatashaNeural-Female")
        assert friendly is not None
        self.assertEqual(friendly.label_es, "Inglés (Australia) — Mujer")

    def test_unknown_language_falls_back_to_uppercased_code(self):
        friendly = voice_catalog._parse_edge_voice("xx-YY-SomeNeural-Male")
        assert friendly is not None
        self.assertIn("XX", friendly.label_es)

    def test_malformed_name_without_gender_suffix_is_skipped(self):
        self.assertIsNone(voice_catalog._parse_edge_voice("not-a-valid-voice-name"))

    def test_never_leaks_the_raw_technical_name_in_the_label(self):
        friendly = voice_catalog._parse_edge_voice("zh-CN-XiaoxiaoNeural-Female")
        assert friendly is not None
        self.assertNotIn("Neural", friendly.label_es)
        self.assertNotIn("XiaoxiaoNeural", friendly.label_es)


class TestFriendlyVoiceCatalog(unittest.TestCase):
    def setUp(self):
        self.original_app_config = dict(config.app)
        self.original_elevenlabs_config = dict(config.elevenlabs)
        self.original_siliconflow_config = dict(config.siliconflow)

    def tearDown(self):
        config.app.clear()
        config.app.update(self.original_app_config)
        config.elevenlabs.clear()
        config.elevenlabs.update(self.original_elevenlabs_config)
        config.siliconflow.clear()
        config.siliconflow.update(self.original_siliconflow_config)

    def test_spanish_and_english_groups_come_first(self):
        groups = voice_catalog.get_friendly_voice_catalog()
        labels = [group.language_label_es for group in groups]
        self.assertEqual(labels[0], "Español")
        self.assertEqual(labels[1], "Inglés")

    def test_every_edge_voice_id_is_a_real_technical_voice_name(self):
        # The catalog must not invent a separate id space: the frontend
        # sends `id` straight back as `voice_name`, so it has to be exactly
        # what app.services.voice already understands.
        groups = voice_catalog.get_friendly_voice_catalog()
        spanish_group = next(g for g in groups if g.language_label_es == "Español")
        for friendly_voice in spanish_group.voices:
            self.assertTrue(friendly_voice.id.startswith("es-"))
            self.assertTrue(friendly_voice.id.endswith(("-Female", "-Male")))

    def test_elevenlabs_group_absent_without_api_key(self):
        config.elevenlabs["api_key"] = ""
        groups = voice_catalog.get_friendly_voice_catalog()
        labels = [group.language_label_es for group in groups]
        self.assertNotIn("ElevenLabs (tu cuenta)", labels)

    def test_elevenlabs_group_present_once_api_key_configured(self):
        config.elevenlabs["api_key"] = "fake-key"
        with patch(
            "app.services.voice.get_elevenlabs_voices",
            return_value=["elevenlabs:voice123:Ana"],
        ):
            groups = voice_catalog.get_friendly_voice_catalog()
        labels = [group.language_label_es for group in groups]
        self.assertIn("ElevenLabs (tu cuenta)", labels)

    def test_siliconflow_group_present_once_api_key_configured(self):
        config.siliconflow["api_key"] = "fake-key"
        groups = voice_catalog.get_friendly_voice_catalog()
        labels = [group.language_label_es for group in groups]
        self.assertIn("SiliconFlow", labels)


class TestSampleTextForVoice(unittest.TestCase):
    def test_spanish_voice_gets_spanish_sample(self):
        text = voice_catalog.sample_text_for_voice("es-CO-SalomeNeural-Female")
        self.assertEqual(text, voice_catalog._SAMPLE_TEXTS_BY_LANGUAGE["es"])

    def test_unrecognized_language_falls_back_to_default(self):
        text = voice_catalog.sample_text_for_voice("zh-CN-XiaoxiaoNeural-Female")
        self.assertEqual(text, voice_catalog._DEFAULT_SAMPLE_TEXT)


if __name__ == "__main__":
    unittest.main()
