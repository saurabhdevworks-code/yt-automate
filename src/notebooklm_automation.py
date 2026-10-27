"""Experimental NotebookLM UI automation via Playwright; not an official API."""
import argparse, asyncio, json, os, sys, time
from pathlib import Path
from playwright.async_api import async_playwright


async def safe_click(page, selector, timeout=5000):
    """Try to click a locator; return True on success, False on failure."""
    try:
        loc = page.locator(selector).first
        if await loc.is_visible(timeout=timeout):
            await loc.click(timeout=timeout)
            return True
    except Exception:
        pass
    return False


def normalize_cookie(c):
    """Normalize cookie dict from any source (Playwright, Cookie-Editor, EditThisCookie)."""
    if not isinstance(c, dict):
        return None
    name = c.get("name")
    value = c.get("value")
    if not name or value is None:
        return None

    cookie = {
        "name": str(name),
        "value": str(value),
    }

    # In Playwright, specify either domain + path OR url (never both)
    domain = c.get("domain")
    path = c.get("path") or "/"
    url = c.get("url")

    if domain:
        cookie["domain"] = domain
        cookie["path"] = path
    elif url:
        cookie["url"] = url
    else:
        cookie["domain"] = ".google.com"
        cookie["path"] = path

    # Expiry
    if "expires" in c and isinstance(c["expires"], (int, float)) and c["expires"] > 0:
        cookie["expires"] = float(c["expires"])
    elif "expirationDate" in c and isinstance(c["expirationDate"], (int, float)) and c["expirationDate"] > 0:
        cookie["expires"] = float(c["expirationDate"])

    # Flags
    if "httpOnly" in c:
        cookie["httpOnly"] = bool(c["httpOnly"])
    if "secure" in c:
        cookie["secure"] = bool(c["secure"])

    # sameSite: strictly check none/no_restriction BEFORE strict
    raw_ss = c.get("sameSite")
    if raw_ss is not None:
        ss = str(raw_ss).lower().strip()
        if ss in ("none", "no_restriction"):
            cookie["sameSite"] = "None"
        elif ss == "lax":
            cookie["sameSite"] = "Lax"
        elif ss == "strict":
            cookie["sameSite"] = "Strict"

    return cookie


async def close_all_modals(page, max_attempts=5):
    """Dismiss every modal / popup / onboarding banner on the screen."""
    for attempt in range(max_attempts):
        await page.keyboard.press("Escape")
        await page.wait_for_timeout(400)

        try:
            # Use JavaScript to find and click modal close / dismiss buttons
            closed_js = await page.evaluate("""() => {
                let clicked = false;
                const buttons = document.querySelectorAll('button, [role="button"]');
                for (const btn of buttons) {
                    const text = (btn.textContent || '').trim().toLowerCase();
                    const label = (btn.getAttribute('aria-label') || '').toLowerCase();
                    const title = (btn.getAttribute('title') || '').toLowerCase();
                    if ((text === 'close' || text === '✕' || text === '×' || text === 'got it' || text === 'dismiss' ||
                         label === 'close' || label.includes('close dialog') || title === 'close') 
                        && btn.offsetParent !== null) {
                        btn.click();
                        clicked = true;
                    }
                }
                return clicked;
            }""")
            if closed_js:
                await page.wait_for_timeout(400)
        except Exception:
            pass

        for sel in [
            'div[role="dialog"] button[aria-label*="close" i]',
            'div[role="dialog"] button:has-text("close")',
            'div[role="dialog"] button:has(svg)',
            'button[aria-label="Close"]',
            'button:has-text("close")',
            'button:has-text("Got it")',
            'button:has-text("Dismiss")',
        ]:
            try:
                loc = page.locator(sel).first
                if await loc.is_visible(timeout=300):
                    await loc.click(timeout=1000)
                    await page.wait_for_timeout(400)
            except Exception:
                pass


async def run(args):
    profile_str = getattr(args, "profile", "") or os.getenv("NOTEBOOKLM_PROFILE", "")
    if not profile_str:
        profile_str = r"C:\notebooklm-playwright-profile" if sys.platform.startswith("win") else "~/.notebooklm-playwright-profile"
    elif not sys.platform.startswith("win") and (profile_str.startswith("C:") or profile_str.startswith("c:")):
        profile_str = "~/.notebooklm-playwright-profile"

    profile = Path(profile_str).expanduser().resolve()
    profile.mkdir(parents=True, exist_ok=True)
    out = Path(args.output).resolve()
    out.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        storage_state_file = getattr(args, "storage_state", None)
        if not storage_state_file and Path("storage_state.json").exists():
            storage_state_file = "storage_state.json"

        browser_args = [
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
        ]

        user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        )

        launch_kwargs = {
            "headless": getattr(args, "headless", False),
            "accept_downloads": True,
            "viewport": {"width": 1440, "height": 1000},
            "user_agent": user_agent,
            "locale": "en-US",
            "args": browser_args,
        }

        if sys.platform.startswith("win") and not getattr(args, "headless", False):
            try:
                ctx = await p.chromium.launch_persistent_context(
                    str(profile),
                    channel="chrome",
                    **launch_kwargs
                )
            except Exception:
                ctx = await p.chromium.launch_persistent_context(
                    str(profile),
                    **launch_kwargs
                )
        else:
            ctx = await p.chromium.launch_persistent_context(
                str(profile),
                **launch_kwargs
            )

        origins_to_inject = []
        if storage_state_file and Path(storage_state_file).exists():
            try:
                raw_text = Path(storage_state_file).read_text(encoding="utf-8").strip()
                if raw_text:
                    data = json.loads(raw_text)
                    raw_cookies = data if isinstance(data, list) else data.get("cookies", [])
                    origins_to_inject = data.get("origins", []) if isinstance(data, dict) else []

                    valid_cookies = []
                    for c in raw_cookies:
                        norm = normalize_cookie(c)
                        if norm:
                            valid_cookies.append(norm)
                            dom = norm.get("domain", "")
                            # Duplicate cookies between notebooklm.google.com and notebook.google.com
                            if "notebooklm.google.com" in dom:
                                alt = dict(norm)
                                alt["domain"] = dom.replace("notebooklm.google.com", "notebook.google.com")
                                valid_cookies.append(alt)
                            elif "notebook.google.com" in dom:
                                alt = dict(norm)
                                alt["domain"] = dom.replace("notebook.google.com", "notebooklm.google.com")
                                valid_cookies.append(alt)

                    if valid_cookies:
                        await ctx.add_cookies(valid_cookies)
                        print(f"[NotebookLM] Successfully loaded {len(valid_cookies)} authenticated cookies from {storage_state_file}")
                    else:
                        print(f"[NotebookLM] Warning: No valid cookies found in {storage_state_file}")
            except Exception as e:
                print(f"[NotebookLM] Error loading cookies from {storage_state_file}: {e}")

        page = ctx.pages[0] if ctx.pages else await ctx.new_page()

        # Stealth: mask webdriver flag
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)

        # Restore localStorage from origins if present
        for orig in origins_to_inject:
            orig_name = orig.get("origin", "")
            ls_list = orig.get("localStorage", [])
            if ls_list and ("notebook" in orig_name or "google" in orig_name):
                js_code = f"""
                (() => {{
                    const items = {json.dumps(ls_list)};
                    for (const item of items) {{
                        try {{
                            localStorage.setItem(item.name, item.value);
                        }} catch (e) {{}}
                    }}
                }})();
                """
                await page.add_init_script(js_code)
        try:
            # ── Navigate ─────────────────────────────────────────────
            target_url = "https://notebook.google.com/"
            print(f"[NotebookLM] Navigating to {target_url}...")
            await page.goto(target_url, wait_until="networkidle")
            await page.wait_for_timeout(3000)
            print(f"[NotebookLM] Current page URL: {page.url}")

            # Check if redirected to landing/trynow promotional page
            if "trynow" in page.url.lower():
                print("[NotebookLM] Landed on /trynow promotional page. Clicking sign-in button...")
                clicked = False
                for signin_btn in [
                    'a.landing-cta-primary',
                    'a:has-text("Sign in to Gemini Notebook")',
                    'a.landing-header-signin',
                    'a:has-text("Sign in")',
                    'a[href*="/login"]',
                    'button:has-text("Sign in")',
                    'text="Sign in to Gemini Notebook"',
                    'text="Sign in"',
                    'text="Try now"',
                    'text="Try NotebookLM"',
                ]:
                    if await safe_click(page, signin_btn, timeout=2000):
                        print(f"[NotebookLM] Clicked sign-in element '{signin_btn}'")
                        clicked = True
                        break

                if not clicked:
                    print("[NotebookLM] Sign-in button not found on /trynow; navigating directly to /login...")
                    await page.goto("https://notebook.google.com/login?continue=https://notebook.google.com/", wait_until="networkidle")

                # Wait for Google SSO redirects to complete
                print("[NotebookLM] Waiting for authentication redirects...")
                try:
                    await page.wait_for_url(
                        lambda u: "trynow" not in u.lower() and "accounts.google.com" not in u.lower(),
                        timeout=15000
                    )
                except Exception:
                    await page.wait_for_timeout(4000)

            # Check if Google shows the account chooser (multiple accounts or select profile)
            if "accounts.google.com" in page.url:
                print(f"[NotebookLM] On accounts.google.com ({page.url}). Checking for account picker...")
                for acc_sel in [
                    'div[data-identifier]',
                    'div[data-email]',
                    'li div[role="link"]',
                    '[aria-label*="@"]',
                ]:
                    if await safe_click(page, acc_sel, timeout=2000):
                        print(f"[NotebookLM] Clicked account selector '{acc_sel}'")
                        try:
                            await page.wait_for_url(
                                lambda u: "accounts.google.com" not in u.lower() and "trynow" not in u.lower(),
                                timeout=15000
                            )
                        except Exception:
                            await page.wait_for_timeout(4000)
                        break

            print(f"[NotebookLM] Post-auth URL: {page.url}")

            if "accounts.google.com" in page.url or "trynow" in page.url.lower():
                await page.screenshot(path=str(out / "notebooklm_not_signed_in.png"), full_page=True)
                raise RuntimeError(
                    f"Not signed in to NotebookLM! Still on {page.url}. "
                    "NOTEBOOKLM_AUTH_JSON session cookies may have expired or Google is requesting interactive verification. "
                    "Please re-run 'python scripts/notebooklm_login.py' locally and update NOTEBOOKLM_AUTH_JSON in GitHub Secrets."
                )

            # ── Step 1: Create a new notebook ────────────────────────
            print("[NotebookLM] Creating new notebook...")
            # Look for '+ New notebook', 'New notebook', or 'Create notebook'
            created = False
            for sel in [
                'button:has-text("New notebook")',
                'button:has-text("+ New notebook")',
                'button:has-text("Create notebook")',
                '[aria-label*="New notebook" i]',
                '[aria-label*="Create" i]',
            ]:
                if await safe_click(page, sel, timeout=3000):
                    print(f"[NotebookLM] Clicked '{sel}'")
                    created = True
                    await page.wait_for_timeout(3500)
                    break

            if not created and "notebook/" not in page.url:
                try:
                    await page.locator('text="New notebook"').first.click(timeout=3000)
                    await page.wait_for_timeout(3500)
                except Exception:
                    pass

            print(f"[NotebookLM] Current URL: {page.url}")

            # ── Step 2: Dismiss Gemini Notebook Flexibility/Onboarding Modal ──
            # The 'We\'re giving you more flexibility...' modal appears over the new notebook.
            print("[NotebookLM] Checking for flexibility / onboarding modal...")
            await close_all_modals(page, max_attempts=5)

            # ── Step 3: Open Source Picker if not already open ───────
            # In NotebookLM, the left panel has 'Sources' with a '+' button and 'Drop files here'
            print("[NotebookLM] Opening source picker...")
            source_dialog_open = False
            for opt in ['text="Copied text"', 'text="Paste text"', 'text="Upload files"', 'text="Choose files"']:
                try:
                    if await page.locator(opt).first.is_visible(timeout=1000):
                        source_dialog_open = True
                        print(f"[NotebookLM] Source picker already visible ({opt})")
                        break
                except Exception:
                    pass

            if not source_dialog_open:
                for add_sel in [
                    'text="Drop files here"',
                    'button:has-text("+")',
                    '[aria-label*="Add source" i]',
                    '[aria-label*="Add sources" i]',
                    'button:has-text("Add source")',
                    'button:has-text("Add sources")',
                    'button:has-text("+ Add source")',
                ]:
                    if await safe_click(page, add_sel, timeout=2000):
                        print(f"[NotebookLM] Clicked '{add_sel}' to open source picker.")
                        await page.wait_for_timeout(2000)
                        break

            # ── Step 4: Add Source (Copied Text / File Upload) ─────────
            source_files = [str(Path(s).resolve()) for s in args.sources]
            uploaded = False

            # Strategy A: 'Copied text' / 'Paste text' (Most reliable, zero file DOM issues)
            for text_sel in [
                'text="Copied text"',
                'text="Paste text"',
                'button:has-text("Copied text")',
                'button:has-text("Paste text")',
                '[aria-label*="Copied text" i]',
            ]:
                if await safe_click(page, text_sel, timeout=2500):
                    print(f"[NotebookLM] Clicked '{text_sel}'. Pasting brief...")
                    await page.wait_for_timeout(1000)
                    try:
                        source_text = Path(source_files[0]).read_text(encoding="utf-8")
                    except Exception:
                        source_text = "Educational Research Brief\n"

                    pasted = False
                    for txt_loc in ['textarea', '[contenteditable="true"]', 'input[type="text"]']:
                        try:
                            loc = page.locator(txt_loc).last
                            if await loc.is_visible(timeout=2000):
                                await loc.fill(source_text)
                                pasted = True
                                print("[NotebookLM] Pasted research text into source field.")
                                break
                        except Exception:
                            pass

                    if pasted:
                        await page.wait_for_timeout(1000)
                        for ins in ['button:has-text("Insert")', 'button:has-text("Save")', 'button:has-text("Done")', 'button:has-text("Add")']:
                            if await safe_click(page, ins, timeout=3000):
                                uploaded = True
                                print("[NotebookLM] Clicked Insert/Save for Copied Text!")
                                break
                    if uploaded:
                        break

            # Strategy B: Direct input[type='file'] in DOM
            if not uploaded:
                file_input = page.locator('input[type="file"]')
                if await file_input.count():
                    try:
                        await file_input.first.set_input_files(source_files)
                        uploaded = True
                        print("[NotebookLM] Uploaded via direct input[type='file'].")
                    except Exception as e:
                        print(f"[NotebookLM] Direct file input failed: {e}")

            # Strategy C: Click 'Upload files' card / tab
            if not uploaded:
                for upload_card in ['text="Upload files"', 'text="Choose files"', 'text="Computer"', 'button:has-text("Upload files")']:
                    if await safe_click(page, upload_card, timeout=2500):
                        await page.wait_for_timeout(1000)
                        file_input = page.locator('input[type="file"]')
                        if await file_input.count():
                            try:
                                await file_input.first.set_input_files(source_files)
                                uploaded = True
                                print("[NotebookLM] Uploaded via Upload files card.")
                                break
                            except Exception:
                                pass

            # Strategy D: Expect file chooser
            if not uploaded:
                try:
                    async with page.expect_file_chooser(timeout=4000) as fc:
                        for trg in ['text="Upload files"', 'text="Choose files"', 'button:has-text("Upload")', 'text="Drop files here"']:
                            if await safe_click(page, trg, timeout=2000):
                                break
                    chooser = await fc.value
                    await chooser.set_files(source_files)
                    uploaded = True
                    print("[NotebookLM] Uploaded via file chooser event.")
                except Exception:
                    pass

            if not uploaded:
                await page.screenshot(
                    path=str(out / "notebooklm_failure_upload.png"), full_page=True
                )
                raise RuntimeError(
                    "Could not upload sources. See notebooklm_failure_upload.png"
                )

            # Wait for NotebookLM to ingest the sources
            print("[NotebookLM] Source added! Waiting 15s for ingestion...")
            await page.wait_for_timeout(15000)

            # Dismiss any leftover modal after adding source
            await page.keyboard.press("Escape")
            await page.wait_for_timeout(500)

            # ── Step 5: Click Video Overview in Studio panel ─────────
            # Studio panel is on the right side; Video Overview is one of
            # the artifact cards (along with Audio Overview, Slide Deck, etc.)
            print("[NotebookLM] Locating Video Overview in Studio panel...")
            video_clicked = False

            # Dismiss any promo/announcement banner inside Studio if present
            for promo_close in [
                'studio-panel button[aria-label*="close" i]',
                'button[aria-label="Dismiss"]',
            ]:
                await safe_click(page, promo_close, timeout=1000)

            # Ensure Studio panel is open/expanded
            await safe_click(page, 'button:has-text("Studio")', timeout=1500)
            await safe_click(page, 'text="Studio"', timeout=1500)
            await page.wait_for_timeout(1000)

            # Candidate selectors for Video Overview card
            video_selectors = [
                'text="Video Overview"',
                'button:has-text("Video Overview")',
                'text="Video overview"',
                'button:has-text("Video overview")',
                '[aria-label*="Video Overview" i]',
                '[aria-label*="Video overview" i]',
                'text="Video"',
                'button:has-text("Video")',
            ]

            for sel in video_selectors:
                if await safe_click(page, sel, timeout=2500):
                    video_clicked = True
                    print(f"[NotebookLM] Clicked Video Overview ({sel})")
                    await page.wait_for_timeout(2000)
                    break

            if not video_clicked:
                # Scroll Studio panel down to bring cards into view
                try:
                    await page.evaluate("""() => {
                        const panels = document.querySelectorAll('studio-panel, [role="complementary"], .studio-container');
                        for (const p of panels) {
                            p.scrollTop = p.scrollHeight;
                        }
                    }""")
                    await page.wait_for_timeout(1500)
                except Exception:
                    pass

                for sel in video_selectors:
                    if await safe_click(page, sel, timeout=2500):
                        video_clicked = True
                        print(f"[NotebookLM] Clicked Video Overview after scroll ({sel})")
                        await page.wait_for_timeout(2000)
                        break

            if not video_clicked:
                await page.screenshot(
                    path=str(out / "notebooklm_failure_video.png"), full_page=True
                )
                raise RuntimeError(
                    "Could not find Video Overview button. See screenshot."
                )

            # ── Step 6: Fill optional prompt ─────────────────────────
            prompt_text = Path(args.prompt).read_text(encoding="utf-8").strip()
            if prompt_text:
                for sel in ["textarea", '[contenteditable="true"]']:
                    try:
                        loc = page.locator(sel)
                        for i in range(min(await loc.count(), 5)):
                            item = loc.nth(i)
                            if await item.is_visible(timeout=1000):
                                await item.fill(prompt_text)
                                print("Filled prompt field.")
                                break
                    except Exception:
                        pass

            # ── Step 7: Click Generate ───────────────────────────────
            for gen_label in ["Generate now", "Generate", "Create"]:
                if await safe_click(page, f'button:has-text("{gen_label}")', timeout=3000):
                    print(f"Clicked '{gen_label}'. Waiting for video generation...")
                    break

            # ── Step 8: Wait for video and download ──────────────────
            deadline = time.time() + args.timeout_minutes * 60
            while time.time() < deadline:
                await page.wait_for_timeout(15000)
                # Check for download button
                for dl_label in ["Download video", "Download overview", "Download"]:
                    try:
                        dl_btn = page.locator(f'button:has-text("{dl_label}")').first
                        if await dl_btn.is_visible(timeout=2000):
                            async with page.expect_download(timeout=30000) as dl_info:
                                await dl_btn.click()
                            dl = await dl_info.value
                            target = out / "notebooklm_video.mp4"
                            await dl.save_as(target)
                            if target.exists() and target.stat().st_size > 100_000:
                                print(f"Downloaded NotebookLM video: {target}")
                                return
                    except Exception:
                        pass
                print(f"Still generating... ({int(deadline - time.time())}s remaining)")

            raise TimeoutError("Video did not become downloadable before timeout.")

        except Exception:
            try:
                await page.screenshot(
                    path=str(out / "notebooklm_failure.png"), full_page=True
                )
                (out / "notebooklm_failure_url.txt").write_text(
                    page.url, encoding="utf-8"
                )
            except Exception:
                pass
            raise
        finally:
            await ctx.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sources", nargs="+", required=True)
    ap.add_argument("--prompt", required=True)
    ap.add_argument(
        "--profile",
        default=os.getenv("NOTEBOOKLM_PROFILE", r"C:\notebooklm-playwright-profile"),
    )
    ap.add_argument("--output", default="output/notebooklm")
    ap.add_argument("--timeout-minutes", type=int, default=75)
    ap.add_argument("--storage-state", default=None, help="Path to storage_state.json")
    ap.add_argument("--headless", action="store_true", default=False)
    asyncio.run(run(ap.parse_args()))


if __name__ == "__main__":
    main()
