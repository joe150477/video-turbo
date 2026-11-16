"""Endpoints behind the desktop app's onboarding wizard and settings screens.

These are the only backend surface the new React/Electron frontend needs
beyond the existing `/videos`, `/scripts`, etc. endpoints: connection tests,
a friendly voice catalog, general settings, and system diagnostics — so a
non-technical user never has to open `config.toml`.
"""

import base64
import os
import uuid

from fastapi import File, Request, UploadFile

from app.controllers.v1.base import new_router
from app.models.exception import HttpException
from app.models.schema import (
    BrandSettingsRequest,
    FishKeyRequest,
    GeneralSettingsRequest,
    ImportFolderRequest,
    LlmProviderSaveRequest,
    LlmProviderTestRequest,
    MaterialProviderSaveRequest,
    MaterialProviderTestRequest,
    VoicePreviewRequest,
)
from app.services import branding, setup, updates, voice, voice_catalog
from app.utils import utils

_LOGO_EXTS = (".png", ".jpg", ".jpeg", ".webp")
_MATERIAL_EXTS = (".mp4", ".mov", ".avi", ".mkv", ".jpg", ".jpeg", ".png", ".webp")


def _safe_upload_name(filename: str | None) -> str:
    # Keep only the base name and strip any path separators so an upload can
    # never escape its target directory.
    return os.path.basename((filename or "").replace("\\", "/")).strip()


router = new_router()


@router.get("/system/ping", summary="Trivial liveness check for the desktop shell")
def ping(request: Request):
    return utils.get_response(200, {"ok": True})


@router.get("/system/onboarding/status", summary="Whether the first-run wizard is needed")
def onboarding_status(request: Request):
    return utils.get_response(200, {"completed": not setup.is_first_run()})


@router.post("/system/onboarding/complete", summary="Mark the first-run wizard as done")
def complete_onboarding(request: Request):
    setup.mark_onboarding_completed()
    return utils.get_response(200, {"completed": True})


@router.post("/system/settings/llm/test", summary="Try an LLM provider without saving it")
def test_llm_provider(request: Request, body: LlmProviderTestRequest):
    result = setup.test_llm_connection(
        provider=body.provider.value,
        api_key=body.api_key,
        model_name=body.model_name,
        base_url=body.base_url,
    )
    return utils.get_response(200, result)


@router.post("/system/settings/llm", summary="Save a working LLM provider configuration")
def save_llm_provider(request: Request, body: LlmProviderSaveRequest):
    setup.save_llm_provider(
        provider=body.provider.value,
        api_key=body.api_key,
        model_name=body.model_name,
        base_url=body.base_url,
    )
    return utils.get_response(200, {"saved": True})


@router.get("/system/settings/llm", summary="Current LLM provider (API key masked)")
def get_llm_provider(request: Request):
    return utils.get_response(200, setup.get_llm_settings())


@router.post(
    "/system/settings/material/test", summary="Try a stock-video provider without saving it"
)
def test_material_provider(request: Request, body: MaterialProviderTestRequest):
    result = setup.test_material_provider(provider=body.provider.value, api_key=body.api_key)
    return utils.get_response(200, result)


@router.post("/system/settings/material", summary="Save a working stock-video provider key")
def save_material_provider(request: Request, body: MaterialProviderSaveRequest):
    setup.save_material_provider(provider=body.provider.value, api_key=body.api_key)
    return utils.get_response(200, {"saved": True})


@router.get("/system/settings/material", summary="Which stock-video providers have a saved key")
def get_material_providers(request: Request):
    return utils.get_response(200, setup.get_material_settings())


@router.get("/system/settings/general", summary="Output folder, resolution, voice, concurrency")
def get_general_settings(request: Request):
    return utils.get_response(200, setup.get_general_settings())


@router.post("/system/settings/general", summary="Save general settings")
def save_general_settings(request: Request, body: GeneralSettingsRequest):
    payload = {
        "output_directory": body.output_directory,
        "video_aspect": body.video_aspect.value if body.video_aspect else None,
        "voice_name": body.voice_name,
        "max_concurrent_tasks": body.max_concurrent_tasks,
    }
    setup.save_general_settings(payload)
    return utils.get_response(200, {"saved": True})


@router.get("/system/voices", summary="Friendly, grouped voice catalog")
def get_voices(request: Request):
    groups = voice_catalog.get_friendly_voice_catalog()
    data = {
        "groups": [
            {
                "language_label_es": group.language_label_es,
                "voices": [
                    {
                        "id": friendly_voice.id,
                        "label_es": friendly_voice.label_es,
                        "gender": friendly_voice.gender,
                        "provider": friendly_voice.provider,
                    }
                    for friendly_voice in group.voices
                ],
            }
            for group in groups
        ]
    }
    return utils.get_response(200, data)


@router.post("/system/voices/preview", summary="Synthesize a short sample of a voice")
def preview_voice(request: Request, body: VoicePreviewRequest):
    sample_text = voice_catalog.sample_text_for_voice(body.voice_id)
    temp_dir = utils.storage_dir("temp", create=True)
    audio_file = os.path.join(temp_dir, f"voice-preview-{uuid.uuid4().hex}.mp3")
    try:
        sub_maker = voice.tts(
            text=sample_text, voice_name=body.voice_id, voice_rate=1.0, voice_file=audio_file
        )
        if not sub_maker or not os.path.exists(audio_file):
            return utils.get_response(
                200,
                {"ok": False, "message_es": "No se pudo generar el audio de ejemplo."},
            )
        with open(audio_file, "rb") as f:
            audio_bytes = f.read()
        return utils.get_response(
            200,
            {
                "ok": True,
                "audio_base64": base64.b64encode(audio_bytes).decode("ascii"),
                "mime_type": "audio/mpeg",
            },
        )
    finally:
        if os.path.exists(audio_file):
            os.remove(audio_file)


@router.get("/system/diagnostics", summary="Run the pre-flight system diagnostics")
def diagnostics(request: Request):
    checks = setup.run_diagnostics()
    return utils.get_response(200, {"checks": checks, "all_ok": all(c["ok"] for c in checks)})


@router.get("/system/settings/brand", summary="Brand context, logo, own-materials settings")
def get_brand_settings(request: Request):
    return utils.get_response(200, setup.get_brand_settings())


@router.post("/system/settings/brand", summary="Save brand settings")
def save_brand_settings(request: Request, body: BrandSettingsRequest):
    setup.save_brand_settings(
        {
            "brand_context": body.brand_context,
            "logo_position": body.logo_position,
            "logo_size": body.logo_size,
            "use_own_materials": body.use_own_materials,
            "supplement_with_stock": body.supplement_with_stock,
            "content_language": body.content_language,
            "persuasive_mode": body.persuasive_mode,
            "target_audience": body.target_audience,
            "role_models": body.role_models,
            "enhance_media": body.enhance_media,
        }
    )
    return utils.get_response(200, {"saved": True})


@router.post("/system/settings/brand/logo", summary="Upload a brand logo image")
def upload_brand_logo(request: Request, file: UploadFile = File(...)):
    name = _safe_upload_name(file.filename)
    if not name or not name.lower().endswith(_LOGO_EXTS):
        raise HttpException(
            "", status_code=400, message="Solo se permiten imágenes PNG, JPG o WEBP."
        )
    # Normalise to a single stored filename so a new logo replaces the old one.
    stored_name = f"logo{os.path.splitext(name)[1].lower()}"
    for existing in os.listdir(branding.logo_dir()):
        try:
            os.remove(os.path.join(branding.logo_dir(), existing))
        except OSError:
            pass
    save_path = os.path.join(branding.logo_dir(), stored_name)
    with open(save_path, "wb+") as buffer:
        file.file.seek(0)
        buffer.write(file.file.read())
    setup.set_logo_filename(stored_name)
    return utils.get_response(200, {"logo_filename": stored_name})


_VOICE_SAMPLE_EXTS = (".mp3", ".wav", ".m4a", ".ogg", ".webm", ".flac")


@router.get("/system/settings/voice-clone", summary="Voice cloning status (Fish Audio)")
def get_voice_clone(request: Request):
    return utils.get_response(200, setup.get_voice_clone_settings())


@router.post("/system/settings/voice-clone/test", summary="Test the Fish Audio key")
def test_fish_key(request: Request, body: FishKeyRequest):
    return utils.get_response(200, setup.test_fish_connection(body.api_key))


@router.post("/system/settings/voice-clone/key", summary="Save the Fish Audio key")
def save_fish_key(request: Request, body: FishKeyRequest):
    result = setup.test_fish_connection(body.api_key)
    if result.get("ok"):
        setup.save_fish_api_key(body.api_key)
    return utils.get_response(200, result)


@router.post("/system/voices/clone", summary="Clone the user's voice from a sample")
def clone_voice(request: Request, file: UploadFile = File(...), title: str = "Mi voz"):
    name = _safe_upload_name(file.filename)
    if not name or not name.lower().endswith(_VOICE_SAMPLE_EXTS):
        raise HttpException(
            "", status_code=400, message="Sube un audio (MP3, WAV, M4A, OGG o FLAC)."
        )
    temp_dir = utils.storage_dir("temp", create=True)
    sample_path = os.path.join(
        temp_dir, f"voice-sample-{uuid.uuid4().hex}{os.path.splitext(name)[1].lower()}"
    )
    with open(sample_path, "wb+") as buffer:
        file.file.seek(0)
        buffer.write(file.file.read())
    try:
        result = setup.create_voice_clone(sample_path, title)
    finally:
        if os.path.exists(sample_path):
            os.remove(sample_path)
    return utils.get_response(200, result)


@router.get("/system/voices/mimika-status", summary="Is MimikaStudio (local) running?")
def mimika_status(request: Request):
    return utils.get_response(200, setup.get_mimika_status())


@router.post("/system/voices/clone-local", summary="Clone the user's voice locally (MimikaStudio)")
def clone_voice_local(
    request: Request,
    file: UploadFile = File(...),
    name: str = "Mi voz",
    engine: str = "chatterbox",
):
    filename = _safe_upload_name(file.filename)
    if not filename or not filename.lower().endswith(_VOICE_SAMPLE_EXTS):
        raise HttpException(
            "", status_code=400, message="Sube un audio (MP3, WAV, M4A, OGG o FLAC)."
        )
    temp_dir = utils.storage_dir("temp", create=True)
    sample_path = os.path.join(
        temp_dir, f"voice-sample-{uuid.uuid4().hex}{os.path.splitext(filename)[1].lower()}"
    )
    with open(sample_path, "wb+") as buffer:
        file.file.seek(0)
        buffer.write(file.file.read())
    try:
        result = setup.create_mimika_clone(sample_path, name, engine)
    finally:
        if os.path.exists(sample_path):
            os.remove(sample_path)
    return utils.get_response(200, result)


@router.delete("/system/settings/brand/logo", summary="Remove the brand logo")
def delete_brand_logo(request: Request):
    for existing in os.listdir(branding.logo_dir()):
        try:
            os.remove(os.path.join(branding.logo_dir(), existing))
        except OSError:
            pass
    setup.clear_logo()
    return utils.get_response(200, {"removed": True})


@router.get("/system/materials", summary="List the user's own uploaded materials")
def list_materials(request: Request):
    materials_dir = utils.storage_dir("local_videos", create=True)
    files = sorted(
        f
        for f in os.listdir(materials_dir)
        if f.lower().endswith(_MATERIAL_EXTS) and os.path.isfile(os.path.join(materials_dir, f))
    )
    return utils.get_response(200, {"materials": files})


@router.post("/system/materials", summary="Upload one of the user's own materials")
def upload_material(request: Request, file: UploadFile = File(...)):
    name = _safe_upload_name(file.filename)
    if not name or not name.lower().endswith(_MATERIAL_EXTS):
        raise HttpException(
            "",
            status_code=400,
            message="Formato no admitido. Usa vídeo (mp4/mov) o imagen (jpg/png).",
        )
    materials_dir = utils.storage_dir("local_videos", create=True)
    with open(os.path.join(materials_dir, name), "wb+") as buffer:
        file.file.seek(0)
        buffer.write(file.file.read())
    return utils.get_response(200, {"file": name})


@router.post("/system/materials/import-folder", summary="Import all media from a folder")
def import_materials_folder(request: Request, body: ImportFolderRequest):
    return utils.get_response(200, setup.import_materials_from_folder(body.folder))


@router.post("/system/materials/sync-folder", summary="Re-sync from the remembered folder")
def sync_materials_folder(request: Request):
    return utils.get_response(200, setup.sync_materials_folder())


@router.delete("/system/materials/{filename}", summary="Delete one of the user's materials")
def delete_material(request: Request, filename: str):
    name = _safe_upload_name(filename)
    target = os.path.join(utils.storage_dir("local_videos", create=True), name)
    if name and os.path.isfile(target):
        os.remove(target)
    return utils.get_response(200, {"removed": True})


@router.get("/system/updates/check", summary="Check for an upstream project update")
def check_updates(request: Request):
    return utils.get_response(200, updates.check_for_updates())


@router.post("/system/updates/apply", summary="Apply the upstream update (with auto-rollback)")
def apply_update(request: Request):
    return utils.get_response(200, updates.apply_update())
