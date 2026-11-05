import json
from datetime import datetime, timezone
from pathlib import Path

from src.models import SignalMessage
from src.outbox import write_outbox
from src.parser import parse_signal

SELL = """#XAUUSD SELL 4315-4318

TP 4312
TP 4309
TP 4305

SL 4327
"""


def _signal(msg_id: int = 77) -> SignalMessage:
    parsed = parse_signal(SELL)
    assert parsed is not None
    return SignalMessage(
        group_name="profit_kings",
        group_id=-1002984909577,
        group_title="profit____kings",
        telegram_msg_id=msg_id,
        received_at=datetime(2026, 11, 3, 8, 15, tzinfo=timezone.utc),
        parsed=parsed,
    )


def test_outbox_hands_off_group_identity_and_levels(tmp_path: Path):
    path = write_outbox(tmp_path, _signal())
    assert path.name == "-1002984909577_77.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["group"] == {
        "name": "profit_kings",
        "id": -1002984909577,
        "title": "profit____kings",
    }
    assert payload["side"] == "SELL"
    assert payload["entry"] == 4315
    assert payload["sl"] == 4327
    assert payload["tps"] == [4312, 4309, 4305]
    assert payload["received_at"].startswith("2026-11-03T08:15")
    assert "month_seq" not in payload


def test_outbox_leaves_no_temp_file(tmp_path: Path):
    write_outbox(tmp_path, _signal())
    assert [p.name for p in tmp_path.iterdir()] == ["-1002984909577_77.json"]


def test_same_message_overwrites_instead_of_duplicating(tmp_path: Path):
    write_outbox(tmp_path, _signal())
    write_outbox(tmp_path, _signal())
    assert len(list(tmp_path.glob("*.json"))) == 1
