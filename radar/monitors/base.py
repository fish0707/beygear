"""Monitor 共用型別與介面。

所有 monitor 只抓「公開事實資料」(上架 / 售價 / 是否原價 / 庫存 / 開賣時間戳),
不繞登入牆、不整批複製對方資料庫。回傳統一的 ProductSnapshot。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Protocol

from config import Watch


@dataclass
class ProductSnapshot:
    """一次觀測到的商品即時狀態(平台無關的統一格式)。"""

    product_key: str          # 跨平台合併鍵(例:"UX-04")
    platform: str             # "momo" | "pchome" | "funbox" | "manual"
    item_id: str              # 平台商品碼
    name: str
    url: str
    price: Optional[int] = None            # NT$;未知為 None
    original_price: Optional[int] = None   # 已知原價(來自設定)
    stock: Optional[int] = None            # 庫存數;未知為 None
    on_sale_ts: Optional[int] = None       # 開賣 unix timestamp(秒);未知為 None
    available: bool = False                # 目前是否可購買 / 已上架
    raw: dict = field(default_factory=dict)  # 原始回應片段(除錯用)

    @property
    def is_original_price(self) -> Optional[bool]:
        """觀測售價是否為「原價或更低」。

        原價(建議售價)來自設定;沒有已知原價或沒有售價時回 None(未知)。
        「補到原價」是我們最想通知的訊號 —— 秒殺後常見加價轉賣,回到原價才值得搶。
        """
        if self.price is None or self.original_price is None:
            return None
        return self.price <= self.original_price


class Monitor(Protocol):
    """monitor 介面:吃一份 Watch 清單,回傳觀測到的 ProductSnapshot。"""

    platform: str

    def fetch(self, watches: list[Watch]) -> list[ProductSnapshot]:
        ...
