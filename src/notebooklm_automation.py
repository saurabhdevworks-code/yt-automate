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


async def close_all_modals(page, max_attempts=5):
    """Dismiss every modal / popup / onboarding banner on the screen."""
    for attempt in range(max_attempts):
        # Method 1: Press Escape — works on almost every modal/dialog
        await page.keyboard.press("Escape")
        await page.wait_for_timeout(500)

        # Method 2: Click the X button on the flexibility/onboarding modal
        # The X is an SVG/icon button inside the modal overlay
        try:
            # Use JavaScript to find and click the modal close button
            closed_js = await page.evaluate("""() => {
                // Find buttons that look like close/dismiss
                const buttons = document.querySelectorAll('button');
                for (const btn of buttons) {
                    const text = btn.textContent.trim().toLowerCase();
                    const label = (btn.getAttribute('aria-label') || '').toLowerCase();
                    // The modal X button has text "close" (Material icon) or aria-label
                    if ((text === 'close' || text === '✕' || text === '×' || label === 'close') 
                        && btn.offsetParent !== null) {
                        btn.click();
                        return true;
                    }
                }
                return false;
            }""")
            if closed_js:
                await page.wait_for_timeout(500)
        except Exception:
            pass

        # Method 3: Click specific dismiss buttons
        for sel in [
            'button[aria-label="Close"]',
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
    profile = Path(args.profile).expanduser().resolve()
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

        launch_kwargs = {
            "headless": getattr(args, "headless", False),
            "accept_downloads": True,
            "viewport": {"width": 1440, "height": 1000},
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

        if storage_state_file and Path(storage_state_file).exists():
            try:
                state_data = json.loads(Path(storage_state_file).read_text(encoding="utf-8"))
                cookies = state_data.get("cookies", [])
                if cookies:
                    await ctx.add_cookies(cookies)
                    print(f"[NotebookLM] Injected {len(cookies)} session cookies from {storage_state_file}")
            except Exception as e:
                print(f"[NotebookLM] Warning loading cookies: {e}")
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        try:
            # ── Navigate ─────────────────────────────────────────────
            await page.goto(
                "https://notebooklm.google.com/", wait_until="networkidle"
            )
            await page.wait_for_timeout(3000)

            if "accounts.google.com" in page.url:
                raise RuntimeError(
                    "Not signed in. Run the Chrome login helper first."
                )

            # ── Step 1: Create a new notebook ────────────────────────
            for label in ["New notebook", "Create notebook"]:
                if await safe_click(page, f'button:has-text("{label}")'):
                    await page.wait_for_timeout(3000)
                    break

            # ── Step 2: Ensure modal is clean, but DO NOT close source picker ──
            # Only dismiss onboarding banners like "Got it", "Dismiss", "Try it"
            for dismiss_sel in ['button:has-text("Got it")', 'button:has-text("Dismiss")', 'button:has-text("Try it")']:
                await safe_click(page, dismiss_sel, timeout=1000)

            # ── Step 3: Add source (Multi-strategy: Copied Text / File Upload) ──
            source_files = [str(Path(s).resolve()) for s in args.sources]
            uploaded = False

            # Wait briefly for UI to stabilize
            await page.wait_for_timeout(2000)

            # Strategy A: Check if "Copied text" or "Paste text" is visible
            print("[NotebookLM] Checking source options...")
            for text_opt in ['text="Copied text"', 'text="Paste text"', 'button:has-text("Copied text")', 'button:has-text("Paste text")', '[aria-label*="Copied text" i]']:
                if await safe_click(page, text_opt, timeout=2500):
                    print(f"[NotebookLM] Clicked '{text_opt}'. Pasting source text...")
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
                                break
                        except Exception:
                            pass
                    
                    if pasted:
                        await page.wait_for_timeout(1000)
                        for ins in ['button:has-text("Insert")', 'button:has-text("Save")', 'button:has-text("Done")', 'button:has-text("Add")']:
                            if await safe_click(page, ins, timeout=3000):
                                uploaded = True
                                print("[NotebookLM] Successfully added source via Copied Text!")
                                break
                    if uploaded:
                        break

            # Strategy B: Direct input[type="file"] in DOM
            if not uploaded:
                file_input = page.locator('input[type="file"]')
                if await file_input.count():
                    try:
                        await file_input.first.set_input_files(source_files)
                        uploaded = True
                        print("[NotebookLM] Uploaded via direct input[type='file'].")
                    except Exception as e:
                        print(f"[NotebookLM] Direct file input failed: {e}")

            # Strategy C: Click "Upload files" / "Choose files"
            if not uploaded:
                for upload_btn in ['text="Upload files"', 'text="Choose files"', 'text="Computer"', 'button:has-text("Upload files")']:
                    if await safe_click(page, upload_btn, timeout=2500):
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

            # Strategy D: If dialog wasn't open, open it with "Add source" (singular) or "Add sources"
            if not uploaded:
                for add_sel in [
                    'button:has-text("Add source")',
                    'button:has-text("Add sources")',
                    'button:has-text("+ Add source")',
                    'button:has-text("+ Add sources")',
                    '[aria-label*="Add source" i]',
                    'text="Add source"',
                    'text="Add sources"'
                ]:
                    if await safe_click(page, add_sel, timeout=2000):
                        await page.wait_for_timeout(1500)
                        file_input = page.locator('input[type="file"]')
                        if await file_input.count():
                            try:
                                await file_input.first.set_input_files(source_files)
                                uploaded = True
                                print("[NotebookLM] Uploaded after clicking Add source button.")
                                break
                            except Exception:
                                pass

            # Strategy E: File chooser event
            if not uploaded:
                try:
                    async with page.expect_file_chooser(timeout=5000) as fc:
                        for trigger in ['text="Upload files"', 'text="Choose files"', 'button:has-text("Upload")']:
                            if await safe_click(page, trigger, timeout=2000):
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
            print("Sources uploaded. Waiting for ingestion...")
            await page.wait_for_timeout(15000)

            # ── Step 4: Close any new modals that appeared after upload ──
            await close_all_modals(page)

            # ── Step 5: Click Video Overview in Studio panel ─────────
            # Studio panel is on the right side; Video Overview is one of
            # the artifact cards (along with Audio Overview, Slide Deck, etc.)
            # First check if "Video Overview" text is directly visible
            video_clicked = False
            for sel in [
                'text="Video Overview"',
                'button:has-text("Video Overview")',
                'text="Video"',
            ]:
                if await safe_click(page, sel, timeout=3000):
                    video_clicked = True
                    print("Clicked Video Overview.")
                    await page.wait_for_timeout(2000)
                    break

            if not video_clicked:
                # Maybe Studio panel needs to be expanded first
                await safe_click(page, 'text="Studio"', timeout=2000)
                await page.wait_for_timeout(1500)
                for sel in [
                    'text="Video Overview"',
                    'button:has-text("Video")',
                ]:
                    if await safe_click(page, sel, timeout=3000):
                        video_clicked = True
                        print("Clicked Video Overview (after expanding Studio).")
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
