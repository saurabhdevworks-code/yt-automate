"""Experimental NotebookLM UI automation via Playwright; not an official API."""
import argparse, asyncio, os, time
from pathlib import Path
from playwright.async_api import async_playwright

async def click_any(page, labels, timeout=10000):
    for label in labels:
        for locator in (page.get_by_role("button", name=label, exact=False),
                        page.get_by_text(label, exact=False)):
            try:
                if await locator.count():
                    await locator.first.click(timeout=timeout)
                    return
            except Exception:
                pass
    raise RuntimeError(f"NotebookLM UI control not found: {labels}")

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
                "--no-sandbox"
            ]
        )
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        try:
            await page.goto("https://notebooklm.google.com/", wait_until="domcontentloaded")
            await page.wait_for_timeout(2500)
            if "accounts.google.com" in page.url:
                raise RuntimeError("Not signed in. Run scripts/notebooklm_login.py once on this Windows runner.")
            # Create a notebook if the UI exposes a create control.
            for label in ["Create new notebook", "Create new", "New notebook"]:
                try:
                    loc = page.get_by_text(label, exact=False)
                    if await loc.count():
                        await loc.first.click(timeout=3000)
                        await page.wait_for_timeout(2000)
                        break
                except Exception:
                    pass
            await click_any(page, ["Add sources", "Add source"])
            await page.wait_for_timeout(1000)
            file_input = page.locator('input[type="file"]')
            if not await file_input.count():
                await click_any(page, ["Upload sources", "Upload files", "Upload"])
                await page.wait_for_timeout(700)
                file_input = page.locator('input[type="file"]')
            if not await file_input.count():
                raise RuntimeError("Could not locate NotebookLM source upload input; UI selectors may have changed.")
            await file_input.first.set_input_files([str(Path(s).resolve()) for s in args.sources])
            await page.wait_for_timeout(5000)
            await click_any(page, ["Studio"])
            await page.wait_for_timeout(1000)
            await click_any(page, ["Video Overview", "Video overview"])
            await page.wait_for_timeout(1500)
            prompt = Path(args.prompt).read_text(encoding="utf-8")
            for sel in ["textarea", '[contenteditable="true"]', 'input[type="text"]']:
                loc = page.locator(sel)
                try:
                    for i in range(min(await loc.count(), 10)):
                        item = loc.nth(i)
                        if await item.is_visible():
                            desc = ((await item.get_attribute("placeholder")) or "") + " " + ((await item.get_attribute("aria-label")) or "")
                            if any(x in desc.lower() for x in ["prompt", "instruction", "topic", "custom"]):
                                await item.fill(prompt)
                                break
                except Exception:
                    pass
            try:
                await click_any(page, ["Language", "Output language"], timeout=2500)
                await click_any(page, ["Hindi"], timeout=2500)
            except Exception:
                print("WARNING: Hindi language selector not detected; inspect NotebookLM settings.")
            await click_any(page, ["Generate now", "Generate", "Create"])
            deadline = time.time() + args.timeout_minutes * 60
            while time.time() < deadline:
                await page.wait_for_timeout(15000)
                try:
                    async with page.expect_download(timeout=3000) as info:
                        await click_any(page, ["Download video", "Download overview", "Download"], timeout=2500)
                    dl = await info.value
                    target = out / "notebooklm_video.mp4"
                    await dl.save_as(target)
                    if target.exists() and target.stat().st_size > 100000:
                        print(f"Downloaded NotebookLM video: {target}")
                        return
                except Exception:
                    pass
            raise TimeoutError("Video did not become downloadable before timeout.")
        except Exception:
            try:
                await page.screenshot(path=str(out / "notebooklm_failure.png"), full_page=True)
                (out / "notebooklm_failure_url.txt").write_text(page.url, encoding="utf-8")
            except Exception:
                pass
            raise
        finally:
            await ctx.close()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sources", nargs="+", required=True)
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--profile", default=os.getenv("NOTEBOOKLM_PROFILE", r"C:\notebooklm-playwright-profile"))
    ap.add_argument("--output", default="output/notebooklm")
    ap.add_argument("--timeout-minutes", type=int, default=75)
    asyncio.run(run(ap.parse_args()))

if __name__ == "__main__":
    main()
