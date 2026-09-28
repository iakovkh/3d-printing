# Staunton Queen Keychain v001 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build, validate, render, and prepare for approval a one-piece 50 mm black Staunton queen with a 3.2 mm transverse key-ring hole.

**Architecture:** Blender 5.2.1 procedurally builds a parameterized body of revolution, an eight-tooth crown, and an 8 mm finial, unifies them into one manifold mesh, then cuts the exact ring hole last. A separate Python toolchain exports STL, packages an immutable one-object 3MF, reopens it for measurements and topology QA, and renders only the reopened candidate.

**Tech Stack:** Blender 5.2.1 LTS Python API, Python 3.12.14, NumPy 2.5.3, Trimesh 5.1.0, SciPy 1.18.1, Pillow 12.2.0, `unittest`, 3MF Core XML, PowerShell.

**Spec:** `docs/superpowers/specs/2026-09-23-staunton-queen-keychain-design.md`

## Global Constraints

- Read and obey `AGENTS.md`, `00_PROJECT_INSTRUCTIONS.md`, and `01_CLOUD_WORKFLOW.md` before execution.
- Full height is `50.0 ± 0.10 mm`; base diameter is `22.5 ± 0.10 mm`.
- Finial diameter is nominally `8.0 mm`; transverse clear bore is `3.2 ± 0.10 mm` along X.
- Crown has exactly eight design teeth; output is one black PLA body for a `0.4 mm` nozzle.
- Canonical source is `projects/staunton-queen-keychain/03_build/v001/staunton_queen_keychain_v001_source.blend`.
- Candidate is never overwritten; any geometry change after presentation creates `v002`.
- Final measurements and proof renders use only the independently reopened candidate 3MF.
- No release is created before the user approves the exact version and eight-character ID.
- Approved candidate bytes are copied without rebuilding; release SHA-256 must match candidate SHA-256.
- Git is not used in this project. Immutable version directories and file hashes replace commit checkpoints.
- Use the verified dependency bundle at `projects/skull-egg-cup/02_source/vendor` read-only; record its locked versions in this project.

## Review Focus

- A 3MF that silently changes from millimetres or gains a second build item must fail before QA measurements; Task 4 tests both cases.
- A bore that looks open but is undersized or blocked after round trip must produce a `BLOCKER`; Task 5 tests an undersized bore fixture and the real candidate cross-section.
- A crown with seven, nine, or poorly expressed peaks must fail source validation; Task 2 tests tooth metadata and angular peak count.
- Hidden cutters or construction meshes must never export; Task 3 tests the exact exportable-object set and Task 4 verifies one 3MF object.
- Re-running a build against an existing candidate or mutating it during QA must fail or be detected; Tasks 4 and 5 test overwrite refusal, SHA-256, and modification time stability.

---

### Task 1: Configuration and toolchain contracts

**Files:**
- Create: `projects/staunton-queen-keychain/02_source/blender/model_config.py`
- Create: `projects/staunton-queen-keychain/02_source/tests/test_model_config.py`
- Create: `projects/staunton-queen-keychain/02_source/tests/test_toolchain.py`
- Create: `projects/staunton-queen-keychain/02_source/requirements-lock.txt`
- Create: `projects/staunton-queen-keychain/02_source/toolchain.json`

**Interfaces:**
- Consumes: approved values from `projects/staunton-queen-keychain/00_brief/requirements.md`.
- Produces: immutable `ModelConfig` and exact tool/dependency versions used by all later tasks.

- [ ] **Step 1: Write failing configuration tests**

```python
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
        self.assertEqual(cfg.version, "v001")
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
```

- [ ] **Step 2: Run the tests and verify the module is missing**

```powershell
$runtimePython = 'C:\Users\user\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
& $runtimePython -m unittest 'projects\staunton-queen-keychain\02_source\tests\test_model_config.py' -v
```

Expected: non-zero exit with `ModuleNotFoundError: No module named 'model_config'`.

- [ ] **Step 3: Implement the immutable configuration**

```python
from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class ModelConfig:
    model_name: str = "staunton_queen_keychain"
    version: str = "v001"
    body_name: str = "staunton_queen_keychain_body"
    height_mm: float = 50.0
    base_diameter_mm: float = 22.5
    finial_diameter_mm: float = 8.0
    finial_center_z_mm: float = 46.0
    hole_diameter_mm: float = 3.2
    hole_axis: str = "X"
    hole_chamfer_mm: float = 0.4
    crown_teeth: int = 8
    base_z_mm: float = 0.0
    remesh_voxel_mm: float = 0.12
    dimensional_tolerance_mm: float = 0.10
    base_plane_tolerance_mm: float = 0.05
    minimum_hole_ligament_mm: float = 2.20
    lathe_profile: Sequence[tuple[float, float]] = (
        (0.00, 10.80), (0.45, 11.25), (2.40, 11.25),
        (3.20, 10.80), (4.40, 9.85), (5.60, 9.65),
        (7.80, 10.65), (9.80, 10.10), (12.20, 8.40),
        (14.50, 6.90), (18.00, 5.80), (23.50, 4.85),
        (28.20, 4.45), (30.20, 5.00), (31.30, 6.55),
        (32.70, 6.70), (34.00, 5.85), (35.60, 5.40),
    )
```

- [ ] **Step 4: Record and test the verified toolchain**

`requirements-lock.txt`:

```text
numpy==2.5.3
scipy==1.18.1
trimesh==5.1.0
lxml==6.1.3
pillow==12.2.0
networkx==3.6.1
```

`toolchain.json` records Blender `5.2.1 LTS`, runtime Python `3.12.14`, dependency versions above, the portable Blender path, and the read-only vendor path. `test_toolchain.py` loads the JSON, verifies each path exists, imports every locked package through the vendor directory, and compares `__version__` values.

- [ ] **Step 5: Run both contract suites**

```powershell
$runtimePython = 'C:\Users\user\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$env:PYTHONPATH = (Resolve-Path 'projects\skull-egg-cup\02_source\vendor')
& $runtimePython -m unittest discover -s 'projects\staunton-queen-keychain\02_source\tests' -p 'test_*.py' -v
```

Expected: configuration and toolchain tests pass. Preserve the files as the first immutable implementation checkpoint.

### Task 2: Procedural Blender geometry and source validation

**Files:**
- Create: `projects/staunton-queen-keychain/02_source/blender/geometry.py`
- Create: `projects/staunton-queen-keychain/02_source/blender/build_source.py`
- Create: `projects/staunton-queen-keychain/02_source/tests/blender_validate_source.py`
- Create: `projects/staunton-queen-keychain/03_build/v001/staunton_queen_keychain_v001_source.blend`

**Interfaces:**
- Consumes: `ModelConfig` from Task 1.
- Produces: one visible mesh named `staunton_queen_keychain_body`, hidden construction objects, and a saved canonical `.blend`.
- Geometry functions: `create_lathed_body`, `create_crown`, `create_finial`, `join_and_remesh`, `normalize_outer_dimensions`, `cut_ring_hole`, `flatten_base`, `finalize_body`.

- [ ] **Step 1: Write the failing Blender validator**

```python
import bmesh
import bpy

body = bpy.data.objects.get("staunton_queen_keychain_body")
assert body is not None, "missing staunton_queen_keychain_body"
assert body.type == "MESH"
assert abs(body.dimensions.x - 22.5) <= 0.10
assert abs(body.dimensions.y - 22.5) <= 0.10
assert abs(body.dimensions.z - 50.0) <= 0.10
assert body.get("crown_teeth") == 8
assert abs(float(body.get("hole_diameter_mm")) - 3.2) <= 0.001
assert body.get("hole_axis") == "X"

base_z = min((body.matrix_world @ vertex.co).z for vertex in body.data.vertices)
assert abs(base_z) <= 0.05

exportable = [
    obj for obj in bpy.context.scene.objects
    if obj.type == "MESH" and not bool(obj.get("no_export")) and not obj.hide_get()
]
assert exportable == [body], [obj.name for obj in exportable]

bm = bmesh.new()
bm.from_mesh(body.data)
assert not [edge for edge in bm.edges if edge.is_boundary]
assert not [edge for edge in bm.edges if not edge.is_manifold]
bm.free()
```

- [ ] **Step 2: Run the validator against a factory scene**

```powershell
& 'tools\blender-5.2.1-windows-x64\blender.exe' --background --factory-startup --python-exit-code 1 --python 'projects\staunton-queen-keychain\02_source\tests\blender_validate_source.py'
```

Expected: non-zero exit with `missing staunton_queen_keychain_body`.

- [ ] **Step 3: Implement the geometry interfaces**

`geometry.py` must expose these exact typed interfaces:

- `create_lathed_body(cfg: ModelConfig) -> bpy.types.Object`
- `create_crown(cfg: ModelConfig) -> list[bpy.types.Object]`
- `create_finial(cfg: ModelConfig) -> bpy.types.Object`
- `join_and_remesh(parts: list[bpy.types.Object], cfg: ModelConfig) -> bpy.types.Object`
- `normalize_outer_dimensions(body: bpy.types.Object, cfg: ModelConfig) -> bpy.types.Object`
- `cut_ring_hole(body: bpy.types.Object, cfg: ModelConfig) -> bpy.types.Object`
- `flatten_base(body: bpy.types.Object, cfg: ModelConfig) -> bpy.types.Object`
- `finalize_body(body: bpy.types.Object, cfg: ModelConfig) -> bpy.types.Object`

Implementation requirements:

- `create_lathed_body` revolves `cfg.lathe_profile` with 192 radial segments and closes the axis and base.
- `create_crown` creates one central dome plus eight identical thick petals at `45°` intervals. Petal tips end near `Z=43.0`, valleys near `Z=40.2`, and every petal overlaps the dome and collar by at least `0.8 mm`.
- `create_finial` creates a UV sphere of diameter `8.0 mm` centered at `Z=46.0`; its bottom overlaps the crown assembly.
- `join_and_remesh` joins outer parts, applies a voxel remesh of `0.12 mm`, and moves source operands to a hidden `construction` collection with `no_export=True`.
- `normalize_outer_dimensions` scales the unified outer body to X/Y `22.5 mm`, clips the base at `Z=0`, and ensures the sphere top reaches `Z=50.0` before the bore is cut.
- `cut_ring_hole` subtracts a 3.2 mm X-axis cylinder through the finial and two short conical entrance cutters that form 0.4 mm chamfers. Boolean solver is `EXACT`; cutters remain hidden construction objects.
- `finalize_body` applies modifiers, recalculates outward normals, removes loose vertices, sets the required custom properties, assigns one matte-black material, and leaves exactly one visible mesh.

- [ ] **Step 4: Implement the build entry point**

`build_source.py` parses `--output`, clears the factory scene, sets metric units with `scale_length = 0.001`, calls the geometry functions in the declared order, saves the `.blend`, and prints:

```python
print("SOURCE_BUILD=" + json.dumps({
    "body_name": body.name,
    "bounds_mm": [round(float(value), 4) for value in body.dimensions],
    "crown_teeth": int(body["crown_teeth"]),
    "hole_diameter_mm": float(body["hole_diameter_mm"]),
    "visible_export_bodies": 1,
}, sort_keys=True))
```

- [ ] **Step 5: Build the canonical source**

```powershell
& 'tools\blender-5.2.1-windows-x64\blender.exe' --background --factory-startup --python-exit-code 1 --python 'projects\staunton-queen-keychain\02_source\blender\build_source.py' -- --output 'projects\staunton-queen-keychain\03_build\v001\staunton_queen_keychain_v001_source.blend'
```

Expected: one source `.blend`; JSON reports `[22.5, 22.5, 50.0]` within tolerance.

- [ ] **Step 6: Validate geometry, crown, and export isolation**

Extend the validator to sample crown vertices between `Z=39.5` and `Z=43.5`, bin them into 128 angular bins, and require eight separated angular maxima above `Z=42.5`. Add negative fixture checks in the script for seven and nine synthetic peak arrays, then run:

```powershell
& 'tools\blender-5.2.1-windows-x64\blender.exe' --background 'projects\staunton-queen-keychain\03_build\v001\staunton_queen_keychain_v001_source.blend' --python-exit-code 1 --python 'projects\staunton-queen-keychain\02_source\tests\blender_validate_source.py'
```

Expected: pass; one watertight visible export body, eight detected crown peaks, correct dimensions, flat base, and hidden cutters excluded.

### Task 3: Canonical-source export

**Files:**
- Create: `projects/staunton-queen-keychain/02_source/blender/export_source.py`
- Create: `projects/staunton-queen-keychain/02_source/tests/test_export_contract.py`
- Create: `projects/staunton-queen-keychain/03_build/v001/staunton_queen_keychain_v001_body.stl`

**Interfaces:**
- Consumes: the saved canonical `.blend` from Task 2.
- Produces: one binary STL containing only `staunton_queen_keychain_body` with applied transforms and triangulation.

- [ ] **Step 1: Write the export contract test**

```python
import pathlib
import unittest
import trimesh


class ExportContractTest(unittest.TestCase):
    def test_stl_has_one_watertight_component_and_expected_envelope(self):
        root = pathlib.Path(__file__).resolve().parents[4]
        path = root / "projects/staunton-queen-keychain/03_build/v001/staunton_queen_keychain_v001_body.stl"
        mesh = trimesh.load_mesh(path, file_type="stl", process=True)
        self.assertIsInstance(mesh, trimesh.Trimesh)
        self.assertTrue(mesh.is_watertight)
        self.assertEqual(len(mesh.split(only_watertight=False)), 1)
        self.assertTrue((abs(mesh.extents - [22.5, 22.5, 50.0]) <= 0.10).all())
        self.assertAlmostEqual(float(mesh.bounds[0][2]), 0.0, delta=0.05)
```

- [ ] **Step 2: Run it before export**

Use the runtime Python and vendor path from Task 1. Expected: failure because the STL does not exist.

- [ ] **Step 3: Implement guarded Blender export**

`export_source.py` must fail unless the only visible non-`no_export` mesh is the named body. It applies transforms to an export duplicate, triangulates the duplicate, and calls:

```python
bpy.ops.wm.stl_export(
    filepath=str(output.resolve()),
    export_selected_objects=True,
    apply_modifiers=True,
    global_scale=1.0,
)
```

The canonical body remains unchanged in the saved `.blend`.

- [ ] **Step 4: Export and run the contract test**

```powershell
& 'tools\blender-5.2.1-windows-x64\blender.exe' --background 'projects\staunton-queen-keychain\03_build\v001\staunton_queen_keychain_v001_source.blend' --python-exit-code 1 --python 'projects\staunton-queen-keychain\02_source\blender\export_source.py' -- --output 'projects\staunton-queen-keychain\03_build\v001\staunton_queen_keychain_v001_body.stl'
$runtimePython = 'C:\Users\user\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$env:PYTHONPATH = (Resolve-Path 'projects\skull-egg-cup\02_source\vendor')
& $runtimePython -m unittest 'projects\staunton-queen-keychain\02_source\tests\test_export_contract.py' -v
```

Expected: pass. Preserve the STL and canonical `.blend` without overwriting.

### Task 4: Immutable 3MF candidate and package inspection

**Files:**
- Create: `projects/staunton-queen-keychain/02_source/tools/build_candidate.py`
- Create: `projects/staunton-queen-keychain/02_source/tools/inspect_3mf.py`
- Create: `projects/staunton-queen-keychain/02_source/tests/test_3mf_contract.py`
- Create: `projects/staunton-queen-keychain/03_build/v001/staunton_queen_keychain_v001_candidate.3mf`

**Interfaces:**
- Consumes: the Task 3 STL.
- Produces: a one-object millimetre 3MF, full SHA-256, short uppercase ID, and independent package metadata.
- Functions: `build_candidate(stl_path, candidate_path) -> dict`, `inspect_package(path) -> dict`.

- [ ] **Step 1: Write package and overwrite tests**

```python
def write_3mf_fixture(path, unit="millimeter", object_count=1, build_item_count=1):
    import zipfile

    objects = []
    for object_id in range(1, object_count + 1):
        objects.append(
            f'<object id="{object_id}" type="model"><mesh>'
            '<vertices><vertex x="0" y="0" z="0"/>'
            '<vertex x="1" y="0" z="0"/><vertex x="0" y="1" z="0"/></vertices>'
            '<triangles><triangle v1="0" v2="1" v3="2"/></triangles>'
            '</mesh></object>'
        )
    items = ''.join(
        f'<item objectid="{1 + (index % object_count)}"/>'
        for index in range(build_item_count)
    )
    model = (
        f'<model unit="{unit}" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">'
        f'<resources>{"".join(objects)}</resources><build>{items}</build></model>'
    )
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types xmlns=\"http://schemas.openxmlformats.org/package/2006/content-types\"/>")
        archive.writestr("_rels/.rels", "<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\"/>")
        archive.writestr("3D/3dmodel.model", model)

def test_round_trip_preserves_mm_and_one_object(self):
    mesh = trimesh.creation.box(extents=[10.0, 20.0, 30.0])
    mesh.units = "mm"
    payload = trimesh.Scene({"fixture": mesh}).export(file_type="3mf")
    with tempfile.TemporaryDirectory() as tmp:
        path = pathlib.Path(tmp) / "fixture.3mf"
        path.write_bytes(payload)
        info = inspect_package(path)
        self.assertEqual(info["unit"], "millimeter")
        self.assertEqual(info["object_count"], 1)
        self.assertEqual(info["build_item_count"], 1)

def test_refuses_existing_candidate(self):
    with tempfile.TemporaryDirectory() as tmp:
        target = pathlib.Path(tmp) / "existing.3mf"
        target.write_bytes(b"sentinel")
        with self.assertRaises(FileExistsError):
            build_candidate(pathlib.Path(tmp) / "unused.stl", target)
        self.assertEqual(target.read_bytes(), b"sentinel")

def test_inspector_rejects_two_build_items(self):
    with tempfile.TemporaryDirectory() as tmp:
        path = pathlib.Path(tmp) / "two-items.3mf"
        write_3mf_fixture(path, build_item_count=2)
        with self.assertRaisesRegex(ValueError, "one object and one build item"):
            inspect_package(path)

def test_inspector_rejects_inches(self):
    with tempfile.TemporaryDirectory() as tmp:
        path = pathlib.Path(tmp) / "inches.3mf"
        write_3mf_fixture(path, unit="inch")
        with self.assertRaisesRegex(ValueError, "expected 'millimeter'"):
            inspect_package(path)
```

- [ ] **Step 2: Run and confirm imports fail**

Run the single test module with the runtime Python and vendor path. Expected: failure because candidate tools do not exist.

- [ ] **Step 3: Implement candidate assembly**

`build_candidate.py` loads exactly one STL mesh with `process=False`, merges duplicate vertices, removes unreferenced vertices, sets `units="mm"`, names it `staunton_queen_keychain_body`, exports one-scene 3MF bytes, refuses overwrite, and returns:

```python
{
    "candidate": str(candidate_path.resolve()),
    "sha256": digest,
    "short_id": digest[:8].upper(),
    "bytes": len(payload),
    "geometry_count": 1,
    "vertex_count": int(len(mesh.vertices)),
    "triangle_count": int(len(mesh.faces)),
    "bounds_mm": [round(float(value), 4) for value in scene.extents],
}
```

- [ ] **Step 4: Implement independent ZIP/XML inspection**

`inspect_3mf.py` uses only `zipfile` and `xml.etree.ElementTree`, requires `[Content_Types].xml`, `_rels/.rels`, and `3D/3dmodel.model`, verifies `unit="millimeter"`, exactly one resource object, and exactly one build item. It returns object, vertex, triangle, and build-item counts.

- [ ] **Step 5: Pass the fixture tests and build the candidate once**

```powershell
$runtimePython = 'C:\Users\user\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$env:PYTHONPATH = (Resolve-Path 'projects\skull-egg-cup\02_source\vendor')
& $runtimePython -m unittest 'projects\staunton-queen-keychain\02_source\tests\test_3mf_contract.py' -v
& $runtimePython 'projects\staunton-queen-keychain\02_source\tools\build_candidate.py' --stl 'projects\staunton-queen-keychain\03_build\v001\staunton_queen_keychain_v001_body.stl' --output 'projects\staunton-queen-keychain\03_build\v001\staunton_queen_keychain_v001_candidate.3mf'
& $runtimePython 'projects\staunton-queen-keychain\02_source\tools\inspect_3mf.py' 'projects\staunton-queen-keychain\03_build\v001\staunton_queen_keychain_v001_candidate.3mf'
```

Expected: all tests pass; one immutable candidate exists; record its SHA-256 and short ID.

### Task 5: Reopened-candidate geometric QA

**Files:**
- Create: `projects/staunton-queen-keychain/02_source/tools/qa_candidate.py`
- Create: `projects/staunton-queen-keychain/02_source/tests/test_qa_measurements.py`
- Create: `projects/staunton-queen-keychain/04_review/v001/reopened_body.stl`
- Create: `projects/staunton-queen-keychain/04_review/v001/staunton_queen_keychain_v001_qa.json`
- Create: `projects/staunton-queen-keychain/04_review/v001/staunton_queen_keychain_v001_qa.md`

**Interfaces:**
- Consumes: only the candidate 3MF plus approved numeric requirements.
- Produces: reopened STL, structured QA, human-readable QA, immutable hash evidence.
- Functions: `load_candidate_mesh`, `measure_cross_section_loops`, `measure_concentric_rings`, `measure_hole`, `evaluate_hole`, `measure_base`, `count_peaks_from_polar_samples`, `count_crown_peaks`, `run_qa`.

- [ ] **Step 1: Write measurement fixture tests**

Create analytic fixtures with Trimesh and test:

```python
def concentric_fixture(inner_radius, outer_radius, count=128):
    theta = numpy.linspace(0.0, 2.0 * numpy.pi, count, endpoint=False)
    inner = numpy.column_stack((inner_radius * numpy.cos(theta), 46.0 + inner_radius * numpy.sin(theta)))
    outer = numpy.column_stack((outer_radius * numpy.cos(theta), 46.0 + outer_radius * numpy.sin(theta)))
    return numpy.vstack((inner, outer))

def peak_fixture(count, samples=720):
    theta = numpy.linspace(0.0, 2.0 * numpy.pi, samples, endpoint=False)
    heights = 40.0 + 3.0 * numpy.maximum(numpy.cos(count * theta), 0.0)
    return theta, heights

def test_measure_hole_finds_3_2_mm_bore(self):
    result = measure_concentric_rings(concentric_fixture(1.6, 4.0), center_y=0.0, center_z=46.0)
    self.assertAlmostEqual(result["diameter_mm"], 3.2, delta=0.06)
    self.assertGreaterEqual(result["minimum_ligament_mm"], 2.2)

def test_undersized_bore_becomes_blocker(self):
    measurement = measure_concentric_rings(concentric_fixture(1.35, 4.0), center_y=0.0, center_z=46.0)
    result = evaluate_hole(measurement, expected=3.2, tolerance=0.1)
    self.assertIn("hole diameter", " ".join(result["blockers"]))

def test_eight_peak_detector_rejects_seven_and_nine(self):
    self.assertEqual(count_peaks_from_polar_samples(*peak_fixture(8)), 8)
    self.assertNotEqual(count_peaks_from_polar_samples(*peak_fixture(7)), 8)
    self.assertNotEqual(count_peaks_from_polar_samples(*peak_fixture(9)), 8)
```

The real candidate test additionally calls `measure_hole` on mesh-plane segments from the reopened 3MF, so the synthetic-ring unit test cannot mask a closed or malformed production bore.

- [ ] **Step 2: Run tests before implementing QA**

Expected: import failure for `qa_candidate`.

- [ ] **Step 3: Implement candidate loading and physical measurements**

`load_candidate_mesh` loads the 3MF as a scene, requires one geometry instance, applies its transform, and returns one merged `trimesh.Trimesh`.

`measure_cross_section_loops` calls `trimesh.intersections.mesh_plane` at the finial centre with plane normal X, joins segment endpoints within `0.03 mm`, and classifies concentric loops by median radius. The inner loop gives bore diameter; the outer loop gives finial radius and remaining ligament. No configured diameter is copied into the measurement result.

`measure_base` uses vertices within `0.20 mm` of minimum Z to calculate radial diameter and maximum deviation from the base plane. `count_crown_peaks` samples the angular height envelope in the crown band, smooths it circularly, and counts separated local maxima.

- [ ] **Step 4: Implement the typed QA result and blockers**

```python
class QaResult(TypedDict):
    sha256: str
    short_id: str
    bounds_mm: list[float]
    body_count: int
    watertight: bool
    winding_consistent: bool
    euler_number: int
    degenerate_face_count: int
    connected_component_count: int
    base_diameter_mm: float
    hole_diameter_mm: float
    finial_outer_diameter_mm: float
    minimum_hole_ligament_mm: float
    crown_peak_count: int
    base_plane_error_mm: float
    blockers: list[str]
    warnings: list[str]
```

Blockers enforce body count one, watertight and winding-consistent mesh, no degenerates, one connected component, bounds `[22.5, 22.5, 50.0] ± 0.10 mm`, bore `3.2 ± 0.10 mm`, ligament at least `2.2 mm`, eight crown peaks, and base-plane error at most `0.05 mm`. Warnings cover the horizontal bore bridge, crown overhangs, and unverified slicer behaviour.

- [ ] **Step 5: Run real-candidate QA without mutating the candidate**

```powershell
$runtimePython = 'C:\Users\user\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$env:PYTHONPATH = (Resolve-Path 'projects\skull-egg-cup\02_source\vendor')
$candidate = 'projects\staunton-queen-keychain\03_build\v001\staunton_queen_keychain_v001_candidate.3mf'
$beforeHash = (Get-FileHash -Algorithm SHA256 $candidate).Hash
$beforeTime = (Get-Item $candidate).LastWriteTimeUtc
& $runtimePython -m unittest 'projects\staunton-queen-keychain\02_source\tests\test_qa_measurements.py' -v
& $runtimePython 'projects\staunton-queen-keychain\02_source\tools\qa_candidate.py' --candidate $candidate --review-dir 'projects\staunton-queen-keychain\04_review\v001'
$afterHash = (Get-FileHash -Algorithm SHA256 $candidate).Hash
$afterTime = (Get-Item $candidate).LastWriteTimeUtc
if ($beforeHash -ne $afterHash -or $beforeTime -ne $afterTime) { throw 'candidate mutated during QA' }
```

Expected: tests pass, QA exits zero only with no blockers, reopened STL and reports exist, and candidate bytes/time remain unchanged.

### Task 6: Proof renders from the reopened candidate

**Files:**
- Create: `projects/staunton-queen-keychain/02_source/blender/render_reopened.py`
- Create: `projects/staunton-queen-keychain/02_source/tools/make_proof_sheet.py`
- Create: `projects/staunton-queen-keychain/02_source/tests/test_preview_traceability.py`
- Create: `projects/staunton-queen-keychain/04_review/v001/previews/*.png`

**Interfaces:**
- Consumes: only `04_review/v001/reopened_body.stl` and QA JSON.
- Produces: labeled front, back, side, top, isometric, detail, dimensions, parts-colors, and proof-sheet PNGs.

- [ ] **Step 1: Write preview traceability tests**

```python
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
QA_PATH = ROOT / "projects/staunton-queen-keychain/04_review/v001/staunton_queen_keychain_v001_qa.json"
PREVIEW_DIR = ROOT / "projects/staunton-queen-keychain/04_review/v001/previews"

REQUIRED = {
    "front", "back", "side", "top", "isometric",
    "detail", "dimensions", "parts-colors", "proof-sheet",
}

def test_every_preview_matches_qa_identity(self):
    qa = json.loads(QA_PATH.read_text(encoding="utf-8"))
    for kind in REQUIRED:
        path = PREVIEW_DIR / f"staunton_queen_keychain_v001_{kind}.png"
        self.assertTrue(path.is_file(), path)
        with Image.open(path) as image:
            self.assertEqual(image.info["version"], "v001")
            self.assertEqual(image.info["short_id"], qa["short_id"])
            self.assertEqual(image.info["sha256"], qa["sha256"])
```

- [ ] **Step 2: Run before rendering**

Expected: failure listing missing PNGs.

- [ ] **Step 3: Implement reopened-mesh rendering**

`render_reopened.py` starts from factory startup, imports only `reopened_body.stl`, assigns a rough matte-black material, creates a neutral floor and three-area-light rig, and renders orthographic cameras:

```python
VIEWS = {
    "front": (0.0, -1.0, 0.08),
    "back": (0.0, 1.0, 0.08),
    "side": (1.0, 0.0, 0.08),
    "top": (0.0, 0.0, 1.0),
    "isometric": (1.0, -1.0, 0.75),
    "detail": (1.0, -1.0, 0.25),
}
```

The detail camera crops to the crown and bore. The renderer never opens the canonical `.blend`.

- [ ] **Step 4: Implement labels and proof sheets**

`make_proof_sheet.py` uses Pillow to add model, version, ID, view name, and full PNG metadata to each raw render. The dimensions sheet lists measured X/Y/Z, base diameter, bore diameter, finial outer diameter, ligament, crown peaks, and base error from QA JSON. The parts-colors sheet states `1 body / black PLA / 0.4 mm nozzle / ring not included`. The proof sheet combines all views without substituting generated concept art.

- [ ] **Step 5: Render and verify all proof assets**

```powershell
& 'tools\blender-5.2.1-windows-x64\blender.exe' --background --factory-startup --python-exit-code 1 --python 'projects\staunton-queen-keychain\02_source\blender\render_reopened.py' -- --mesh 'projects\staunton-queen-keychain\04_review\v001\reopened_body.stl' --qa 'projects\staunton-queen-keychain\04_review\v001\staunton_queen_keychain_v001_qa.json' --output-dir 'projects\staunton-queen-keychain\04_review\v001\previews'
$runtimePython = 'C:\Users\user\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$env:PYTHONPATH = (Resolve-Path 'projects\skull-egg-cup\02_source\vendor')
& $runtimePython 'projects\staunton-queen-keychain\02_source\tools\make_proof_sheet.py' --qa 'projects\staunton-queen-keychain\04_review\v001\staunton_queen_keychain_v001_qa.json' --preview-dir 'projects\staunton-queen-keychain\04_review\v001\previews'
& $runtimePython -m unittest 'projects\staunton-queen-keychain\02_source\tests\test_preview_traceability.py' -v
```

Expected: all required images exist and carry the exact candidate version, ID, and SHA-256.

### Task 7: User review gate and version loop

**Files:**
- Read: `projects/staunton-queen-keychain/04_review/v001/staunton_queen_keychain_v001_qa.md`
- Read: `projects/staunton-queen-keychain/04_review/v001/previews/*.png`
- Do not create: `projects/staunton-queen-keychain/05_release/v001/*`

**Interfaces:**
- Consumes: proof sheet and blocker-free QA.
- Produces: either explicit approval of `v001` plus its actual ID, or a change request that starts `v002`.

- [ ] **Step 1: Recheck review readiness**

Read QA JSON and assert `blockers == []`, required preview metadata matches, and the candidate hash still equals QA `sha256`.

- [ ] **Step 2: Present evidence in chat**

Show the proof sheet and individual detail/dimension views directly in chat. Report measured dimensions, topology results, one-body count, hole ligament, and every warning. Call the file a candidate, not final.

- [ ] **Step 3: Request exact approval**

Use the actual short ID in this form:

```text
Утверждаю staunton_queen_keychain v001, ID 1234ABCD.
```

- [ ] **Step 4: Route changes without overwrite**

If the user requests a geometry, size, colour, or part change, create `03_build/v002` and `04_review/v002`, update only `ModelConfig.version`, make the requested canonical-source change, and repeat Tasks 2–7. Preserve every `v001` artifact unchanged.

### Task 8: Approval-gated immutable release

**Files:**
- Create after approval: `projects/staunton-queen-keychain/02_source/tools/release_candidate.py`
- Create after approval: `projects/staunton-queen-keychain/02_source/tests/test_release_identity.py`
- Create after approval: `projects/staunton-queen-keychain/05_release/v001/*`

**Interfaces:**
- Consumes: explicit approval of the exact candidate version and ID.
- Produces: byte-identical `geometry.3mf`, source snapshot, exchange STL, previews, requirements, QA, print notes, and release manifest.

- [ ] **Step 1: Write the identity test after approval**

```python
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
CANDIDATE = ROOT / "projects/staunton-queen-keychain/03_build/v001/staunton_queen_keychain_v001_candidate.3mf"
RELEASE_3MF = ROOT / "projects/staunton-queen-keychain/05_release/v001/staunton_queen_keychain_v001_geometry.3mf"
QA_JSON = ROOT / "projects/staunton-queen-keychain/04_review/v001/staunton_queen_keychain_v001_qa.json"

def test_release_is_byte_identical_to_approved_candidate(self):
    digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    self.assertEqual(digest(CANDIDATE), digest(RELEASE_3MF))
    qa = json.loads(QA_JSON.read_text(encoding="utf-8"))
    self.assertEqual(digest(RELEASE_3MF), qa["sha256"])
```

- [ ] **Step 2: Verify it fails before release exists**

Expected: failure because `staunton_queen_keychain_v001_geometry.3mf` does not exist.

- [ ] **Step 3: Implement approval-gated copying**

`release_candidate.py` requires `--approved-version v001` and the exact eight-character `--approved-id`. It verifies both against QA JSON, refuses a non-empty release directory, copies candidate bytes without rebuilding, copies the approved source/requirements/STL/QA/previews, and writes a manifest containing tool versions, measured bounds, parts, material, canonical path, every file hash, candidate SHA-256, release SHA-256, and short ID.

- [ ] **Step 4: Write print notes**

Record upright orientation, black PLA, 0.4 mm nozzle, the horizontal-bore bridge warning, crown-overhang warning, ring-not-included statement, and the requirement that the user inspect supports and layers in Anycubic Slicer Next.

- [ ] **Step 5: Create and verify the release only after exact approval**

```powershell
$runtimePython = 'C:\Users\user\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$env:PYTHONPATH = (Resolve-Path 'projects\skull-egg-cup\02_source\vendor')
$qa = Get-Content -Raw 'projects\staunton-queen-keychain\04_review\v001\staunton_queen_keychain_v001_qa.json' | ConvertFrom-Json
$approvedId = $qa.short_id
& $runtimePython 'projects\staunton-queen-keychain\02_source\tools\release_candidate.py' --approved-version v001 --approved-id $approvedId --project 'projects\staunton-queen-keychain'
& $runtimePython -m unittest 'projects\staunton-queen-keychain\02_source\tests\test_release_identity.py' -v
```

Run the command only after the user has approved the same `$approvedId` displayed in the proof sheet.

- [ ] **Step 6: Final readback and handoff**

Independently reopen the release 3MF, compare object count and bounds to QA JSON, verify the release folder contains no mixed versions, list hashes, and hand off `staunton_queen_keychain_v001_geometry.3mf` for import into Anycubic Slicer Next.
