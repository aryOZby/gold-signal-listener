from pathlib import Path

from src.config import load_config


def test_config_keeps_original_telegram_titles(tmp_path: Path, monkeypatch):
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(
        """
timezone: Asia/Jerusalem
telegram:
  session_name: t
  groups:
    - name: vip_signals_room
      title: "VIP SIGNALS ROOM (LIFETIME)"
      chat_id: -1002001216034
    - name: technical_pips
      title: "Technical Pips ™"
      username: TechnicalPips6273
      chat_id: -1001569906975
    - name: profit_kings
      title: "profit__kings"
      username: profitkingscalper_007
      chat_id: -1002984909577
paths:
  data_dir: data
""",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    cfg = load_config(cfg_path)
    titles = {g.name: g.title for g in cfg.groups}
    assert titles["vip_signals_room"] == "VIP SIGNALS ROOM (LIFETIME)"
    assert titles["technical_pips"] == "Technical Pips ™"
    assert titles["profit_kings"] == "profit__kings"
