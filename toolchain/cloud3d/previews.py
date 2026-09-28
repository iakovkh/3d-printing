"""Create labeled proof images with candidate identity embedded in PNG metadata."""

from __future__ import annotations

import pathlib
import re
from collections.abc import Sequence

from PIL import Image, ImageDraw, ImageFont, PngImagePlugin

from .qa import QaReport
from .three_mf import CandidateIdentity


VIEWS = ("front", "back", "side", "top", "isometric")
VIEW_LABELS = {
    "front": "FRONT / СПЕРЕДИ",
    "back": "BACK / СЗАДИ",
    "side": "SIDE / СБОКУ",
    "top": "TOP / СВЕРХУ",
    "isometric": "ISOMETRIC / ИЗОМЕТРИЯ",
}


def candidate_model_version(path: pathlib.Path) -> tuple[str, str]:
    match = re.fullmatch(r"(.+)_(v\d{3})_candidate", path.stem)
    if match is None:
        raise ValueError(f"candidate filename is not versioned: {path.name}")
    return match.group(1), match.group(2)


def _font(size: int, bold: bool = False):
    candidates = (
        "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
        "arialbd.ttf" if bold else "arial.ttf",
    )
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            pass
    return ImageFont.load_default()


def _metadata(model: str, version: str, identity: CandidateIdentity):
    info = PngImagePlugin.PngInfo()
    info.add_text("model", model)
    info.add_text("version", version)
    info.add_text("short_id", identity.short_id)
    info.add_text("sha256", identity.sha256)
    info.add_text("geometry_source", "reopened candidate 3MF")
    return info


def _header(
    draw: ImageDraw.ImageDraw,
    width: int,
    title: str,
    model: str,
    version: str,
    identity: CandidateIdentity,
) -> None:
    draw.rectangle((0, 0, width, 70), fill=(27, 31, 37))
    draw.text((24, 10), title, font=_font(22, True), fill=(245, 247, 250))
    draw.text(
        (24, 42),
        f"{model} · {version} · ID {identity.short_id} · REOPENED 3MF",
        font=_font(13),
        fill=(140, 189, 235),
    )


def _label_view(
    source: pathlib.Path,
    destination: pathlib.Path,
    label: str,
    model: str,
    version: str,
    identity: CandidateIdentity,
) -> None:
    with Image.open(source) as opened:
        image = opened.convert("RGB")
    image.thumbnail((720, 720))
    canvas = Image.new("RGB", (720, 790), (225, 230, 236))
    canvas.paste(image, ((720 - image.width) // 2, 70 + (720 - image.height) // 2))
    _header(ImageDraw.Draw(canvas), 720, label, model, version, identity)
    canvas.save(destination, pnginfo=_metadata(model, version, identity))


def _dimensions(
    destination: pathlib.Path,
    source: pathlib.Path,
    model: str,
    version: str,
    identity: CandidateIdentity,
    qa: QaReport,
) -> None:
    canvas = Image.new("RGB", (720, 790), (231, 235, 240))
    draw = ImageDraw.Draw(canvas)
    _header(draw, 720, "DIMENSIONS / РАЗМЕРЫ", model, version, identity)
    with Image.open(source) as opened:
        preview = opened.convert("RGB")
    preview.thumbnail((620, 500))
    canvas.paste(preview, ((720 - preview.width) // 2, 75))
    x, y, z = qa.bounds_mm
    rows = (
        f"X / Y / Z: {x:.3f} × {y:.3f} × {z:.3f} mm",
        f"Bodies / части: {len(qa.body_names)}",
        f"BLOCKER: {sum(item.severity.value == 'BLOCKER' for item in qa.findings)}",
        f"WARNING: {sum(item.severity.value == 'WARNING' for item in qa.findings)}",
    )
    draw.rectangle((24, 570, 696, 766), fill=(246, 247, 249), outline=(55, 91, 125), width=2)
    for index, row in enumerate(rows):
        draw.text((45, 590 + index * 38), row, font=_font(18, index == 0), fill=(22, 29, 36))
    canvas.save(destination, pnginfo=_metadata(model, version, identity))


def _parts(
    destination: pathlib.Path,
    source: pathlib.Path,
    model: str,
    version: str,
    identity: CandidateIdentity,
    qa: QaReport,
) -> None:
    canvas = Image.new("RGB", (720, 790), (231, 235, 240))
    draw = ImageDraw.Draw(canvas)
    _header(draw, 720, "PARTS & COLORS / ЧАСТИ И ЦВЕТА", model, version, identity)
    with Image.open(source) as opened:
        preview = opened.convert("RGB")
    preview.thumbnail((620, 470))
    canvas.paste(preview, ((720 - preview.width) // 2, 75))
    draw.rectangle((24, 555, 696, 766), fill=(246, 247, 249), outline=(55, 91, 125), width=2)
    for index, name in enumerate(qa.body_names[:5]):
        color = qa.colors.get(name, "#808080")
        y = 575 + index * 34
        draw.rectangle((45, y, 69, y + 24), fill=color, outline=(30, 30, 30))
        draw.text((84, y), f"{name}: {color}", font=_font(17), fill=(22, 29, 36))
    canvas.save(destination, pnginfo=_metadata(model, version, identity))


def _proof_sheet(
    destination: pathlib.Path,
    tiles: Sequence[pathlib.Path],
    model: str,
    version: str,
    identity: CandidateIdentity,
) -> None:
    tile_size = (360, 395)
    canvas = Image.new("RGB", (1440, 860), (18, 23, 29))
    draw = ImageDraw.Draw(canvas)
    draw.text((30, 16), f"{model} — CANDIDATE PROOF", font=_font(28, True), fill=(245, 247, 250))
    draw.text(
        (30, 55),
        f"{version} · ID {identity.short_id} · SHA-256 {identity.sha256}",
        font=_font(14),
        fill=(140, 189, 235),
    )
    for index, path in enumerate(tiles):
        with Image.open(path) as opened:
            tile = opened.convert("RGB").resize(tile_size)
        x = (index % 4) * tile_size[0]
        y = 70 + (index // 4) * tile_size[1]
        canvas.paste(tile, (x, y))
    canvas.save(destination, pnginfo=_metadata(model, version, identity))


def label_and_compose(
    raw_dir: pathlib.Path,
    output_dir: pathlib.Path,
    identity: CandidateIdentity,
    qa: QaReport,
) -> list[pathlib.Path]:
    if qa.sha256 != identity.sha256 or qa.short_id != identity.short_id:
        raise ValueError("QA identity does not match candidate identity")
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite previews: {output_dir}")
    output_dir.mkdir(parents=True)
    model, version = candidate_model_version(identity.path)
    outputs: list[pathlib.Path] = []
    labeled: dict[str, pathlib.Path] = {}
    for view in VIEWS:
        source = raw_dir / f"{model}_{version}_{view}_raw.png"
        if not source.is_file():
            raise FileNotFoundError(source)
        destination = output_dir / f"{model}_{version}_{view}.png"
        _label_view(source, destination, VIEW_LABELS[view], model, version, identity)
        labeled[view] = destination
        outputs.append(destination)
    dimensions = output_dir / f"{model}_{version}_dimensions.png"
    _dimensions(dimensions, labeled["isometric"], model, version, identity, qa)
    outputs.append(dimensions)
    parts = output_dir / f"{model}_{version}_parts-colors.png"
    _parts(parts, labeled["front"], model, version, identity, qa)
    outputs.append(parts)
    proof = output_dir / f"{model}_{version}_proof-sheet.png"
    _proof_sheet(proof, outputs, model, version, identity)
    outputs.append(proof)
    verify_preview_traceability(outputs, identity)
    return outputs


def verify_preview_traceability(
    paths: Sequence[pathlib.Path], identity: CandidateIdentity
) -> None:
    model, version = candidate_model_version(identity.path)
    expected = {
        "model": model,
        "version": version,
        "short_id": identity.short_id,
        "sha256": identity.sha256,
        "geometry_source": "reopened candidate 3MF",
    }
    for path in paths:
        with Image.open(path) as image:
            for key, value in expected.items():
                actual = image.info.get(key)
                if actual != value:
                    raise ValueError(f"{path.name} {key}={actual!r}, expected {value!r}")
