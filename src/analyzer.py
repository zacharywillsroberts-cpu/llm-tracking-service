"""Optional Gemini API analyzer that enriches collected models with Pros, Cons,
and clearer US / US Gov pricing notes.

How it works:
- Reads GEMINI_API_KEY from your local `.env` file (which is ignored by Git).
- If the key is present, sends collected release items in one compact batch to
  the Gemini API (free tier supported) and gets structured JSON back.
- If no key is set yet, the app skips AI enrichment cleanly and uses the direct
  official feed + Azure Retail Prices API data instead.
"""

from __future__ import annotations

import json
import os
import time
from typing import List, Tuple

from src.models import LLMRecord

DEFAULT_GEMINI_MODEL = "gemini-3.8-flash"
FALLBACK_GEMINI_MODELS = (
    "gemini-3.8-flash",
    "gemini-3.8-flash-lite",
    "gemini-3.5-flash",
    "gemini-3.0-flash",
)


def is_ai_configured() -> bool:
    return bool(os.getenv("GEMINI_API_KEY", "").strip())


def _build_prompt(records: List[LLMRecord]) -> str:
    payload = [
        {
            "id": r.id,
            "provider": r.provider,
            "service": r.service,
            "raw_title": r.model_name,
            "vendor": r.vendor,
            "release_date": r.release_date,
            "raw_summary": r.summary,
            "detected_us_pricing": r.us_commercial_pricing,
            "detected_us_gov_pricing": r.us_gov_pricing,
            "detected_us_gov_available": r.us_gov_available,
            "source_url": r.source_url,
        }
        for r in records
    ]

    return (
        "You are a cloud AI solutions architect helping a team track newly added LLMs "
        "across AWS Bedrock, Azure AI Foundry / OpenAI, and Google Cloud Vertex AI.\n\n"
        "For each item in the JSON array below, return a JSON object with a single key "
        '`"items"` containing an array of enriched objects with these exact keys:\n'
        "- id (exact matching string from input)\n"
        "- model_name (concise, clean model or release title, max 85 chars)\n"
        "- vendor (model maker such as Anthropic, OpenAI, Google, Meta, Amazon, Mistral AI, etc.)\n"
        "- summary (1-2 clear plain-English sentences explaining what is new and why it matters)\n"
        "- us_commercial_available (short status like 'Yes (US Regions)' or 'Preview (US)')\n"
        "- us_gov_available (short status like 'Yes (Azure Gov)', 'Yes (GovCloud US)', 'Via Assured Workloads', 'Pending / Commercial Only', or 'Check Gov Portal')\n"
        "- us_gov_notes (1 short sentence on US Gov / FedRAMP availability or regional notes)\n"
        "- us_commercial_pricing (preserve verified $/1M token numbers if present in input; otherwise give known approximate US $/1M input & output token price or 'See official pricing page' if unknown — never invent exact numbers if uncertain)\n"
        "- us_gov_pricing (preserve verified US Gov meter numbers if present; otherwise explain US Gov pricing expectations clearly)\n"
        "- pros (array of 3 concise, specific strengths)\n"
        "- cons (array of 3 concise, specific trade-offs or limitations)\n\n"
        "Input items:\n"
        f"{json.dumps(payload, indent=2)}"
    )


def enrich_with_gemini(records: List[LLMRecord]) -> Tuple[List[LLMRecord], bool, str]:
    """Enrich records with Gemini API if GEMINI_API_KEY is configured.

    Returns:
        (records, ai_used, status_message)
    """
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return (
            records,
            False,
            "Running in Direct Feed Mode (no GEMINI_API_KEY in .env yet). "
            "Add a free Gemini API key anytime to unlock AI-written Pros/Cons.",
        )

    if not records:
        return records, True, "Gemini API ready, but no records needed enrichment."

    preferred = os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL).strip() or DEFAULT_GEMINI_MODEL
    candidates = [preferred] + [m for m in FALLBACK_GEMINI_MODELS if m != preferred]

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        prompt = _build_prompt(records[:20])

        response = None
        used_model = preferred
        last_error: Exception | None = None

        for candidate in candidates:
            for attempt in range(2):
                try:
                    response = client.models.generate_content(
                        model=candidate,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            temperature=0.2,
                        ),
                    )
                    used_model = candidate
                    break
                except Exception as exc:
                    last_error = exc
                    err_text = str(exc)
                    # Transient 503/429 high demand: wait briefly once before retrying or falling back
                    if ("503" in err_text or "429" in err_text) and attempt == 0:
                        time.sleep(2)
                        continue
                    break
            if response is not None:
                break

        if response is None:
            raise last_error or RuntimeError("No Gemini model responded.")

        raw_text = (response.text or "").strip()
        parsed = json.loads(raw_text)
        enriched_items = parsed.get("items", []) if isinstance(parsed, dict) else parsed
        by_id = {
            item["id"]: item
            for item in enriched_items
            if isinstance(item, dict) and item.get("id")
        }

        updated_count = 0
        for rec in records:
            info = by_id.get(rec.id)
            if not info:
                continue
            rec.model_name = str(info.get("model_name") or rec.model_name)
            rec.vendor = str(info.get("vendor") or rec.vendor)
            rec.summary = str(info.get("summary") or rec.summary)
            rec.us_commercial_available = str(
                info.get("us_commercial_available") or rec.us_commercial_available
            )
            rec.us_gov_available = str(info.get("us_gov_available") or rec.us_gov_available)
            rec.us_gov_notes = str(info.get("us_gov_notes") or rec.us_gov_notes)
            rec.us_commercial_pricing = str(
                info.get("us_commercial_pricing") or rec.us_commercial_pricing
            )
            rec.us_gov_pricing = str(info.get("us_gov_pricing") or rec.us_gov_pricing)
            if isinstance(info.get("pros"), list) and info["pros"]:
                rec.pros = [str(p) for p in info["pros"][:4]]
            if isinstance(info.get("cons"), list) and info["cons"]:
                rec.cons = [str(c) for c in info["cons"][:4]]
            rec.ai_enriched = True
            updated_count += 1

        return (
            records,
            True,
            f"Enriched {updated_count} model(s) with Gemini ({used_model}).",
        )
    except Exception as exc:
        return (
            records,
            False,
            f"Gemini API enrichment skipped due to error ({exc}). Using direct official feed data.",
        )
