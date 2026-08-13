"""發現式監控(掃描搜尋頁抓新品)的共用基底。

跟一般 monitor 不同:
    - 一般 monitor:盯「已知商品碼」(config.WATCHES)。
    - 發現式 monitor:拿關鍵字掃某商城搜尋/分類頁 → 撈出目前所有 Beyblade X 商品
      → 交給行事曆比對,「以前沒看過」的就是新上架。

每個商城一個子類別(一站一個 adapter)。子類別只要實作 `_search()`。
"""

from __future__ import annotations

from typing import Optional

import requests

from config import Search
from monitors.base import ProductSnapshot


class DiscoveryMonitor:
    platform: str = ""

    def __init__(self, session: Optional[requests.Session] = None):
        self._session = session or requests.Session()

    def fetch_searches(self, searches: list[Search]) -> list[ProductSnapshot]:
        out: list[ProductSnapshot] = []
        for s in searches:
            if s.platform != self.platform:
                continue
            try:
                out.extend(self._search(s))
            except Exception as exc:  # 單一關鍵字失敗不拖垮整輪
                print(f"[{self.platform}] 搜尋「{s.keyword}」失敗: {exc}")
        return out

    def _search(self, search: Search) -> list[ProductSnapshot]:  # pragma: no cover - 由子類別實作
        raise NotImplementedError
