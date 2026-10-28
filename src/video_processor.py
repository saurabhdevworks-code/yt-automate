"""Video Post-Processing & Customization Engine.
Handles:
1. Google Drive / Direct link downloading for Intro video, Watermark & Thumbnail.
2. Trimming video start/end using ffmpeg (Auto mode trims the last 3s NotebookLM outro).
3. Hiding/Replacing NotebookLM watermark with custom image from assets folder or upload URL.
4. Adding intro video seamlessly to NotebookLM generated video.
5. Overriding YouTube metadata (Title, Description, Tags).
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


def download_file(url: str, dest_path: Path) -> bool:
    """Download file from Google Drive or direct HTTP/HTTPS URL."""
    url = url.strip()
    if not url:
        return False

    dest_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"\n[DOWNLOADER] Fetching media from: {url}")

    # Check if Google Drive link
    gdrive_match = re.search(r"drive\.google\.com\/(?:file\/d\/|open\?id=|uc\?id=)([a-zA-Z0-9_-]+)", url)
    if gdrive_match:
        file_id = gdrive_match.group(1)
        print(f"[DOWNLOADER] Detected Google Drive file ID: {file_id}")

        # Try gdown first
        try:
            import gdown
            print("[DOWNLOADER] Using gdown to fetch Google Drive file...")
            res = gdown.download(id=file_id, output=str(dest_path), quiet=False, fuzzy=True)
            if res and dest_path.exists() and dest_path.stat().st_size > 1000:
                print(f"[DOWNLOADER] Successfully downloaded: {dest_path} ({dest_path.stat().st_size:,} bytes)")
                return True
        except Exception as e:
            print(f"[DOWNLOADER] gdown failed ({e}), falling back to direct stream...")

        direct_url = f"https://drive.google.com/uc?export=download&id={file_id}"
    else:
        direct_url = url

    try:
        import requests
        with requests.get(direct_url, stream=True, timeout=120, allow_redirects=True) as r:
            r.raise_for_status()
            with open(dest_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        f.write(chunk)
        if dest_path.exists() and dest_path.stat().st_size > 1000:
            print(f"[DOWNLOADER] Successfully downloaded: {dest_path} ({dest_path.stat().st_size:,} bytes)")
            return True
    except Exception as exc:
        print(f"[DOWNLOADER ERROR] Failed to download {url}: {exc}")

    return False


def get_video_duration(video_path: Path) -> float:
    """Get video duration in seconds using ffprobe or ffmpeg fallback."""
    # 1. ffprobe format duration
    try:
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(video_path)
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if res.returncode == 0 and res.stdout.strip():
            val = float(res.stdout.strip())
            if val > 0:
                return val
    except Exception:
        pass

    # 2. ffprobe video stream duration
    try:
        cmd = [
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(video_path)
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if res.returncode == 0 and res.stdout.strip():
            val = float(res.stdout.strip())
            if val > 0:
                return val
    except Exception:
        pass

    # 3. ffmpeg -i parsing
    try:
        cmd = ["ffmpeg", "-i", str(video_path)]
        res = subprocess.run(cmd, capture_output=True, text=True, check=False)
        match = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", res.stderr)
        if match:
            h, m, s = match.groups()
            return int(h) * 3600 + int(m) * 60 + float(s)
    except Exception:
        pass

    return 0.0


def get_video_dimensions(video_path: Path) -> tuple[int, int]:
    """Get video width and height using ffprobe or ffmpeg fallback."""
    try:
        cmd = [
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height",
            "-of", "csv=s=x:p=0",
            str(video_path)
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if res.returncode == 0 and "x" in res.stdout:
            parts = res.stdout.strip().split("x")
            return int(parts[0]), int(parts[1])
    except Exception:
        pass

    try:
        cmd = ["ffmpeg", "-i", str(video_path)]
        res = subprocess.run(cmd, capture_output=True, text=True, check=False)
        match = re.search(r"Video:.*,\s*(\d{3,4})x(\d{3,4})", res.stderr)
        if match:
            return int(match.group(1)), int(match.group(2))
    except Exception:
        pass

    return 1920, 1080


def trim_video(input_video: Path, output_video: Path, start: str = "", end: str = ""):
    """Trim video start and/or end using ffmpeg."""
    cmd = ["ffmpeg", "-y"]
    if start:
        cmd.extend(["-ss", str(start)])
    if end:
        cmd.extend(["-to", str(end)])
    cmd.extend([
        "-i", str(input_video),
        "-c:v", "libx264",
        "-preset", "fast",
        "-c:a", "aac",
        "-b:a", "192k",
        str(output_video)
    ])
    print(f"\n[TRIM] Running: {' '.join(cmd)}")
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"[TRIM ERROR] ffmpeg failed:\n{res.stderr}", file=sys.stderr)
        raise RuntimeError("Failed to trim video")
    print(f"[TRIM] Succeeded -> {output_video} ({output_video.stat().st_size:,} bytes)")


def find_watermark_image(custom_path: str = "", base_dir: Path = None) -> Path | None:
    """Find watermark/logo image from custom path, assets directory, or project root."""
    if base_dir is None:
        base_dir = Path(".").resolve()

    # 1. Direct custom path if specified and exists
    if custom_path:
        p = Path(custom_path)
        if not p.is_absolute():
            p = base_dir / p
        if p.exists() and p.is_file():
            return p.resolve()

    # 2. Check candidate locations in assets/
    candidate_names = [
        "watermark.png", "watermark.jpg", "watermark.jpeg", "watermark.webp",
        "logo.png", "logo.jpg", "logo.jpeg", "logo.webp",
        "channel_logo.png", "channel_logo.jpg", "badge.png",
        "channel_watermark.png"
    ]
    assets_dir = base_dir / "assets"
    if assets_dir.exists():
        for name in candidate_names:
            candidate = assets_dir / name
            if candidate.exists() and candidate.is_file() and candidate.stat().st_size > 0:
                return candidate.resolve()

    # 3. Check config/settings.json for configured watermark path
    settings_file = base_dir / "config" / "settings.json"
    if settings_file.exists():
        try:
            settings = json.loads(settings_file.read_text(encoding="utf-8"))
            cfg_path = settings.get("watermark_image") or settings.get("watermark", {}).get("image_path")
            if cfg_path:
                cp = Path(cfg_path)
                if not cp.is_absolute():
                    cp = base_dir / cp
                if cp.exists() and cp.is_file():
                    return cp.resolve()
        except Exception:
            pass

    return None


def prepare_watermark_badge(
    image_path: Path,
    target_w: int,
    target_h: int,
    output_path: Path
) -> Path:
    """Prepare and optimize watermark badge using Pillow to completely obscure the NotebookLM watermark.
    
    If the image has transparency, composites it over an opaque dark rounded pill
    so that the underlying 'NotebookLM' text/logo cannot peek through.
    """
    try:
        from PIL import Image, ImageDraw

        with Image.open(image_path) as img:
            img = img.convert("RGBA")
            orig_w, orig_h = img.size

            # Compute scaling to fit comfortably within target bounding box with padding
            pad_x = max(10, int(target_w * 0.06))
            pad_y = max(6, int(target_h * 0.08))
            avail_w = max(10, target_w - (pad_x * 2))
            avail_h = max(10, target_h - (pad_y * 2))

            ratio = min(avail_w / orig_w, avail_h / orig_h)
            new_w = max(1, int(orig_w * ratio))
            new_h = max(1, int(orig_h * ratio))

            resized_img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

            # Create solid badge base canvas (Opaque dark charcoal background)
            # This guarantees 100% masking of the NotebookLM watermark beneath
            badge = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0))
            draw = ImageDraw.Draw(badge)

            # Draw rounded pill background
            radius = min(target_h // 2, 14)
            # Primary pill background: dark elegant slate (#0f172a with 96% opacity)
            draw.rounded_rectangle(
                [(0, 0), (target_w - 1, target_h - 1)],
                radius=radius,
                fill=(15, 23, 42, 245),
                outline=(51, 65, 85, 255),
                width=2
            )

            # Paste logo centered inside pill
            pos_x = (target_w - new_w) // 2
            pos_y = (target_h - new_h) // 2
            badge.alpha_composite(resized_img, (pos_x, pos_y))

            output_path.parent.mkdir(parents=True, exist_ok=True)
            badge.save(output_path, format="PNG")
            return output_path
    except Exception as e:
        print(f"[WATERMARK] Pillow badge rendering failed ({e}), using raw image directly.")
        shutil.copy2(image_path, output_path)
        return output_path


def apply_watermark_overlay(
    input_video: Path,
    watermark_image: Path,
    output_video: Path,
    position: str = "bottom-right",
    margin_x: int = None,
    margin_y: int = None,
    work_dir: Path = None
):
    """Overlay replacement image on video using ffmpeg, covering NotebookLM watermark."""
    print(f"\n[WATERMARK] Covering NotebookLM watermark with custom image: {watermark_image.name}")
    vid_w, vid_h = get_video_dimensions(input_video)
    print(f"[WATERMARK] Detected video resolution: {vid_w}x{vid_h}")

    # NotebookLM watermark spans roughly 14% width and 6.5% height in bottom-right
    target_w = max(240, int(vid_w * 0.155))
    target_h = max(60, int(vid_h * 0.068))

    if margin_x is None:
        margin_x = max(18, int(vid_w * 0.015))
    if margin_y is None:
        margin_y = max(18, int(vid_h * 0.022))

    if work_dir is None:
        work_dir = output_video.parent

    prepared_badge = work_dir / "prepared_watermark_badge.png"
    badge_path = prepare_watermark_badge(watermark_image, target_w, target_h, prepared_badge)

    # Position coordinates formula
    pos = position.lower()
    if pos == "bottom-right":
        overlay_coord = f"W-w-{margin_x}:H-h-{margin_y}"
    elif pos == "bottom-left":
        overlay_coord = f"{margin_x}:H-h-{margin_y}"
    elif pos == "top-right":
        overlay_coord = f"W-w-{margin_x}:{margin_y}"
    elif pos == "top-left":
        overlay_coord = f"{margin_x}:{margin_y}"
    else:
        overlay_coord = f"W-w-{margin_x}:H-h-{margin_y}"

    cmd = [
        "ffmpeg", "-y",
        "-i", str(input_video),
        "-i", str(badge_path),
        "-filter_complex", f"[0:v][1:v]overlay={overlay_coord}[v]",
        "-map", "[v]",
        "-map", "0:a?",
        "-c:v", "libx264",
        "-preset", "fast",
        "-c:a", "copy",
        str(output_video)
    ]
    print(f"[WATERMARK] Running ffmpeg overlay at [{overlay_coord}] (Size: {target_w}x{target_h})...")
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"[WATERMARK ERROR] ffmpeg overlay failed:\n{res.stderr}", file=sys.stderr)
        raise RuntimeError("Failed to overlay watermark image on video")

    print(f"[WATERMARK] Successfully hid watermark -> {output_video} ({output_video.stat().st_size:,} bytes)")


def concat_intro_video(intro_video: Path, main_video: Path, output_video: Path):
    """Concatenate intro video with main video, standardizing resolution and audio."""
    print(f"\n[INTRO] Merging Intro ({intro_video}) + Main ({main_video}) -> {output_video}...")

    # Check if intro has audio
    probe_cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "a:0",
        "-show_entries", "stream=codec_type",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(intro_video)
    ]
    probe_res = subprocess.run(probe_cmd, capture_output=True, text=True)
    has_audio = bool(probe_res.stdout.strip())

    if has_audio:
        filter_complex = (
            "[0:v]scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30[v0];"
            "[1:v]scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30[v1];"
            "[0:a]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo[a0];"
            "[1:a]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo[a1];"
            "[v0][a0][v1][a1]concat=n=2:v=1:a=1[v][a]"
        )
    else:
        # Generate silent audio track for intro if absent
        filter_complex = (
            "[0:v]scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30[v0];"
            "[1:v]scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30[v1];"
            "aevalsrc=0:d=1[a0];"
            "[1:a]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo[a1];"
            "[v0][1:a]concat=n=2:v=1:a=1[v][a]"
        )

    cmd = [
        "ffmpeg", "-y",
        "-i", str(intro_video),
        "-i", str(main_video),
        "-filter_complex", filter_complex,
        "-map", "[v]",
        "-map", "[a]",
        "-c:v", "libx264",
        "-preset", "fast",
        "-c:a", "aac",
        "-b:a", "192k",
        str(output_video)
    ]
    print(f"[INTRO] Running concat...")
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"[INTRO ERROR] ffmpeg concat failed:\n{res.stderr}", file=sys.stderr)
        raise RuntimeError("Failed to attach intro to video")
    print(f"[INTRO] Succeeded -> {output_video} ({output_video.stat().st_size:,} bytes)")


def main():
    parser = argparse.ArgumentParser(description="Process video: trimming, watermark replacement, intro, thumbnail, metadata")
    parser.add_argument("--video", required=True, help="Main NotebookLM video path")
    parser.add_argument("--mode", default="auto", choices=["auto", "custom"], help="Execution mode (auto or custom)")
    parser.add_argument("--trim-last-seconds", type=float, default=3.0, help="Seconds to trim from end in auto mode (default: 3.0)")
    parser.add_argument("--trim-start", default="", help="Trim start timestamp (seconds or HH:MM:SS)")
    parser.add_argument("--trim-end", default="", help="Trim end timestamp (seconds or HH:MM:SS)")
    parser.add_argument("--watermark-image", default="", help="Path to watermark/logo image to hide NotebookLM watermark")
    parser.add_argument("--watermark-url", default="", help="Watermark image link (Google Drive / Direct URL)")
    parser.add_argument("--watermark-position", default="bottom-right", choices=["bottom-right", "bottom-left", "top-right", "top-left"], help="Watermark placement position")
    parser.add_argument("--disable-watermark", action="store_true", help="Disable watermark hiding/replacement")
    parser.add_argument("--intro-url", default="", help="Intro video link (Google Drive / direct URL)")
    parser.add_argument("--custom-thumbnail-url", default="", help="Custom thumbnail link")
    parser.add_argument("--thumbnail-out", default="output/thumbnail.jpg", help="Output thumbnail path")
    parser.add_argument("--metadata", default="output/metadata.json", help="Metadata JSON path")
    parser.add_argument("--custom-title", default="", help="Custom YouTube title")
    parser.add_argument("--custom-description", default="", help="Custom YouTube description")
    parser.add_argument("--custom-tags", default="", help="Custom YouTube tags (comma-separated)")
    args = parser.parse_args()

    video_path = Path(args.video).resolve()
    if not video_path.exists() or video_path.stat().st_size == 0:
        print(f"[ERROR] Main video not found at: {video_path}")
        return

    work_dir = video_path.parent / "temp_processing"
    work_dir.mkdir(parents=True, exist_ok=True)
    current_video = video_path

    # =========================================================================
    # 1. Trimming Logic
    # Case of auto: trim the video from last 3s (cuts off NotebookLM outro card)
    # Case of custom: respects explicit --trim-start / --trim-end
    # =========================================================================
    start_trim = args.trim_start.strip()
    end_trim = args.trim_end.strip()

    if args.mode == "auto" and not end_trim and args.trim_last_seconds > 0:
        duration = get_video_duration(current_video)
        if duration > args.trim_last_seconds:
            calc_end = duration - args.trim_last_seconds
            end_trim = f"{calc_end:.2f}"
            print(f"\n[AUTO MODE] Video duration: {duration:.2f}s. Automatically trimming final {args.trim_last_seconds}s (NotebookLM outro). End set to: {end_trim}s.")
        else:
            print(f"\n[AUTO MODE] Video duration ({duration:.2f}s) is shorter than trim margin ({args.trim_last_seconds}s). Skipping auto-trim.")

    if start_trim or end_trim:
        trimmed_video = work_dir / "trimmed_temp.mp4"
        try:
            trim_video(current_video, trimmed_video, start_trim, end_trim)
            current_video = trimmed_video
        except Exception as e:
            print(f"[WARNING] Trimming failed: {e}. Proceeding with current video.")

    # =========================================================================
    # 2. Watermark Replacement (Applied in BOTH auto & custom modes)
    # Replaces/hides NotebookLM watermark in bottom-right corner with an image
    # from uploaded URL or assets/ folder.
    # =========================================================================
    if not args.disable_watermark:
        watermark_img_path = None

        # Priority A: Download from URL if supplied
        if args.watermark_url.strip():
            downloaded_wm = work_dir / "downloaded_watermark.png"
            if download_file(args.watermark_url.strip(), downloaded_wm):
                watermark_img_path = downloaded_wm

        # Priority B: Use local image path or search assets folder
        if not watermark_img_path:
            watermark_img_path = find_watermark_image(args.watermark_image.strip())

        if watermark_img_path and watermark_img_path.exists():
            watermarked_video = work_dir / "watermarked_temp.mp4"
            try:
                apply_watermark_overlay(
                    input_video=current_video,
                    watermark_image=watermark_img_path,
                    output_video=watermarked_video,
                    position=args.watermark_position,
                    work_dir=work_dir
                )
                current_video = watermarked_video
            except Exception as e:
                print(f"[WARNING] Could not apply watermark overlay: {e}. Keeping video as is.")
        else:
            print("\n[WATERMARK] No watermark replacement image found in assets/ or via URL; keeping original video.")

    # =========================================================================
    # 3. Add Intro Video (if requested)
    # Concatenated after watermark so intro video remains untouched
    # =========================================================================
    if args.intro_url.strip():
        intro_path = work_dir / "downloaded_intro.mp4"
        if download_file(args.intro_url.strip(), intro_path):
            merged_video = work_dir / "merged_with_intro.mp4"
            try:
                concat_intro_video(intro_path, current_video, merged_video)
                current_video = merged_video
            except Exception as e:
                print(f"[WARNING] Could not attach intro: {e}. Keeping video as is.")

    # =========================================================================
    # 4. Replace original video with final processed video if modified
    # =========================================================================
    if current_video != video_path and current_video.exists():
        backup_path = video_path.with_name("notebooklm_video_raw.mp4")
        if not backup_path.exists():
            shutil.copy2(video_path, backup_path)
        shutil.copy2(current_video, video_path)
        print(f"\n[SUCCESS] Final processed video saved to: {video_path} ({video_path.stat().st_size:,} bytes)")

    # =========================================================================
    # 5. Custom Thumbnail (if requested)
    # =========================================================================
    if args.custom_thumbnail_url.strip():
        thumb_out = Path(args.thumbnail_out).resolve()
        if download_file(args.custom_thumbnail_url.strip(), thumb_out):
            print(f"[SUCCESS] Custom thumbnail saved to: {thumb_out}")

    # =========================================================================
    # 6. Override YouTube Metadata (if provided)
    # =========================================================================
    meta_path = Path(args.metadata).resolve()
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            updated = False
            if args.custom_title.strip():
                meta["title"] = args.custom_title.strip()[:100]
                updated = True
            if args.custom_description.strip():
                meta["description"] = args.custom_description.strip()[:5000]
                updated = True
            if args.custom_tags.strip():
                meta["tags"] = [t.strip() for t in args.custom_tags.split(",") if t.strip()][:30]
                updated = True
            if updated:
                meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
                print(f"[METADATA] Updated {meta_path} with custom YouTube title/description/tags.")
        except Exception as e:
            print(f"[METADATA WARNING] Could not update metadata: {e}")

    # Clean temporary folder
    try:
        shutil.rmtree(work_dir)
    except Exception:
        pass


if __name__ == "__main__":
    main()
