from __future__ import annotations

import pathlib
import tempfile
import unittest

from PIL import Image, PngImagePlugin

from tests.test_qa_contract import make_box_candidate
from toolchain.cloud3d.previews import label_and_compose, verify_preview_traceability
from toolchain.cloud3d.qa import run_generic_qa


RAW_VIEWS = ("front", "back", "side", "top", "isometric")


class PreviewTraceabilityTest(unittest.TestCase):
    def test_required_views_embed_candidate_identity(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            identity, roundtrip = make_box_candidate(root)
            qa = run_generic_qa(identity.path, roundtrip, {})
            raw = root / "raw"
            raw.mkdir()
            for index, view in enumerate(RAW_VIEWS):
                Image.new("RGB", (320, 320), (30 + index * 20, 80, 130)).save(
                    raw / f"fixture_v001_{view}_raw.png"
                )
            outputs = label_and_compose(raw, root / "previews", identity, qa)
            expected = {
                "front",
                "back",
                "side",
                "top",
                "isometric",
                "dimensions",
                "parts-colors",
                "proof-sheet",
            }
            self.assertEqual(
                {path.stem.removeprefix("fixture_v001_") for path in outputs}, expected
            )
            verify_preview_traceability(outputs, identity)
            for path in outputs:
                with Image.open(path) as image:
                    self.assertEqual(image.info["model"], "fixture")
                    self.assertEqual(image.info["version"], "v001")
                    self.assertEqual(image.info["short_id"], identity.short_id)
                    self.assertEqual(image.info["sha256"], identity.sha256)
                    self.assertEqual(image.info["geometry_source"], "reopened candidate 3MF")

    def test_preview_from_other_version_or_sha_is_rejected_even_when_filename_matches(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            identity, _ = make_box_candidate(root)
            path = root / "fixture_v001_front.png"
            metadata = PngImagePlugin.PngInfo()
            metadata.add_text("model", "fixture")
            metadata.add_text("version", "v001")
            metadata.add_text("short_id", identity.short_id)
            metadata.add_text("sha256", "0" * 64)
            metadata.add_text("geometry_source", "reopened candidate 3MF")
            Image.new("RGB", (20, 20)).save(path, pnginfo=metadata)
            with self.assertRaisesRegex(ValueError, "sha256"):
                verify_preview_traceability([path], identity)


if __name__ == "__main__":
    unittest.main()
