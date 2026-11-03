from __future__ import annotations

import json
from pathlib import Path

from .models import CatalogRecord


def write_outbox(outbox_dir: Path, rec: CatalogRecord) -> Path:
    """One JSON file per signal — consumed later by the chart executor."""
    outbox_dir.mkdir(parents=True, exist_ok=True)
    path = outbox_dir / f"{rec.id}.json"
    payload = {
        "id": rec.id,
        "month": rec.month,
        "month_seq": rec.month_seq,
        "group": {
            "name": rec.group_name,
            "id": rec.group_id,
            "title": rec.group_title,
        },
        "received_at": rec.received_at.isoformat(),
        "telegram_msg_id": rec.telegram_msg_id,
        "side": rec.side,
        "symbol": rec.symbol,
        "entry": rec.entry,
        "zone_low": rec.zone_low,
        "zone_high": rec.zone_high,
        "sl": rec.sl,
        "tps": list(rec.tps),
        "raw_text": rec.raw_text,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
