"""One-time interactive login to NotebookLM to export session for GitHub Cloud Actions."""
import asyncio, os, json, sys
from pathlib import Path
from playwright.async_api import async_playwright

async def main():
    profile_dir = Path(os.getenv("NOTEBOOKLM_PROFILE", r"C:\notebooklm-playwright-profile")).expanduser().resolve()
    profile_dir.mkdir(parents=True, exist_ok=True)
    storage_state_file = Path("storage_state.json").resolve()

    print("\n=======================================================")
    print("NotebookLM Cloud Login Helper")
    print("=======================================================")
    print("Opening Chrome browser. Please sign in to your Google Account.")
    print("Once NotebookLM is open and loaded, come back to this terminal")
    print("and press Enter.\n")

    async with async_playwright() as p:
        # Try chrome channel first, fallback to standard chromium
        launch_kwargs = {
            "headless": False,
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox"
            ]
        }
        try:
            ctx = await p.chromium.launch_persistent_context(
                str(profile_dir),
                channel="chrome",
                **launch_kwargs
            )
        except Exception:
            ctx = await p.chromium.launch_persistent_context(
                str(profile_dir),
                **launch_kwargs
            )

        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        await page.goto("https://notebook.google.com/", wait_until="domcontentloaded")
        
        input("\n>>> Press ENTER here AFTER you are fully signed in and see NotebookLM dashboard... <<<\n")
        
        # Save storage state (cookies + tokens)
        await ctx.storage_state(path=str(storage_state_file))
        await ctx.close()

    if storage_state_file.exists() and storage_state_file.stat().st_size > 50:
        try:
            data = json.loads(storage_state_file.read_text(encoding="utf-8"))
            cookies = data.get("cookies", [])
            auth_found = any(c.get("name") in ("SID", "__Secure-1PSID", "SAPISID", "SSID") for c in cookies)
            print("\n" + "=" * 60)
            print(f" SUCCESS! Session state saved to: {storage_state_file}")
            print(f" Total cookies captured: {len(cookies)}")
            if auth_found:
                print(" Google authenticated session detected!")
            else:
                print(" WARNING: Main Google auth cookies (SID, __Secure-1PSID) not detected.")
                print(" Make sure you completed sign-in and see the NotebookLM dashboard before pressing Enter.")
            print("=" * 60)
        except Exception:
            print("\n" + "=" * 60)
            print(" SUCCESS! Session state saved to: " + str(storage_state_file))
            print("=" * 60)
        print("\nNext step for 100% Cloud Automation (No PC needed):")
        print("1. Go to your GitHub Repository -> Settings -> Secrets and variables -> Actions")
        print("2. Add a new repository secret named:")
        print("   NOTEBOOKLM_AUTH_JSON")
        print("3. Paste the contents of storage_state.json into the secret value.\n")
    else:
        print("\n[ERROR] Failed to save session state. Please try running again.")

if __name__ == "__main__":
    asyncio.run(main())
