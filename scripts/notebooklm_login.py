"""One-time interactive login to NotebookLM using a persistent Playwright profile."""
import asyncio, os
from pathlib import Path
from playwright.async_api import async_playwright

async def main():
    profile = Path(os.getenv("NOTEBOOKLM_PROFILE", r"C:\notebooklm-playwright-profile")).expanduser().resolve()
    profile.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(str(profile), headless=False)
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        await page.goto("https://notebooklm.google.com/", wait_until="domcontentloaded")
        input("Sign in interactively in the browser. When NotebookLM is open, press Enter here.")
        await ctx.close()

if __name__ == "__main__":
    asyncio.run(main())
