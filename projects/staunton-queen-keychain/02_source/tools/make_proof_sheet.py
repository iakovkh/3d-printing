"""Label reopened-candidate renders and compose proof sheets."""

from __future__ import annotations

import argparse
import json
import pathlib
import re

from PIL import Image, ImageDraw, ImageFont, PngImagePlugin


MODEL = "staunton_queen_keychain"
VIEW_LABELS = {
    "front": "FRONT / СПЕРЕДИ",
    "back": "BACK / СЗАДИ",
    "side": "SIDE / СБОКУ",
    "top": "TOP / СВЕРХУ",
    "isometric": "ISOMETRIC / ИЗОМЕТРИЯ",
    "detail": "CROWN & RING HOLE / КОРОНА И ОТВЕРСТИЕ",
}


def font(size, bold=False):
    filename = "arialbd.ttf" if bold else "arial.ttf"
    path = pathlib.Path(r"C:\Windows\Fonts") / filename
    return ImageFont.truetype(str(path), size) if path.exists() else ImageFont.load_default()


def version_from_qa(path: pathlib.Path) -> str:
    match = re.search(r"_(v\d{3})_qa$", path.stem)
    if match is None:
        raise ValueError(f"QA filename is not versioned: {path.name}")
    return match.group(1)


def metadata(qa, version):
    info = PngImagePlugin.PngInfo()
    info.add_text("model", MODEL)
    info.add_text("version", version)
    info.add_text("short_id", qa["short_id"])
    info.add_text("sha256", qa["sha256"])
    info.add_text("geometry_source", "reopened candidate 3MF")
    return info


def header(draw, width, title, qa, version):
    draw.rectangle((0, 0, width, 70), fill=(27, 31, 37))
    draw.text((24, 12), title, font=font(24, True), fill=(245, 247, 250))
    trace = f"{MODEL} · {version} · ID {qa['short_id']} · REOPENED 3MF"
    draw.text((24, 43), trace, font=font(14), fill=(140, 189, 235))


def label_views(directory, qa, version):
    outputs = {}
    for name, label in VIEW_LABELS.items():
        raw_path = directory / f"{MODEL}_{version}_{name}_raw.png"
        with Image.open(raw_path) as raw_image:
            raw = raw_image.convert("RGB")
        canvas = Image.new("RGB", (720, 790), (225, 230, 236))
        canvas.paste(raw, (0, 70))
        draw = ImageDraw.Draw(canvas)
        header(draw, 720, label, qa, version)
        output = directory / f"{MODEL}_{version}_{name}.png"
        canvas.save(output, pnginfo=metadata(qa, version))
        outputs[name] = output
    return outputs


def make_dimensions(directory, qa, version, isometric):
    canvas = Image.new("RGB", (720, 790), (231, 235, 240))
    draw = ImageDraw.Draw(canvas)
    header(draw, 720, "DIMENSIONS / РАЗМЕРЫ", qa, version)
    with Image.open(isometric) as image:
        preview = image.convert("RGB").crop((80, 95, 640, 570)).resize((560, 475))
    canvas.paste(preview, (80, 74))
    draw.rectangle((24, 548, 696, 766), fill=(246, 247, 249), outline=(55, 91, 125), width=2)
    bounds = qa["bounds_mm"]
    rows = [
        f"X / Y / Z: {bounds[0]:.2f} × {bounds[1]:.2f} × {bounds[2]:.2f} mm",
        f"Base / основание: {qa['base_diameter_mm']:.3f} mm",
        f"Ring hole / отверстие: {qa['hole_diameter_mm']:.3f} mm",
        f"Finial / шарик: {qa['finial_outer_diameter_mm']:.3f} mm",
        f"Hole ligament / перемычка: {qa['minimum_hole_ligament_mm']:.3f} mm",
        f"Crown peaks / зубцы: {qa['crown_peak_count']} · Base error: {qa['base_plane_error_mm']:.4f} mm",
    ]
    for index, row in enumerate(rows):
        draw.text((45, 565 + index * 31), row, font=font(18, index == 0), fill=(22, 29, 36))
    output = directory / f"{MODEL}_{version}_dimensions.png"
    canvas.save(output, pnginfo=metadata(qa, version))
    return output


def make_parts(directory, qa, version, front):
    canvas = Image.new("RGB", (720, 790), (231, 235, 240))
    draw = ImageDraw.Draw(canvas)
    header(draw, 720, "PARTS & COLOUR / СОСТАВ И ЦВЕТ", qa, version)
    with Image.open(front) as image:
        preview = image.convert("RGB").crop((135, 90, 585, 550)).resize((450, 460))
    canvas.paste(preview, (135, 78))
    draw.rectangle((24, 548, 696, 766), fill=(246, 247, 249), outline=(55, 91, 125), width=2)
    rows = [
        ("BODY", "1 connected watertight mesh"),
        ("COLOUR", "matte black PLA · one spool"),
        ("NOZZLE", "0.4 mm"),
        ("RING", "standard metal key ring · not included"),
        ("ORIENTATION", "upright on the flat base"),
    ]
    for index, (key, value) in enumerate(rows):
        y_value = 565 + index * 37
        draw.text((44, y_value), key, font=font(17, True), fill=(36, 90, 138))
        draw.text((185, y_value), value, font=font(17), fill=(22, 29, 36))
    output = directory / f"{MODEL}_{version}_parts-colors.png"
    canvas.save(output, pnginfo=metadata(qa, version))
    return output


def make_proof(directory, qa, version, tiles):
    canvas = Image.new("RGB", (2880, 1680), (18, 23, 29))
    draw = ImageDraw.Draw(canvas)
    draw.rectangle((0, 0, 2880, 100), fill=(27, 31, 37))
    draw.text((40, 16), "STAUNTON QUEEN KEYCHAIN — CANDIDATE PROOF", font=font(34, True), fill=(245, 247, 250))
    draw.text(
        (40, 61),
        f"{version} · ID {qa['short_id']} · SHA-256 {qa['sha256']} · rendered only from reopened 3MF",
        font=font(17),
        fill=(140, 189, 235),
    )
    ordered = [
        tiles["front"],
        tiles["back"],
        tiles["side"],
        tiles["top"],
        tiles["isometric"],
        tiles["detail"],
        tiles["dimensions"],
        tiles["parts"],
    ]
    for index, path in enumerate(ordered):
        with Image.open(path) as source:
            image = source.convert("RGB")
        x_value = (index % 4) * 720
        y_value = 100 + (index // 4) * 790
        canvas.paste(image, (x_value, y_value))
    output = directory / f"{MODEL}_{version}_proof-sheet.png"
    canvas.save(output, pnginfo=metadata(qa, version))
    return output


def verify_traceability(paths, qa, version):
    for path in paths:
        with Image.open(path) as image:
            assert image.info.get("version") == version, path
            assert image.info.get("short_id") == qa["short_id"], path
            assert image.info.get("sha256") == qa["sha256"], path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--qa", type=pathlib.Path, required=True)
    parser.add_argument("--preview-dir", type=pathlib.Path, required=True)
    args = parser.parse_args()
    qa = json.loads(args.qa.read_text(encoding="utf-8"))
    version = version_from_qa(args.qa)
    views = label_views(args.preview_dir, qa, version)
    dimensions = make_dimensions(args.preview_dir, qa, version, views["isometric"])
    parts = make_parts(args.preview_dir, qa, version, views["front"])
    proof = make_proof(
        args.preview_dir,
        qa,
        version,
        {**views, "dimensions": dimensions, "parts": parts},
    )
    outputs = [*views.values(), dimensions, parts, proof]
    verify_traceability(outputs, qa, version)
    print("PROOF_FILES=" + ",".join(path.name for path in outputs))


if __name__ == "__main__":
    main()
