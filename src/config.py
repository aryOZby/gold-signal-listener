from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml
from dotenv import load_dotenv

from .models import GroupConfig

ROOT = Path(__file__).resolve().parent.parent


@dataclass
class AppConfig:
    timezone: str
    tz: ZoneInfo
    session_name: str
    groups: list[GroupConfig]
    admin_chat_id: int
    telegram_api_id: int
    telegram_api_hash: str
    telegram_phone: str
    data_dir: Path
    logs_dir: Path
    outbox_dir: Path


def load_config(path: Path | None = None) -> AppConfig:
    load_dotenv(ROOT / ".env")
    cfg_path = path or (ROOT / "config.yaml")
    raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    telegram = raw.get("telegram") or {}
    paths = raw.get("paths") or {}
    groups: list[GroupConfig] = []
    for item in telegram.get("groups") or []:
        name = str(item["name"]).strip()
        username = str(item.get("username") or "").strip().lstrip("@")
        title = str(item.get("title") or "").strip()
        try:
            chat_id = int(item.get("chat_id") or 0)
        except (TypeError, ValueError):
            chat_id = 0
        if not chat_id and not username:
            raise ValueError(f"Group {name} needs chat_id or username")
        groups.append(GroupConfig(name=name, chat_id=chat_id, username=username, title=title))
    if not groups:
        raise ValueError("Configure at least one Telegram group")
    tz_name = str(raw.get("timezone") or "Asia/Jerusalem")
    admin = os.getenv("TELEGRAM_ADMIN_CHAT_ID") or telegram.get("admin_chat_id") or 0
    api_id = os.getenv("TELEGRAM_API_ID")
    return AppConfig(
        timezone=tz_name,
        tz=ZoneInfo(tz_name),
        session_name=str(telegram.get("session_name") or "gold_signal_listener"),
        groups=groups,
        admin_chat_id=int(admin or 0),
        telegram_api_id=int(api_id) if api_id else 0,
        telegram_api_hash=os.getenv("TELEGRAM_API_HASH") or "",
        telegram_phone=os.getenv("TELEGRAM_PHONE") or "",
        data_dir=ROOT / str(paths.get("data_dir") or "data"),
        logs_dir=ROOT / str(paths.get("logs_dir") or "logs"),
        outbox_dir=ROOT / str(paths.get("outbox_dir") or "data/outbox"),
    )


def group_by_chat_id(cfg: AppConfig, chat_id: int) -> GroupConfig | None:
    return next((g for g in cfg.groups if g.chat_id == chat_id), None)


def group_by_username(cfg: AppConfig, username: str | None) -> GroupConfig | None:
    if not username:
        return None
    token = username.strip().lstrip("@").lower()
    return next((g for g in cfg.groups if g.username.lower() == token), None)
