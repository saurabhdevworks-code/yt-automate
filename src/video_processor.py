"""Video Post-Processing & Customization Engine.
Handles:
1. Google Drive / Direct link downloading for Intro video & Thumbnail.
2. Trimming video start/end using ffmpeg.
3. Adding intro video seamlessly to NotebookLM generated video.
4. Overriding YouTube metadata (Title, Description, Tags).
"""
import argparse, json, os, re, shutil, subprocess, sys
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

        # Fallback direct Google Drive download
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

def trim_video(input_video: Path, output_video: Path, start: str, end: str):
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
    parser = argparse.ArgumentParser(description="Process video: trimming, intro, thumbnail, metadata")
    parser.add_argument("--video", required=True, help="Main NotebookLM video path")
    parser.add_argument("--intro-url", default="", help="Intro video link (Google Drive / direct URL)")
    parser.add_argument("--trim-start", default="", help="Trim start (seconds or HH:MM:SS)")
    parser.add_argument("--trim-end", default="", help="Trim end timestamp (seconds or HH:MM:SS)")
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

    # 1. Trimming (if requested)
    if args.trim_start.strip() or args.trim_end.strip():
        trimmed_video = work_dir / "trimmed_temp.mp4"
        trim_video(current_video, trimmed_video, args.trim_start.strip(), args.trim_end.strip())
        current_video = trimmed_video

    # 2. Add Intro Video (if requested)
    if args.intro_url.strip():
        intro_path = work_dir / "downloaded_intro.mp4"
        if download_file(args.intro_url.strip(), intro_path):
            merged_video = work_dir / "merged_with_intro.mp4"
            try:
                concat_intro_video(intro_path, current_video, merged_video)
                current_video = merged_video
            except Exception as e:
                print(f"[WARNING] Could not attach intro: {e}. Keeping video as is.")

    # 3. Replace original video with processed video if modified
    if current_video != video_path and current_video.exists():
        backup_path = video_path.with_name("notebooklm_video_raw.mp4")
        if not backup_path.exists():
            shutil.copy2(video_path, backup_path)
        shutil.copy2(current_video, video_path)
        print(f"\n[SUCCESS] Final processed video saved to: {video_path} ({video_path.stat().st_size:,} bytes)")

    # 4. Custom Thumbnail (if requested)
    if args.custom_thumbnail_url.strip():
        thumb_out = Path(args.thumbnail_out).resolve()
        if download_file(args.custom_thumbnail_url.strip(), thumb_out):
            print(f"[SUCCESS] Custom thumbnail saved to: {thumb_out}")

    # 5. Override YouTube Metadata (if provided)
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
