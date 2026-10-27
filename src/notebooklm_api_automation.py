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

    # 1. Verify Authentication & Auto-heal/Refresh
    print("[1/5] Checking NotebookLM RPC authentication...")
    auth_res = run_cmd(["notebooklm", "--storage", storage_path, "auth", "check", "--test"], check=False)
    if auth_res.returncode != 0:
        print("\n[AUTH NOTICE] Token fetch check failed. Attempting to refresh / re-mint session...")
        refresh_res = run_cmd(["notebooklm", "--storage", storage_path, "auth", "refresh"], check=False)
        auth_retry = run_cmd(["notebooklm", "--storage", storage_path, "auth", "check", "--test"], check=False)
        if auth_retry.returncode != 0:
            print("\n[AUTH ERROR] Could not authenticate with Google NotebookLM.", file=sys.stderr)
            print("Session cookies have expired and no valid Master Token was found.", file=sys.stderr)
            raise RuntimeError("Authentication expired or invalid. Please configure NOTEBOOKLM_MASTER_TOKEN_JSON.")

    # 2. Create Notebook and set as active context
    print(f"[2/5] Creating notebook: {args.title}...")
    run_cmd(["notebooklm", "--storage", storage_path, "create", args.title, "-u"])

    # 3. Add Sources & Wait for indexing
    print("[3/5] Adding research sources...")
    source_ids = []
    for src in args.sources:
        src_path = str(Path(src).resolve())
        print(f"Adding source: {src_path}")
        add_res = run_cmd(["notebooklm", "--storage", storage_path, "source", "add", src_path])
        for line in (add_res.stdout or "").splitlines():
            if "Added source:" in line:
                sid = line.split("Added source:")[-1].strip()
                source_ids.append(sid)

    # Crucial: Wait for Google's server to finish parsing the source document
    if source_ids:
        for sid in source_ids:
            print(f"Waiting for source {sid} to finish indexing on Google servers...")
            run_cmd(["notebooklm", "--storage", storage_path, "source", "wait", sid, "--timeout", "180"], check=False)
    else:
        print("Waiting 15 seconds for source indexing...")
        time.sleep(15)

    time.sleep(5)

    # 4. Generate Video (Trigger and wait) with automatic rate-limit cooldown handling
    print(f"[4/5] Triggering Hindi Video Overview generation (max wait: {args.timeout_minutes}m)...")
    prompt_file = str(Path(args.prompt).resolve())
    timeout_sec = args.timeout_minutes * 60
    
    gen_cmd = [
        "notebooklm", "--storage", storage_path,
        "generate", "video",
        "--language", "hi",
        "--wait",
        "--timeout", str(timeout_sec)
    ]
    if source_ids:
        for sid in source_ids:
            gen_cmd.extend(["-s", sid])
    if Path(prompt_file).exists() and Path(prompt_file).stat().st_size > 0:
        gen_cmd.extend(["--prompt-file", prompt_file])

    max_attempts = 4
    delay_sec = 300  # 5 minutes cooldown between attempts
    for attempt in range(1, max_attempts + 1):
        res = run_cmd(gen_cmd, check=False)
        if res.returncode == 0:
            break
        
        combined_err = (res.stdout or "") + "\n" + (res.stderr or "")

        # Fallback: if server rejected custom prompt file, retry with default prompt over the ready sources
        if ("invalid argument" in combined_err.lower() or "rpc_code=3" in combined_err.lower()) and "--prompt-file" in gen_cmd:
            print("\n[FALLBACK] Custom prompt rejected by server. Retrying with direct Hindi generation...")
            fallback_cmd = [
                "notebooklm", "--storage", storage_path,
                "generate", "video",
                "--language", "hi",
                "--wait",
                "--timeout", str(timeout_sec)
            ]
            if source_ids:
                for sid in source_ids:
                    fallback_cmd.extend(["-s", sid])
            res = run_cmd(fallback_cmd, check=False)
            if res.returncode == 0:
                break
            combined_err = (res.stdout or "") + "\n" + (res.stderr or "")

        if "Rate limited" in combined_err or "RateLimitError" in combined_err or "rate_limit" in combined_err.lower():
            if attempt < max_attempts:
                print(f"\n[RATE-LIMIT COOLDOWN] Google NotebookLM temporary quota cooldown.")
                print(f"Waiting 5 minutes before retry ({attempt}/{max_attempts - 1})...\n")
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
