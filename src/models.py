from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class Side(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


@dataclass(frozen=True)
class ParsedSignal:
    symbol: str
    side: Side
    zone_low: float
    zone_high: float
    tps: tuple[float, ...]
    sl: float
    raw_text: str
    entry: float = 0.0

    @property
    def tp_count(self) -> int:
        return len(self.tps)


@dataclass
class GroupConfig:
    name: str
    chat_id: int
    username: str = ""
    title: str = ""


@dataclass
class CatalogRecord:
    id: str
    group_name: str
    group_id: int
    group_title: str
    month: str
    month_seq: int
    received_at: datetime
    telegram_msg_id: int
    side: str
    symbol: str
    entry: float
    zone_low: float
    zone_high: float
    sl: float
    tps: tuple[float, ...]
    raw_text: str
