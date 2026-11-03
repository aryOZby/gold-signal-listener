#!/usr/bin/env python3
"""Print Telegram dialog ids so you can paste them into config.yaml."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.config import load_config  # noqa: E402


async def _run() -> int:
    cfg = load_config()
    if not cfg.telegram_api_id or not cfg.telegram_api_hash:
        print("Missing TELEGRAM_API_ID / TELEGRAM_API_HASH in .env")
        return 1
    from telethon import TelegramClient

    cfg.data_dir.mkdir(parents=True, exist_ok=True)
    session = cfg.data_dir / cfg.session_name
    client = TelegramClient(str(session), cfg.telegram_api_id, cfg.telegram_api_hash)
    await client.start(phone=cfg.telegram_phone or None)
    print("chat_id\ttitle")
    async for dialog in client.iter_dialogs():
        print(f"{dialog.id}\t{dialog.name}")
    await client.disconnect()
    print("\nCopy the group id into config.yaml under telegram.groups.chat_id")
    return 0


def main() -> int:
    return asyncio.run(_run())


if __name__ == "__main__":
    raise SystemExit(main())
