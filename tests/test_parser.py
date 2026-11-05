from src.parser import parse_signal
from src.models import Side

SELL = """#XAUUSD SELL 4315-4318

TP 4312
TP 4309
TP 4305
TP 4300
TP 4295
TP 4285

SL 4327
"""

BUY = """#XAUUSD BUY 4349-4346

TP 4352
TP 4355
TP 4359
TP 4364
TP 4369
TP 4379

SL 4337
"""


def test_parse_sell_template():
    sig = parse_signal(SELL)
    assert sig is not None
    assert sig.symbol == "XAUUSD"
    assert sig.side is Side.SELL
    assert sig.zone_low == 4315
    assert sig.zone_high == 4318
    assert sig.tps == (4312, 4309, 4305, 4300, 4295, 4285)
    assert sig.sl == 4327
    assert sig.tp_count == 6


def test_parse_buy_template():
    sig = parse_signal(BUY)
    assert sig is not None
    assert sig.side is Side.BUY
    assert sig.zone_low == 4346
    assert sig.zone_high == 4349
    assert sig.tps[0] == 4352
    assert sig.sl == 4337


def test_parse_messy_whitespace_and_dashes():
    text = "#XAUUSD  buy  4349–4346\n\nTP: 4352\nTP 4355\nSL:4337"
    sig = parse_signal(text)
    assert sig is not None
    assert sig.side is Side.BUY
    assert sig.tps == (4352, 4355)
    assert sig.sl == 4337


PLAN_SELL = """XAUUSD SELL PLAN @4365_4368

tp @4349
tp @4335

SL@4381
"""

PLAN_BUY = """XAUUSD BUY PLAN @4397_4395

tp @4418
tp @4444

SL@4381
"""


def test_parse_plan_sell_template():
    sig = parse_signal(PLAN_SELL)
    assert sig is not None
    assert sig.symbol == "XAUUSD"
    assert sig.side is Side.SELL
    assert sig.zone_low == 4365
    assert sig.zone_high == 4368
    assert sig.tps == (4349, 4335)
    assert sig.sl == 4381
    assert sig.tp_count == 2


def test_parse_plan_buy_template():
    sig = parse_signal(PLAN_BUY)
    assert sig is not None
    assert sig.side is Side.BUY
    assert sig.zone_low == 4395
    assert sig.zone_high == 4397
    assert sig.tps == (4418, 4444)
    assert sig.sl == 4381


STYLED_BUY = """#XAUUSD BUY 4152-4158

𝐓𝐏 ( ❶ ) 4168
𝐓𝐏 ( ❷ ) 4176
𝐓𝐏 ( ❸ ) 4185
𝐓𝐏 ( ❹ ) 4193
𝐓𝐏 ( ❺ ) 4200
𝐓𝐏 ( ❻ ) 4210

𝐒𝐋 4140
"""


def test_parse_unicode_tp_with_circled_index():
    sig = parse_signal(STYLED_BUY)
    assert sig is not None
    assert sig.side is Side.BUY
    assert sig.zone_low == 4152
    assert sig.zone_high == 4158
    assert sig.tps == (4168, 4176, 4185, 4193, 4200, 4210)
    assert sig.sl == 4140


def test_ignore_non_signal():
    assert parse_signal("good morning") is None
    assert parse_signal("#XAUUSD SELL 4315-4318\nTP 4312") is None  # no SL
    assert parse_signal("XAUUSD SELL PLAN @4365_4368\ntp @4349") is None  # no SL


def test_header_keeps_first_number_as_entry():
    sig = parse_signal(SELL)
    assert sig is not None
    assert sig.entry == 4315.0
    buy = parse_signal(BUY)
    assert buy is not None
    assert buy.entry == 4349.0


SNIPER_SELL = """XAUUSD SELL 4083
MORE SELL 4086

TP1 4081
TP2 4079
TP3 4077
TP4 4075
TP5 4073

TP OPEN
"""

SNIPER_BUY = """XAUUSD BUY 4116
MORE BUY 4113

TP¹ 4119
TP² 4122
TP³ 4126

TP OPEN

SL 4106 SCALPING
"""


def test_parse_sniper_buy_tp_index_and_sl_suffix():
    sig = parse_signal(SNIPER_BUY)
    assert sig is not None
    assert sig.side is Side.BUY
    assert sig.entry == 4116
    assert sig.tps == (4119, 4122, 4126)
    assert sig.sl == 4106


def test_parse_sniper_sell_without_sl_is_rejected():
    assert parse_signal(SNIPER_SELL) is None


GOLD_SLASH_SELL = """GOLD SELL 4146/4150

SL 4150

TP 4143
TP 4140
TP 4137
TP 4134
TP 4130
TP 4125
TP 4115
"""

GOLD_SLASH_BUY = """GOLD buy 4147/4144

SL 4135

TP 4150
TP 4153
TP 4156
TP 4160
TP 4163
TP 4166
TP 4170
"""


def test_parse_gold_slash_header():
    sell = parse_signal(GOLD_SLASH_SELL)
    assert sell is not None
    assert sell.symbol == "XAUUSD"
    assert sell.side is Side.SELL
    assert sell.entry == 4146
    assert sell.zone_high == 4150
    assert sell.sl == 4150
    assert sell.tps[-1] == 4115
    buy = parse_signal(GOLD_SLASH_BUY)
    assert buy is not None
    assert buy.side is Side.BUY
    assert buy.entry == 4147
    assert buy.sl == 4135


DOUBLE_HEADER_SELL = """#XAUUSD SELL  4164
#XAUUSD SELL 4167

TP1 4161
TP2 4158
TP3 4155
TP4 4152
TP5 4149
TP6 4143

SL   4177
"""


def test_parse_double_header_uses_first_entry():
    sig = parse_signal(DOUBLE_HEADER_SELL)
    assert sig is not None
    assert sig.side is Side.SELL
    assert sig.entry == 4164
    assert sig.tps == (4161, 4158, 4155, 4152, 4149, 4143)
    assert sig.sl == 4177


def test_header_accepts_single_full_price():
    text = "#XAUUSD SELL 4176.25\nTP 4170.10\nSL 4182.40\n"
    sig = parse_signal(text)
    assert sig is not None
    assert sig.entry == 4176.25
    assert sig.zone_low == 4176.25
    assert sig.zone_high == 4176.25
    assert sig.tps == (4170.10,)
    assert sig.sl == 4182.40
