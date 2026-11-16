import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from PIL import Image

from app.services import video


class TestEnhanceImageFile(unittest.TestCase):
    def test_enhances_a_real_image_into_a_new_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = str(Path(tmp) / "photo.jpg")
            Image.new("RGB", (640, 480), (90, 90, 90)).save(src)

            out = video.enhance_image_file(src)

            self.assertNotEqual(out, src)
            self.assertTrue(Path(out).exists())
            # The result must still be a readable image of the same size.
            with Image.open(out) as img:
                self.assertEqual(img.size, (640, 480))

    def test_returns_original_path_on_failure(self):
        # A path that is not a real image must not raise; enhancement is
        # best-effort and falls back to the original so no video is lost.
        with tempfile.TemporaryDirectory() as tmp:
            bogus = str(Path(tmp) / "not-an-image.jpg")
            Path(bogus).write_text("this is not an image")

            out = video.enhance_image_file(bogus)

            self.assertEqual(out, bogus)


if __name__ == "__main__":
    unittest.main()
