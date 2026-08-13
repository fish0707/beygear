"""History logging and web export.

`events` is upserted in place, so the price/restock timeline only survives if
`history` is appended to. These tests pin that behaviour and the JSON shape the
website builds from.
"""

from __future__ import annotations

import json
import os

from calendar_db import Calendar
from monitors.base import ProductSnapshot
import export_web


def _snap(price: int, *, available: bool, stock: int | None = 5,
          original: int = 795) -> ProductSnapshot:
    return ProductSnapshot(
        product_key="ux-18",
        platform="momo",
        item_id="12345",
        name="BEYBLADE X UX-18 鮫鯊狂鱗改造組",
        url="https://www.momoshop.com.tw/goods/12345",
        price=price,
        original_price=original,
        stock=stock,
        available=available,
        raw={},
    )


def test_history_records_each_meaningful_change(tmp_path):
    db = Calendar(str(tmp_path / "r.db"))
    try:
        db.upsert_snapshot(_snap(795, available=True), now=1000)      # first sighting
        db.upsert_snapshot(_snap(795, available=True), now=1100)      # unchanged
        db.upsert_snapshot(_snap(795, available=False, stock=0), now=1200)  # sold out
        db.upsert_snapshot(_snap(795, available=True), now=1300)      # restocked

        hist = db.history_for("ux-18")
        # The unchanged poll must not create a row, the other three must.
        assert len(hist) == 3
        assert [h["observed_at"] for h in hist] == [1000, 1200, 1300]
        assert hist[-1]["status"] == "RESTOCKED"
        assert hist[-1]["old_status"] == "SOLD_OUT"
    finally:
        db.close()


def test_history_captures_price_drop(tmp_path):
    db = Calendar(str(tmp_path / "r.db"))
    try:
        db.upsert_snapshot(_snap(1200, available=True), now=1000)
        db.upsert_snapshot(_snap(795, available=True), now=1100)
        hist = db.history_for("ux-18")
        assert len(hist) == 2
        assert hist[1]["old_price"] == 1200
        assert hist[1]["price"] == 795
    finally:
        db.close()


def test_export_writes_site_json(tmp_path):
    db_path = str(tmp_path / "r.db")
    db = Calendar(db_path)
    try:
        db.upsert_snapshot(_snap(795, available=True), now=1000)
        db.upsert_snapshot(_snap(795, available=False, stock=0), now=1100)
        db.upsert_snapshot(_snap(1490, available=True), now=1200)  # scalper markup
    finally:
        db.close()

    out = tmp_path / "data"
    bundle = export_web.build(db_path)
    os.makedirs(out, exist_ok=True)
    for name in ("snapshot", "products", "meta"):
        (out / f"{name}.json").write_text(
            json.dumps(bundle[name], ensure_ascii=False), encoding="utf-8"
        )

    products = bundle["products"]["products"]
    assert len(products) == 1
    p = products[0]
    assert p["product_key"] == "ux-18"
    assert p["restock_count"] == 1
    assert p["in_stock_anywhere"] is True
    # Listed at 1490 against an original of 795 — the markup is the headline number.
    assert p["available_at_original_price"] is False
    assert bundle["snapshot"]["listings"][0]["markup_pct"] == 87.4
    # The bulky raw payload must never reach the public JSON.
    assert "raw" not in bundle["snapshot"]["listings"][0]
    assert bundle["meta"]["history_count"] == 3


def test_markup_handles_missing_values():
    assert export_web._markup_pct(None, 795) is None
    assert export_web._markup_pct(795, None) is None
    assert export_web._markup_pct(795, 0) is None
    assert export_web._markup_pct(795, 795) == 0.0
