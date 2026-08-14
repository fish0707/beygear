"""誠品 athena 搜尋 API 解析。

樣本是真實回應的一筆 hit(見 tools/probe_sites.py 的 job log)。誠品賣的是
書,所以多數商品名稱裡沒有型號代碼,合併鍵必須有退路。
"""

from __future__ import annotations

from monitors.eslite import EsliteMonitor

REAL_PAYLOAD = {
    "hits": {
        "found": 40,
        "hit": [
            {
                "id": "10022136782683093780004",
                "fields": {
                    "name": "BEYBLADE X 必勝XTRAガイド (2026/附陀螺)",
                    "final_price": "799",
                    "mprice": "888",
                    "stock": "0",
                    "url": "https://www.eslite.com/product/10022136782683093780004",
                    "eslite_sn": "2683093780004",
                },
            },
            {
                "id": "10012150962682602551005",
                "fields": {
                    "name": "戰鬥陀螺X UX-15 攻略",
                    "final_price": "300",
                    "mprice": "300",
                    "stock": "12",
                },
            },
            {
                "id": "10052305272682863630006",
                "fields": {
                    "name": "【ONE HOUSE】享樂趣加大貨櫃公仔盒 4入",
                    "final_price": "590",
                    "mprice": "590",
                    "stock": "2",
                },
            },
        ],
    }
}


def test_reads_price_and_stock_from_the_api():
    snaps = EsliteMonitor.parse_search(REAL_PAYLOAD)
    # 第三筆(公仔收納盒)是誠品模糊比對撈到的不相干商品,要被濾掉。
    assert len(snaps) == 2

    book = snaps[0]
    # 舊的 HTML 解析器在這裡永遠拿到 0 —— 頁面根本沒有價格。
    assert book.price == 799
    assert book.original_price == 888
    assert book.stock == 0
    assert book.available is False
    assert book.url == "https://www.eslite.com/product/10022136782683093780004"
    assert book.is_original_price is True


def test_product_key_falls_back_when_there_is_no_model_code():
    snaps = EsliteMonitor.parse_search(REAL_PAYLOAD)
    assert snaps[0].product_key == "eslite-10022136782683093780004"
    # 有型號的就用型號,才能跟 momo 的同款併成一條時間軸。
    assert snaps[1].product_key == "UX-15"
    assert snaps[1].available is True


def test_empty_or_malformed_payload_is_not_an_error():
    assert EsliteMonitor.parse_search({}) == []
    assert EsliteMonitor.parse_search({"hits": {"hit": [{"id": "1", "fields": {}}]}}) == []


def test_fuzzy_search_hits_that_are_not_beyblade_are_dropped():
    ids = {s.item_id for s in EsliteMonitor.parse_search(REAL_PAYLOAD)}
    assert "10052305272682863630006" not in ids
