"""Weekly email delivery for the Cloud LLM Tracking Service.

Sends the styled HTML report as the email body AND attaches the PDF report
using Python's built-in `smtplib` (100% free, zero extra libraries needed).

Required environment variables (stored in `.env` locally or GitHub Secrets):
    EMAIL_TO          - Recipient email address (or comma-separated list, e.g., you@example.com)
    SMTP_USER         - Sender Gmail address (usually your own Gmail address)
    SMTP_APP_PASSWORD - 16-character Google App Password (NOT your regular password!)
"""

from __future__ import annotations

import os
import smtplib
from datetime import date
from email.message import EmailMessage
from pathlib import Path
from typing import Tuple


def is_email_configured() -> bool:
    return bool(
        os.getenv("EMAIL_TO", "").strip()
        and os.getenv("SMTP_USER", "").strip()
        and os.getenv("SMTP_APP_PASSWORD", "").strip()
    )


def send_weekly_email(
    html_path: Path,
    pdf_path: Path,
    total_count: int,
    new_count: int,
) -> Tuple[bool, str]:
    """Send the weekly HTML + PDF report via Gmail SMTP SSL (port 465)."""
    recipient = os.getenv("EMAIL_TO", "").strip()
    smtp_user = os.getenv("SMTP_USER", "").strip()
    smtp_pass = os.getenv("SMTP_APP_PASSWORD", "").strip().replace(" ", "")
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com").strip()
    smtp_port = int(os.getenv("SMTP_PORT", "465"))

    if not (recipient and smtp_user and smtp_pass):
        return (
            False,
            "Email skipped (SMTP_APP_PASSWORD not set yet in .env or GitHub Secrets).",
        )

    today_str = date.today().isoformat()
    subject = f"Weekly Cloud LLM Report ({today_str}) — {new_count} New / {total_count} Tracked"

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = smtp_user
    msg["To"] = recipient

    plain_fallback = (
        f"Your Weekly Cloud LLM Report for {today_str} is ready!\n"
        f"Tracked models: {total_count} | New this run: {new_count}\n\n"
        "Open the HTML version of this email or the attached PDF report for full "
        "US / US Gov pricing, pros, and cons across AWS, Azure, and Google Cloud."
    )
    msg.set_content(plain_fallback)

    if html_path.exists():
        html_body = html_path.read_text(encoding="utf-8")
        msg.add_alternative(html_body, subtype="html")

    if pdf_path.exists():
        pdf_bytes = pdf_path.read_bytes()
        msg.add_attachment(
            pdf_bytes,
            maintype="application",
            subtype="pdf",
            filename=pdf_path.name,
        )

    try:
        with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=30) as server:
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        return True, f"Weekly HTML + PDF report emailed to {recipient}."
    except Exception as exc:
        return False, f"Email failed ({exc})."
