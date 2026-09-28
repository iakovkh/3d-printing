# Cloud GitHub 3D Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Перенести существующий контракт 3D-моделирования в `iakovkh/3d-printing` и сделать его воспроизводимо исполнимым в Codex Cloud без включённого домашнего компьютера.

**Architecture:** Корневые документы остаются нормативным контрактом, а переносимый Python-пакет `toolchain/cloud3d` реализует проверяемые операции жизненного цикла, 3MF, QA, превью и выпуска. Закреплённый Linux setup-скрипт подготавливает CadQuery, OpenSCAD и headless Blender; GitHub Actions повторяет контрактные проверки, а Git LFS хранит крупные канонические CAD/mesh-исходники.

**Tech Stack:** Python 3.12, `unittest`, Trimesh 5.1.0, NumPy 2.5.3, SciPy 1.18.1, Pillow 12.2.0, lxml 6.1.3, NetworkX 3.6.1, CadQuery 2.8.0, Blender 5.2.1 Linux x64, OpenSCAD 2021.01, Git LFS, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-09-28-cloud-github-3d-workflow-design.md`

## Global Constraints

- `AGENTS.md`, `00_PROJECT_INSTRUCTIONS.md` и `01_CLOUD_WORKFLOW.md` остаются нормативными; новые файлы не меняют порядок стадий или стоп-условия.
- Домашний Windows-компьютер и локальная папка `tools/` не требуются для облачного выполнения.
- Моделирование запрещено до подтверждённого ТЗ; органический/декоративный концепт подтверждается отдельно.
- Показанный `vNNN` не перезаписывается; изменение геометрии, размеров, цвета, частей или трансформаций создаёт новую версию.
- QA и проверочные изображения строятся только после независимого повторного открытия кандидатного 3MF.
- `BLOCKER` запрещает запрос утверждения и выпуск.
- Release создаётся только побитовым копированием утверждённого кандидата; SHA-256 должен совпасть.
- 3MF содержит миллиметры; пользователь выполняет профиль, нарезку и отправку на Anycubic Kobra S1 Combo самостоятельно в Anycubic Slicer Next.
- `.blend`, `.stl`, `.step` и `.stp` отслеживаются Git LFS; `.3mf`, QA Markdown/JSON и компактные PNG остаются обычными Git-файлами.
- Кэши, vendored Python-пакеты, Windows Blender и экспериментальные промежуточные исходники не входят в первый push.

## Review Focus

- Частично заполненное или лишь текстово похожее на утверждённое ТЗ не должно разблокировать моделирование — Task 3 проверяет машинное состояние и доказательство подтверждения.
- Многоцветный 3MF с несколькими именованными телами не должен быть отклонён правилом старого однотельного проекта — Task 4 проверяет одно- и многотельные fixtures.
- Повторный запуск на существующем `candidate.3mf` или `05_release/vNNN` не должен менять байты — Tasks 4 и 6 проверяют отказ от перезаписи.
- PNG от другой версии или кандидата не должен пройти только из-за подходящего имени — Task 5 проверяет встроенные version/ID/SHA-256 metadata.
- Release с совпадающим коротким ID, но другим полным SHA-256 не должен пройти — Task 6 сравнивает полный digest и байты.

---

### Task 1: Repository Baseline and Existing Contract

**Files:**
- Create: `.gitignore`
- Create: `.gitattributes`
- Create: `README.md`
- Create: `tests/test_repository_layout.py`
- Modify: `00_PROJECT_INSTRUCTIONS.md`
- Modify: `01_CLOUD_WORKFLOW.md`
- Modify: `AGENTS.md`

**Interfaces:**
- Consumes: существующие нормативные документы и структура `projects/<project-slug>/00_brief` — `05_release`.
- Produces: переносимый корень репозитория, правила Git/LFS и краткая мобильная инструкция, на которые опираются все следующие задачи.

- [ ] **Step 1: Write the failing repository-layout tests**

Добавить `RepositoryLayoutTest` с проверками:

```python
def test_normative_documents_exist_at_repository_root(): ...
def test_contract_keeps_required_gate_phrases(): ...
def test_gitignore_excludes_local_toolchains_caches_and_vendor_dirs(): ...
def test_lfs_tracks_source_meshes_but_not_release_3mf_or_png(): ...
def test_readme_names_phone_cloud_github_and_anycubic_handoff(): ...
```

Проверка LFS должна требовать паттерны для `*.blend`, `*.stl`, `*.step`, `*.stp` и запрещать паттерн `*.3mf filter=lfs`.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m unittest tests.test_repository_layout -v`  
Expected: FAIL because the baseline files and cloud appendices do not exist.

- [ ] **Step 3: Add repository hygiene and cloud appendices without rewriting the contract**

`.gitignore` должен исключить `tools/`, `**/vendor/`, `**/__pycache__/`, `*.pyc`, Blender autosaves, raw render intermediates and local virtual environments. `.gitattributes` должен configure Git LFS only for canonical mesh/CAD source formats listed above.

`README.md` должен описать: подключение репозитория в Codex Cloud, запуск с телефона, обязательные подтверждения, получение PR и скачивание `geometry.3mf`. В нормативных документах заменить только устаревшее «Git пока не используется» и добавить короткий раздел о ветках/PR, не меняя стадии.

- [ ] **Step 4: Run the tests**

Run: `python -m unittest tests.test_repository_layout -v`  
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add .gitignore .gitattributes README.md AGENTS.md 00_PROJECT_INSTRUCTIONS.md 01_CLOUD_WORKFLOW.md tests/test_repository_layout.py
git commit -m "docs: prepare 3d workflow repository"
```

### Task 2: Reproducible Cloud Toolchain

**Files:**
- Create: `toolchain/requirements.lock`
- Create: `toolchain/versions.json`
- Create: `toolchain/setup_cloud.sh`
- Create: `toolchain/verify_toolchain.py`
- Create: `tests/test_toolchain_manifest.py`

**Interfaces:**
- Consumes: Linux x64 cloud environment with Python 3.12, outbound access during setup, and repository working tree.
- Produces: `load_expected_versions(path: Path) -> dict[str, object]`, `probe_toolchain(repo_root: Path) -> dict[str, object]`, and an idempotent `bash toolchain/setup_cloud.sh` entry point.

- [ ] **Step 1: Write failing toolchain-manifest tests**

```python
def test_versions_pin_python_blender_openscad_and_cadquery(): ...
def test_python_lock_preserves_existing_qa_versions(): ...
def test_blender_download_is_linux_x64_and_has_sha256(): ...
def test_probe_fails_on_missing_or_mismatched_required_tool(): ...
def test_setup_script_does_not_reference_windows_paths_or_repo_tools_dir(): ...
```

Expected pinned values: Python `3.12`, Blender `5.2.1`, OpenSCAD `2021.01`, CadQuery `2.8.0`, NumPy `2.5.3`, SciPy `1.18.1`, Trimesh `5.1.0`, lxml `6.1.3`, Pillow `12.2.0`, NetworkX `3.6.1`.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m unittest tests.test_toolchain_manifest -v`  
Expected: FAIL because no shared cloud toolchain exists.

- [ ] **Step 3: Implement pinned setup and verification**

`versions.json` must hold exact command probes, the official Blender Linux URL, archive SHA-256 copied from Blender's `blender-5.2.1.sha256`, and package versions. `setup_cloud.sh` must download to a cache outside the repository, verify SHA-256 before extraction, create `.venv`, install `requirements.lock`, and install/probe OpenSCAD. Re-running it must reuse already verified downloads and leave repository artifacts untouched.

`probe_toolchain(repo_root: Path) -> dict[str, object]` must return actual versions and raise `RuntimeError` on a required mismatch.

- [ ] **Step 4: Run unit and live probes**

Run: `python -m unittest tests.test_toolchain_manifest -v`  
Expected: PASS.

Run in a clean Linux container/cloud task: `bash toolchain/setup_cloud.sh && .venv/bin/python toolchain/verify_toolchain.py`  
Expected: exit 0 and JSON reporting every pinned tool.

- [ ] **Step 5: Commit**

```bash
git add toolchain tests/test_toolchain_manifest.py
git commit -m "build: add reproducible cloud modeling toolchain"
```

### Task 3: Project Template and Lifecycle Gates

**Files:**
- Create: `templates/project/00_brief/original_request.md`
- Create: `templates/project/00_brief/requirements.md`
- Create: `templates/project/project-state.json`
- Create: `templates/project/02_source/source-manifest.example.json`
- Create: `toolchain/__init__.py`
- Create: `toolchain/cloud3d/__init__.py`
- Create: `toolchain/cloud3d/project.py`
- Create: `toolchain/cloud3d/state.py`
- Create: `toolchain/cloud3d/schemas/project-state.schema.json`
- Create: `tests/test_project_lifecycle.py`

**Interfaces:**
- Consumes: `repo_root: Path`, validated lowercase kebab-case slug, exact original request text, status transition, and user evidence string.
- Produces: `create_project(repo_root: Path, slug: str, original_request: str) -> Path`, `load_state(project_dir: Path) -> ProjectState`, `advance_state(project_dir: Path, target: Status, evidence: str) -> ProjectState`, `assert_modeling_allowed(project_dir: Path) -> None`.

- [ ] **Step 1: Write failing lifecycle tests**

```python
def test_create_project_preserves_original_request_verbatim(): ...
def test_create_project_makes_contract_directory_tree_and_intake_state(): ...
def test_rejects_path_traversal_reserved_and_duplicate_slugs(): ...
def test_waiting_for_input_cannot_advance_to_geometry_draft(): ...
def test_ready_to_model_requires_requirements_approval_evidence(): ...
def test_organic_model_requires_concept_approval_before_geometry(): ...
def test_invalid_backward_or_skipped_transition_is_rejected(): ...
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m unittest tests.test_project_lifecycle -v`  
Expected: FAIL with missing `cloud3d.project` and `cloud3d.state`.

- [ ] **Step 3: Implement the template, typed state, and transition table**

`ProjectState` must expose `slug`, `classification`, `status`, `requirements_approval`, `concept_required`, `concept_approval`, and `current_version`. Allowed statuses and transition order must exactly match `00_PROJECT_INSTRUCTIONS.md`. Approval evidence must include exact user text and ISO-8601 timestamp; an empty evidence string is invalid.

- [ ] **Step 4: Run lifecycle tests**

Run: `python -m unittest tests.test_project_lifecycle -v`  
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add templates toolchain/cloud3d tests/test_project_lifecycle.py
git commit -m "feat: enforce project lifecycle gates"
```

### Task 4: Generic Immutable 3MF Candidate and Round-Trip Inspection

**Files:**
- Create: `toolchain/cloud3d/three_mf.py`
- Create: `toolchain/cloud3d/roundtrip.py`
- Create: `tests/fixtures/meshes.py`
- Create: `tests/test_three_mf.py`
- Preserve: `projects/*/02_source/tools/build_candidate.py`
- Preserve: `projects/*/02_source/tools/inspect_3mf.py`

**Interfaces:**
- Consumes: `Sequence[BodyInput]`, where `BodyInput` contains `path: Path`, `name: str`, optional RGB color and a 4×4 transform; destination `candidate_path: Path`.
- Produces: `build_candidate(bodies: Sequence[BodyInput], candidate_path: Path) -> CandidateIdentity`, `inspect_package(path: Path) -> PackageReport`, `reopen_candidate(candidate: Path, output_dir: Path) -> RoundTripReport`.

- [ ] **Step 1: Write failing single- and multi-body tests**

```python
def test_build_candidate_refuses_existing_destination_and_preserves_bytes(): ...
def test_single_body_roundtrip_preserves_millimeters_bounds_and_volume(): ...
def test_multibody_roundtrip_preserves_names_count_transforms_and_colors(): ...
def test_candidate_matches_source_manifest_names_transforms_and_colors(): ...
def test_inspector_rejects_missing_package_members_and_non_mm_units(): ...
def test_roundtrip_exports_reopened_bodies_not_original_stls(): ...
def test_short_id_is_uppercase_first_eight_sha256_characters(): ...
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m unittest tests.test_three_mf -v`  
Expected: FAIL because the generic module does not exist.

- [ ] **Step 3: Generalize the proven per-project implementation**

Reuse the existing Trimesh export, ZIP/XML package inspection, exact overwrite refusal and SHA calculation. Remove hard-coded model names and the old assumption that every valid model has exactly one object. `PackageReport` and `RoundTripReport` must carry unit, body names, body/build counts, transforms, extents, per-body volume and exported reopened-body paths.

Keep the old project-local scripts unchanged until migration validation in Task 8 proves equivalent results.

- [ ] **Step 4: Run tests**

Run: `python -m unittest tests.test_three_mf -v`  
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add toolchain/cloud3d tests/fixtures/meshes.py tests/test_three_mf.py
git commit -m "feat: add immutable multibody 3mf pipeline"
```

### Task 5: Generic QA, Reopened-Candidate Rendering, and Traceable Proof Sheets

**Files:**
- Create: `toolchain/cloud3d/qa.py`
- Create: `toolchain/cloud3d/previews.py`
- Create: `toolchain/blender/render_reopened.py`
- Create: `tests/test_qa_contract.py`
- Create: `tests/test_preview_traceability.py`

**Interfaces:**
- Consumes: candidate path, `RoundTripReport`, requirements/expectations JSON, model/version identity, optional model-specific measurement callback.
- Produces: `run_generic_qa(candidate: Path, roundtrip: RoundTripReport, expectations: dict) -> QaReport`, `label_and_compose(raw_dir: Path, output_dir: Path, identity: CandidateIdentity, qa: QaReport) -> list[Path]`, `verify_preview_traceability(paths: Sequence[Path], identity: CandidateIdentity) -> None`.

- [ ] **Step 1: Write failing QA and traceability tests**

```python
def test_qa_marks_non_watertight_missing_body_and_dimension_mismatch_as_blocker(): ...
def test_qa_keeps_support_risk_as_warning_not_blocker(): ...
def test_qa_records_unavailable_reliable_check_explicitly(): ...
def test_required_views_are_front_back_side_top_isometric_dimensions_parts_colors(): ...
def test_every_png_embeds_model_version_short_id_full_sha_and_reopened_source(): ...
def test_preview_from_other_version_or_sha_is_rejected_even_when_filename_matches(): ...
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m unittest tests.test_qa_contract tests.test_preview_traceability -v`  
Expected: FAIL with missing QA and preview modules.

- [ ] **Step 3: Extract and parameterize existing QA/proof-sheet behavior**

Preserve the established checks and PNG metadata from the two project implementations. Generic QA owns package identity, topology, components, bounds, units, transforms, base-plane and minimum-feature facts; project-specific scripts provide named critical measurements and tolerances. No unsupported self-intersection result may be reported as verified.

`render_reopened.py` must accept only the reopened-body manifest from Task 4, never the canonical `.blend` or original STL. It must create raw technical views in headless Blender, then `label_and_compose` must create the mandatory labeled outputs and proof sheet.

- [ ] **Step 4: Run tests and one headless render fixture**

Run: `python -m unittest tests.test_qa_contract tests.test_preview_traceability -v`  
Expected: PASS.

Run: `blender --background --factory-startup --python toolchain/blender/render_reopened.py -- --manifest tests/fixtures/reopened-manifest.json --output /tmp/cloud3d-previews`  
Expected: exit 0 and five raw camera views; proof composition then produces all seven mandatory labeled views plus proof sheet.

- [ ] **Step 5: Commit**

```bash
git add toolchain/cloud3d toolchain/blender tests/test_qa_contract.py tests/test_preview_traceability.py tests/fixtures/reopened-manifest.json
git commit -m "feat: add traceable candidate qa and previews"
```

### Task 6: Exact Approval and Byte-Identical Release

**Files:**
- Create: `toolchain/cloud3d/approval.py`
- Create: `toolchain/cloud3d/release.py`
- Create: `toolchain/cloud3d/schemas/approval.schema.json`
- Create: `tests/test_release_gate.py`

**Interfaces:**
- Consumes: project directory, exact `vNNN`, exact short ID, full SHA-256, exact user approval text, QA report and candidate path.
- Produces: `record_approval(project_dir: Path, version: str, short_id: str, sha256: str, user_text: str) -> Path`, `validate_release_gate(project_dir: Path, version: str) -> ReleaseInputs`, `release_candidate(project_dir: Path, version: str) -> Path`.

- [ ] **Step 1: Write failing release-gate tests**

```python
def test_rejects_missing_approval_wrong_version_short_id_or_full_sha(): ...
def test_rejects_qa_with_any_blocker(): ...
def test_release_refuses_existing_release_directory(): ...
def test_release_copies_candidate_bytes_without_reexport(): ...
def test_release_reopens_geometry_and_writes_manifest_with_same_sha(): ...
def test_same_short_id_with_different_full_sha_is_rejected(): ...
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m unittest tests.test_release_gate -v`  
Expected: FAIL with missing approval/release modules.

- [ ] **Step 3: Implement approval evidence and copy-only release**

Store approval at `04_review/vNNN/<name>_vNNN_approval.json`. `release_candidate` must create a new `05_release/vNNN` atomically, use `shutil.copyfile` for 3MF, recompute both hashes, independently reopen the copied file and write the release manifest. It must never call exporters or model builders.

- [ ] **Step 4: Run release tests**

Run: `python -m unittest tests.test_release_gate -v`  
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add toolchain/cloud3d tests/test_release_gate.py
git commit -m "feat: enforce approved byte-identical releases"
```

### Task 7: Repository Validator, CI, and Cloud Smoke Test

**Files:**
- Create: `toolchain/cloud3d/repository.py`
- Create: `toolchain/validate_repository.py`
- Create: `tests/test_repository_validation.py`
- Create: `tests/fixtures/smoke_project/model.py`
- Create: `toolchain/run_smoke_test.py`
- Create: `.github/workflows/contract.yml`
- Create: `.github/workflows/cloud-smoke.yml`

**Interfaces:**
- Consumes: repository root or changed project paths.
- Produces: `validate_repository(repo_root: Path) -> ValidationReport`, CLI exit 0 only with no blocker, and a disposable complete candidate/review fixture that deliberately stops before release.

- [ ] **Step 1: Write failing repository validation tests**

```python
def test_rejects_mixed_versions_and_duplicate_candidate_identity(): ...
def test_rejects_modified_or_deleted_committed_candidate_and_release_against_base_ref(): ...
def test_rejects_geometry_created_before_requirements_gate(): ...
def test_rejects_release_without_approval_or_matching_hash(): ...
def test_accepts_complete_candidate_that_has_not_yet_been_approved(): ...
def test_smoke_run_stops_at_ready_for_review_without_creating_release(): ...
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.test_repository_validation -v`  
Expected: FAIL with missing repository validator.

- [ ] **Step 3: Implement validator and workflows**

`validate_repository(repo_root: Path, base_ref: str | None = None) -> ValidationReport` must also compare changed candidate/release paths with the pull request base and reject modifications or deletion of an already committed `vNNN`. `contract.yml` runs Python contract tests and this validator with the pull request base SHA on every pull request and without a base on push. `cloud-smoke.yml` is manual plus changes to `toolchain/**`; it runs `setup_cloud.sh`, creates a small CadQuery parameterized fixture, exports candidate, reopens it, performs QA and creates previews. The smoke workflow must assert no `05_release` exists because it has no user approval.

- [ ] **Step 4: Run the full local suite and smoke test in Linux**

Run: `python -m unittest discover -s tests -v`  
Expected: PASS.

Run: `.venv/bin/python toolchain/run_smoke_test.py --output /tmp/cloud3d-smoke`  
Expected: exit 0, status `READY_FOR_REVIEW`, candidate/QA/previews present, release absent.

- [ ] **Step 5: Commit**

```bash
git add toolchain tests .github/workflows
git commit -m "ci: validate cloud 3d workflow"
```

### Task 8: Curate Existing Projects Without Changing Geometry

**Files:**
- Create: `projects/skull-egg-cup/migration-manifest.json`
- Create: `projects/staunton-queen-keychain/migration-manifest.json`
- Modify: only toolchain-path fields inside existing project metadata where they refer to Windows-local paths
- Preserve: all selected candidates, QA reports, labeled previews, canonical sources and the existing skull release bytes
- Exclude: caches, `vendor/`, failed candidates, reference-draft renders, noncanonical intermediate `.blend` files and duplicate reopened STL files
- Create: `tests/test_migrated_projects.py`

**Interfaces:**
- Consumes: current local projects, their QA/manifest identity and the selection rules in the design spec.
- Produces: one explicit include/exclude manifest per project with SHA-256 for every migrated binary; no regenerated geometry.

- [ ] **Step 1: Record current hashes and write failing migration tests**

```python
def test_every_included_binary_matches_recorded_pre_migration_sha256(): ...
def test_no_cache_vendor_failed_candidate_or_noncanonical_blend_is_tracked(): ...
def test_skull_release_geometry_still_matches_its_release_manifest(): ...
def test_queen_has_candidates_and_reviews_but_no_fabricated_release(): ...
def test_all_lfs_eligible_files_are_lfs_tracked(): ...
```

- [ ] **Step 2: Run migration tests before curation**

Run: `python -m unittest tests.test_migrated_projects -v`  
Expected: FAIL because migration manifests and Git tracking policy are absent.

- [ ] **Step 3: Curate with explicit `git add` lists and validate existing artifacts**

Do not delete local excluded files. Add only paths named by the migration manifests. Preserve the skull `v001` release exactly. Preserve queen `v001`/`v002` candidates and reviews as non-release history; do not infer approval. Replace Windows-local executable paths only in metadata, never in geometry or approval records.

- [ ] **Step 4: Run migrated-project and full validation**

Run: `python -m unittest tests.test_migrated_projects -v`  
Expected: PASS.

Run: `python toolchain/validate_repository.py`  
Expected: exit 0; skull reports `RELEASED`, queen reports `READY_FOR_REVIEW` or its exact recorded non-release status, with no fabricated approval.

- [ ] **Step 5: Commit**

```bash
git add projects/*/migration-manifest.json tests/test_migrated_projects.py
git add <explicit paths listed by both migration manifests>
git commit -m "chore: migrate verified 3d project artifacts"
```

### Task 9: Publish, Read Back, and Protect the GitHub Repository

**Files:**
- Modify: no product files expected; GitHub repository settings change externally.

**Interfaces:**
- Consumes: clean local `main`, authenticated `iakovkh` GitHub session, empty `https://github.com/iakovkh/3d-printing.git`.
- Produces: pushed `main`, successful Actions runs, verified downloadable artifacts, and branch protection requiring contract validation.

- [ ] **Step 1: Run final pre-push verification**

Run: `git status --short`  
Expected: empty.

Run: `python -m unittest discover -s tests -v`  
Expected: PASS.

Run: `python toolchain/validate_repository.py`  
Expected: exit 0 and zero `BLOCKER`.

Run: `git lfs ls-files`  
Expected: every tracked `.blend`, `.stl`, `.step`, `.stp` is listed; no `.3mf` or `.png` is listed.

- [ ] **Step 2: Push the bootstrap history**

Run: `git push --set-upstream origin main`  
Expected: new `main` branch created on `iakovkh/3d-printing`.

- [ ] **Step 3: Wait for and verify GitHub Actions**

Run: `gh run list --repo iakovkh/3d-printing --limit 5` then `gh run watch <run-id> --repo iakovkh/3d-printing --exit-status`  
Expected: contract workflow succeeds.

- [ ] **Step 4: Read back critical files and artifact hashes from GitHub**

Use `gh api repos/iakovkh/3d-printing/contents/...` to confirm the three normative documents, README, workflows, skull release 3MF and previews are present. Download the release 3MF to a temporary directory and compare its SHA-256 with the committed release manifest.

- [ ] **Step 5: Configure branch protection**

Require pull requests and the successful `contract` status check for changes to `main`, while retaining administrator recovery. If the account/repository tier refuses branch protection, record that limitation visibly in `README.md` and keep the workflow as the mandatory manual merge check.

- [ ] **Step 6: Perform the phone handoff check**

From ChatGPT mobile/Codex Cloud, select `iakovkh/3d-printing`, open `README.md`, and start a disposable brief-only project. Verify that the agent reads `AGENTS.md`, creates `original_request.md` and `requirements.md`, and stops in `WAITING_FOR_INPUT` without geometry. Close without merging the disposable branch.

- [ ] **Step 7: Record acceptance**

Add the GitHub Actions run URL and mobile check result to the implementation handoff. Do not claim Anycubic compatibility until the user downloads the preserved skull release and opens it in Anycubic Slicer Next.
