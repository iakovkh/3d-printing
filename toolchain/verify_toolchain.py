"""Verify that the active Linux environment matches the pinned toolchain."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
import pathlib
import platform
import re
import shutil
import subprocess
from collections.abc import Callable


Probe = Callable[[str], str | None]


def load_expected_versions(path: pathlib.Path) -> dict[str, object]:
    data = json.loads(path.read_text(encoding="utf-8"))
    required = {"python", "blender", "openscad", "packages"}
    missing = required - data.keys()
    if missing:
        raise ValueError(f"toolchain manifest is missing {sorted(missing)}")
    blender = data["blender"]
    if not isinstance(blender, dict) or not {"version", "url", "sha256"} <= blender.keys():
        raise ValueError("blender manifest must include version, url and sha256")
    if not re.fullmatch(r"[0-9a-f]{64}", str(blender["sha256"])):
        raise ValueError("blender sha256 must be 64 lowercase hexadecimal characters")
    if not isinstance(data["packages"], dict) or not data["packages"]:
        raise ValueError("packages must be a non-empty object")
    return data


def _command_output(command: list[str]) -> str | None:
    try:
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return (result.stdout or result.stderr).strip()


def default_probe(name: str) -> str | None:
    if name == "python":
        return platform.python_version()
    if name == "blender":
        executable = os.environ.get("CLOUD3D_BLENDER") or shutil.which("blender")
        return _command_output([executable, "--version"]) if executable else None
    if name == "openscad":
        executable = os.environ.get("CLOUD3D_OPENSCAD") or shutil.which("openscad")
        return _command_output([executable, "--version"]) if executable else None
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def _matches(name: str, actual: str, expected: str) -> bool:
    if name == "python":
        return actual == expected or actual.startswith(expected + ".")
    if name in {"blender", "openscad"}:
        return expected in actual
    return actual == expected


def probe_toolchain(repo_root: pathlib.Path, probe: Probe | None = None) -> dict[str, object]:
    expected = load_expected_versions(repo_root / "toolchain" / "versions.json")
    probe = probe or default_probe
    wanted = {
        "python": str(expected["python"]),
        "blender": str(expected["blender"]["version"]),
        "openscad": str(expected["openscad"]),
        **{str(name): str(version) for name, version in expected["packages"].items()},
    }
    actual: dict[str, str | None] = {}
    failures: list[str] = []
    for name, version in wanted.items():
        found = probe(name)
        actual[name] = found
        if found is None:
            failures.append(f"{name}: missing")
        elif not _matches(name, found, version):
            failures.append(f"{name}: expected {version}, got {found}")
    if failures:
        raise RuntimeError("toolchain mismatch: " + "; ".join(failures))
    return {"expected": wanted, "actual": actual}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--repo-root",
        type=pathlib.Path,
        default=pathlib.Path(__file__).resolve().parents[1],
    )
    args = parser.parse_args()
    print(json.dumps(probe_toolchain(args.repo_root), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
