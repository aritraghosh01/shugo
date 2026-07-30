from __future__ import annotations

import asyncio
from pathlib import Path

from aiohttp import web

from shugo.approval.file_channel import apply_verdict, list_pending


HTML_PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>SHUGO — Pending Approvals</title>
<style>
 :root { color-scheme: light dark; --brand:#A03A26; }
 * { box-sizing: border-box; }
 body { font: 15px/1.5 -apple-system, Segoe UI, Roboto, sans-serif; margin: 0; padding: 2rem; max-width: 900px; margin-inline: auto; }
 h1 { color: var(--brand); margin: 0 0 1rem; font-size: 1.4rem; }
 .empty { opacity: .6; padding: 2rem; text-align: center; border: 1px dashed #888; border-radius: 6px; }
 .card { border: 1px solid #8884; border-radius: 8px; padding: 1rem 1.25rem; margin-bottom: 1rem; }
 .card h2 { font-size: 1rem; margin: 0 0 .5rem; }
 .card dl { display: grid; grid-template-columns: max-content 1fr; gap: .25rem 1rem; margin: 0 0 .75rem; }
 .card dt { opacity: .6; }
 .card pre { background: #8881; padding: .5rem .75rem; border-radius: 4px; overflow-x: auto; margin: .25rem 0; }
 button { font: inherit; padding: .5rem 1rem; border-radius: 6px; border: 1px solid #8884; cursor: pointer; margin-right: .5rem; }
 button.approve { background: #0a7c3a; color: white; border-color: #0a7c3a; }
 button.deny    { background: #b23a2e; color: white; border-color: #b23a2e; }
 footer { opacity: .55; margin-top: 2rem; font-size: .85rem; }
</style>
</head>
<body>
<h1>SHUGO — pending approvals</h1>
<div id="root"><div class="empty">loading…</div></div>
<footer>polling every 1 s · bound to 127.0.0.1 · no auth (local single-user tool)</footer>
<script>
async function fetchPending() {
  const r = await fetch('/api/pending');
  return await r.json();
}
async function resolve(id, decision) {
  const note = decision === 'deny' ? (prompt('note (optional):') || null) : null;
  const r = await fetch('/api/verdict/' + encodeURIComponent(id), {
    method: 'POST',
    headers: {'content-type': 'application/json'},
    body: JSON.stringify({decision, note}),
  });
  if (!r.ok) alert('failed: ' + await r.text());
  await render();
}
function esc(s) { return String(s).replace(/[<>&"']/g, c => ({'<':'&lt;','>':'&gt;','&':'&amp;','"':'&quot;',"'":'&#39;'}[c])); }
async function render() {
  const items = await fetchPending();
  const root = document.getElementById('root');
  if (!items.length) { root.innerHTML = '<div class="empty">no pending approvals</div>'; return; }
  root.innerHTML = items.map(e => `
    <div class="card">
      <h2>${esc(e.server)}::${esc(e.tool)} <small style="opacity:.5">${esc(e.id.slice(0,8))}</small></h2>
      <dl>
        <dt>rule</dt><dd>${esc(e.rule_id || '-')}</dd>
        <dt>reason</dt><dd>${esc(e.reason || '-')}</dd>
        ${(e.controls||[]).length ? `<dt>controls</dt><dd>${(e.controls||[]).map(esc).join(', ')}</dd>` : ''}
      </dl>
      <pre>${esc(JSON.stringify(e.args || {}, null, 2))}</pre>
      <button class="approve" onclick="resolve('${esc(e.id)}','allow')">Approve</button>
      <button class="deny"    onclick="resolve('${esc(e.id)}','deny')">Deny</button>
    </div>
  `).join('');
}
render();
setInterval(render, 1000);
</script>
</body>
</html>
"""


def build_app(home: Path) -> web.Application:
    async def index(_request: web.Request) -> web.Response:
        return web.Response(text=HTML_PAGE, content_type="text/html")

    async def api_pending(_request: web.Request) -> web.Response:
        return web.json_response(list_pending(home))

    async def api_verdict(request: web.Request) -> web.Response:
        approval_id = request.match_info["id"]
        try:
            payload = await request.json()
        except Exception:
            return web.Response(status=400, text="invalid json body")
        decision = payload.get("decision")
        if decision not in ("allow", "deny"):
            return web.Response(status=400, text="decision must be 'allow' or 'deny'")
        note = payload.get("note")
        try:
            apply_verdict(home, approval_id, decision, approver="http-ui", note=note)
        except FileNotFoundError:
            return web.Response(status=404, text="already resolved")
        return web.json_response({"ok": True})

    app = web.Application()
    app.router.add_get("/", index)
    app.router.add_get("/api/pending", api_pending)
    app.router.add_post("/api/verdict/{id}", api_verdict)
    return app


async def run_http_ui(home: Path, host: str = "127.0.0.1", port: int = 6247) -> None:
    """Run the aiohttp app forever. Cancel this task to shut down."""
    app = build_app(home)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host=host, port=port)
    await site.start()
    try:
        while True:
            await asyncio.sleep(3600)
    finally:
        await runner.cleanup()
