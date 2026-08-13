"""momo 解析測試(餵 mock 回應,不打真實 API)。"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Watch  # noqa: E402
from monitors.momo import MomoMonitor, _to_unix_seconds, _price_from_text  # noqa: E402

WATCH = Watch(product_key="UX-04", platform="momo", item_id="15462754",
              original_price=390, name="UX-04")


class MomoParseTest(unittest.TestCase):
    def test_parse_full_response(self):
        data = {
            "rtnGoodsData": {
                "goodsName": "戰鬥陀螺 UX-04",
                "goodsStock": 5,
                "goodsPrice": 390,
                "onSaleTimestamp": 1769000400000,  # 毫秒
                "goodsPaymentDescription": "$390",
            }
        }
        s = MomoMonitor.parse(data, WATCH)
        self.assertEqual(s.price, 390)
        self.assertEqual(s.stock, 5)
        self.assertTrue(s.available)
        self.assertTrue(s.is_original_price)
        self.assertEqual(s.on_sale_ts, 1769000400)  # 轉成秒
        self.assertEqual(s.platform, "momo")
        self.assertEqual(s.product_key, "UX-04")

    def test_parse_out_of_stock(self):
        data = {"rtnGoodsData": {"goodsStock": 0, "goodsPrice": 390}}
        s = MomoMonitor.parse(data, WATCH)
        self.assertFalse(s.available)
        self.assertEqual(s.stock, 0)

    def test_parse_price_from_description_only(self):
        data = {"rtnGoodsData": {"goodsStock": 2, "goodsPaymentDescription": "售價 1,290 元"}}
        s = MomoMonitor.parse(data, WATCH)
        self.assertEqual(s.price, 1290)

    def test_parse_missing_fields_does_not_crash(self):
        s = MomoMonitor.parse({}, WATCH)
        self.assertIsNone(s.price)
        self.assertIsNone(s.stock)
        self.assertIsNone(s.on_sale_ts)
        self.assertFalse(s.available)
        # 名稱退回設定值
        self.assertEqual(s.name, "UX-04")

    def test_high_price_flag(self):
        data = {"rtnGoodsData": {"goodsStock": 1, "goodsPrice": 990}}
        s = MomoMonitor.parse(data, WATCH)
        self.assertFalse(s.is_original_price)  # 990 > 390

    def test_timestamp_helpers(self):
        self.assertEqual(_to_unix_seconds(1769000400000), 1769000400)  # 毫秒→秒
        self.assertEqual(_to_unix_seconds(1769000400), 1769000400)     # 已是秒
        self.assertIsNone(_to_unix_seconds(None))
        self.assertIsNone(_to_unix_seconds("abc"))
        self.assertIsNone(_to_unix_seconds(0))

    def test_price_from_text_helper(self):
        self.assertEqual(_price_from_text("$390"), 390)
        self.assertEqual(_price_from_text("NT$1,290"), 1290)
        self.assertIsNone(_price_from_text(""))
        self.assertIsNone(_price_from_text(None))


if __name__ == "__main__":
    unittest.main()
