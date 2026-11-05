from __future__ import annotations

import json
import os
from pathlib import Path

from .models import SignalMessage


def write_outbox(outbox_dir: Path, msg: SignalMessage) -> Path:
    """Hand one signal to the chart executor. The listener keeps no copy."""
    outbox_dir.mkdir(parents=True, exist_ok=True)
    path = outbox_dir / f"{msg.id}.json"
    parsed = msg.parsed
    payload = {
        "id": msg.id,
        "group": {
            "name": msg.group_name,
            "id": msg.group_id,
            "title": msg.group_title,
        },
        "received_at": msg.received_at.isoformat(),
        "telegram_msg_id": msg.telegram_msg_id,
        "side": parsed.side.value,
        "symbol": parsed.symbol,
        "entry": parsed.entry or parsed.zone_low,
        "zone_low": parsed.zone_low,
        "zone_high": parsed.zone_high,
        "sl": parsed.sl,
        "tps": list(parsed.tps),
        "raw_text": parsed.raw_text,
    }
    # The executor polls *.json, so it must never see a half-written file.
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)
    return path
