"""Create a new project without bypassing the intake contract."""

from __future__ import annotations

import json
import pathlib
import re


_SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_WINDOWS_RESERVED = {
    "con",
    "prn",
    "aux",
    "nul",
    *(f"com{index}" for index in range(1, 10)),
    *(f"lpt{index}" for index in range(1, 10)),
}
_DIRECTORIES = (
    "00_brief",
    "01_concept",
    "02_source",
    "03_build",
    "04_review",
    "05_release",
)


def _template_root() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parents[2] / "templates" / "project"


def validate_slug(slug: str) -> str:
    if not _SLUG.fullmatch(slug) or slug.lower() in _WINDOWS_RESERVED:
        raise ValueError(f"invalid project slug: {slug!r}")
    return slug


def create_project(
    repo_root: pathlib.Path, slug: str, original_request: str
) -> pathlib.Path:
    slug = validate_slug(slug)
    if not original_request.strip():
        raise ValueError("original request must not be empty")
    project_dir = repo_root / "projects" / slug
    if project_dir.exists():
        raise FileExistsError(f"project already exists: {project_dir}")
    for directory in _DIRECTORIES:
        (project_dir / directory).mkdir(parents=True, exist_ok=True)
    (project_dir / "00_brief" / "original_request.md").write_text(
        original_request, encoding="utf-8"
    )
    requirements = (_template_root() / "00_brief" / "requirements.md").read_text(
        encoding="utf-8"
    )
    (project_dir / "00_brief" / "requirements.md").write_text(
        requirements.replace("__PROJECT_SLUG__", slug), encoding="utf-8"
    )
    state = json.loads(
        (_template_root() / "project-state.json").read_text(encoding="utf-8")
    )
    state["slug"] = slug
    (project_dir / "project-state.json").write_text(
        json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return project_dir
