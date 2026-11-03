#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.config import load_config  # noqa: E402


def main() -> int:
    try:
        cfg = load_config()
    except Exception as exc:
        print(f"config.yaml rejected: {exc}")
        return 1
    print(f"timezone={cfg.timezone}")
    print(f"session={cfg.session_name}")
    for g in cfg.groups:
        print(f"  {g.title or g.name}  chat_id={g.chat_id}  username={g.username or '-'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
