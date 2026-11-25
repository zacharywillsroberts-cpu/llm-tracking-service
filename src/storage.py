"""Local JSON storage for tracking model history across weekly runs.

Why we save a snapshot (`data/catalog.json`):
Each week, the tracker fetches the latest announcements and pricing. By
comparing today's results against the saved snapshot, we know which models are
genuinely NEW since your last run.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

from src.models import LLMRecord

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
CATALOG_PATH = DATA_DIR / "catalog.json"


def load_catalog(path: Path = CATALOG_PATH) -> dict:
    """Load the saved catalog snapshot, or return an empty structure on first run."""
    if not path.exists():
        return {
            "last_run": None,
            "lookback_days": 7,
            "ai_enabled": False,
            "run_history": [],
            "models": {},
        }
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def merge_and_save_catalog(
    incoming: List[LLMRecord],
    lookback_days: int,
    ai_enabled: bool,
    path: Path = CATALOG_PATH,
) -> Tuple[List[LLMRecord], List[LLMRecord], dict]:
    """Merge newly fetched records into the persistent catalog.

    Returns:
        all_records: Full sorted list of tracked models.
        new_records: Models newly added during this run.
        catalog: The saved catalog dictionary.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    catalog = load_catalog(path)
    existing_map: Dict[str, dict] = catalog.get("models", {})
    today_str = date.today().isoformat()
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    new_records: List[LLMRecord] = []

    # Reset the "is_new" flag on previously saved records before merging today's run
    for saved in existing_map.values():
        saved["is_new"] = False

    for record in incoming:
        if record.id not in existing_map:
            record.first_seen = record.first_seen or today_str
            record.last_updated = today_str
            record.is_new = True
            existing_map[record.id] = record.to_dict()
            new_records.append(record)
        else:
            prev = existing_map[record.id]
            record.first_seen = prev.get("first_seen") or today_str
            record.last_updated = today_str
            # Preserve prior AI enrichment if this run didn't re-enrich it
            if prev.get("ai_enriched") and not record.ai_enriched:
                record.pros = prev.get("pros", record.pros)
                record.cons = prev.get("cons", record.cons)
                record.us_commercial_pricing = prev.get(
                    "us_commercial_pricing", record.us_commercial_pricing
                )
                record.us_gov_pricing = prev.get("us_gov_pricing", record.us_gov_pricing)
                record.us_gov_available = prev.get(
                    "us_gov_available", record.us_gov_available
                )
                record.us_gov_notes = prev.get("us_gov_notes", record.us_gov_notes)
                record.ai_enriched = True
            # Mark as new if first seen today
            record.is_new = record.first_seen == today_str
            existing_map[record.id] = record.to_dict()

    all_records = [LLMRecord.from_dict(v) for v in existing_map.values()]
    all_records.sort(
        key=lambda r: (r.is_new, r.release_date or r.first_seen, r.provider, r.model_name),
        reverse=True,
    )

    run_history = catalog.get("run_history", [])
    run_history.insert(
        0,
        {
            "timestamp": now_iso,
            "date": today_str,
            "total_models": len(all_records),
            "new_models": len(new_records),
            "lookback_days": lookback_days,
            "ai_enabled": ai_enabled,
        },
    )
    # Keep the last 52 weekly runs in history
    run_history = run_history[:52]

    updated_catalog = {
        "last_run": now_iso,
        "lookback_days": lookback_days,
        "ai_enabled": ai_enabled,
        "run_history": run_history,
        "models": existing_map,
    }

    with path.open("w", encoding="utf-8") as fh:
        json.dump(updated_catalog, fh, indent=2, ensure_ascii=False)

    return all_records, new_records, updated_catalog
