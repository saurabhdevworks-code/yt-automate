"""Experimental NotebookLM UI automation via Playwright; not an official API."""
import argparse, asyncio, os, time
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
        ctx = await p.chromium.launch_persistent_context(
            str(profile),
            headless=False,
            channel="chrome",
            accept_downloads=True,
            viewport={"width": 1440, "height": 1000},
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ],
        )
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

            # ── Step 2: Close ALL popups / modals ────────────────────
            await close_all_modals(page)
            await page.wait_for_timeout(1000)

            # ── Step 3: Upload source file ───────────────────────────
            source_files = [str(Path(s).resolve()) for s in args.sources]
            uploaded = False

            # Method A: Hidden file input may already exist in the DOM
            file_input = page.locator('input[type="file"]')
            if await file_input.count():
                await file_input.first.set_input_files(source_files)
                uploaded = True
                print("Uploaded via existing file input.")

            # Method B: Click '+ Add sources' then 'Upload files' tab
            if not uploaded:
                await safe_click(page, 'button:has-text("Add sources")')
                await page.wait_for_timeout(2000)

                # Click the "Upload files" chip/tab in the source picker dialog
                await safe_click(page, 'text="Upload files"', timeout=3000)
                await page.wait_for_timeout(1000)

                # Now check for file input again
                file_input = page.locator('input[type="file"]')
                if await file_input.count():
                    await file_input.first.set_input_files(source_files)
                    uploaded = True
                    print("Uploaded via Add sources > Upload files file input.")

            # Method C: Use file chooser event on the drag-drop zone
            if not uploaded:
                try:
                    async with page.expect_file_chooser(timeout=5000) as fc:
                        # Click the drag-drop upload area
                        drop_zone = page.locator('text="Drag & drop your files to upload"').first
                        if await drop_zone.is_visible(timeout=2000):
                            await drop_zone.click()
                        else:
                            await safe_click(page, 'text="Upload files"', timeout=2000)
                    chooser = await fc.value
                    await chooser.set_files(source_files)
                    uploaded = True
                    print("Uploaded via file chooser on drag-drop zone.")
                except Exception:
                    pass

            # Method D: JavaScript to find ANY file input (even hidden)
            if not uploaded:
                try:
                    has_input = await page.evaluate("""() => {
                        const inp = document.querySelector('input[type="file"]');
                        return inp !== null;
                    }""")
                    if has_input:
                        await page.locator('input[type="file"]').first.set_input_files(source_files)
                        uploaded = True
                        print("Uploaded via JS-found hidden file input.")
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
    asyncio.run(run(ap.parse_args()))


if __name__ == "__main__":
    main()
