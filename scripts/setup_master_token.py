"""Interactive Durable Master-Token Setup for Google NotebookLM.
Creates a permanent Android-style OAuth Master Token that NEVER expires in GitHub Actions.
"""
import os, sys, json, subprocess
from pathlib import Path

def main():
    print("\n" + "=" * 70)
    print("   Permanent NotebookLM Master Token Setup (Never Expires)")
    print("=" * 70)
    print("\nUnlike regular browser cookies that expire every few hours/days,")
    print("a Google Master Token (Android OAuth) remains valid and allows")
    print("GitHub Actions to automatically mint fresh cookies on every run!\n")

    email = ""
    if len(sys.argv) > 1:
        email = sys.argv[1].strip()
    while not email or "@" not in email:
        email = input("Enter your Google Account email (e.g. name@gmail.com): ").strip()

    print(f"\n[1/3] Initiating Master Token login for: {email}...")
    print("A browser window will open to Google's Embedded Setup.")
    print("Sign in with your Google account credentials & 2FA.")

    cmd = [
        sys.executable, "-m", "notebooklm", "login",
        "--master-token",
        "--account", email,
        "--browser", "chrome"
    ]
    
    try:
        res = subprocess.run(cmd)
        if res.returncode != 0:
            print("\nRetrying with default browser engine...")
            cmd[-1] = "chromium"
            res = subprocess.run(cmd)
    except Exception as e:
        print(f"\n[ERROR] Failed to run login: {e}")
        return

    # Find master_token.json
    possible_paths = [
        Path.home() / ".notebooklm" / "profiles" / "default" / "master_token.json",
        Path("master_token.json").resolve(),
    ]

    found_path = None
    for p in possible_paths:
        if p.exists() and p.stat().st_size > 20:
            found_path = p
            break

    if not found_path:
        print("\n[ERROR] master_token.json was not created. Please try running again.")
        return

    raw_json = found_path.read_text(encoding="utf-8").strip()
    try:
        data = json.loads(raw_json)
        # Also copy a local copy into the current repository root
        Path("master_token.json").write_text(raw_json, encoding="utf-8")
    except Exception as e:
        print(f"\n[ERROR] Token file is invalid JSON: {e}")
        return

    print("\n" + "=" * 70)
    print(" SUCCESS! Permanent Master Token successfully generated!")
    print(f" Saved to: {found_path}")
    print(f" Account:  {data.get('email', email)}")
    print("=" * 70)

    # Copy to clipboard
    try:
        subprocess.run(["clip"], input=raw_json.encode("utf-8"), check=True)
        print("\n>>> AUTOMATICALLY COPIED TO YOUR CLIPBOARD! <<<")
    except Exception:
        pass

    print("\nNext Steps to make GitHub Actions NEVER EXPIRE:")
    print("1. Go to your GitHub repository -> Settings -> Secrets and variables -> Actions")
    print("2. Click 'New repository secret'")
    print("3. Name:   NOTEBOOKLM_MASTER_TOKEN_JSON")
    print("4. Value:  Paste (Ctrl + V) the copied JSON content")
    print("5. Click 'Add secret'.")
    print("\nYour workflow will now use this permanent master token and never expire!\n")

if __name__ == "__main__":
    main()
