import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.utils import error_messages


class TestTranslateException(unittest.TestCase):
    def test_connection_error_maps_to_network_message(self):
        message, code = error_messages.translate_exception(ConnectionError("Connection refused"))
        self.assertEqual(code, "network_error")
        self.assertIn("internet", message.lower())

    def test_timeout_error_maps_to_network_message(self):
        message, code = error_messages.translate_exception(TimeoutError("timed out"))
        self.assertEqual(code, "network_error")

    def test_unauthorized_error_maps_to_invalid_api_key(self):
        message, code = error_messages.translate_exception(
            ValueError("401 Unauthorized: invalid_api_key")
        )
        self.assertEqual(code, "invalid_api_key")
        self.assertIn("clave", message.lower())

    def test_rate_limit_error_maps_to_rate_limited(self):
        message, code = error_messages.translate_exception(
            Exception("429 Too Many Requests: quota exceeded")
        )
        self.assertEqual(code, "rate_limited")

    def test_missing_ffmpeg_maps_to_missing_component(self):
        message, code = error_messages.translate_exception(
            FileNotFoundError("[Errno 2] No such file or directory: 'ffmpeg'")
        )
        self.assertEqual(code, "missing_component")

    def test_unknown_error_falls_back_to_generic_message_with_id(self):
        message, code = error_messages.translate_exception(RuntimeError("something exploded"))
        self.assertEqual(code, "unknown_error")
        self.assertIn("código", message.lower())

    def test_translated_message_never_leaks_technical_details(self):
        """No matter the exception, the user-facing text must never contain a
        traceback, a file path, or the raw exception text — that is exactly
        what would defeat the purpose of translating it in the first place."""
        try:
            raise RuntimeError("Traceback details: /Users/dev/project/app/services/llm.py line 42")
        except RuntimeError as exc:
            message, _code = error_messages.translate_exception(exc)

        self.assertNotIn("Traceback", message)
        self.assertNotIn(".py", message)
        self.assertNotIn("/Users/", message)

    def test_translate_message_classifies_a_plain_string_the_same_way(self):
        message, code = error_messages.translate_message(
            "API key not valid. Please pass a valid API key."
        )
        self.assertEqual(code, "invalid_api_key")


if __name__ == "__main__":
    unittest.main()
