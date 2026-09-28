# Skull Egg Cup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Создать, проверить и выпустить геометрический 3MF монолитной детализированной кокотницы-черепа для одного варёного яйца.

**Architecture:** Blender 5.2.1 LTS формирует канонический органический `.blend` из параметрической функциональной основы и управляемых скульптурных операций. Blender экспортирует одно STL-тело, а отдельный Python-контур на базе Trimesh собирает и повторно открывает 3MF, выполняет независимые проверки ZIP/XML и геометрический QA. Контрольные изображения строятся только из сетки, повторно открытой из кандидатного 3MF.

**Tech Stack:** Blender 5.2.1 LTS Portable, Blender Python API, Python 3.12, NumPy 2.5.3, SciPy 1.18.1, Trimesh 5.1.0, lxml 6.1.3, Pillow 12.2.0, PowerShell.

**Spec:** `docs/superpowers/specs/2026-09-17-skull-egg-cup-design.md`

## Global Constraints

- Принтер: Anycubic Kobra S1 Combo; слайсер: Anycubic Slicer Next.
- Единицы: миллиметры; материал: стандартный PLA; сопло: 0,4 мм.
- Расчётное яйцо: 45 × 58 мм.
- Верхнее отверстие: 42,0 ± 0,2 мм; глубина чаши: 22,0 ± 0,2 мм.
- Минимальная стенка: 2,4 мм; минимальный значимый рельеф: 0,8 мм.
- Ориентировочный внешний габарит: 78 × 88 × 72 мм; отклонение до 2 мм допустимо только ради устойчивости или стенки.
- Одно связное, замкнутое, manifold-тело; один цвет; без отдельных вставок.
- Проверочные изображения создаются только из повторно открытого `candidate.3mf`.
- Показанная версия не перезаписывается; любая геометрическая правка получает следующий номер.
- Выпускной 3MF должен побитово совпасть с утверждённым кандидатом.
- Git не используется; контрольные точки фиксируются версиями файлов и отчётами.
- Температурный риск PLA принят пользователем и фиксируется как `WARNING`.

## File Map

```text
projects/skull-egg-cup/
├── 00_brief/
│   ├── original_request.md
│   └── requirements.md
├── 01_concept/
│   ├── skull_egg_cup_v001_concept.svg
│   └── skull_egg_cup_v001_concept-preview.png
├── 02_source/
│   ├── requirements-lock.txt
│   ├── toolchain.json
│   ├── source-manifest.json
│   ├── vendor/
│   ├── blender/
│   │   ├── model_config.py
│   │   ├── geometry_core.py
│   │   ├── skull_features.py
│   │   ├── build_source.py
│   │   ├── export_source.py
│   │   └── render_reopened.py
│   ├── tools/
│   │   ├── build_candidate.py
│   │   ├── inspect_3mf.py
│   │   ├── qa_candidate.py
│   │   ├── make_proof_sheet.py
│   │   └── release_candidate.py
│   └── tests/
│       ├── test_model_config.py
│       ├── test_3mf_contract.py
│       └── test_release_identity.py
├── 03_build/v001/
│   ├── skull_egg_cup_v001_source.blend
│   ├── skull_egg_cup_v001_body.stl
│   └── skull_egg_cup_v001_candidate.3mf
├── 04_review/v001/
│   ├── reopened_body.stl
│   ├── skull_egg_cup_v001_qa.json
│   ├── skull_egg_cup_v001_qa.md
│   └── previews/
└── 05_release/v001/
```

## Spec Coverage Map

- Цель, классификация `HYBRID` и границы проекта: Tasks 2–9.
- Подтверждённые размеры и расчётное яйцо: Tasks 2, 3 и 6.
- Конструкция одного монолитного тела: Tasks 3–6.
- Художественное направление B и анатомические признаки: Task 4.
- PLA, вертикальная ориентация и печатные предупреждения: Tasks 4, 6, 8 и 9.
- Канонический Blender-исходник: Tasks 1–4.
- Версионный кандидатный 3MF и SHA-256 ID: Tasks 5–6.
- Повторное открытие и геометрический QA: Task 6.
- Проверочные изображения `front` (вид спереди), `back` (вид сзади), `side` (вид сбоку), `top` (вид сверху), изометрия, размерный лист и легенда: Task 7.
- Пользовательское утверждение версии и ID: Task 8.
- Побитово идентичный неизменяемый выпуск и передача в Anycubic Slicer Next: Task 9.

---

### Task 1: Reproducible local toolchain

**Files:**
- Create: `projects/skull-egg-cup/02_source/requirements-lock.txt`
- Create: `projects/skull-egg-cup/02_source/toolchain.json`
- Create: `projects/skull-egg-cup/02_source/tests/test_toolchain.py`
- Create: `tools/blender-5.2.1-windows-x64/` from the verified official portable archive.

**Interfaces:**
- Consumes: official Blender 5.2.1 LTS Windows x64 ZIP and its published SHA-256 list.
- Produces: `tools/blender-5.2.1-windows-x64/blender.exe`, importable Python dependencies under `02_source/vendor`, and machine-readable `toolchain.json`.

- [ ] **Step 1: Record the pinned Python dependency set**

```text
numpy==2.5.3
scipy==1.18.1
trimesh==5.1.0
lxml==6.1.3
pillow==12.2.0
```

- [ ] **Step 2: Write a failing toolchain test**

```python
import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[4]
PROJECT = ROOT / "projects" / "skull-egg-cup"

class ToolchainTest(unittest.TestCase):
    def test_blender_and_vendor_are_available(self):
        blender = ROOT / "tools" / "blender-5.2.1-windows-x64" / "blender.exe"
        self.assertTrue(blender.is_file())
        data = json.loads((PROJECT / "02_source" / "toolchain.json").read_text("utf-8"))
        self.assertEqual(data["blender"], "5.2.1 LTS")
        self.assertEqual(data["python"], "3.12")
        import numpy, scipy, trimesh, lxml, PIL
        self.assertEqual(numpy.__version__, "2.5.3")
        self.assertEqual(scipy.__version__, "1.18.1")
        self.assertEqual(trimesh.__version__, "5.1.0")
        self.assertEqual(lxml.__version__, "6.1.3")
        self.assertEqual(PIL.__version__, "12.2.0")
```

- [ ] **Step 3: Run the test and verify it fails before installation**

Run:

```powershell
python -m unittest projects\skull-egg-cup\02_source\tests\test_toolchain.py -v
```

Expected: `FAIL` because `blender.exe` and `toolchain.json` do not exist.

- [ ] **Step 4: Download and verify Blender 5.2.1 LTS Portable**

Download only after the user approves the network operation:

```powershell
$downloadDir = 'tools\downloads'
New-Item -ItemType Directory -Force $downloadDir | Out-Null
Invoke-WebRequest 'https://download.blender.org/release/Blender5.2/blender-5.2.1-windows-x64.zip' -OutFile "$downloadDir\blender-5.2.1-windows-x64.zip"
Invoke-WebRequest 'https://download.blender.org/release/Blender5.2/blender-5.2.1.sha256' -OutFile "$downloadDir\blender-5.2.1.sha256"
$actual = (Get-FileHash "$downloadDir\blender-5.2.1-windows-x64.zip" -Algorithm SHA256).Hash.ToUpperInvariant()
$line = (Select-String -Path "$downloadDir\blender-5.2.1.sha256" -Pattern 'blender-5.2.1-windows-x64.zip$').Line
$published = ($line -split '\s+')[0].ToUpperInvariant()
if ($actual -ne $published) { throw "Blender SHA-256 mismatch: $actual != $published" }
Expand-Archive "$downloadDir\blender-5.2.1-windows-x64.zip" -DestinationPath 'tools' -Force
```

Expected: no exception; the archive expands to `tools/blender-5.2.1-windows-x64/`.

- [ ] **Step 5: Install pinned Python packages into the project-local vendor directory**

```powershell
python -m pip install --target 'projects\skull-egg-cup\02_source\vendor' -r 'projects\skull-egg-cup\02_source\requirements-lock.txt'
```

- [ ] **Step 6: Create `toolchain.json` from actual version output**

```json
{
  "blender": "5.2.1 LTS",
  "blender_distribution": "official portable windows-x64",
  "python": "3.12",
  "numpy": "2.5.3",
  "scipy": "1.18.1",
  "trimesh": "5.1.0",
  "lxml": "6.1.3",
  "pillow": "12.2.0"
}
```

- [ ] **Step 7: Run the toolchain test and Blender smoke test**

```powershell
$env:PYTHONPATH = (Resolve-Path 'projects\skull-egg-cup\02_source\vendor')
python -m unittest projects\skull-egg-cup\02_source\tests\test_toolchain.py -v
& 'tools\blender-5.2.1-windows-x64\blender.exe' --background --factory-startup --python-expr "import bpy; assert bpy.app.version_string.startswith('5.2.1'); print(bpy.app.version_string)"
```

Expected: one Python test passes and Blender exits with code `0` while printing `5.2.1`.

### Task 2: Dimension contract and source manifest

**Files:**
- Create: `projects/skull-egg-cup/02_source/blender/model_config.py`
- Create: `projects/skull-egg-cup/02_source/source-manifest.json`
- Create: `projects/skull-egg-cup/02_source/tests/test_model_config.py`

**Interfaces:**
- Produces: immutable `ModelConfig` values consumed by Blender generation, QA, proof sheets, and release manifest.

- [ ] **Step 1: Write failing dimension-contract tests**

```python
import importlib.util
import pathlib
import unittest

CONFIG_PATH = pathlib.Path(__file__).resolve().parents[1] / "blender" / "model_config.py"

class ModelConfigTest(unittest.TestCase):
    def test_v001_contract(self):
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
```

- [ ] **Step 2: Verify the test fails because the config module is absent**

Run:

```powershell
python -m unittest projects\skull-egg-cup\02_source\tests\test_model_config.py -v
```

Expected: import failure for `model_config.py`.

- [ ] **Step 3: Implement the frozen configuration object**

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class ModelConfig:
    name: str = "skull_egg_cup"
    version: str = "v001"
    egg_diameter_mm: float = 45.0
    egg_height_mm: float = 58.0
    opening_diameter_mm: float = 42.0
    cavity_depth_mm: float = 22.0
    min_wall_mm: float = 2.4
    min_relief_mm: float = 0.8
    target_width_mm: float = 78.0
    target_depth_mm: float = 88.0
    target_height_mm: float = 72.0
    dimension_tolerance_mm: float = 0.2
    envelope_tolerance_mm: float = 2.0
    body_count: int = 1

CONFIG = ModelConfig()
```

- [ ] **Step 4: Create the source manifest with one canonical Blender source**

```json
{
  "model": "skull_egg_cup",
  "version": "v001",
  "classification": "HYBRID",
  "units": "millimeter",
  "canonical_source": "../03_build/v001/skull_egg_cup_v001_source.blend",
  "body": {
    "name": "skull_egg_cup_body",
    "color_role": "single_spool_color",
    "transform": {"translation_mm": [0, 0, 0], "rotation_deg": [0, 0, 0], "scale": [1, 1, 1]}
  },
  "protected_geometry": {
    "opening_diameter_mm": 42.0,
    "cavity_depth_mm": 22.0,
    "minimum_wall_mm": 2.4,
    "base_plane_z_mm": 0.0
  }
}
```

- [ ] **Step 5: Run the contract test**

Expected: all assertions pass.

### Task 3: Functional core and printable envelope

**Files:**
- Create: `projects/skull-egg-cup/02_source/blender/geometry_core.py`
- Create: `projects/skull-egg-cup/02_source/blender/build_source.py`
- Create: `projects/skull-egg-cup/02_source/tests/blender_validate_core.py`
- Create: `projects/skull-egg-cup/03_build/v001/skull_egg_cup_v001_core.blend`

**Interfaces:**
- Consumes: `model_config.CONFIG`.
- Produces: Blender object `skull_egg_cup_body`, helper object `egg_reference_no_export`, and JSON measurement report printed to stdout.

- [ ] **Step 1: Write the Blender-side failing validator**

```python
import bpy

body = bpy.data.objects.get("skull_egg_cup_body")
assert body is not None, "missing skull_egg_cup_body"
assert body.type == "MESH"
assert abs(body.dimensions.x - 78.0) <= 2.0
assert abs(body.dimensions.y - 88.0) <= 2.0
assert body.dimensions.z >= 70.0
base_z = min((body.matrix_world @ v.co).z for v in body.data.vertices)
assert abs(base_z) <= 0.05
```

- [ ] **Step 2: Run the validator against an empty factory scene**

```powershell
& 'tools\blender-5.2.1-windows-x64\blender.exe' --background --factory-startup --python-exit-code 1 --python 'projects\skull-egg-cup\02_source\tests\blender_validate_core.py'
```

Expected: non-zero exit with `missing skull_egg_cup_body`.

- [ ] **Step 3: Implement functional primitives**

`geometry_core.py` must provide these exact interfaces:

- `create_egg_reference(cfg: ModelConfig) -> bpy.types.Object`
- `create_outer_cranium(cfg: ModelConfig) -> bpy.types.Object`
- `create_face_and_jaw(cfg: ModelConfig) -> list[bpy.types.Object]`
- `create_cavity_cutter(cfg: ModelConfig) -> bpy.types.Object`
- `boolean_union(objects: list[bpy.types.Object], result_name: str) -> bpy.types.Object`
- `boolean_difference(body: bpy.types.Object, cutters: list[bpy.types.Object]) -> bpy.types.Object`
- `flatten_base(body: bpy.types.Object, z_mm: float = 0.0) -> bpy.types.Object`
- `measure_opening_and_depth(body: bpy.types.Object, cfg: ModelConfig) -> dict[str, float]`

Use ellipsoidal cranial and facial volumes, a widened jaw volume, exact egg/cavity cutters, voxel remesh no coarser than `0.45 mm`, and a base cut at `Z=0`. Boolean operands stay in a hidden `construction` collection and never export.

- [ ] **Step 4: Implement the build entry point**

`build_source.py` must clear the factory scene, call the geometry functions, name the single export body `skull_egg_cup_body`, set units to millimetres, save `skull_egg_cup_v001_core.blend`, and print a JSON object containing `bounds_mm`, `opening_diameter_mm`, `cavity_depth_mm`, and `body_count`.

- [ ] **Step 5: Build the functional core**

```powershell
& 'tools\blender-5.2.1-windows-x64\blender.exe' --background --factory-startup --python-exit-code 1 --python 'projects\skull-egg-cup\02_source\blender\build_source.py' -- --stage core --output 'projects\skull-egg-cup\03_build\v001\skull_egg_cup_v001_core.blend'
```

- [ ] **Step 6: Validate the saved core scene**

```powershell
& 'tools\blender-5.2.1-windows-x64\blender.exe' --background 'projects\skull-egg-cup\03_build\v001\skull_egg_cup_v001_core.blend' --python-exit-code 1 --python 'projects\skull-egg-cup\02_source\tests\blender_validate_core.py'
```

Expected: exit code `0`; one export body; flat base; envelope within the approved tolerance.

### Task 4: Anatomical skull detailing and canonical source

**Files:**
- Create: `projects/skull-egg-cup/02_source/blender/skull_features.py`
- Modify: `projects/skull-egg-cup/02_source/blender/build_source.py`
- Create: `projects/skull-egg-cup/02_source/tests/blender_validate_source.py`
- Create: `projects/skull-egg-cup/03_build/v001/skull_egg_cup_v001_source.blend`

**Interfaces:**
- Consumes: the functional core and protected cavity dimensions.
- Produces: the canonical Blender source with exactly one visible export body and printable relief.

- [ ] **Step 1: Extend the failing validator with feature and topology checks**

```python
import bmesh
import bpy

body = bpy.data.objects["skull_egg_cup_body"]
mesh = body.data
bm = bmesh.new()
bm.from_mesh(mesh)
boundary = [edge for edge in bm.edges if edge.is_boundary]
non_manifold = [edge for edge in bm.edges if not edge.is_manifold]
assert not boundary, f"boundary edges: {len(boundary)}"
assert not non_manifold, f"non-manifold edges: {len(non_manifold)}"
for feature in ("brow_ridge", "left_eye_socket", "right_eye_socket", "nasal_cavity", "teeth_relief", "cranial_sutures"):
    assert feature in body, f"missing feature marker {feature}"
bm.free()
```

- [ ] **Step 2: Implement printable skull features**

`skull_features.py` must provide these exact interfaces:

- `carve_eye_sockets(body: bpy.types.Object, cfg: ModelConfig) -> bpy.types.Object`
- `carve_nasal_cavity(body: bpy.types.Object, cfg: ModelConfig) -> bpy.types.Object`
- `shape_brow_and_cheekbones(body: bpy.types.Object, cfg: ModelConfig) -> bpy.types.Object`
- `add_fused_teeth_relief(body: bpy.types.Object, cfg: ModelConfig) -> bpy.types.Object`
- `engrave_cranial_sutures(body: bpy.types.Object, cfg: ModelConfig) -> bpy.types.Object`
- `add_bone_microrelief(body: bpy.types.Object, cfg: ModelConfig, amplitude_mm: float = 0.35) -> bpy.types.Object`
- `restore_protected_cavity(body: bpy.types.Object, cfg: ModelConfig) -> bpy.types.Object`
- `finalize_manifold(body: bpy.types.Object, voxel_mm: float = 0.35) -> bpy.types.Object`

Eye and nasal cavities are real shallow Boolean recesses. Teeth remain fused to the jaw and have grooves at least `0.8 mm` wide/deep. Sutures are shallow engravings at least `0.8 mm` wide. Microrelief amplitude stays below `0.35 mm` and is masked away from the bowl, rim, and base.

Each feature function must set the corresponding Boolean custom property on the final body, for example `body["left_eye_socket"] = True`; the validator reads those properties instead of inferring artistic intent from object names.

- [ ] **Step 3: Build the complete v001 canonical source**

```powershell
& 'tools\blender-5.2.1-windows-x64\blender.exe' --background --factory-startup --python-exit-code 1 --python 'projects\skull-egg-cup\02_source\blender\build_source.py' -- --stage final --output 'projects\skull-egg-cup\03_build\v001\skull_egg_cup_v001_source.blend'
```

- [ ] **Step 4: Run Blender topology and feature validation**

```powershell
& 'tools\blender-5.2.1-windows-x64\blender.exe' --background 'projects\skull-egg-cup\03_build\v001\skull_egg_cup_v001_source.blend' --python-exit-code 1 --python 'projects\skull-egg-cup\02_source\tests\blender_validate_source.py'
```

Expected: exit code `0`; no boundary or non-manifold edges; all feature markers present.

- [ ] **Step 5: Render a non-approval draft for internal comparison with concept B**

Create front, side, back, and isometric draft PNGs from the `.blend` under `03_build/v001/draft/`. Label each image `ЧЕРНОВОЙ РЕНДЕР ИСХОДНИКА — НЕ ДЛЯ УТВЕРЖДЕНИЯ`. Check that the real geometry contains the chosen brow, sockets, nasal cavity, cheekbones, teeth, sutures, and back-of-skull detail before continuing.

### Task 5: Export the body and build the candidate 3MF

**Files:**
- Create: `projects/skull-egg-cup/02_source/blender/export_source.py`
- Create: `projects/skull-egg-cup/02_source/tools/build_candidate.py`
- Create: `projects/skull-egg-cup/02_source/tests/test_3mf_contract.py`
- Create: `projects/skull-egg-cup/03_build/v001/skull_egg_cup_v001_body.stl`
- Create: `projects/skull-egg-cup/03_build/v001/skull_egg_cup_v001_candidate.3mf`

**Interfaces:**
- Consumes: canonical `.blend` with object `skull_egg_cup_body`.
- Produces: binary STL and a one-object millimetre 3MF.

- [ ] **Step 1: Write a round-trip contract test using a small box fixture**

```python
import pathlib
import tempfile
import trimesh
import unittest

class ThreeMFContractTest(unittest.TestCase):
    def test_export_reopen_preserves_mm_bounds_and_one_body(self):
        mesh = trimesh.creation.box(extents=[10.0, 20.0, 30.0])
        mesh.units = "mm"
        scene = trimesh.Scene({"fixture": mesh})
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "fixture.3mf"
            path.write_bytes(scene.export(file_type="3mf"))
            reopened = trimesh.load(path, force="scene")
            self.assertEqual(len(reopened.geometry), 1)
            self.assertTrue((abs(reopened.extents - [10.0, 20.0, 30.0]) < 0.001).all())
```

- [ ] **Step 2: Run the test with the project-local dependencies**

```powershell
$env:PYTHONPATH = (Resolve-Path 'projects\skull-egg-cup\02_source\vendor')
python -m unittest projects\skull-egg-cup\02_source\tests\test_3mf_contract.py -v
```

Expected: PASS before production export is attempted.

- [ ] **Step 3: Export only the named body from Blender**

`export_source.py` must fail unless exactly one visible mesh named `skull_egg_cup_body` exists, apply transforms, triangulate, and call Blender's STL exporter with millimetre scale.

```powershell
& 'tools\blender-5.2.1-windows-x64\blender.exe' --background 'projects\skull-egg-cup\03_build\v001\skull_egg_cup_v001_source.blend' --python-exit-code 1 --python 'projects\skull-egg-cup\02_source\blender\export_source.py' -- --output 'projects\skull-egg-cup\03_build\v001\skull_egg_cup_v001_body.stl'
```

- [ ] **Step 4: Implement candidate assembly**

```python
def build_candidate(stl_path, candidate_path):
    mesh = trimesh.load_mesh(stl_path, file_type="stl", process=False)
    mesh.units = "mm"
    mesh.metadata["name"] = "skull_egg_cup_body"
    scene = trimesh.Scene({"skull_egg_cup_body": mesh})
    candidate_path.write_bytes(scene.export(file_type="3mf"))
```

The script must refuse to overwrite an existing candidate and must print its full SHA-256 plus the first eight uppercase hexadecimal characters.

- [ ] **Step 5: Build `v001` candidate once**

```powershell
$env:PYTHONPATH = (Resolve-Path 'projects\skull-egg-cup\02_source\vendor')
python 'projects\skull-egg-cup\02_source\tools\build_candidate.py' --stl 'projects\skull-egg-cup\03_build\v001\skull_egg_cup_v001_body.stl' --output 'projects\skull-egg-cup\03_build\v001\skull_egg_cup_v001_candidate.3mf'
```

Expected: new candidate created; full SHA-256 and eight-character ID printed; no overwrite path exists.

### Task 6: Reopen the candidate and run geometric QA

**Files:**
- Create: `projects/skull-egg-cup/02_source/tools/inspect_3mf.py`
- Create: `projects/skull-egg-cup/02_source/tools/qa_candidate.py`
- Create: `projects/skull-egg-cup/04_review/v001/reopened_body.stl`
- Create: `projects/skull-egg-cup/04_review/v001/skull_egg_cup_v001_qa.json`
- Create: `projects/skull-egg-cup/04_review/v001/skull_egg_cup_v001_qa.md`

**Interfaces:**
- Consumes: only `skull_egg_cup_v001_candidate.3mf`, never the `.blend` or pre-candidate STL for measurements.
- Produces: reopened STL, structured QA, human-readable QA, final candidate ID.

- [ ] **Step 1: Implement independent 3MF package inspection**

`inspect_3mf.py` must use only `zipfile` and `xml.etree.ElementTree` to verify:

```python
REQUIRED_MEMBERS = {"[Content_Types].xml", "_rels/.rels", "3D/3dmodel.model"}

def inspect_package(path):
    # return unit, object_count, build_item_count, vertex_count, triangle_count
    # require unit == "millimeter"
    # require object_count == build_item_count == 1
```

- [ ] **Step 2: Implement reopened-mesh QA**

`qa_candidate.py` must load the 3MF through Trimesh as a scene, concatenate the one geometry instance with transforms applied, and emit a JSON object with this exact typed schema:

```python
from typing import TypedDict

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
    opening_diameter_mm: float
    cavity_depth_mm: float
    minimum_wall_mm: float
    base_plane_error_mm: float
    blockers: list[str]
    warnings: list[str]
```

The accepted result requires `body_count == 1`, `watertight is True`, `winding_consistent is True`, zero degenerate faces, one connected component, opening `42.0 ± 0.2 mm`, cavity depth `22.0 ± 0.2 mm`, minimum wall at least `2.4 mm`, and base-plane error at most `0.05 mm`. Record `euler_number` but do not require `2` for the anatomical derivative: intentional orbital, nasal, zygomatic, and cranial passages create handles while the surface remains one connected watertight manifold. A non-2 value must be reported as a warning with the derived genus. The warnings list always includes `PLA temperature risk accepted by user`.

Opening, depth, wall, and base measurements must be derived from cross-sections or ray tests on the reopened mesh; do not copy them from `model_config.py` into the result.

- [ ] **Step 3: Run QA and export the reopened body**

```powershell
$env:PYTHONPATH = (Resolve-Path 'projects\skull-egg-cup\02_source\vendor')
python 'projects\skull-egg-cup\02_source\tools\qa_candidate.py' --candidate 'projects\skull-egg-cup\03_build\v001\skull_egg_cup_v001_candidate.3mf' --review-dir 'projects\skull-egg-cup\04_review\v001'
```

Expected: exit code `0` only when `blockers` is empty; reopened STL, JSON, and Markdown report created.

- [ ] **Step 4: Cross-check candidate immutability**

Compute SHA-256 before and after QA. Expected: hashes match exactly and the candidate modification timestamp is unchanged.

### Task 7: Proof renders from the reopened candidate

**Files:**
- Create: `projects/skull-egg-cup/02_source/blender/render_reopened.py`
- Create: `projects/skull-egg-cup/02_source/tools/make_proof_sheet.py`
- Create: `projects/skull-egg-cup/04_review/v001/previews/skull_egg_cup_v001_front.png`
- Create: `projects/skull-egg-cup/04_review/v001/previews/skull_egg_cup_v001_back.png`
- Create: `projects/skull-egg-cup/04_review/v001/previews/skull_egg_cup_v001_side.png`
- Create: `projects/skull-egg-cup/04_review/v001/previews/skull_egg_cup_v001_top.png`
- Create: `projects/skull-egg-cup/04_review/v001/previews/skull_egg_cup_v001_isometric.png`
- Create: `projects/skull-egg-cup/04_review/v001/previews/skull_egg_cup_v001_dimensions.png`
- Create: `projects/skull-egg-cup/04_review/v001/previews/skull_egg_cup_v001_parts-colors.png`
- Create: `projects/skull-egg-cup/04_review/v001/previews/skull_egg_cup_v001_proof-sheet.png`

**Interfaces:**
- Consumes: `04_review/v001/reopened_body.stl` and QA JSON only.
- Produces: mandatory labeled review images tied to the candidate's version and ID.

- [ ] **Step 1: Implement the reopened-mesh renderer**

`render_reopened.py` must start from a factory scene, import only `reopened_body.stl`, assign a neutral bone material, create a neutral studio floor and three-area-light rig, and render orthographic cameras named:

```python
VIEWS = {
    "front": (0, -1, 0),
    "back": (0, 1, 0),
    "side": (1, 0, 0),
    "top": (0, 0, 1),
    "isometric": (1, -1, 0.8),
}
```

Every PNG must contain `skull_egg_cup`, `v001`, and the exact short ID from QA JSON. The script must not open the canonical `.blend`.

- [ ] **Step 2: Render the five geometry views**

```powershell
& 'tools\blender-5.2.1-windows-x64\blender.exe' --background --factory-startup --python-exit-code 1 --python 'projects\skull-egg-cup\02_source\blender\render_reopened.py' -- --mesh 'projects\skull-egg-cup\04_review\v001\reopened_body.stl' --qa 'projects\skull-egg-cup\04_review\v001\skull_egg_cup_v001_qa.json' --output-dir 'projects\skull-egg-cup\04_review\v001\previews'
```

- [ ] **Step 3: Build dimension, parts/colour, and proof sheets**

`make_proof_sheet.py` must use Pillow to compose the rendered PNGs and QA values. The dimension sheet lists measured X/Y/Z, opening diameter, cavity depth, and minimum wall. The parts sheet states `1 body / single spool colour / PLA`. The proof sheet combines all mandatory views without resampling the model.

- [ ] **Step 4: Verify image traceability**

Run a script assertion that every required file exists and that its PNG metadata contains the same `version`, `short_id`, and full candidate SHA-256 recorded in QA JSON.

### Task 8: User review gate and version loop

**Files:**
- Read: `projects/skull-egg-cup/04_review/v001/skull_egg_cup_v001_qa.md`
- Read: `projects/skull-egg-cup/04_review/v001/previews/*.png`
- No release files are created in this task.

**Interfaces:**
- Produces: either an explicit approval string for the displayed version/ID or a change request that starts a new version.

- [ ] **Step 1: Present the proof sheet and key QA results directly in chat**

Show the front, back, side, top, isometric, dimension, and parts/colour views. State every `WARNING`, including PLA temperature risk and any required supports. Do not call the version final.

- [ ] **Step 2: Request version-specific approval**

Use this exact form with the actual ID:

```text
Утверждаю skull_egg_cup v001, ID 1234ABCD.
```

- [ ] **Step 3: Handle requested changes without overwriting**

If the user requests a geometry, size, colour, or part change, create `v002` directories, update `ModelConfig.version`, rebuild from the canonical source path for `v002`, and repeat Tasks 3–8. Preserve all `v001` files unchanged.

### Task 9: Immutable release after approval

**Files:**
- Create: `projects/skull-egg-cup/02_source/tools/release_candidate.py`
- Create: `projects/skull-egg-cup/02_source/tests/test_release_identity.py`
- Create: `projects/skull-egg-cup/05_release/v001/skull_egg_cup_v001_geometry.3mf`
- Create: `projects/skull-egg-cup/05_release/v001/skull_egg_cup_v001_manifest.json`
- Create: `projects/skull-egg-cup/05_release/v001/skull_egg_cup_v001_print-notes.md`
- Copy without rebuilding: approved requirements, source snapshot, STL, QA, and previews.

**Interfaces:**
- Consumes: explicit user approval of the exact candidate version and ID.
- Produces: immutable release directory whose 3MF hash equals the approved candidate hash.

- [ ] **Step 1: Write the release identity test**

```python
import hashlib
import pathlib
import unittest

class ReleaseIdentityTest(unittest.TestCase):
    def test_release_is_byte_identical_to_candidate(self):
        root = pathlib.Path(__file__).resolve().parents[4]
        candidate = root / "projects/skull-egg-cup/03_build/v001/skull_egg_cup_v001_candidate.3mf"
        release = root / "projects/skull-egg-cup/05_release/v001/skull_egg_cup_v001_geometry.3mf"
        digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
        self.assertEqual(digest(candidate), digest(release))
```

- [ ] **Step 2: Verify the identity test fails before release**

Expected: failure because the release file does not exist.

- [ ] **Step 3: Implement approval-gated release copying**

`release_candidate.py` must require `--approved-version v001` and an eight-character `--approved-id`, verify both against QA JSON, refuse a non-empty release directory, copy the candidate bytes to the `geometry.3mf` name, and compare SHA-256 after the copy.

The release manifest must contain `model`, `version`, `status`, `release_date`, measured `bounds_mm`, `parts`, `material`, `nozzle_mm`, `toolchain`, canonical source path, candidate SHA-256, release SHA-256, short ID, and a file-to-SHA-256 map. The print notes must repeat the accepted PLA temperature warning, manual-wash restriction, likely support areas, and the user's responsibility for slicing.

- [ ] **Step 4: Create the release without rebuilding geometry**

```powershell
$env:PYTHONPATH = (Resolve-Path 'projects\skull-egg-cup\02_source\vendor')
$qa = Get-Content -Raw 'projects\skull-egg-cup\04_review\v001\skull_egg_cup_v001_qa.json' | ConvertFrom-Json
$approvedId = $qa.short_id
python 'projects\skull-egg-cup\02_source\tools\release_candidate.py' --approved-version v001 --approved-id $approvedId --project 'projects\skull-egg-cup'
```

Run this command only after the user has explicitly approved the same `$approvedId` shown in the review images.

- [ ] **Step 5: Run final release verification**

```powershell
python -m unittest projects\skull-egg-cup\02_source\tests\test_release_identity.py -v
```

Expected: PASS; candidate and release hashes are byte-identical.

- [ ] **Step 6: Perform final readback and handoff**

Reopen the released 3MF once more, compare bounds/body count with QA JSON, list all release files and hashes, and instruct the user to import `skull_egg_cup_v001_geometry.3mf` into Anycubic Slicer Next for profile selection, supports, layer preview, and printing.
