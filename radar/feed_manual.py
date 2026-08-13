"""人工餵料(階段二,已可用)。

超商限量、誠品、官方粉專公告等「難自動抓」的情報,用同一格式寫進行事曆,
走與自動 monitor 完全相同的 upsert / 狀態機 / 通知路徑。

用法:
    python feed_manual.py \
        --key UX-05 --platform seven --name "UX-05 超商限量" \
        --price 420 --original-price 390 \
        --on-sale "2026-08-01 00:00" --stock 30 \
        --url "https://..." --available

    # 不帶 --available 表示尚未開賣(預告)。
"""

from __future__ import annotations

import argparse
import datetime as _dt

from calendar_db import Calendar
from config import SETTINGS
from monitors.base import ProductSnapshot
from notify import Notifier


def parse_on_sale(text: str | None) -> int | None:
    if not text:
        return None
    tz = _dt.timezone(_dt.timedelta(hours=8))
    dt = _dt.datetime.strptime(text, "%Y-%m-%d %H:%M").replace(tzinfo=tz)
    return int(dt.timestamp())


def build_snapshot(args: argparse.Namespace) -> ProductSnapshot:
    return ProductSnapshot(
        product_key=args.key,
        platform=args.platform,
        item_id=args.item_id or args.key,
        name=args.name,
        url=args.url or "",
        price=args.price,
        original_price=args.original_price,
        stock=args.stock,
        on_sale_ts=parse_on_sale(args.on_sale),
        available=args.available,
        raw={"source": "manual"},
    )


def main() -> None:
    p = argparse.ArgumentParser(description="手動把一筆情報餵進行事曆")
    p.add_argument("--key", required=True, help="product_key(跨平台合併鍵,如 UX-05)")
    p.add_argument("--platform", required=True, help="平台標籤(如 seven / eslite / manual)")
    p.add_argument("--name", required=True, help="商品名稱")
    p.add_argument("--item-id", default="", help="平台商品碼(留空則用 --key)")
    p.add_argument("--url", default="", help="商品/公告連結")
    p.add_argument("--price", type=int, default=None, help="售價 NT$")
    p.add_argument("--original-price", type=int, default=None, help="已知原價 NT$")
    p.add_argument("--stock", type=int, default=None, help="庫存")
    p.add_argument("--on-sale", default=None, help="開賣時間 'YYYY-MM-DD HH:MM'(台灣時間)")
    p.add_argument("--available", action="store_true", help="目前已可購買")
    p.add_argument("--no-notify", action="store_true", help="只寫入不通知")
    args = p.parse_args()

    cal = Calendar(SETTINGS.db_path)
    snap = build_snapshot(args)
    change = cal.add_manual_event(
        snap, imminent_lead_sec=SETTINGS.imminent_lead_min * 60
    )
    if change is None:
        print("已寫入(無狀態變更,不通知)。")
        return
    print(f"已寫入:{change.event.name} → {change.event.status}")
    if not args.no_notify:
        Notifier().notify_change(change)


if __name__ == "__main__":
    main()
