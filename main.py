from __future__ import annotations

import argparse
import logging
from pathlib import Path

import yaml

from src.config import load_config
from src.listener import SignalListener, describe_groups
from src.logging_setup import setup_logging

_LOG = logging.getLogger(__name__)


def main() -> int:
    parser = argparse.ArgumentParser(description="Gold Trading — Telegram Group Listener")
    parser.add_argument("--config", default="config.yaml")
    args = parser.parse_args()

    try:
        cfg = load_config(Path(args.config) if args.config else None)
    except yaml.YAMLError as exc:
        mark = getattr(exc, "problem_mark", None)
        where = f" (line {mark.line + 1}, column {mark.column + 1})" if mark else ""
        print(f"config.yaml syntax error{where}: {getattr(exc, 'problem', exc)}")
        return 1
    except (ValueError, KeyError) as exc:
        print(f"config.yaml rejected: {exc}")
        return 1

    setup_logging(cfg.logs_dir)
    if not cfg.telegram_api_id or not cfg.telegram_api_hash:
        _LOG.error("Set TELEGRAM_API_ID and TELEGRAM_API_HASH in .env")
        return 1

    cfg.data_dir.mkdir(parents=True, exist_ok=True)
    cfg.outbox_dir.mkdir(parents=True, exist_ok=True)
    service = SignalListener(cfg)
    _LOG.info("Listener start groups=%s tz=%s", describe_groups(cfg.groups), cfg.timezone)

    try:
        import asyncio

        async def runner():
            await service.start()
            await service.run_until_disconnected()

        asyncio.run(runner())
    except KeyboardInterrupt:
        _LOG.info("Interrupted")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
