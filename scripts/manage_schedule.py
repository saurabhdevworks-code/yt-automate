#!/usr/bin/env python3
"""
scripts/manage_schedule.py

Allows easy management of YouTube auto-posting schedule:
- Number of videos per day
- Posting times in IST (Indian Standard Time)
- YouTube Privacy setting (private, public, unlisted)
- Applies updates to .github/workflows/full-pipeline-cloud.yml
- Optionally commits & pushes changes to GitHub repo
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
SCHEDULE_FILE = ROOT_DIR / "config" / "schedule.json"
WORKFLOW_FILE = ROOT_DIR / ".github" / "workflows" / "full-pipeline-cloud.yml"


def ist_to_utc_cron(time_str: str) -> tuple[str, str]:
    """
    Converts 'HH:MM' (IST 24-hr) to (cron_str, 12hr_formatted_str).
    IST is UTC + 5:30.
    """
    parts = time_str.strip().split(":")
    if len(parts) != 2:
        raise ValueError(f"Invalid time format '{time_str}'. Expected HH:MM (e.g. 09:00, 18:30).")

    hour, minute = int(parts[0]), int(parts[1])
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError(f"Time out of range: {time_str}")

    total_minutes = hour * 60 + minute
    utc_minutes = (total_minutes - 330) % 1440
    utc_hour = utc_minutes // 60
    utc_minute = utc_minutes % 60

    # Format 12hr IST
    period = "AM" if hour < 12 else "PM"
    h12 = hour % 12
    if h12 == 0:
        h12 = 12
    label_12h = f"{h12:02d}:{minute:02d} {period} IST"

    cron = f"{utc_minute} {utc_hour} * * *"
    return cron, label_12h


def load_schedule_config() -> dict:
    if not SCHEDULE_FILE.exists():
        default_cfg = {
            "_comment": "YouTube Automation Schedule Settings. Har time entry par 1 video generate & upload hogi.",
            "enabled": True,
            "privacy": "private",
            "_time_format_info": "24-Hour Format (HH:MM) - Indian Standard Time (IST)",
            "times_ist": ["09:00"]
        }
        SCHEDULE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(SCHEDULE_FILE, "w", encoding="utf-8") as f:
            json.dump(default_cfg, f, indent=2)
        return default_cfg

    with open(SCHEDULE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_schedule_config(cfg: dict):
    if "_time_format_info" not in cfg:
        cfg["_time_format_info"] = "24-Hour Format (HH:MM) - Indian Standard Time (IST)"
    if "_time_format_examples" in cfg:
        del cfg["_time_format_examples"]
    with open(SCHEDULE_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)


def apply_to_workflow(cfg: dict) -> bool:
    """Updates .github/workflows/full-pipeline-cloud.yml with new schedule & privacy."""
    if not WORKFLOW_FILE.exists():
        print(f"[ERROR] Workflow file not found: {WORKFLOW_FILE}")
        return False

    with open(WORKFLOW_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    enabled = cfg.get("enabled", True)
    privacy = cfg.get("privacy", "private").lower()
    times = cfg.get("times_ist", ["09:00"])

    # Build schedule YAML block
    if enabled and times:
        schedule_lines = ["  schedule:"]
        for t in times:
            cron, label = ist_to_utc_cron(t)
            schedule_lines.append(f'    - cron: "{cron}" # {label}')
        new_schedule_block = "\n".join(schedule_lines)
    else:
        new_schedule_block = "  # schedule: (Automated daily runs disabled)"

    # Replace schedule in workflow file
    # Matches either active `schedule:` block or commented `# schedule:` block up to permissions:
    pattern = r"([ \t]*#?[ \t]*schedule:\s*\n(?:\s*#?[ \t]*-\s*cron:.*\n|\s*#.*?\n)*)"
    if re.search(pattern, content):
        content = re.sub(pattern, new_schedule_block + "\n\n", content, count=1)
    else:
        # Fallback: insert before permissions:
        perm_idx = content.find("permissions:")
        if perm_idx != -1:
            content = content[:perm_idx] + new_schedule_block + "\n\n" + content[perm_idx:]
        else:
            print("[ERROR] Could not find schedule or permissions block in workflow file.")
            return False

    # Update default PRIVACY fallback on line 330:
    privacy_pattern = r"(PRIVACY:\s*\$\{\{\s*inputs\.upload_privacy\s*\|\|\s*')[^']+(\'\s*\}\})"
    content = re.sub(privacy_pattern, rf"\g<1>{privacy}\g<2>", content)

    with open(WORKFLOW_FILE, "w", encoding="utf-8") as f:
        f.write(content)

    return True


def show_status():
    cfg = load_schedule_config()
    print("\n" + "=" * 60)
    print("      CURRENT YOUTUBE AUTO-POSTING SCHEDULE")
    print("=" * 60)
    print(f"Auto-run Active : {'YES (Enabled)' if cfg.get('enabled', True) else 'NO (Disabled)'}")
    print(f"Upload Privacy  : {cfg.get('privacy', 'private').upper()}")
    times = cfg.get("times_ist", [])
    print(f"Videos Per Day  : {len(times)}")
    print("\nPosting Times (IST):")
    if not times:
        print("  - None configured")
    for i, t in enumerate(times, 1):
        try:
            cron, label = ist_to_utc_cron(t)
            print(f"  {i}. {t} (24h) -> {label} [Cron: '{cron}']")
        except Exception as e:
            print(f"  {i}. {t} (Invalid time: {e})")
    print("=" * 60 + "\n")


def interactive_setup():
    cfg = load_schedule_config()
    print("\n--- Set Up Daily YouTube Video Schedule ---")

    # 1. Enable/Disable
    status_choice = input(f"Auto-post on schedule enable karna hai? (y/n) [default: {'y' if cfg.get('enabled', True) else 'n'}]: ").strip().lower()
    if status_choice in ['y', 'yes']:
        cfg["enabled"] = True
    elif status_choice in ['n', 'no']:
        cfg["enabled"] = False

    if cfg["enabled"]:
        # 2. Number of videos per day
        curr_count = len(cfg.get("times_ist", ["09:00"]))
        count_input = input(f"Ek din me kitni videos post karni hain? (1 to 6) [default: {curr_count}]: ").strip()
        count = int(count_input) if count_input.isdigit() and 1 <= int(count_input) <= 6 else curr_count

        new_times = []
        default_suggestions = ["09:00", "18:00", "13:30", "20:30", "11:00", "16:00"]
        for i in range(count):
            suggested = cfg.get("times_ist", [])[i] if i < len(cfg.get("times_ist", [])) else default_suggestions[i]
            while True:
                t_val = input(f"Video {i+1} ka time daalein (24-hour IST format HH:MM, e.g. 09:00, 18:30) [default: {suggested}]: ").strip()
                if not t_val:
                    t_val = suggested
                try:
                    ist_to_utc_cron(t_val)
                    new_times.append(t_val)
                    break
                except ValueError as err:
                    print(f"  [X] {err}. Phir se try karein.")
        cfg["times_ist"] = new_times

    # 3. Privacy
    curr_privacy = cfg.get("privacy", "private")
    print("\nYouTube Privacy setting:")
    print("  1. private  (Safe: video uploaded as private so you can review first)")
    print("  2. public   (Direct: video is immediately public to all subscribers)")
    print("  3. unlisted (Only people with link can view)")
    priv_input = input(f"Choose privacy (1=private, 2=public, 3=unlisted) [default: {curr_privacy}]: ").strip()
    if priv_input == "1":
        cfg["privacy"] = "private"
    elif priv_input == "2":
        cfg["privacy"] = "public"
    elif priv_input == "3":
        cfg["privacy"] = "unlisted"

    save_schedule_config(cfg)
    print("\n[OK] Configuration saved in config/schedule.json!")
    
    apply_to_workflow(cfg)
    print("[OK] Workflow file .github/workflows/full-pipeline-cloud.yml updated!")

    # 4. Git Push
    push_choice = input("\nGitHub par push karke live activate karna hai? (y/n) [default: y]: ").strip().lower()
    if push_choice in ['', 'y', 'yes']:
        git_commit_and_push()


def git_commit_and_push():
    print("\nPushing changes to GitHub repository...")
    try:
        subprocess.run(["git", "add", "config/schedule.json", ".github/workflows/full-pipeline-cloud.yml"], check=True)
        commit_msg = "chore: update auto-posting schedule & videos frequency"
        subprocess.run(["git", "commit", "-m", commit_msg], check=True)
        subprocess.run(["git", "push"], check=True)
        print("\n[SUCCESS] Schedule updated & pushed to GitHub! Naya schedule ab live hai.")
    except subprocess.CalledProcessError as e:
        print(f"\n[WARNING] Git commit/push me issue aayi: {e}")
        print("Aap manually bhi 'git add', 'git commit', 'git push' chala sakte hain.")


def main():
    parser = argparse.ArgumentParser(description="Manage YouTube auto-posting schedule and frequency.")
    parser.add_argument("--status", action="store_true", help="Show current schedule status")
    parser.add_argument("--interactive", action="store_true", help="Launch interactive step-by-step setup")
    parser.add_argument("--apply", action="store_true", help="Apply config/schedule.json to workflow file")
    parser.add_argument("--push", action="store_true", help="Commit and push changes to GitHub")

    args = parser.parse_args()

    if args.status:
        show_status()
    elif args.apply:
        cfg = load_schedule_config()
        if apply_to_workflow(cfg):
            print("[OK] Successfully applied config/schedule.json to workflow file!")
            if args.push:
                git_commit_and_push()
    elif args.interactive:
        interactive_setup()
    else:
        # Default behavior: show status and ask
        show_status()
        interactive_setup()


if __name__ == "__main__":
    main()
