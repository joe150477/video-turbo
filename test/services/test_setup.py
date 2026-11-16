import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.config import config
from app.services import setup


class TestOnboardingState(unittest.TestCase):
    def setUp(self):
        self.original_app_config = dict(config.app)

    def tearDown(self):
        config.app.clear()
        config.app.update(self.original_app_config)

    def test_is_first_run_true_when_flag_absent(self):
        config.app.pop(setup.ONBOARDING_COMPLETED_KEY, None)
        self.assertTrue(setup.is_first_run())

    def test_mark_onboarding_completed_flips_is_first_run(self):
        config.app.pop(setup.ONBOARDING_COMPLETED_KEY, None)
        with patch("app.config.config.save_config"):
            setup.mark_onboarding_completed()
        self.assertFalse(setup.is_first_run())


class TestGeneralSettings(unittest.TestCase):
    def setUp(self):
        self.original_app_config = dict(config.app)
        self.original_ui_config = dict(config.ui)

    def tearDown(self):
        config.app.clear()
        config.app.update(self.original_app_config)
        config.ui.clear()
        config.ui.update(self.original_ui_config)

    def test_save_general_settings_persists_only_provided_fields(self):
        config.app["max_concurrent_tasks"] = 5
        with patch("app.config.config.save_config"):
            setup.save_general_settings({"max_concurrent_tasks": 3})

        self.assertEqual(config.app["max_concurrent_tasks"], 3)

    def test_get_general_settings_reports_current_values(self):
        config.app["output_directory"] = "/tmp/videos"
        config.app["video_aspect"] = "16:9"
        config.ui["voice_name"] = "es-MX-DaliaNeural-Female"

        settings = setup.get_general_settings()

        self.assertEqual(settings["output_directory"], "/tmp/videos")
        self.assertEqual(settings["video_aspect"], "16:9")
        self.assertEqual(settings["voice_name"], "es-MX-DaliaNeural-Female")

    def test_save_and_get_brand_settings(self):
        with patch("app.config.config.save_config"):
            setup.save_brand_settings(
                {
                    "brand_context": "Mi marca vende café artesanal, tono cercano.",
                    "logo_position": "top-left",
                    "logo_size": 20,
                    "use_own_materials": True,
                }
            )
        settings = setup.get_brand_settings()
        self.assertIn("café", settings["brand_context"])
        self.assertEqual(settings["logo_position"], "top-left")
        self.assertEqual(settings["logo_size"], 20)
        self.assertTrue(settings["use_own_materials"])

    def test_brand_context_is_length_capped(self):
        with patch("app.config.config.save_config"):
            setup.save_brand_settings({"brand_context": "x" * 5000})
        self.assertLessEqual(len(setup.get_brand_settings()["brand_context"]), 2000)

    def test_set_and_clear_logo_filename(self):
        with patch("app.config.config.save_config"):
            setup.set_logo_filename("logo.png")
            self.assertEqual(setup.get_brand_settings()["logo_filename"], "logo.png")
            setup.clear_logo()
            self.assertEqual(setup.get_brand_settings()["logo_filename"], "")


class TestImportMaterialsFromFolder(unittest.TestCase):
    def test_missing_folder_reports_friendly_message(self):
        result = setup.import_materials_from_folder("/no/such/folder")
        self.assertFalse(result["ok"])
        self.assertEqual(result["imported"], 0)

    def test_imports_only_media_files(self):
        import os
        import tempfile

        with tempfile.TemporaryDirectory() as source, tempfile.TemporaryDirectory() as dest:
            for name in ("clip.mp4", "foto.jpg", "notas.txt", "hoja.pdf"):
                with open(os.path.join(source, name), "wb") as handle:
                    handle.write(b"data")
            with patch("app.services.setup.utils.storage_dir", return_value=dest):
                result = setup.import_materials_from_folder(source)

            self.assertTrue(result["ok"])
            self.assertEqual(result["imported"], 2)  # only the mp4 and jpg
            copied = sorted(os.listdir(dest))
            self.assertEqual(copied, ["clip.mp4", "foto.jpg"])

    def test_empty_folder_reports_no_media_found(self):
        import tempfile

        with tempfile.TemporaryDirectory() as source, tempfile.TemporaryDirectory() as dest:
            with patch("app.services.setup.utils.storage_dir", return_value=dest):
                result = setup.import_materials_from_folder(source)
            self.assertTrue(result["ok"])
            self.assertEqual(result["imported"], 0)
            self.assertIn("No se encontraron", result["message_es"])


class TestLlmConnectionTest(unittest.TestCase):
    def setUp(self):
        self.original_app_config = dict(config.app)
        self.original_environ = dict(os.environ)

    def tearDown(self):
        config.app.clear()
        config.app.update(self.original_app_config)
        os.environ.clear()
        os.environ.update(self.original_environ)

    def test_gemini_success_reports_ok(self):
        with patch("app.services.llm._generate_response", return_value="OK"):
            result = setup.test_llm_connection("gemini", "fake-key")
        self.assertTrue(result["ok"])

    def test_new_providers_are_supported(self):
        # Kimi/DeepSeek/Qwen are already in the engine; the wizard must
        # accept them and route to their config fields.
        for provider in ("moonshot", "deepseek", "qwen"):
            with patch("app.services.llm._generate_response", return_value="OK"):
                result = setup.test_llm_connection(provider, "fake-key")
            self.assertTrue(result["ok"], provider)

    def test_zai_sets_base_url_and_model_then_restores(self):
        config.app.pop("zai_base_url", None)
        config.app.pop("zai_model_name", None)
        captured = {}

        def fake_generate(_prompt):
            captured["base_url"] = config.app.get("zai_base_url")
            captured["model"] = config.app.get("zai_model_name")
            captured["provider"] = config.app.get("llm_provider")
            return "OK"

        with patch("app.services.llm._generate_response", side_effect=fake_generate):
            result = setup.test_llm_connection(
                "zai", "fake-key", model_name="glm-4.6", base_url="https://api.z.ai/api/paas/v4"
            )

        self.assertTrue(result["ok"])
        # The candidate values were visible to the engine during the test...
        self.assertEqual(captured["base_url"], "https://api.z.ai/api/paas/v4")
        self.assertEqual(captured["model"], "glm-4.6")
        self.assertEqual(captured["provider"], "zai")
        # ...and cleared afterwards (nothing persisted by a mere test).
        self.assertFalse(config.app.get("zai_base_url"))

    def test_save_zai_persists_base_url_and_model(self):
        with patch("app.config.config.save_config"):
            setup.save_llm_provider(
                "zai", "real-key", model_name="glm-4.6", base_url="https://api.z.ai/api/paas/v4"
            )
        self.assertEqual(config.app["llm_provider"], "zai")
        self.assertEqual(config.app["zai_api_key"], "real-key")
        self.assertEqual(config.app["zai_base_url"], "https://api.z.ai/api/paas/v4")
        self.assertEqual(config.app["zai_model_name"], "glm-4.6")

    def test_gemini_failure_reports_translated_message(self):
        with patch(
            "app.services.llm._generate_response",
            return_value="Error: 401 Unauthorized: invalid_api_key",
        ):
            result = setup.test_llm_connection("gemini", "bad-key")
        self.assertFalse(result["ok"])
        self.assertIn("clave", result["message_es"].lower())

    def test_llm_connection_restores_previous_config_after_test(self):
        config.app["gemini_api_key"] = "previous-key"
        config.app["llm_provider"] = "openai"
        with patch("app.services.llm._generate_response", return_value="OK"):
            setup.test_llm_connection("gemini", "candidate-key")

        self.assertEqual(config.app["gemini_api_key"], "previous-key")
        self.assertEqual(config.app["llm_provider"], "openai")

    def test_ollama_checks_local_tags_endpoint(self):
        fake_response = SimpleNamespace(raise_for_status=lambda: None)
        with patch("app.services.setup.requests.get", return_value=fake_response) as get:
            result = setup.test_llm_connection("ollama", "")
        self.assertTrue(result["ok"])
        self.assertIn("/api/tags", get.call_args.args[0])

    def test_ollama_connection_error_reports_network_message(self):
        with patch("app.services.setup.requests.get", side_effect=ConnectionError("boom")):
            result = setup.test_llm_connection("ollama", "")
        self.assertFalse(result["ok"])

    def test_claude_sets_and_restores_anthropic_env_var(self):
        os.environ.pop("ANTHROPIC_API_KEY", None)
        with patch("app.services.llm._generate_response", return_value="OK") as generate:
            result = setup.test_llm_connection("claude", "sk-ant-fake")
            # while the request is (synchronously) "in flight" the candidate
            # key must be visible to litellm via the environment
            self.assertEqual(generate.call_count, 1)
        self.assertTrue(result["ok"])
        self.assertNotIn("ANTHROPIC_API_KEY", os.environ)

    def test_unsupported_provider_reports_friendly_message(self):
        result = setup.test_llm_connection("not-a-real-provider", "x")
        self.assertFalse(result["ok"])


class TestLlmProviderPersistence(unittest.TestCase):
    def setUp(self):
        self.original_app_config = dict(config.app)
        self.original_environ = dict(os.environ)

    def tearDown(self):
        config.app.clear()
        config.app.update(self.original_app_config)
        os.environ.clear()
        os.environ.update(self.original_environ)

    def test_save_llm_provider_persists_gemini_key(self):
        with patch("app.config.config.save_config"):
            setup.save_llm_provider("gemini", "gemini-key-123")
        self.assertEqual(config.app["llm_provider"], "gemini")
        self.assertEqual(config.app["gemini_api_key"], "gemini-key-123")

    def test_save_llm_provider_routes_claude_through_litellm(self):
        with patch("app.config.config.save_config"):
            setup.save_llm_provider("claude", "sk-ant-fake")
        self.assertEqual(config.app["llm_provider"], "litellm")
        self.assertIn("anthropic/", config.app["litellm_model_name"])
        self.assertEqual(os.environ["ANTHROPIC_API_KEY"], "sk-ant-fake")

    def test_get_llm_settings_masks_api_key(self):
        config.app["llm_provider"] = "gemini"
        config.app["gemini_api_key"] = "abcdefgh1234"
        settings = setup.get_llm_settings()
        self.assertEqual(settings["provider"], "gemini")
        self.assertTrue(settings["masked_api_key"].endswith("1234"))
        self.assertNotIn("abcdefgh", settings["masked_api_key"])


class TestMaterialProviderTest(unittest.TestCase):
    def setUp(self):
        self.original_app_config = dict(config.app)

    def tearDown(self):
        config.app.clear()
        config.app.update(self.original_app_config)

    def test_pexels_success(self):
        fake_response = SimpleNamespace(status_code=200, raise_for_status=lambda: None)
        with patch("app.services.setup.requests.get", return_value=fake_response):
            result = setup.test_material_provider("pexels", "a-key")
        self.assertTrue(result["ok"])

    def test_pexels_unauthorized_reports_invalid_key_message(self):
        fake_response = SimpleNamespace(status_code=401, raise_for_status=lambda: None)
        with patch("app.services.setup.requests.get", return_value=fake_response):
            result = setup.test_material_provider("pexels", "bad-key")
        self.assertFalse(result["ok"])
        self.assertIn("clave", result["message_es"].lower())

    def test_pixabay_timeout_reports_translated_message(self):
        with patch("app.services.setup.requests.get", side_effect=TimeoutError("timed out")):
            result = setup.test_material_provider("pixabay", "a-key")
        self.assertFalse(result["ok"])

    def test_unsupported_provider_reports_friendly_message(self):
        result = setup.test_material_provider("not-a-real-provider", "x")
        self.assertFalse(result["ok"])

    def test_save_material_provider_persists_as_single_item_list(self):
        with patch("app.config.config.save_config"):
            setup.save_material_provider("pixabay", "pixabay-key")
        self.assertEqual(config.app["pixabay_api_keys"], ["pixabay-key"])

    def test_get_material_settings_reports_which_providers_are_configured(self):
        config.app["pexels_api_keys"] = ["a-key"]
        config.app["pixabay_api_keys"] = []
        config.app["coverr_api_keys"] = []
        settings = setup.get_material_settings()
        self.assertEqual(settings, {"pexels": True, "pixabay": False, "coverr": False})


class TestDiagnostics(unittest.TestCase):
    def setUp(self):
        self.original_app_config = dict(config.app)

    def tearDown(self):
        config.app.clear()
        config.app.update(self.original_app_config)

    def test_ffmpeg_check_fails_when_binary_missing(self):
        with (
            patch("app.services.setup.utils.get_ffmpeg_binary", return_value="/no/such/ffmpeg"),
            patch("app.services.setup.subprocess.run", side_effect=FileNotFoundError()),
        ):
            result = setup._check_ffmpeg()
        self.assertFalse(result["ok"])
        self.assertIn("fix_hint_es", result)

    def test_disk_space_check_fails_when_low(self):
        low_space = SimpleNamespace(total=100 * 1024**3, used=99 * 1024**3, free=1024**2)
        with patch("app.services.setup.shutil.disk_usage", return_value=low_space):
            result = setup._check_disk_space(min_free_gb=1.0)
        self.assertFalse(result["ok"])

    def test_internet_check_fails_when_unreachable(self):
        with patch("app.services.setup.socket.create_connection", side_effect=OSError()):
            result = setup._check_internet()
        self.assertFalse(result["ok"])

    def test_llm_configured_check_fails_with_no_provider_key(self):
        config.app["llm_provider"] = "gemini"
        config.app["gemini_api_key"] = ""
        result = setup._check_llm_configured()
        self.assertFalse(result["ok"])

    def test_run_diagnostics_returns_a_result_per_check(self):
        with (
            patch(
                "app.services.setup._check_ffmpeg",
                return_value={"name": "ffmpeg", "ok": True, "message_es": ""},
            ),
            patch(
                "app.services.setup._check_disk_space",
                return_value={"name": "disk_space", "ok": True, "message_es": ""},
            ),
            patch(
                "app.services.setup._check_internet",
                return_value={"name": "internet", "ok": True, "message_es": ""},
            ),
            patch(
                "app.services.setup._check_output_folder_writable",
                return_value={"name": "output_folder", "ok": True, "message_es": ""},
            ),
            patch(
                "app.services.setup._check_llm_configured",
                return_value={"name": "llm_provider", "ok": True, "message_es": ""},
            ),
        ):
            checks = setup.run_diagnostics()
        self.assertEqual(len(checks), 5)
        self.assertTrue(all(check["ok"] for check in checks))


class TestBrandSettingsPersuasive(unittest.TestCase):
    def setUp(self):
        self.original_app_config = dict(config.app)

    def tearDown(self):
        config.app.clear()
        config.app.update(self.original_app_config)

    def test_persuasive_mode_defaults_on(self):
        config.app.pop("persuasive_mode", None)
        self.assertTrue(setup.get_brand_settings()["persuasive_mode"])

    def test_save_persuasive_fields(self):
        with patch("app.config.config.save_config"):
            setup.save_brand_settings(
                {
                    "persuasive_mode": False,
                    "target_audience": "Padres estrato 4-6 en Barranquilla",
                    "role_models": {"research": "gemini", "qa": ""},
                }
            )
        brand = setup.get_brand_settings()
        self.assertFalse(brand["persuasive_mode"])
        self.assertEqual(brand["target_audience"], "Padres estrato 4-6 en Barranquilla")
        # Empty provider entries are dropped; only real overrides are kept.
        self.assertEqual(brand["role_models"], {"research": "gemini"})


class TestMaterialsFolderMemory(unittest.TestCase):
    def setUp(self):
        self.original_app_config = dict(config.app)

    def tearDown(self):
        config.app.clear()
        config.app.update(self.original_app_config)

    def test_get_materials_folder_defaults_empty(self):
        config.app.pop("materials_folder", None)
        self.assertEqual(setup.get_materials_folder(), "")

    def test_import_remembers_folder_for_later_sync(self):
        import tempfile

        with tempfile.TemporaryDirectory() as folder:
            with (
                patch("app.config.config.save_config"),
                patch(
                    "app.services.setup.utils.storage_dir",
                    return_value=tempfile.mkdtemp(),
                ),
            ):
                setup.import_materials_from_folder(folder)
            self.assertEqual(config.app["materials_folder"], folder)

    def test_sync_is_noop_without_a_configured_folder(self):
        config.app.pop("materials_folder", None)
        result = setup.sync_materials_folder()
        self.assertTrue(result["ok"])
        self.assertEqual(result["imported"], 0)

    def test_enhance_media_defaults_on_and_saves(self):
        config.app.pop("enhance_media", None)
        self.assertTrue(setup.get_brand_settings()["enhance_media"])
        with patch("app.config.config.save_config"):
            setup.save_brand_settings({"enhance_media": False})
        self.assertFalse(setup.get_brand_settings()["enhance_media"])


class TestBrandMemory(unittest.TestCase):
    def setUp(self):
        self.original_app_config = dict(config.app)

    def tearDown(self):
        config.app.clear()
        config.app.update(self.original_app_config)

    def test_record_used_content_appends_and_dedupes(self):
        config.app.pop("used_phrases", None)
        config.app.pop("preferred_ctas", None)
        with patch("app.config.config.save_config"):
            setup.record_used_content(hook="Gancho A", cta="CTA A")
            setup.record_used_content(hook="Gancho A", cta="CTA B")  # dup hook
        memory = setup.get_brand_memory()
        self.assertEqual(memory["used_phrases"], ["Gancho A"])
        self.assertEqual(memory["preferred_ctas"], ["CTA A", "CTA B"])

    def test_record_used_content_caps_history(self):
        config.app["used_phrases"] = [f"frase {i}" for i in range(setup._MAX_USED_PHRASES)]
        config.app.pop("preferred_ctas", None)
        with patch("app.config.config.save_config"):
            setup.record_used_content(hook="frase nueva")
        memory = setup.get_brand_memory()
        self.assertEqual(len(memory["used_phrases"]), setup._MAX_USED_PHRASES)
        self.assertEqual(memory["used_phrases"][-1], "frase nueva")
        self.assertNotIn("frase 0", memory["used_phrases"])

    def test_empty_hook_and_cta_are_ignored(self):
        config.app.pop("used_phrases", None)
        config.app.pop("preferred_ctas", None)
        with patch("app.config.config.save_config"):
            setup.record_used_content(hook="  ", cta="")
        memory = setup.get_brand_memory()
        self.assertEqual(memory["used_phrases"], [])
        self.assertEqual(memory["preferred_ctas"], [])


if __name__ == "__main__":
    unittest.main()
