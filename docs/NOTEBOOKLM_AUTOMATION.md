# NotebookLM automation (experimental, UI-based)

This uses Playwright to operate the NotebookLM website because no documented public API for personal-account Video Overview generation was found. UI selectors may change; this is not guaranteed production-ready.

## One-time Windows setup
1. Register a self-hosted GitHub Actions runner on your Windows PC and add custom label `notebooklm`.
2. Run the runner interactively in the logged-in desktop session, not as a Windows service. The PC must be on, awake and online at schedule time.
3. In PowerShell in the repository:
   ```powershell
   pip install -r requirements.txt
   pip install playwright
   python -m playwright install chromium
   $env:NOTEBOOKLM_PROFILE = "C:\notebooklm-playwright-profile"
   python scripts/notebooklm_login.py
   ```
4. Sign in to Google in the opened browser once. Do not commit or share the browser profile.
5. Configure YouTube OAuth secrets and optional `GEMINI_API_KEY` in GitHub Actions.
6. Trigger `Full NotebookLM Pipeline (Windows self-hosted)` manually for the first test.

The intended recurring flow is research → NotebookLM UI → Video Overview → download → private YouTube upload. If it fails, inspect the artifact `notebooklm_failure.png` and `notebooklm_failure_url.txt`.

Security: no passwords/cookies are stored in GitHub secrets. Google login/MFA is not bypassed. Start with private uploads and verify the run before enabling the schedule.
