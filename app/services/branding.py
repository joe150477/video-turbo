"""Brand logo overlay for generated videos.

Kept in its own module so the change to the core video pipeline
(app/services/video.py) is a single, additive line. When no logo is
configured the overlay is a no-op and the default rendering is untouched.
"""

import os

from loguru import logger
from moviepy import CompositeVideoClip, ImageClip

from app.utils import file_security, utils

# Where uploaded brand logos live (inside the per-user storage dir).
LOGO_DIR_NAME = "brand"

_VALID_POSITIONS = {"top-left", "top-right", "bottom-left", "bottom-right", "center"}
_DEFAULT_POSITION = "bottom-right"
_DEFAULT_SIZE_PERCENT = 12  # logo width as a percentage of the video width
_MARGIN_PERCENT = 4  # gap from the video edges, as a percentage of the width


def logo_dir() -> str:
    return utils.storage_dir(LOGO_DIR_NAME, create=True)


def resolve_logo_path(logo_filename: str) -> str | None:
    """Resolve a stored logo filename to a safe absolute path, or None."""
    if not logo_filename:
        return None
    try:
        path = file_security.resolve_path_within_directory(logo_dir(), logo_filename)
    except ValueError as exc:
        logger.warning(f"skip unsafe logo path: {logo_filename}, error: {exc}")
        return None
    return path if os.path.isfile(path) else None


def _position_for(position: str, video_w: int, video_h: int, logo_w: float, logo_h: float):
    position = position if position in _VALID_POSITIONS else _DEFAULT_POSITION
    margin = int(video_w * _MARGIN_PERCENT / 100)
    left = margin
    right = int(video_w - logo_w - margin)
    top = margin
    bottom = int(video_h - logo_h - margin)

    if position == "center":
        return ("center", "center")
    if position == "top-left":
        return (left, top)
    if position == "top-right":
        return (right, top)
    if position == "bottom-left":
        return (left, bottom)
    return (right, bottom)  # bottom-right (default)


def apply_logo_overlay(video_clip, params):
    """Return `video_clip` with the configured brand logo composited on top.

    A no-op (returns the clip unchanged) when the params carry no logo, so
    callers can invoke it unconditionally. Any failure is logged and the
    original clip is returned — a broken logo must never fail a whole video.
    """
    logo_filename = getattr(params, "logo_path", "") or ""
    if not logo_filename:
        return video_clip

    logo_path = resolve_logo_path(logo_filename)
    if not logo_path:
        logger.warning(f"configured logo not found, skipping overlay: {logo_filename}")
        return video_clip

    try:
        video_w, video_h = video_clip.size
        size_percent = getattr(params, "logo_size", None) or _DEFAULT_SIZE_PERCENT
        size_percent = max(3, min(int(size_percent), 40))
        target_w = int(video_w * size_percent / 100)

        logo_clip = ImageClip(logo_path).with_duration(video_clip.duration)
        scale = target_w / logo_clip.size[0]
        logo_clip = logo_clip.resized(scale)

        position = getattr(params, "logo_position", "") or _DEFAULT_POSITION
        logo_clip = logo_clip.with_position(
            _position_for(position, video_w, video_h, logo_clip.size[0], logo_clip.size[1])
        )

        return CompositeVideoClip([video_clip, logo_clip])
    except Exception as exc:
        logger.error(f"failed to apply logo overlay, continuing without it: {exc}")
        return video_clip
