"""
Export the radar's SQLite state into JSON for the public site.

The website is a static build plus a small client-side fetch, so everything it
needs has to be a plain file in the repo:

  data/snapshot.json  — current state of every tracked product (client fetches
                        this for live stock, so the site stays fresh between
                        rebuilds without burning a deploy)
  data/products.json  — one entry per product_key with its full history, used to
                        pre-render the per-product pages at build time
  data/meta.json      — generation timestamp and counts

Run after each radar pass:  python export_web.py --db radar.db --out ../data
"""

from __future__ import annotations

import argparse
import json
import os
import time
from collections import defaultdict
from typing import Any

from dataclasses import asdict

from calendar_db import Calendar


def _clean(row: dict[str, Any]) -> dict[str, Any]:
    """Drop internal columns and normalise booleans for the front end."""
    out = {k: v for k, v in row.items() if k not in ("raw", "id")}
    for key in ("is_original_price", "available"):
        if key in out and out[key] is not None:
            out[key] = bool(out[key])
    return out


def _markup_pct(price: int | None, original: int | None) -> float | None:
    """How far above the original price this listing sits, as a percentage."""
    if not price or not original or original <= 0:
        return None
    return round((price - original) / original * 100, 1)


def build(db_path: str) -> dict[str, Any]:
    db = Calendar(db_path)
    try:
        events = [_clean(asdict(r)) for r in db.all_events()]
        history = [_clean(h) for h in db.all_history()]
    finally:
        db.close()

    for e in events:
        e["markup_pct"] = _markup_pct(e.get("price"), e.get("original_price"))

    by_key: dict[str, list[dict]] = defaultdict(list)
    for h in history:
        by_key[h["product_key"]].append(h)

    products = []
    for key in sorted({e["product_key"] for e in events}):
        listings = [e for e in events if e["product_key"] == key]
        hist = sorted(by_key.get(key, []), key=lambda h: h["observed_at"])
        in_stock = [l for l in listings if l.get("available")]
        at_original = [l for l in in_stock if l.get("is_original_price")]
        cheapest = min((l for l in listings if l.get("price")),
                       key=lambda l: l["price"], default=None)
        products.append({
            "product_key": key,
            "name": next((l.get("name") for l in listings if l.get("name")), key),
            "platforms": sorted({l["platform"] for l in listings}),
            "listings": listings,
            "history": hist,
            "restock_count": sum(1 for h in hist if h.get("status") == "RESTOCKED"),
            "in_stock_anywhere": bool(in_stock),
            "available_at_original_price": bool(at_original),
            "lowest_price": cheapest.get("price") if cheapest else None,
            "original_price": next(
                (l.get("original_price") for l in listings if l.get("original_price")), None
            ),
            "last_updated_at": max((l.get("last_updated_at") or 0) for l in listings),
        })

    now = int(time.time())
    return {
        "snapshot": {
            "generated_at": now,
            "listings": events,
        },
        "products": {
            "generated_at": now,
            "products": products,
        },
        "meta": {
            "generated_at": now,
            "product_count": len(products),
            "listing_count": len(events),
            "history_count": len(history),
            "in_stock_count": sum(1 for p in products if p["in_stock_anywhere"]),
            "at_original_price_count": sum(
                1 for p in products if p["available_at_original_price"]
            ),
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="radar.db")
    ap.add_argument("--out", default="../data")
    args = ap.parse_args()

    if not os.path.exists(args.db):
        print(f"[export] no database at {args.db}; nothing to export")
        return

    bundle = build(args.db)
    os.makedirs(args.out, exist_ok=True)
    for name in ("snapshot", "products", "meta"):
        path = os.path.join(args.out, f"{name}.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(bundle[name], fh, ensure_ascii=False, indent=2, sort_keys=True)
        print(f"[export] wrote {path}")

    m = bundle["meta"]
    print(
        f"[export] {m['product_count']} products, {m['listing_count']} listings, "
        f"{m['history_count']} history rows, {m['in_stock_count']} in stock"
    )


if __name__ == "__main__":
    main()
