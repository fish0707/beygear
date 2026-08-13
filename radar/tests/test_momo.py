"""momo 搜尋頁解析。

樣本取自真實回應(GitHub Actions runner 實抓,見 tools/probe_sites.py)。
重點在於:momo 的商品 JSON 是塞在 JavaScript 字串裡的,引號都跳脫過,而且
一頁裡混著自營商品與摩天商城賣家商品。
"""

from __future__ import annotations

from monitors.momo import MomoMonitor

# 真實搜尋頁的片段:引號跳脫、巢狀價格物件、後面還接著別的欄位。
REAL_HTML = r'''
<script>var d = "{\"goodsInfoList\":[
 {\"goodsCode\":\"15162670\",\"goodsName\":\"【TAKARA TOMY】BEYBLADE X 戰鬥陀螺X UX-15 鮫鯊狂鱗改造組\",
  \"goodsPrice\":\"$$795\",\"goodsPriceModel\":{\"basePrice\":{\"sign\":\"$$\",\"price\":\"795\"}},
  \"goodsPriceOri\":\"$$880\",\"goodsStock\":\"168\"},
 {\"goodsCode\":\"15489159\",\"goodsName\":\"【TAKARA TOMY】戰鬥陀螺X UX-03 魔導神杖 5-70DB 鳳凰飛翼BX-23 武士聖劍\",
  \"goodsPrice\":\"$$1,199\",\"goodsPriceOri\":\"$$1,199\",\"goodsStock\":\"6\"},
 {\"goodsCode\":\"TP00074150005933\",\"goodsName\":\"鳳凰飛翼 爆裂陀螺 神杖 BX-23 正拉線 發射器\",
  \"goodsPrice\":\"$$528\",\"goodsStock\":\"62337\"},
 {\"goodsCode\":\"15489158\",\"goodsName\":\"【TAKARA TOMY】戰鬥陀螺X 戰犀號角 BX-19 3-80S\",
  \"goodsPrice\":\"$$799\",\"goodsStock\":\"0\"}
]}";</script>
'''


def test_parses_momo_own_listings_with_price_and_stock():
    snaps = MomoMonitor.parse_search(REAL_HTML)
    by_id = {s.item_id: s for s in snaps}

    # 摩天商城賣家商品(TP…)的商品頁網址規則未經實測,所以刻意不收。
    assert "TP00074150005933" not in by_id
    assert set(by_id) == {"15162670", "15489159", "15489158"}

    s = by_id["15162670"]
    assert s.price == 795            # "$$795" 要脫掉貨幣符號
    assert s.original_price == 880   # goodsPriceOri,不是 goodsPrice
    assert s.stock == 168
    assert s.available is True
    assert s.url == "https://www.momoshop.com.tw/product/15162670"
    assert s.is_original_price is True


def test_thousands_separator_and_sold_out():
    by_id = {s.item_id: s for s in MomoMonitor.parse_search(REAL_HTML)}
    assert by_id["15489159"].price == 1199   # "$$1,199"
    sold_out = by_id["15489158"]
    assert sold_out.stock == 0
    assert sold_out.available is False


def test_bundles_do_not_pollute_a_single_products_timeline():
    """名稱裡有多個型號的是套裝,不能算成其中任一支的價格歷史。"""
    by_id = {s.item_id: s for s in MomoMonitor.parse_search(REAL_HTML)}
    assert by_id["15162670"].product_key == "UX-15"
    assert by_id["15489158"].product_key == "BX-19"
    # UX-03 + BX-23 同時出現 → 套裝
    assert by_id["15489159"].product_key == "bundle-15489159"


def test_gear_specs_are_not_mistaken_for_model_codes():
    """「5-70DB」「3-80S」是齒輪規格,不是型號。"""
    assert MomoMonitor.product_key_for("戰鬥陀螺X 5-70DB 3-80S", "123456") == "bundle-123456"


def test_broken_page_returns_nothing_rather_than_raising():
    assert MomoMonitor.parse_search("") == []
    assert MomoMonitor.parse_search('"goodsInfoList": [ {oops') == []
