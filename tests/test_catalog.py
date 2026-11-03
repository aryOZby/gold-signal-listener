from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from src.catalog import write_signal
from src.db import CatalogDB
from src.models import ParsedSignal, Side
from src.outbox import write_outbox
from src.parser import parse_signal

SELL = """#XAUUSD SELL 4315-4318

TP 4312
TP 4309
TP 4305

SL 4327
"""

TZ = ZoneInfo("Asia/Jerusalem")


def _parsed() -> ParsedSignal:
    sig = parse_signal(SELL)
    assert sig is not None
    return sig


def test_monthly_seq_resets_per_group(tmp_path: Path):
    db = CatalogDB(tmp_path / "catalog.db")
    parsed = _parsed()
    oct_dt = datetime(2026, 10, 31, 10, 0, tzinfo=timezone.utc)
    nov_dt = datetime(2026, 11, 1, 10, 0, tzinfo=timezone.utc)

    a1 = db.insert_signal(
        group_name="kings",
        group_id=-1001,
        group_title="Profit Kings",
        received_at=oct_dt,
        telegram_msg_id=1,
        parsed=parsed,
        tz=TZ,
    )
    a2 = db.insert_signal(
        group_name="kings",
        group_id=-1001,
        group_title="Profit Kings",
        received_at=oct_dt,
        telegram_msg_id=2,
        parsed=parsed,
        tz=TZ,
    )
    b1 = db.insert_signal(
        group_name="kings",
        group_id=-1001,
        group_title="Profit Kings",
        received_at=nov_dt,
        telegram_msg_id=3,
        parsed=parsed,
        tz=TZ,
    )
    other = db.insert_signal(
        group_name="pips",
        group_id=-1002,
        group_title="Technical Pips",
        received_at=nov_dt,
        telegram_msg_id=3,
        parsed=parsed,
        tz=TZ,
    )
    assert a1 is not None and a1.month_seq == 1 and a1.month == "2026-10"
    assert a2 is not None and a2.month_seq == 2
    assert b1 is not None and b1.month_seq == 1 and b1.month == "2026-11"
    assert other is not None and other.month_seq == 1
    assert other.group_title == "Technical Pips"


def test_duplicate_message_ignored(tmp_path: Path):
    db = CatalogDB(tmp_path / "catalog.db")
    parsed = _parsed()
    now = datetime(2026, 11, 3, 10, 0, tzinfo=timezone.utc)
    first = db.insert_signal(
        group_name="kings",
        group_id=-1001,
        group_title="Profit Kings",
        received_at=now,
        telegram_msg_id=99,
        parsed=parsed,
        tz=TZ,
    )
    again = db.insert_signal(
        group_name="kings",
        group_id=-1001,
        group_title="Profit Kings",
        received_at=now,
        telegram_msg_id=99,
        parsed=parsed,
        tz=TZ,
    )
    assert first is not None
    assert again is None


def test_excel_and_outbox(tmp_path: Path):
    db = CatalogDB(tmp_path / "catalog.db")
    parsed = _parsed()
    rec = db.insert_signal(
        group_name="kings",
        group_id=-1002984909577,
        group_title="Profit Kings Original",
        received_at=datetime(2026, 11, 3, 8, 15, tzinfo=timezone.utc),
        telegram_msg_id=77,
        parsed=parsed,
        tz=TZ,
    )
    assert rec is not None
    xlsx = write_signal(tmp_path / "reports", rec, TZ)
    out = write_outbox(tmp_path / "outbox", rec)
    assert xlsx.exists()
    assert "kings" in str(xlsx)
    assert rec.month in xlsx.name
    payload = out.read_text(encoding="utf-8")
    assert '"title": "Profit Kings Original"' in payload
    assert '"id": -1002984909577' in payload
    assert '"month_seq": 1' in payload
    assert parsed.side is Side.SELL
