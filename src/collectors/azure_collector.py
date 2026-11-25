"""Azure collector: combines live Azure Retail Prices API + Azure Updates RSS.

Official public sources used (no Azure account or login required):
1. Azure Retail Prices API (https://prices.azure.com/api/retail/prices):
   Queries live Microsoft pricing meters in BOTH US Commercial (`eastus`) and
   Azure Government (`usgovvirginia`)!
2. Azure Updates RSS:
   https://www.microsoft.com/releasecommunications/api/v2/azure/rss
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Dict, List

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

AZURE_PRICES_API = "https://prices.azure.com/api/retail/prices"
AZURE_UPDATES_RSS = "https://www.microsoft.com/releasecommunications/api/v2/azure/rss"
AZURE_PRICING_URL = "https://azure.microsoft.com/en-us/pricing/details/cognitive-services/openai-service/"


def _extract_model_label(meter_name: str) -> str:
    """Clean up an Azure billing meter name into a readable LLM model name."""
    cleaned = meter_name
    for suffix in (
        "Input",
        "Output",
        "Cached",
        "Inp",
        "Outp",
        "Tokens",
        "Regional",
        "Global",
        "Data Zone",
        "Batch",
        "Standard",
        "Glbl",
        "Regnl",
        "DZone",
        "Text",
    ):
        cleaned = re.sub(rf"\b{suffix}\b", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" -/|,")
    return cleaned or meter_name


def _format_price_per_1m(unit_price: float, unit_of_measure: str) -> str:
    """Normalize Azure prices (often per 1K or 1M tokens) into $/1M tokens."""
    uom = (unit_of_measure or "").lower()
    if "1k" in uom or "1,000" in uom:
        per_m = unit_price * 1000.0
    elif "100k" in uom:
        per_m = unit_price * 10.0
    else:
        per_m = unit_price
    if per_m < 0.01:
        return f"${per_m:.4f}/1M"
    return f"${per_m:.2f}/1M"


def _fetch_azure_live_prices(session) -> Dict[str, dict]:
    """Pull live Azure OpenAI / Foundry token prices for US Commercial and US Gov."""
    model_prices: Dict[str, dict] = defaultdict(
        lambda: {
            "name": "",
            "us_in": None,
            "us_out": None,
            "gov_in": None,
            "gov_out": None,
            "has_gov": False,
        }
    )

    queries = [
        ("us", "serviceName eq 'Foundry Models' and armRegionName eq 'eastus' and priceType eq 'Consumption'"),
        ("gov", "serviceName eq 'Foundry Models' and armRegionName eq 'usgovvirginia' and priceType eq 'Consumption'"),
        ("us", "serviceName eq 'Cognitive Services' and armRegionName eq 'eastus' and contains(productName, 'OpenAI') and priceType eq 'Consumption'"),
        ("gov", "serviceName eq 'Cognitive Services' and armRegionName eq 'usgovvirginia' and contains(productName, 'OpenAI') and priceType eq 'Consumption'"),
    ]

    for region_kind, odata_filter in queries:
        try:
            resp = session.get(
                AZURE_PRICES_API,
                params={"$filter": odata_filter},
                timeout=REQUEST_TIMEOUT,
            )
            if resp.status_code != 200:
                continue
            items = resp.json().get("Items", [])
        except Exception:
            continue

        for item in items:
            meter = item.get("meterName", "")
            uom = item.get("unitOfMeasure", "")
            price = item.get("retailPrice")
            if not meter or price is None or price <= 0:
                continue
            # Focus on token-based LLM meters (skip PTU hourly reservations & audio/image per-sec)
            if "token" not in meter.lower() and "1k" not in uom.lower() and "1m" not in uom.lower():
                continue
            if "batch" in meter.lower() or "cached" in meter.lower() or "fine" in meter.lower():
                continue
            if not is_llm_related(meter):
                continue

            label = _extract_model_label(meter)
            key = make_slug(label)
            if not key:
                continue

            entry = model_prices[key]
            entry["name"] = entry["name"] or label
            formatted = _format_price_per_1m(float(price), uom)

            is_input = any(tok in meter.lower() for tok in ("input", "inp", "prompt"))
            is_output = any(tok in meter.lower() for tok in ("output", "outp", "completion"))

            if region_kind == "gov":
                entry["has_gov"] = True
                if is_input and not entry["gov_in"]:
                    entry["gov_in"] = formatted
                elif is_output and not entry["gov_out"]:
                    entry["gov_out"] = formatted
            else:
                if is_input and not entry["us_in"]:
                    entry["us_in"] = formatted
                elif is_output and not entry["us_out"]:
                    entry["us_out"] = formatted

    return model_prices


def _format_pair(in_price: str | None, out_price: str | None, fallback: str) -> str:
    parts = []
    if in_price:
        parts.append(f"{in_price} in")
    if out_price:
        parts.append(f"{out_price} out")
    return " · ".join(parts) if parts else fallback


def collect_azure_models(lookback_days: int = 7, max_items: int = 12) -> List[LLMRecord]:
    """Fetch recent Azure AI Foundry / OpenAI model releases + live US/US Gov pricing."""
    session = create_session()
    records: List[LLMRecord] = []
    seen_ids: set[str] = set()

    # 1. Fetch live US Commercial + US Gov pricing from Microsoft's public Retail Prices API
    live_prices = _fetch_azure_live_prices(session)

    # 2. Fetch recent Azure Updates RSS announcements
    recent_rss: List[LLMRecord] = []
    fallback_rss: List[LLMRecord] = []
    try:
        resp = session.get(AZURE_UPDATES_RSS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        parsed = feedparser.parse(resp.content)
        for entry in parsed.entries:
            title = strip_html(entry.get("title", ""))
            summary = strip_html(entry.get("summary", "") or entry.get("description", ""))
            combined = f"{title} {summary}".lower()
            if not any(
                k in combined for k in ("openai", "foundry", "azure ai", "model", "llm")
            ):
                continue
            if not is_llm_related(combined):
                continue

            entry_date = parse_entry_date(entry)
            rec_id = f"azure::{make_slug(title)}"
            if rec_id in seen_ids:
                continue

            gov_mentioned = any(
                term in combined
                for term in ("azure government", "us gov", "usgov", "fedramp", "il5", "dod")
            )

            # Try matching this announcement against our live Azure Retail Prices API lookup
            matched_price = None
            for slug_key, pdata in live_prices.items():
                if slug_key and slug_key in make_slug(title):
                    matched_price = pdata
                    break

            us_price_str = (
                _format_pair(matched_price["us_in"], matched_price["us_out"], "Pay-per-token (Azure Foundry)")
                if matched_price
                else "Pay-per-token (see Azure Foundry Pricing)"
            )
            gov_available = (
                "Yes (Live US Gov Meter)"
                if (matched_price and matched_price["has_gov"])
                else ("Yes (Mentioned)" if gov_mentioned else "Check Azure Gov Catalog")
            )
            gov_price_str = (
                _format_pair(matched_price["gov_in"], matched_price["gov_out"], "Azure Gov rate available")
                if (matched_price and matched_price["has_gov"])
                else "Check Azure Gov pricing (usgovvirginia / usgovarizona)"
            )

            record = LLMRecord(
                id=rec_id,
                provider="Azure",
                service="Azure AI Foundry / OpenAI",
                model_name=title,
                vendor=infer_vendor(f"{title} {summary}"),
                release_date=entry_date.isoformat() if entry_date else "",
                summary=shorten(summary or title),
                us_commercial_available="Yes (US Regions)",
                us_gov_available=gov_available,
                us_gov_notes=(
                    "Active billing meter confirmed in Azure Government (usgovvirginia)."
                    if (matched_price and matched_price["has_gov"])
                    else "Azure Government (US Gov Virginia / Arizona) supports vetted models with FedRAMP High & DoD IL4/IL5 compliance."
                ),
                us_commercial_pricing=us_price_str,
                us_gov_pricing=gov_price_str,
                pros=[
                    "Deep Microsoft Entra ID, RBAC, Private Endpoints, and MACC enterprise billing.",
                    "Official Azure Retail Prices API exposes transparent US & Azure Gov token rates.",
                ],
                cons=[
                    "Azure Government model availability and API versions lag commercial US regions.",
                    "Global Standard routing is restricted in US Gov compliance boundaries.",
                ],
                source_url=entry.get("link") or AZURE_PRICING_URL,
                source_type="rss:Azure Updates",
            )

            if is_within_lookback(entry_date, lookback_days):
                recent_rss.append(record)
                seen_ids.add(rec_id)
            elif len(fallback_rss) < 4:
                fallback_rss.append(record)
    except Exception as exc:
        print(f"  [Azure] Could not fetch Azure Updates RSS: {exc}")

    records.extend(recent_rss if recent_rss else fallback_rss)

    # 3. Also surface up to 5 verified live US Gov / US Commercial priced models directly from Azure API
    gov_first = sorted(
        live_prices.items(),
        key=lambda kv: (kv[1]["has_gov"], bool(kv[1]["us_in"] and kv[1]["us_out"]), kv[1]["name"]),
        reverse=True,
    )
    added_api = 0
    for slug_key, pdata in gov_first:
        if added_api >= 5 or len(records) >= max_items:
            break
        rec_id = f"azure::api-{slug_key}"
        if rec_id in seen_ids:
            continue
        seen_ids.add(rec_id)
        us_price = _format_pair(pdata["us_in"], pdata["us_out"], "See Azure Pricing")
        gov_price = (
            _format_pair(pdata["gov_in"], pdata["gov_out"], "Live US Gov meter active")
            if pdata["has_gov"]
            else "Not currently listed in usgovvirginia API"
        )
        records.append(
            LLMRecord(
                id=rec_id,
                provider="Azure",
                service="Azure AI Foundry / OpenAI (Live Price Catalog)",
                model_name=pdata["name"],
                vendor=infer_vendor(pdata["name"]),
                release_date="",
                summary=(
                    f"Live billing meter detected via Microsoft's public Azure Retail Prices API "
                    f"({'East US + US Gov Virginia' if pdata['has_gov'] else 'East US Commercial'})."
                ),
                us_commercial_available="Yes (East US)",
                us_gov_available="Yes (US Gov Virginia)" if pdata["has_gov"] else "Commercial Only (So Far)",
                us_gov_notes=(
                    "Verified active consumption meter in Azure Government (usgovvirginia)."
                    if pdata["has_gov"]
                    else "Active in East US; no consumption meter returned for usgovvirginia."
                ),
                us_commercial_pricing=us_price,
                us_gov_pricing=gov_price,
                pros=[
                    "Pricing verified directly against Microsoft's live Azure Retail Prices API.",
                    "Supports enterprise Azure security, Private Link, and Batch API (~50% discount).",
                ],
                cons=[
                    "Provisioned Throughput (PTU) requires hourly commitment for strict latency SLAs.",
                    "Model lifecycle retirements require periodic version upgrades.",
                ],
                source_url=AZURE_PRICING_URL,
                source_type="api:prices.azure.com",
            )
        )
        added_api += 1

    return records[:max_items]
