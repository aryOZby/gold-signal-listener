# Gold Trading — Telegram Group Listener

Ingest service for a gold-trading desk. Its only job is to listen: it watches Telegram signal groups, recognizes XAUUSD calls, and hands each one to the next service. It keeps no records, builds no reports, and never talks to MetaTrader.

| Service | Role |
|---|---|
| **Telegram Group Listener** (this repo) | Listen to groups by chat id and hand off each recognized signal |
| [Chart Executor](https://github.com/aryOZby/gold-trading-chart-executor) | Trade those signals on the MT5 chart |
| Reporting (planned) | Build monthly Excel tables per group and email them |

Identity is always the Telegram **chat id**. The live channel title travels with every signal so operators can recognize the group downstream.

## Hand-off

Each recognized signal becomes one file in `paths.outbox_dir` — MT5 `Common\Files\gt_signals`, where the Chart Executor EA reads it — named `<chat_id>_<message_id>.json`:

- group chat id, internal name, and original Telegram title
- message time
- side, symbol, entry, zone, SL, and take-profits
- the raw message text

The EA picks the file up and moves it out of the folder. Promotional or malformed messages are ignored and never reach the outbox.

Log line for a recognized signal:

```
Signal [Technical Pips ™ | -1001569906975] 2026-11-03 11:15:00 SELL XAUUSD entry=4315.0 sl=4327.0 tps=[...]
```

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
