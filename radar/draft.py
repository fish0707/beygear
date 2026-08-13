"""貼文草稿生成(階段三,已可用)。

產生「自寫摘要」貼文 + 蝦皮分潤/導流連結,供你審核後手動貼到 Threads/IG/FB。
重要合規點:
    - 只用自寫摘要(價格/開賣時間等事實),不複製他人原圖原文。
    - 分潤連結明示「內含推廣」。
    - 蝦皮分潤 ID 未設定時,退回純導流的蝦皮搜尋連結(無分潤參數)。
"""

from __future__ import annotations

import datetime as _dt
import urllib.parse

from calendar_db import EventRow, RESTOCKED
from config import SETTINGS


def shopee_link(keyword: str) -> str:
    """蝦皮搜尋連結;有分潤 ID 就帶上,無則純導流。"""
    q = urllib.parse.quote(keyword)
    base = f"https://shopee.tw/search?keyword={q}"
    if SETTINGS.shopee_affiliate_id:
        # 註:實際分潤連結格式以蝦皮分潤後台產生的短連結為準;
        # 此處以 utm 佔位,過審後改成後台連結。
        base += f"&af_id={urllib.parse.quote(SETTINGS.shopee_affiliate_id)}"
    return base


def generate_draft(event: EventRow) -> str:
    """依事件生成一則貼文草稿(繁中,自寫摘要)。"""
    is_restock = event.status == RESTOCKED
    hook = "♻️ 原價補貨快閃" if is_restock else "📡 Beyblade X 原價情報"

    parts: list[str] = [f"{hook}｜{event.name}"]

    facts: list[str] = []
    if event.price is not None:
        tag = "（原價）" if event.is_original_price else ""
        facts.append(f"售價 NT${event.price:,}{tag}")
    if event.on_sale_ts is not None:
        facts.append(f"開賣 {_fmt_ts(event.on_sale_ts)}")
    if event.stock is not None:
        facts.append(f"庫存 {event.stock}")
    if facts:
        parts.append("・".join(facts))

    parts.append("手滑前先看有沒有原價，加價轉賣的先跳過 👀")

    kw = event.name.split("（")[0].strip() or "Beyblade X"
    parts.append(f"👉 蝦皮找同款：{shopee_link(kw)}")
    if event.url:
        parts.append(f"（{event.platform} 商品頁：{event.url}）")

    parts.append("—")
    parts.append("※ 本文含推廣連結，透過連結購買我可能獲得分潤。")

    return "\n".join(parts)


def _fmt_ts(ts: int) -> str:
    tz = _dt.timezone(_dt.timedelta(hours=8))
    return _dt.datetime.fromtimestamp(ts, tz).strftime("%m/%d %H:%M")


if __name__ == "__main__":  # 快速手測
    from calendar_db import EventRow as _E
    demo = _E(
        product_key="UX-04", platform="momo", item_id="15462754",
        name="Beyblade X UX-04", url="https://example.com/goods/15462754",
        price=390, original_price=390, is_original_price=True, stock=5,
        on_sale_ts=int(_dt.datetime(2026, 7, 26, 11, 0).timestamp()),
        available=True, status="RESTOCKED", first_seen_at=0, last_updated_at=0,
    )
    print(generate_draft(demo))
