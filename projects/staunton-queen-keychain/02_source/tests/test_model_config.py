from pathlib import Path
import sys
import unittest


BLENDER_DIR = Path(__file__).resolve().parents[1] / "blender"
sys.path.insert(0, str(BLENDER_DIR))

from model_config import ModelConfig


class ModelConfigTest(unittest.TestCase):
    def test_approved_dimensions_and_names(self):
        cfg = ModelConfig()
        self.assertEqual(cfg.model_name, "staunton_queen_keychain")
        self.assertEqual(cfg.version, "v002")
        self.assertAlmostEqual(cfg.height_mm, 50.0)
        self.assertAlmostEqual(cfg.base_diameter_mm, 22.5)
        self.assertAlmostEqual(cfg.finial_diameter_mm, 8.0)
        self.assertAlmostEqual(cfg.hole_diameter_mm, 3.2)
        self.assertEqual(cfg.crown_teeth, 8)
        self.assertEqual(cfg.body_name, "staunton_queen_keychain_body")

    def test_printability_invariants(self):
        cfg = ModelConfig()
        ligament = (cfg.finial_diameter_mm - cfg.hole_diameter_mm) / 2.0
        self.assertGreaterEqual(ligament, 2.4)
        self.assertEqual(cfg.hole_axis, "X")
        self.assertAlmostEqual(cfg.base_z_mm, 0.0)
        self.assertLessEqual(cfg.remesh_voxel_mm, 0.15)

    def test_profile_is_monotonic_in_z_and_hits_base_limit(self):
        cfg = ModelConfig()
        zs = [z for z, radius in cfg.lathe_profile]
        radii = [radius for z, radius in cfg.lathe_profile]
        self.assertEqual(zs, sorted(zs))
        self.assertAlmostEqual(max(radii) * 2.0, cfg.base_diameter_mm)
        self.assertAlmostEqual(zs[0], 0.0)
        self.assertLess(zs[-1], cfg.finial_center_z_mm)


if __name__ == "__main__":
    unittest.main()
