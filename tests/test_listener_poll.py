import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest

import src.listener as listener_mod
from src.listener import SeenMessages, SignalListener
from src.models import GroupConfig

PIPS = -1001569906975
SIGNAL = "#XAUUSD SELL 3874-3877\nTP 3871\nTP 3868\nTP 3864\nSL 3987"


def _msg(msg_id: int, text: str):
    return SimpleNamespace(id=msg_id, raw_text=text, date=datetime(2026, 11, 16, 1, 41, tzinfo=timezone.utc))


def test_seen_messages_skips_old_and_duplicates():
    seen = SeenMessages(keep=3)
    seen.set_baseline(PIPS, 100)
    assert not seen.first_time(PIPS, 99)
    assert not seen.first_time(PIPS, 100)
    assert seen.first_time(PIPS, 101)
    assert not seen.first_time(PIPS, 101)
    assert seen.first_time(-1, 5)


class FakeClient:
    def __init__(self, messages):
        self.messages = messages

    async def get_messages(self, entity, limit):
        return list(reversed(self.messages))[:limit]


def test_direct_read_writes_signal_missed_by_live_updates(tmp_path: Path, monkeypatch):
    service = SignalListener.__new__(SignalListener)
    service.cfg = SimpleNamespace(outbox_dir=tmp_path, tz=ZoneInfo("Asia/Jerusalem"))
    service.seen = SeenMessages()
    service.client = FakeClient([_msg(10, "old"), _msg(11, "GOLD SELL 3874"), _msg(12, SIGNAL)])
    service._entities = {PIPS: (GroupConfig(name="technical_pips", chat_id=PIPS, title="Pips"), object())}
    service.seen.set_baseline(PIPS, 10)
    rounds = {"n": 0}

    async def fake_sleep(_seconds):
        rounds["n"] += 1
        if rounds["n"] > 2:
            raise asyncio.CancelledError

    monkeypatch.setattr(listener_mod.asyncio, "sleep", fake_sleep)
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(service._poll_loop())

    files = sorted(p.name for p in tmp_path.glob("*.json"))
    assert files == [f"{PIPS}_12.json"]
    data = json.loads((tmp_path / files[0]).read_text(encoding="utf-8"))
    assert data["side"] == "SELL" and data["sl"] == 3987
    assert not service.seen.first_time(PIPS, 12)
