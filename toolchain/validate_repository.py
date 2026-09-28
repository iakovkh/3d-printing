from __future__ import annotations

import argparse
import dataclasses
import json
import pathlib

from toolchain.cloud3d.repository import validate_repository


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=pathlib.Path, default=pathlib.Path.cwd())
    parser.add_argument("--base-ref")
    args = parser.parse_args()
    report = validate_repository(args.repo_root, args.base_ref)
    print(json.dumps([dataclasses.asdict(item) for item in report.findings], indent=2))
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
