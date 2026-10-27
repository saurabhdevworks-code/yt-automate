"""Direct Backend API Automation for Google NotebookLM (via notebooklm-py).
No browser needed, no Playwright, no datacenter bot blocks! 100% Cloud Server Compatible."""
import argparse, json, os, subprocess, sys, time
from pathlib import Path

def run_cmd(cmd, check=True):
    print(f">>> Running: {' '.join(cmd)}")
    res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    if res.stdout:
        print(res.stdout.strip())
    if res.stderr and res.returncode != 0:
        print(f"[STDERR] {res.stderr.strip()}", file=sys.stderr)
    if check and res.returncode != 0:
        raise RuntimeError(f"Command failed with code {res.returncode}: {' '.join(cmd)}")
    return res

def main():
    parser = argparse.ArgumentParser(description="NotebookLM Direct API Cloud Automation")
    parser.add_argument("--sources", nargs="+", required=True)
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--storage-state", default="storage_state.json")
    parser.add_argument("--output", default="output/notebooklm")
    parser.add_argument("--timeout-minutes", type=int, default=75)
    parser.add_argument("--title", default="AI Hindi Video Overview")
    args = parser.parse_args()

    storage_path = str(Path(args.storage_state).resolve())
    out_dir = Path(args.output).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    target_mp4 = out_dir / "notebooklm_video.mp4"

    # [RESUME CHECK] If video already exists from a previous step / run, reuse it!
    if target_mp4.exists() and target_mp4.stat().st_size > 50000:
        print("\n==========================================================")
        print(f" [RESUME] Found existing completed video: {target_mp4} ({target_mp4.stat().st_size:,} bytes)")
        print(f" Skipping NotebookLM generation and reusing existing video!")
        print("==========================================================\n")
        return

    # Use title from metadata if available
    if args.title == "AI Hindi Video Overview" and Path("output/metadata.json").exists():
        try:
            meta = json.loads(Path("output/metadata.json").read_text(encoding="utf-8"))
            args.title = str(meta.get("title", args.title))[:50]
        except Exception:
            pass

    # 1. Verify Authentication
    print("[1/5] Checking NotebookLM RPC authentication...")
    run_cmd(["notebooklm", "--storage", storage_path, "auth", "check"])

    # 2. Create Notebook and set as active context
    print(f"[2/5] Creating notebook: {args.title}...")
    run_cmd(["notebooklm", "--storage", storage_path, "create", args.title, "-u"])

    # 3. Add Sources
    print("[3/5] Adding research sources...")
    for src in args.sources:
        src_path = str(Path(src).resolve())
        print(f"Adding source: {src_path}")
        run_cmd(["notebooklm", "--storage", storage_path, "source", "add", src_path])

    # 4. Generate Video (Trigger and wait) with automatic rate-limit cooldown handling
    print(f"[4/5] Triggering Hindi Video Overview generation (max wait: {args.timeout_minutes}m)...")
    prompt_file = str(Path(args.prompt).resolve())
    timeout_sec = args.timeout_minutes * 60
    
    gen_cmd = [
        "notebooklm", "--storage", storage_path,
        "generate", "video",
        "--prompt-file", prompt_file,
        "--language", "hi",
        "--wait",
        "--timeout", str(timeout_sec)
    ]

    max_attempts = 4
    delay_sec = 300  # 5 minutes cooldown between attempts
    for attempt in range(1, max_attempts + 1):
        res = run_cmd(gen_cmd, check=False)
        if res.returncode == 0:
            break
        
        combined_err = (res.stdout or "") + "\n" + (res.stderr or "")
        if "Rate limited" in combined_err or "RateLimitError" in combined_err or "rate_limit" in combined_err.lower():
            if attempt < max_attempts:
                print(f"\n[RATE-LIMIT COOLDOWN] Google NotebookLM has a temporary cooldown after generating a video.")
                print(f"Waiting 5 minutes for quota reset before retry ({attempt}/{max_attempts - 1})...\n")
                time.sleep(delay_sec)
                continue
        raise RuntimeError(f"Command failed with code {res.returncode}: {' '.join(gen_cmd)}")

    # 5. Download Video MP4
    print(f"[5/5] Downloading video to {target_mp4}...")
    run_cmd([
        "notebooklm", "--storage", storage_path,
        "download", "video",
        "--force",
        str(target_mp4)
    ])

    if target_mp4.exists() and target_mp4.stat().st_size > 50000:
        print(f"\n==========================================================")
        print(f" SUCCESS! Video downloaded: {target_mp4} ({target_mp4.stat().st_size:,} bytes)")
        print(f"==========================================================")
    else:
        raise RuntimeError(f"Video file missing or too small after download: {target_mp4}")

if __name__ == "__main__":
    main()
