"""Core pipeline orchestrator shared by the CLI (`run_tracker.py`) and web dashboard."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict

from dotenv import load_dotenv

from src.analyzer import enrich_with_gemini
from src.collectors import (
    collect_aws_models,
    collect_azure_models,
    collect_google_models,
)
from src.emailer import send_weekly_email
from src.reporter import generate_reports
from src.storage import merge_and_save_catalog


def run_full_scan(
    lookback_days: int | None = None,
    send_email: bool = False,
) -> Dict[str, object]:
    """Run all three cloud collectors, optionally enrich with Gemini, save history,
    generate HTML + PDF reports, and optionally email the weekly report.
    """
    load_dotenv(override=True)
    days = lookback_days or int(os.getenv("LOOKBACK_DAYS", "7"))
    should_email = send_email or os.getenv("SEND_EMAIL", "").lower() in ("1", "true", "yes")

    print(f"\n[1/4] Collecting latest LLM updates (lookback: {days} days)...")
    aws_models = collect_aws_models(lookback_days=days)
    print(f"      AWS Bedrock:   {len(aws_models)} item(s)")
    azure_models = collect_azure_models(lookback_days=days)
    print(f"      Azure Foundry: {len(azure_models)} item(s)")
    google_models = collect_google_models(lookback_days=days)
    print(f"      Google Vertex: {len(google_models)} item(s)")

    combined = aws_models + azure_models + google_models

    print("[2/4] Running AI analysis (Pros, Cons, US/US Gov pricing)...")
    enriched, ai_used, status_note = enrich_with_gemini(combined)
    print(f"      {status_note}")

    print("[3/4] Updating local model history (data/catalog.json)...")
    all_records, new_records, catalog = merge_and_save_catalog(
        enriched, lookback_days=days, ai_enabled=ai_used
    )
    print(f"      Total tracked: {len(all_records)} | New this run: {len(new_records)}")

    print("[4/4] Generating HTML and PDF reports...")
    html_path, pdf_path = generate_reports(
        all_records, lookback_days=days, status_note=status_note
    )
    print(f"      HTML Report: {html_path}")
    print(f"      PDF Report:  {pdf_path}")

    email_sent = False
    email_status = "Email not requested for this run."
    if should_email:
        print("[5/5] Sending weekly email report...")
        email_sent, email_status = send_weekly_email(
            html_path=html_path,
            pdf_path=pdf_path,
            total_count=len(all_records),
            new_count=len(new_records),
        )
        print(f"      {email_status}")

    return {
        "total": len(all_records),
        "new_count": len(new_records),
        "ai_used": ai_used,
        "status_note": status_note,
        "html_report": str(html_path),
        "pdf_report": str(pdf_path),
        "email_sent": email_sent,
        "email_status": email_status,
        "last_run": catalog.get("last_run"),
    }
