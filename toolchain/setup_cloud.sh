#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
manifest="$repo_root/toolchain/versions.json"
python_bin="${CLOUD3D_PYTHON:-python3.12}"
venv_dir="$repo_root/.venv"
cache_base="${CLOUD3D_CACHE_DIR:-${XDG_CACHE_HOME:-$HOME/.cache}/cloud3d}"
blender_version="5.2.1"
archive_name="blender-${blender_version}-linux-x64.tar.xz"
archive_url="https://download.blender.org/release/Blender5.2/$archive_name"
archive_sha="a31f524fa99a527d3d52b7f5aaa68c34e1a19d5a1c9473f79c5cc610fd5b10e9"
archive_path="$cache_base/$archive_name"
blender_dir="$cache_base/blender-${blender_version}-linux-x64"

"$python_bin" -c 'import sys; assert sys.version_info[:2] == (3, 12), sys.version'

if [ ! -x "$venv_dir/bin/python" ]; then
  "$python_bin" -m venv "$venv_dir"
fi
"$venv_dir/bin/python" -m pip install --disable-pip-version-check --upgrade pip
"$venv_dir/bin/python" -m pip install --disable-pip-version-check -r "$repo_root/toolchain/requirements.lock"

mkdir -p "$cache_base"
if [ ! -f "$archive_path" ]; then
  curl --fail --location --retry 3 "$archive_url" --output "$archive_path"
fi
printf '%s  %s\n' "$archive_sha" "$archive_path" | sha256sum --check --status
if [ ! -x "$blender_dir/blender" ]; then
  tar -xJf "$archive_path" -C "$cache_base"
fi
ln -sfn "$blender_dir/blender" "$venv_dir/bin/blender"

if ! command -v openscad >/dev/null 2>&1; then
  sudo apt-get update
  sudo apt-get install --yes openscad
fi

CLOUD3D_BLENDER="$venv_dir/bin/blender" \
  "$venv_dir/bin/python" "$repo_root/toolchain/verify_toolchain.py" --repo-root "$repo_root"

