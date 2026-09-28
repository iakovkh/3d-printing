import pathlib
import unittest

import trimesh


ROOT = pathlib.Path(__file__).resolve().parents[4]
STL_PATH = ROOT / "projects/staunton-queen-keychain/03_build/v002/staunton_queen_keychain_v002_body.stl"


class ExportContractTest(unittest.TestCase):
    def test_stl_has_one_watertight_component_and_expected_envelope(self):
        self.assertTrue(STL_PATH.is_file(), STL_PATH)
        mesh = trimesh.load_mesh(STL_PATH, file_type="stl", process=True)
        self.assertIsInstance(mesh, trimesh.Trimesh)
        self.assertTrue(mesh.is_watertight)
        self.assertEqual(len(mesh.split(only_watertight=False)), 1)
        self.assertTrue((abs(mesh.extents - [22.5, 22.5, 50.0]) <= 0.10).all())
        self.assertAlmostEqual(float(mesh.bounds[0][2]), 0.0, delta=0.05)


if __name__ == "__main__":
    unittest.main()
