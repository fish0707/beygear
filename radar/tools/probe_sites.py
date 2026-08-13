"""
Probe the real retailer responses and print their structure.

The dev sandbox cannot reach Taiwanese e-commerce (its egress proxy refuses
momoshop and eslite), and neither parser has been calibrated against a real
response. A GitHub Actions runner *can* reach them, so this script runs there
and prints enough structure to the job log to write the selectors against.

Round 1 told us what does NOT work:
  - momo's getGoodsRealTimeInfo answers 200 with {"success": false,
    "resultMessage": "查無商品"} for goodsCode 15462752, so either the endpoint
    or the payload shape is wrong — the code itself is right, the user's own
    product URL uses it.
  - all three eslite URLs returned *exactly* 13583 bytes, identical length for a
    search page and two different products. That is one canned shell/challenge
    page, not content.

So round 2 stops guessing at JSON shapes and looks at the HTML the browser
actually gets, and prints the head of eslite's canned page to identify it.

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
ESLITE_PRODUCTS = [
    "10042014802683176604005",
    "10042014802683165873009",
]
ESLITE_SEARCH = "https://www.eslite.com/search?keyword=beyblade"

BROWSER_HEADERS = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,"
              "image/webp,*/*;q=0.8",
    "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
}


def hr(title: str) -> None:
    print(f"\n{'=' * 12} {title} {'=' * 12}")


def show_ld_json(html: str) -> None:
    blocks = re.findall(
        r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html, re.I | re.S)
    print("ld+json blocks:", len(blocks))
    for raw in blocks:
        try:
            obj = json.loads(raw.strip())
        except Exception:  # noqa: BLE001
            print("   (unparseable block, head:", raw.strip()[:120], ")")
            continue
        for it in (obj if isinstance(obj, list) else [obj]):
            if not isinstance(it, dict):
                continue
            print("   @type:", it.get("@type"), "| keys:", list(it)[:14])
            if it.get("@type") in ("Product", "product"):
                print("   name:", it.get("name"))
                print("   offers:", json.dumps(it.get("offers"), ensure_ascii=False)[:400])


def show_meta(html: str) -> None:
    """Print the og:/product: meta tags — the most stable price source on a
    server-rendered shop page."""
    hits = re.findall(
        r'<meta[^>]+(?:property|name)=["\']((?:og|product|twitter):[^"\']+)["\']'
        r'[^>]+content=["\']([^"\']{0,120})["\']', html, re.I)
    print("meta tags:", len(hits))
    for k, v in hits[:20]:
        print(f"   {k} = {v}")


def probe_momo_html() -> None:
    """The product page itself. If momo server-renders price/availability we do
    not need the private API at all."""
    for label, url in (
        ("classic", f"https://www.momoshop.com.tw/goods/GoodsDetail.jsp?i_code={MOMO_ITEM}"),
        ("short", f"https://www.momoshop.com.tw/product/{MOMO_ITEM}"),
    ):
        hr(f"momo HTML ({label}) — {url}")
        try:
            r = requests.get(url, headers=BROWSER_HEADERS, timeout=25)
            print("status:", r.status_code, "| final url:", r.url, "| bytes:", len(r.text))
            html = r.text
            title = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
            print("title:", title.group(1).strip()[:120] if title else None)
            show_meta(html)
            show_ld_json(html)
            # momo puts the price in a few well-known spots; show whatever matches.
            for pat, name in (
                (r'"goodsPrice"\s*:\s*"?(\d[\d,]*)', "goodsPrice json"),
                (r'id=["\']goodsPrice["\'][^>]*>\s*\$?([\d,]+)', "#goodsPrice"),
                (r'class=["\'][^"\']*price[^"\']*["\'][^>]*>\s*\$?([\d,]+)', "class*=price"),
                (r'i_code["\']?\s*[:=]\s*["\']?(\d+)', "i_code echo"),
            ):
                m = re.search(pat, html, re.I)
                print(f"   {name}: {m.group(1) if m else None}")
        except Exception as exc:  # noqa: BLE001
            print("failed:", type(exc).__name__, exc)


def probe_momo_api_variants() -> None:
    """Round 1 got 查無商品. Try the payload/endpoint variants momo has shipped."""
    hr(f"momo API variants — {MOMO_ITEM}")
    headers = {
        "User-Agent": UA,
        "Content-Type": "application/json;charset=UTF-8",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
        "Origin": "https://www.momoshop.com.tw",
        "Referer": f"https://www.momoshop.com.tw/goods/GoodsDetail.jsp?i_code={MOMO_ITEM}",
        "X-Requested-With": "XMLHttpRequest",
    }
    variants = [
        ("moecapp goodsCode", "https://www.momoshop.com.tw/api/moecapp/getGoodsRealTimeInfo",
         {"goodsCode": MOMO_ITEM}),
        ("moecapp i_code", "https://www.momoshop.com.tw/api/moecapp/getGoodsRealTimeInfo",
         {"i_code": MOMO_ITEM}),
        ("moecapp +host", "https://www.momoshop.com.tw/api/moecapp/getGoodsRealTimeInfo",
         {"goodsCode": MOMO_ITEM, "host": "momoshop", "flag": "1"}),
        ("goodsDetail", "https://www.momoshop.com.tw/api/goods/getGoodsDetail",
         {"goodsCode": MOMO_ITEM}),
        ("eccapi", "https://eccapi.momoshop.com.tw/user/goods/getGoodsRealTimeInfo",
         {"goodsCode": MOMO_ITEM}),
    ]
    for label, url, payload in variants:
        try:
            r = requests.post(url, json=payload, headers=headers, timeout=20)
            body = r.text[:300].replace("\n", " ")
            print(f"   [{label}] {r.status_code} :: {body}")
        except Exception as exc:  # noqa: BLE001
            print(f"   [{label}] failed: {type(exc).__name__} {exc}")


def probe_eslite(url: str, label: str) -> None:
    hr(f"eslite {label} — {url}")
    try:
        r = requests.get(url, headers=BROWSER_HEADERS, timeout=25)
        print("status:", r.status_code, "| final url:", r.url, "| bytes:", len(r.text))
        print("content-type:", r.headers.get("content-type"))
        print("server:", r.headers.get("server"), "| set-cookie:",
              str(r.headers.get("set-cookie"))[:160])
        html = r.text
        # Round 1: every eslite URL returned the same 13583 bytes. Print the head
        # so we can name what that page actually is (challenge? SPA shell? 404?).
        print("--- first 1200 chars ---")
        print(html[:1200])
        print("--- end ---")
        print("has __NEXT_DATA__:", "__NEXT_DATA__" in html)
        print("product links:", len(set(re.findall(r"/product/(\d{6,})", html))))
        show_ld_json(html)
    except Exception as exc:  # noqa: BLE001
        print("failed:", type(exc).__name__, exc)


if __name__ == "__main__":
    probe_momo_html()
    probe_momo_api_variants()
    probe_eslite(f"https://www.eslite.com/product/{ESLITE_PRODUCTS[0]}", "product")
    probe_eslite(ESLITE_SEARCH, "search")
    print("\n[probe] done")
