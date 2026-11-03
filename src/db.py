from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from threading import Lock
from zoneinfo import ZoneInfo

from .models import CatalogRecord, ParsedSignal
from .timeutil import as_utc, month_key


class CatalogDB:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = Lock()
        self._init()

    def _init(self) -> None:
        with self._lock:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS signals (
                    id TEXT PRIMARY KEY,
                    group_name TEXT NOT NULL,
                    group_id INTEGER NOT NULL,
                    group_title TEXT NOT NULL,
                    month TEXT NOT NULL,
                    month_seq INTEGER NOT NULL,
                    received_at TEXT NOT NULL,
                    telegram_msg_id INTEGER NOT NULL,
                    side TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    entry REAL NOT NULL,
                    zone_low REAL NOT NULL,
                    zone_high REAL NOT NULL,
                    sl REAL NOT NULL,
                    tps TEXT NOT NULL,
                    raw_text TEXT NOT NULL,
                    UNIQUE(group_id, telegram_msg_id)
                )
                """
            )
            self._conn.commit()

    def already_seen(self, group_id: int, telegram_msg_id: int) -> bool:
        with self._lock:
            row = self._conn.execute(
                "SELECT 1 FROM signals WHERE group_id=? AND telegram_msg_id=?",
                (group_id, telegram_msg_id),
            ).fetchone()
        return row is not None

    def insert_signal(
        self,
        *,
        group_name: str,
        group_id: int,
        group_title: str,
        received_at: datetime,
        telegram_msg_id: int,
        parsed: ParsedSignal,
        tz: ZoneInfo,
    ) -> CatalogRecord | None:
        month = month_key(received_at, tz)
        received = as_utc(received_at) or received_at
        with self._lock:
            if self._conn.execute(
                "SELECT 1 FROM signals WHERE group_id=? AND telegram_msg_id=?",
                (group_id, telegram_msg_id),
            ).fetchone():
                return None
            row = self._conn.execute(
                "SELECT COALESCE(MAX(month_seq), 0) AS n FROM signals WHERE group_id=? AND month=?",
                (group_id, month),
            ).fetchone()
            seq = int(row["n"]) + 1
            signal_id = f"{group_id}-{month}-{seq:04d}-{telegram_msg_id}"
            self._conn.execute(
                """
                INSERT INTO signals (
                    id, group_name, group_id, group_title, month, month_seq,
                    received_at, telegram_msg_id, side, symbol, entry,
                    zone_low, zone_high, sl, tps, raw_text
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    signal_id,
                    group_name,
                    group_id,
                    group_title,
                    month,
                    seq,
                    received.isoformat(),
                    telegram_msg_id,
                    parsed.side.value,
                    parsed.symbol,
                    parsed.entry or parsed.zone_low,
                    parsed.zone_low,
                    parsed.zone_high,
                    parsed.sl,
                    json.dumps(list(parsed.tps)),
                    parsed.raw_text,
                ),
            )
            self._conn.commit()
        return CatalogRecord(
            id=signal_id,
            group_name=group_name,
            group_id=group_id,
            group_title=group_title,
            month=month,
            month_seq=seq,
            received_at=received,
            telegram_msg_id=telegram_msg_id,
            side=parsed.side.value,
            symbol=parsed.symbol,
            entry=parsed.entry or parsed.zone_low,
            zone_low=parsed.zone_low,
            zone_high=parsed.zone_high,
            sl=parsed.sl,
            tps=parsed.tps,
            raw_text=parsed.raw_text,
        )

    def for_group_month(self, group_name: str, month: str) -> list[CatalogRecord]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM signals WHERE group_name=? AND month=? ORDER BY month_seq",
                (group_name, month),
            ).fetchall()
        return [_row_to_record(r) for r in rows]


def _row_to_record(row: sqlite3.Row) -> CatalogRecord:
    tps = tuple(json.loads(row["tps"]))
    return CatalogRecord(
        id=row["id"],
        group_name=row["group_name"],
        group_id=int(row["group_id"]),
        group_title=row["group_title"],
        month=row["month"],
        month_seq=int(row["month_seq"]),
        received_at=datetime.fromisoformat(row["received_at"]),
        telegram_msg_id=int(row["telegram_msg_id"]),
        side=row["side"],
        symbol=row["symbol"],
        entry=float(row["entry"]),
        zone_low=float(row["zone_low"]),
        zone_high=float(row["zone_high"]),
        sl=float(row["sl"]),
        tps=tps,
        raw_text=row["raw_text"],
    )
