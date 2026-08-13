"""統一開賣行事曆(核心,SQLite)。

事件 = {商品, 平台, 開賣時間, 售價, 是否原價, 庫存, 連結, 狀態}。
職責:
    - 去重:同一 (平台, 商品碼) 只有一列,重複觀測就 upsert 更新。
    - 跨平台合併:同一 product_key 可跨平台查詢(by_product_key)。
    - 狀態機:預告 → 即將開賣 → 已上架/開賣 → 售罄 → 回補。
    - 變更偵測:upsert 回傳 Change,讓 run.py / notify.py 決定要不要通知。

只存公開事實資料。此模組不發通知、不打網路,純資料層。
"""

from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass
from typing import Optional

from monitors.base import ProductSnapshot

# --- 狀態機 -----------------------------------------------------------------

ANNOUNCED = "ANNOUNCED"   # 預告(有未來開賣時間,尚未上架)
IMMINENT = "IMMINENT"     # 即將開賣(距開賣 <= 提前提醒門檻)
ON_SALE = "ON_SALE"       # 已上架 / 開賣中(可購買)
SOLD_OUT = "SOLD_OUT"     # 售罄
RESTOCKED = "RESTOCKED"   # 回補(售罄後又可購買 —— 最想通知的訊號)

ALL_STATUSES = (ANNOUNCED, IMMINENT, ON_SALE, SOLD_OUT, RESTOCKED)


@dataclass
class EventRow:
    product_key: str
    platform: str
    item_id: str
    name: str
    url: str
    price: Optional[int]
    original_price: Optional[int]
    is_original_price: Optional[bool]
    stock: Optional[int]
    on_sale_ts: Optional[int]
    available: bool
    status: str
    first_seen_at: int
    last_updated_at: int
    id: Optional[int] = None


@dataclass
class Change:
    """一次 upsert 造成的變更(給通知層用)。"""

    event: EventRow
    old_status: Optional[str]      # None 表示全新事件
    old_price: Optional[int]

    @property
    def is_new(self) -> bool:
        return self.old_status is None

    @property
    def status_changed(self) -> bool:
        return self.old_status is not None and self.old_status != self.event.status

    @property
    def is_restock(self) -> bool:
        return self.event.status == RESTOCKED

    @property
    def is_imminent(self) -> bool:
        return self.status_changed and self.event.status == IMMINENT

    @property
    def is_original_price_restock(self) -> bool:
        return self.is_restock and self.event.is_original_price is True

    @property
    def price_dropped(self) -> bool:
        return (
            self.old_price is not None
            and self.event.price is not None
            and self.event.price < self.old_price
        )


def compute_status(
    snap: ProductSnapshot,
    prev_status: Optional[str],
    now: int,
    imminent_lead_sec: int,
) -> str:
    """依觀測 + 前一狀態推導新狀態。"""
    if snap.available:
        if prev_status == SOLD_OUT:
            return RESTOCKED
        if prev_status == RESTOCKED:
            # 已通知過回補,穩定下來歸為開賣中,避免重複通知。
            return ON_SALE
        return ON_SALE

    # 目前不可購買
    if prev_status in (ON_SALE, RESTOCKED):
        return SOLD_OUT
    if snap.on_sale_ts is not None and snap.on_sale_ts > now:
        if snap.on_sale_ts - now <= imminent_lead_sec:
            return IMMINENT
        return ANNOUNCED
    if prev_status == SOLD_OUT:
        return SOLD_OUT
    return prev_status or ANNOUNCED


# --- 行事曆 -----------------------------------------------------------------

class Calendar:
    def __init__(self, db_path: str = "radar.db"):
        self.db_path = db_path
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def close(self) -> None:
        self._conn.close()

    def _init_schema(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_key TEXT NOT NULL,
                platform TEXT NOT NULL,
                item_id TEXT NOT NULL,
                name TEXT,
                url TEXT,
                price INTEGER,
                original_price INTEGER,
                is_original_price INTEGER,
                stock INTEGER,
                on_sale_ts INTEGER,
                available INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL,
                first_seen_at INTEGER NOT NULL,
                last_updated_at INTEGER NOT NULL,
                raw TEXT,
                UNIQUE(platform, item_id)
            )
            """
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_events_product_key ON events(product_key)"
        )
        # Append-only log. `events` holds only the latest observation per product,
        # so without this the price and restock timeline is overwritten on every
        # poll — and that timeline is the part nobody else can reproduce.
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_key TEXT NOT NULL,
                platform TEXT NOT NULL,
                item_id TEXT NOT NULL,
                name TEXT,
                url TEXT,
                price INTEGER,
                original_price INTEGER,
                is_original_price INTEGER,
                stock INTEGER,
                available INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL,
                old_status TEXT,
                old_price INTEGER,
                observed_at INTEGER NOT NULL
            )
            """
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_history_product_key ON history(product_key)"
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_history_observed_at ON history(observed_at)"
        )
        self._conn.commit()

    # --- 讀取 ---

    def get(self, platform: str, item_id: str) -> Optional[EventRow]:
        cur = self._conn.execute(
            "SELECT * FROM events WHERE platform=? AND item_id=?",
            (platform, item_id),
        )
        row = cur.fetchone()
        return _row_to_event(row) if row else None

    def by_product_key(self, product_key: str) -> list[EventRow]:
        """跨平台同款:同一 product_key 的所有平台列。"""
        cur = self._conn.execute(
            "SELECT * FROM events WHERE product_key=? ORDER BY platform",
            (product_key,),
        )
        return [_row_to_event(r) for r in cur.fetchall()]

    def count_platform(self, platform: str) -> int:
        """某平台目前已存幾筆(用來判斷發現式監控是否為首次掃描)。"""
        cur = self._conn.execute(
            "SELECT COUNT(*) AS n FROM events WHERE platform=?", (platform,)
        )
        return int(cur.fetchone()["n"])

    def all_events(self) -> list[EventRow]:
        cur = self._conn.execute(
            "SELECT * FROM events ORDER BY COALESCE(on_sale_ts, last_updated_at)"
        )
        return [_row_to_event(r) for r in cur.fetchall()]

    # --- 寫入 ---

    def upsert_snapshot(
        self,
        snap: ProductSnapshot,
        now: Optional[int] = None,
        imminent_lead_sec: int = 1800,
    ) -> Optional[Change]:
        """寫入一筆觀測。回傳 Change(新事件或有意義的變更),否則 None。"""
        now = now or int(time.time())
        prev = self.get(snap.platform, snap.item_id)
        prev_status = prev.status if prev else None
        new_status = compute_status(snap, prev_status, now, imminent_lead_sec)

        first_seen = prev.first_seen_at if prev else now
        is_orig = snap.is_original_price

        self._conn.execute(
            """
            INSERT INTO events (product_key, platform, item_id, name, url, price,
                original_price, is_original_price, stock, on_sale_ts, available,
                status, first_seen_at, last_updated_at, raw)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(platform, item_id) DO UPDATE SET
                product_key=excluded.product_key,
                name=excluded.name,
                url=excluded.url,
                price=excluded.price,
                original_price=excluded.original_price,
                is_original_price=excluded.is_original_price,
                stock=excluded.stock,
                on_sale_ts=excluded.on_sale_ts,
                available=excluded.available,
                status=excluded.status,
                last_updated_at=excluded.last_updated_at,
                raw=excluded.raw
            """,
            (
                snap.product_key, snap.platform, snap.item_id, snap.name, snap.url,
                snap.price, snap.original_price, _bool_to_db(is_orig), snap.stock,
                snap.on_sale_ts, 1 if snap.available else 0, new_status,
                first_seen, now, json.dumps(snap.raw, ensure_ascii=False),
            ),
        )
        self._conn.commit()

        event = self.get(snap.platform, snap.item_id)
        assert event is not None

        # 判斷是否值得回報:全新事件,或狀態變更,或原價降價。
        is_new = prev is None
        status_changed = prev is not None and prev_status != new_status
        price_dropped = (
            prev is not None
            and prev.price is not None
            and snap.price is not None
            and snap.price < prev.price
        )
        if is_new or status_changed or price_dropped:
            self._append_history(event, prev_status, prev.price if prev else None, now)
            return Change(
                event=event,
                old_status=prev_status,
                old_price=prev.price if prev else None,
            )
        return None

    def _append_history(
        self,
        event: EventRow,
        old_status: Optional[str],
        old_price: Optional[int],
        observed_at: int,
    ) -> None:
        self._conn.execute(
            """
            INSERT INTO history (product_key, platform, item_id, name, url, price,
                original_price, is_original_price, stock, available, status,
                old_status, old_price, observed_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                event.product_key, event.platform, event.item_id, event.name, event.url,
                event.price, event.original_price, _bool_to_db(event.is_original_price),
                event.stock, 1 if event.available else 0, event.status,
                old_status, old_price, observed_at,
            ),
        )
        self._conn.commit()

    def history_for(self, product_key: str) -> list[dict]:
        cur = self._conn.execute(
            "SELECT * FROM history WHERE product_key=? ORDER BY observed_at ASC",
            (product_key,),
        )
        return [dict(r) for r in cur.fetchall()]

    def all_history(self) -> list[dict]:
        cur = self._conn.execute("SELECT * FROM history ORDER BY observed_at ASC")
        return [dict(r) for r in cur.fetchall()]

    def upsert_many(
        self,
        snaps: list[ProductSnapshot],
        now: Optional[int] = None,
        imminent_lead_sec: int = 1800,
    ) -> list[Change]:
        changes: list[Change] = []
        for s in snaps:
            c = self.upsert_snapshot(s, now=now, imminent_lead_sec=imminent_lead_sec)
            if c is not None:
                changes.append(c)
        return changes

    def add_manual_event(self, snap: ProductSnapshot, now: Optional[int] = None,
                         imminent_lead_sec: int = 1800) -> Optional[Change]:
        """人工餵料入口(feed_manual 用):走同一條 upsert / 狀態機 / 通知路徑。"""
        return self.upsert_snapshot(snap, now=now, imminent_lead_sec=imminent_lead_sec)


# --- 轉換小工具 -------------------------------------------------------------

def _bool_to_db(val: Optional[bool]) -> Optional[int]:
    if val is None:
        return None
    return 1 if val else 0


def _db_to_bool(val) -> Optional[bool]:
    if val is None:
        return None
    return bool(val)


def _row_to_event(row: sqlite3.Row) -> EventRow:
    return EventRow(
        id=row["id"],
        product_key=row["product_key"],
        platform=row["platform"],
        item_id=row["item_id"],
        name=row["name"],
        url=row["url"],
        price=row["price"],
        original_price=row["original_price"],
        is_original_price=_db_to_bool(row["is_original_price"]),
        stock=row["stock"],
        on_sale_ts=row["on_sale_ts"],
        available=bool(row["available"]),
        status=row["status"],
        first_seen_at=row["first_seen_at"],
        last_updated_at=row["last_updated_at"],
    )
