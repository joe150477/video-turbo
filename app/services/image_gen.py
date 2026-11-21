"""Generate original images with AI as an extra visual source.

This is the "Imágenes con IA" option in the desktop app: instead of (or on top
of) stock footage and the school's own material, the pipeline can invent images
that match each line of the script. The still images then flow through the exact
same path as the user's own photos (``video.preprocess_video``), so they get the
Ken Burns motion, auto-enhancement and aspect handling already built for stills.

Design goals for a non-technical user on a MacBook Air:
- Default provider is **Pollinations** (https://image.pollinations.ai): free,
  no API key, FLUX under the hood, runs in the cloud so the Air stays cool.
- An optional **OpenAI (DALL·E 3)** provider gives higher quality when the user
  has pasted an OpenAI key in the app; if there is no key we quietly fall back
  to Pollinations instead of failing the whole video.
Nothing here needs a local GPU, so it never blocks or overheats the machine.
"""

import math
import os
import time
from typing import List
from urllib.parse import quote

import requests
from loguru import logger

from app.config import config
from app.models.schema import VideoAspect
from app.utils import utils

# How many images we are willing to generate for one render, so a very long
# narration can never spin up hundreds of slow cloud calls.
_MAX_IMAGES = 30
_DEFAULT_STYLE = "cinematic, photorealistic, high detail, natural lighting"


def _images_needed(audio_duration: float, max_clip_duration: int, term_count: int) -> int:
    """At least one image per script term, and enough to cover the narration."""
    by_duration = 0
    if audio_duration and max_clip_duration:
        by_duration = math.ceil(audio_duration / max_clip_duration)
    needed = max(term_count, by_duration, 1)
    return min(needed, _MAX_IMAGES)


def _generation_size(video_aspect: VideoAspect) -> tuple[int, int]:
    """A fast, model-friendly size per aspect. The video pipeline scales the
    still to the final resolution later, so we don't generate at full 1080x1920
    (that is needlessly slow on free providers)."""
    if video_aspect == VideoAspect.landscape:
        return 1344, 768
    if video_aspect == VideoAspect.square:
        return 1024, 1024
    # portrait (default for shorts/reels)
    return 768, 1344


def _save_bytes(data: bytes, save_dir: str, index: int) -> str:
    os.makedirs(save_dir, exist_ok=True)
    path = os.path.join(save_dir, f"ai_image_{index:02d}.jpg")
    with open(path, "wb") as fh:
        fh.write(data)
    return path


def _pollinations_image(prompt: str, width: int, height: int, seed: int, token: str = "") -> bytes:
    """Free FLUX image from Pollinations. Returns raw JPEG bytes or raises.

    Works with no key at all, but the anonymous tier stamps a small
    "pollinations.ai" watermark even with nologo=true. A free token (from
    auth.pollinations.ai) removes the watermark and improves reliability; when
    the user has pasted one in the app we send it.
    """
    url = (
        f"https://image.pollinations.ai/prompt/{quote(prompt)}"
        f"?width={width}&height={height}&nologo=true&model=flux&seed={seed}"
    )
    headers = {}
    if token:
        # Pollinations accepts the token as a referrer/bearer; the header is the
        # documented way and keeps the token out of logs/URLs.
        headers["Authorization"] = f"Bearer {token}"

    # The free tier is intermittently overloaded (HTTP 503). Retry a few times
    # with a growing wait so a transient hiccup doesn't drop the image.
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            response = requests.get(url, headers=headers, timeout=180)
            response.raise_for_status()
            content = response.content
            if not content or len(content) < 1024:
                raise ValueError("empty or too-small image response")
            return content
        except Exception as exc:  # noqa: BLE001 - retried below, re-raised if final
            last_error = exc
            if attempt < 2:
                time.sleep(2 * (attempt + 1))
    raise last_error if last_error else RuntimeError("pollinations failed")


def _openai_size(video_aspect: VideoAspect) -> str:
    if video_aspect == VideoAspect.landscape:
        return "1792x1024"
    if video_aspect == VideoAspect.square:
        return "1024x1024"
    return "1024x1792"


def _openai_image(prompt: str, video_aspect: VideoAspect, api_key: str) -> bytes:
    """DALL·E 3 image. Returns raw bytes or raises. Needs an OpenAI key."""
    response = requests.post(
        "https://api.openai.com/v1/images/generations",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "model": "dall-e-3",
            "prompt": prompt,
            "n": 1,
            "size": _openai_size(video_aspect),
            "response_format": "url",
        },
        timeout=180,
    )
    response.raise_for_status()
    image_url = response.json()["data"][0]["url"]
    img = requests.get(image_url, timeout=180)
    img.raise_for_status()
    return img.content


def _first_api_key(cfg_key: str) -> str:
    value = config.app.get(cfg_key)
    if isinstance(value, list):
        return str(value[0]).strip() if value else ""
    return str(value or "").strip()


def generate_ai_images(
    task_id: str,
    search_terms: List[str],
    video_aspect: VideoAspect = VideoAspect.portrait,
    audio_duration: float = 0.0,
    max_clip_duration: int = 5,
    video_count: int = 1,
    provider: str = "",
    style: str = "",
) -> List[str]:
    """Generate one AI image per script beat and return their local file paths.

    Never raises to the caller: on a provider failure it skips that image and
    keeps going, returning whatever succeeded (possibly an empty list, which the
    caller treats like "no materials found").
    """
    provider = (
        provider or config.app.get("image_gen_provider", "pollinations") or "pollinations"
    ).lower()
    style = style or config.app.get("image_gen_style", "") or _DEFAULT_STYLE

    terms = [t for t in (search_terms or []) if str(t).strip()]
    if not terms:
        terms = ["abstract background"]

    total_duration = audio_duration * max(video_count, 1)
    count = _images_needed(total_duration, max_clip_duration, len(terms))
    width, height = _generation_size(video_aspect)

    # Resolve the OpenAI key up front so we can fall back before the loop.
    openai_key = _first_api_key("openai_api_keys")
    if provider == "openai" and not openai_key:
        logger.warning("image_gen: OpenAI selected but no key set; falling back to Pollinations")
        provider = "pollinations"
    # Optional free token that removes the Pollinations watermark.
    pollinations_token = _first_api_key("pollinations_token")

    material_directory = config.app.get("material_directory", "").strip()
    if (
        material_directory == "task"
        or not material_directory
        or not os.path.isdir(material_directory)
    ):
        material_directory = utils.task_dir(task_id)

    logger.info(f"image_gen: generating {count} AI image(s) via {provider}")
    paths: List[str] = []
    for index in range(count):
        term = terms[index % len(terms)]
        prompt = f"{term}, {style}"
        try:
            if provider == "openai":
                data = _openai_image(prompt, video_aspect, openai_key)
            else:
                data = _pollinations_image(
                    prompt, width, height, seed=1000 + index, token=pollinations_token
                )
            path = _save_bytes(data, material_directory, index)
            paths.append(path)
            logger.info(f"image_gen: saved {path} ('{term}')")
        except Exception as exc:  # noqa: BLE001 - one bad image must not kill the render
            logger.warning(f"image_gen: failed image {index} ('{term}'): {exc}")
            # brief backoff so a transient hiccup doesn't cascade
            time.sleep(1)

    logger.success(f"image_gen: produced {len(paths)} AI image(s)")
    return paths
