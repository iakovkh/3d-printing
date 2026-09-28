import json
from pathlib import Path
import unittest

from PIL import Image


ROOT = Path(__file__).resolve().parents[4]
QA_PATH = ROOT / "projects/staunton-queen-keychain/04_review/v002/staunton_queen_keychain_v002_qa.json"
PREVIEW_DIR = ROOT / "projects/staunton-queen-keychain/04_review/v002/previews"
REQUIRED = {
    "front",
    "back",
    "side",
    "top",
    "isometric",
    "detail",
    "dimensions",
    "parts-colors",
    "proof-sheet",
}


class PreviewTraceabilityTest(unittest.TestCase):
    def test_every_preview_matches_qa_identity(self):
        qa = json.loads(QA_PATH.read_text(encoding="utf-8"))
        for kind in REQUIRED:
            path = PREVIEW_DIR / f"staunton_queen_keychain_v002_{kind}.png"
            self.assertTrue(path.is_file(), path)
            with Image.open(path) as image:
                self.assertEqual(image.info["version"], "v002")
                self.assertEqual(image.info["short_id"], qa["short_id"])
                self.assertEqual(image.info["sha256"], qa["sha256"])


if __name__ == "__main__":
    unittest.main()
