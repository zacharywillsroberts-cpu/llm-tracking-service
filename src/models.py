"""Data models for the Cloud LLM Tracking Service.

Keeping our data shape in one place (a "schema") makes it easy to pass model
records cleanly between collectors, the AI analyzer, storage, reports, and the
web dashboard.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import List


@dataclass
class LLMRecord:
    """Represents one LLM model or release announcement tracked across clouds."""

    id: str
    provider: str  # "AWS", "Azure", or "Google Cloud"
    service: str  # e.g., "Amazon Bedrock", "Azure AI Foundry", "Google Vertex AI"
    model_name: str
    vendor: str = "Unknown"
    release_date: str = ""  # YYYY-MM-DD from the official announcement/feed
    first_seen: str = ""  # YYYY-MM-DD when this tracker first saw it
    last_updated: str = ""  # YYYY-MM-DD when last refreshed
    is_new: bool = False  # True if newly detected in this run or within lookback window
    summary: str = ""
    us_commercial_available: str = "Check Docs"
    us_gov_available: str = "Check Gov Portal"
    us_gov_notes: str = ""
    us_commercial_pricing: str = "See official pricing page"
    us_gov_pricing: str = "See US Gov pricing schedule"
    pros: List[str] = field(default_factory=list)
    cons: List[str] = field(default_factory=list)
    source_url: str = ""
    source_type: str = "official_feed"
    ai_enriched: bool = False

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "LLMRecord":
        valid_keys = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)
