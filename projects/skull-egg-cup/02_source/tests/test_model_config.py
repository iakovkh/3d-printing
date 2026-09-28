import importlib.util
import pathlib
import unittest


CONFIG_PATH = pathlib.Path(__file__).resolve().parents[1] / "blender" / "model_config.py"


class ModelConfigTest(unittest.TestCase):
    def test_v001_contract(self):
        self.assertTrue(CONFIG_PATH.is_file(), f"missing config: {CONFIG_PATH}")
        spec = importlib.util.spec_from_file_location("model_config", CONFIG_PATH)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        cfg = module.CONFIG

        self.assertEqual(cfg.version, "v001")
        self.assertEqual(cfg.egg_diameter_mm, 45.0)
        self.assertEqual(cfg.egg_height_mm, 58.0)
        self.assertEqual(cfg.opening_diameter_mm, 42.0)
        self.assertEqual(cfg.cavity_depth_mm, 22.0)
        self.assertGreaterEqual(cfg.min_wall_mm, 2.4)
        self.assertGreaterEqual(cfg.min_relief_mm, 0.8)
        self.assertEqual(cfg.body_count, 1)


if __name__ == "__main__":
    unittest.main()
