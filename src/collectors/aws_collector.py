"""AWS collector: tracks newly added LLMs in Amazon Bedrock & AWS GovCloud (US).

Official public sources used (no AWS account or credentials required):
1. Amazon Bedrock User Guide RSS:
   https://docs.aws.amazon.com/bedrock/latest/userguide/bedrock-ug.rss
2. AWS What's New RSS (filtered for Amazon Bedrock & foundation models):
   https://aws.amazon.com/about-aws/whats-new/recent/feed/
"""

from __future__ import annotations

from typing import List

import feedparser

from src.collectors.common import (
    REQUEST_TIMEOUT,
    create_session,
    infer_vendor,
    is_llm_related,
    is_within_lookback,
    make_slug,
    parse_entry_date,
    shorten,
    strip_html,
)
from src.models import LLMRecord

AWS_FEEDS = [
    ("AWS What's New", "https://aws.amazon.com/about-aws/whats-new/recent/feed/"),
    ("Amazon Bedrock Docs", "https://docs.aws.amazon.com/bedrock/latest/userguide/bedrock-ug.rss"),
]
AWS_PRICING_URL = "https://aws.amazon.com/bedrock/pricing/"


def _is_bedrock_model_update(title: str, summary: str, feed_name: str) -> bool:
    combined = f"{title} {summary}".lower()
    if feed_name == "AWS What's New" and "bedrock" not in combined:
        return False
    return is_llm_related(combined)


def _build_record(entry: dict, feed_name: str) -> LLMRecord:
    title = strip_html(entry.get("title", "Amazon Bedrock Update"))
    summary = strip_html(entry.get("summary", "") or entry.get("description", ""))
    entry_date = parse_entry_date(entry)
    link = entry.get("link") or AWS_PRICING_URL
    combined = f"{title} {summary}".lower()

    gov_mentioned = any(
        term in combined for term in ("govcloud", "us-gov", "fedramp", "dod", "il4", "il5")
    )

    us_gov_available = "Yes (Mentioned)" if gov_mentioned else "Check GovCloud Matrix"
    us_gov_notes = (
        "Announcement references AWS GovCloud (US) or federal compliance."
        if gov_mentioned
        else "AWS GovCloud (US-West / US-East) typically rolls out select models after commercial US regions."
    )

    pros = [
        "Serverless On-Demand API on Amazon Bedrock with AWS IAM & PrivateLink security.",
        "Supports Batch Inference (~50% discount on eligible models) and Bedrock Guardrails.",
    ]
    cons = [
        "AWS GovCloud (US) model parity often trails commercial US regions (us-east-1 / us-west-2).",
        "Fine-tuned models generally require Provisioned Throughput commitments.",
    ]

    return LLMRecord(
        id=f"aws::{make_slug(title)}",
        provider="AWS",
        service="Amazon Bedrock",
        model_name=title,
        vendor=infer_vendor(f"{title} {summary}"),
        release_date=entry_date.isoformat() if entry_date else "",
        summary=shorten(summary or title),
        us_commercial_available="Yes (US Regions)",
        us_gov_available=us_gov_available,
        us_gov_notes=us_gov_notes,
        us_commercial_pricing="Pay-per-token (see Bedrock Pricing)",
        us_gov_pricing="GovCloud regional rate (often slight premium over US commercial)",
        pros=pros,
        cons=cons,
        source_url=link,
        source_type=f"rss:{feed_name}",
    )


def collect_aws_models(lookback_days: int = 7, max_items: int = 10) -> List[LLMRecord]:
    """Fetch recent Amazon Bedrock LLM announcements from official AWS RSS feeds."""
    session = create_session()
    recent_records: List[LLMRecord] = []
    fallback_records: List[LLMRecord] = []
    seen_ids: set[str] = set()

    for feed_name, url in AWS_FEEDS:
        try:
            resp = session.get(url, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            parsed = feedparser.parse(resp.content)
        except Exception as exc:
            print(f"  [AWS] Could not fetch {feed_name}: {exc}")
            continue

        for entry in parsed.entries:
            title = strip_html(entry.get("title", ""))
            summary = strip_html(entry.get("summary", "") or entry.get("description", ""))
            if not _is_bedrock_model_update(title, summary, feed_name):
                continue

            record = _build_record(entry, feed_name)
            if record.id in seen_ids:
                continue
            seen_ids.add(record.id)

            entry_date = parse_entry_date(entry)
            if is_within_lookback(entry_date, lookback_days):
                recent_records.append(record)
            elif len(fallback_records) < 5:
                fallback_records.append(record)

    # If the last 7 days had zero AWS model releases, return up to 5 latest announcements
    # so you still see the most recent Bedrock model additions.
    selected = recent_records if recent_records else fallback_records
    return selected[:max_items]
