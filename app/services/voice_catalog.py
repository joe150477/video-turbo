"""Curated, non-technical voice catalog for the desktop onboarding wizard.

`app.services.voice` already exposes every TTS voice by its raw technical
name (e.g. "es-MX-DaliaNeural-Female", "gemini:Zephyr-Female"). Those names
mean nothing to a non-technical user, so this module maps them to short
Spanish labels grouped by language/provider, with Spanish and English
surfaced first. The `id` of a `FriendlyVoice` is the same technical name the
rest of the app already uses as `voice_name` — no separate lookup table is
needed, the frontend just never has to display it.
"""

from dataclasses import dataclass, field

from app.config import config
from app.services import voice

_SPANISH_COUNTRY_NAMES_ES = {
    "AR": "Argentina",
    "BO": "Bolivia",
    "CL": "Chile",
    "CO": "Colombia",
    "CR": "Costa Rica",
    "CU": "Cuba",
    "DO": "Rep. Dominicana",
    "EC": "Ecuador",
    "ES": "España",
    "GQ": "Guinea Ecuatorial",
    "GT": "Guatemala",
    "HN": "Honduras",
    "MX": "México",
    "NI": "Nicaragua",
    "PA": "Panamá",
    "PE": "Perú",
    "PR": "Puerto Rico",
    "PY": "Paraguay",
    "SV": "El Salvador",
    "US": "Estados Unidos",
    "UY": "Uruguay",
    "VE": "Venezuela",
}

_ENGLISH_COUNTRY_NAMES_ES = {
    "US": "EE. UU.",
    "GB": "Reino Unido",
    "AU": "Australia",
    "CA": "Canadá",
    "IN": "India",
    "IE": "Irlanda",
    "NZ": "Nueva Zelanda",
    "ZA": "Sudáfrica",
}

_LANGUAGE_NAMES_ES = {
    "af": "Afrikáans",
    "am": "Amárico",
    "ar": "Árabe",
    "az": "Azerí",
    "bg": "Búlgaro",
    "bn": "Bengalí",
    "bs": "Bosnio",
    "ca": "Catalán",
    "cs": "Checo",
    "cy": "Galés",
    "da": "Danés",
    "de": "Alemán",
    "el": "Griego",
    "et": "Estonio",
    "fa": "Persa",
    "fi": "Finlandés",
    "fil": "Filipino",
    "fr": "Francés",
    "ga": "Irlandés",
    "gl": "Gallego",
    "gu": "Guyaratí",
    "he": "Hebreo",
    "hi": "Hindi",
    "hr": "Croata",
    "hu": "Húngaro",
    "id": "Indonesio",
    "is": "Islandés",
    "it": "Italiano",
    "iu": "Inuktitut",
    "ja": "Japonés",
    "jv": "Javanés",
    "ka": "Georgiano",
    "kk": "Kazajo",
    "km": "Jemer",
    "kn": "Canarés",
    "ko": "Coreano",
    "lo": "Lao",
    "lt": "Lituano",
    "lv": "Letón",
    "mk": "Macedonio",
    "ml": "Malayalam",
    "mn": "Mongol",
    "mr": "Maratí",
    "ms": "Malayo",
    "mt": "Maltés",
    "my": "Birmano",
    "nb": "Noruego",
    "ne": "Nepalí",
    "nl": "Neerlandés",
    "pl": "Polaco",
    "ps": "Pastú",
    "pt": "Portugués",
    "ro": "Rumano",
    "ru": "Ruso",
    "si": "Cingalés",
    "sk": "Eslovaco",
    "sl": "Esloveno",
    "so": "Somalí",
    "sq": "Albanés",
    "sr": "Serbio",
    "su": "Sundanés",
    "sv": "Sueco",
    "sw": "Suajili",
    "ta": "Tamil",
    "te": "Telugu",
    "th": "Tailandés",
    "tr": "Turco",
    "uk": "Ucraniano",
    "ur": "Urdu",
    "uz": "Uzbeko",
    "vi": "Vietnamita",
    "zh": "Chino",
    "zu": "Zulú",
}

_GENDER_LABELS_ES = {"Female": "Mujer", "Male": "Hombre"}

_SAMPLE_TEXTS_BY_LANGUAGE = {
    "es": "Hola, esta es una voz de ejemplo para tu vídeo.",
    "en": "Hello, this is a sample voice for your video.",
    "pt": "Olá, esta é uma voz de exemplo para o seu vídeo.",
    "fr": "Bonjour, ceci est un exemple de voix pour votre vidéo.",
    "de": "Hallo, dies ist eine Beispielstimme für dein Video.",
}
_DEFAULT_SAMPLE_TEXT = _SAMPLE_TEXTS_BY_LANGUAGE["es"]


@dataclass
class FriendlyVoice:
    id: str
    label_es: str
    gender: str
    provider: str = "edge"


@dataclass
class VoiceGroup:
    language_label_es: str
    voices: list[FriendlyVoice] = field(default_factory=list)


def _parse_edge_voice(raw_name: str) -> FriendlyVoice | None:
    # raw_name looks like "es-MX-DaliaNeural-Female" or
    # "zh-CN-XiaoxiaoMultilingualNeural-V2-Female".
    if not raw_name.endswith(("-Female", "-Male")):
        return None

    gender = "Female" if raw_name.endswith("-Female") else "Male"
    body = raw_name[: -len(f"-{gender}")]
    parts = body.split("-")
    if len(parts) < 2:
        return None

    lang_code, country_code = parts[0].lower(), parts[1].upper()
    gender_es = _GENDER_LABELS_ES.get(gender, gender)

    if lang_code == "es":
        place = _SPANISH_COUNTRY_NAMES_ES.get(country_code, country_code)
        label = f"Español ({place}) — {gender_es}"
    elif lang_code == "en":
        place = _ENGLISH_COUNTRY_NAMES_ES.get(country_code, country_code)
        label = f"Inglés ({place}) — {gender_es}"
    else:
        language_es = _LANGUAGE_NAMES_ES.get(lang_code, lang_code.upper())
        label = f"{language_es} ({country_code}) — {gender_es}"

    return FriendlyVoice(id=raw_name, label_es=label, gender=gender, provider="edge")


def _edge_voice_groups() -> list[VoiceGroup]:
    spanish, english, other = [], [], []
    for raw_name in voice.get_all_azure_voices():
        parsed = _parse_edge_voice(raw_name)
        if parsed is None:
            continue
        lang_code = raw_name.split("-")[0].lower()
        if lang_code == "es":
            spanish.append(parsed)
        elif lang_code == "en":
            english.append(parsed)
        else:
            other.append(parsed)

    groups = []
    if spanish:
        groups.append(VoiceGroup("Español", spanish))
    if english:
        groups.append(VoiceGroup("Inglés", english))
    if other:
        other.sort(key=lambda v: v.label_es)
        groups.append(VoiceGroup("Otros idiomas", other))
    return groups


def _split_provider_voice(raw: str, prefix_parts: int) -> tuple[str, str]:
    """Split "provider:...:name-Gender" into (name, gender)."""
    body = raw.split(":", prefix_parts)[-1]
    name, _, gender = body.rpartition("-")
    return (name or body), gender


def _configured_provider_groups() -> list[VoiceGroup]:
    groups = []

    elevenlabs_key = config.elevenlabs.get("api_key", "")
    if elevenlabs_key:
        voices = []
        for raw in voice.get_elevenlabs_voices(elevenlabs_key):
            parts = raw.split(":", 2)
            name = parts[2] if len(parts) >= 3 else raw
            voices.append(FriendlyVoice(id=raw, label_es=name, gender="", provider="elevenlabs"))
        if voices:
            groups.append(VoiceGroup("ElevenLabs (tu cuenta)", voices))

    if config.siliconflow.get("api_key", ""):
        voices = []
        for raw in voice.get_siliconflow_voices():
            name, gender = _split_provider_voice(raw, 2)
            gender_es = _GENDER_LABELS_ES.get(gender, gender)
            voices.append(
                FriendlyVoice(
                    id=raw,
                    label_es=f"{name.capitalize()} ({gender_es})",
                    gender=gender,
                    provider="siliconflow",
                )
            )
        if voices:
            groups.append(VoiceGroup("SiliconFlow", voices))

    if config.app.get("gemini_api_key", ""):
        voices = []
        for raw in voice.get_gemini_voices():
            name, gender = _split_provider_voice(raw, 1)
            gender_es = _GENDER_LABELS_ES.get(gender, gender)
            voices.append(
                FriendlyVoice(
                    id=raw, label_es=f"{name} ({gender_es})", gender=gender, provider="gemini"
                )
            )
        if voices:
            groups.append(VoiceGroup("Gemini TTS", voices))

    if config.app.get("mimo_api_key", ""):
        voices = []
        for raw in voice.get_mimo_voices():
            name, gender = _split_provider_voice(raw, 1)
            gender_es = _GENDER_LABELS_ES.get(gender, gender)
            voices.append(
                FriendlyVoice(
                    id=raw, label_es=f"{name} ({gender_es})", gender=gender, provider="mimo"
                )
            )
        if voices:
            groups.append(VoiceGroup("MiMo TTS", voices))

    return groups


def get_friendly_voice_catalog() -> list[VoiceGroup]:
    """Return all voices available right now, grouped for display.

    Spanish and English (Edge TTS, free, no API key needed) always come
    first. Provider-specific groups (ElevenLabs, SiliconFlow, ...) only
    appear once the user has already saved a key for that provider.
    """
    return _edge_voice_groups() + _configured_provider_groups()


def sample_text_for_voice(voice_id: str) -> str:
    """Pick a short preview sentence in the voice's own language when known."""
    lang_code = voice_id.split("-")[0].lower() if "-" in voice_id else ""
    return _SAMPLE_TEXTS_BY_LANGUAGE.get(lang_code, _DEFAULT_SAMPLE_TEXT)
