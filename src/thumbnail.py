import argparse, os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

W, H = 1280, 720

def make_thumbnail(text, output, font_path, background=None):
    if not font_path or not Path(font_path).is_file():
        raise FileNotFoundError("Add a licensed Devanagari font at assets/fonts/NotoSansDevanagari-Bold.ttf.")
    if background and Path(background).is_file():
        image = Image.open(background).convert("RGB").resize((W, H))
    else:
        image = Image.new("RGB", (W, H), (22, 24, 55))
        d = ImageDraw.Draw(image)
        d.polygon([(760, 0), (W, 0), (W, H), (560, H)], fill=(88, 45, 160))
        d.ellipse((900, 110, 1230, 440), fill=(235, 95, 70))
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(font_path, 82)
    words, lines, current = text.split(), [], ""
    for word in words:
        test = (current + " " + word).strip()
        if draw.textbbox((0, 0), test, font=font, stroke_width=3)[2] <= 820:
            current = test
        else:
            if current: lines.append(current)
            current = word
    if current: lines.append(current)
    if len(lines) > 4:
        raise ValueError("Headline too long; use 2–5 short words.")
    heights = [draw.textbbox((0,0), line, font=font, stroke_width=3)[3] for line in lines]
    y = max(45, (H - sum(heights) - (len(lines)-1)*14)//2)
    for line, height in zip(lines, heights):
        draw.text((55, y), line, font=font, fill="white", stroke_width=4, stroke_fill="#101326")
        y += height + 14
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    image.save(output, quality=95)
    return output

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", required=True)
    ap.add_argument("--output", default="thumbnail.jpg")
    ap.add_argument("--background")
    ap.add_argument("--font", default=os.getenv("DEVANAGARI_FONT", "assets/fonts/NotoSansDevanagari-Bold.ttf"))
    a = ap.parse_args()
    make_thumbnail(a.text, a.output, a.font, a.background)
    print(f"Created {a.output}")

if __name__ == "__main__":
    main()
