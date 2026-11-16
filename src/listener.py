from __future__ import annotations

import asyncio
import logging
from datetime import timezone
from pathlib import Path

from telethon import TelegramClient, events
from telethon.tl.custom.message import Message
from telethon.utils import get_peer_id

from .config import AppConfig, group_by_chat_id, group_by_username
from .models import GroupConfig, SignalMessage
from .outbox import write_outbox
from .parser import parse_signal
from .timeutil import display_dt, utcnow

_LOG = logging.getLogger(__name__)

# Telegram can stop pushing updates without dropping the connection, so every group is also
# read directly on this interval and anything the live updates missed is handled then.
POLL_INTERVAL_SEC = 15
POLL_LIMIT = 5
HEARTBEAT_EVERY_SEC = 1800


class SeenMessages:
    """Message ids already handled per chat, so live updates and polling never double up."""

    def __init__(self, keep: int = 500):
        self.keep = keep
        self._baseline: dict[int, int] = {}
        self._seen: dict[int, set[int]] = {}

    def set_baseline(self, chat_id: int, last_id: int) -> None:
        """Messages up to last_id existed before the listener started and are not handled."""
        self._baseline[chat_id] = last_id

    def first_time(self, chat_id: int, msg_id: int) -> bool:
        if msg_id <= self._baseline.get(chat_id, 0):
            return False
        seen = self._seen.setdefault(chat_id, set())
        if msg_id in seen:
            return False
        seen.add(msg_id)
        if len(seen) > self.keep:
            seen.discard(min(seen))
        return True


class SignalListener:
    def __init__(self, cfg: AppConfig):
        self.cfg = cfg
        cfg.data_dir.mkdir(parents=True, exist_ok=True)
        session = Path(cfg.data_dir) / cfg.session_name
        self.client = TelegramClient(str(session), cfg.telegram_api_id, cfg.telegram_api_hash)
        self.seen = SeenMessages()
        self._entities: dict[int, tuple[GroupConfig, object]] = {}
        self._poll_task: asyncio.Task | None = None

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
        if self._entities:
            self._poll_task = asyncio.create_task(self._poll_loop())
            _LOG.info("Also reading every group directly every %ss", POLL_INTERVAL_SEC)

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
                latest = await self.client.get_messages(entity, limit=1)
                self.seen.set_baseline(group.chat_id, latest[0].id if latest else 0)
                self._entities[group.chat_id] = (group, entity)
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
        if not self.seen.first_time(int(chat_id), int(msg.id)):
            return
        title = await self._chat_title(event, group)
        self._handle(group, int(chat_id), msg, title, polled=False)

    async def _poll_loop(self) -> None:
        loop = asyncio.get_running_loop()
        last_beat = loop.time()
        while True:
            await asyncio.sleep(POLL_INTERVAL_SEC)
            failed = 0
            for chat_id, (group, entity) in list(self._entities.items()):
                try:
                    msgs = await asyncio.wait_for(self.client.get_messages(entity, limit=POLL_LIMIT), timeout=30)
                except Exception as exc:
                    failed += 1
                    _LOG.warning("Direct read of %s failed: %s", group.name, exc)
                    continue
                for msg in sorted(msgs, key=lambda m: m.id):
                    if self.seen.first_time(chat_id, int(msg.id)):
                        try:
                            self._handle(group, chat_id, msg, group.title or group.name, polled=True)
                        except Exception:
                            _LOG.exception("Failed to handle message %s from %s", msg.id, group.name)
            if loop.time() - last_beat >= HEARTBEAT_EVERY_SEC:
                last_beat = loop.time()
                _LOG.info("Alive: reading %d groups, %d failed this round", len(self._entities), failed)

    def _handle(self, group: GroupConfig, chat_id: int, msg: Message, title: str, polled: bool) -> None:
        text = msg.raw_text or ""
        via = " (missed by live updates, caught by direct read)" if polled else ""
        parsed = parse_signal(text)
        if parsed is None:
            if text.strip():
                _LOG.info(
                    "Not a signal from %s (%s / %s)%s. Preview: %s",
                    group.name,
                    group.title or "?",
                    chat_id,
                    via,
                    text[:120],
                )
            return
        received = msg.date
        if received is None:
            received = utcnow()
        elif received.tzinfo is None:
            received = received.replace(tzinfo=timezone.utc)
        signal = SignalMessage(
            group_name=group.name,
            group_id=chat_id,
            group_title=title,
            telegram_msg_id=int(msg.id),
            received_at=received,
            parsed=parsed,
        )
        write_outbox(self.cfg.outbox_dir, signal)
        _LOG.info("Signal%s %s", via, format_signal(signal, self.cfg.tz))

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


def format_signal(signal: SignalMessage, tz) -> str:
    parsed = signal.parsed
    return (
        f"[{signal.group_title} | {signal.group_id}] "
        f"{display_dt(signal.received_at, tz)} "
        f"{parsed.side.value} {parsed.symbol} entry={parsed.entry} sl={parsed.sl} "
        f"tps={list(parsed.tps)}"
    )
