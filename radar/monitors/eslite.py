"""誠品線上(eslite)發現式 monitor —— 掃搜尋頁抓 Beyblade X 新上架。

⚠️ 選擇器需以真實 HTML 校準:此環境無法連外,eslite 的搜尋結果實際結構
   請用瀏覽器 DevTools 確認(見 README「校準」段)。程式已用多重策略防呆:
     1) __NEXT_DATA__ 內嵌 JSON(eslite 為 Next.js 站,通常最完整)
     2) schema.org JSON-LD 的 ItemList / Product
     3) 最後退回:抓 /product/{id} 連結
   任一策略成功即用;全失敗回空清單,不炸整輪。

「新上架」判斷:掃到的商品交給 calendar_db,首次掃描建立基準線(不通知),
之後出現的新 item_id 才會以「新商品上架」通知你(run.py 負責首輪 seeding)。
"""

from __future__ import annotations

import json
import re
from typing import Any, Iterator, Optional

from config import SETTINGS, Search
from monitors.base import ProductSnapshot
from monitors.discovery import DiscoveryMonitor

SEARCH_URL = "https://www.eslite.com/search?keyword={kw}"
PRODUCT_URL = "https://www.eslite.com/product/{id}"

_NEXT_DATA_RE = re.compile(
    r'<script[^>]*id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>',
    re.IGNORECASE | re.DOTALL,
)
_LD_JSON_RE = re.compile(
    r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.IGNORECASE | re.DOTALL,
)
_PRODUCT_LINK_RE = re.compile(r'/product/(\d{6,})')
# 型號代碼:BX-10 / UX-04 / CX-05 …(用來當 product_key,順便跨平台合併)
_MODEL_RE = re.compile(r'\b([A-Z]{2,3}-\d{1,3})\b')


class EsliteMonitor(DiscoveryMonitor):
    platform = "eslite"

    def _search(self, search: Search) -> list[ProductSnapshot]:
        resp = self._session.get(
            SEARCH_URL.format(kw=search.keyword),
            headers={"User-Agent": SETTINGS.user_agent, "Accept": "text/html"},
            timeout=SETTINGS.http_timeout_sec,
        )
        resp.raise_for_status()
        return self.parse_search(resp.text, search)

    @classmethod
    def parse_search(cls, html: str, search: Search) -> list[ProductSnapshot]:
        """把搜尋頁 HTML 解析成 ProductSnapshot 清單。抽成 classmethod 方便測試。"""
        products = cls.extract_products(html)
        snaps: list[ProductSnapshot] = []
        seen: set[str] = set()
        for p in products:
            snap = cls.to_snapshot(p, search)
            if snap is None or snap.item_id in seen:
                continue
            seen.add(snap.item_id)
            snaps.append(snap)
        return snaps

    @staticmethod
    def extract_products(html: str) -> list[dict]:
        """多重策略抽出商品原始 dict(id/name/url/price/available)。"""
        for strategy in (_from_next_data, _from_jsonld, _from_links):
            items = strategy(html or "")
            if items:
                return items
        return []

    @staticmethod
    def to_snapshot(p: dict, search: Search) -> Optional[ProductSnapshot]:
        item_id = _clean_id(p.get("id"))
        if not item_id:
            return None
        name = str(p.get("name") or "").strip() or f"eslite 商品 {item_id}"
        # 只留跟 Beyblade 有關的,避免搜尋雜訊(關鍵字命中或型號命中)。
        if not _looks_beyblade(name, search.keyword):
            return None
        model = _model_code(name)
        return ProductSnapshot(
            product_key=model or item_id,
            platform="eslite",
            item_id=item_id,
            name=name,
            url=str(p.get("url") or PRODUCT_URL.format(id=item_id)),
            price=_to_int(p.get("price")),
            original_price=None,     # 誠品搜尋頁不一定有原價,未知
            stock=None,
            on_sale_ts=None,
            available=bool(p.get("available", True)),  # 出現在搜尋結果視為上架
            raw={"src": "eslite-search"},
        )


# --- 抽取策略 ---------------------------------------------------------------

def _from_next_data(html: str) -> list[dict]:
    m = _NEXT_DATA_RE.search(html)
    if not m:
        return []
    try:
        data = json.loads(m.group(1))
    except (ValueError, TypeError):
        return []
    out: list[dict] = []
    seen: set[str] = set()
    for node in _walk_product_like(data):
        pid = _clean_id(node.get("_id"))
        if pid and pid not in seen:
            seen.add(pid)
            out.append(node)
    return out


def _walk_product_like(obj: Any) -> Iterator[dict]:
    """遞迴走訪 JSON,找出「像商品」的 dict(有 id 類與 name 類欄位)。"""
    if isinstance(obj, dict):
        pid = _first(obj, ("id", "productId", "product_id", "sku", "code", "itemId"))
        name = _first(obj, ("name", "title", "productName", "product_name"))
        if pid is not None and name:
            yield {
                "_id": pid,
                "id": pid,
                "name": name,
                "price": _first(obj, ("price", "salePrice", "sellingPrice", "sell_price", "memberPrice")),
                "url": _first(obj, ("url", "link", "permalink")),
            }
        for v in obj.values():
            yield from _walk_product_like(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _walk_product_like(v)


def _from_jsonld(html: str) -> list[dict]:
    out: list[dict] = []
    for m in _LD_JSON_RE.finditer(html):
        try:
            block = json.loads(m.group(1).strip())
        except (ValueError, TypeError):
            continue
        for node in _flatten_ld(block):
            if _is_type(node, "Product"):
                offer = node.get("offers") or {}
                if isinstance(offer, list):
                    offer = offer[0] if offer else {}
                out.append({
                    "id": node.get("sku") or node.get("productID") or _id_from_url(node.get("url")),
                    "name": node.get("name"),
                    "price": (offer or {}).get("price"),
                    "url": node.get("url"),
                    "available": "InStock" in str((offer or {}).get("availability") or "InStock"),
                })
    return [p for p in out if p.get("id")]


def _from_links(html: str) -> list[dict]:
    out: list[dict] = []
    seen: set[str] = set()
    for pid in _PRODUCT_LINK_RE.findall(html):
        if pid in seen:
            continue
        seen.add(pid)
        out.append({"id": pid, "name": "", "url": PRODUCT_URL.format(id=pid)})
    return out


# --- JSON-LD 走訪(與 funbox 同套邏輯,獨立一份避免耦合) -------------------

def _flatten_ld(block: Any) -> Iterator[dict]:
    if isinstance(block, list):
        for item in block:
            yield from _flatten_ld(item)
    elif isinstance(block, dict):
        graph = block.get("@graph")
        if isinstance(graph, list):
            for item in graph:
                yield from _flatten_ld(item)
        # ItemList → itemListElement → item
        elements = block.get("itemListElement")
        if isinstance(elements, list):
            for el in elements:
                if isinstance(el, dict):
                    yield from _flatten_ld(el.get("item", el))
        yield block


def _is_type(node: Any, type_name: str) -> bool:
    if not isinstance(node, dict):
        return False
    t = node.get("@type")
    return type_name in t if isinstance(t, list) else t == type_name


# --- 小工具 -----------------------------------------------------------------

def _first(d: dict, keys: tuple[str, ...]) -> Any:
    for k in keys:
        v = d.get(k)
        if v not in (None, "", [], {}):
            return v
    return None


def _clean_id(val: Any) -> str:
    if val is None:
        return ""
    return re.sub(r"\s+", "", str(val))


def _id_from_url(url: Any) -> str:
    if not url:
        return ""
    m = _PRODUCT_LINK_RE.search(str(url))
    return m.group(1) if m else ""


def _model_code(name: str) -> Optional[str]:
    m = _MODEL_RE.search(name or "")
    return m.group(1) if m else None


def _looks_beyblade(name: str, keyword: str) -> bool:
    low = (name or "").lower()
    if "beyblade" in low or "戰鬥陀螺" in name or "戰鬥盤" in name or "發射器" in name:
        return True
    kw = (keyword or "").lower().strip()
    return bool(kw) and kw in low


def _to_int(val: Any) -> Optional[int]:
    if val is None:
        return None
    try:
        return int(float(str(val).replace(",", "").replace("NT$", "").replace("$", "").strip()))
    except (ValueError, TypeError):
        return None
