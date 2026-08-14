"""發現式監控(掃描搜尋頁抓新品)的共用基底。

跟一般 monitor 不同:
    - 一般 monitor:盯「已知商品碼」(config.WATCHES)。
    - 發現式 monitor:拿關鍵字掃某商城搜尋/分類頁 → 撈出目前所有 Beyblade X 商品
      → 交給行事曆比對,「以前沒看過」的就是新上架。

每個商城一個子類別(一站一個 adapter)。子類別只要實作 `_search()`。
"""

from __future__ import annotations

import re
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


# 搜尋關鍵字會掃到別的東西:momo 搜「戰鬥陀螺」會回「爆丸戰鬥場」(BAKUGAN,
# 完全不同的玩具),誠品會回「享樂趣加大貨櫃公仔盒」。這些混進來不只是雜訊 ——
# 爆丸那筆一度成為首頁的「最低有貨價」,等於用一個不相干的商品誤導讀者。
#
# 判斷標準保守:名稱要嘛提到陀螺 / beyblade,要嘛帶有 Beyblade X 的型號代碼。
_RELEVANT_RE = re.compile(r"陀螺|beyblade|(?<![A-Za-z0-9])(?:BX|UX|CX)-\d{2}(?![0-9])",
                          re.IGNORECASE)


def looks_relevant(name: str) -> bool:
    """這個商品名稱看起來真的跟 Beyblade 有關嗎。"""
    return bool(_RELEVANT_RE.search(name or ""))
