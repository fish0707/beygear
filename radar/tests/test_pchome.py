"""PChome 解析測試(餵 mock 回應,不打真實 API)。"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Watch  # noqa: E402
from monitors.pchome import PChomeMonitor  # noqa: E402

WATCH = Watch(product_key="UX-04", platform="pchome", item_id="DGAJ8T-A900AVFV7",
              original_price=390, name="UX-04")


class PChomeParseTest(unittest.TestCase):
    def test_parse_keyed_response_in_stock(self):
        data = {
            "DGAJ8T-A900AVFV7": {
                "Id": "DGAJ8T-A900AVFV7",
                "Name": "戰鬥陀螺 UX-04",
                "Price": {"P": 390, "M": 420},
                "Qty": 8,
                "ButtonType": "1",
            }
        }
        s = PChomeMonitor.parse(data, WATCH)
        self.assertEqual(s.price, 390)
        self.assertEqual(s.stock, 8)
        self.assertTrue(s.available)
        self.assertTrue(s.is_original_price)  # 390 <= 390
        self.assertEqual(s.platform, "pchome")
        self.assertEqual(s.product_key, "UX-04")

    def test_parse_out_of_stock(self):
        data = {"DGAJ8T-A900AVFV7": {"Price": {"P": 390, "M": 420}, "Qty": 0}}
        s = PChomeMonitor.parse(data, WATCH)
        self.assertFalse(s.available)
        self.assertEqual(s.stock, 0)

    def test_original_price_falls_back_to_market_price(self):
        # 設定沒給 original_price → 用 PChome 市價 M(420);售價 450 > 420 → 非原價
        w = Watch(product_key="UX-04", platform="pchome", item_id="X", name="UX-04")
        data = {"X": {"Price": {"P": 450, "M": 420}, "Qty": 3}}
        s = PChomeMonitor.parse(data, w)
        self.assertEqual(s.original_price, 420)
        self.assertFalse(s.is_original_price)

    def test_parse_inner_dict_without_key(self):
        # 容忍回應直接是內層 dict
        data = {"Id": "X", "Price": 390, "Qty": 2}
        w = Watch(product_key="UX-04", platform="pchome", item_id="X", original_price=390)
        s = PChomeMonitor.parse(data, w)
        self.assertEqual(s.price, 390)
        self.assertEqual(s.stock, 2)

    def test_parse_missing_does_not_crash(self):
        s = PChomeMonitor.parse({}, WATCH)
        self.assertIsNone(s.price)
        self.assertIsNone(s.stock)
        self.assertFalse(s.available)
        self.assertEqual(s.name, "UX-04")

    def test_no_on_sale_ts(self):
        data = {"DGAJ8T-A900AVFV7": {"Price": {"P": 390}, "Qty": 1}}
        s = PChomeMonitor.parse(data, WATCH)
        self.assertIsNone(s.on_sale_ts)


if __name__ == "__main__":
    unittest.main()
