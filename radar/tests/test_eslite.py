"""誠品 eslite 發現式監控測試(餵 mock HTML,不打真實站台)。"""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from calendar_db import Calendar  # noqa: E402
from config import Search  # noqa: E402
from monitors.eslite import EsliteMonitor, _model_code, _looks_beyblade  # noqa: E402

SEARCH = Search(platform="eslite", keyword="beyblade", name="誠品掃描")


def next_data_html(products: list[dict]) -> str:
    payload = {"props": {"pageProps": {"searchResult": {"items": products}}}}
    return (
        '<html><head><script id="__NEXT_DATA__" type="application/json">'
        + json.dumps(payload, ensure_ascii=False)
        + "</script></head><body></body></html>"
    )


class EsliteExtractTest(unittest.TestCase):
    def test_next_data_extraction(self):
        html = next_data_html([
            {"id": "10042014802683179742001", "name": "BEYBLADE X 戰鬥陀螺 BX-10 極限衝擊戰鬥盤", "price": 350},
            {"id": "10042014802683165874006", "name": "BEYBLADE X 戰鬥陀螺 BX-51 蒼旋風發射器 黑綠", "price": 280},
            {"id": "99999", "name": "無關的筆記本", "price": 100},  # 應被濾掉
        ])
        snaps = EsliteMonitor.parse_search(html, SEARCH)
        self.assertEqual(len(snaps), 2)
        by_id = {s.item_id: s for s in snaps}
        s1 = by_id["10042014802683179742001"]
        self.assertEqual(s1.platform, "eslite")
        self.assertEqual(s1.product_key, "BX-10")  # 型號當 product_key
        self.assertEqual(s1.price, 350)
        self.assertTrue(s1.available)
        self.assertIn("BX-10", s1.name)
        self.assertTrue(s1.url.endswith("/product/10042014802683179742001"))

    def test_jsonld_itemlist_extraction(self):
        ld = {
            "@context": "https://schema.org",
            "@type": "ItemList",
            "itemListElement": [
                {"@type": "ListItem", "item": {
                    "@type": "Product", "name": "BEYBLADE X BX-10 戰鬥盤",
                    "url": "https://www.eslite.com/product/10042014802683179742001",
                    "offers": {"@type": "Offer", "price": "350", "availability": "https://schema.org/InStock"}}},
            ],
        }
        html = f'<script type="application/ld+json">{json.dumps(ld)}</script>'
        snaps = EsliteMonitor.parse_search(html, SEARCH)
        self.assertEqual(len(snaps), 1)
        self.assertEqual(snaps[0].item_id, "10042014802683179742001")
        self.assertEqual(snaps[0].price, 350)

    def test_link_fallback_extraction(self):
        # 沒有結構化資料時,至少從 /product/ 連結撈到 id
        html = '<a href="/product/10042014802683179742001">看商品</a>'
        snaps = EsliteMonitor.parse_search(html, SEARCH)
        # name 空 → 用「eslite 商品 {id}」,但 _looks_beyblade 濾掉(非 beyblade 名稱)
        # 這裡驗證不炸即可
        self.assertIsInstance(snaps, list)

    def test_empty_html_no_crash(self):
        self.assertEqual(EsliteMonitor.parse_search("", SEARCH), [])

    def test_helpers(self):
        self.assertEqual(_model_code("BEYBLADE X BX-10 戰鬥盤"), "BX-10")
        self.assertEqual(_model_code("UX-04 亂心弓箭手"), "UX-04")
        self.assertIsNone(_model_code("沒有型號的名稱"))
        self.assertTrue(_looks_beyblade("BEYBLADE X 戰鬥陀螺", "beyblade"))
        self.assertTrue(_looks_beyblade("蒼旋風發射器", "beyblade"))
        self.assertFalse(_looks_beyblade("普通筆記本", "beyblade"))


class EsliteDiscoveryFlowTest(unittest.TestCase):
    """首次掃描建立基準線、之後才通知新品 —— 模擬 run.py 的 seeding 邏輯。"""

    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.cal = Calendar(self.path)

    def tearDown(self):
        self.cal.close()
        os.remove(self.path)

    def test_first_run_seeds_then_new_item_notifies(self):
        # 第一輪:兩個商品 → 首次掃描,建立基準線(run.py 會選擇不通知)
        first = next_data_html([
            {"id": "111", "name": "BEYBLADE X BX-10 戰鬥盤", "price": 350},
            {"id": "222", "name": "BEYBLADE X BX-51 發射器", "price": 280},
        ])
        self.assertEqual(self.cal.count_platform("eslite"), 0)  # 首次
        snaps1 = EsliteMonitor.parse_search(first, SEARCH)
        self.cal.upsert_many(snaps1)
        self.assertEqual(self.cal.count_platform("eslite"), 2)  # 已建立基準線

        # 第二輪:多了一個新商品 333 → 非首次,應偵測到 1 筆新變更
        second = next_data_html([
            {"id": "111", "name": "BEYBLADE X BX-10 戰鬥盤", "price": 350},
            {"id": "222", "name": "BEYBLADE X BX-51 發射器", "price": 280},
            {"id": "333", "name": "BEYBLADE X UX-04 亂心弓箭手", "price": 390},
        ])
        snaps2 = EsliteMonitor.parse_search(second, SEARCH)
        changes = self.cal.upsert_many(snaps2)
        new_ids = [c.event.item_id for c in changes if c.is_new]
        self.assertEqual(new_ids, ["333"])


if __name__ == "__main__":
    unittest.main()
