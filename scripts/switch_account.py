#!/usr/bin/env python3
"""
scripts/switch_account.py

Allows 1-click switching between your 2 Google NotebookLM accounts:
1. bhawisyakakisan@gmail.com
2. saurabh.devworks@gmail.com

Automatically sets the active local profile and copies the corresponding
Master Token JSON to your clipboard for easy pasting into GitHub Secrets.
"""

import sys
import json
import subprocess
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
PROFILES_BASE = Path.home() / ".notebooklm" / "profiles"

ACCOUNTS = {
    "1": ("bhawisyakakisan", "bhawisyakakisan@gmail.com"),
    "bhawisyakakisan": ("bhawisyakakisan", "bhawisyakakisan@gmail.com"),
    "bhawisya": ("bhawisyakakisan", "bhawisyakakisan@gmail.com"),
    "2": ("default", "saurabh.devworks@gmail.com"),
    "saurabh": ("default", "saurabh.devworks@gmail.com"),
    "default": ("default", "saurabh.devworks@gmail.com"),
}

def switch(account_key: str):
    target = ACCOUNTS.get(account_key.lower().strip())
    if not target:
        print(f"[ERROR] Unknown account: {account_key}")
        print("Available: '1' / 'bhawisyakakisan' OR '2' / 'saurabh'")
        return

    profile_name, email = target
    profile_dir = PROFILES_BASE / profile_name
    token_file = profile_dir / "master_token.json"

    if not token_file.exists():
        print(f"[ERROR] Token file not found at: {token_file}")
        print(f"Please run setup_master_token.bat for {email} first.")
        return

    # 1. Switch CLI active profile
    subprocess.run(["notebooklm", "profile", "switch", profile_name], check=False)

    # 2. Update local master_token.json
    raw_json = token_file.read_text(encoding="utf-8").strip()
    (ROOT_DIR / "master_token.json").write_text(raw_json, encoding="utf-8")

    # 3. Copy to Windows clipboard
    try:
        subprocess.run(["clip"], input=raw_json.encode("utf-8"), check=True)
        clipboard_msg = ">>> Master Token JSON has been COPIED TO YOUR CLIPBOARD (Ctrl + V)!"
    except Exception:
        clipboard_msg = ""

    print("\n" + "=" * 70)
    print(f" SUCCESS! Switched active account to: {email}")
    print(f" Profile: {profile_name}")
    print("=" * 70)
    if clipboard_msg:
        print(f"\n{clipboard_msg}")
    print("\nNext step (for GitHub Cloud Actions):")
    print("1. Open GitHub Secrets: Settings -> Secrets and variables -> Actions")
    print("2. Paste (Ctrl + V) the token into NOTEBOOKLM_MASTER_TOKEN_JSON")
    print("3. Done! GitHub Actions will now generate videos using this account.\n")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        switch(sys.argv[1])
    else:
        print("\nChoose Account to activate:")
        print("1. bhawisyakakisan@gmail.com")
        print("2. saurabh.devworks@gmail.com")
        c = input("\nEnter 1 or 2: ").strip()
        switch(c)
