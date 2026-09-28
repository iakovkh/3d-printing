from __future__ import annotations

import json
import pathlib
import tempfile
import unittest


from toolchain.cloud3d.project import create_project
from toolchain.cloud3d.state import (
    Status,
    advance_state,
    assert_modeling_allowed,
    configure_requirements,
    load_state,
    record_concept_approval,
    set_current_version,
)


class ProjectLifecycleTest(unittest.TestCase):
    def test_create_project_preserves_original_request_verbatim(self):
        request = "Сделай держатель 42 мм.\nНе меняй отверстие."
        with tempfile.TemporaryDirectory() as temporary:
            project = create_project(pathlib.Path(temporary), "phone-holder", request)
            saved = (project / "00_brief" / "original_request.md").read_text(
                encoding="utf-8"
            )
            self.assertEqual(saved, request)

    def test_create_project_makes_contract_tree_and_intake_state(self):
        with tempfile.TemporaryDirectory() as temporary:
            project = create_project(pathlib.Path(temporary), "phone-holder", "brief")
            for directory in (
                "00_brief",
                "01_concept",
                "02_source",
                "03_build",
                "04_review",
                "05_release",
            ):
                self.assertTrue((project / directory).is_dir(), directory)
            self.assertTrue((project / "00_brief" / "requirements.md").is_file())
            self.assertEqual(load_state(project).status, Status.INTAKE)

    def test_rejects_path_traversal_reserved_and_duplicate_slugs(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            for invalid in ("../escape", "Has Spaces", "con", "ends-"):
                with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                    create_project(root, invalid, "brief")
            create_project(root, "valid-slug", "brief")
            with self.assertRaises(FileExistsError):
                create_project(root, "valid-slug", "other")

    def test_rejects_empty_original_request(self):
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(ValueError, "original request"):
                create_project(pathlib.Path(temporary), "fixture", "  \n")

    def test_waiting_for_input_cannot_skip_to_geometry_draft(self):
        with tempfile.TemporaryDirectory() as temporary:
            project = create_project(pathlib.Path(temporary), "fixture", "brief")
            advance_state(project, Status.WAITING_FOR_INPUT, "brief structured")
            with self.assertRaisesRegex(ValueError, "transition"):
                advance_state(project, Status.GEOMETRY_DRAFT, "start")

    def test_ready_to_model_requires_no_critical_questions_and_approval_evidence(self):
        with tempfile.TemporaryDirectory() as temporary:
            project = create_project(pathlib.Path(temporary), "fixture", "brief")
            advance_state(project, Status.WAITING_FOR_INPUT, "brief structured")
            configure_requirements(
                project,
                classification="FUNCTIONAL",
                concept_required=False,
                critical_questions_open=True,
            )
            with self.assertRaisesRegex(ValueError, "critical"):
                advance_state(project, Status.READY_TO_MODEL, "Подтверждаю ТЗ fixture")
            configure_requirements(
                project,
                classification="FUNCTIONAL",
                concept_required=False,
                critical_questions_open=False,
            )
            with self.assertRaisesRegex(ValueError, "evidence"):
                advance_state(project, Status.READY_TO_MODEL, "   ")
            ready = advance_state(
                project, Status.READY_TO_MODEL, "Подтверждаю ТЗ fixture"
            )
            self.assertEqual(
                ready.requirements_approval.user_text, "Подтверждаю ТЗ fixture"
            )

    def test_organic_model_requires_concept_approval_before_geometry(self):
        with tempfile.TemporaryDirectory() as temporary:
            project = create_project(pathlib.Path(temporary), "owl", "brief")
            advance_state(project, Status.WAITING_FOR_INPUT, "brief structured")
            configure_requirements(
                project,
                classification="ORGANIC",
                concept_required=True,
                critical_questions_open=False,
            )
            advance_state(project, Status.READY_TO_MODEL, "Подтверждаю ТЗ owl")
            with self.assertRaisesRegex(ValueError, "concept"):
                assert_modeling_allowed(project)
            record_concept_approval(project, "Подтверждаю концепт owl v001")
            assert_modeling_allowed(project)
            state = advance_state(project, Status.GEOMETRY_DRAFT, "begin geometry")
            self.assertEqual(state.status, Status.GEOMETRY_DRAFT)

    def test_invalid_backward_transition_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            project = create_project(pathlib.Path(temporary), "fixture", "brief")
            advance_state(project, Status.WAITING_FOR_INPUT, "brief structured")
            configure_requirements(
                project,
                classification="FUNCTIONAL",
                concept_required=False,
                critical_questions_open=False,
            )
            advance_state(project, Status.READY_TO_MODEL, "Подтверждаю ТЗ fixture")
            with self.assertRaisesRegex(ValueError, "transition"):
                advance_state(project, Status.INTAKE, "go back")

    def test_review_can_return_to_geometry_for_a_new_version(self):
        with tempfile.TemporaryDirectory() as temporary:
            project = create_project(pathlib.Path(temporary), "fixture", "brief")
            advance_state(project, Status.WAITING_FOR_INPUT, "brief structured")
            configure_requirements(
                project,
                classification="FUNCTIONAL",
                concept_required=False,
                critical_questions_open=False,
            )
            advance_state(project, Status.READY_TO_MODEL, "Подтверждаю ТЗ fixture")
            advance_state(project, Status.GEOMETRY_DRAFT, "begin v001")
            advance_state(project, Status.READY_FOR_REVIEW, "v001 QA complete")
            state = advance_state(project, Status.GEOMETRY_DRAFT, "begin v002")
            self.assertEqual(state.status, Status.GEOMETRY_DRAFT)

    def test_state_file_is_valid_json_with_schema_version(self):
        with tempfile.TemporaryDirectory() as temporary:
            project = create_project(pathlib.Path(temporary), "fixture", "brief")
            raw = json.loads((project / "project-state.json").read_text(encoding="utf-8"))
            self.assertEqual(raw["schema_version"], 1)
            self.assertEqual(raw["slug"], "fixture")

    def test_current_version_is_explicit_and_cannot_move_backwards(self):
        with tempfile.TemporaryDirectory() as temporary:
            project = create_project(pathlib.Path(temporary), "fixture", "brief")
            advance_state(project, Status.WAITING_FOR_INPUT, "brief structured")
            configure_requirements(
                project,
                classification="FUNCTIONAL",
                concept_required=False,
                critical_questions_open=False,
            )
            advance_state(project, Status.READY_TO_MODEL, "requirements approved")
            advance_state(project, Status.GEOMETRY_DRAFT, "begin geometry")
            self.assertEqual(set_current_version(project, "v001").current_version, "v001")
            self.assertEqual(set_current_version(project, "v002").current_version, "v002")
            with self.assertRaisesRegex(ValueError, "newer"):
                set_current_version(project, "v001")


if __name__ == "__main__":
    unittest.main()
