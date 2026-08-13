"""Funbox 官網 monitor(階段二,已可用 —— 原價第一手)。

Funbox 官網為 SHOPLINE 站型。SHOPLINE 商品頁通常內嵌 schema.org 的
JSON-LD(<script type="application/ld+json">),含 Product 名稱、Offer 的
price 與 availability(InStock / OutOfStock / SoldOut)。用 JSON-LD 解析
比逆向站台私有 JSON 穩定,且對多數 SHOPLINE / 電商站通用。

config 的 item_id 請填「商品頁完整網址」(Funbox 商品連結)。
低頻、遵守 robots.txt、不繞登入牆、只抓公開事實資料。
"""

from __future__ import annotations

import json
import re
from typing import Any, Optional

import requests

from config import SETTINGS, Watch
from monitors.base import ProductSnapshot

_LD_JSON_RE = re.compile(
    r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.IGNORECASE | re.DOTALL,
)


class FunboxMonitor:
    platform = "funbox"

    def __init__(self, session: Optional[requests.Session] = None):
        self._session = session or requests.Session()

    def fetch(self, watches: list[Watch]) -> list[ProductSnapshot]:
        out: list[ProductSnapshot] = []
        for w in watches:
            if w.platform != self.platform or not w.item_id:
                continue
            snap = self._fetch_one(w)
            if snap is not None:
                out.append(snap)
        return out

    # --- 內部 ---------------------------------------------------------------

    def _fetch_one(self, w: Watch) -> Optional[ProductSnapshot]:
        # funbox 的 item_id 即商品頁網址。
        url = w.item_id if w.item_id.startswith("http") else ""
        if not url:
            print(f"[funbox] {w.product_key} 需要商品頁網址當 item_id")
            return None
        try:
            resp = self._session.get(
                url,
                headers={"User-Agent": SETTINGS.user_agent, "Accept": "text/html"},
                timeout=SETTINGS.http_timeout_sec,
            )
            resp.raise_for_status()
            html = resp.text
        except requests.RequestException as exc:
            print(f"[funbox] {url} 取得失敗: {exc}")
            return None
        return self.parse(html, w)

    @staticmethod
    def parse(html: str, w: Watch) -> ProductSnapshot:
        """從商品頁 HTML 的 JSON-LD 抽 Product/Offer。抽成 static 方便測試。"""
        product = _find_product(html)
        offer = _first_offer(product) if product else {}

        price = _to_int(offer.get("price"))
        availability = str(offer.get("availability") or "")
        available = "InStock" in availability or "PreOrder" in availability
        # 沒有 availability 資訊時,退回看有無 price(有價通常代表上架中)。
        if not availability:
            available = price is not None

        name = w.name or str((product or {}).get("name") or w.product_key)
        url = w.item_id

        return ProductSnapshot(
            product_key=w.product_key,
            platform="funbox",
            item_id=w.item_id,
            name=name,
            url=url,
            price=price,
            original_price=w.original_price,
            stock=None,  # JSON-LD 通常不給庫存數
            on_sale_ts=None,
            available=available,
            raw={"availability": availability, "price": offer.get("price")},
        )


# --- JSON-LD 解析小工具 -----------------------------------------------------

def _iter_ld_blocks(html: str):
    for m in _LD_JSON_RE.finditer(html or ""):
        raw = m.group(1).strip()
        try:
            yield json.loads(raw)
        except (ValueError, TypeError):
            continue


def _find_product(html: str) -> Optional[dict]:
    """找出 @type 為 Product 的 JSON-LD 節點(可能被包在 @graph 或陣列裡)。"""
    for block in _iter_ld_blocks(html):
        for node in _flatten(block):
            if _is_type(node, "Product"):
                return node
    return None


def _flatten(block: Any):
    """把 JSON-LD 可能的巢狀(list / @graph)攤平成節點序列。"""
    if isinstance(block, list):
        for item in block:
            yield from _flatten(item)
    elif isinstance(block, dict):
        if "@graph" in block and isinstance(block["@graph"], list):
            for item in block["@graph"]:
                yield from _flatten(item)
        yield block


def _is_type(node: Any, type_name: str) -> bool:
    if not isinstance(node, dict):
        return False
    t = node.get("@type")
    if isinstance(t, list):
        return type_name in t
    return t == type_name


def _first_offer(product: dict) -> dict:
    offers = product.get("offers")
    if isinstance(offers, list):
        return offers[0] if offers and isinstance(offers[0], dict) else {}
    if isinstance(offers, dict):
        return offers
    return {}


def _to_int(val: Any) -> Optional[int]:
    if val is None:
        return None
    try:
        # 價格可能是 "390.00" / "390" / 390
        return int(float(str(val).replace(",", "").strip()))
    except (ValueError, TypeError):
        return None
