"""通知訊息 + 草稿格式化測試(純字串,不送網路)。"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from calendar_db import Change, EventRow, RESTOCKED, IMMINENT, SOLD_OUT  # noqa: E402
import draft as draft_mod  # noqa: E402
from notify import format_change  # noqa: E402


def event(**kw) -> EventRow:
    base = dict(
        product_key="UX-04", platform="momo", item_id="15462754",
        name="Beyblade X UX-04", url="https://example.com/g/15462754",
        price=390, original_price=390, is_original_price=True, stock=4,
        on_sale_ts=1769000400, available=True, status=RESTOCKED,
        first_seen_at=0, last_updated_at=0, id=1,
    )
    base.update(kw)
    return EventRow(**base)


class NotifyFormatTest(unittest.TestCase):
    def test_original_price_restock_headline(self):
        c = Change(event=event(status=RESTOCKED), old_status=SOLD_OUT, old_price=390)
        msg = format_change(c)
        self.assertIn("原價補貨", msg)
        self.assertIn("原價✅", msg)
        self.assertIn("https://example.com/g/15462754", msg)

    def test_imminent_headline(self):
        c = Change(event=event(status=IMMINENT, available=False), old_status="ANNOUNCED", old_price=None)
        msg = format_change(c)
        self.assertIn("即將開賣", msg)

    def test_new_available_headline(self):
        # 新商品且可購買 → 新商品上架(對齊截圖那種通知)
        c = Change(event=event(status="ON_SALE", available=True), old_status=None, old_price=None)
        msg = format_change(c)
        self.assertIn("新商品上架", msg)

    def test_new_unavailable_headline(self):
        # 新事件但尚未可購買(如預告)→ 新情報
        c = Change(event=event(status="ANNOUNCED", available=False, price=None), old_status=None, old_price=None)
        msg = format_change(c)
        self.assertIn("新情報", msg)

    def test_price_drop_shown(self):
        c = Change(event=event(price=390), old_status="ON_SALE", old_price=590)
        msg = format_change(c)
        self.assertIn("↓", msg)


class DraftTest(unittest.TestCase):
    def test_draft_contains_disclosure_and_shopee(self):
        text = draft_mod.generate_draft(event())
        self.assertIn("推廣連結", text)          # 明示推廣
        self.assertIn("shopee.tw", text)         # 蝦皮導流
        self.assertIn("Beyblade X UX-04", text)

    def test_shopee_link_without_affiliate_is_plain(self):
        # 未設定分潤 ID 時,連結不帶 af_id
        link = draft_mod.shopee_link("UX-04")
        self.assertIn("shopee.tw/search", link)


if __name__ == "__main__":
    unittest.main()
