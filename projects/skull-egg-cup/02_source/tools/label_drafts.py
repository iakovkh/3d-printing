from __future__ import annotations

import argparse
import pathlib

from PIL import Image, ImageDraw, ImageFont


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", type=pathlib.Path, required=True)
    args = parser.parse_args()
    label = "ЧЕРНОВОЙ РЕНДЕР ИСХОДНИКА — НЕ ДЛЯ УТВЕРЖДЕНИЯ"
    font_path = pathlib.Path(r"C:\Windows\Fonts\arialbd.ttf")
    font = ImageFont.truetype(str(font_path), 18) if font_path.exists() else ImageFont.load_default()
    finished = []
    for raw_path in sorted(args.directory.glob("*_raw.png")):
        image = Image.open(raw_path).convert("RGB")
        canvas = Image.new("RGB", (image.width, image.height + 54), (35, 28, 24))
        canvas.paste(image, (0, 54))
        draw = ImageDraw.Draw(canvas)
        bounds = draw.textbbox((0, 0), label, font=font)
        x_value = max(10, (canvas.width - (bounds[2] - bounds[0])) // 2)
        draw.text((x_value, 17), label, font=font, fill=(248, 232, 205))
        output = raw_path.with_name(raw_path.name.replace("_raw.png", ".png"))
        canvas.save(output, pnginfo=None)
        finished.append(output.name)
    print("LABELED_DRAFTS=" + ",".join(finished))


if __name__ == "__main__":
    main()
