"""High-CTR YouTube Thumbnail Generator for Kisan Badlega.
Creates world-class 1280x720 thumbnails for Indian Agriculture channels:
1. Dynamic background generation using Google Imagen 3 API (via GEMINI_API_KEY),
   with graceful fallbacks to Pollinations AI, NotebookLM video frame extraction, or cinematic gradients.
2. 3 High-CTR YouTube creator formats:
   - Format 1: 'scheme' (Government Schemes, Subsidies, PM Kisan, Kusum)
   - Format 2: 'profit' (Cash Crops, Polyhouse, Vermicompost, High Income)
   - Format 3: 'tech' (Smart Farming, Drones, Drip Irrigation, Modern Methods)
3. Pixel-perfect Canva-grade rendering using Headless Chrome / Chromium (HTML5 + CSS3 + Google Fonts),
   with pure PIL drawing fallback if Chrome is not installed.
"""
import argparse
import base64
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

W, H = 1280, 720
ROOT = Path(__file__).resolve().parents[1]
FONTS_DIR = ROOT / "assets" / "fonts"

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="hi">
<head>
<meta charset="UTF-8">
<style>
  @import url('https://fonts.googleapis.com/css2?family=Baloo+2:wght@700;800;900&family=Poppins:wght@700;800;900&display=swap');
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    width: 1280px; height: 720px; overflow: hidden;
    font-family: 'Baloo 2', 'Poppins', sans-serif;
    position: relative; background: #000;
  }}
  .bg-image {{
    position: absolute; top: 0; right: 0; width: 100%; height: 100%;
    background-image: url('{bg_url}');
    background-size: cover;
    background-position: {bg_pos};
  }}
  .vignette-overlay {{
    position: absolute; inset: 0;
    background: linear-gradient(90deg, 
      rgba(5, 12, 10, 0.96) 0%, 
      rgba(5, 12, 10, 0.92) 44%, 
      rgba(5, 12, 10, 0.65) 62%, 
      rgba(5, 12, 10, 0.15) 85%,
      transparent 100%);
  }}
  .bottom-vignette {{
    position: absolute; bottom: 0; left: 0; right: 0; height: 140px;
    background: linear-gradient(0deg, rgba(5, 12, 10, 0.85) 0%, transparent 100%);
  }}
  .content {{
    position: relative; z-index: 10; height: 100%;
    padding: 44px 52px; display: flex; flex-direction: column; justify-content: space-between;
  }}
  .top-bar {{ display: flex; align-items: center; gap: 16px; }}
  .channel-pill {{
    background: rgba(15, 23, 42, 0.9); backdrop-filter: blur(12px);
    border: 2px solid #334155; color: #f8fafc; padding: 8px 22px;
    border-radius: 12px; font-size: 20px; font-family: 'Poppins', sans-serif;
    font-weight: 800; display: flex; align-items: center; gap: 8px;
    box-shadow: 0 4px 15px rgba(0,0,0,0.6);
  }}
  .alert-pill {{
    background: {alert_bg};
    border: 2px solid {alert_border}; color: #ffffff; padding: 8px 22px;
    border-radius: 12px; font-size: 22px; font-weight: 800;
    box-shadow: 0 4px 20px rgba(239, 68, 68, 0.6);
  }}
  .headline-group {{ max-width: 720px; margin-top: -15px; }}
  .title-line-1 {{
    font-size: 82px; font-weight: 900; color: #ffffff; line-height: 1.08;
    text-shadow: 0 4px 14px rgba(0,0,0,0.95), 0 8px 28px rgba(0,0,0,0.9);
    margin-bottom: 8px;
  }}
  .highlight-banner {{
    display: inline-block;
    background: linear-gradient(135deg, #fde047 0%, #eab308 100%);
    color: #0f172a; font-size: 80px; font-weight: 900; line-height: 1.1;
    padding: 8px 30px; border-radius: 20px; border: 4px solid #ffffff;
    box-shadow: 0 10px 30px rgba(0,0,0,0.8), 0 0 45px rgba(234, 179, 8, 0.45);
    transform: rotate(-1.5deg); margin: 10px 0 18px -6px;
  }}
  .benefit-pill {{
    display: inline-flex; align-items: center; gap: 12px;
    background: linear-gradient(135deg, #15803d 0%, #166534 100%);
    border: 2px solid #4ade80; color: #f0fdf4; font-size: 38px;
    font-weight: 800; padding: 10px 26px; border-radius: 14px;
    box-shadow: 0 6px 20px rgba(22, 101, 52, 0.6);
  }}
  .bottom-badge {{
    display: inline-flex; align-items: center; gap: 18px;
    background: rgba(15, 23, 42, 0.88); backdrop-filter: blur(12px);
    border: 2px solid #eab308; padding: 12px 26px; border-radius: 16px;
    box-shadow: 0 8px 30px rgba(0,0,0,0.7); max-width: 540px;
  }}
  .badge-stat {{
    font-size: 52px; font-weight: 900; color: #fde047; line-height: 1;
    text-shadow: 0 2px 10px rgba(0,0,0,0.8);
  }}
  .badge-text {{
    font-size: 26px; font-weight: 800; color: #ffffff; line-height: 1.2;
  }}
  .badge-tag {{
    font-size: 17px; font-weight: 700; color: #4ade80; display: block; margin-top: 2px;
  }}
  .outer-frame {{
    position: absolute; inset: 0; border: 4px solid rgba(255, 255, 255, 0.15);
    pointer-events: none; z-index: 50;
  }}
</style>
</head>
<body>
  <div class="bg-image"></div>
  <div class="vignette-overlay"></div>
  <div class="bottom-vignette"></div>
  <div class="outer-frame"></div>
  <div class="content">
    <div class="top-bar">
      <div class="channel-pill">{channel}</div>
      <div class="alert-pill">{top_badge}</div>
    </div>
    <div class="headline-group">
      <div class="title-line-1">{line1}</div>
      <div class="highlight-banner">{highlight}</div>
      <div>
        <div class="benefit-pill">{benefit}</div>
      </div>
    </div>
    <div class="bottom-badge">
      <div class="badge-stat">{stat_num}</div>
      <div class="badge-text">
        {stat_title}
        <span class="badge-tag">{stat_tag}</span>
      </div>
    </div>
  </div>
</body>
</html>"""


def resolve_template_html(template_name: str = None, fmt_type: str = "scheme") -> str:
    """Resolve and load HTML template, prioritizing context/thumbnail_templates/."""
    templates_dirs = [
        ROOT / "context" / "thumbnail_templates",
        ROOT / "Context" / "thumbnail_templates",
        ROOT / "context" / "thumbnailTemplate",
        ROOT / "Context" / "thumbnailTemplate"
    ]

    # 1. If explicit template requested (e.g. template1, template2, template4_split)
    if template_name:
        req = str(template_name).strip().lower()
        for tdir in templates_dirs:
            if tdir.is_dir():
                for p in tdir.glob("*.html"):
                    if req == p.stem.lower() or req in p.stem.lower():
                        try:
                            print(f"[THUMBNAIL] Using custom template from {p.name}")
                            return p.read_text(encoding="utf-8")
                        except Exception:
                            pass

    # 2. Match based on format type
    target_map = {
        "scheme": ["template1_scheme.html", "template1.html", "scheme.html"],
        "profit": ["template2_profit.html", "template2.html", "profit.html"],
        "tech": ["template3_tech.html", "template3.html", "tech.html"],
        "split": ["template4_split.html", "template4.html", "split.html"],
        "bold": ["template5_bold.html", "template5.html", "bold.html"],
    }
    candidates = target_map.get(fmt_type, ["template1_scheme.html"])
    for tdir in templates_dirs:
        if tdir.is_dir():
            for c in candidates:
                p = tdir / c
                if p.is_file():
                    try:
                        return p.read_text(encoding="utf-8")
                    except Exception:
                        pass
            # Fallback to any html matching format keyword
            for p in tdir.glob("*.html"):
                if fmt_type in p.stem.lower():
                    try:
                        return p.read_text(encoding="utf-8")
                    except Exception:
                        pass

    # 3. Default built-in template
    return HTML_TEMPLATE


def find_custom_background() -> Path | None:
    """Look for any user-provided background in context/images/thumbnails/."""
    for candidate_dir in [
        ROOT / "context" / "images" / "thumbnails",
        ROOT / "Context" / "images" / "thumbnails",
        ROOT / "context" / "images" / "Thumbnails",
        ROOT / "Context" / "images" / "Thumbnails"
    ]:
        if candidate_dir.is_dir():
            for p in candidate_dir.glob("*"):
                if p.is_file() and p.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp"] and not p.name.startswith("README"):
                    return p
    return None


def populate_template(template_str: str, data: dict) -> str:
    """Safely populate placeholders {key} or {{key}} without interfering with CSS { ... } blocks."""
    res = template_str
    for k, v in data.items():
        res = res.replace(f"{{{{{k}}}}}", str(v))
        res = res.replace(f"{{{k}}}", str(v))
    return res


def find_chrome_executable() -> str:
    """Find Google Chrome, Chromium, or Microsoft Edge on host or CI."""
    # 1. System PATH
    for name in ["google-chrome", "chrome", "chromium", "chromium-browser", "msedge"]:
        path = shutil.which(name)
        if path:
            return path
    # 2. Windows known locations
    for win_path in [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"
    ]:
        if os.path.isfile(win_path):
            return win_path
    # 3. Linux known locations
    for linux_path in [
        "/usr/bin/google-chrome",
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser"
    ]:
        if os.path.isfile(linux_path):
            return linux_path
    return None


def generate_imagen3_background(prompt: str, api_key: str, out_path: Path) -> bool:
    """Generate 16:9 photorealistic visual using Google Imagen 3 API via GEMINI_API_KEY."""
    if not api_key:
        return False
    try:
        import requests
        url = f"https://generativelanguage.googleapis.com/v1beta/models/imagen-3.0-generate-002:predict?key={api_key}"
        payload = {
            "instances": [{"prompt": prompt}],
            "parameters": {
                "sampleCount": 1,
                "aspectRatio": "16:9",
                "outputMimeType": "image/jpeg"
            }
        }
        res = requests.post(url, json=payload, timeout=60)
        if res.status_code == 200:
            data = res.json()
            predictions = data.get("predictions", [])
            if predictions and "bytesBase64Encoded" in predictions[0]:
                b64 = predictions[0]["bytesBase64Encoded"]
                out_path.write_bytes(base64.b64decode(b64))
                print(f"[IMAGEN 3] Successfully generated photorealistic AI background: {out_path}")
                return True
        print(f"[IMAGEN 3] Status {res.status_code}: {res.text[:120]}")
    except Exception as exc:
        print(f"[IMAGEN 3] Warning: Imagen 3 request failed: {exc}")
    return False


def generate_pollinations_background(prompt: str, out_path: Path) -> bool:
    """Fallback 1: Free Pollinations Flux image generator."""
    try:
        encoded = urllib.parse.quote(prompt)
        url = f"https://image.pollinations.ai/prompt/{encoded}?width=1280&height=720&model=flux&nologo=true&seed=42"
        urllib.request.urlretrieve(url, str(out_path))
        if out_path.exists() and out_path.stat().st_size > 10000:
            print(f"[POLLINATIONS] Successfully fetched background: {out_path}")
            return True
    except Exception as exc:
        print(f"[POLLINATIONS] Warning: Pollinations fetch failed: {exc}")
    return False


def extract_video_frame(video_path: Path, output_frame: Path, timestamp: str = "00:00:08") -> bool:
    """Fallback 2: Extract a high quality scenic frame from video using ffmpeg."""
    if not video_path or not Path(video_path).exists():
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
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=20)
        return res.returncode == 0 and output_frame.exists() and output_frame.stat().st_size > 1000
    except Exception:
        return False


def create_gradient_backdrop(out_path: Path):
    """Fallback 3: Rich cinematic multi-stop emerald & navy gradient."""
    base = Image.new("RGB", (W, H), (10, 25, 18))
    draw = ImageDraw.Draw(base)
    for y in range(H):
        for x in range(0, W, 4):
            t = (x / W) * 0.6 + (y / H) * 0.4
            r = int(6 + 18 * t)
            g = int(28 + 48 * (1 - t * 0.5))
            b = int(22 + 45 * t)
            draw.rectangle([x, y, x + 4, y + 1], fill=(r, g, b))
    base.save(str(out_path), quality=95)


def render_with_chrome(html_file: Path, out_path: Path) -> bool:
    """Render HTML template to 1280x720 JPEG using Chrome or Edge headless."""
    chrome_path = find_chrome_executable()
    if not chrome_path:
        return False

    cmd = [
        chrome_path,
        "--headless=new",
        f"--screenshot={out_path}",
        "--window-size=1280,720",
        "--hide-scrollbars",
        "--virtual-time-budget=3000",
        "--disable-gpu",
        "--no-sandbox",
        html_file.as_uri()
    ]
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
        return out_path.exists() and out_path.stat().st_size > 5000
    except Exception as exc:
        print(f"[CHROME] Headless render error: {exc}")
        return False


def make_thumbnail(
    metadata_path: str = None,
    output: str = "output/thumbnail.jpg",
    video_path: str = None,
    custom_bg: str = None,
    text: str = None,
    channel_name: str = "Kisan bdlega",
    template: str = None
) -> str:
    """Main entrypoint: generates a pro high-CTR YouTube thumbnail."""
    out_path = Path(output).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    temp_dir = out_path.parent / "_thumb_temp"
    temp_dir.mkdir(parents=True, exist_ok=True)

    # 1. Parse Metadata or set defaults
    meta = {}
    if metadata_path and Path(metadata_path).is_file():
        try:
            meta = json.loads(Path(metadata_path).read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[WARN] Failed to load metadata: {e}")

    # Determine Format: 'scheme', 'profit', or 'tech'
    fmt_type = meta.get("thumbnail_format", "")
    if not fmt_type:
        topic_lower = (meta.get("topic") or meta.get("title") or text or "").lower()
        if any(k in topic_lower for k in ["सब्सिडी", "योजना", "निधि", "kusum", "pm kisan", "scheme"]):
            fmt_type = "scheme"
        elif any(k in topic_lower for k in ["कमाई", "मुनाफा", "लाख", "करोड़", "business", "profit", "पॉलीहाउस"]):
            fmt_type = "profit"
        else:
            fmt_type = "tech"

    # Default values per format
    if fmt_type == "scheme":
        alert_bg = "linear-gradient(135deg, #ef4444 0%, #dc2626 100%)"
        alert_border = "#fca5a5"
        default_top = "🚨 सरकारी योजना 2026"
        default_line1 = meta.get("thumbnail_line1") or "सरकारी योजना से"
        default_highlight = meta.get("thumbnail_highlight") or "80% सब्सिडी तुरंत!"
        default_benefit = meta.get("thumbnail_benefit") or "⚡ बिजली बिल ₹0 • पानी भरपूर सप्लाई"
        default_num = meta.get("thumbnail_stat_num") or "80%"
        default_title = meta.get("thumbnail_stat_title") or "सरकारी सब्सिडी"
        default_tag = meta.get("thumbnail_stat_tag") or "✔ ऑनलाइन आवेदन शुरू"
        default_prompt = (
            "Cinematic YouTube thumbnail of an Indian farmer smiling with thumbs up standing next to "
            "modern solar panels powering an irrigation pump gushing clean water into a lush green field, "
            "sunny blue sky, photorealistic, 4K commercial photography quality, vivid saturated colors."
        )
    elif fmt_type == "profit":
        alert_bg = "linear-gradient(135deg, #f59e0b 0%, #d97706 100%)"
        alert_border = "#fde68a"
        default_top = "💰 बंपर कमाई 2026"
        default_line1 = meta.get("thumbnail_line1") or "आधुनिक खेती से"
        default_highlight = meta.get("thumbnail_highlight") or "₹5 लाख महीना कमाई!"
        default_benefit = meta.get("thumbnail_benefit") or "🚀 कम जमीन में 4x ज्यादा मुनाफा"
        default_num = meta.get("thumbnail_stat_num") or "₹5L"
        default_title = meta.get("thumbnail_stat_title") or "प्रति महीना कमाई"
        default_tag = meta.get("thumbnail_stat_tag") or "✔ 100% सफल मॉडल"
        default_prompt = (
            "Cinematic YouTube thumbnail inside a modern high-tech commercial polyhouse greenhouse in India, "
            "lush rows of ripe red tomatoes, proud Indian farmer holding fresh harvest basket, "
            "diffused greenhouse sunlight, photorealistic, 4K commercial agricultural photography, vivid rich colors."
        )
    else:  # tech
        alert_bg = "linear-gradient(135deg, #ef4444 0%, #dc2626 100%)"
        alert_border = "#fca5a5"
        default_top = "🔥 2026 की नई तकनीक"
        default_line1 = meta.get("thumbnail_line1") or "स्मार्ट खेती तकनीक से"
        default_highlight = meta.get("thumbnail_highlight") or "कम पानी, बंपर पैदावार!"
        default_benefit = meta.get("thumbnail_benefit") or "💧 80% पानी की बचत + ड्रोन छिड़काव"
        default_num = meta.get("thumbnail_stat_num") or "3X"
        default_title = meta.get("thumbnail_stat_title") or "बंपर पैदावार"
        default_tag = meta.get("thumbnail_stat_tag") or "✔ 100% सटीक जानकारी"
        default_prompt = (
            "Cinematic YouTube thumbnail of an Indian smart farmer holding an illuminated telemetry tablet "
            "in a lush green crop field with drip irrigation pipes and an agricultural drone hovering in golden hour sky, "
            "4K commercial photography quality, vivid saturated colors."
        )

    # Use explicit text if passed via CLI
    if text:
        default_highlight = text

    # 2. Prepare Background Image
    bg_img_path = temp_dir / "bg_visual.jpg"
    bg_ready = False

    # A. Custom image passed or found in context/images/thumbnails
    if custom_bg and Path(custom_bg).is_file():
        shutil.copy(custom_bg, bg_img_path)
        bg_ready = True
    elif not custom_bg:
        auto_bg = find_custom_background()
        if auto_bg:
            print(f"[THUMBNAIL] Using custom background from {auto_bg}")
            shutil.copy(auto_bg, bg_img_path)
            bg_ready = True

    # B. Imagen 3 via GEMINI_API_KEY
    gemini_key = os.getenv("GEMINI_API_KEY", "")
    img_prompt = meta.get("thumbnail_image_prompt") or default_prompt
    if not bg_ready and gemini_key:
        print("[THUMBNAIL] Attempting Google Imagen 3 generation...")
        bg_ready = generate_imagen3_background(img_prompt, gemini_key, bg_img_path)

    # C. Pollinations Flux fallback
    if not bg_ready:
        print("[THUMBNAIL] Falling back to Pollinations AI generation...")
        bg_ready = generate_pollinations_background(img_prompt, bg_img_path)

    # D. Video frame extraction fallback
    if not bg_ready and video_path and Path(video_path).is_file():
        print("[THUMBNAIL] Falling back to video frame extraction...")
        bg_ready = extract_video_frame(Path(video_path), bg_img_path)

    # E. Gradient fallback
    if not bg_ready:
        print("[THUMBNAIL] Falling back to cinematic gradient...")
        create_gradient_backdrop(bg_img_path)
        bg_ready = True

    # 3. Render via Chrome Headless
    fmt_data = {
        "bg_url": bg_img_path.name,
        "bg_pos": "right 30%",
        "channel": f"🌾 {channel_name.upper()}",
        "alert_bg": alert_bg,
        "alert_border": alert_border,
        "top_badge": meta.get("thumbnail_top_badge") or default_top,
        "line1": meta.get("thumbnail_line1") or default_line1,
        "highlight": meta.get("thumbnail_highlight") or default_highlight,
        "benefit": meta.get("thumbnail_benefit") or default_benefit,
        "stat_num": meta.get("thumbnail_stat_num") or default_num,
        "stat_title": meta.get("thumbnail_stat_title") or default_title,
        "stat_tag": meta.get("thumbnail_stat_tag") or default_tag,
    }

    html_tpl = resolve_template_html(template_name=template, fmt_type=fmt_type)
    html_file = temp_dir / "thumbnail.html"
    html_file.write_text(populate_template(html_tpl, fmt_data), encoding="utf-8")

    rendered = render_with_chrome(html_file, out_path)
    if rendered:
        print(f"[THUMBNAIL] Successfully rendered Pro High-CTR Thumbnail: {out_path}")
        return str(out_path)

    # Fallback to pure Pillow rendering if Chrome unavailable
    print("[THUMBNAIL] Chrome not found; using Pillow rendering fallback...")
    _render_pillow_fallback(bg_img_path, out_path, fmt_data)
    return str(out_path)


def _render_pillow_fallback(bg_path: Path, out_path: Path, data: dict):
    """Pillow fallback rendering in case Chrome is not found on environment."""
    img = Image.open(bg_path).convert("RGB").resize((W, H))
    draw = ImageDraw.Draw(img)

    # Dark gradient overlay
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ov_draw = ImageDraw.Draw(overlay)
    for x in range(W):
        t = x / W
        alpha = int(245 * max(0, 1 - t * 1.3))
        ov_draw.line([(x, 0), (x, H)], fill=(5, 12, 10, alpha))
    img.paste(Image.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, 0)), overlay).convert("RGB"), (0, 0), overlay)

    draw = ImageDraw.Draw(img)
    font_large = ImageFont.load_default()
    # Draw simple fallback text
    draw.text((60, 60), data["top_badge"], fill=(239, 68, 68), font=font_large)
    draw.text((60, 140), data["line1"], fill=(255, 255, 255), font=font_large)
    draw.text((60, 240), data["highlight"], fill=(250, 204, 21), font=font_large)
    draw.text((60, 340), data["benefit"], fill=(74, 222, 128), font=font_large)
    img.save(str(out_path), quality=95)


def main():
    ap = argparse.ArgumentParser(description="Generate high-CTR YouTube thumbnail")
    ap.add_argument("--metadata", help="Path to metadata.json containing title and prompt")
    ap.add_argument("--text", default="", help="Main catchy thumbnail text")
    ap.add_argument("--output", default="output/thumbnail.jpg", help="Output thumbnail path")
    ap.add_argument("--background", help="Custom background image path")
    ap.add_argument("--video", help="Video path to extract high quality frame")
    ap.add_argument("--font", default="", help="Specific font path (kept for compatibility)")
    ap.add_argument("--font-style", default="baloo", help="Font style (kept for compatibility)")
    ap.add_argument("--channel", default="Kisan bdlega", help="Channel name")
    ap.add_argument("--template", help="Specific template name (e.g. template1, template2, template4_split)")
    args = ap.parse_args()

    out = make_thumbnail(
        metadata_path=args.metadata,
        output=args.output,
        video_path=args.video,
        custom_bg=args.background,
        text=args.text,
        channel_name=args.channel,
        template=args.template
    )
    print(f"Generated High-CTR YouTube thumbnail: {out}")


if __name__ == "__main__":
    main()
