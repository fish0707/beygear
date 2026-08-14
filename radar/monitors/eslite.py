"""誠品線上(eslite)發現式 monitor —— 走官方前端在用的 athena API。

為什麼不再解析 HTML:
    eslite 是 Vue 單頁應用。實測(見 tools/probe_sites.py)搜尋頁和兩個不同的
    商品頁回的是**同一份 13,583 bytes 的空殼**,沒有 __NEXT_DATA__、沒有
    ld+json、沒有任何 /product/ 連結 —— 內容全部是前端用 XHR 抓回來再渲染的。
    舊版解析器對著 HTML 找選擇器,所以永遠掃到 0 筆、價格永遠 NT$0。
    它的 JS bundle 自己寫著 API 位置,照著呼叫就拿得到乾淨的 JSON:

        GET https://athena.eslite.com/api/v2/search?keyword=…&page=1&per_page=20
        → {"facets": …, "hits": {"found": 40, "hit": [{"id": …, "fields": {
             "name", "final_price", "mprice", "stock", "url", …}}]}}

    (單品端點 /api/v3/products/<id> 回空陣列、帶參數則回 500,所以只用搜尋。)

注意誠品賣的是書:「戰鬥陀螺」在誠品幾乎都是攻略本、漫畫與附錄雜誌,不是
玩具本體。留著它是為了掃到「附陀螺」的雜誌與攻略本這類週邊上架。
"""

from __future__ import annotations

import re
from typing import Any, Optional

from config import ORIGINAL_PRICES, SETTINGS, Search
from monitors.base import ProductSnapshot
from monitors.discovery import DiscoveryMonitor, looks_relevant

API_URL = "https://athena.eslite.com/api/v2/search"
PRODUCT_URL = "https://www.eslite.com/product/{id}"
PER_PAGE = 20

_MODEL_RE = re.compile(r"(?<![A-Za-z0-9])((?:BX|UX|CX)-\d{2})(?![0-9])")


class EsliteMonitor(DiscoveryMonitor):
    platform = "eslite"

    def _search(self, search: Search) -> list[ProductSnapshot]:
        resp = self._session.get(
            API_URL,
            params={"keyword": search.keyword, "page": 1, "per_page": PER_PAGE},
            headers={
                "User-Agent": SETTINGS.user_agent,
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
                "Origin": "https://www.eslite.com",
                "Referer": "https://www.eslite.com/",
            },
            timeout=SETTINGS.http_timeout_sec,
        )
        resp.raise_for_status()
        return self.parse_search(resp.json())

    @classmethod
    def parse_search(cls, payload: dict) -> list[ProductSnapshot]:
        """athena 搜尋回應 → ProductSnapshot 清單。抽出來方便用真實樣本測試。"""
        hits = ((payload or {}).get("hits") or {}).get("hit") or []
        snaps: list[ProductSnapshot] = []
        seen: set[str] = set()
        for hit in hits:
            snap = cls.to_snapshot(hit)
            if snap is None or snap.item_id in seen:
                continue
            seen.add(snap.item_id)
            snaps.append(snap)
        return snaps

    @classmethod
    def to_snapshot(cls, hit: dict) -> Optional[ProductSnapshot]:
        item_id = str(hit.get("id") or "").strip()
        fields = hit.get("fields") or {}
        name = str(fields.get("name") or "").strip()
        if not item_id or not name or not looks_relevant(name):
            return None  # 誠品的模糊比對會帶回不相干的商品(例:公仔收納盒)

        price = _to_int(fields.get("final_price"))
        stock = _to_int(fields.get("stock"))
        key = cls.product_key_for(name, item_id)
        # mprice 是誠品標示的定價;設定檔若有建議售價則以設定為準。
        original = ORIGINAL_PRICES.get(key) or _to_int(fields.get("mprice"))

        return ProductSnapshot(
            product_key=key,
            platform="eslite",
            item_id=item_id,
            name=name,
            url=str(fields.get("url") or PRODUCT_URL.format(id=item_id)),
            price=price,
            original_price=original,
            stock=stock,
            available=bool(stock) if stock is not None else price is not None,
            raw={k: fields.get(k) for k in ("final_price", "mprice", "stock", "eslite_sn")},
        )

    @staticmethod
    def product_key_for(name: str, item_id: str) -> str:
        """型號當合併鍵。誠品多半是書,抓不到型號就用它自己的商品編號。"""
        models = sorted(set(_MODEL_RE.findall(name.upper())))
        if len(models) == 1:
            return models[0]
        return f"eslite-{item_id}"


def _to_int(val: Any) -> Optional[int]:
    if val is None or val == "":
        return None
    try:
        return int(str(val).replace(",", "").strip())
    except (ValueError, TypeError):
        return None
