"""
Probe the real retailer responses and print their structure.

The dev sandbox cannot reach Taiwanese e-commerce (its egress proxy refuses
momoshop and eslite), so this runs on a GitHub Actions runner, which can, and
prints structure to the job log to write the parsers against.

Where rounds 1–4 landed:

  momo — the product page and the per-item API are both closed to a datacenter
    IP (bot-guard page; 查無商品 through every session and payload variant).
    The *search* page is wide open and carries everything we need, embedded as
    escaped JSON:

        "goodsInfoList":[{"goodsCode":"15162670",
          "goodsName":"【TAKARA TOMY】BEYBLADE X 戰鬥陀螺X UX-15 鮫鯊狂鱗改造組",
          "goodsPrice":"$$795", "goodsPriceOri":"$$795",
          "goodsPriceModel":{"basePrice":{"price":"795"}},
          "goodsStock":"168", ...}]

    So the monitor should be search-driven, not item-driven. Round 5 pulls that
    blob out properly and prints one full record so every field name is known.
    (momo's apisearch host answers 403 Access Denied, so the page is the API.)

  eslite — athena.eslite.com/api/v2/search?keyword=… returns real JSON:
    {facets, hits:{start, found, hit:[{id, fields}]}}. The field names inside
    `fields` are the last unknown, so print one hit in full. The keyword
    "beyblade" matched only manga, so also try the Chinese product name.

It prints shapes and short samples, never whole pages.

    python tools/probe_sites.py
"""

from __future__ import annotations

import json
import re
import sys

import requests

sys.path.insert(0, ".")
from config import SETTINGS  # noqa: E402

UA = SETTINGS.user_agent

BROWSER_HEADERS = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
    "Upgrade-Insecure-Requests": "1",
}

JSON_HEADERS = {
    "User-Agent": UA,
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
    "Origin": "https://www.eslite.com",
    "Referer": "https://www.eslite.com/",
}


def hr(title: str) -> None:
    print(f"\n{'=' * 12} {title} {'=' * 12}")


def extract_goods_list(html: str) -> list[dict]:
    """Pull goodsInfoList out of momo's search page.

    The blob sits inside a JavaScript string, so the JSON is backslash-escaped.
    Unescape first, then let the JSON decoder find the end of the array for us —
    a regex cannot balance nested brackets reliably.
    """
    text = html.replace('\\"', '"')
    out: list[dict] = []
    for m in re.finditer(r'"goodsInfoList"\s*:\s*\[', text):
        start = text.index("[", m.end() - 1)
        try:
            arr, _ = json.JSONDecoder().raw_decode(text[start:])
        except ValueError as exc:
            print("   raw_decode failed:", exc)
            continue
        if isinstance(arr, list):
            out.extend(x for x in arr if isinstance(x, dict))
    return out


def probe_momo_search(keyword: str) -> None:
    hr(f"momo search — {keyword}")
    url = f"https://www.momoshop.com.tw/search/searchShop.jsp?keyword={keyword}"
    try:
        r = requests.get(url, headers=BROWSER_HEADERS, timeout=30)
        print("status:", r.status_code, "| bytes:", len(r.text))
        goods = extract_goods_list(r.text)
        print("goods parsed:", len(goods))
        if not goods:
            return
        print("\nfull first record:")
        print(json.dumps(goods[0], ensure_ascii=False, indent=2)[:2500])
        print("\nall records (code / price / stock / name):")
        for g in goods[:30]:
            print(f"   {g.get('goodsCode')} | {g.get('goodsPrice')} | "
                  f"stock={g.get('goodsStock')} | {str(g.get('goodsName'))[:52]}")
    except Exception as exc:  # noqa: BLE001
        print("failed:", type(exc).__name__, exc)


def probe_eslite_search(keyword: str) -> None:
    hr(f"eslite search — {keyword}")
    try:
        r = requests.get("https://athena.eslite.com/api/v2/search",
                         params={"keyword": keyword, "page": 1, "per_page": 20},
                         headers=JSON_HEADERS, timeout=25)
        print("status:", r.status_code, "|", r.url)
        data = r.json()
        hits = data.get("hits", {})
        print("found:", hits.get("found"), "| returned:", len(hits.get("hit", [])))
        hit = (hits.get("hit") or [{}])[0]
        print("\nfull first hit:")
        print(json.dumps(hit, ensure_ascii=False, indent=2)[:2500])
        print("\nall hits (id / name):")
        for h in hits.get("hit", [])[:20]:
            f = h.get("fields", {})
            print(f"   {h.get('id')} | {str(f.get('title') or f.get('name'))[:60]}")
    except Exception as exc:  # noqa: BLE001
        print("failed:", type(exc).__name__, exc)


def probe_eslite_product_variants(pid: str) -> None:
    """v3/products/<id> returned an empty array; try the other shapes."""
    hr(f"eslite product lookups — {pid}")
    attempts = [
        ("ids[] repeated", "https://athena.eslite.com/api/v3/products", {"ids[]": pid}),
        ("id", "https://athena.eslite.com/api/v3/products", {"id": pid}),
        ("v2 products", f"https://athena.eslite.com/api/v2/products/{pid}", None),
        ("v3 slug", f"https://athena.eslite.com/api/v3/products/{pid}/detail", None),
    ]
    for label, url, params in attempts:
        try:
            r = requests.get(url, params=params, headers=JSON_HEADERS, timeout=20)
            print(f"   [{label}] {r.status_code} | {len(r.text)} bytes | "
                  f"{r.text[:200]}")
        except Exception as exc:  # noqa: BLE001
            print(f"   [{label}] failed: {type(exc).__name__} {exc}")


if __name__ == "__main__":
    probe_momo_search("BEYBLADE")
    probe_momo_search("%E6%88%B0%E9%AC%A5%E9%99%80%E8%9E%BA")  # 戰鬥陀螺
    probe_eslite_search("戰鬥陀螺")
    probe_eslite_product_variants("10042014802683176604005")
    print("\n[probe] done")
