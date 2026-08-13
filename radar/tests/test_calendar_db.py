"""行事曆去重 + 狀態機 + 變更偵測測試。"""

import os
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from calendar_db import (  # noqa: E402
    ANNOUNCED, IMMINENT, ON_SALE, SOLD_OUT, RESTOCKED, Calendar,
)
from monitors.base import ProductSnapshot  # noqa: E402

NOW = 1_700_000_000
LEAD = 1800  # 30 分鐘


def snap(**kw) -> ProductSnapshot:
    base = dict(
        product_key="UX-04", platform="momo", item_id="15462754",
        name="UX-04", url="https://example.com/g/15462754",
        original_price=390,
    )
    base.update(kw)
    return ProductSnapshot(**base)


class CalendarTest(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.cal = Calendar(self.path)

    def tearDown(self):
        self.cal.close()
        os.remove(self.path)

    def test_new_event_returns_change(self):
        c = self.cal.upsert_snapshot(
            snap(price=390, stock=5, available=True), now=NOW, imminent_lead_sec=LEAD
        )
        self.assertIsNotNone(c)
        self.assertTrue(c.is_new)
        self.assertEqual(c.event.status, ON_SALE)

    def test_dedup_no_change_returns_none(self):
        s = snap(price=390, stock=5, available=True)
        self.cal.upsert_snapshot(s, now=NOW, imminent_lead_sec=LEAD)
        c2 = self.cal.upsert_snapshot(s, now=NOW + 60, imminent_lead_sec=LEAD)
        self.assertIsNone(c2)
        # 去重:仍只有一列
        self.assertEqual(len(self.cal.all_events()), 1)

    def test_announced_then_imminent(self):
        # 開賣在 2 小時後 → 預告
        c1 = self.cal.upsert_snapshot(
            snap(on_sale_ts=NOW + 7200, available=False), now=NOW, imminent_lead_sec=LEAD
        )
        self.assertEqual(c1.event.status, ANNOUNCED)
        # 開賣在 10 分鐘後 → 即將開賣
        c2 = self.cal.upsert_snapshot(
            snap(on_sale_ts=NOW + 600, available=False), now=NOW + 100, imminent_lead_sec=LEAD
        )
        self.assertEqual(c2.event.status, IMMINENT)
        self.assertTrue(c2.is_imminent)

    def test_sold_out_then_restock_at_original_price(self):
        # 開賣中
        self.cal.upsert_snapshot(
            snap(price=390, stock=3, available=True), now=NOW, imminent_lead_sec=LEAD
        )
        # 售罄
        c_out = self.cal.upsert_snapshot(
            snap(price=390, stock=0, available=False), now=NOW + 60, imminent_lead_sec=LEAD
        )
        self.assertEqual(c_out.event.status, SOLD_OUT)
        # 原價補貨 → RESTOCKED,且 is_original_price 為 True
        c_re = self.cal.upsert_snapshot(
            snap(price=390, stock=4, available=True), now=NOW + 120, imminent_lead_sec=LEAD
        )
        self.assertEqual(c_re.event.status, RESTOCKED)
        self.assertTrue(c_re.is_restock)
        self.assertTrue(c_re.is_original_price_restock)

    def test_restock_settles_to_on_sale(self):
        self.cal.upsert_snapshot(snap(stock=1, available=True), now=NOW, imminent_lead_sec=LEAD)
        self.cal.upsert_snapshot(snap(stock=0, available=False), now=NOW + 1, imminent_lead_sec=LEAD)
        self.cal.upsert_snapshot(snap(stock=2, available=True), now=NOW + 2, imminent_lead_sec=LEAD)  # RESTOCKED
        c = self.cal.upsert_snapshot(snap(stock=2, available=True), now=NOW + 3, imminent_lead_sec=LEAD)
        # RESTOCKED → ON_SALE 是狀態變更,會回一個 change,但不再是 restock
        self.assertEqual(c.event.status, ON_SALE)
        self.assertFalse(c.is_restock)

    def test_is_original_price_flag(self):
        # 高於原價
        c = self.cal.upsert_snapshot(
            snap(price=590, original_price=390, stock=1, available=True),
            now=NOW, imminent_lead_sec=LEAD,
        )
        self.assertFalse(c.event.is_original_price)

    def test_price_drop_detected(self):
        self.cal.upsert_snapshot(
            snap(price=590, stock=1, available=True), now=NOW, imminent_lead_sec=LEAD
        )
        c = self.cal.upsert_snapshot(
            snap(price=390, stock=1, available=True), now=NOW + 60, imminent_lead_sec=LEAD
        )
        self.assertIsNotNone(c)
        self.assertTrue(c.price_dropped)

    def test_cross_platform_merge_by_product_key(self):
        self.cal.upsert_snapshot(
            snap(platform="momo", item_id="A", available=True), now=NOW, imminent_lead_sec=LEAD
        )
        self.cal.upsert_snapshot(
            snap(platform="pchome", item_id="B", available=True), now=NOW, imminent_lead_sec=LEAD
        )
        rows = self.cal.by_product_key("UX-04")
        self.assertEqual(len(rows), 2)
        self.assertEqual({r.platform for r in rows}, {"momo", "pchome"})


if __name__ == "__main__":
    unittest.main()
