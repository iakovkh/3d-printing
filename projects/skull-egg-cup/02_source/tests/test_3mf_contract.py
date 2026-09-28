import pathlib
import tempfile
import unittest

import numpy
import trimesh


class ThreeMFContractTest(unittest.TestCase):
    def test_export_reopen_preserves_mm_bounds_and_one_body(self):
        mesh = trimesh.creation.box(extents=[10.0, 20.0, 30.0])
        mesh.units = "mm"
        scene = trimesh.Scene({"fixture": mesh})
        with tempfile.TemporaryDirectory() as temporary:
            path = pathlib.Path(temporary) / "fixture.3mf"
            path.write_bytes(scene.export(file_type="3mf"))
            reopened = trimesh.load(path, force="scene")
            self.assertEqual(len(reopened.geometry), 1)
            self.assertTrue(numpy.all(abs(reopened.extents - [10.0, 20.0, 30.0]) < 0.001))


if __name__ == "__main__":
    unittest.main()
