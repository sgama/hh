import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "prune-public.py"


class PrunePublicTest(unittest.TestCase):
    def test_keeps_images_referenced_under_the_pages_base_path(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            script = root / "scripts" / "prune-public.py"
            script.parent.mkdir()
            shutil.copyfile(SCRIPT, script)

            images = root / "public" / "projects" / "demo" / "images"
            images.mkdir(parents=True)
            root_relative = images / "root-relative.webp"
            absolute = images / "absolute.webp"
            unused = images / "unused.webp"
            for image in (root_relative, absolute, unused):
                image.write_bytes(b"image")

            (root / "public" / "index.html").write_text(
                '<img src="/hh/projects/demo/images/root-relative.webp">'
                '<img src="https://sgama.github.io/hh/projects/demo/images/absolute.webp">',
                encoding="utf-8",
            )

            subprocess.run(
                [sys.executable, str(script), "https://sgama.github.io/hh/"],
                check=True,
                capture_output=True,
                text=True,
            )

            self.assertTrue(root_relative.exists())
            self.assertTrue(absolute.exists())
            self.assertFalse(unused.exists())


if __name__ == "__main__":
    unittest.main()
