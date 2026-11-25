"""Google Cloud collector: tracks newly added LLMs in Vertex AI & Assured Workloads.

Official public sources used (no GCP account or credentials required):
1. Vertex AI Generative AI Release Notes RSS:
   https://cloud.google.com/feeds/vertex-ai-generative-ai-release-notes.xml
2. Vertex AI General Release Notes RSS:
   https://cloud.google.com/feeds/vertex-ai-release-notes.xml
"""

from __future__ import annotations

import re
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

GOOGLE_FEEDS = [
    (
        "Vertex AI Release Notes",
        "https://cloud.google.com/feeds/vertex-ai-release-notes.xml",
    ),
]
GOOGLE_PRICING_URL = "https://cloud.google.com/vertex-ai/generative-ai/pricing"
_DATE_TITLE_RE = re.compile(
    r"^(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}$",
    re.IGNORECASE,
)


def _extract_headline(title: str, summary: str) -> str:
    """Google Cloud RSS titles are often dates; extract a clean headline from summary if needed."""
    cleaned_title = strip_html(title)
    is_date_only = (
        bool(_DATE_TITLE_RE.match(cleaned_title))
        or cleaned_title.replace("-", "").replace(" ", "").isdigit()
    )
    if len(cleaned_title) >= 18 and not is_date_only:
        return cleaned_title
    # Split on sentence boundary (period followed by space or end) so version numbers like 3.2 stay intact
    first_sentence = re.split(r"\.(?:\s|$)", summary)[0].strip() if summary else cleaned_title
    first_sentence = re.sub(r"^(Feature|Announcement|Changed|Deprecated)\s+", "", first_sentence, flags=re.IGNORECASE)
    return shorten(first_sentence or cleaned_title, 110)


def collect_google_models(lookback_days: int = 7, max_items: int = 10) -> List[LLMRecord]:
    """Fetch recent Google Cloud Vertex AI LLM announcements from official RSS feeds."""
    session = create_session()
    recent_records: List[LLMRecord] = []
    fallback_records: List[LLMRecord] = []
    seen_ids: set[str] = set()

    for feed_name, url in GOOGLE_FEEDS:
        try:
            resp = session.get(url, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            parsed = feedparser.parse(resp.content)
        except Exception as exc:
            print(f"  [Google Cloud] Could not fetch {feed_name}: {exc}")
            continue

        for entry in parsed.entries:
            raw_title = entry.get("title", "")
            summary = strip_html(entry.get("summary", "") or entry.get("description", ""))
            headline = _extract_headline(raw_title, summary)
            combined = f"{headline} {summary}".lower()

            if not is_llm_related(combined):
                continue

            rec_id = f"google::{make_slug(headline)}"
            if rec_id in seen_ids:
                continue
            seen_ids.add(rec_id)

            entry_date = parse_entry_date(entry)
            gov_mentioned = any(
                term in combined
                for term in ("assured workloads", "fedramp", "il4", "il5", "us gov", "gov")
            )

            record = LLMRecord(
                id=rec_id,
                provider="Google Cloud",
                service="Google Vertex AI / Model Garden",
                model_name=headline,
                vendor=infer_vendor(f"{headline} {summary}"),
                release_date=entry_date.isoformat() if entry_date else "",
                summary=shorten(summary or headline),
                us_commercial_available="Yes (US Regions)",
                us_gov_available=(
                    "Yes (Assured Workloads Mentioned)"
                    if gov_mentioned
                    else "Via Assured Workloads (Check Scope)"
                ),
                us_gov_notes=(
                    "US Gov compliance runs via Google Cloud Assured Workloads (FedRAMP Moderate/High, US data boundary)."
                ),
                us_commercial_pricing="Pay-per-token (see Vertex AI Pricing)",
                us_gov_pricing="Standard Vertex AI rates (+0% free tier or 5-20% Premium Assured Workloads tier)",
                pros=[
                    "Unified Model Garden hosting Gemini plus partner models (Claude, Llama, Mistral).",
                    "Strong long-context pricing, context caching, and native BigQuery / Search grounding.",
                ],
                cons=[
                    "US Gov compliance requires Assured Workloads setup and verifying each model's FedRAMP scope.",
                    "Global endpoints must be restricted to US-only regional endpoints for strict data residency.",
                ],
                source_url=entry.get("link") or GOOGLE_PRICING_URL,
                source_type=f"rss:{feed_name}",
            )

            if is_within_lookback(entry_date, lookback_days):
                recent_records.append(record)
            elif len(fallback_records) < 5:
                fallback_records.append(record)

    selected = recent_records if recent_records else fallback_records
    return selected[:max_items]
