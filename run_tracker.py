"""Main entry point for the Cloud LLM Tracking Service.

Examples:
    # Run a weekly scan (7-day lookback) and generate HTML + PDF reports:
    .venv\\Scripts\\python.exe run_tracker.py

    # Run a broader 30-day scan (great for your very first run):
    .venv\\Scripts\\python.exe run_tracker.py --days 30

    # Launch the local web dashboard at http://localhost:5000:
    .venv\\Scripts\\python.exe run_tracker.py --dashboard
"""

from __future__ import annotations

import argparse

from src.dashboard import start_dashboard
from src.pipeline import run_full_scan


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Track newly added LLMs on AWS, Azure, and Google Cloud (US & US Gov)."
    )
    parser.add_argument(
        "--days",
        type=int,
        default=None,
        help="How many days back to scan release feeds (defaults to LOOKBACK_DAYS in .env or 7).",
    )
    parser.add_argument(
        "--dashboard",
        action="store_true",
        help="Launch the local interactive web dashboard instead of running a one-off CLI scan.",
    )
    parser.add_argument(
        "--send-email",
        action="store_true",
        help="Email the generated HTML + PDF report using the SMTP settings in .env.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Port for the local dashboard (default: 5000).",
    )
    args = parser.parse_args()

    if args.dashboard:
        start_dashboard(port=args.port)
    else:
        run_full_scan(lookback_days=args.days, send_email=args.send_email)


if __name__ == "__main__":
    main()
