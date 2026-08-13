"""PChome 24h monitor(階段二,已可用)。

PChome 有公開 JSON API:
    單品:https://ecapi.pchome.com.tw/ecshop/prodapi/v2/prod/{id}&fields=Id,Name,Price,Qty,ButtonType,SaleStatus
          回應是以商品 id 為鍵的物件,值含 Price({P:售價, M:市價})、Qty(庫存)、ButtonType/SaleStatus。
    搜尋:https://ecshweb.pchome.com.tw/search/v3.3/all/results?q=beyblade&page=1&sort=sale/dc

設計原則同 momo:防呆解析(欄位缺漏不炸整輪)、低頻、只查設定清單裡的單品。
config 的 item_id 請填 PChome 商品 id(如 "DGAJ8T-A900AVFV7")。
"""

from __future__ import annotations

from typing import Any, Optional

import requests

from config import SETTINGS, Watch
from monitors.base import ProductSnapshot

API_PROD = (
    "https://ecapi.pchome.com.tw/ecshop/prodapi/v2/prod/{id}"
    "&fields=Id,Name,Price,Qty,ButtonType,SaleStatus"
)
PROD_PAGE = "https://24h.pchome.com.tw/prod/{id}"


class PChomeMonitor:
    platform = "pchome"

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
            resp = self._session.get(
                API_PROD.format(id=w.item_id),
                headers={
                    "User-Agent": SETTINGS.user_agent,
                    "Accept": "application/json",
                    "Referer": PROD_PAGE.format(id=w.item_id),
                },
                timeout=SETTINGS.http_timeout_sec,
            )
            resp.raise_for_status()
            data = resp.json()
        except (requests.RequestException, ValueError) as exc:
            print(f"[pchome] {w.item_id} 取得失敗: {exc}")
            return None
        return self.parse(data, w)

    @staticmethod
    def parse(data: Any, w: Watch) -> ProductSnapshot:
        """把 PChome 回應解析成統一 snapshot。抽成 static 方便單元測試餵 mock。

        回應通常是 {"<id>": {...}};也容忍直接就是內層 dict。
        """
        rec: dict = {}
        if isinstance(data, dict):
            if w.item_id in data and isinstance(data[w.item_id], dict):
                rec = data[w.item_id]
            elif "Id" in data or "Price" in data:  # 已是內層
                rec = data
            elif data:  # 取第一個值
                first = next(iter(data.values()))
                rec = first if isinstance(first, dict) else {}

        price, market_price = _parse_price(rec.get("Price"))
        stock = _to_int(rec.get("Qty"))

        # 原價:優先用設定值,沒有就退回 PChome 市價(M)。
        original_price = w.original_price if w.original_price is not None else market_price

        if stock is not None:
            available = stock > 0
        else:
            available = price is not None and _buttontype_buyable(rec.get("ButtonType"))

        name = w.name or str(rec.get("Name") or w.item_id)

        return ProductSnapshot(
            product_key=w.product_key,
            platform="pchome",
            item_id=w.item_id,
            name=name,
            url=PROD_PAGE.format(id=w.item_id),
            price=price,
            original_price=original_price,
            stock=stock,
            on_sale_ts=None,  # PChome 單品 API 不給開賣時間戳
            available=available,
            raw={k: rec.get(k) for k in ("Id", "Price", "Qty", "ButtonType", "SaleStatus")},
        )


# --- 解析小工具 -------------------------------------------------------------

def _to_int(val: Any) -> Optional[int]:
    if val is None:
        return None
    try:
        return int(str(val).replace(",", "").strip())
    except (ValueError, TypeError):
        return None


def _parse_price(price: Any) -> tuple[Optional[int], Optional[int]]:
    """回 (售價P, 市價M)。Price 可能是 {'P':390,'M':420} 或純數字。"""
    if isinstance(price, dict):
        return _to_int(price.get("P")), _to_int(price.get("M"))
    return _to_int(price), None


def _buttontype_buyable(bt: Any) -> bool:
    """ButtonType 為空或明顯的不可買狀態時視為不可購買。

    PChome ButtonType 語意會變,這裡保守處理:沒值就當不可買。
    有庫存(Qty)時本來就會走 Qty 判斷,這條只是 Qty 缺失時的後備。
    """
    if bt in (None, "", "0"):
        return False
    return True
