import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.models.schema import VideoAspect
from app.services import image_gen


class TestImagesNeeded(unittest.TestCase):
    def test_at_least_one_per_term(self):
        # 2 terms, tiny duration -> at least 2 images
        self.assertEqual(image_gen._images_needed(3.0, 5, 2), 2)

    def test_covers_duration(self):
        # 20s narration, 5s clips -> 4 images even with a single term
        self.assertEqual(image_gen._images_needed(20.0, 5, 1), 4)

    def test_capped(self):
        self.assertEqual(image_gen._images_needed(10_000.0, 1, 1), image_gen._MAX_IMAGES)

    def test_minimum_one(self):
        self.assertEqual(image_gen._images_needed(0.0, 5, 0), 1)


class TestGenerationSize(unittest.TestCase):
    def test_portrait_is_tall(self):
        w, h = image_gen._generation_size(VideoAspect.portrait)
        self.assertLess(w, h)

    def test_landscape_is_wide(self):
        w, h = image_gen._generation_size(VideoAspect.landscape)
        self.assertGreater(w, h)

    def test_square(self):
        self.assertEqual(image_gen._generation_size(VideoAspect.square), (1024, 1024))


class TestGenerateAiImages(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def _fake_cfg(self, **extra):
        cfg = {"material_directory": self.tmp}
        cfg.update(extra)
        return cfg

    def test_generates_one_file_per_image(self):
        with (
            patch.object(image_gen.config, "app", self._fake_cfg()),
            patch.object(image_gen, "_pollinations_image", return_value=b"x" * 4096) as poll,
        ):
            paths = image_gen.generate_ai_images(
                task_id="t1",
                search_terms=["a", "b"],
                video_aspect=VideoAspect.portrait,
                audio_duration=4.0,
                max_clip_duration=5,
            )
        self.assertEqual(len(paths), 2)
        for p in paths:
            self.assertTrue(os.path.exists(p))
        self.assertEqual(poll.call_count, 2)

    def test_openai_without_key_falls_back_to_pollinations(self):
        with (
            patch.object(image_gen.config, "app", self._fake_cfg(image_gen_provider="openai")),
            patch.object(image_gen, "_pollinations_image", return_value=b"x" * 4096) as poll,
            patch.object(image_gen, "_openai_image") as openai,
        ):
            paths = image_gen.generate_ai_images(
                task_id="t2",
                search_terms=["only-term"],
                video_aspect=VideoAspect.portrait,
                audio_duration=3.0,
                max_clip_duration=5,
            )
        self.assertEqual(len(paths), 1)
        poll.assert_called()  # fell back
        openai.assert_not_called()

    def test_one_bad_image_does_not_kill_the_batch(self):
        calls = {"n": 0}

        def flaky(*args, **kwargs):
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("provider hiccup")
            return b"x" * 4096

        with (
            patch.object(image_gen.config, "app", self._fake_cfg()),
            patch.object(image_gen, "_pollinations_image", side_effect=flaky),
            patch.object(image_gen.time, "sleep"),
        ):
            paths = image_gen.generate_ai_images(
                task_id="t3",
                search_terms=["a", "b", "c"],
                video_aspect=VideoAspect.portrait,
                audio_duration=15.0,
                max_clip_duration=5,
            )
        # 3 attempted, first failed -> 2 survive
        self.assertEqual(len(paths), 2)

    def test_token_is_passed_when_present(self):
        with (
            patch.object(image_gen.config, "app", self._fake_cfg(pollinations_token="tok123")),
            patch.object(image_gen, "_pollinations_image", return_value=b"x" * 4096) as poll,
        ):
            image_gen.generate_ai_images(
                task_id="t4",
                search_terms=["a"],
                video_aspect=VideoAspect.portrait,
                audio_duration=3.0,
                max_clip_duration=5,
            )
        self.assertEqual(poll.call_args.kwargs.get("token"), "tok123")


class _Resp:
    def __init__(self, status, content=b"\xff\xd8\xff" + b"x" * 4096):
        self.status_code = status
        self.content = content

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class TestPollinationsRetry(unittest.TestCase):
    def test_retries_then_succeeds(self):
        # Two 503s, then a good image -> should return bytes, not raise.
        responses = [_Resp(503), _Resp(503), _Resp(200)]
        with (
            patch.object(image_gen.requests, "get", side_effect=responses) as get,
            patch.object(image_gen.time, "sleep"),
        ):
            data = image_gen._pollinations_image("x", 768, 1344, seed=1)
        self.assertTrue(data.startswith(b"\xff\xd8\xff"))
        self.assertEqual(get.call_count, 3)

    def test_gives_up_after_three(self):
        with (
            patch.object(image_gen.requests, "get", side_effect=[_Resp(503)] * 3),
            patch.object(image_gen.time, "sleep"),
        ):
            with self.assertRaises(Exception):
                image_gen._pollinations_image("x", 768, 1344, seed=1)


if __name__ == "__main__":
    unittest.main()
