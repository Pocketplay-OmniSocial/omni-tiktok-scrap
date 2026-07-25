from __future__ import annotations

import argparse
import json
import tempfile
import subprocess
import atexit
import sys
import threading
import uuid
from dataclasses import asdict, dataclass, field
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


@dataclass
class Job:
    id: str
    command: list[str]
    cookie_file: str | None = None
    status: str = "queued"
    returncode: int | None = None
    log: list[str] = field(default_factory=list)


PROCESSES: dict[str, subprocess.Popen[str]] = {}


JOBS: dict[str, Job] = {}
JOBS_LOCK = threading.Lock()

INDEX_HTML = """<!doctype html>
<html lang="vi">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Omni TikTok Scraper</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #09090f;
      --panel: rgba(255,255,255,.08);
      --panel-strong: rgba(255,255,255,.13);
      --text: #f7f7fb;
      --muted: #aaa7b8;
      --line: rgba(255,255,255,.14);
      --accent: #00f2ea;
      --accent-2: #ff0050;
      --good: #31d0aa;
      --bad: #ff6b7a;
      --shadow: 0 28px 80px rgba(0,0,0,.45);
      --radius: 24px;
      font-family: "Segoe UI", Roboto, Arial, "Helvetica Neue", sans-serif;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      background:
        radial-gradient(circle at top left, rgba(0,242,234,.28), transparent 32rem),
        radial-gradient(circle at top right, rgba(255,0,80,.24), transparent 30rem),
        var(--bg);
      color: var(--text);
    }
    main { width: min(1120px, calc(100% - 32px)); margin: 0 auto; padding: 48px 0; }
    .hero { display: grid; grid-template-columns: 1.1fr .9fr; gap: 24px; align-items: stretch; }
    .card { background: var(--panel); border: 1px solid var(--line); border-radius: var(--radius); box-shadow: var(--shadow); backdrop-filter: blur(18px); }
    .intro { padding: clamp(24px, 5vw, 48px); }
    .eyebrow { color: var(--accent); font-weight: 800; letter-spacing: .16em; text-transform: uppercase; font-size: 12px; }
    h1 { margin: 14px 0 16px; font-size: clamp(40px, 7vw, 84px); line-height: .9; letter-spacing: -.07em; }
    p { color: var(--muted); font-size: 17px; line-height: 1.65; max-width: 64ch; }
    .badges { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 28px; }
    .badge { border: 1px solid var(--line); border-radius: 999px; padding: 9px 12px; color: #dddaf0; background: rgba(255,255,255,.06); font-size: 13px; }
    form { padding: 24px; display: grid; gap: 16px; }
    label { display: grid; gap: 8px; color: #e9e7f4; font-weight: 700; }
    input, select, textarea { width: 100%; border: 1px solid var(--line); border-radius: 14px; background: rgba(0,0,0,.28); color: var(--text); min-height: 48px; padding: 0 14px; font: inherit; outline: none; }
    textarea { min-height: 120px; padding: 12px 14px; resize: vertical; line-height: 1.45; }
    input:focus, select:focus, textarea:focus, button:focus-visible { border-color: var(--accent); box-shadow: 0 0 0 4px rgba(0,242,234,.16); }
    .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
    .toggle { display: flex; align-items: center; gap: 10px; color: var(--muted); font-weight: 600; }
    .toggle input { width: 20px; min-height: 20px; accent-color: var(--accent); }
    button { border: 0; border-radius: 16px; min-height: 54px; color: #05050a; background: linear-gradient(135deg, var(--accent), #7cf7ff 52%, var(--accent-2)); font-weight: 900; font-size: 16px; cursor: pointer; transition: transform .18s ease, filter .18s ease; }
    button:hover { transform: translateY(-1px); filter: brightness(1.08); }
    button:disabled { cursor: not-allowed; opacity: .58; transform: none; }
    .status { margin-top: 24px; padding: 18px; }
    .status-head { display: flex; justify-content: space-between; gap: 12px; align-items: center; color: var(--muted); }
    .status-actions { display: flex; gap: 10px; align-items: center; }
    .ghost { min-height: 38px; padding: 0 14px; border: 1px solid var(--line); color: var(--text); background: rgba(255,255,255,.07); }
    .pill { border-radius: 999px; padding: 7px 11px; background: var(--panel-strong); color: var(--text); font-weight: 800; }
    .progress-wrap { margin-top: 14px; display: grid; gap: 8px; }
    .progress-meta { display: flex; justify-content: space-between; gap: 12px; color: var(--muted); font-size: 14px; }
    .progress-track { height: 12px; overflow: hidden; border-radius: 999px; background: rgba(255,255,255,.1); border: 1px solid var(--line); }
    .progress-fill { width: 0%; height: 100%; border-radius: inherit; background: linear-gradient(90deg, var(--accent), var(--accent-2)); transition: width .22s ease; }
    pre { margin: 14px 0 0; min-height: 220px; max-height: 420px; overflow: auto; white-space: pre-wrap; background: rgba(0,0,0,.35); border: 1px solid var(--line); border-radius: 16px; padding: 14px; color: #e9e7f4; line-height: 1.55; }
    .steps { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; margin-top: 24px; }
    .step { padding: 18px; }
    .step strong { display: block; margin-bottom: 8px; }
    .step span { color: var(--muted); line-height: 1.5; }
    @media (max-width: 820px) { main { padding: 24px 0; } .hero, .grid, .steps { grid-template-columns: 1fr; } }
    @media (prefers-reduced-motion: reduce) { * { transition: none !important; scroll-behavior: auto !important; } }
  </style>
</head>
<body>
  <main>
    <section class="hero">
      <div class="card intro">
        <div class="eyebrow">Omni TikTok Scraper</div>
        <h1>T&#7843;i k&#234;nh TikTok g&#7885;n, r&#245;, c&#243; log.</h1>
        <p>Nh&#7853;p username ho&#7863;c link k&#234;nh. App l&#7845;y metadata JSON/CSV v&#224; t&#7843;i video v&#224;o th&#432; m&#7909;c output b&#7857;ng engine CLI hi&#7879;n c&#243;.</p>
        <div class="badges" aria-label="T&#237;nh n&#259;ng">
          <span class="badge">Kh&#244;ng login m&#7863;c &#273;&#7883;nh</span>
          <span class="badge">Cookie t&#249;y ch&#7885;n</span>
          <span class="badge">Proxy t&#249;y ch&#7885;n</span>
          <span class="badge">Retry + delay</span>
        </div>
      </div>
      <form class="card" id="job-form" action="javascript:void(0)">
        <label>Username, URL, ho&#7863;c channel ID
          <input name="target" required placeholder="khaby.lame, https://www.tiktok.com/@khaby.lame, ho&#7863;c tiktokuser:MS4w..." autocomplete="off">
        </label>
        <div class="grid">
          <label>S&#7889; video
            <input name="limit" type="number" min="1" value="50" placeholder="50" inputmode="numeric">
          </label>
          <label>&#272;&#7883;nh d&#7841;ng metadata
            <select name="format">
              <option value="both">JSON + CSV</option>
              <option value="json">JSON</option>
              <option value="csv">CSV</option>
            </select>
          </label>
        </div>
        <label>Th&#432; m&#7909;c output
          <input name="output" value="downloads" autocomplete="off">
        </label>
        <div class="grid">
          <label>Cookie file
            <input name="cookies" placeholder="cookies.txt" autocomplete="off">
          </label>
          <label>Proxy
            <input name="proxy" placeholder="http://user:pass@host:port" autocomplete="off">
          </label>
        </div>
        <label>Paste cookie
          <textarea name="cookie_text" spellcheck="false" placeholder="D&#225;n JSON t&#7915; omni-chrome-cookies, Netscape cookies.txt, ho&#7863;c header Cookie: a=b; c=d"></textarea>
        </label>
        <div class="grid">
          <label>Delay min
            <input name="delay_min" type="number" min="0" step="0.1" value="1">
          </label>
          <label>Delay max
            <input name="delay_max" type="number" min="0" step="0.1" value="4">
          </label>
        </div>
        <div class="grid">
          <label>Retries
            <input name="retries" type="number" min="1" value="3" inputmode="numeric">
          </label>
          <label class="toggle"><input name="no_download" type="checkbox"> Ch&#7881; l&#7845;y metadata</label>
          <label class="toggle"><input name="video_only" type="checkbox" checked> T&#7843;i video th&#244;i</label>
        </div>
        <button id="submit" type="button">B&#7855;t &#273;&#7847;u t&#7843;i</button>
      </form>
    </section>
    <section class="steps" aria-label="Quy tr&#236;nh">
      <div class="card step"><strong>1. L&#7845;y danh s&#225;ch</strong><span>Duy&#7879;t k&#234;nh, gi&#7899;i h&#7841;n theo s&#7889; video n&#7871;u c&#243;.</span></div>
      <div class="card step"><strong>2. Xu&#7845;t metadata</strong><span>L&#432;u caption, stats, hashtag, nh&#7841;c, t&#225;c gi&#7843;.</span></div>
      <div class="card step"><strong>3. T&#7843;i video</strong><span>Retry khi l&#7895;i, log video fail v&#224;o `failed.json`.</span></div>
    </section>
    <section class="card status" aria-live="polite">
      <div class="status-head"><strong>Ti&#7871;n tr&#236;nh</strong><div class="status-actions"><button class="ghost" id="cancel" type="button" disabled>D&#7915;ng job</button><span class="pill" id="status">idle</span></div></div>
      <div class="progress-wrap" aria-label="Ti&#7871;n tr&#236;nh t&#7843;i">
        <div class="progress-meta"><span id="progress-label">Ch&#432;a t&#7843;i</span><span id="progress-percent">0%</span></div>
        <div class="progress-track"><div class="progress-fill" id="progress-fill"></div></div>
      </div>
      <pre id="log">Ch&#432;a c&#243; job.</pre>
    </section>
  </main>
  <script>
    var form = document.querySelector('#job-form');
    var statusEl = document.querySelector('#status');
    var logEl = document.querySelector('#log');
    var submit = document.querySelector('#submit');
    var cancel = document.querySelector('#cancel');
    var progressFill = document.querySelector('#progress-fill');
    var progressLabel = document.querySelector('#progress-label');
    var progressPercent = document.querySelector('#progress-percent');
    var currentJobId = null;
    var timer;

    var storageKey = 'omni-tiktok-scraper-form-v1';

    function payload(formData) {
      var data = {};
      formData.forEach(function(value, key) { data[key] = value; });
      data.no_download = formData.has('no_download');
      data.video_only = formData.has('video_only');
      return data;
    }

    function saveForm() {
      try { localStorage.setItem(storageKey, JSON.stringify(payload(new FormData(form)))); }
      catch (error) { /* ignore private mode/storage errors */ }
    }

    function restoreForm() {
      try {
        var saved = JSON.parse(localStorage.getItem(storageKey) || '{}');
        Array.prototype.forEach.call(form.elements, function(field) {
          if (!field.name || saved[field.name] === undefined) return;
          if (field.type === 'checkbox') field.checked = Boolean(saved[field.name]);
          else field.value = saved[field.name];
        });
      } catch (error) { /* ignore corrupted local storage */ }
    }

    function setProgress(percent, label) {
      progressFill.style.width = Math.max(0, Math.min(100, percent)) + '%';
      progressPercent.textContent = Math.max(0, Math.min(100, percent)) + '%';
      if (label) progressLabel.textContent = label;
    }

    function updateProgress(log) {
      for (var i = log.length - 1; i >= 0; i--) {
        var match = /^PROGRESS (\\d+)\\/(\\d+) (\\d+)%(?: speed=(\\d+)B\\/s eta=([^s]+)s)?/.exec(log[i]);
        if (!match) continue;
        var speed = match[4] ? Math.round(Number(match[4]) / 1024) + ' KB/s' : '';
        var eta = match[5] ? ' ETA ' + match[5] + 's' : '';
        setProgress(Number(match[3]), 'Video ' + match[1] + '/' + match[2] + (speed ? ' - ' + speed : '') + eta);
        return;
      }
    }

    function showError(error) {
      clearInterval(timer);
      statusEl.textContent = 'error';
      logEl.textContent = error && error.message ? error.message : String(error);
      submit.disabled = false;
      cancel.disabled = true;
    }

    async function readJson(res) {
      var text = await res.text();
      try { return JSON.parse(text); }
      catch (error) { return { error: text || 'HTTP ' + res.status }; }
    }

    async function poll(id) {
      try {
        var res = await fetch('/api/jobs/' + encodeURIComponent(id));
        var job = await readJson(res);
        if (!res.ok) throw new Error(job.error || 'HTTP ' + res.status);
        statusEl.textContent = job.status;
        logEl.textContent = job.log.length ? job.log.join('\\n') : '\u0110ang kh\u1edfi \u0111\u1ed9ng...';
        logEl.scrollTop = logEl.scrollHeight;
        if (job.status === 'done' || job.status === 'failed') {
          clearInterval(timer);
          submit.disabled = false;
          cancel.disabled = true;
        }
      } catch (error) {
        showError(error);
      }
    }

    async function startJob(event) {
      if (event) event.preventDefault();
      if (!form.reportValidity()) return false;
      saveForm();
      submit.disabled = true;
      cancel.disabled = true;
      currentJobId = null;
      statusEl.textContent = 'queued';
      setProgress(0, '\u0110ang chuẩn bị...');
      logEl.textContent = '\u0110ang t\u1ea1o job...';
      try {
        var res = await fetch('/api/jobs', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload(new FormData(form)))
        });
        var job = await readJson(res);
        if (!res.ok) throw new Error(job.error || 'HTTP ' + res.status);
        currentJobId = job.id;
        cancel.disabled = false;
        statusEl.textContent = job.status;
        logEl.textContent = 'Job created: ' + job.id;
        clearInterval(timer);
        timer = setInterval(function() { poll(job.id); }, 1000);
        poll(job.id);
      } catch (error) {
        showError(error);
      }
      return false;
    }

    async function cancelJob() {
      if (!currentJobId) return;
      cancel.disabled = true;
      try {
        var res = await fetch('/api/jobs/' + encodeURIComponent(currentJobId) + '/cancel', { method: 'POST' });
        var job = await readJson(res);
        if (!res.ok) throw new Error(job.error || 'HTTP ' + res.status);
        statusEl.textContent = job.status;
        logEl.textContent = job.log.length ? job.log.join('\\n') : 'Job stopped';
      } catch (error) {
        showError(error);
      }
    }

    restoreForm();
    form.addEventListener('input', saveForm);
    form.addEventListener('change', saveForm);
    form.addEventListener('submit', startJob);
    submit.addEventListener('click', startJob);
    cancel.addEventListener('click', cancelJob);
  </script>
</body>
</html>
"""


def clean_text(value: object) -> str:
    return str(value or "").strip()


def cookie_to_netscape(cookie_text: str) -> str:
    cookie_text = cookie_text.strip()
    if not cookie_text:
        return ""
    if cookie_text.startswith("{"):
        data = json.loads(cookie_text)
        cookies = data.get("cookies", [])
        lines = ["# Netscape HTTP Cookie File"]
        for cookie in cookies:
            domain = clean_text(cookie.get("domain")) or ".tiktok.com"
            include_subdomains = "TRUE" if domain.startswith(".") or not cookie.get("hostOnly") else "FALSE"
            path = clean_text(cookie.get("path")) or "/"
            secure = "TRUE" if cookie.get("secure") else "FALSE"
            expires = str(int(float(cookie.get("expirationDate") or 0)))
            name = clean_text(cookie.get("name"))
            value = clean_text(cookie.get("value"))
            if name:
                lines.append("\t".join([domain, include_subdomains, path, secure, expires, name, value]))
        return "\n".join(lines) + "\n"
    if "\t" in cookie_text and "Netscape" in cookie_text[:200]:
        return cookie_text + ("" if cookie_text.endswith("\n") else "\n")

    header = cookie_text.removeprefix("Cookie:").strip()
    lines = ["# Netscape HTTP Cookie File"]
    for part in header.split(";"):
        if "=" not in part:
            continue
        name, value = part.strip().split("=", 1)
        if name:
            lines.append("\t".join([".tiktok.com", "TRUE", "/", "FALSE", "0", name, value]))
    return "\n".join(lines) + "\n"


def write_cookie_file(cookie_text: str) -> str | None:
    content = cookie_to_netscape(cookie_text)
    if not content.strip().splitlines()[1:]:
        return None
    file = tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, suffix=".cookies.txt")
    with file:
        file.write(content)
    return file.name


def make_command(data: dict[str, object]) -> tuple[list[str], str | None]:
    target = clean_text(data.get("target"))
    if not target:
        raise ValueError("Thieu username hoac URL")

    command = [sys.executable, "-m", "omni_tiktok_scraper", target]
    cookie_file = write_cookie_file(clean_text(data.get("cookie_text")))
    if not clean_text(data.get("limit")):
        data["limit"] = "50"

    options = {
        "limit": "--limit",
        "output": "--output",
        "format": "--format",
        "proxy": "--proxy",
        "delay_min": "--delay-min",
        "delay_max": "--delay-max",
        "retries": "--retries",
    }
    for key, flag in options.items():
        value = clean_text(data.get(key))
        if value:
            command.extend([flag, value])
    cookies = cookie_file or clean_text(data.get("cookies"))
    if cookies:
        command.extend(["--cookies", cookies])
    if data.get("video_only"):
        command.append("--video-only")
    if data.get("no_download"):
        command.append("--no-download")
    return command, cookie_file


def run_job(job_id: str) -> None:
    with JOBS_LOCK:
        job = JOBS[job_id]
        job.status = "running"
        job.log.append("Job started")
        job.log.append("Running: " + " ".join(job.command))

    try:
        process = subprocess.Popen(
            job.command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=Path.cwd(),
        )
        with JOBS_LOCK:
            PROCESSES[job_id] = process
        assert process.stdout is not None
        for line in process.stdout:
            with JOBS_LOCK:
                job.log.append(line.rstrip())
                job.log = job.log[-500:]
        returncode = process.wait()
        with JOBS_LOCK:
            job.returncode = returncode
            job.status = "done" if returncode == 0 else "failed"
            job.log.append(f"Exit code: {returncode}")
    except Exception as exc:  # noqa: BLE001 - keep job visible when process launch fails.
        with JOBS_LOCK:
            job.returncode = -1
            job.status = "failed"
            job.log.append(str(exc))
    finally:
        with JOBS_LOCK:
            PROCESSES.pop(job_id, None)
        if job.cookie_file:
            Path(job.cookie_file).unlink(missing_ok=True)


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/":
            self.send_html(INDEX_HTML)
            return
        if path.startswith("/api/jobs/"):
            job_id = path.rsplit("/", 1)[-1]
            with JOBS_LOCK:
                job = JOBS.get(job_id)
                payload = asdict(job) if job else {"error": "Job khong ton tai"}
            self.send_json(payload, HTTPStatus.OK if job else HTTPStatus.NOT_FOUND)
            return
        self.send_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path.startswith("/api/jobs/") and path.endswith("/cancel"):
            job_id = path.split("/")[-2]
            self.cancel_job(job_id)
            return
        if path != "/api/jobs":
            self.send_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)
            return
        try:
            length = int(self.headers.get("content-length", "0"))
            data = json.loads(self.rfile.read(length) or b"{}")
            command, cookie_file = make_command(data)
        except (ValueError, json.JSONDecodeError) as exc:
            self.send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            return
        except Exception as exc:  # noqa: BLE001 - show web error instead of silent browser failure.
            self.send_json({"error": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        job = Job(id=uuid.uuid4().hex[:10], command=command, cookie_file=cookie_file)
        with JOBS_LOCK:
            JOBS[job.id] = job
        threading.Thread(target=run_job, args=(job.id,), daemon=True).start()
        self.send_json(asdict(job), HTTPStatus.CREATED)

    def cancel_job(self, job_id: str) -> None:
        with JOBS_LOCK:
            job = JOBS.get(job_id)
            process = PROCESSES.get(job_id)
        if not job:
            self.send_json({"error": "Job khong ton tai"}, HTTPStatus.NOT_FOUND)
            return
        if process and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
            with JOBS_LOCK:
                job.status = "failed"
                job.returncode = -9
                job.log.append("Job stopped by user")
        self.send_json(asdict(job), HTTPStatus.OK)

    def log_message(self, format: str, *args: object) -> None:
        return

    def send_html(self, body: str) -> None:
        encoded = body.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def send_json(self, payload: dict[str, object], status: HTTPStatus) -> None:
        encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Web UI cho Omni TikTok Scraper")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=7860)
    return parser.parse_args(argv)


def stop_running_jobs() -> None:
    with JOBS_LOCK:
        processes = list(PROCESSES.items())
    for job_id, process in processes:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
        with JOBS_LOCK:
            job = JOBS.get(job_id)
            if job and job.status == "running":
                job.status = "failed"
                job.returncode = -9
                job.log.append("Server stopped; job killed")


def main() -> None:
    args = parse_args(sys.argv[1:])
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    atexit.register(stop_running_jobs)
    print(f"Open http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Stopping server and running jobs...")
    finally:
        stop_running_jobs()
        server.server_close()


if __name__ == "__main__":
    main()
