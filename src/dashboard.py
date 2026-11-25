"""Local interactive web dashboard powered by Flask.

Start it anytime with:
    python run_tracker.py --dashboard
Then open http://localhost:5000 in your browser!
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template_string, request, send_from_directory

from src.analyzer import is_ai_configured
from src.pipeline import run_full_scan
from src.reporter import REPORTS_DIR
from src.storage import load_catalog

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Cloud LLM Tracker — Local Dashboard</title>
  <style>
    :root {
      --bg: #f1f5f9;
      --card: #ffffff;
      --text: #0f172a;
      --muted: #475569;
      --border: #e2e8f0;
      --primary: #4f46e5;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: var(--bg);
      color: var(--text);
    }
    .topbar {
      background: linear-gradient(135deg, #0f172a, #1e293b 55%, #312e81);
      color: #fff;
      padding: 22px 28px;
    }
    .topbar-inner {
      max-width: 1200px;
      margin: 0 auto;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 14px;
    }
    .topbar h1 { margin: 0 0 4px; font-size: 1.55rem; }
    .topbar p { margin: 0; color: #cbd5e1; font-size: 0.9rem; }
    .actions { display: flex; flex-wrap: wrap; gap: 10px; }
    .btn {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      border-radius: 10px;
      padding: 9px 15px;
      font-size: 0.88rem;
      font-weight: 600;
      cursor: pointer;
      border: 1px solid rgba(255,255,255,0.22);
      background: rgba(255,255,255,0.12);
      color: #fff;
      text-decoration: none;
    }
    .btn:hover { background: rgba(255,255,255,0.22); }
    .btn-primary { background: #6366f1; border-color: #818cf8; }
    .btn-primary:hover { background: #4f46e5; }
    .btn:disabled { opacity: 0.6; cursor: wait; }
    .main { max-width: 1200px; margin: 22px auto 60px; padding: 0 18px; }
    .notice {
      background: #fffbeb;
      border: 1px solid #fde68a;
      color: #92400e;
      padding: 12px 16px;
      border-radius: 12px;
      margin-bottom: 18px;
      font-size: 0.9rem;
    }
    .notice.ok { background: #ecfdf5; border-color: #a7f3d0; color: #065f46; }
    .kpis {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
      gap: 12px;
      margin-bottom: 18px;
    }
    .kpi {
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 15px 17px;
    }
    .kpi-label { font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.04em; color: var(--muted); }
    .kpi-val { font-size: 1.65rem; font-weight: 700; margin-top: 3px; }
    .controls {
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 14px 16px;
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      align-items: center;
      margin-bottom: 18px;
    }
    .controls input, .controls select {
      padding: 8px 12px;
      border: 1px solid #cbd5e1;
      border-radius: 8px;
      font-size: 0.9rem;
      background: #fff;
    }
    .controls input { flex: 1; min-width: 220px; }
    .cards { display: grid; grid-template-columns: 1fr; gap: 14px; }
    .card {
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 18px 20px;
    }
    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      flex-wrap: wrap;
      gap: 10px;
    }
    .card h3 { margin: 0; font-size: 1.06rem; }
    .meta { color: var(--muted); font-size: 0.84rem; margin-top: 3px; }
    .badge {
      display: inline-block;
      padding: 3px 9px;
      border-radius: 999px;
      font-size: 0.75rem;
      font-weight: 600;
    }
    .b-aws { background: #fff7ed; color: #ea580c; border: 1px solid #fed7aa; }
    .b-azure { background: #f0f9ff; color: #0284c7; border: 1px solid #bae6fd; }
    .b-gcp { background: #ecfdf5; color: #059669; border: 1px solid #a7f3d0; }
    .b-new { background: #f5f3ff; color: #7c3aed; border: 1px solid #ddd6fe; }
    .b-gov { background: #eef2ff; color: #4338ca; border: 1px solid #c7d2fe; }
    .pricing-box {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 12px;
      background: #f8fafc;
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 12px 14px;
      margin: 12px 0;
      font-size: 0.88rem;
    }
    .pros-cons {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      gap: 12px;
    }
    .box { border-radius: 10px; padding: 11px 14px; font-size: 0.87rem; }
    .box-pros { background: #f0fdf4; border: 1px solid #bbf7d0; }
    .box-cons { background: #fffbeb; border: 1px solid #fde68a; }
    .box h4 { margin: 0 0 6px; font-size: 0.82rem; text-transform: uppercase; letter-spacing: 0.04em; }
    .box ul { margin: 0; padding-left: 18px; }
    .reports-strip {
      margin-top: 28px;
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 16px 18px;
    }
    .reports-strip h2 { margin: 0 0 10px; font-size: 1.05rem; }
    .report-links { display: flex; flex-wrap: wrap; gap: 10px; }
    .report-pill {
      padding: 6px 12px;
      border-radius: 8px;
      background: #f8fafc;
      border: 1px solid #cbd5e1;
      color: #1e293b;
      text-decoration: none;
      font-size: 0.85rem;
    }
    .report-pill:hover { background: #e2e8f0; }
    #scanStatus { font-size: 0.88rem; color: #e0e7ff; margin-top: 6px; }
  </style>
</head>
<body>
  <header class="topbar">
    <div class="topbar-inner">
      <div>
        <h1>Cloud LLM Tracker Dashboard</h1>
        <p>AWS Bedrock &middot; Azure AI Foundry &middot; Google Vertex AI (US &amp; US Gov) &middot; Last scan: <span id="lastRun">{{ last_run or 'Not yet run' }}</span></p>
        <div id="scanStatus"></div>
      </div>
      <div class="actions">
        <button class="btn btn-primary" id="scanBtn" onclick="triggerScan()">Run Fresh Scan</button>
        <a class="btn" href="/reports/latest.html" target="_blank">Open Latest HTML Report</a>
        <a class="btn" href="/reports/latest.pdf" target="_blank">Open Latest PDF Report</a>
      </div>
    </div>
  </header>

  <main class="main">
    {% if ai_configured %}
      <div class="notice ok"><strong>Gemini AI Analysis Active:</strong> Newly discovered models are automatically summarized with Pros, Cons, and US / US Gov pricing notes.</div>
    {% else %}
      <div class="notice"><strong>Direct Feed Mode:</strong> Showing official AWS, Azure (live <code>prices.azure.com</code> US &amp; US Gov API), and Google Cloud feeds. Add a free <code>GEMINI_API_KEY</code> to <code>.env</code> anytime to unlock AI-written Pros &amp; Cons.</div>
    {% endif %}

    <section class="kpis">
      <div class="kpi"><div class="kpi-label">Models Tracked</div><div class="kpi-val" id="kTotal">0</div></div>
      <div class="kpi"><div class="kpi-label">New This Run</div><div class="kpi-val" id="kNew">0</div></div>
      <div class="kpi"><div class="kpi-label">AWS Bedrock</div><div class="kpi-val" id="kAws">0</div></div>
      <div class="kpi"><div class="kpi-label">Azure Foundry</div><div class="kpi-val" id="kAzure">0</div></div>
      <div class="kpi"><div class="kpi-label">Google Vertex AI</div><div class="kpi-val" id="kGcp">0</div></div>
      <div class="kpi"><div class="kpi-label">US Gov Highlighted</div><div class="kpi-val" id="kGov">0</div></div>
    </section>

    <section class="controls">
      <input type="text" id="searchBox" placeholder="Search models, vendors, pricing, or notes..." oninput="render()" />
      <select id="providerFilter" onchange="render()">
        <option value="ALL">All Clouds</option>
        <option value="AWS">AWS Bedrock</option>
        <option value="Azure">Azure Foundry</option>
        <option value="Google Cloud">Google Vertex AI</option>
      </select>
      <select id="govFilter" onchange="render()">
        <option value="ALL">All US Regions</option>
        <option value="GOV_YES">US Gov Confirmed / Mentioned</option>
      </select>
      <label style="font-size:0.88rem; display:flex; align-items:center; gap:6px; cursor:pointer;">
        <input type="checkbox" id="newOnly" onchange="render()" /> New this run only
      </label>
    </section>

    <section class="cards" id="cardsContainer"></section>

    <section class="reports-strip">
      <h2>Saved Weekly Reports (HTML &amp; PDF)</h2>
      <div class="report-links">
        {% for f in report_files %}
          <a class="report-pill" href="/reports/{{ f }}" target="_blank">{{ f }}</a>
        {% else %}
          <span class="meta">No saved reports yet. Click "Run Fresh Scan" above!</span>
        {% endfor %}
      </div>
    </section>
  </main>

  <script>
    let allModels = [];

    function badgeClass(provider) {
      if (provider === 'AWS') return 'b-aws';
      if (provider === 'Azure') return 'b-azure';
      return 'b-gcp';
    }

    function esc(str) {
      return String(str || '').replace(/[&<>"']/g, s => ({
        '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'
      }[s]));
    }

    async function loadModels() {
      const res = await fetch('/api/models');
      const data = await res.json();
      allModels = data.models || [];
      document.getElementById('lastRun').textContent = data.last_run || 'Not yet run';
      document.getElementById('kTotal').textContent = allModels.length;
      document.getElementById('kNew').textContent = allModels.filter(m => m.is_new).length;
      document.getElementById('kAws').textContent = allModels.filter(m => m.provider === 'AWS').length;
      document.getElementById('kAzure').textContent = allModels.filter(m => m.provider === 'Azure').length;
      document.getElementById('kGcp').textContent = allModels.filter(m => m.provider === 'Google Cloud').length;
      document.getElementById('kGov').textContent = allModels.filter(m => (m.us_gov_available || '').toLowerCase().includes('yes')).length;
      render();
    }

    function render() {
      const q = document.getElementById('searchBox').value.trim().toLowerCase();
      const prov = document.getElementById('providerFilter').value;
      const gov = document.getElementById('govFilter').value;
      const newOnly = document.getElementById('newOnly').checked;

      const filtered = allModels.filter(m => {
        if (prov !== 'ALL' && m.provider !== prov) return false;
        if (newOnly && !m.is_new) return false;
        if (gov === 'GOV_YES' && !(m.us_gov_available || '').toLowerCase().includes('yes')) return false;
        if (q) {
          const blob = [m.model_name, m.vendor, m.provider, m.service, m.summary, m.us_commercial_pricing, m.us_gov_pricing, m.us_gov_notes].join(' ').toLowerCase();
          if (!blob.includes(q)) return false;
        }
        return true;
      });

      const container = document.getElementById('cardsContainer');
      if (!filtered.length) {
        container.innerHTML = '<div class="card"><p class="meta">No models match your current filter. Try clearing filters or click "Run Fresh Scan".</p></div>';
        return;
      }

      container.innerHTML = filtered.map(m => `
        <article class="card">
          <div class="card-header">
            <div>
              <h3>${esc(m.model_name)}</h3>
              <div class="meta">${esc(m.service)} &middot; Vendor: ${esc(m.vendor)}${m.release_date ? ' &middot; Announced: ' + esc(m.release_date) : ''} &middot; First seen: ${esc(m.first_seen)}</div>
            </div>
            <div>
              <span class="badge ${badgeClass(m.provider)}">${esc(m.provider)}</span>
              ${m.is_new ? '<span class="badge b-new">NEW</span>' : ''}
              <span class="badge b-gov">${esc(m.us_gov_available)}</span>
            </div>
          </div>
          <p>${esc(m.summary)}</p>
          <div class="pricing-box">
            <div><strong>US Commercial (${esc(m.us_commercial_available)})</strong><br/><span class="meta">${esc(m.us_commercial_pricing)}</span></div>
            <div><strong>US Gov (${esc(m.us_gov_available)})</strong><br/><span class="meta">${esc(m.us_gov_pricing)}</span><br/><span class="meta">${esc(m.us_gov_notes)}</span></div>
          </div>
          <div class="pros-cons">
            <div class="box box-pros"><h4>Pros</h4><ul>${(m.pros || []).map(p => '<li>' + esc(p) + '</li>').join('')}</ul></div>
            <div class="box box-cons"><h4>Cons &amp; Watchouts</h4><ul>${(m.cons || []).map(c => '<li>' + esc(c) + '</li>').join('')}</ul></div>
          </div>
          ${m.source_url ? '<div class="meta" style="margin-top:10px;">Official Source: <a href="' + esc(m.source_url) + '" target="_blank" rel="noopener">' + esc(m.source_url) + '</a></div>' : ''}
        </article>
      `).join('');
    }

    async function triggerScan() {
      const btn = document.getElementById('scanBtn');
      const status = document.getElementById('scanStatus');
      btn.disabled = true;
      btn.textContent = 'Scanning clouds...';
      status.textContent = 'Fetching AWS, Azure, and Google Cloud feeds + regenerating HTML & PDF reports...';
      try {
        const res = await fetch('/api/scan', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({}) });
        const data = await res.json();
        status.textContent = `Done! Tracked ${data.total} models (${data.new_count} new). HTML & PDF reports updated.`;
        await loadModels();
      } catch (err) {
        status.textContent = 'Scan error: ' + err;
      } finally {
        btn.disabled = false;
        btn.textContent = 'Run Fresh Scan';
      }
    }

    loadModels();
  </script>
</body>
</html>
"""


def create_app() -> Flask:
    load_dotenv()
    app = Flask(__name__)

    @app.route("/")
    def index():
        load_dotenv(override=True)
        catalog = load_catalog()
        report_files = []
        if REPORTS_DIR.exists():
            report_files = sorted(
                [p.name for p in REPORTS_DIR.iterdir() if p.suffix in (".html", ".pdf")],
                reverse=True,
            )
        return render_template_string(
            DASHBOARD_HTML,
            last_run=catalog.get("last_run"),
            ai_configured=is_ai_configured(),
            report_files=report_files,
        )

    @app.route("/api/models")
    def api_models():
        catalog = load_catalog()
        models = list(catalog.get("models", {}).values())
        models.sort(
            key=lambda m: (
                bool(m.get("is_new")),
                m.get("release_date") or m.get("first_seen") or "",
                m.get("provider") or "",
                m.get("model_name") or "",
            ),
            reverse=True,
        )
        return jsonify(
            {
                "last_run": catalog.get("last_run"),
                "ai_enabled": catalog.get("ai_enabled", False),
                "models": models,
            }
        )

    @app.route("/api/scan", methods=["POST"])
    def api_scan():
        body = request.get_json(silent=True) or {}
        days = body.get("days")
        result = run_full_scan(lookback_days=int(days) if days else None)
        return jsonify(result)

    @app.route("/reports/<path:filename>")
    def serve_report(filename: str):
        return send_from_directory(REPORTS_DIR, filename)

    return app


def start_dashboard(port: int | None = None) -> None:
    load_dotenv()
    listen_port = port or int(os.getenv("DASHBOARD_PORT", "5000"))
    app = create_app()
    print(f"\nLocal Dashboard running at: http://localhost:{listen_port}")
    print("Press Ctrl+C to stop the dashboard.\n")
    app.run(host="127.0.0.1", port=listen_port, debug=False)
