"""Modern 1-Click Control Dashboard for NotebookLM YouTube Pipeline.
Zero external dependencies (uses standard Python library).
"""
import http.server, json, os, re, socketserver, sys, urllib.request, webbrowser
from pathlib import Path

PORT = 7860
REPO = "saurabhdevworks-code/yt-automate"
WORKFLOW_FILE = "full-pipeline-cloud.yml"
ENV_PATH = Path(__file__).resolve().parents[1] / ".env"

def load_env():
    env_vars = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env_vars[k.strip()] = v.strip().strip('"').strip("'")
    return env_vars

def save_env_token(token):
    existing = load_env()
    existing["GITHUB_TOKEN"] = token.strip()
    lines = [f"{k}={v}" for k, v in existing.items()]
    ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")

def trigger_github_workflow(inputs, token):
    url = f"https://api.github.com/repos/{REPO}/actions/workflows/{WORKFLOW_FILE}/dispatches"
    payload = {
        "ref": "main",
        "inputs": inputs
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    req.add_header("User-Agent", "NotebookLM-Dashboard")

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status in (200, 204), "Workflow triggered successfully!"
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="ignore")
        return False, f"GitHub API Error ({e.code}): {body or e.reason}"
    except Exception as e:
        return False, f"Network Error: {str(e)}"

HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>YouTube Automation Studio</title>
  <style>
    :root {
      --bg: #0b0f19;
      --card: #151c2c;
      --border: #232d42;
      --primary: #6366f1;
      --primary-hover: #4f46e5;
      --accent: #10b981;
      --text: #f3f4f6;
      --text-muted: #9ca3af;
      --danger: #ef4444;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
    body { background-color: var(--bg); color: var(--text); padding: 30px 20px; display: flex; justify-content: center; }
    .container { width: 100%; max-width: 680px; }
    .header { text-align: center; margin-bottom: 28px; }
    .header h1 { font-size: 26px; font-weight: 700; color: #fff; margin-bottom: 8px; }
    .header p { color: var(--text-muted); font-size: 14px; }
    
    /* Toggle Tabs */
    .mode-selector {
      display: flex;
      background: var(--card);
      border: 1px solid var(--border);
      padding: 6px;
      border-radius: 14px;
      margin-bottom: 24px;
      gap: 6px;
    }
    .mode-btn {
      flex: 1;
      padding: 12px;
      border: none;
      background: transparent;
      color: var(--text-muted);
      font-size: 15px;
      font-weight: 600;
      border-radius: 10px;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      transition: all 0.2s ease;
    }
    .mode-btn.active {
      background: var(--primary);
      color: #fff;
      box-shadow: 0 4px 12px rgba(99, 102, 241, 0.35);
    }
    .mode-btn:hover:not(.active) { color: #fff; background: rgba(255,255,255,0.04); }

    /* Cards */
    .card {
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 16px;
      padding: 24px;
      margin-bottom: 20px;
      box-shadow: 0 8px 24px rgba(0,0,0,0.2);
    }
    .card-title { font-size: 16px; font-weight: 600; margin-bottom: 16px; display: flex; align-items: center; gap: 8px; color: #e5e7eb; }
    .form-group { margin-bottom: 16px; }
    .form-group:last-child { margin-bottom: 0; }
    label { display: block; font-size: 13px; font-weight: 500; color: var(--text-muted); margin-bottom: 6px; }
    input[type="text"], textarea, select {
      width: 100%;
      background: #0f1523;
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 11px 14px;
      color: #fff;
      font-size: 14px;
      outline: none;
      transition: border 0.2s;
    }
    input[type="text"]:focus, textarea:focus, select:focus { border-color: var(--primary); }
    textarea { resize: vertical; min-height: 70px; }
    .row { display: flex; gap: 12px; }
    .row .form-group { flex: 1; }

    /* Submit Button */
    .btn-submit {
      width: 100%;
      padding: 15px;
      background: var(--primary);
      border: none;
      border-radius: 12px;
      color: #fff;
      font-size: 16px;
      font-weight: 600;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 10px;
      transition: background 0.2s, transform 0.1s;
    }
    .btn-submit:hover { background: var(--primary-hover); }
    .btn-submit:active { transform: scale(0.99); }
    .btn-submit:disabled { opacity: 0.6; cursor: not-allowed; }

    /* Auto View */
    .auto-info {
      text-align: center;
      padding: 30px 10px;
    }
    .auto-icon { font-size: 48px; margin-bottom: 16px; }
    .auto-info h3 { font-size: 18px; margin-bottom: 10px; color: #fff; }
    .auto-info p { color: var(--text-muted); font-size: 14px; line-height: 1.6; max-width: 480px; margin: 0 auto 24px; }

    /* Status Alert */
    .status-box {
      display: none;
      padding: 14px 18px;
      border-radius: 10px;
      font-size: 14px;
      margin-top: 16px;
      line-height: 1.5;
    }
    .status-success { background: rgba(16, 185, 129, 0.15); border: 1px solid var(--accent); color: #34d399; }
    .status-error { background: rgba(239, 68, 68, 0.15); border: 1px solid var(--danger); color: #f87171; }
    .status-box a { color: #fff; text-decoration: underline; font-weight: 600; }

    /* Token settings */
    .token-bar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 18px;
      font-size: 12px;
      color: var(--text-muted);
      background: rgba(255,255,255,0.02);
      padding: 8px 14px;
      border-radius: 8px;
      border: 1px dashed var(--border);
    }
    .token-bar span { display: flex; align-items: center; gap: 6px; }
    .token-link { color: var(--primary); text-decoration: none; cursor: pointer; font-weight: 600; }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>🎬 YouTube Automation Studio</h1>
      <p>Google NotebookLM AI Video Generation & Upload Control</p>
    </div>

    <!-- Mode Selector Buttons -->
    <div class="mode-selector">
      <button class="mode-btn active" id="btn-auto" onclick="setMode('auto')">
        <span>🤖</span> Auto Mode (1-Click)
      </button>
      <button class="mode-btn" id="btn-custom" onclick="setMode('custom')">
        <span>🎨</span> Custom Studio
      </button>
    </div>

    <!-- GitHub Token Indicator -->
    <div class="token-bar">
      <span id="token-status">🔑 GitHub Access Token: <b id="token-status-text">Checking...</b></span>
      <a class="token-link" onclick="toggleTokenBox()">Change Token</a>
    </div>
    <div id="token-box" style="display:none; margin-bottom: 16px;" class="card">
      <div class="form-group">
        <label>Personal Access Token (Needs 'repo' or 'actions:write' permission):</label>
        <input type="text" id="token-input" placeholder="ghp_xxxxxxxxxxxxxxxxxxxx">
      </div>
      <div style="display:flex; justify-content:space-between; align-items:center;">
        <a href="https://github.com/settings/tokens/new?scopes=repo&description=NotebookLM-Dashboard" target="_blank" style="color:var(--primary); font-size:12px;">Generate Token on GitHub ↗</a>
        <button onclick="saveToken()" style="padding: 7px 16px; background:var(--primary); border:none; color:#fff; border-radius:6px; cursor:pointer;">Save Token</button>
      </div>
    </div>

    <!-- AUTO MODE VIEW -->
    <div id="view-auto">
      <div class="card">
        <div class="auto-info">
          <div class="auto-icon">⚡</div>
          <h3>100% Fully Automated Pipeline</h3>
          <p>
            NotebookLM automatically discovers trending topics, writes the research brief, generates the Hindi Video Overview in cloud, creates the thumbnail, and uploads privately to YouTube.
          </p>
          <button class="btn-submit" onclick="submitPipeline('auto')">
            <span>🚀</span> Launch Auto Pipeline
          </button>
        </div>
      </div>
    </div>

    <!-- CUSTOM MODE VIEW -->
    <div id="view-custom" style="display:none;">
      <div class="card">
        <div class="card-title">💡 1. Topic & Research</div>
        <div class="form-group">
          <label>Video Topic / Concept:</label>
          <input type="text" id="custom-topic" placeholder="e.g. How Space Missions Work in Hindi">
        </div>
      </div>

      <div class="card">
        <div class="card-title">✂️ 2. Video Editing & Intro</div>
        <div class="row">
          <div class="form-group">
            <label>Trim Start (e.g. 5 or 00:00:05):</label>
            <input type="text" id="trim-start" placeholder="Leave empty for no trim">
          </div>
          <div class="form-group">
            <label>Trim End (e.g. 00:06:00):</label>
            <input type="text" id="trim-end" placeholder="Leave empty for no trim">
          </div>
        </div>
        <div class="form-group">
          <label>Intro Video Link (Google Drive / Direct MP4 URL):</label>
          <input type="text" id="intro-url" placeholder="https://drive.google.com/file/d/...">
        </div>
      </div>

      <div class="card">
        <div class="card-title">🖼️ 3. Thumbnail & Branding</div>
        <div class="form-group">
          <label>Custom Thumbnail Link (Google Drive / Direct Image URL):</label>
          <input type="text" id="thumb-url" placeholder="https://drive.google.com/file/d/... or leave empty for AI thumb">
        </div>
      </div>

      <div class="card">
        <div class="card-title">📺 4. YouTube Publishing Details</div>
        <div class="form-group">
          <label>YouTube Title (optional):</label>
          <input type="text" id="yt-title" placeholder="Auto-generated if left blank">
        </div>
        <div class="form-group">
          <label>YouTube Description (optional):</label>
          <textarea id="yt-desc" placeholder="Auto-generated if left blank"></textarea>
        </div>
        <div class="row">
          <div class="form-group">
            <label>Tags (comma-separated):</label>
            <input type="text" id="yt-tags" placeholder="AI, Tech, Hindi">
          </div>
          <div class="form-group">
            <label>Upload Privacy:</label>
            <select id="yt-privacy">
              <option value="private" selected>Private (Safe preview)</option>
              <option value="unlisted">Unlisted (Shareable link)</option>
              <option value="public">Public (Instant publish)</option>
            </select>
          </div>
        </div>
      </div>

      <button class="btn-submit" onclick="submitPipeline('custom')">
        <span>🚀</span> Launch Custom Pipeline
      </button>
    </div>

    <!-- Status Box -->
    <div id="status-box" class="status-box"></div>
  </div>

  <script>
    let currentMode = 'auto';

    function setMode(mode) {
      currentMode = mode;
      document.getElementById('btn-auto').classList.toggle('active', mode === 'auto');
      document.getElementById('btn-custom').classList.toggle('active', mode === 'custom');
      document.getElementById('view-auto').style.display = mode === 'auto' ? 'block' : 'none';
      document.getElementById('view-custom').style.display = mode === 'custom' ? 'block' : 'none';
      hideStatus();
    }

    function toggleTokenBox() {
      const el = document.getElementById('token-box');
      el.style.display = el.style.display === 'none' ? 'block' : 'none';
    }

    async function checkToken() {
      const res = await fetch('/api/token');
      const data = await res.json();
      const txt = document.getElementById('token-status-text');
      if (data.configured) {
        txt.innerHTML = '<span style="color:#10b981;">Configured ✓</span>';
      } else {
        txt.innerHTML = '<span style="color:#ef4444;">Not Set (Click Change Token)</span>';
      }
    }

    async function saveToken() {
      const val = document.getElementById('token-input').value.trim();
      if (!val) return;
      await fetch('/api/token', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: json.stringify({token: val})
      });
      document.getElementById('token-box').style.display = 'none';
      checkToken();
    }

    function showStatus(isSuccess, msg, actionUrl) {
      const box = document.getElementById('status-box');
      box.style.display = 'block';
      box.className = 'status-box ' + (isSuccess ? 'status-success' : 'status-error');
      if (isSuccess && actionUrl) {
        box.innerHTML = msg + '<br><br><a href="' + actionUrl + '" target="_blank">🔗 Click here to watch live pipeline execution on GitHub ↗</a>';
      } else {
        box.innerHTML = msg;
      }
    }

    function hideStatus() {
      document.getElementById('status-box').style.display = 'none';
    }

    async function submitPipeline(mode) {
      hideStatus();
      const btn = event.target.closest('button');
      btn.disabled = true;
      const oldHtml = btn.innerHTML;
      btn.innerHTML = '<span>⏳</span> Triggering Pipeline...';

      const payload = {
        mode: mode,
        custom_topic: mode === 'custom' ? document.getElementById('custom-topic').value : '',
        custom_trim_start: mode === 'custom' ? document.getElementById('trim-start').value : '',
        custom_trim_end: mode === 'custom' ? document.getElementById('trim-end').value : '',
        custom_intro_url: mode === 'custom' ? document.getElementById('intro-url').value : '',
        custom_thumbnail_url: mode === 'custom' ? document.getElementById('thumb-url').value : '',
        custom_yt_title: mode === 'custom' ? document.getElementById('yt-title').value : '',
        custom_yt_description: mode === 'custom' ? document.getElementById('yt-desc').value : '',
        custom_yt_tags: mode === 'custom' ? document.getElementById('yt-tags').value : '',
        upload_privacy: mode === 'custom' ? document.getElementById('yt-privacy').value : 'private',
        force_fresh: 'true'
      };

      try {
        const res = await fetch('/api/run', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify(payload)
        });
        const data = await res.json();
        showStatus(data.success, data.message, data.actions_url);
      } catch (err) {
        showStatus(false, 'Failed to communicate with local dashboard: ' + err.message);
      } finally {
        btn.disabled = false;
        btn.innerHTML = oldHtml;
      }
    }

    checkToken();
  </script>
</body>
</html>
"""

class DashboardHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode("utf-8"))
        elif self.path == "/api/token":
            env = load_env()
            has_tok = bool(env.get("GITHUB_TOKEN") or env.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN"))
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"configured": has_tok}).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length).decode("utf-8")
        data = json.loads(raw) if raw else {}

        if self.path == "/api/token":
            tok = data.get("token", "").strip()
            if tok:
                save_env_token(tok)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"success": True}).encode("utf-8"))
            return

        if self.path == "/api/run":
            env = load_env()
            tok = env.get("GITHUB_TOKEN") or env.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
            actions_url = f"https://github.com/{REPO}/actions/workflows/{WORKFLOW_FILE}"

            if not tok:
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                err_msg = (
                    "<b>GitHub Token Missing:</b><br>"
                    "Please enter your GitHub Personal Access Token in 'Change Token' above, or "
                    f"<a href='{actions_url}' target='_blank'>Run directly on GitHub ↗</a>"
                )
                self.wfile.write(json.dumps({"success": False, "message": err_msg}).encode("utf-8"))
                return

            ok, msg = trigger_github_workflow(data, tok)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "success": ok,
                "message": msg,
                "actions_url": actions_url
            }).encode("utf-8"))
            return

        self.send_response(404)
        self.end_headers()

    def log_message(self, format, *args):
        pass

def main():
    print("\n" + "=" * 65)
    print(" 🎬 YouTube Automation Studio Dashboard")
    print(f" Running at: http://localhost:{PORT}")
    print("=" * 65)
    print("Press Ctrl+C to stop the dashboard server.\n")

    webbrowser.open(f"http://localhost:{PORT}")
    with socketserver.TCPServer(("", PORT), DashboardHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nDashboard server stopped.")

if __name__ == "__main__":
    main()
