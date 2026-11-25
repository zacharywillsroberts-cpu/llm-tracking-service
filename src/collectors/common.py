"""Shared helper utilities used by the AWS, Azure, and Google collectors."""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Optional

import requests
from bs4 import BeautifulSoup

USER_AGENT = "LLM-Tracking-Service/1.0 (Educational Cloud LLM Tracker)"
REQUEST_TIMEOUT = 20

# Keywords that indicate a release note is about an LLM / generative AI model
LLM_KEYWORDS = (
    "llm",
    "language model",
    "foundation model",
    "model garden",
    "claude",
    "gemini",
    "gpt",
    "llama",
    "nova",
    "mistral",
    "mixtral",
    "deepseek",
    "cohere",
    "command r",
    "grok",
    "qwen",
    "phi-",
    "titan",
    "jamba",
    "o1",
    "o3",
    "o4",
    "sonnet",
    "opus",
    "haiku",
    "gemma",
    "nemotron",
    "kimi",
    "minimax",
    "reasoning model",
    "frontier model",
    "generative ai",
    "openai",
)

VENDOR_PATTERNS = [
    ("Anthropic", ("anthropic", "claude", "sonnet", "opus", "haiku")),
    ("OpenAI", ("openai", "gpt-", "gpt ", "chatgpt", "o1", "o3", "o4", "codex")),
    ("Google", ("gemini", "gemma", "imagen", "veo", "palm")),
    ("Meta", ("meta", "llama")),
    ("Amazon", ("amazon nova", "nova ", "titan")),
    ("Mistral AI", ("mistral", "mixtral", "pixtral", "codestral")),
    ("DeepSeek", ("deepseek",)),
    ("Cohere", ("cohere", "command r", "command a", "embed")),
    ("Microsoft", ("phi-", "mai-")),
    ("xAI", ("xai", "grok")),
    ("Alibaba / Qwen", ("qwen",)),
    ("NVIDIA", ("nemotron", "nvidia")),
    ("AI21 Labs", ("ai21", "jamba")),
]


def create_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    return session


def strip_html(raw_html: str) -> str:
    """Convert HTML snippets from RSS feeds into clean single-line text."""
    if not raw_html:
        return ""
    soup = BeautifulSoup(raw_html, "html.parser")
    text = soup.get_text(" ", strip=True)
    return re.sub(r"\s+", " ", text).strip()


def make_slug(text: str) -> str:
    """Turn a model title into a clean, repeatable ID slug."""
    cleaned = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return cleaned[:70]


def infer_vendor(text: str) -> str:
    """Guess the model creator (Anthropic, OpenAI, Google, etc.) from title/summary."""
    lower = text.lower()
    for vendor, needles in VENDOR_PATTERNS:
        if any(needle in lower for needle in needles):
            return vendor
    return "Cloud / Partner"


def is_llm_related(text: str) -> bool:
    """Return True if a release note looks related to LLMs or foundation models."""
    lower = text.lower()
    return any(keyword in lower for keyword in LLM_KEYWORDS)


def parse_entry_date(entry: dict) -> Optional[date]:
    """Parse an RSS/Atom entry date into a Python date object."""
    for key in ("published_parsed", "updated_parsed"):
        parsed = entry.get(key)
        if parsed:
            try:
                return date(parsed.tm_year, parsed.tm_mon, parsed.tm_mday)
            except Exception:
                pass

    for key in ("published", "updated"):
        raw = entry.get(key)
        if not raw:
            continue
        try:
            dt = parsedate_to_datetime(raw)
            return dt.date()
        except Exception:
            pass
        match = re.search(r"(\d{4}-\d{2}-\d{2})", raw)
        if match:
            try:
                return date.fromisoformat(match.group(1))
            except ValueError:
                pass
    return None


def is_within_lookback(entry_date: Optional[date], lookback_days: int) -> bool:
    """Check if an entry date falls within the requested lookback window."""
    if entry_date is None:
        return True
    cutoff = datetime.now(timezone.utc).date() - timedelta(days=lookback_days)
    return entry_date >= cutoff


def shorten(text: str, max_len: int = 280) -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - 3].rstrip() + "..."
