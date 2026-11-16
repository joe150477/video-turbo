import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastapi.testclient import TestClient

from app.asgi import app
from app.config import config

client = TestClient(app)


class TestSystemEndpoints(unittest.TestCase):
    def setUp(self):
        self.original_app_config = dict(config.app)

    def tearDown(self):
        config.app.clear()
        config.app.update(self.original_app_config)

    def test_ping(self):
        response = client.get("/api/v1/system/ping")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"], {"ok": True})

    def test_onboarding_status_reflects_config_flag(self):
        config.app["onboarding_completed"] = False
        response = client.get("/api/v1/system/onboarding/status")
        self.assertEqual(response.json()["data"], {"completed": False})

    def test_complete_onboarding_persists_flag(self):
        with patch("app.config.config.save_config"):
            response = client.post("/api/v1/system/onboarding/complete")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(config.app["onboarding_completed"])

    def test_llm_test_endpoint_rejects_unknown_provider(self):
        response = client.post(
            "/api/v1/system/settings/llm/test",
            json={"provider": "not-a-real-provider", "api_key": "x"},
        )
        self.assertEqual(response.status_code, 400)

    def test_llm_test_endpoint_returns_setup_service_result(self):
        with patch(
            "app.services.setup.test_llm_connection",
            return_value={"ok": True, "message_es": "Conectado correctamente."},
        ):
            response = client.post(
                "/api/v1/system/settings/llm/test",
                json={"provider": "gemini", "api_key": "fake-key"},
            )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["data"]["ok"])

    def test_diagnostics_endpoint_returns_all_checks(self):
        fake_checks = [{"name": "ffmpeg", "ok": True, "message_es": "ok"}]
        with patch("app.services.setup.run_diagnostics", return_value=fake_checks):
            response = client.get("/api/v1/system/diagnostics")
        body = response.json()["data"]
        self.assertEqual(body["checks"], fake_checks)
        self.assertTrue(body["all_ok"])

    def test_voices_endpoint_returns_grouped_catalog(self):
        response = client.get("/api/v1/system/voices")
        self.assertEqual(response.status_code, 200)
        groups = response.json()["data"]["groups"]
        self.assertTrue(any(g["language_label_es"] == "Español" for g in groups))

    def test_general_settings_roundtrip(self):
        with patch("app.config.config.save_config"):
            save_response = client.post(
                "/api/v1/system/settings/general", json={"max_concurrent_tasks": 4}
            )
        self.assertEqual(save_response.status_code, 200)

        get_response = client.get("/api/v1/system/settings/general")
        self.assertEqual(get_response.json()["data"]["max_concurrent_tasks"], 4)

    def test_brand_settings_roundtrip(self):
        with patch("app.config.config.save_config"):
            save = client.post(
                "/api/v1/system/settings/brand",
                json={"brand_context": "Marca de café", "logo_position": "top-left"},
            )
        self.assertEqual(save.status_code, 200)
        data = client.get("/api/v1/system/settings/brand").json()["data"]
        self.assertEqual(data["brand_context"], "Marca de café")
        self.assertEqual(data["logo_position"], "top-left")

    def test_logo_upload_rejects_non_image(self):
        response = client.post(
            "/api/v1/system/settings/brand/logo",
            files={"file": ("evil.exe", b"nope", "application/octet-stream")},
        )
        self.assertEqual(response.status_code, 400)

    def test_materials_listing_and_rejects_bad_upload(self):
        list_response = client.get("/api/v1/system/materials")
        self.assertEqual(list_response.status_code, 200)
        self.assertIn("materials", list_response.json()["data"])

        bad = client.post(
            "/api/v1/system/materials",
            files={"file": ("script.py", b"print(1)", "text/x-python")},
        )
        self.assertEqual(bad.status_code, 400)


if __name__ == "__main__":
    unittest.main()
