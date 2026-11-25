# Cloud LLM Tracking Service

A lightweight Python tracker, local web dashboard, and automated weekly email reporter that monitors newly added LLMs across **AWS Bedrock**, **Azure AI Foundry / OpenAI**, and **Google Cloud Vertex AI** — highlighting **Pros & Cons** and **US Commercial vs. US Gov** availability and pricing.

## Features
- **Multi-Cloud Live Collection:**
  - **AWS:** Official Amazon Bedrock & AWS What's New feeds (including AWS GovCloud US launches).
  - **Azure:** Official Azure Updates feed + Microsoft's free public **Azure Retail Prices API** (`prices.azure.com`) comparing live US Commercial (`eastus`) and **Azure Government** (`usgovvirginia`) token pricing.
  - **Google Cloud:** Official Vertex AI / Model Garden release notes feed with **Assured Workloads (US Gov)** compliance notes.
- **AI-Powered Pros, Cons & Pricing Summaries:** Uses the **Gemini API** (free tier supported) with automatic retry and fallback models — and still works in Direct Feed Mode if no API key is configured.
- **HTML & PDF Reports (100% Free):** Generates styled standalone HTML (`reports/latest.html`) and ready-to-share PDF (`reports/latest.pdf`) reports on every run.
- **Interactive Local Web Dashboard:** Filter by cloud provider, US Gov availability, newly added models, or search keywords at `http://localhost:5000`.
- **Automated Weekly Monday Emails:** Includes a ready-to-use GitHub Actions workflow that runs every Monday morning, updates the reports in your fork, and emails the HTML + PDF report directly to your inbox.

---

## Quick Start (Run Locally)

### Prerequisites
- **Python 3.10+** (tested on Python 3.12)
- **Git**

### 1. Clone the repository & install dependencies

**Windows (PowerShell):**
```powershell
git clone https://github.com/zacharywillsroberts-cpu/llm-tracking-service.git
cd llm-tracking-service
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

**macOS / Linux:**
```bash
git clone https://github.com/zacharywillsroberts-cpu/llm-tracking-service.git
cd llm-tracking-service
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure your local `.env` file
Copy `.env.example` to `.env` (`.env` is listed in `.gitignore` so your keys and email settings are never uploaded to Git):

```powershell
# Windows PowerShell
Copy-Item .env.example .env
```
```bash
# macOS / Linux
cp .env.example .env
```

Open `.env` and fill in:
- `GEMINI_API_KEY` *(optional, recommended)* — get a free API key from [Google AI Studio](https://aistudio.google.com/apikey) to unlock AI-written Pros, Cons, and pricing summaries.
- `EMAIL_TO`, `SMTP_USER`, `SMTP_APP_PASSWORD` *(optional)* — only needed if you want to send email reports (see setup below).

### 3. Run a scan & view your reports

```powershell
# Run a 7-day weekly scan and generate HTML + PDF reports in reports/
.venv\Scripts\python.exe run_tracker.py

# Look back 30 days (great for your very first scan)
.venv\Scripts\python.exe run_tracker.py --days 30

# Run a scan AND email the HTML + PDF report immediately
.venv\Scripts\python.exe run_tracker.py --send-email

# Launch the interactive local web dashboard at http://localhost:5000
.venv\Scripts\python.exe run_tracker.py --dashboard
```
*(On macOS/Linux, use `python run_tracker.py ...` with your virtual environment activated.)*

---

## Receive Weekly Monday Morning Reports at Your Own Email

You can receive the styled **HTML report + PDF attachment** automatically every Monday morning for free using **GitHub Actions** — even when your computer is turned off!

### Step 1: Fork this repository
Click the **Fork** button at the top-right of this GitHub repository to create your own copy under your GitHub account.

### Step 2: Create a Gmail App Password (for sending email)
Google blocks regular passwords in automated scripts. Instead, create a free 16-character App Password:
1. Turn on **2-Step Verification** in your Google Account ([Security settings](https://myaccount.google.com/security)) if it isn't enabled yet.
2. Open [Google App Passwords](https://myaccount.google.com/apppasswords).
3. Name it `LLM Tracker`, click **Create**, and copy the 16-character code.

*(Using another email provider? Set `SMTP_HOST` and `SMTP_PORT` in your environment or workflow.)*

### Step 3: Add your GitHub Repository Secrets
In **your fork** on GitHub, go to **Settings → Secrets and variables → Actions → New repository secret** and add these four secrets:

| Secret Name | Value |
| --- | --- |
| `GEMINI_API_KEY` | Your free Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey) |
| `EMAIL_TO` | The email address where you want to receive weekly reports (you can comma-separate multiple recipients) |
| `SMTP_USER` | Your Gmail address used to send the email |
| `SMTP_APP_PASSWORD` | Your 16-character Google App Password from Step 2 |

### Step 4: Enable Actions & send yourself a test email
1. Go to the **Actions** tab in your fork (click **I understand my workflows, go ahead and enable them** if prompted on a new fork).
2. Click **Weekly Cloud LLM Report** in the left sidebar.
3. Click **Run workflow** to test it right away — within ~30–60 seconds you'll receive your first HTML + PDF Cloud LLM report!

### Customizing the Schedule
By default, `.github/workflows/weekly-llm-report.yml` runs every Monday at **8:00 AM EST / 9:00 AM EDT** (`cron: "0 13 * * 1"` in UTC). Edit that cron line in your fork if you'd like a different day or time.

---

## Project Structure

```text
├── src/
│   ├── collectors/       # AWS Bedrock, Azure Foundry/Prices API, and Google Vertex AI collectors
│   ├── analyzer.py       # Gemini API enrichment with automatic retry & model fallback
│   ├── storage.py        # Persistent catalog snapshot (data/catalog.json) to detect new models
│   ├── reporter.py       # Free standalone HTML + PDF report generator
│   ├── emailer.py        # SMTP HTML + PDF email sender
│   ├── pipeline.py       # End-to-end scan orchestrator
│   └── dashboard.py      # Local Flask web dashboard
├── .github/workflows/    # Weekly Monday morning GitHub Actions automation
├── data/                 # Tracked model history (catalog.json)
├── reports/              # Generated HTML & PDF reports (including latest.html / latest.pdf)
├── run_tracker.py        # CLI entry point
├── requirements.txt      # Python dependencies
└── .env.example          # Safe configuration template (copy to .env locally)
```
