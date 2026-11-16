"""Check for app updates published as GitHub Releases on the user's own repo.

This powers the "Buscar actualizaciones" button in the desktop app. Checking
is read-only (a GitHub API call to the public releases feed). Downloading and
replacing the app is done by the Electron shell (it must swap the running
/Applications bundle and relaunch), so this module only reports whether a newer
version exists and where to download it.
"""

import os
import re

import requests

from app.utils import error_messages

# The user's own repo. GitHub Actions builds each tagged version and publishes
# the .dmg as a Release; the installed app checks here for something newer.
RELEASES_OWNER = "joe150477"
RELEASES_REPO = "video-turbo"
_GITHUB_API = "https://api.github.com"
_REQUEST_TIMEOUT = 10

_VERSION_RE = re.compile(r"(\d+)\.(\d+)\.(\d+)")


def get_installed_version() -> str:
    """The running app's version. Electron passes it as MPT_APP_VERSION
    (app.getVersion()); empty in a dev checkout."""
    return os.getenv("MPT_APP_VERSION", "").strip()


def _parse_version(text: str) -> tuple[int, int, int] | None:
    """Extract a (major, minor, patch) tuple from a tag like "v1.2.3"."""
    match = _VERSION_RE.search(text or "")
    if not match:
        return None
    return (int(match.group(1)), int(match.group(2)), int(match.group(3)))


def _find_dmg_asset(release: dict) -> str:
    for asset in release.get("assets", []):
        name = str(asset.get("name", "")).lower()
        if name.endswith(".dmg"):
            return asset.get("browser_download_url", "")
    return ""


def check_for_updates() -> dict:
    """Return whether a newer published version exists, and where to get it.

    Never raises to the caller; every failure becomes a friendly Spanish
    message. Shape the frontend relies on: `update_available`, `message_es`,
    and (when an update exists) `version`, `notes`, `download_url`.
    """
    installed = get_installed_version()
    installed_tuple = _parse_version(installed)

    try:
        response = requests.get(
            f"{_GITHUB_API}/repos/{RELEASES_OWNER}/{RELEASES_REPO}/releases/latest",
            timeout=_REQUEST_TIMEOUT,
            headers={"Accept": "application/vnd.github+json"},
        )
        if response.status_code == 404:
            return {
                "update_available": False,
                "message_es": "Aún no hay versiones publicadas.",
            }
        response.raise_for_status()
        release = response.json()

        latest_tag = release.get("tag_name", "")
        latest_tuple = _parse_version(latest_tag)
        if not latest_tuple:
            return {
                "update_available": False,
                "message_es": "No se pudo leer la última versión publicada.",
            }

        download_url = _find_dmg_asset(release)

        # Can't compare without knowing the installed version (dev checkout):
        # just report what's published so the user isn't left guessing.
        if not installed_tuple:
            return {
                "update_available": False,
                "latest_version": latest_tag,
                "message_es": f"Última versión publicada: {latest_tag}.",
            }

        if latest_tuple <= installed_tuple:
            return {
                "update_available": False,
                "installed_version": installed,
                "latest_version": latest_tag,
                "message_es": "Ya tienes la versión más reciente.",
            }

        if not download_url:
            return {
                "update_available": False,
                "latest_version": latest_tag,
                "message_es": (
                    f"Hay una versión nueva ({latest_tag}), pero aún no tiene "
                    "instalador listo. Inténtalo en unos minutos."
                ),
            }

        return {
            "update_available": True,
            "installed_version": installed,
            "version": latest_tag,
            "notes": str(release.get("body", "")).strip()[:2000],
            "download_url": download_url,
            "message_es": f"¡Hay una versión nueva disponible: {latest_tag}!",
        }
    except Exception as exc:
        message, _code = error_messages.translate_exception(exc, context="updates:check")
        return {"update_available": False, "message_es": message}
