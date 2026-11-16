import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services import script_studio


def _brief_json(hook="Gancho inicial", cta="Agenda tu cita hoy", framework="AIDA"):
    return json.dumps(
        {"framework": framework, "hook": hook, "emotion": "confianza", "cta": cta},
        ensure_ascii=False,
    )


def _qa_json(passed=True, notes=None):
    return json.dumps({"passed": passed, "notes": notes or []}, ensure_ascii=False)


class TestPersuasiveChainHappyPath(unittest.TestCase):
    def test_runs_four_steps_and_returns_structured_result(self):
        responses = [
            "- Los padres temen pagar de más\n- Quieren futuro para sus hijos",  # research
            _brief_json(),  # marketing
            "Este es el guion persuasivo. Agenda tu cita hoy.",  # copywriter
            _qa_json(passed=True),  # qa
        ]
        with patch("app.services.llm._generate_response", side_effect=responses) as mock_llm:
            result = script_studio.generate_persuasive_script(
                video_subject="Colegio en Barranquilla",
                language="Español (Colombia)",
                paragraph_number=1,
            )
        self.assertFalse(result.used_fallback)
        self.assertTrue(result.qa_passed)
        self.assertEqual(result.framework, "AIDA")
        self.assertEqual(result.hook, "Gancho inicial")
        self.assertEqual(result.cta, "Agenda tu cita hoy")
        self.assertIn("guion persuasivo", result.script)
        self.assertEqual(mock_llm.call_count, 4)


class TestPersuasiveChainQaRetry(unittest.TestCase):
    def test_rewrites_once_when_qa_fails(self):
        responses = [
            "investigación",  # research
            _brief_json(),  # marketing
            "Primera versión sin CTA.",  # copywriter (rejected)
            _qa_json(passed=False, notes=["Falta la llamada a la acción"]),  # qa fail
            "Segunda versión. Agenda tu cita hoy.",  # copywriter rewrite
            _qa_json(passed=True),  # qa pass
        ]
        with patch("app.services.llm._generate_response", side_effect=responses) as mock_llm:
            result = script_studio.generate_persuasive_script(
                video_subject="Colegio", language="es"
            )
        self.assertFalse(result.used_fallback)
        self.assertTrue(result.qa_passed)
        self.assertIn("Segunda versión", result.script)
        # 4 base steps + 1 rewrite + 1 re-check = 6 calls
        self.assertEqual(mock_llm.call_count, 6)


class TestPersuasiveChainFallback(unittest.TestCase):
    def test_falls_back_to_classic_when_marketing_json_is_unusable(self):
        responses = [
            "investigación",  # research
            "esto no es json y no tiene hook ni cta",  # marketing (unparseable)
        ]
        with (
            patch("app.services.llm._generate_response", side_effect=responses),
            patch("app.services.llm.generate_script", return_value="guion clásico") as mock_classic,
        ):
            result = script_studio.generate_persuasive_script(
                video_subject="Colegio", language="es"
            )
        self.assertTrue(result.used_fallback)
        self.assertEqual(result.script, "guion clásico")
        mock_classic.assert_called_once()

    def test_falls_back_when_a_step_raises(self):
        with (
            patch("app.services.llm._generate_response", side_effect=RuntimeError("boom")),
            patch("app.services.llm.generate_script", return_value="guion clásico"),
        ):
            result = script_studio.generate_persuasive_script(video_subject="X")
        self.assertTrue(result.used_fallback)
        self.assertEqual(result.script, "guion clásico")


class TestMultiModelRouting(unittest.TestCase):
    def test_routes_each_role_to_its_provider(self):
        responses = ["research", _brief_json(), "copy. CTA.", _qa_json(True)]
        role_models = {
            "research": "gemini",
            "marketing": "openai",
            "copywriter": "openai",
            "qa": "deepseek",
        }
        with patch("app.services.llm._generate_response", side_effect=responses) as mock_llm:
            script_studio.generate_persuasive_script(video_subject="X", role_models=role_models)
        overrides = [c.kwargs.get("provider_override") for c in mock_llm.call_args_list]
        self.assertEqual(overrides, ["gemini", "openai", "openai", "deepseek"])

    def test_empty_role_models_uses_default_provider(self):
        responses = ["research", _brief_json(), "copy. CTA.", _qa_json(True)]
        with patch("app.services.llm._generate_response", side_effect=responses) as mock_llm:
            script_studio.generate_persuasive_script(video_subject="X")
        overrides = [c.kwargs.get("provider_override") for c in mock_llm.call_args_list]
        self.assertEqual(overrides, ["", "", "", ""])


class TestQaSeesUsedPhrases(unittest.TestCase):
    def test_previous_phrases_are_passed_into_the_qa_prompt(self):
        responses = ["research", _brief_json(), "copy. CTA.", _qa_json(True)]
        captured = {}

        def _capture(prompt, provider_override=""):
            # Record the QA prompt (the 4th call).
            captured.setdefault("prompts", []).append(prompt)
            return responses[len(captured["prompts"]) - 1]

        with patch("app.services.llm._generate_response", side_effect=_capture):
            script_studio.generate_persuasive_script(
                video_subject="X", used_phrases=["frase repetida anterior"]
            )
        qa_prompt = captured["prompts"][3]
        self.assertIn("frase repetida anterior", qa_prompt)


if __name__ == "__main__":
    unittest.main()
