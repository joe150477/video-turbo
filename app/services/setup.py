"""Backend logic behind the desktop app's onboarding wizard and settings screens.

Every function here reads and writes `app.config.config`'s module-level state
directly — the same object the rest of the app already uses — and persists
through the existing `config.save_config()`. None of this requires the user
to open `config.toml` themselves.
"""

import os
import shutil
import socket
import subprocess
from typing import Optional

import requests

from app.config import config
from app.services import llm, material
from app.utils import error_messages, utils

ONBOARDING_COMPLETED_KEY = "onboarding_completed"

# Providers offered as first-class choices in the wizard. Each maps to the
# config.toml field names `llm._generate_response` already reads. The
# optional "base_url" field is for OpenAI-compatible providers whose
# endpoint the user supplies (e.g. z.ai / GLM).
_LLM_PROVIDER_FIELDS = {
    "gemini": {"api_key": "gemini_api_key", "model": "gemini_model_name"},
    "openai": {"api_key": "openai_api_key", "model": "openai_model_name"},
    "groq": {"api_key": "groq_api_key", "model": "groq_model_name"},
    "moonshot": {"api_key": "moonshot_api_key", "model": "moonshot_model_name"},
    "deepseek": {"api_key": "deepseek_api_key", "model": "deepseek_model_name"},
    "qwen": {"api_key": "qwen_api_key", "model": "qwen_model_name"},
    "zai": {
        "api_key": "zai_api_key",
        "model": "zai_model_name",
        "base_url": "zai_base_url",
    },
}

# MoneyPrinterTurbo has no native Anthropic/Claude client; it is reached
# through the existing LiteLLM gateway, which reads the API key from the
# ANTHROPIC_API_KEY environment variable rather than from config.toml.
_CLAUDE_LITELLM_MODEL = "anthropic/claude-3-5-haiku-20241022"
_CLAUDE_ENV_VAR = "ANTHROPIC_API_KEY"

_MATERIAL_PROVIDER_CONFIG_KEYS = {
    "pexels": "pexels_api_keys",
    "pixabay": "pixabay_api_keys",
    "coverr": "coverr_api_keys",
}

_TEST_PROMPT = "Responde solo con la palabra OK."
_CONNECTED_MESSAGE = "Conectado correctamente."


# --------------------------------------------------------------------------
# Onboarding state
# --------------------------------------------------------------------------


def is_first_run() -> bool:
    return not bool(config.app.get(ONBOARDING_COMPLETED_KEY, False))


def mark_onboarding_completed() -> None:
    config.app[ONBOARDING_COMPLETED_KEY] = True
    config.save_config()


# --------------------------------------------------------------------------
# General settings (output folder, resolution, voice, concurrency)
# --------------------------------------------------------------------------


def get_general_settings() -> dict:
    return {
        "output_directory": config.app.get("output_directory", ""),
        "video_aspect": config.app.get("video_aspect", "9:16"),
        "voice_name": config.ui.get("voice_name", ""),
        "max_concurrent_tasks": config.app.get("max_concurrent_tasks", 5),
    }


def save_general_settings(payload: dict) -> None:
    if payload.get("output_directory") is not None:
        config.app["output_directory"] = payload["output_directory"]
    if payload.get("video_aspect") is not None:
        config.app["video_aspect"] = payload["video_aspect"]
    if payload.get("voice_name") is not None:
        config.ui["voice_name"] = payload["voice_name"]
    if payload.get("max_concurrent_tasks") is not None:
        config.app["max_concurrent_tasks"] = int(payload["max_concurrent_tasks"])
    config.save_config()


# --------------------------------------------------------------------------
# Brand settings: context text for the AI, logo overlay, and own materials.
# These are read by the desktop app's "Marca" settings section and applied
# per-video by the frontend when creating a video.
# --------------------------------------------------------------------------


# Roles the persuasive script chain can route to different providers. Kept in
# sync with app.services.script_studio.ALL_ROLES.
_PERSUASIVE_ROLES = ("research", "marketing", "copywriter", "qa")

# How much brand memory to keep so the QA step can avoid repetition without the
# config file growing unbounded.
_MAX_USED_PHRASES = 40
_MAX_PREFERRED_CTAS = 20


def get_brand_settings() -> dict:
    return {
        "brand_context": config.app.get("brand_context", ""),
        "logo_filename": config.app.get("logo_filename", ""),
        "logo_position": config.app.get("logo_position", "bottom-right"),
        "logo_size": int(config.app.get("logo_size", 12)),
        "use_own_materials": bool(config.app.get("use_own_materials", False)),
        "supplement_with_stock": bool(config.app.get("supplement_with_stock", False)),
        # Default to Colombian Spanish so scripts and voice stay local.
        "content_language": config.app.get("content_language", "Español (Colombia)"),
        # Persuasive multi-agent script chain. On by default: it is the whole
        # point of the "sell, don't just describe" workflow, and degrades to the
        # classic script automatically if it ever fails.
        "persuasive_mode": bool(config.app.get("persuasive_mode", True)),
        "target_audience": config.app.get("target_audience", ""),
        # Optional role -> provider overrides for multi-model routing. Empty means
        # every role uses the globally configured provider.
        "role_models": get_role_models(),
        # "Live" folder (Google Photos/Drive) the app re-syncs from before each
        # video, plus automatic image enhancement of the user's own footage.
        "materials_folder": get_materials_folder(),
        "enhance_media": bool(config.app.get("enhance_media", True)),
    }


def get_role_models() -> dict:
    stored = config.app.get("role_models", {})
    if not isinstance(stored, dict):
        return {}
    return {
        role: str(stored.get(role, "")).strip()
        for role in _PERSUASIVE_ROLES
        if str(stored.get(role, "")).strip()
    }


def save_brand_settings(payload: dict) -> None:
    if payload.get("brand_context") is not None:
        config.app["brand_context"] = str(payload["brand_context"])[:2000]
    if payload.get("logo_position") is not None:
        config.app["logo_position"] = str(payload["logo_position"])
    if payload.get("logo_size") is not None:
        config.app["logo_size"] = int(payload["logo_size"])
    if payload.get("use_own_materials") is not None:
        config.app["use_own_materials"] = bool(payload["use_own_materials"])
    if payload.get("supplement_with_stock") is not None:
        config.app["supplement_with_stock"] = bool(payload["supplement_with_stock"])
    if payload.get("content_language") is not None:
        config.app["content_language"] = str(payload["content_language"])[:64]
    if payload.get("persuasive_mode") is not None:
        config.app["persuasive_mode"] = bool(payload["persuasive_mode"])
    if payload.get("target_audience") is not None:
        config.app["target_audience"] = str(payload["target_audience"])[:500]
    if payload.get("enhance_media") is not None:
        config.app["enhance_media"] = bool(payload["enhance_media"])
    if payload.get("role_models") is not None and isinstance(payload["role_models"], dict):
        config.app["role_models"] = {
            role: str(payload["role_models"].get(role, "")).strip()
            for role in _PERSUASIVE_ROLES
            if str(payload["role_models"].get(role, "")).strip()
        }
    config.save_config()


# --------------------------------------------------------------------------
# Brand memory: phrases and CTAs already used, so the persuasive QA step can
# steer later videos away from repeating themselves.
# --------------------------------------------------------------------------


def get_brand_memory() -> dict:
    used_phrases = config.app.get("used_phrases", [])
    preferred_ctas = config.app.get("preferred_ctas", [])
    return {
        "used_phrases": (
            [str(p) for p in used_phrases if str(p).strip()]
            if isinstance(used_phrases, list)
            else []
        ),
        "preferred_ctas": (
            [str(c) for c in preferred_ctas if str(c).strip()]
            if isinstance(preferred_ctas, list)
            else []
        ),
    }


def record_used_content(hook: str = "", cta: str = "") -> None:
    """Append a video's hook/CTA to brand memory, most-recent-last, capped."""
    memory = get_brand_memory()
    phrases = memory["used_phrases"]
    ctas = memory["preferred_ctas"]

    hook = (hook or "").strip()
    cta = (cta or "").strip()
    if hook and hook not in phrases:
        phrases.append(hook)
    if cta and cta not in ctas:
        ctas.append(cta)

    config.app["used_phrases"] = phrases[-_MAX_USED_PHRASES:]
    config.app["preferred_ctas"] = ctas[-_MAX_PREFERRED_CTAS:]
    config.save_config()


# --------------------------------------------------------------------------
# Voice cloning (Fish Audio): the user records a short sample once and every
# AI narration is then spoken in their own voice.
# --------------------------------------------------------------------------


def get_voice_clone_settings() -> dict:
    key = config.app.get("fish_api_key", "")
    return {
        "fish_configured": bool(key),
        "fish_masked_key": f"…{key[-4:]}" if key else "",
        "cloned_voices": [v for v in config.app.get("cloned_voices", []) if isinstance(v, dict)],
        "current_voice": config.ui.get("voice_name", ""),
    }


def save_fish_api_key(api_key: str) -> None:
    config.app["fish_api_key"] = (api_key or "").strip()
    config.save_config()


def test_fish_connection(api_key: str) -> dict:
    """Validate a Fish Audio key with a lightweight authenticated request."""
    api_key = (api_key or "").strip()
    if not api_key:
        return {"ok": False, "message_es": "Escribe tu clave de Fish Audio."}
    try:
        response = requests.get(
            "https://api.fish.audio/model",
            headers={"Authorization": f"Bearer {api_key}"},
            params={"page_size": 1, "self": "true"},
            timeout=15,
        )
        if response.status_code == 200:
            return {"ok": True, "message_es": _CONNECTED_MESSAGE}
        if response.status_code in (401, 403):
            return {
                "ok": False,
                "message_es": "La clave de Fish Audio no es válida o no tiene permisos.",
            }
        return {
            "ok": False,
            "message_es": f"Fish Audio respondió con un error ({response.status_code}).",
        }
    except Exception as exc:
        message, _code = error_messages.translate_exception(exc, context="fish_test")
        return {"ok": False, "message_es": message}


def create_voice_clone(sample_path: str, title: str) -> dict:
    """Clone the user's voice from a sample and make it the default narration."""
    from app.services import voice

    if not config.app.get("fish_api_key", ""):
        return {
            "ok": False,
            "message_es": "Primero guarda tu clave de Fish Audio.",
        }
    title = (title or "Mi voz").strip()[:80]
    model_id = voice.create_fish_voice_clone(sample_path, title)
    if not model_id:
        return {
            "ok": False,
            "message_es": "No se pudo crear tu voz. Revisa el audio (10-30s, voz clara) y tu clave.",
        }

    voice_name = f"fish:{model_id}:{title}"
    cloned = [v for v in config.app.get("cloned_voices", []) if isinstance(v, dict)]
    cloned = [v for v in cloned if v.get("id") != model_id]
    cloned.append({"id": model_id, "title": title, "voice_name": voice_name})
    config.app["cloned_voices"] = cloned[-10:]
    # Make the freshly cloned voice the default for new videos.
    config.ui["voice_name"] = voice_name
    config.save_config()
    return {
        "ok": True,
        "voice_name": voice_name,
        "message_es": f"¡Listo! Tu voz «{title}» quedó guardada y seleccionada.",
    }


# --------------------------------------------------------------------------
# Local voice cloning via MimikaStudio (offline, free). Requires the separate
# MimikaStudio app to be running; the app talks to its local FastAPI server.
# --------------------------------------------------------------------------

# Engines that support voice cloning and multilingual (Spanish + English) output.
_MIMIKA_CLONE_ENGINES = ("chatterbox", "qwen3")


def get_mimika_status() -> dict:
    """Report whether MimikaStudio is running locally and which clone-capable
    engines have a model downloaded, so the UI can guide the user."""
    from app.services import voice

    base = voice.get_mimika_base_url()
    try:
        health = requests.get(f"{base}/api/health", timeout=4)
        if health.status_code != 200:
            return {"reachable": False, "engines": [], "base_url": base}
    except Exception:
        return {"reachable": False, "engines": [], "base_url": base}

    engines = []
    try:
        status = requests.get(f"{base}/api/models/status", timeout=8)
        models = status.json().get("models", []) if status.status_code == 200 else []
        ready = {
            m.get("engine")
            for m in models
            if m.get("downloaded") and m.get("mode") in ("clone", "custom")
        }
        engines = [e for e in _MIMIKA_CLONE_ENGINES if e in ready]
    except Exception:
        engines = []
    return {"reachable": True, "engines": engines, "base_url": base}


def create_mimika_clone(sample_path: str, name: str, engine: str = "chatterbox") -> dict:
    """Clone the user's voice locally with MimikaStudio and make it the default."""
    from app.services import voice

    name = (name or "Mi voz").strip()[:80]
    if engine not in _MIMIKA_CLONE_ENGINES:
        engine = "chatterbox"

    status = get_mimika_status()
    if not status["reachable"]:
        return {
            "ok": False,
            "message_es": "MimikaStudio no está abierto. Ábrelo y espera a que cargue.",
        }

    stored = voice.create_mimika_voice_clone(sample_path, name, engine=engine)
    if not stored:
        return {
            "ok": False,
            "message_es": "No se pudo crear tu voz local. Revisa el audio (10-30s, voz clara).",
        }

    voice_name = f"mimika:{engine}:{stored}"
    cloned = [v for v in config.app.get("cloned_voices", []) if isinstance(v, dict)]
    cloned = [v for v in cloned if v.get("voice_name") != voice_name]
    cloned.append({"id": stored, "title": stored, "voice_name": voice_name})
    config.app["cloned_voices"] = cloned[-10:]
    config.ui["voice_name"] = voice_name
    config.save_config()
    return {
        "ok": True,
        "voice_name": voice_name,
        "message_es": f"¡Listo! Tu voz local «{stored}» quedó guardada y seleccionada.",
    }


def set_logo_filename(filename: str) -> None:
    config.app["logo_filename"] = filename
    config.save_config()


def clear_logo() -> None:
    config.app["logo_filename"] = ""
    config.save_config()


# Media types worth importing from a user's folder (e.g. a synced Google
# Drive folder). Kept in sync with the upload endpoints in system.py.
_IMPORT_MEDIA_EXTS = (
    ".mp4",
    ".mov",
    ".avi",
    ".mkv",
    ".webm",
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
)
# Safety cap: a synced-cloud folder can be enormous, so never copy more than
# this in one import (a video is built from a handful of clips anyway).
_MAX_IMPORT_FILES = 300


def get_materials_folder() -> str:
    """The user's designated "live" folder (e.g. a Google Photos/Drive folder)
    that the app re-syncs from before every video, or "" if none is set."""
    return config.app.get("materials_folder", "")


def sync_materials_folder() -> dict:
    """Re-import from the remembered folder so newly added photos/videos are
    picked up. No-op (ok) when the user never designated a folder."""
    folder = get_materials_folder()
    if not folder:
        return {"ok": True, "imported": 0, "message_es": "No hay carpeta configurada."}
    return import_materials_from_folder(folder)


def import_materials_from_folder(folder: str) -> dict:
    """Copy images/videos from a user-picked folder into the app's own
    materials directory, so a whole Google Drive/Dropbox folder of the
    business's real footage can be reused with one click.

    Copies (rather than references) so videos still build if the cloud
    folder later goes offline, and so the existing local-materials pipeline
    keeps working unchanged. On success the folder path is remembered so the
    app can re-sync from it automatically before each new video.
    """
    if not folder or not os.path.isdir(folder):
        return {"ok": False, "imported": 0, "message_es": "No se encontró la carpeta seleccionada."}

    # Remember the folder so the app can re-sync from it before each new video.
    config.app["materials_folder"] = folder
    config.save_config()

    destination = utils.storage_dir("local_videos", create=True)
    real_destination = os.path.realpath(destination)
    imported = 0
    skipped = 0

    for root, _dirs, files in os.walk(folder):
        # Don't re-import the app's own materials directory if it happens to
        # be inside the chosen folder.
        if os.path.realpath(root) == real_destination:
            continue
        for name in files:
            if imported >= _MAX_IMPORT_FILES:
                break
            if not name.lower().endswith(_IMPORT_MEDIA_EXTS):
                continue
            source = os.path.join(root, name)
            target = os.path.join(destination, os.path.basename(name))
            try:
                if os.path.exists(target) and os.path.getsize(target) == os.path.getsize(source):
                    skipped += 1
                    continue
                shutil.copy2(source, target)
                imported += 1
            except OSError:
                skipped += 1
        if imported >= _MAX_IMPORT_FILES:
            break

    if imported == 0 and skipped == 0:
        return {
            "ok": True,
            "imported": 0,
            "message_es": "No se encontraron fotos ni vídeos en esa carpeta.",
        }
    message = f"Se importaron {imported} archivo(s)."
    if skipped:
        message += f" ({skipped} ya estaban o no se pudieron copiar.)"
    if imported >= _MAX_IMPORT_FILES:
        message += f" Se alcanzó el máximo de {_MAX_IMPORT_FILES}."
    return {"ok": True, "imported": imported, "skipped": skipped, "message_es": message}


# --------------------------------------------------------------------------
# LLM provider: connection test + persistence
# --------------------------------------------------------------------------


def _result_from_llm_response(response: Optional[str], context: str) -> dict:
    if not response:
        return {
            "ok": False,
            "message_es": "El proveedor no devolvió ninguna respuesta. Inténtalo de nuevo.",
        }
    if response.startswith("Error: "):
        message, _code = error_messages.translate_message(
            response[len("Error: ") :], context=context
        )
        return {"ok": False, "message_es": message}
    return {"ok": True, "message_es": _CONNECTED_MESSAGE}


def _test_ollama_connection() -> dict:
    base_url = config.app.get("ollama_base_url") or config.get_default_ollama_base_url()
    tags_url = base_url.rstrip("/")
    if tags_url.endswith("/v1"):
        tags_url = tags_url[: -len("/v1")]
    try:
        response = requests.get(f"{tags_url}/api/tags", timeout=3)
        response.raise_for_status()
        return {"ok": True, "message_es": _CONNECTED_MESSAGE}
    except Exception as exc:
        message, _code = error_messages.translate_exception(exc, context="llm_test:ollama")
        return {"ok": False, "message_es": message}


def _test_llm_via_litellm(api_key: str, model_name: str, env_var: str, context: str) -> dict:
    previous_env = os.environ.get(env_var)
    previous_provider = config.app.get("llm_provider")
    previous_model = config.app.get("litellm_model_name")
    try:
        os.environ[env_var] = api_key
        config.app["llm_provider"] = "litellm"
        config.app["litellm_model_name"] = model_name
        response = llm._generate_response(_TEST_PROMPT)
    finally:
        if previous_env is None:
            os.environ.pop(env_var, None)
        else:
            os.environ[env_var] = previous_env
        config.app["llm_provider"] = previous_provider
        config.app["litellm_model_name"] = previous_model

    return _result_from_llm_response(response, context=context)


def test_llm_connection(
    provider: str,
    api_key: str,
    model_name: Optional[str] = None,
    base_url: Optional[str] = None,
) -> dict:
    """Try a candidate LLM configuration without persisting it.

    Applies the candidate values to `config.app` only for the duration of a
    single trivial request, then restores whatever was there before —
    saving to disk is a separate, explicit step (`save_llm_provider`) that
    only happens once the user has seen a successful test.
    """
    provider = (provider or "").strip().lower()

    if provider == "ollama":
        return _test_ollama_connection()

    if provider == "claude":
        return _test_llm_via_litellm(
            api_key, model_name or _CLAUDE_LITELLM_MODEL, _CLAUDE_ENV_VAR, "llm_test:claude"
        )

    field_map = _LLM_PROVIDER_FIELDS.get(provider)
    if not field_map:
        return {"ok": False, "message_es": f"Proveedor de IA no soportado: {provider}"}

    api_key_field = field_map["api_key"]
    model_field = field_map["model"]
    base_url_field = field_map.get("base_url")
    previous_api_key = config.app.get(api_key_field)
    previous_provider = config.app.get("llm_provider")
    previous_model = config.app.get(model_field)
    previous_base_url = config.app.get(base_url_field) if base_url_field else None
    try:
        config.app[api_key_field] = api_key
        config.app["llm_provider"] = provider
        if model_name:
            config.app[model_field] = model_name
        if base_url_field and base_url:
            config.app[base_url_field] = base_url
        response = llm._generate_response(_TEST_PROMPT)
    finally:
        config.app[api_key_field] = previous_api_key
        config.app["llm_provider"] = previous_provider
        config.app[model_field] = previous_model
        if base_url_field:
            config.app[base_url_field] = previous_base_url

    return _result_from_llm_response(response, context=f"llm_test:{provider}")


def save_llm_provider(
    provider: str,
    api_key: str,
    model_name: Optional[str] = None,
    base_url: Optional[str] = None,
) -> None:
    """Persist a working LLM provider configuration to config.toml."""
    provider = (provider or "").strip().lower()

    if provider == "claude":
        config.app["llm_provider"] = "litellm"
        config.app["litellm_model_name"] = model_name or _CLAUDE_LITELLM_MODEL
        # LiteLLM only reads the key from the environment; config.toml keeps
        # a copy purely so the desktop UI can show "already configured".
        config.app["anthropic_api_key"] = api_key
        os.environ[_CLAUDE_ENV_VAR] = api_key
    elif provider == "ollama":
        config.app["llm_provider"] = "ollama"
        if model_name:
            config.app["ollama_model_name"] = model_name
    else:
        field_map = _LLM_PROVIDER_FIELDS.get(provider)
        if not field_map:
            raise ValueError(f"unsupported llm provider: {provider}")
        config.app["llm_provider"] = provider
        config.app[field_map["api_key"]] = api_key
        if model_name:
            config.app[field_map["model"]] = model_name
        if field_map.get("base_url") and base_url:
            config.app[field_map["base_url"]] = base_url

    config.save_config()


def get_llm_settings() -> dict:
    """Return the active provider and a masked view of its API key."""
    provider = config.app.get("llm_provider", "")
    masked_key = ""
    if provider == "litellm" and "anthropic" in (config.app.get("litellm_model_name") or ""):
        provider = "claude"
        masked_key = _mask_key(config.app.get("anthropic_api_key", ""))
    elif provider in _LLM_PROVIDER_FIELDS:
        masked_key = _mask_key(config.app.get(_LLM_PROVIDER_FIELDS[provider]["api_key"], ""))
    return {"provider": provider, "masked_api_key": masked_key}


def _mask_key(key: str) -> str:
    key = key or ""
    if len(key) <= 4:
        return "*" * len(key)
    return f"{'*' * (len(key) - 4)}{key[-4:]}"


# --------------------------------------------------------------------------
# Material (stock video) provider: connection test + persistence
# --------------------------------------------------------------------------


def test_material_provider(provider: str, api_key: str) -> dict:
    provider = (provider or "").strip().lower()
    if provider not in _MATERIAL_PROVIDER_CONFIG_KEYS:
        return {"ok": False, "message_es": f"Proveedor de vídeos no soportado: {provider}"}

    try:
        verify = material.get_tls_verify()
        if provider == "pexels":
            response = requests.get(
                "https://api.pexels.com/videos/search",
                headers={"Authorization": api_key},
                params={"query": "nature", "per_page": 1},
                timeout=5,
                verify=verify,
            )
        elif provider == "pixabay":
            response = requests.get(
                "https://pixabay.com/api/videos/",
                params={"key": api_key, "q": "nature", "per_page": 3},
                timeout=5,
                verify=verify,
            )
        else:  # coverr
            response = requests.get(
                "https://api.coverr.co/videos",
                headers={"Authorization": f"Bearer {api_key}"},
                params={"query": "nature", "page_size": 1},
                timeout=5,
                verify=verify,
            )

        if response.status_code in (401, 403):
            return {
                "ok": False,
                "message_es": (
                    "La clave de API no es válida o no tiene permisos. "
                    "Revisa que la copiaste completa."
                ),
            }
        response.raise_for_status()
        return {"ok": True, "message_es": _CONNECTED_MESSAGE}
    except Exception as exc:
        message, _code = error_messages.translate_exception(
            exc, context=f"material_test:{provider}"
        )
        return {"ok": False, "message_es": message}


def save_material_provider(provider: str, api_key: str) -> None:
    provider = (provider or "").strip().lower()
    cfg_key = _MATERIAL_PROVIDER_CONFIG_KEYS.get(provider)
    if not cfg_key:
        raise ValueError(f"unsupported material provider: {provider}")
    config.app[cfg_key] = [api_key]
    config.save_config()


def get_material_settings() -> dict:
    """Report which stock-video providers already have a key saved (no key values)."""
    return {
        provider: bool(config.app.get(cfg_key))
        for provider, cfg_key in _MATERIAL_PROVIDER_CONFIG_KEYS.items()
    }


# --------------------------------------------------------------------------
# System diagnostics
# --------------------------------------------------------------------------


def _check_ffmpeg() -> dict:
    ffmpeg_bin = utils.get_ffmpeg_binary()
    try:
        subprocess.run([ffmpeg_bin, "-version"], timeout=5, capture_output=True, check=True)
        return {"name": "ffmpeg", "ok": True, "message_es": "FFmpeg funciona correctamente."}
    except Exception:
        return {
            "name": "ffmpeg",
            "ok": False,
            "message_es": "No se encontró FFmpeg, un componente necesario para crear vídeos.",
            "fix_hint_es": "Intenta reinstalar la aplicación; este componente debería venir incluido.",
        }


def _check_disk_space(min_free_gb: float = 1.0) -> dict:
    output_dir = config.app.get("output_directory") or utils.storage_dir()
    try:
        usage = shutil.disk_usage(output_dir if os.path.isdir(output_dir) else utils.storage_dir())
        free_gb = usage.free / (1024**3)
        if free_gb < min_free_gb:
            return {
                "name": "disk_space",
                "ok": False,
                "message_es": f"Queda muy poco espacio libre en el disco ({free_gb:.1f} GB).",
                "fix_hint_es": "Libera espacio en tu computadora antes de generar más vídeos.",
            }
        return {
            "name": "disk_space",
            "ok": True,
            "message_es": f"Espacio en disco suficiente ({free_gb:.1f} GB libres).",
        }
    except OSError as exc:
        message, _code = error_messages.translate_exception(exc, context="diagnostics:disk_space")
        return {"name": "disk_space", "ok": False, "message_es": message}


def _check_internet() -> dict:
    try:
        socket.create_connection(("1.1.1.1", 443), timeout=3).close()
        return {"name": "internet", "ok": True, "message_es": "Conexión a internet detectada."}
    except OSError:
        return {
            "name": "internet",
            "ok": False,
            "message_es": "No se detecta conexión a internet.",
            "fix_hint_es": "Revisa tu red Wi-Fi o cable de red e inténtalo de nuevo.",
        }


def _check_output_folder_writable() -> dict:
    output_dir = config.app.get("output_directory") or utils.storage_dir()
    try:
        os.makedirs(output_dir, exist_ok=True)
        probe_path = os.path.join(output_dir, ".mpt_write_test")
        with open(probe_path, "w", encoding="utf-8") as probe_file:
            probe_file.write("ok")
        os.remove(probe_path)
        return {
            "name": "output_folder",
            "ok": True,
            "message_es": "La carpeta de salida se puede usar sin problemas.",
        }
    except OSError as exc:
        message, _code = error_messages.translate_exception(
            exc, context="diagnostics:output_folder"
        )
        return {
            "name": "output_folder",
            "ok": False,
            "message_es": message,
            "fix_hint_es": "Elige otra carpeta de salida en Configuración.",
        }


def _check_llm_configured() -> dict:
    provider = config.app.get("llm_provider", "")
    field_map = _LLM_PROVIDER_FIELDS.get(provider)
    configured = bool(provider == "ollama") or bool(
        field_map and config.app.get(field_map["api_key"])
    )
    if provider == "litellm":
        configured = bool(config.app.get("anthropic_api_key")) or bool(
            os.environ.get(_CLAUDE_ENV_VAR)
        )
    if not configured:
        return {
            "name": "llm_provider",
            "ok": False,
            "message_es": "Todavía no configuraste ningún proveedor de IA.",
            "fix_hint_es": "Completa el asistente de configuración inicial.",
        }
    return {"name": "llm_provider", "ok": True, "message_es": "Proveedor de IA configurado."}


def run_diagnostics() -> list[dict]:
    return [
        _check_ffmpeg(),
        _check_disk_space(),
        _check_internet(),
        _check_output_folder_writable(),
        _check_llm_configured(),
    ]
