# Gold Trading — Telegram Group Listener

Ingest service for a gold-trading desk. This repository is the **listener** half of the system: it watches Telegram signal groups and catalogs XAUUSD calls. It does not size lots, open orders, or talk to MetaTrader.

The split is the same idea as backend / frontend:

| Service | Role |
|---|---|
| **Telegram Group Listener** (this repo) | Subscribe to groups by chat id, parse BUY/SELL templates, store a durable catalog |
| **Chart Executor** (next repo) | Read the listener outbox and run entries, lots, stops, and reports on the chart |

Identity is always the Telegram **chat id**. The original channel title is stored next to it so operators can recognize the group in logs and workbooks.

## What it records

Every accepted signal is stored with:

- original Telegram title and numeric chat id
- date and time (`Asia/Jerusalem`)
- per-group monthly sequence (`#1`, `#2`, …) that resets on the 1st of each month
- side, symbol, entry, SL, take-profits, and the raw message

Outputs:

- SQLite: `data/catalog.db`
- Excel: `reports/<internal-name>/<YYYY-MM>.xlsx`
- Executor outbox: `data/outbox/<id>.json`

Log line:

```
[Technical Pips ™ | -1001569906975] 2026-11 #3 2026-11-03 11:15:00 SELL XAUUSD ...
```

Promotional or malformed messages are ignored on purpose.

## Groups

Configure groups in `config.yaml`. `name` is a stable internal key. `title` is the human label; at runtime it is replaced with the live Telegram title.

```yaml
    - name: gold_sniper
      title: "GOLD SNIPER"
      username: GOLDSNNPER786
      chat_id: -1001754381715
```

Add another group by appending a block and restarting. The account that logs in must already be a member of that channel. `python scripts/list_chats.py` prints id + original title.

## Setup (Windows VPS)

```bat
cd C:\Users\Administrator\gold-signal-listener
copy config.example.yaml config.yaml
copy .env.example .env
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe scripts\login_telegram.py
.venv\Scripts\python.exe main.py
```

`.env` needs `TELEGRAM_API_ID`, `TELEGRAM_API_HASH`, and `TELEGRAM_PHONE` from [my.telegram.org](https://my.telegram.org). Keep the CMD window open while listening.

## Outbox for the executor

Each catalogued signal writes JSON the chart service will consume later: group id, original title, monthly sequence, side, entry, SL, and TPs.
