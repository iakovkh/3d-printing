import pathlib
import sys
import unittest

import numpy
import trimesh


TOOLS_DIR = pathlib.Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS_DIR))

from qa_candidate import (
    candidate_version,
    count_peaks_from_polar_samples,
    evaluate_hole,
    measure_concentric_rings,
    measure_hole_or_blocker,
)


def concentric_fixture(inner_radius, outer_radius, count=128):
    theta = numpy.linspace(0.0, 2.0 * numpy.pi, count, endpoint=False)
    inner = numpy.column_stack(
        (inner_radius * numpy.cos(theta), 46.0 + inner_radius * numpy.sin(theta))
    )
    outer = numpy.column_stack(
        (outer_radius * numpy.cos(theta), 46.0 + outer_radius * numpy.sin(theta))
    )
    return numpy.vstack((inner, outer))


def peak_fixture(count, samples=720):
    theta = numpy.linspace(0.0, 2.0 * numpy.pi, samples, endpoint=False)
    heights = 40.0 + 3.0 * numpy.maximum(numpy.cos(count * theta), 0.0)
    return theta, heights


class QaMeasurementTest(unittest.TestCase):
    def test_candidate_version_is_derived_from_versioned_filename(self):
        path = pathlib.Path("staunton_queen_keychain_v002_candidate.3mf")
        self.assertEqual(candidate_version(path), "v002")

    def test_measure_hole_finds_3_2_mm_bore(self):
        result = measure_concentric_rings(
            concentric_fixture(1.6, 4.0), center_y=0.0, center_z=46.0
        )
        self.assertAlmostEqual(result["diameter_mm"], 3.2, delta=0.06)
        self.assertGreaterEqual(result["minimum_ligament_mm"], 2.2)

    def test_undersized_bore_becomes_blocker(self):
        measurement = measure_concentric_rings(
            concentric_fixture(1.35, 4.0), center_y=0.0, center_z=46.0
        )
        result = evaluate_hole(measurement, expected=3.2, tolerance=0.1)
        self.assertIn("hole diameter", " ".join(result["blockers"]))

    def test_missing_bore_becomes_blocker_instead_of_exception(self):
        sphere = trimesh.creation.icosphere(subdivisions=3, radius=4.0)
        sphere.apply_translation([0.0, 0.0, 46.0])
        measurement, blockers = measure_hole_or_blocker(sphere)
        self.assertEqual(measurement["diameter_mm"], 0.0)
        self.assertIn("could not identify the ring hole", " ".join(blockers))

    def test_eight_peak_detector_rejects_seven_and_nine(self):
        self.assertEqual(count_peaks_from_polar_samples(*peak_fixture(8)), 8)
        self.assertNotEqual(count_peaks_from_polar_samples(*peak_fixture(7)), 8)
        self.assertNotEqual(count_peaks_from_polar_samples(*peak_fixture(9)), 8)


if __name__ == "__main__":
    unittest.main()
