"""Funbox JSON-LD 解析測試(餵 mock HTML,不打真實站台)。"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Watch  # noqa: E402
from monitors.funbox import FunboxMonitor  # noqa: E402

URL = "https://shop.example.com/products/ux-04"
WATCH = Watch(product_key="UX-04", platform="funbox", item_id=URL,
              original_price=390, name="")


def html_with_ld(ld: str) -> str:
    return f"""<!doctype html><html><head>
    <script type="application/ld+json">{ld}</script>
    </head><body>...</body></html>"""


class FunboxParseTest(unittest.TestCase):
    def test_parse_in_stock_product(self):
        ld = """
        {"@context":"https://schema.org","@type":"Product","name":"戰鬥陀螺 UX-04",
         "offers":{"@type":"Offer","price":"390.00","priceCurrency":"TWD",
                   "availability":"https://schema.org/InStock"}}
        """
        s = FunboxMonitor.parse(html_with_ld(ld), WATCH)
        self.assertEqual(s.price, 390)
        self.assertTrue(s.available)
        self.assertTrue(s.is_original_price)
        self.assertEqual(s.name, "戰鬥陀螺 UX-04")
        self.assertEqual(s.platform, "funbox")
        self.assertEqual(s.url, URL)

    def test_parse_out_of_stock(self):
        ld = """
        {"@type":"Product","name":"UX-04",
         "offers":{"@type":"Offer","price":"390","availability":"https://schema.org/OutOfStock"}}
        """
        s = FunboxMonitor.parse(html_with_ld(ld), WATCH)
        self.assertFalse(s.available)
        self.assertEqual(s.price, 390)

    def test_parse_graph_wrapped(self):
        ld = """
        {"@context":"https://schema.org","@graph":[
           {"@type":"BreadcrumbList"},
           {"@type":"Product","name":"UX-04 in graph",
            "offers":{"@type":"Offer","price":390,"availability":"InStock"}}
        ]}
        """
        s = FunboxMonitor.parse(html_with_ld(ld), WATCH)
        self.assertEqual(s.price, 390)
        self.assertTrue(s.available)
        self.assertEqual(s.name, "UX-04 in graph")

    def test_offers_as_list(self):
        ld = """
        {"@type":"Product","name":"UX-04",
         "offers":[{"@type":"Offer","price":"420","availability":"InStock"}]}
        """
        s = FunboxMonitor.parse(html_with_ld(ld), WATCH)
        self.assertEqual(s.price, 420)
        self.assertTrue(s.available)

    def test_no_ld_json_does_not_crash(self):
        s = FunboxMonitor.parse("<html><body>no ld here</body></html>", WATCH)
        self.assertIsNone(s.price)
        self.assertFalse(s.available)
        self.assertEqual(s.name, "UX-04")  # 退回 product_key

    def test_malformed_ld_json_skipped(self):
        html = html_with_ld("{ this is not valid json }")
        s = FunboxMonitor.parse(html, WATCH)
        self.assertIsNone(s.price)


if __name__ == "__main__":
    unittest.main()
