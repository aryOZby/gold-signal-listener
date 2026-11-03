# Gold Signal Listener

Listen-only catalog for Telegram gold signals. This process does **not** open trades.

Stage 1 of the split:

1. This listener watches configured Telegram groups by `chat_id`.
2. It stores every parsed BUY/SELL with the original group title, numeric id, date/time, and a per-group monthly sequence that resets on the 1st (Asia/Jerusalem).
3. A later chart bot (stage 2) will read `data/outbox/*.json` and execute on MT5.

Live `gold-signal-bot` and stats `gold-stats-bot` stay unchanged until stage 2 is ready.

## What you see per signal

```
[Profit Kings Original | -1002984909577] 2026-11 #3 2026-11-03 11:15:00 SELL XAUUSD ...
```

- original Telegram title
- group `chat_id`
- monthly number (`#1`, `#2`, …) that starts over each month, independently per group
- Excel workbook: `reports/<internal-name>/<YYYY-MM>.xlsx`

## Setup

```bash
cp config.example.yaml config.yaml
cp .env.example .env
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/login_telegram.py
python main.py
```

Fill `.env` with `TELEGRAM_API_ID`, `TELEGRAM_API_HASH`, `TELEGRAM_PHONE`. Edit `config.yaml` groups. Run `python scripts/list_chats.py` to copy ids and original titles.

## Stage 2 outbox

Each catalogued signal writes `data/outbox/<id>.json` with group id+title, month sequence, side, entry, SL, TPs. The chart executor will consume those files.
