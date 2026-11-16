# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the MoneyPrinterTurbo backend.

Bundles the FastAPI backend as a standalone executable so the desktop app
never requires the end user to install Python. Build with:

    uv run --group build pyinstaller desktop/build/backend.spec --noconfirm

`faster_whisper`/`ctranslate2` and the Azure Speech SDK are excluded: both
are only reachable through config.toml options the desktop wizard never
exposes (subtitle generation defaults to Edge TTS; Azure TTS v2 requires a
manually-set speech_key/speech_region), and both imports are already
guarded at their call sites (see app/services/subtitle.py and
app/services/voice.py), so excluding them shrinks the bundle without
breaking anything reachable from the UI.
"""

import os
import subprocess

import imageio_ffmpeg
from PyInstaller.utils.hooks import copy_metadata

REPO_ROOT = os.path.abspath(os.path.join(SPECPATH, "..", ".."))  # noqa: F821  (PyInstaller global)


def repo_path(*parts: str) -> str:
    return os.path.join(REPO_ROOT, *parts)


# Record the git commit this build came from so the frozen app (which has no
# .git) can still check GitHub for a newer version. See
# app/services/updates.py::_baked_build_commit.
_build_commit_file = os.path.join(SPECPATH, "_generated", "build_commit.txt")  # noqa: F821
os.makedirs(os.path.dirname(_build_commit_file), exist_ok=True)
try:
    _commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True
    ).strip()
except Exception:
    _commit = ""
with open(_build_commit_file, "w", encoding="utf-8") as _f:
    _f.write(_commit)


# Several dependencies (imageio in particular, transitively pulled in by
# moviepy) call importlib.metadata.version(...) on themselves at import
# time. PyInstaller does not bundle a package's .dist-info by default, so
# without this those imports crash with PackageNotFoundError the first
# time they run *inside the frozen app* — a class of failure that never
# shows up in a normal `uv run` dev environment.
_METADATA_PACKAGES = [
    "moviepy", "imageio", "imageio-ffmpeg", "decorator", "proglog",
    "numpy", "pillow", "tqdm", "openai", "google-generativeai", "litellm",
    "tiktoken", "edge-tts", "fastapi", "starlette", "uvicorn", "keyring",
    "redis", "pydantic", "pydub", "requests", "loguru", "toml", "dashscope",
]
metadata_datas = []
for _package in _METADATA_PACKAGES:
    try:
        metadata_datas += copy_metadata(_package)
    except Exception:
        # Not every name above is guaranteed to be an installed
        # distribution (e.g. it may be a sub-package of a larger one);
        # skip silently rather than aborting the whole build over it.
        pass

datas = [
    (repo_path("config.example.toml"), "."),
    (_build_commit_file, "."),
    (repo_path("resource", "fonts"), "resource/fonts"),
    (repo_path("resource", "songs"), "resource/songs"),
    (repo_path("resource", "public"), "resource/public"),
    (repo_path("app", "services", "data"), "app/services/data"),
    *metadata_datas,
]

binaries = [
    (imageio_ffmpeg.get_ffmpeg_exe(), "."),
]

excludes = [
    "faster_whisper",
    "ctranslate2",
    "azure.cognitiveservices.speech",
]

a = Analysis(  # noqa: F821  (PyInstaller global)
    [repo_path("main.py")],
    pathex=[REPO_ROOT],
    binaries=binaries,
    datas=datas,
    # `main.py` only references "app.asgi:app" as a string (uvicorn resolves
    # it dynamically), so PyInstaller's static analysis never sees it or
    # anything it imports (routers, controllers, every app/services/*.py)
    # unless it's listed explicitly here.
    hiddenimports=["app.asgi", "litellm", "google.generativeai"],
    excludes=excludes,
    noarchive=False,
)

pyz = PYZ(a.pure)  # noqa: F821  (PyInstaller global)

exe = EXE(  # noqa: F821  (PyInstaller global)
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="moneyprinterturbo-backend",
    console=True,
)

# --onedir (not --onefile): a bundled onefile executable spawns an
# extra bootloader process that survives its own child being killed,
# which would break Electron's clean-shutdown logic in
# desktop/electron/src/backend-manager.ts.
coll = COLLECT(  # noqa: F821  (PyInstaller global)
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="moneyprinterturbo-backend",
)
