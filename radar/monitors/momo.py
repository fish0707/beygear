"""momo 購物網 monitor —— 掃搜尋頁,抓目前在架的 Beyblade X 商品。

為什麼是「搜尋式」而不是「盯商品碼」:
    原本的做法是 POST /api/moecapp/getGoodsRealTimeInfo 查單一 goodsCode。
    實測(GitHub Actions runner,見 tools/probe_sites.py)那條路是死的:
        - 商品頁回 200,但內容是 momo 的擋機器人頁(title「Mobile管理訊息」),
          沒有價格、沒有 ld+json。
        - 即時資訊 API 回 200 但 {"success":false,"resultMessage":"查無商品"},
          換 payload、換 header、先養 cookie 都一樣。(把欄位名改掉會回
          「goodsCode is empty!!!」,可見端點活著、也讀得到我們,是它不給。)
        - apisearch.momoshop.com.tw 直接 403 Access Denied。
    但**搜尋頁是開的**,而且整包商品資料就內嵌在裡面:
        "goodsInfoList":[{"goodsCode":"15162670",
          "goodsName":"【TAKARA TOMY】BEYBLADE X 戰鬥陀螺X UX-15 鮫鯊狂鱗改造組",
          "goodsPrice":"$$795","goodsPriceOri":"$$795","goodsStock":"168", …}]
    所以改成掃搜尋頁。這也比盯單品好:新品一上架就會被掃到,不必先知道商品碼。

只收 momo 自營商品(純數字 goodsCode)。搜尋結果裡另有一批 "TP…" 開頭的
摩天商城賣家商品,它們的商品頁網址規則尚未實測,寧可不收也不要給出錯的連結;
而且雷達要盯的是「原價開賣」,自營商品正是原價那一側。
"""

from __future__ import annotations

import json
import re
from typing import Any, Optional
from urllib.parse import quote

from config import ORIGINAL_PRICES, SETTINGS, Search
from monitors.base import ProductSnapshot
from monitors.discovery import DiscoveryMonitor

SEARCH_URL = "https://www.momoshop.com.tw/search/searchShop.jsp?keyword={kw}"
PRODUCT_URL = "https://www.momoshop.com.tw/product/{code}"

# Beyblade X 的型號規則就是 BX/UX/CX + 兩位數。限定這三個字首,才不會把
# 「5-70DB」「3-80S」這類齒輪規格或其他品牌代號誤判成型號。
_MODEL_RE = re.compile(r"(?<![A-Za-z0-9])((?:BX|UX|CX)-\d{2})(?![0-9])")
_GOODS_LIST_RE = re.compile(r'"goodsInfoList"\s*:\s*\[')
_NUMERIC_CODE_RE = re.compile(r"^\d{6,}$")


class MomoMonitor(DiscoveryMonitor):
    platform = "momo"

    def _search(self, search: Search) -> list[ProductSnapshot]:
        resp = self._session.get(
            SEARCH_URL.format(kw=quote(search.keyword)),
            headers={
                "User-Agent": SETTINGS.user_agent,
                "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
                "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
            },
            timeout=SETTINGS.http_timeout_sec,
        )
        resp.raise_for_status()
        return self.parse_search(resp.text)

    @classmethod
    def parse_search(cls, html: str) -> list[ProductSnapshot]:
        """搜尋頁 HTML → ProductSnapshot 清單。抽成 classmethod 方便用真實樣本測試。"""
        snaps: list[ProductSnapshot] = []
        seen: set[str] = set()
        for goods in cls.extract_goods(html):
            snap = cls.to_snapshot(goods)
            if snap is None or snap.item_id in seen:
                continue
            seen.add(snap.item_id)
            snaps.append(snap)
        return snaps

    @staticmethod
    def extract_goods(html: str) -> list[dict]:
        """把 goodsInfoList 陣列從頁面裡挖出來。

        這包 JSON 是塞在 JavaScript 字串裡的,所以引號是跳脫過的;先還原,再讓
        JSON decoder 自己找到陣列結尾 —— 正規表達式沒辦法可靠地配對巢狀括號。
        """
        text = html.replace('\\"', '"')
        out: list[dict] = []
        for m in _GOODS_LIST_RE.finditer(text):
            start = text.index("[", m.end() - 1)
            try:
                arr, _ = json.JSONDecoder().raw_decode(text[start:])
            except ValueError:
                continue  # 這段壞掉就跳過,別讓整輪掛掉
            if isinstance(arr, list):
                out.extend(x for x in arr if isinstance(x, dict))
        return out

    @classmethod
    def to_snapshot(cls, goods: dict) -> Optional[ProductSnapshot]:
        code = str(goods.get("goodsCode") or "").strip()
        if not _NUMERIC_CODE_RE.match(code):
            return None  # 摩天商城賣家商品,網址規則未驗證,不收

        name = str(goods.get("goodsName") or "").strip()
        if not name:
            return None

        price = _money(goods.get("goodsPrice")) or _money(
            _dig(goods, "goodsPriceModel", "basePrice", "price")
        )
        stock = _to_int(goods.get("goodsStock"))
        key = cls.product_key_for(name, code)

        # 已知建議售價優先(設定檔維護);沒有就退回 momo 自己標的原價。
        original = ORIGINAL_PRICES.get(key) or _money(goods.get("goodsPriceOri"))

        return ProductSnapshot(
            product_key=key,
            platform="momo",
            item_id=code,
            name=name,
            url=PRODUCT_URL.format(code=code),
            price=price,
            original_price=original,
            stock=stock,
            available=bool(stock) if stock is not None else price is not None,
            raw={k: goods.get(k) for k in
                 ("goodsCode", "goodsPrice", "goodsPriceOri", "goodsStock")},
        )

    @staticmethod
    def product_key_for(name: str, code: str) -> str:
        """型號當合併鍵,好讓同一顆陀螺在不同平台併成一條時間軸。

        套裝商品名稱裡會同時出現好幾個型號(「UX-03 魔導神杖 … 鳳凰飛翼BX-23」),
        硬挑第一個會把套裝的價格混進單品的歷史裡,所以多型號一律另立為套裝。
        """
        models = sorted(set(_MODEL_RE.findall(name.upper())))
        if len(models) == 1:
            return models[0]
        return f"bundle-{code}"


# --- 解析小工具 -------------------------------------------------------------

def _dig(d: dict, *keys: str) -> Any:
    cur: Any = d
    for k in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(k)
    return cur


def _money(val: Any) -> Optional[int]:
    """「$$1,199」「795」→ 1199 / 795。抓不到回 None。"""
    if val is None:
        return None
    m = re.search(r"(\d[\d,]*)", str(val))
    if not m:
        return None
    try:
        return int(m.group(1).replace(",", ""))
    except ValueError:
        return None


def _to_int(val: Any) -> Optional[int]:
    if val is None or val == "":
        return None
    try:
        return int(str(val).replace(",", "").strip())
    except (ValueError, TypeError):
        return None
