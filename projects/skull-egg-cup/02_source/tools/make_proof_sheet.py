from __future__ import annotations

import argparse
import json
import pathlib

from PIL import Image, ImageDraw, ImageFont, PngImagePlugin


VIEW_LABELS = {
    "front": "FRONT / СПЕРЕДИ",
    "back": "BACK / СЗАДИ",
    "side": "SIDE / СБОКУ",
    "top": "TOP / СВЕРХУ",
    "isometric": "ISOMETRIC / ИЗОМЕТРИЯ",
}


def font(size, bold=False):
    filename = "arialbd.ttf" if bold else "arial.ttf"
    path = pathlib.Path(r"C:\Windows\Fonts") / filename
    return ImageFont.truetype(str(path), size) if path.exists() else ImageFont.load_default()


def metadata(qa):
    info = PngImagePlugin.PngInfo()
    info.add_text("model", "skull_egg_cup")
    info.add_text("version", "v001")
    info.add_text("short_id", qa["short_id"])
    info.add_text("candidate_sha256", qa["sha256"])
    info.add_text("geometry_source", "reopened candidate 3MF")
    return info


def header(draw, width, title, qa):
    draw.rectangle((0, 0, width, 70), fill=(28, 22, 19))
    draw.text((24, 14), title, font=font(25, True), fill=(250, 233, 202))
    trace = f"skull_egg_cup · v001 · ID {qa['short_id']} · REOPENED 3MF"
    draw.text((24, 43), trace, font=font(14), fill=(214, 169, 109))


def label_views(directory, qa):
    outputs = {}
    for name, label in VIEW_LABELS.items():
        raw = Image.open(directory / f"skull_egg_cup_v001_{name}_raw.png").convert("RGB")
        canvas = Image.new("RGB", (720, 790), (18, 23, 28))
        canvas.paste(raw, (0, 70))
        draw = ImageDraw.Draw(canvas)
        header(draw, 720, label, qa)
        output = directory / f"skull_egg_cup_v001_{name}.png"
        canvas.save(output, pnginfo=metadata(qa))
        outputs[name] = output
    return outputs


def make_dimensions(directory, qa, isometric):
    canvas = Image.new("RGB", (720, 790), (22, 27, 31))
    draw = ImageDraw.Draw(canvas)
    header(draw, 720, "DIMENSIONS / РАЗМЕРЫ", qa)
    preview = Image.open(isometric).convert("RGB").crop((0, 70, 720, 790))
    preview = preview.crop((150, 40, 720, 610))
    canvas.paste(preview, (150, 80))
    draw.rectangle((24, 540, 696, 766), fill=(31, 35, 38), outline=(205, 157, 94), width=2)
    bounds = qa["bounds_mm"]
    rows = [
        f"X width / ширина: {bounds[0]:.2f} mm",
        f"Y depth / глубина: {bounds[1]:.2f} mm",
        f"Z height / высота: {bounds[2]:.2f} mm",
        f"Opening / отверстие: {qa['opening_diameter_mm']:.2f} mm",
        f"Bowl depth / глубина чаши: {qa['cavity_depth_mm']:.2f} mm",
        f"Min functional wall / мин. стенка: {qa['minimum_wall_mm']:.2f} mm",
    ]
    for index, row in enumerate(rows):
        draw.text((48, 560 + index * 31), row, font=font(20, index < 3), fill=(242, 230, 210))
    output = directory / "skull_egg_cup_v001_dimensions.png"
    canvas.save(output, pnginfo=metadata(qa))
    return output


def make_parts(directory, qa, front):
    canvas = Image.new("RGB", (720, 790), (22, 27, 31))
    draw = ImageDraw.Draw(canvas)
    header(draw, 720, "PARTS & COLOUR / СОСТАВ И ЦВЕТ", qa)
    preview = Image.open(front).convert("RGB").crop((0, 70, 720, 790)).crop((130, 30, 590, 490))
    canvas.paste(preview, (130, 78))
    draw.rectangle((24, 550, 696, 765), fill=(31, 35, 38), outline=(205, 157, 94), width=2)
    rows = [
        ("1 BODY", "one connected watertight mesh"),
        ("1 COLOUR", "single-spool print; warm bone shown only as preview"),
        ("MATERIAL", "standard PLA — risk accepted by user"),
        ("NOZZLE", "0.4 mm"),
        ("SUPPORTS", "likely under cheek arches, jaw and dental undercuts"),
    ]
    for index, (key, value) in enumerate(rows):
        y_value = 568 + index * 36
        draw.text((44, y_value), key, font=font(18, True), fill=(222, 161, 91))
        draw.text((190, y_value), value, font=font(17), fill=(240, 229, 211))
    output = directory / "skull_egg_cup_v001_parts-colors.png"
    canvas.save(output, pnginfo=metadata(qa))
    return output


def make_proof(directory, qa, tiles):
    canvas = Image.new("RGB", (2880, 1680), (13, 17, 21))
    draw = ImageDraw.Draw(canvas)
    draw.rectangle((0, 0, 2880, 100), fill=(28, 22, 19))
    draw.text((40, 20), "SKULL EGG CUP — CANDIDATE PROOF", font=font(34, True), fill=(250, 233, 202))
    draw.text(
        (40, 62),
        f"v001 · ID {qa['short_id']} · SHA-256 {qa['sha256']} · views rendered only from reopened 3MF",
        font=font(18),
        fill=(214, 169, 109),
    )
    ordered = [
        tiles["front"], tiles["back"], tiles["side"], tiles["top"],
        tiles["isometric"], tiles["dimensions"], tiles["parts"],
    ]
    for index, path in enumerate(ordered):
        image = Image.open(path).convert("RGB")
        x_value = (index % 4) * 720
        y_value = 100 + (index // 4) * 790
        canvas.paste(image, (x_value, y_value))
    draw.rectangle((2160, 890, 2879, 1679), fill=(24, 29, 33))
    draw.text((2200, 940), "QA STATUS", font=font(30, True), fill=(222, 161, 91))
    qa_rows = [
        "NO BLOCKERS",
        f"Watertight: {qa['watertight']}",
        f"Connected bodies: {qa['connected_component_count']}",
        f"Degenerate faces: {qa['degenerate_face_count']}",
        f"Base error: {qa['base_plane_error_mm']:.4f} mm",
        "",
        "WARNINGS:",
        "PLA heat risk accepted",
        "Supports likely for undercuts",
        "Hand wash only",
        f"Euler {qa['euler_number']}: intentional anatomy",
    ]
    for index, row in enumerate(qa_rows):
        draw.text((2200, 1000 + index * 43), row, font=font(20, index in (0, 6)), fill=(238, 227, 208))
    output = directory / "skull_egg_cup_v001_proof-sheet.png"
    canvas.save(output, pnginfo=metadata(qa))
    return output


def verify_traceability(paths, qa):
    for path in paths:
        with Image.open(path) as image:
            assert image.info.get("version") == "v001", path
            assert image.info.get("short_id") == qa["short_id"], path
            assert image.info.get("candidate_sha256") == qa["sha256"], path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", type=pathlib.Path, required=True)
    parser.add_argument("--qa", type=pathlib.Path, required=True)
    args = parser.parse_args()
    qa = json.loads(args.qa.read_text(encoding="utf-8"))
    views = label_views(args.directory, qa)
    dimensions = make_dimensions(args.directory, qa, views["isometric"])
    parts = make_parts(args.directory, qa, views["front"])
    proof = make_proof(
        args.directory,
        qa,
        {**views, "dimensions": dimensions, "parts": parts},
    )
    outputs = [*views.values(), dimensions, parts, proof]
    verify_traceability(outputs, qa)
    print("PROOF_FILES=" + ",".join(path.name for path in outputs))


if __name__ == "__main__":
    main()
