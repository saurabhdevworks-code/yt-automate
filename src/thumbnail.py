"""High-CTR YouTube Thumbnail Generator.
Creates modern, click-worthy 1280x720 thumbnails for Indian Farming & Agriculture channels:
- Multi-stop rich cinematic background gradient with radial spotlights.
- High-contrast sticker ribbons (Yellow on dark pill, Emerald green ribbons).
- 3D drop-shadow typography in bold Hindi Devanagari (Baloo2, Mukta, Poppins).
- Right-side glowing 3D Stat/Benefit Callout Badge.
- Optional: Video frame extraction with left-side dark gradient fade.
"""
import argparse
import os
import re
import subprocess
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

W, H = 1280, 720
ROOT = Path(__file__).resolve().parents[1]
FONTS_DIR = ROOT / "assets" / "fonts"

FONT_CANDIDATES = {
    "baloo": FONTS_DIR / "Baloo2-Bold.ttf",
    "mukta": FONTS_DIR / "Mukta-Bold.ttf",
    "poppins": FONTS_DIR / "Poppins-Bold.ttf",
    "hind": FONTS_DIR / "Hind-Bold.ttf",
    "noto": FONTS_DIR / "NotoSansDevanagari-Bold.ttf"
}


def resolve_font(preferred_style="baloo", size=60):
    """Resolve font path and load TrueType font with fallback."""
    key = str(preferred_style).lower() if preferred_style else "baloo"
    order = [key, "baloo", "mukta", "poppins", "hind", "noto"]

    for k in order:
        if k in FONT_CANDIDATES:
            path = FONT_CANDIDATES[k]
            if path.exists() and path.is_file():
                try:
                    return ImageFont.truetype(str(path), size)
                except Exception:
                    pass

    # System fallbacks
    for sys_font in [
        "/usr/share/fonts/truetype/deva/Mukta-Bold.ttf",
        "/usr/share/fonts/truetype/deva/Hind-Bold.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf"
    ]:
        if Path(sys_font).is_file():
            try:
                return ImageFont.truetype(sys_font, size)
            except Exception:
                pass

    return ImageFont.load_default()


def create_gradient_backdrop():
    """Create a high-end cinematic dark emerald-to-navy gradient with radial lighting."""
    base = Image.new("RGB", (W, H), (10, 25, 18))
    draw = ImageDraw.Draw(base)

    # Diagonal gradient
    for y in range(H):
        for x in range(0, W, 4):
            t = (x / W) * 0.6 + (y / H) * 0.4
            r = int(6 + 18 * t)
            g = int(28 + 48 * (1 - t * 0.5))
            b = int(22 + 45 * t)
            draw.rectangle([x, y, x + 4, y + 1], fill=(r, g, b))

    # Add radial golden/emerald glow on the right
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    cx, cy = 960, 360
    max_radius = 420
    for r in range(max_radius, 0, -10):
        alpha = int(35 * (1 - r / max_radius))
        glow_draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(34, 197, 94, alpha))

    # Warm golden spotlight accent
    cx2, cy2 = 1040, 280
    for r in range(300, 0, -8):
        alpha = int(45 * (1 - r / 300))
        glow_draw.ellipse([cx2 - r, cy2 - r, cx2 + r, cy2 + r], fill=(245, 158, 11, alpha))

    base.paste(Image.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, 0)), glow).convert("RGB"), (0, 0), glow)
    return base


def extract_video_frame(video_path: Path, output_frame: Path, timestamp: str = "00:00:08") -> bool:
    """Extract a high quality scenic frame from video using ffmpeg."""
    if not video_path.exists():
        return False
    cmd = [
        "ffmpeg", "-y",
        "-ss", timestamp,
        "-i", str(video_path),
        "-vframes", "1",
        "-q:v", "2",
        str(output_frame)
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=False)
        return res.returncode == 0 and output_frame.exists() and output_frame.stat().st_size > 1000
    except Exception:
        return False


def apply_dark_fade_overlay(image: Image.Image) -> Image.Image:
    """Apply a smooth left-to-right dark gradient so text remains 100% readable over video frames."""
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # 100% dark on the left (0 to 600px), transitioning to transparent on the right
    for x in range(W):
        if x < 450:
            alpha = 235
        elif x < 900:
            t = (x - 450) / 450.0
            alpha = int(235 * (1.0 - t * 0.75))
        else:
            alpha = 55
        draw.line([(x, 0), (x, H)], fill=(10, 15, 25, alpha))

    base_rgba = image.convert("RGBA")
    return Image.alpha_composite(base_rgba, overlay).convert("RGB")


def draw_pill(draw, box, fill_color, outline_color=None, outline_width=2, radius=14):
    """Draw a smooth rounded rectangle pill."""
    draw.rounded_rectangle(box, radius=radius, fill=fill_color, outline=outline_color, width=outline_width)


def make_thumbnail(
    text: str,
    output: str,
    font_path: str = None,
    font_style: str = "baloo",
    background: str = None,
    video_path: str = None,
    channel_name: str = "Kisan bdlega",
    top_badge: str = "🔥 नई कृषि तकनीक 2026",
    stat_callout: str = "बंपर मुनाफा",
    stat_sub: str = "100% सटीक जानकारी"
):
    """Generate high-CTR YouTube thumbnail."""
    # 1. Base image setup
    out_path = Path(output).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    img = None
    # Try video frame extraction if video provided
    if video_path and Path(video_path).exists():
        temp_frame = out_path.parent / "temp_extracted_frame.jpg"
        if extract_video_frame(Path(video_path), temp_frame):
            try:
                frame_img = Image.open(temp_frame).convert("RGB").resize((W, H))
                img = apply_dark_fade_overlay(frame_img)
            except Exception:
                pass
            finally:
                if temp_frame.exists():
                    try: os.remove(temp_frame)
                    except Exception: pass

    # Try custom background image
    if img is None and background and Path(background).is_file():
        try:
            bg_img = Image.open(background).convert("RGB").resize((W, H))
            img = apply_dark_fade_overlay(bg_img)
        except Exception:
            pass

    # Default: Rich multi-stop gradient with radial spotlight
    if img is None:
        img = create_gradient_backdrop()

    draw = ImageDraw.Draw(img)

    # 2. Channel Branding Badge (Top Left)
    font_badge = resolve_font("poppins", 24)
    ch_text = f"🌾 {channel_name.upper()}"
    b_bbox = draw.textbbox((0, 0), ch_text, font=font_badge)
    bw, bh = b_bbox[2] - b_bbox[0], b_bbox[3] - b_bbox[1]
    draw_pill(draw, (50, 36, 50 + bw + 34, 36 + bh + 16), (15, 23, 42), (51, 65, 85), 2, 10)
    draw.text((66, 43), ch_text, font=font_badge, fill=(248, 250, 252))

    # 3. Top Alert Hook Pill
    font_hook = resolve_font("baloo", 28)
    h_bbox = draw.textbbox((0, 0), top_badge, font=font_hook)
    hw, hh = h_bbox[2] - h_bbox[0], h_bbox[3] - h_bbox[1]
    draw_pill(draw, (50, 105, 50 + hw + 34, 105 + hh + 18), (220, 38, 38), (248, 113, 113), 2, 12)
    draw.text((66, 112), top_badge, font=font_hook, fill=(255, 255, 255))

    # 4. Text Line Splitting & Typography
    words = [w.strip() for w in text.split() if w.strip()]
    if not words:
        words = ["किसान", "बदलेगा", "विशेष"]

    # Divide words into 2 or 3 high-impact lines
    if len(words) <= 3:
        line1 = " ".join(words[:1])
        line2 = " ".join(words[1:]) if len(words) > 1 else "बड़ा खुलासा"
        line3 = "पूरी जानकारी देखें ➔"
    elif len(words) <= 6:
        split_idx = len(words) // 2
        line1 = " ".join(words[:split_idx])
        line2 = " ".join(words[split_idx:])
        line3 = "पूरी जानकारी देखें ➔"
    else:
        line1 = " ".join(words[:3])
        line2 = " ".join(words[3:7])
        line3 = " ".join(words[7:10]) if len(words) > 7 else "पूरी जानकारी देखें ➔"

    # Line 1: Main Title (Bold White with Deep Shadow)
    font_l1 = resolve_font("baloo", 82)
    y_pos = 195
    draw.text((54, y_pos + 6), line1, font=font_l1, fill=(0, 0, 0))
    draw.text((50, y_pos), line1, font=font_l1, fill=(255, 255, 255), stroke_width=4, stroke_fill=(15, 23, 42))

    # Line 2: Highlight Sticker Ribbon (Bright Yellow on Contrast Pill)
    y_pos += 112
    font_l2 = resolve_font("baloo", 80)
    l2_bbox = draw.textbbox((0, 0), line2, font=font_l2)
    l2_w, l2_h = l2_bbox[2] - l2_bbox[0], l2_bbox[3] - l2_bbox[1]
    max_w = min(l2_w + 36, 750)
    draw_pill(draw, (48, y_pos - 6, 50 + max_w, y_pos + l2_h + 16), (250, 204, 21), (255, 255, 255), 3, 16)
    draw.text((66, y_pos + 4), line2, font=font_l2, fill=(15, 23, 42))

    # Line 3: Supporting Benefit Ribbon (Emerald Green Pill)
    y_pos += l2_h + 36
    font_l3 = resolve_font("baloo", 44)
    l3_bbox = draw.textbbox((0, 0), line3, font=font_l3)
    l3_w, l3_h = l3_bbox[2] - l3_bbox[0], l3_bbox[3] - l3_bbox[1]
    draw_pill(draw, (48, y_pos, 50 + l3_w + 32, y_pos + l3_h + 18), (22, 101, 52), (74, 222, 128), 2, 14)
    draw.text((64, y_pos + 8), line3, font=font_l3, fill=(240, 253, 244))

    # 5. Right Side - Glowing 3D Callout Badge
    cx, cy = 980, 360
    # Outer emerald glow ring
    draw.ellipse([cx - 185, cy - 185, cx + 185, cy + 185], fill=(22, 101, 52), outline=(34, 197, 94), width=4)
    # Middle dark circle
    draw.ellipse([cx - 160, cy - 160, cx + 160, cy + 160], fill=(15, 23, 42), outline=(250, 204, 21), width=5)

    # Big Callout Text
    font_stat = resolve_font("baloo", 58)
    st_bbox = draw.textbbox((0, 0), stat_callout, font=font_stat)
    st_w = st_bbox[2] - st_bbox[0]
    draw.text((cx - st_w // 2, cy - 66), stat_callout, font=font_stat, fill=(250, 204, 21))

    # Divider
    draw.line([cx - 80, cy + 16, cx + 80, cy + 16], fill=(234, 179, 8), width=3)

    # Subtext
    font_ss = resolve_font("baloo", 30)
    ss_bbox = draw.textbbox((0, 0), stat_sub, font=font_ss)
    ss_w = ss_bbox[2] - ss_bbox[0]
    draw.text((cx - ss_w // 2, cy + 28), stat_sub, font=font_ss, fill=(255, 255, 255))

    # Verified pill
    draw_pill(draw, (cx - 75, cy + 112, cx + 75, cy + 152), (34, 197, 94), (255, 255, 255), 2, 10)
    font_v = resolve_font("poppins", 20)
    v_text = "✔ 100% सही"
    v_bbox = draw.textbbox((0, 0), v_text, font=font_v)
    vw = v_bbox[2] - v_bbox[0]
    draw.text((cx - vw // 2, cy + 120), v_text, font=font_v, fill=(15, 23, 42))

    # Outer border
    draw.rectangle([0, 0, W - 1, H - 1], outline=(51, 65, 85), width=3)

    img.save(out_path, quality=98)
    return str(out_path)


def main():
    ap = argparse.ArgumentParser(description="Generate high-CTR YouTube thumbnail")
    ap.add_argument("--text", required=True, help="Main catchy thumbnail text")
    ap.add_argument("--output", default="output/thumbnail.jpg", help="Output thumbnail path")
    ap.add_argument("--background", help="Custom background image path")
    ap.add_argument("--video", help="Video path to extract high quality frame")
    ap.add_argument("--font", default="", help="Specific font path")
    ap.add_argument("--font-style", default="baloo", choices=["baloo", "mukta", "poppins", "hind", "noto"])
    ap.add_argument("--channel", default="Kisan bdlega", help="Channel name")
    ap.add_argument("--badge", default="🔥 नई कृषि तकनीक 2026", help="Top alert badge text")
    ap.add_argument("--stat", default="बंपर मुनाफा", help="Stat callout text")
    ap.add_argument("--stat-sub", default="100% सटीक जानकारी", help="Stat callout subtext")
    args = ap.parse_args()

    out = make_thumbnail(
        text=args.text,
        output=args.output,
        font_path=args.font,
        font_style=args.font_style,
        background=args.background,
        video_path=args.video,
        channel_name=args.channel,
        top_badge=args.badge,
        stat_callout=args.stat,
        stat_sub=args.stat_sub
    )
    print(f"Generated High-CTR YouTube thumbnail: {out}")


if __name__ == "__main__":
    main()
