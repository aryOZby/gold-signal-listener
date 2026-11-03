from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook, load_workbook
from zoneinfo import ZoneInfo

from .models import CatalogRecord
from .timeutil import display_date, display_time

HEADERS = [
    "Monthly #",
    "Date",
    "Time",
    "Group ID",
    "Original title",
    "Internal name",
    "Side",
    "Symbol",
    "Entry",
    "SL",
    "TPs",
    "Source text",
]


def write_signal(reports_dir: Path, rec: CatalogRecord, tz: ZoneInfo) -> Path:
    folder = reports_dir / rec.group_name
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{rec.month}.xlsx"
    if path.exists():
        book = load_workbook(path)
        sheet = book.active
    else:
        book = Workbook()
        sheet = book.active
        sheet.title = "Signals"
        sheet.append(HEADERS)
    sheet.append(
        [
            rec.month_seq,
            display_date(rec.received_at, tz),
            display_time(rec.received_at, tz),
            rec.group_id,
            rec.group_title,
            rec.group_name,
            rec.side,
            rec.symbol,
            rec.entry,
            rec.sl,
            ", ".join(str(p) for p in rec.tps),
            rec.raw_text,
        ]
    )
    book.save(path)
    return path
