"""Translate internal exceptions into short, user-facing Spanish messages.

The desktop app never shows Python tracebacks to end users. Every unexpected
exception is logged in full (for support/debugging) but only a curated,
non-technical message and a stable error code cross the API boundary.
"""

import uuid

from loguru import logger

_CONNECTION_KEYWORDS = (
    "connectionerror",
    "connection refused",
    "connection reset",
    "timeout",
    "timed out",
    "name or service not known",
    "network is unreachable",
    "temporary failure in name resolution",
)

_AUTH_KEYWORDS = (
    "401",
    "unauthorized",
    "invalid_api_key",
    "invalid api key",
    "authenticationerror",
    "permission_denied",
    "403",
    "forbidden",
    "api key not valid",
)

_RATE_LIMIT_KEYWORDS = (
    "429",
    "rate limit",
    "rate_limit",
    "quota",
    "resourceexhausted",
    "too many requests",
)

_MISSING_COMPONENT_KEYWORDS = ("ffmpeg", "imagemagick")

_GENERIC_MESSAGE = (
    "Ocurrió un problema inesperado (código {error_id}). "
    "Inténtalo de nuevo; si el problema persiste, contacta soporte."
)


def _classify(exc_text: str, error_id: str) -> tuple[str, str]:
    if any(keyword in exc_text for keyword in _MISSING_COMPONENT_KEYWORDS):
        return (
            "No se encontró un componente interno necesario (FFmpeg). "
            "Intenta reinstalar la aplicación.",
            "missing_component",
        )
    if any(keyword in exc_text for keyword in _AUTH_KEYWORDS):
        return (
            "La clave de API no es válida o no tiene permisos. Revisa que la copiaste completa.",
            "invalid_api_key",
        )
    if any(keyword in exc_text for keyword in _RATE_LIMIT_KEYWORDS):
        return (
            "Has alcanzado el límite de uso de tu proveedor. "
            "Espera un momento o revisa tu plan.",
            "rate_limited",
        )
    if any(keyword in exc_text for keyword in _CONNECTION_KEYWORDS):
        return (
            "No se pudo conectar a internet. Revisa tu conexión e inténtalo de nuevo.",
            "network_error",
        )
    return _GENERIC_MESSAGE.format(error_id=error_id), "unknown_error"


def translate_exception(exc: Exception, context: str = "") -> tuple[str, str]:
    """Return a (spanish_message, error_code) pair for a live exception.

    Logs the full exception (with traceback) server-side under the returned
    error_id, so support can correlate a user report with the real cause
    without ever exposing it to the user. Must be called while `exc` is
    still the active exception (i.e. from inside its `except` block).
    """
    error_id = uuid.uuid4().hex[:8]
    exc_text = f"{type(exc).__name__}: {exc}".lower()
    message, code = _classify(exc_text, error_id)

    log_context = f" [{context}]" if context else ""
    logger.exception(f"error_id={error_id}{log_context}: {exc}")
    return message, code


def translate_message(message: str, context: str = "") -> tuple[str, str]:
    """Same classification as `translate_exception`, for callers that only
    have an error string rather than a live exception object.

    Some provider wrappers in this codebase (see `llm._generate_response`)
    already catch their own exceptions and return a plain "Error: ..."
    string instead of raising, so there is no traceback to attach here.
    """
    error_id = uuid.uuid4().hex[:8]
    result_message, code = _classify(message.lower(), error_id)

    log_context = f" [{context}]" if context else ""
    logger.warning(f"error_id={error_id}{log_context}: {message}")
    return result_message, code
