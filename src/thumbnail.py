import argparse, os, random, sys
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

W, H = 1280, 720

# Available font styles for Kisan bdlega
FONT_CANDIDATES = {
    "mukta": "assets/fonts/Mukta-Bold.ttf",
    "hind": "assets/fonts/Hind-Bold.ttf",
    "poppins": "assets/fonts/Poppins-Bold.ttf",
    "baloo": "assets/fonts/Baloo2-Bold.ttf",
    "default": "assets/fonts/NotoSansDevanagari-Bold.ttf"
}

def resolve_font(preferred_style=None):
    """Resolve font path based on user preference (Mukta, Hind, Poppins, Baloo)."""
    if preferred_style and preferred_style.lower() in FONT_CANDIDATES:
        p = Path(FONT_CANDIDATES[preferred_style.lower()])
        if p.is_file():
            return str(p)

    # Try in priority order: Mukta -> Hind -> Poppins -> Baloo -> Default
    for key in ["mukta", "hind", "poppins", "baloo", "default"]:
        p = Path(FONT_CANDIDATES[key])
        if p.is_file():
            return str(p)

    # Check system fonts or fallback
    for sys_font in [
        "/usr/share/fonts/truetype/deva/Mukta-Bold.ttf",
        "/usr/share/fonts/truetype/deva/Hind-Bold.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf"
    ]:
        if Path(sys_font).is_file():
            return sys_font

    return None

def make_thumbnail(text, output, font_path=None, font_style="mukta", background=None, channel_name="Kisan bdlega"):
    font_file = font_path if (font_path and Path(font_path).is_file()) else resolve_font(font_style)
    if not font_file:
        raise FileNotFoundError("Devanagari font not found in assets/fonts/ (Mukta, Hind, Poppins, Baloo).")

    if background and Path(background).is_file():
        image = Image.open(background).convert("RGB").resize((W, H))
    else:
        # Agriculture / Farming themed premium gradient (Vibrant Lush Green & Dark Forest)
        image = Image.new("RGB", (W, H), (14, 43, 20))
        d = ImageDraw.Draw(image)
        # Decorative dynamic farming shapes (Golden Sun / Sunlight + Emerald Green fields)
        d.polygon([(700, 0), (W, 0), (W, H), (450, H)], fill=(28, 86, 38))
        d.ellipse((850, 60, 1260, 470), fill=(245, 166, 35)) # Warm golden harvest badge
        d.ellipse((870, 80, 1240, 450), fill=(22, 68, 30))

        # Channel watermark badge on top left
        badge_font_path = resolve_font("poppins") or font_file
        try:
            badge_font = ImageFont.truetype(badge_font_path, 28)
            d.rounded_rectangle([(45, 30), (320, 80)], radius=10, fill=(245, 166, 35))
            d.text((65, 38), f"🌾 {channel_name}", font=badge_font, fill=(10, 30, 15))
        except Exception:
            pass

    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(font_file, 88)
    
    # Word wrap
    words, lines, current = text.split(), [], ""
    for word in words:
        test = (current + " " + word).strip()
        if draw.textbbox((0, 0), test, font=font, stroke_width=4)[2] <= 780:
            current = test
        else:
            if current: lines.append(current)
            current = word
    if current: lines.append(current)
    if len(lines) > 4:
        lines = lines[:4]

    heights = [draw.textbbox((0, 0), line, font=font, stroke_width=4)[3] for line in lines]
    y = max(110, (H - sum(heights) - (len(lines) - 1) * 16) // 2 + 20)

    for i, (line, height) in enumerate(zip(lines, heights)):
        # Highlight first line in golden yellow, others in white
        fill_color = "#FFE600" if i == 0 else "#FFFFFF"
        draw.text((55, y), line, font=font, fill=fill_color, stroke_width=6, stroke_fill="#0A1C0E")
        y += height + 16

    Path(output).parent.mkdir(parents=True, exist_ok=True)
    image.save(output, quality=95)
    return output

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", required=True)
    ap.add_argument("--output", default="thumbnail.jpg")
    ap.add_argument("--background")
    ap.add_argument("--font", default="")
    ap.add_argument("--font-style", default="mukta", choices=["mukta", "hind", "poppins", "baloo", "default"])
    ap.add_argument("--channel", default="Kisan bdlega")
    a = ap.parse_args()
    make_thumbnail(a.text, a.output, a.font, a.font_style, a.background, a.channel)
    print(f"Created agricultural thumbnail: {a.output}")

if __name__ == "__main__":
    main()
