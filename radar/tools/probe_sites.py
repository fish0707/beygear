"""
Probe the real retailer responses and print their structure.

The dev sandbox cannot reach Taiwanese e-commerce (its egress proxy refuses
momoshop and eslite), so this runs on a GitHub Actions runner, which can, and
prints structure to the job log to write the parsers against.

What rounds 1–3 established, and why round 4 looks where it does:

  momo — the homepage and the *search* page both come back real (search:
    161 KB, title "BEYBLADE - momo購物網"). Only the product-detail route is
    replaced by the bot-guard page ("Mobile管理訊息"), and the per-item API
    answers 查無商品 no matter what session or headers we bring. So the item
    endpoint is a dead end from a datacenter IP, and search is the way in.
    Round 4 reads what the working search response actually contains — it
    yielded only one i_code, so the results are almost certainly a JSON blob or
    /product/ links rather than the old i_code anchors — and tries momo's search
    API host.

  eslite — the site is a Vue SPA, so there is nothing to scrape from HTML,
    ever. Its own bundle named the API: host athena.eslite.com, paths
    /api/v3/products, /api/v2/search, /api/v2/search_keyword. Round 4 calls
    them. (/llms.txt turned out to be a category-map for AI crawlers, not
    product data, and product/<id>.md just returns the SPA shell — neither is
    a stock source.)

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

MOMO_ITEM = "15462752"
ESLITE_PRODUCT = "10042014802683176604005"

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


def brief(obj, limit: int = 700) -> str:
    return json.dumps(obj, ensure_ascii=False)[:limit]


def walk_keys(obj, depth: int = 0, path: str = "") -> None:
    """Print the shape of a nested response so field names are visible."""
    if depth > 3:
        return
    if isinstance(obj, dict):
        print("   " * depth + f"{path or '.'} {{{', '.join(list(obj)[:18])}}}")
        for k in list(obj)[:8]:
            if isinstance(obj[k], (dict, list)):
                walk_keys(obj[k], depth + 1, k)
    elif isinstance(obj, list):
        print("   " * depth + f"{path}[] len={len(obj)}")
        if obj:
            walk_keys(obj[0], depth + 1, f"{path}[0]")


# --- momo -------------------------------------------------------------------

def probe_momo_search_shape() -> None:
    """The search page renders fine for us; find where the product data lives."""
    hr("momo — inside the working search page")
    s = requests.Session()
    s.headers.update(BROWSER_HEADERS)
    url = "https://www.momoshop.com.tw/search/searchShop.jsp?keyword=BEYBLADE"
    try:
        r = s.get(url, timeout=30)
        html = r.text
        print("status:", r.status_code, "| bytes:", len(html))
        print("product links:", sorted(set(re.findall(r"/product/(\d{6,})", html)))[:15])
        print("i_code links:", sorted(set(re.findall(r"i_code=(\d{6,})", html)))[:15])
        print("goodsCode mentions:", len(re.findall(r"goodsCode", html)))
        for pat, name in (
            (r"window\.__(\w+)__\s*=", "window.__X__ blobs"),
            (r'<script[^>]*id="([^"]+)"[^>]*type="application/json"', "json script ids"),
        ):
            print(f"{name}:", sorted(set(re.findall(pat, html)))[:10])
        # Show the markup around the first price so the selector can be written.
        m = re.search(r".{300}\$[\d,]{3,}.{300}", html, re.S)
        print("--- markup around first price ---")
        print(re.sub(r"\s+", " ", m.group(0)) if m else "no $price found")
        print("--- end ---")
    except Exception as exc:  # noqa: BLE001
        print("failed:", type(exc).__name__, exc)


def probe_momo_search_api() -> None:
    hr("momo — search API host")
    variants = [
        ("apisearch textSearch",
         "https://apisearch.momoshop.com.tw/momoSearchCloud/moec/textSearch",
         {"host": "momoshop", "flag": 99, "data": {"searchValue": "BEYBLADE",
                                                   "curPage": "1", "cateLevel": "-1",
                                                   "cateCode": "", "first": True}}),
        ("apisearch goodsSearch",
         "https://apisearch.momoshop.com.tw/momoSearchCloud/moec/textSearch",
         {"data": {"searchValue": "BEYBLADE", "curPage": "1"}}),
    ]
    headers = {
        "User-Agent": UA,
        "Content-Type": "application/json",
        "Accept": "application/json, text/plain, */*",
        "Origin": "https://www.momoshop.com.tw",
        "Referer": "https://www.momoshop.com.tw/",
    }
    for label, url, payload in variants:
        try:
            r = requests.post(url, json=payload, headers=headers, timeout=25)
            print(f"\n[{label}] {r.status_code} | {len(r.text)} bytes")
            try:
                walk_keys(r.json())
            except ValueError:
                print("   body head:", r.text[:300].replace("\n", " "))
        except Exception as exc:  # noqa: BLE001
            print(f"[{label}] failed: {type(exc).__name__} {exc}")


# --- eslite -----------------------------------------------------------------

def probe_eslite_api() -> None:
    """Call the endpoints the SPA's own bundle names."""
    hr("eslite — athena API")
    attempts = [
        ("product v3", "GET", f"https://athena.eslite.com/api/v3/products/{ESLITE_PRODUCT}", None),
        ("product v3 query", "GET", "https://athena.eslite.com/api/v3/products",
         {"ids": ESLITE_PRODUCT}),
        ("search v2 GET", "GET", "https://athena.eslite.com/api/v2/search",
         {"keyword": "beyblade", "page": 1, "per_page": 20}),
        ("search v2 q", "GET", "https://athena.eslite.com/api/v2/search",
         {"q": "beyblade"}),
        ("search_keyword", "GET", "https://athena.eslite.com/api/v2/search_keyword",
         {"keyword": "beyblade"}),
    ]
    for label, method, url, params in attempts:
        try:
            r = requests.request(method, url, params=params, headers=JSON_HEADERS, timeout=25)
            print(f"\n[{label}] {r.status_code} | {r.headers.get('content-type')} | "
                  f"{len(r.text)} bytes | {r.url}")
            if r.status_code == 200 and "json" in str(r.headers.get("content-type")):
                data = r.json()
                walk_keys(data)
                print("   sample:", brief(data))
            else:
                print("   body head:", r.text[:250].replace("\n", " "))
        except Exception as exc:  # noqa: BLE001
            print(f"[{label}] failed: {type(exc).__name__} {exc}")


if __name__ == "__main__":
    probe_momo_search_shape()
    probe_momo_search_api()
    probe_eslite_api()
    print("\n[probe] done")
