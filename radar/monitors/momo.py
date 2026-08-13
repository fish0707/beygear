"""momo 購物網 monitor(MVP 主力,已逆向端點)。

手法(本 session 前置已驗證,可能改版,上線前用 DevTools Network 再確認一次):
    POST https://www.momoshop.com.tw/api/moecapp/getGoodsRealTimeInfo
    body(JSON): {"goodsCode": "<商品碼>"}
    回應重點欄位(位於 rtnGoodsData):
        - onSaleTimestamp          開賣時間戳(毫秒)
        - goodsStock               庫存
        - goodsPaymentDescription  售價/付款說明字串
        - (價格相關欄位命名各版本不同,這裡用多個候選鍵防呆)

設計原則:
    - 防呆解析:momo 會改欄位,任何欄位缺漏都不應炸掉整輪,回傳能拿到多少算多少。
    - 低頻:由 run.py 控制輪詢間隔,這裡不自帶迴圈。
    - 不繞登入牆、不整批抓取,只查設定清單裡的單品。
"""

from __future__ import annotations

import re
from typing import Any, Optional

import requests

from config import SETTINGS, Watch
from monitors.base import ProductSnapshot

API_URL = "https://www.momoshop.com.tw/api/moecapp/getGoodsRealTimeInfo"
GOODS_URL = "https://www.momoshop.com.tw/goods/GoodsDetail.jsp?i_code={code}"


class MomoMonitor:
    platform = "momo"

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
        try:
            resp = self._session.post(
                API_URL,
                json={"goodsCode": w.item_id},
                headers={
                    "User-Agent": SETTINGS.user_agent,
                    "Content-Type": "application/json;charset=UTF-8",
                    "Referer": GOODS_URL.format(code=w.item_id),
                    "Accept": "application/json",
                },
                timeout=SETTINGS.http_timeout_sec,
            )
            resp.raise_for_status()
            data = resp.json()
        except (requests.RequestException, ValueError) as exc:
            # 網路 / JSON 解析失敗 → 這一輪略過該商品,不影響其他商品。
            print(f"[momo] {w.item_id} 取得失敗: {exc}")
            return None

        return self.parse(data, w)

    @staticmethod
    def parse(data: dict, w: Watch) -> ProductSnapshot:
        """把 momo 回應解析成統一 snapshot。抽成 static 方便單元測試餵 mock。"""
        goods = data.get("rtnGoodsData") or data.get("goodsData") or {}

        stock = _first_int(goods, ["goodsStock", "stock", "qty"])
        on_sale_ts = _to_unix_seconds(
            _first(goods, ["onSaleTimestamp", "onSaleTime", "saleTimestamp"])
        )
        price = _first_int(goods, ["goodsPrice", "price", "salePrice"])
        if price is None:
            price = _price_from_text(
                _first(goods, ["goodsPaymentDescription", "paymentDescription"])
            )

        # 是否已上架 / 可購買:有庫存即視為可購買;沒有庫存欄位就退回看有無售價。
        if stock is not None:
            available = stock > 0
        else:
            available = price is not None

        name = w.name or str(_first(goods, ["goodsName", "name"]) or w.item_id)

        return ProductSnapshot(
            product_key=w.product_key,
            platform="momo",
            item_id=w.item_id,
            name=name,
            url=GOODS_URL.format(code=w.item_id),
            price=price,
            original_price=w.original_price,
            stock=stock,
            on_sale_ts=on_sale_ts,
            available=available,
            raw={k: goods.get(k) for k in list(goods)[:12]},  # 只留前幾欄除錯
        )


# --- 解析小工具 -------------------------------------------------------------

def _first(d: dict, keys: list[str]) -> Any:
    for k in keys:
        if k in d and d[k] not in (None, ""):
            return d[k]
    return None


def _first_int(d: dict, keys: list[str]) -> Optional[int]:
    val = _first(d, keys)
    if val is None:
        return None
    try:
        return int(str(val).replace(",", "").strip())
    except (ValueError, TypeError):
        return None


def _to_unix_seconds(val: Any) -> Optional[int]:
    """momo 的時間戳常為毫秒;>1e12 視為毫秒轉秒。也接受純數字字串。"""
    if val is None:
        return None
    try:
        n = int(str(val).strip())
    except (ValueError, TypeError):
        return None
    if n <= 0:
        return None
    return n // 1000 if n > 10_000_000_000 else n


def _price_from_text(text: Any) -> Optional[int]:
    """從「$390」「售價 390 元」之類字串抽出第一個數字。"""
    if not text:
        return None
    m = re.search(r"(\d[\d,]*)", str(text))
    if not m:
        return None
    try:
        return int(m.group(1).replace(",", ""))
    except ValueError:
        return None
