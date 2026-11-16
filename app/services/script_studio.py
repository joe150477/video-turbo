"""Persuasive multi-step script chain: Research -> Marketing -> Copywriter -> QA.

The classic single-shot ``llm.generate_script`` writes generic narration. A
business that needs to *sell* — e.g. convince a parent to pay a high tuition —
needs more than that. This module chains four focused steps, each with a single
job, and gates the result with a quality check that can reject and retry:

  1. Research      — grounds the video in the real audience and brand context.
  2. Marketing     — picks a copy framework (AIDA / PAS / StoryBrand), the hook,
                     the core emotion and one call to action. It does NOT write
                     the final copy.
  3. Copywriter    — writes the spoken script following the marketing brief.
  4. Quality (QA)  — checks the copy has the CTA, fits the requested length and
                     does not reuse phrases from previous videos. On failure it
                     asks the copywriter to rewrite once with the QA feedback.

Every step calls ``llm._generate_response`` and may be routed to a different
model via ``role_models`` (an optional role -> provider map); a role with no
entry uses the globally configured provider, so the whole chain works with a
single configured API key and only improves if more are added.

Robustness first: if any step raises or returns nothing usable, the chain
degrades gracefully to the classic single-shot script so a video is always
produced — the persuasive layer can only make the result better, never break it.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from loguru import logger

from app.services import llm

# Roles that may be individually routed to a specific provider.
ROLE_RESEARCH = "research"
ROLE_MARKETING = "marketing"
ROLE_COPYWRITER = "copywriter"
ROLE_QA = "qa"
ALL_ROLES = (ROLE_RESEARCH, ROLE_MARKETING, ROLE_COPYWRITER, ROLE_QA)

# Keep the research brief short so the chain stays cheap and fast.
_MAX_RESEARCH_CHARS = 1200


@dataclass
class PersuasiveResult:
    """Outcome of the persuasive chain.

    ``script`` is always present (falling back to the classic script if needed).
    The other fields describe how it was produced, for logging, QA transparency
    and brand memory (``hook``/``cta`` are recorded so later videos don't repeat
    them).
    """

    script: str
    hook: str = ""
    cta: str = ""
    framework: str = ""
    emotion: str = ""
    research: str = ""
    qa_passed: bool = False
    qa_notes: list[str] = field(default_factory=list)
    used_fallback: bool = False


def _provider_for(role: str, role_models: dict[str, str] | None) -> str:
    """Return the provider override for a role, or "" to use the default."""
    if not role_models:
        return ""
    value = role_models.get(role, "")
    return str(value or "").strip()


def _ask(role: str, prompt: str, role_models: dict[str, str] | None) -> str:
    """Run one chain step, routed to the role's provider (or the default)."""
    provider = _provider_for(role, role_models)
    response = llm._generate_response(prompt=prompt, provider_override=provider)
    if isinstance(response, str) and response.startswith("Error: "):
        # llm._generate_response returns an "Error: ..." string on some provider
        # failures instead of raising; treat that as a hard failure for the step.
        raise RuntimeError(f"{role} step failed: {response}")
    return (response or "").strip()


def _parse_json_object(text: str) -> dict:
    """Best-effort parse of a JSON object from an LLM response.

    Reuses ``llm._strip_code_fence`` for fenced output, then falls back to
    extracting the first ``{...}`` block — mirroring the recovery llm.py already
    does for arrays.
    """
    cleaned = llm._strip_code_fence(text)
    try:
        data = json.loads(cleaned)
    except (ValueError, TypeError):
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if not match:
            raise ValueError("no JSON object found in response")
        data = json.loads(match.group())
    if not isinstance(data, dict):
        raise ValueError("parsed JSON is not an object")
    return data


def _research(
    subject: str,
    brand_context: str,
    audience: str,
    role_models: dict[str, str] | None,
) -> str:
    prompt = f"""
# Rol: Investigador de marketing

## Objetivo
Reúne el contexto real que necesita un video corto para conectar con su público.
No escribas el guion. Entrega solo hallazgos accionables.

## Tema del video
{subject}

## Contexto de la marca (puede estar vacío)
{brand_context or "(sin contexto de marca)"}

## Público objetivo (puede estar vacío)
{audience or "(no especificado)"}

## Entrega (máximo 6 viñetas cortas)
- Dolores y miedos reales de este público.
- Deseos y aspiraciones concretas.
- Objeciones típicas antes de decidir.
- Palabras y tono que les resuenan.
No incluyas encabezados de sección, solo las viñetas.
""".strip()
    brief = _ask(ROLE_RESEARCH, prompt, role_models)
    return brief[:_MAX_RESEARCH_CHARS]


def _marketing_brief(
    subject: str,
    research: str,
    brand_context: str,
    role_models: dict[str, str] | None,
) -> dict:
    prompt = f"""
# Rol: Estratega de marketing (StoryBrand, AIDA, PAS, Hormozi, Cialdini)

## Objetivo
Con base en la investigación, decide la ESTRATEGIA del video. No escribas el
guion todavía; solo define la estructura persuasiva.

## Tema
{subject}

## Contexto de la marca
{brand_context or "(sin contexto de marca)"}

## Investigación
{research or "(sin investigación)"}

## Devuelve SOLO un objeto JSON (sin texto adicional, sin markdown) con:
{{
  "framework": "AIDA | PAS | StoryBrand",
  "hook": "el gancho de los primeros 3 segundos, una frase",
  "emotion": "la emoción principal a provocar",
  "cta": "una sola llamada a la acción, clara y específica"
}}
""".strip()
    raw = _ask(ROLE_MARKETING, prompt, role_models)
    data = _parse_json_object(raw)
    brief = {
        "framework": str(data.get("framework", "")).strip()[:60],
        "hook": str(data.get("hook", "")).strip()[:300],
        "emotion": str(data.get("emotion", "")).strip()[:120],
        "cta": str(data.get("cta", "")).strip()[:300],
    }
    if not brief["hook"] and not brief["cta"]:
        raise ValueError("marketing brief has neither hook nor CTA")
    return brief


def _copywriter(
    subject: str,
    language: str,
    paragraph_number: int,
    brief: dict,
    brand_context: str,
    role_models: dict[str, str] | None,
    qa_feedback: str = "",
) -> str:
    language_line = f"- Idioma: {language}\n" if language else ""
    feedback_block = ""
    if qa_feedback:
        feedback_block = f"""

## Corrige estos problemas de la versión anterior
{qa_feedback}
""".rstrip()
    prompt = f"""
# Rol: Copywriter de video

## Objetivo
Escribe SOLO el texto hablado (voz en off) del video. Nada de investigación ni
explicaciones. Sin markdown, sin títulos, sin acotaciones como "narrador" o
"voz en off".

## Tema
{subject}

## Instrucciones de estilo
{language_line}- Párrafos aproximados: {paragraph_number}
- Framework: {brief.get("framework", "")}
- Empieza con este gancho en los primeros segundos: {brief.get("hook", "")}
- Emoción a transmitir: {brief.get("emotion", "")}
- Termina con esta llamada a la acción: {brief.get("cta", "")}

## Contexto de la marca (respeta el tono)
{brand_context or "(sin contexto de marca)"}{feedback_block}

Devuelve únicamente el guion, listo para leer en voz alta.
""".strip()
    script = _ask(ROLE_COPYWRITER, prompt, role_models)
    # Reuse the classic cleaner so downstream stages see the same shape of text.
    return llm.format_script_text(script)


def _qa(
    script: str,
    brief: dict,
    language: str,
    used_phrases: list[str] | None,
    role_models: dict[str, str] | None,
) -> dict:
    used_block = "\n".join(f"- {p}" for p in (used_phrases or [])[:40]) or "(ninguna)"
    prompt = f"""
# Rol: Control de calidad de video

## Objetivo
Revisa el guion. Sé estricto pero justo. Devuelve SOLO un objeto JSON.

## Guion
{script}

## Debía cumplir
- Llamada a la acción esperada: {brief.get("cta", "")}
- Gancho esperado al inicio: {brief.get("hook", "")}
- Idioma: {language or "(el del tema)"}

## Frases ya usadas en videos anteriores (evita repetirlas)
{used_block}

## Revisa
- ¿Incluye una llamada a la acción clara?
- ¿Arranca con un gancho fuerte?
- ¿Evita repetir las frases anteriores?
- ¿Suena natural (no robótico) y sin errores evidentes?

## Devuelve SOLO este JSON
{{
  "passed": true/false,
  "notes": ["problema 1", "problema 2"]
}}
""".strip()
    raw = _ask(ROLE_QA, prompt, role_models)
    data = _parse_json_object(raw)
    notes = data.get("notes", [])
    if not isinstance(notes, list):
        notes = [str(notes)]
    return {
        "passed": bool(data.get("passed", False)),
        "notes": [str(n).strip() for n in notes if str(n).strip()][:10],
    }


def generate_persuasive_script(
    video_subject: str,
    language: str = "",
    paragraph_number: int = 1,
    brand_context: str = "",
    audience: str = "",
    used_phrases: list[str] | None = None,
    role_models: dict[str, str] | None = None,
) -> PersuasiveResult:
    """Run the persuasive chain, degrading to the classic script on any failure."""
    try:
        research = _research(video_subject, brand_context, audience, role_models)
        brief = _marketing_brief(video_subject, research, brand_context, role_models)
        script = _copywriter(
            video_subject,
            language,
            paragraph_number,
            brief,
            brand_context,
            role_models,
        )
        if not script:
            raise ValueError("copywriter returned an empty script")

        qa = _qa(script, brief, language, used_phrases, role_models)
        if not qa["passed"]:
            feedback = (
                "\n".join(f"- {n}" for n in qa["notes"])
                or "- Mejora el gancho y la llamada a la acción."
            )
            logger.warning(f"QA rejected the script, rewriting once. Notes: {qa['notes']}")
            retry = _copywriter(
                video_subject,
                language,
                paragraph_number,
                brief,
                brand_context,
                role_models,
                qa_feedback=feedback,
            )
            if retry:
                script = retry
                # Re-check so the caller knows whether the rewrite satisfied QA.
                qa = _qa(script, brief, language, used_phrases, role_models)

        logger.success(
            f"persuasive script ready (framework={brief.get('framework')}, "
            f"qa_passed={qa['passed']})"
        )
        return PersuasiveResult(
            script=script,
            hook=brief.get("hook", ""),
            cta=brief.get("cta", ""),
            framework=brief.get("framework", ""),
            emotion=brief.get("emotion", ""),
            research=research,
            qa_passed=qa["passed"],
            qa_notes=qa["notes"],
            used_fallback=False,
        )
    except Exception as exc:  # noqa: BLE001 - deliberately broad: never break generation
        logger.warning(f"persuasive chain failed ({exc}); falling back to the classic script")
        fallback = llm.generate_script(
            video_subject=video_subject,
            language=language,
            paragraph_number=paragraph_number,
        )
        return PersuasiveResult(script=fallback or "", used_fallback=True)
