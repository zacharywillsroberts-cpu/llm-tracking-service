"""Report generator: creates standalone HTML and PDF reports (100% free).

Every run writes:
- reports/llm-report-YYYY-MM-DD.html  (and updates reports/latest.html)
- reports/llm-report-YYYY-MM-DD.pdf   (and updates reports/latest.pdf)
"""

from __future__ import annotations

import shutil
from datetime import date, datetime
from pathlib import Path
from typing import List, Tuple

from fpdf import FPDF
from jinja2 import Template

from src.models import LLMRecord

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = PROJECT_ROOT / "reports"

HTML_REPORT_TEMPLATE = Template(
    """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Weekly Cloud LLM Tracker Report — {{ report_date }}</title>
  <style>
    :root {
      --bg: #f8fafc;
      --card: #ffffff;
      --text: #0f172a;
      --muted: #475569;
      --border: #e2e8f0;
      --aws: #ea580c;
      --aws-bg: #fff7ed;
      --azure: #0284c7;
      --azure-bg: #f0f9ff;
      --gcp: #059669;
      --gcp-bg: #ecfdf5;
      --gov: #4f46e5;
      --gov-bg: #eef2ff;
      --new: #7c3aed;
      --new-bg: #f5f3ff;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.55;
      padding: 28px 18px 60px;
    }
    .container { max-width: 1120px; margin: 0 auto; }
    .hero {
      background: linear-gradient(135deg, #0f172a 0%, #1e293b 55%, #312e81 100%);
      color: #fff;
      border-radius: 16px;
      padding: 28px 32px;
      margin-bottom: 24px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 16px;
    }
    .hero h1 { margin: 0 0 6px; font-size: 1.75rem; }
    .hero p { margin: 0; color: #cbd5e1; font-size: 0.95rem; }
    .print-btn {
      background: #ffffff;
      color: #0f172a;
      border: none;
      border-radius: 10px;
      padding: 10px 18px;
      font-weight: 600;
      cursor: pointer;
      font-size: 0.92rem;
    }
    .print-btn:hover { background: #e2e8f0; }
    .banner {
      background: #fefce8;
      border: 1px solid #fde047;
      color: #854d0e;
      padding: 12px 16px;
      border-radius: 10px;
      margin-bottom: 20px;
      font-size: 0.92rem;
    }
    .kpis {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
      gap: 14px;
      margin-bottom: 26px;
    }
    .kpi {
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 16px 18px;
    }
    .kpi-label { font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.04em; color: var(--muted); }
    .kpi-val { font-size: 1.7rem; font-weight: 700; margin-top: 4px; }
    h2 { font-size: 1.25rem; margin: 28px 0 14px; }
    table {
      width: 100%;
      border-collapse: collapse;
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 12px;
      overflow: hidden;
      font-size: 0.88rem;
      margin-bottom: 28px;
    }
    th, td { padding: 11px 13px; text-align: left; border-bottom: 1px solid var(--border); vertical-align: top; }
    th { background: #f1f5f9; font-weight: 600; color: #334155; }
    .badge {
      display: inline-block;
      padding: 3px 9px;
      border-radius: 999px;
      font-size: 0.76rem;
      font-weight: 600;
      white-space: nowrap;
    }
    .badge-aws { background: var(--aws-bg); color: var(--aws); border: 1px solid #fed7aa; }
    .badge-azure { background: var(--azure-bg); color: var(--azure); border: 1px solid #bae6fd; }
    .badge-gcp { background: var(--gcp-bg); color: var(--gcp); border: 1px solid #a7f3d0; }
    .badge-new { background: var(--new-bg); color: var(--new); border: 1px solid #ddd6fe; }
    .badge-gov { background: var(--gov-bg); color: var(--gov); border: 1px solid #c7d2fe; }
    .cards { display: grid; grid-template-columns: 1fr; gap: 16px; }
    .card {
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 20px 22px;
      break-inside: avoid;
    }
    .card-top {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      flex-wrap: wrap;
      gap: 10px;
      margin-bottom: 10px;
    }
    .card h3 { margin: 0; font-size: 1.08rem; }
    .meta { color: var(--muted); font-size: 0.84rem; margin-top: 4px; }
    .pricing-grid {
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
      gap: 14px;
      margin-top: 12px;
    }
    .box {
      border-radius: 10px;
      padding: 12px 14px;
      font-size: 0.88rem;
    }
    .box-pros { background: #f0fdf4; border: 1px solid #bbf7d0; }
    .box-cons { background: #fffbeb; border: 1px solid #fde68a; }
    .box h4 { margin: 0 0 6px; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.04em; }
    .box ul { margin: 0; padding-left: 18px; }
    .box li { margin-bottom: 4px; }
    a { color: #2563eb; text-decoration: none; }
    a:hover { text-decoration: underline; }
    footer { margin-top: 36px; text-align: center; color: var(--muted); font-size: 0.82rem; }
    @media print {
      body { background: #fff; padding: 0; }
      .print-btn { display: none; }
      .hero { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
      .badge, .box { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
    }
  </style>
</head>
<body>
  <div class="container">
    <header class="hero">
      <div>
        <h1>Cloud LLM Weekly Report</h1>
        <p>Generated {{ generated_at }} &middot; Lookback window: {{ lookback_days }} days &middot; AWS, Azure &amp; Google Cloud (US &amp; US Gov)</p>
      </div>
      <button class="print-btn" onclick="window.print()">Print / Save as PDF</button>
    </header>

    {% if status_note %}
    <div class="banner"><strong>Analysis Mode:</strong> {{ status_note }}</div>
    {% endif %}

    <section class="kpis">
      <div class="kpi"><div class="kpi-label">Models Tracked</div><div class="kpi-val">{{ records|length }}</div></div>
      <div class="kpi"><div class="kpi-label">New This Run</div><div class="kpi-val">{{ new_count }}</div></div>
      <div class="kpi"><div class="kpi-label">AWS Bedrock</div><div class="kpi-val">{{ counts['AWS'] }}</div></div>
      <div class="kpi"><div class="kpi-label">Azure Foundry</div><div class="kpi-val">{{ counts['Azure'] }}</div></div>
      <div class="kpi"><div class="kpi-label">Google Vertex AI</div><div class="kpi-val">{{ counts['Google Cloud'] }}</div></div>
      <div class="kpi"><div class="kpi-label">US Gov Highlighted</div><div class="kpi-val">{{ gov_count }}</div></div>
    </section>

    <h2>US &amp; US Gov Pricing &amp; Availability Summary</h2>
    <table>
      <thead>
        <tr>
          <th>Cloud</th>
          <th>Model / Announcement</th>
          <th>Vendor</th>
          <th>US Commercial Price</th>
          <th>US Gov Availability &amp; Price</th>
        </tr>
      </thead>
      <tbody>
        {% for r in records %}
        <tr>
          <td>
            <span class="badge {% if r.provider == 'AWS' %}badge-aws{% elif r.provider == 'Azure' %}badge-azure{% else %}badge-gcp{% endif %}">
              {{ r.provider }}
            </span>
            {% if r.is_new %}<div style="margin-top:4px;"><span class="badge badge-new">NEW</span></div>{% endif %}
          </td>
          <td>
            <strong>{{ r.model_name }}</strong>
            {% if r.release_date %}<div class="meta">{{ r.release_date }}</div>{% endif %}
          </td>
          <td>{{ r.vendor }}</td>
          <td>{{ r.us_commercial_pricing }}</td>
          <td>
            <span class="badge badge-gov">{{ r.us_gov_available }}</span>
            <div class="meta">{{ r.us_gov_pricing }}</div>
          </td>
        </tr>
        {% endfor %}
      </tbody>
    </table>

    <h2>Detailed Model Breakdown (Pros, Cons &amp; US Gov Notes)</h2>
    <div class="cards">
      {% for r in records %}
      <article class="card">
        <div class="card-top">
          <div>
            <h3>{{ r.model_name }}</h3>
            <div class="meta">
              {{ r.service }} &middot; Vendor: {{ r.vendor }}
              {% if r.release_date %} &middot; Announced: {{ r.release_date }}{% endif %}
              &middot; First tracked: {{ r.first_seen }}
            </div>
          </div>
          <div>
            <span class="badge {% if r.provider == 'AWS' %}badge-aws{% elif r.provider == 'Azure' %}badge-azure{% else %}badge-gcp{% endif %}">{{ r.provider }}</span>
            {% if r.is_new %}<span class="badge badge-new">NEW</span>{% endif %}
          </div>
        </div>

        <p>{{ r.summary }}</p>

        <div class="pricing-grid">
          <div>
            <strong>US Commercial:</strong> {{ r.us_commercial_available }}<br />
            <span class="meta">Price: {{ r.us_commercial_pricing }}</span>
          </div>
          <div>
            <strong>US Gov:</strong> {{ r.us_gov_available }}<br />
            <span class="meta">Price: {{ r.us_gov_pricing }}</span><br />
            <span class="meta">{{ r.us_gov_notes }}</span>
          </div>
        </div>

        <div class="pros-cons">
          <div class="box box-pros">
            <h4>Pros</h4>
            <ul>
              {% for p in r.pros %}<li>{{ p }}</li>{% endfor %}
            </ul>
          </div>
          <div class="box box-cons">
            <h4>Cons &amp; Watchouts</h4>
            <ul>
              {% for c in r.cons %}<li>{{ c }}</li>{% endfor %}
            </ul>
          </div>
        </div>

        {% if r.source_url %}
        <div class="meta" style="margin-top: 10px;">
          Official Source: <a href="{{ r.source_url }}" target="_blank" rel="noopener">{{ r.source_url }}</a>
        </div>
        {% endif %}
      </article>
      {% endfor %}
    </div>

    <footer>
      LLM Tracking Service &middot; Open this HTML file in any browser or use the companion PDF report in <code>reports/</code>.
    </footer>
  </div>
</body>
</html>
"""
)


def _pdf_safe(text: str) -> str:
    """Convert Unicode punctuation into clean Latin-1 text for built-in PDF fonts."""
    replacements = {
        "\u2014": "-",
        "\u2013": "-",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2022": "*",
        "\u00b7": "|",
        "\u2026": "...",
    }
    cleaned = text or ""
    for src, dst in replacements.items():
        cleaned = cleaned.replace(src, dst)
    return cleaned.encode("latin-1", "replace").decode("latin-1")


class _ReportPDF(FPDF):
    def header(self) -> None:
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(100, 116, 139)
        self.cell(
            0,
            8,
            "Cloud LLM Weekly Tracker Report (AWS | Azure | Google Cloud)",
            align="L",
            new_x="LMARGIN",
            new_y="NEXT",
        )
        self.ln(2)

    def footer(self) -> None:
        self.set_y(-14)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(148, 163, 184)
        self.cell(0, 8, f"Page {self.page_no()}", align="C")


def _write_pdf(
    records: List[LLMRecord],
    pdf_path: Path,
    report_date: str,
    lookback_days: int,
    status_note: str,
) -> None:
    pdf = _ReportPDF()
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.add_page()
    w = pdf.epw  # Full usable horizontal page width

    # Title block
    pdf.set_fill_color(15, 23, 42)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(
        w,
        12,
        f"  Cloud LLM Weekly Report - {report_date}",
        fill=True,
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.set_font("Helvetica", "", 9.5)
    pdf.cell(
        w,
        7,
        f"  Lookback: {lookback_days} days | Providers: AWS Bedrock, Azure AI Foundry, Google Vertex AI (US & US Gov)",
        fill=True,
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.ln(5)

    # Summary stats
    pdf.set_text_color(15, 23, 42)
    aws_n = sum(1 for r in records if r.provider == "AWS")
    az_n = sum(1 for r in records if r.provider == "Azure")
    gcp_n = sum(1 for r in records if r.provider == "Google Cloud")
    new_n = sum(1 for r in records if r.is_new)

    pdf.set_font("Helvetica", "B", 10)
    pdf.multi_cell(
        w,
        6,
        _pdf_safe(
            f"Summary: {len(records)} models tracked | {new_n} new this run | "
            f"AWS: {aws_n} | Azure: {az_n} | Google Cloud: {gcp_n}"
        ),
        new_x="LMARGIN",
        new_y="NEXT",
    )
    if status_note:
        pdf.set_font("Helvetica", "I", 8.5)
        pdf.set_text_color(71, 85, 105)
        pdf.multi_cell(w, 5, _pdf_safe(f"Mode: {status_note}"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # Model detail sections
    for idx, r in enumerate(records, start=1):
        if pdf.get_y() > 230:
            pdf.add_page()

        tag = " [NEW]" if r.is_new else ""
        pdf.set_x(pdf.l_margin)
        pdf.set_fill_color(241, 245, 249)
        pdf.set_text_color(15, 23, 42)
        pdf.set_font("Helvetica", "B", 10.5)
        pdf.multi_cell(
            w,
            6.5,
            _pdf_safe(f"{idx}. [{r.provider}] {r.model_name}{tag}"),
            fill=True,
            new_x="LMARGIN",
            new_y="NEXT",
        )

        pdf.set_font("Helvetica", "", 8.6)
        pdf.set_text_color(71, 85, 105)
        meta_line = f"Service: {r.service} | Vendor: {r.vendor}"
        if r.release_date:
            meta_line += f" | Announced: {r.release_date}"
        pdf.multi_cell(w, 5, _pdf_safe(meta_line), new_x="LMARGIN", new_y="NEXT")

        pdf.set_text_color(15, 23, 42)
        pdf.set_font("Helvetica", "", 9)
        pdf.multi_cell(w, 5, _pdf_safe(r.summary), new_x="LMARGIN", new_y="NEXT")

        pdf.set_font("Helvetica", "B", 8.6)
        pdf.multi_cell(
            w,
            5,
            _pdf_safe(f"US Commercial ({r.us_commercial_available}): {r.us_commercial_pricing}"),
            new_x="LMARGIN",
            new_y="NEXT",
        )
        pdf.multi_cell(
            w,
            5,
            _pdf_safe(f"US Gov ({r.us_gov_available}): {r.us_gov_pricing}"),
            new_x="LMARGIN",
            new_y="NEXT",
        )
        if r.us_gov_notes:
            pdf.set_font("Helvetica", "I", 8.3)
            pdf.set_text_color(71, 85, 105)
            pdf.multi_cell(
                w, 4.8, _pdf_safe(f"US Gov Note: {r.us_gov_notes}"), new_x="LMARGIN", new_y="NEXT"
            )

        pdf.set_text_color(22, 101, 52)
        pdf.set_font("Helvetica", "B", 8.6)
        pdf.cell(w, 5, "Pros:", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 8.5)
        pdf.set_text_color(15, 23, 42)
        for p in r.pros:
            pdf.multi_cell(w, 4.8, _pdf_safe(f"  + {p}"), new_x="LMARGIN", new_y="NEXT")

        pdf.set_text_color(180, 83, 9)
        pdf.set_font("Helvetica", "B", 8.6)
        pdf.cell(w, 5, "Cons:", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 8.5)
        pdf.set_text_color(15, 23, 42)
        for c in r.cons:
            pdf.multi_cell(w, 4.8, _pdf_safe(f"  - {c}"), new_x="LMARGIN", new_y="NEXT")

        if r.source_url:
            pdf.set_font("Helvetica", "I", 7.8)
            pdf.set_text_color(37, 99, 235)
            pdf.multi_cell(
                w,
                4.5,
                _pdf_safe(f"Source: {r.source_url}"),
                wrapmode="CHAR",
                new_x="LMARGIN",
                new_y="NEXT",
            )

        pdf.ln(3.5)

    pdf.output(str(pdf_path))


def generate_reports(
    records: List[LLMRecord],
    lookback_days: int,
    status_note: str = "",
    reports_dir: Path = REPORTS_DIR,
) -> Tuple[Path, Path]:
    """Generate both HTML and PDF reports and update latest.html / latest.pdf."""
    reports_dir.mkdir(parents=True, exist_ok=True)
    today_str = date.today().isoformat()
    generated_at = datetime.now().strftime("%B %d, %Y at %I:%M %p")

    counts = {
        "AWS": sum(1 for r in records if r.provider == "AWS"),
        "Azure": sum(1 for r in records if r.provider == "Azure"),
        "Google Cloud": sum(1 for r in records if r.provider == "Google Cloud"),
    }
    new_count = sum(1 for r in records if r.is_new)
    gov_count = sum(1 for r in records if "yes" in r.us_gov_available.lower())

    html_content = HTML_REPORT_TEMPLATE.render(
        report_date=today_str,
        generated_at=generated_at,
        lookback_days=lookback_days,
        status_note=status_note,
        records=records,
        counts=counts,
        new_count=new_count,
        gov_count=gov_count,
    )

    html_path = reports_dir / f"llm-report-{today_str}.html"
    latest_html = reports_dir / "latest.html"
    html_path.write_text(html_content, encoding="utf-8")
    shutil.copyfile(html_path, latest_html)

    pdf_path = reports_dir / f"llm-report-{today_str}.pdf"
    latest_pdf = reports_dir / "latest.pdf"
    _write_pdf(records, pdf_path, today_str, lookback_days, status_note)
    shutil.copyfile(pdf_path, latest_pdf)

    return html_path, pdf_path
