# Cloud LLM Tracking Service

A local Python tracker, web dashboard, and automated weekly reporter that monitors newly added LLMs across **AWS Bedrock**, **Azure AI Foundry / OpenAI**, and **Google Cloud Vertex AI** — highlighting **Pros & Cons** and **US Commercial vs. US Gov** availability and pricing.

## What It Produces
- **Styled HTML Reports** (`reports/llm-report-YYYY-MM-DD.html` & `reports/latest.html`) — double-click to open in any browser (with built-in Print/Save as PDF).
- **PDF Reports** (`reports/llm-report-YYYY-MM-DD.pdf` & `reports/latest.pdf`) — ready to read, share, or email.
- **Interactive Local Dashboard** (`http://localhost:5000`) — filter by cloud provider, US Gov availability, or "New This Run".
- **Weekly History Snapshot** (`data/catalog.json`) — remembers previously seen models so each run highlights what's genuinely new.
- **Monday Morning Email Automation** (`.github/workflows/weekly-llm-report.yml`) — runs automatically every Monday morning via GitHub Actions, commits updated HTML & PDF reports to GitHub, and emails them to you.

## Quick Start (Windows PowerShell)

1. **Run a scan and generate HTML + PDF reports:**
   ```powershell
   .venv\Scripts\python.exe run_tracker.py
   ```
   *(Pass `--days 30` to look back 30 days, or `--send-email` to send the email immediately.)*

2. **Open the interactive local web dashboard:**
   ```powershell
   .venv\Scripts\python.exe run_tracker.py --dashboard
   ```
   Then open `http://localhost:5000` in your browser.

## Enabling Automated Monday Morning Emails (GitHub Actions Secrets)
Never put API keys or passwords directly in code. Instead, add these **Repository Secrets** in GitHub (`Settings → Secrets and variables → Actions → New repository secret`):
- `GEMINI_API_KEY` — your free Gemini API key from Google AI Studio
- `SMTP_USER` — your Gmail address (`zachary.wills.roberts@gmail.com`)
- `SMTP_APP_PASSWORD` — a 16-character [Google App Password](https://myaccount.google.com/apppasswords) (requires 2-Step Verification on your Google Account)
- `EMAIL_TO` — recipient email address (`zachary.wills.roberts@gmail.com`)
