"""Interactive login to NotebookLM using genuine Google Chrome (bypasses Google's bot detection)."""
import asyncio, os, json, sys, subprocess, time
from pathlib import Path
from playwright.async_api import async_playwright

def find_chrome():
    candidates = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return "chrome"

async def export_storage_state(profile_dir, storage_state_file):
    for attempt in range(5):
        try:
            async with async_playwright() as p:
                try:
                    ctx = await p.chromium.launch_persistent_context(
                        str(profile_dir),
                        channel="chrome",
                        headless=True
                    )
                except Exception:
                    ctx = await p.chromium.launch_persistent_context(
                        str(profile_dir),
                        headless=True
                    )
                await ctx.storage_state(path=str(storage_state_file))
                await ctx.close()
                return
        except Exception as e:
            if ("ProcessSingleton" in str(e) or "lock" in str(e).lower()) and attempt < 4:
                print("Waiting for Chrome profile to release lock...")
                await asyncio.sleep(2)
            else:
                raise e

def main():
    profile_dir = Path(os.getenv("NOTEBOOKLM_PROFILE", r"C:\notebooklm-playwright-profile")).expanduser().resolve()
    profile_dir.mkdir(parents=True, exist_ok=True)
    storage_state_file = Path("storage_state.json").resolve()

    print("\n" + "=" * 65)
    print(" NotebookLM Login & Session Exporter")
    print("=" * 65)

    chrome_path = find_chrome()
    print(f"\n[1/3] Launching official Google Chrome ({chrome_path})...")
    print("Genuine Chrome is opened without automation flags so Google allows")
    print("normal password/2FA login without 'browser not secure' warnings.\n")

    proc = subprocess.Popen([
        chrome_path,
        f"--user-data-dir={profile_dir}",
        "--no-first-run",
        "--no-default-browser-check",
        "https://notebook.google.com/"
    ])

    print(">>> Chrome window is now OPEN.")
    print(">>> 1. Sign in with your Google Account.")
    print(">>> 2. Wait until you see the NotebookLM / Gemini Notebook dashboard.")
    print(">>> 3. CLOSE the Chrome window completely.")
    input("\n>>> Once Chrome is closed, press ENTER here to export session... <<<\n")

    try:
        proc.wait(timeout=5)
    except Exception:
        proc.terminate()
        time.sleep(2)

    print("\n[2/3] Exporting authenticated session state...")
    asyncio.run(export_storage_state(profile_dir, storage_state_file))

    if storage_state_file.exists() and storage_state_file.stat().st_size > 50:
        raw_text = storage_state_file.read_text(encoding="utf-8")
        data = json.loads(raw_text)
        cookies = data.get("cookies", [])
        cookie_names = [c.get("name") for c in cookies]
        has_sid = any(n in ("SID", "__Secure-1PSID") for n in cookie_names)
        has_osid = any(n in ("OSID", "__Secure-OSID") for n in cookie_names)

        print("\n" + "=" * 65)
        print(f" SUCCESS! Session exported to: {storage_state_file}")
        print(f" Total cookies captured: {len(cookies)}")
        print(f" Google SSO session (SID/__Secure-1PSID): {'YES' if has_sid else 'NO'}")
        print(f" NotebookLM session (OSID/__Secure-OSID): {'YES' if has_osid else 'NO'}")
        print("=" * 65)

        # Copy to Windows clipboard automatically
        try:
            subprocess.run(["clip"], input=raw_text.encode("utf-8"), check=True)
            print("\n>>> COPIED TO CLIPBOARD AUTOMATICALLY! <<<")
            print("The entire storage_state.json content is already on your clipboard.")
        except Exception:
            pass

        print("\nNext step for GitHub Actions Cloud Pipeline:")
        print("1. Go to your GitHub Repository -> Settings -> Secrets and variables -> Actions")
        print("2. Open secret 'NOTEBOOKLM_AUTH_JSON'")
        print("3. Press Ctrl + V (Paste) and click 'Update secret'.")
        print("4. Re-run your workflow in GitHub Actions!\n")
    else:
        print("\n[ERROR] Failed to save session state. Please try running again.")

if __name__ == "__main__":
    main()
