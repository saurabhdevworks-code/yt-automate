"""Interactive Durable Master-Token Setup for Google NotebookLM.
Creates a permanent Android-style OAuth Master Token that NEVER expires in GitHub Actions.
"""
import os, sys, json, subprocess
from pathlib import Path

def find_notebooklm_python():
    # If current python already has notebooklm, use it
    try:
        subprocess.run([sys.executable, "-c", "import notebooklm"], check=True, capture_output=True)
        return sys.executable
    except Exception:
        pass

    # Search known candidate paths on Windows
    candidates = [
        Path.home() / "AppData" / "Local" / "Programs" / "Python" / "Python312" / "python.exe",
        Path.home() / "AppData" / "Local" / "Programs" / "Python" / "Python311" / "python.exe",
        Path.home() / "AppData" / "Local" / "Programs" / "Python" / "Python310" / "python.exe",
        Path(r"C:\Python312\python.exe"),
        Path(r"C:\Python311\python.exe"),
        Path(r"C:\Python310\python.exe"),
    ]
    for c in candidates:
        if c.exists():
            try:
                subprocess.run([str(c), "-c", "import notebooklm"], check=True, capture_output=True)
                return str(c)
            except Exception:
                pass

    # Try py launcher
    for ver in ["-3.12", "-3.11", "-3.10"]:
        try:
            res = subprocess.run(["py", ver, "-c", "import sys; print(sys.executable)"], check=True, capture_output=True, text=True)
            candidate = res.stdout.strip()
            if candidate and Path(candidate).exists():
                return candidate
        except Exception:
            pass

    return sys.executable

def main():
    py_exec = find_notebooklm_python()

    print("\n" + "=" * 70)
    print("   Permanent NotebookLM Master Token Setup (Never Expires)")
    print("=" * 70)
    print("\nUnlike regular browser cookies that expire every few hours/days,")
    print("a Google Master Token (Android OAuth) remains valid and allows")
    print("GitHub Actions to automatically mint fresh cookies on every run!\n")
    print(f"Using Python: {py_exec}")

    email = ""
    if len(sys.argv) > 1:
        email = sys.argv[1].strip()
    while not email or "@" not in email:
        email = input("Enter your Google Account email (e.g. name@gmail.com): ").strip()

    print(f"\n[1/3] Initiating Master Token login for: {email}...")
    print("A browser window will open to Google's Embedded Setup.")
    print("Sign in with your Google account credentials & 2FA.")

    cmd = [
        py_exec, "-m", "notebooklm", "login",
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

    # Print the exact value on screen
    print("\n>>> COPY THE VALUE BELOW (Between the lines) <<<")
    print("-" * 70)
    print(raw_json)
    print("-" * 70)

    # Copy to clipboard
    try:
        subprocess.run(["clip"], input=raw_json.encode("utf-8"), check=True)
        print("\n>>> ALSO AUTOMATICALLY COPIED TO YOUR CLIPBOARD! <<<")
    except Exception:
        pass

    print("\nNext Steps to make GitHub Actions NEVER EXPIRE:")
    print("1. Go to your GitHub repository -> Settings -> Secrets and variables -> Actions")
    print("2. Click 'New repository secret'")
    print("3. Name:   NOTEBOOKLM_MASTER_TOKEN_JSON")
    print("4. Value:  Paste (Ctrl + V) the copied JSON content above")
    print("5. Click 'Add secret'.")
    print("\nYour workflow will now use this permanent master token and never expire!\n")

if __name__ == "__main__":
    main()
