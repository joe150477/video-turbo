"""Check for and apply updates from the upstream MoneyPrinterTurbo project.

This powers the "Buscar actualizaciones" button in the desktop app's
settings. Checking is read-only (a GitHub API call). Applying is guarded:
it always makes a full backup first and restores it automatically if
anything goes wrong, and it never runs unless the user explicitly asks.
"""

import os
import shutil
import subprocess
from datetime import datetime

import requests
from loguru import logger

from app.utils import error_messages, utils

UPSTREAM_OWNER = "harry0703"
UPSTREAM_REPO = "MoneyPrinterTurbo"
UPSTREAM_BRANCH = "main"
_GITHUB_API = "https://api.github.com"
_REQUEST_TIMEOUT = 10

# Core files this project modifies (kept in sync with CUSTOMIZATIONS.md
# section 2). If an upstream update touches one of these, applying it may
# need manual conflict resolution — so we warn the user up front rather
# than letting a merge fail unexpectedly.
MODIFIED_CORE_FILES = {
    "app/router.py",
    "app/asgi.py",
    "app/models/schema.py",
    "app/services/task.py",
    "app/services/material.py",
    "app/config/config.py",
    "app/utils/utils.py",
    "pyproject.toml",
    ".github/workflows/ci.yml",
}

# Directories never worth backing up or restoring: they are large,
# regenerated, or machine-specific.
_BACKUP_EXCLUDES = {
    ".git",
    ".venv",
    "node_modules",
    "storage",
    "release",
    "dist",
    "work",
    "__pycache__",
}


def _run_git(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=utils.root_dir(),
        capture_output=True,
        text=True,
        check=True,
        timeout=120,
    )


def _is_git_checkout() -> bool:
    return os.path.isdir(os.path.join(utils.root_dir(), ".git"))


def _baked_build_commit() -> str | None:
    # The packaged app has no .git, so the build records the commit it was
    # built from in this file (see desktop/build/backend.spec). That lets
    # the frozen app still *check* GitHub for a newer version, even though
    # it can't git-merge itself.
    build_commit_file = os.path.join(utils.root_dir(), "build_commit.txt")
    try:
        with open(build_commit_file, "r", encoding="utf-8") as f:
            value = f.read().strip()
        return value or None
    except OSError:
        return None


def get_local_commit() -> str | None:
    if _is_git_checkout():
        try:
            return _run_git(["rev-parse", "HEAD"]).stdout.strip()
        except Exception as exc:
            logger.warning(f"could not read local git commit: {exc}")
            return None
    return _baked_build_commit()


def check_for_updates() -> dict:
    """Compare the local version against upstream's latest commit.

    Works both from a git checkout (dev) and from the packaged app (which
    reads its build commit from a bundled file). Returns a dict describing
    whether an update exists, a short list of incoming changes, and whether
    it looks compatible — all in Spanish, never raising to the caller.
    """
    local_commit = get_local_commit()
    if not local_commit:
        return {
            "update_available": False,
            "message_es": "No se pudo determinar la versión instalada.",
        }

    try:
        latest = requests.get(
            f"{_GITHUB_API}/repos/{UPSTREAM_OWNER}/{UPSTREAM_REPO}/commits/{UPSTREAM_BRANCH}",
            timeout=_REQUEST_TIMEOUT,
            headers={"Accept": "application/vnd.github+json"},
        )
        latest.raise_for_status()
        remote_commit = latest.json()["sha"]

        if remote_commit.startswith(local_commit) or local_commit.startswith(remote_commit):
            return {
                "update_available": False,
                "local_commit": local_commit[:7],
                "message_es": "Ya tienes la versión más reciente.",
            }

        compare = requests.get(
            f"{_GITHUB_API}/repos/{UPSTREAM_OWNER}/{UPSTREAM_REPO}"
            f"/compare/{local_commit}...{remote_commit}",
            timeout=_REQUEST_TIMEOUT,
            headers={"Accept": "application/vnd.github+json"},
        )
        compare.raise_for_status()
        compare_data = compare.json()

        changes = [
            commit["commit"]["message"].splitlines()[0]
            for commit in compare_data.get("commits", [])
        ]
        changed_files = {file["filename"] for file in compare_data.get("files", [])}
        touched_core = sorted(changed_files & MODIFIED_CORE_FILES)

        can_auto_apply = _is_git_checkout()

        if not can_auto_apply:
            # A packaged, frozen app can detect a new version but can't
            # rewrite its own read-only source; guide the user to the
            # installer instead of offering a one-click merge.
            compatible = True
            compatibility_message = (
                "Hay una versión más reciente disponible. Descarga el nuevo "
                "instalador desde el sitio oficial para actualizar."
            )
        elif touched_core:
            compatible = False
            compatibility_message = (
                "Esta actualización modifica archivos que la aplicación ha "
                "personalizado. Se puede instalar, pero conviene revisarla; "
                "se hará una copia de seguridad y se restaurará si algo falla."
            )
        else:
            compatible = True
            compatibility_message = "Esta actualización es compatible con tu configuración."

        return {
            "update_available": True,
            "can_auto_apply": can_auto_apply,
            "local_commit": local_commit[:7],
            "remote_commit": remote_commit[:7],
            "behind_by": compare_data.get("ahead_by", len(changes)),
            "changes": changes[:20],
            "compatible": compatible,
            "affected_custom_files": touched_core,
            "message_es": compatibility_message,
        }
    except Exception as exc:
        message, _code = error_messages.translate_exception(exc, context="updates:check")
        return {"update_available": False, "message_es": message}


def _backup_root() -> str:
    return utils.storage_dir("backups", create=True)


def create_backup() -> str:
    """Copy the source tree (minus heavy/generated dirs) to a timestamped
    folder, so a failed update can be rolled back file-for-file."""
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    destination = os.path.join(_backup_root(), timestamp)
    shutil.copytree(
        utils.root_dir(),
        destination,
        ignore=shutil.ignore_patterns(*_BACKUP_EXCLUDES),
    )
    logger.info(f"created update backup at {destination}")
    return destination


def _restore_backup(backup_dir: str) -> None:
    root = utils.root_dir()
    for entry in os.listdir(backup_dir):
        source = os.path.join(backup_dir, entry)
        target = os.path.join(root, entry)
        if os.path.isdir(source):
            shutil.rmtree(target, ignore_errors=True)
            shutil.copytree(source, target)
        else:
            shutil.copy2(source, target)
    logger.info(f"restored source tree from backup {backup_dir}")


def apply_update() -> dict:
    """Update the local checkout to upstream's latest commit.

    Always backs up first; on any failure, restores the backup and reports
    it. The upstream merge preserves this project's customizations by
    committing them locally before merging, so a conflict aborts cleanly
    instead of corrupting the tree.
    """
    if not _is_git_checkout():
        return {
            "ok": False,
            "message_es": "Esta versión instalada no admite actualizaciones automáticas.",
        }

    backup_dir = None
    try:
        backup_dir = create_backup()
    except Exception as exc:
        message, _code = error_messages.translate_exception(exc, context="updates:backup")
        return {"ok": False, "message_es": f"No se pudo crear la copia de seguridad. {message}"}

    try:
        # Snapshot local customizations as a commit so the working tree is
        # clean enough to merge; identity is set inline in case git has no
        # global user configured on this machine.
        _run_git(["add", "-A"])
        status = _run_git(["status", "--porcelain"]).stdout.strip()
        if status:
            _run_git(
                [
                    "-c",
                    "user.email=app@moneyprinterturbo.local",
                    "-c",
                    "user.name=MoneyPrinterTurbo",
                    "commit",
                    "-m",
                    "Guardar personalizaciones antes de actualizar",
                ]
            )

        # A depth-1 clone must be deepened before it can merge upstream.
        try:
            _run_git(["fetch", "--unshallow", "origin", UPSTREAM_BRANCH])
        except subprocess.CalledProcessError:
            _run_git(["fetch", "origin", UPSTREAM_BRANCH])

        _run_git(["merge", "--no-edit", f"origin/{UPSTREAM_BRANCH}"])

        return {
            "ok": True,
            "message_es": (
                "Actualización instalada correctamente. "
                "Reinicia la aplicación para aplicar los cambios."
            ),
        }
    except Exception as exc:
        logger.warning(f"update failed, rolling back: {exc}")
        try:
            _run_git(["merge", "--abort"])
        except Exception:
            pass
        try:
            if backup_dir:
                _restore_backup(backup_dir)
            restored = True
        except Exception as restore_exc:
            logger.error(f"failed to restore backup: {restore_exc}")
            restored = False

        if restored:
            return {
                "ok": False,
                "message_es": (
                    "La actualización falló, pero se restauró la versión anterior. "
                    "La aplicación sigue funcionando con normalidad."
                ),
            }
        return {
            "ok": False,
            "message_es": (
                "La actualización falló y no se pudo restaurar automáticamente. "
                f"Hay una copia de seguridad en: {backup_dir}"
            ),
        }
