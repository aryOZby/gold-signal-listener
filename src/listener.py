from __future__ import annotations

import logging
from datetime import timezone
from pathlib import Path

from telethon import TelegramClient, events
from telethon.tl.custom.message import Message
from telethon.utils import get_peer_id

from .catalog import write_signal
from .config import AppConfig, group_by_chat_id, group_by_username
from .db import CatalogDB
from .models import CatalogRecord, GroupConfig
from .outbox import write_outbox
from .parser import parse_signal
from .timeutil import display_date, display_time, utcnow

_LOG = logging.getLogger(__name__)


class SignalListener:
    def __init__(self, cfg: AppConfig, db: CatalogDB):
        self.cfg = cfg
        self.db = db
        cfg.data_dir.mkdir(parents=True, exist_ok=True)
        session = Path(cfg.data_dir) / cfg.session_name
        self.client = TelegramClient(str(session), cfg.telegram_api_id, cfg.telegram_api_hash)

    async def start(self) -> None:
        await self.client.start(phone=self.cfg.telegram_phone or None)
        me = await self.client.get_me()
        _LOG.info("Telegram signed in as %s id=%s", getattr(me, "username", None) or me.id, me.id)
        await self._subscribe_groups()
        targets = [g.chat_id for g in self.cfg.groups if g.chat_id]
        if targets:
            self.client.add_event_handler(self._on_message, events.NewMessage(chats=targets))
            _LOG.info("Listening only to %s", describe_groups(self.cfg.groups))
        else:
            self.client.add_event_handler(self._on_message, events.NewMessage())
            _LOG.warning("No group chat_id resolved — listening to all chats")

    async def _subscribe_groups(self) -> None:
        for group in self.cfg.groups:
            target = group.chat_id or group.username
            if not target:
                _LOG.warning("Missing chat_id/username for group %s", group.name)
                continue
            try:
                entity = await self.client.get_entity(target)
                group.chat_id = int(get_peer_id(entity))
                live = getattr(entity, "title", None) or getattr(entity, "username", None)
                if live:
                    group.title = str(live)
                await self.client.get_messages(entity, limit=1)
                _LOG.info(
                    "Subscribed %s | title=%s | chat_id=%s",
                    group.name,
                    group.title,
                    group.chat_id,
                )
            except Exception:
                _LOG.exception(
                    "Failed to subscribe to %s (%s) — the account must already be a member",
                    group.name,
                    target,
                )

    async def run_until_disconnected(self) -> None:
        await self.client.run_until_disconnected()

    async def _on_message(self, event: events.NewMessage.Event) -> None:
        msg: Message = event.message
        chat_id = event.chat_id
        if chat_id is None:
            return
        text = msg.raw_text or ""
        group = group_by_chat_id(self.cfg, int(chat_id))
        if group is None:
            group = await self._match_by_username(event, int(chat_id))
        if group is None:
            if text.strip():
                _LOG.info("Ignored chat_id=%s. Preview: %s", chat_id, text[:80])
            return
        parsed = parse_signal(text)
        if parsed is None:
            if text.strip():
                _LOG.info(
                    "Not a signal from %s (%s / %s). Preview: %s",
                    group.name,
                    group.title or "?",
                    chat_id,
                    text[:120],
                )
            return
        received = msg.date
        if received is None:
            received = utcnow()
        elif received.tzinfo is None:
            received = received.replace(tzinfo=timezone.utc)
        title = await self._chat_title(event, group)
        rec = self.db.insert_signal(
            group_name=group.name,
            group_id=int(chat_id),
            group_title=title,
            received_at=received,
            telegram_msg_id=int(msg.id),
            parsed=parsed,
            tz=self.cfg.tz,
        )
        if rec is None:
            _LOG.info("Duplicate skipped %s msg_id=%s", group.name, msg.id)
            return
        write_signal(self.cfg.reports_dir, rec, self.cfg.tz)
        write_outbox(self.cfg.outbox_dir, rec)
        _LOG.info("%s", format_record(rec, self.cfg.tz))

    async def _chat_title(self, event: events.NewMessage.Event, group: GroupConfig) -> str:
        chat = event.chat
        if chat is None:
            try:
                chat = await event.get_chat()
            except Exception:
                return group.title or group.name
        live = getattr(chat, "title", None) or getattr(chat, "username", None)
        if live:
            group.title = str(live)
        return group.title or group.name

    async def _match_by_username(self, event: events.NewMessage.Event, chat_id: int) -> GroupConfig | None:
        chat = event.chat
        username = getattr(chat, "username", None) if chat is not None else None
        if not username:
            try:
                chat = await event.get_chat()
                username = getattr(chat, "username", None)
            except Exception:
                return None
        group = group_by_username(self.cfg, username)
        if group is not None and not group.chat_id:
            group.chat_id = chat_id
            _LOG.info("Bound @%s -> chat_id=%s", group.username, chat_id)
        return group


def describe_groups(groups: list[GroupConfig]) -> str:
    parts = []
    for g in groups:
        title = g.title or "?"
        parts.append(f"{title} | {g.chat_id or 'unresolved'}")
    return "; ".join(parts)


def format_record(rec: CatalogRecord, tz) -> str:
    return (
        f"[{rec.group_title} | {rec.group_id}] "
        f"{rec.month} #{rec.month_seq} "
        f"{display_date(rec.received_at, tz)} {display_time(rec.received_at, tz)} "
        f"{rec.side} {rec.symbol} entry={rec.entry} sl={rec.sl} tps={list(rec.tps)}"
    )
