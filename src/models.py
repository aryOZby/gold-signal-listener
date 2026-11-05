from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


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


@dataclass(frozen=True)
class SignalMessage:
    group_name: str
    group_id: int
    group_title: str
    telegram_msg_id: int
    received_at: datetime
    parsed: ParsedSignal

    @property
    def id(self) -> str:
        return f"{self.group_id}_{self.telegram_msg_id}"
