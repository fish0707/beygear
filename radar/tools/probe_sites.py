"""
Probe the real retailer responses and print their structure.

The dev sandbox cannot reach Taiwanese e-commerce (its egress proxy refuses
momoshop and eslite), and the eslite parser has never been calibrated against
real HTML — its own docstring says so. A GitHub Actions runner *can* reach them,
so this script runs there and prints enough structure to the job log to write the
selectors against.

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

MOMO_API = "https://www.momoshop.com.tw/api/moecapp/getGoodsRealTimeInfo"
MOMO_ITEM = "15462752"
ESLITE_PRODUCTS = [
    "10042014802683176604005",
    "10042014802683165873009",
]
ESLITE_SEARCH = "https://www.eslite.com/search?keyword=beyblade"


def hr(title: str) -> None:
    print(f"\n{'=' * 12} {title} {'=' * 12}")


def momo_headers(item_id: str) -> dict:
    return {
        "User-Agent": UA,
        "Content-Type": "application/json;charset=UTF-8",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
        "Origin": "https://www.momoshop.com.tw",
        "Referer": f"https://www.momoshop.com.tw/goods/GoodsDetail.jsp?i_code={item_id}",
        "X-Requested-With": "XMLHttpRequest",
    }


def probe_momo() -> None:
    hr(f"momo API — goodsCode={MOMO_ITEM}")
    try:
        r = requests.post(MOMO_API, json={"goodsCode": MOMO_ITEM},
                          headers=momo_headers(MOMO_ITEM), timeout=20)
        print("status:", r.status_code)
        r.raise_for_status()
        data = r.json()
        print("top-level keys:", list(data)[:20])
        for key in ("rtnGoodsData", "goodsData", "data"):
            block = data.get(key)
            if isinstance(block, dict):
                print(f"\n{key} keys:", list(block)[:40])
                interesting = [k for k in block
                               if re.search(r"price|stock|qty|name|sale|status|avail",
                                            k, re.I)]
                print(f"{key} interesting fields:")
                for k in interesting[:25]:
                    print(f"   {k} = {block[k]!r}")
                break
        else:
            print("no goods block found; raw head:", json.dumps(data, ensure_ascii=False)[:600])
    except Exception as exc:  # noqa: BLE001 - probe should never abort the run
        print("momo probe failed:", type(exc).__name__, exc)


def probe_eslite_product(pid: str) -> None:
    hr(f"eslite product {pid}")
    url = f"https://www.eslite.com/product/{pid}"
    try:
        r = requests.get(url, headers={"User-Agent": UA, "Accept": "text/html",
                                       "Accept-Language": "zh-TW,zh;q=0.9"}, timeout=25)
        print("status:", r.status_code, "| bytes:", len(r.text))
        r.raise_for_status()
        html = r.text

        m = re.search(r'<script[^>]*id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>',
                      html, re.I | re.S)
        print("has __NEXT_DATA__:", bool(m))
        if m:
            try:
                nd = json.loads(m.group(1))
                print("__NEXT_DATA__ top keys:", list(nd)[:10])
                page_props = nd.get("props", {}).get("pageProps", {})
                print("pageProps keys:", list(page_props)[:25])
                blob = json.dumps(page_props, ensure_ascii=False)
                for field in ("price", "sellPrice", "listPrice", "stock", "quantity",
                              "available", "title", "name", "sku"):
                    for hit in re.finditer(rf'"{field}"\s*:\s*("[^"]{{0,60}}"|[\d.]+|true|false|null)',
                                           blob, re.I):
                        print(f"   {field}: {hit.group(1)}")
                        break
            except Exception as exc:  # noqa: BLE001
                print("  __NEXT_DATA__ parse failed:", exc)

        lds = re.findall(r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
                         html, re.I | re.S)
        print("ld+json blocks:", len(lds))
        for raw in lds[:3]:
            try:
                obj = json.loads(raw)
            except Exception:  # noqa: BLE001
                continue
            items = obj if isinstance(obj, list) else [obj]
            for it in items:
                if isinstance(it, dict):
                    print("   @type:", it.get("@type"), "| keys:", list(it)[:12])
                    if it.get("offers"):
                        print("   offers:", json.dumps(it["offers"], ensure_ascii=False)[:300])
    except Exception as exc:  # noqa: BLE001
        print("eslite product probe failed:", type(exc).__name__, exc)


def probe_eslite_search() -> None:
    hr("eslite search — keyword=beyblade")
    try:
        r = requests.get(ESLITE_SEARCH,
                         headers={"User-Agent": UA, "Accept": "text/html",
                                  "Accept-Language": "zh-TW,zh;q=0.9"}, timeout=25)
        print("status:", r.status_code, "| bytes:", len(r.text))
        r.raise_for_status()
        html = r.text
        links = sorted(set(re.findall(r"/product/(\d{6,})", html)))
        print("product links found:", len(links), links[:10])
        print("has __NEXT_DATA__:", bool(re.search(r'id=["\']__NEXT_DATA__["\']', html)))
        m = re.search(r'<script[^>]*id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>',
                      html, re.I | re.S)
        if m:
            nd = json.loads(m.group(1))
            pp = nd.get("props", {}).get("pageProps", {})
            print("search pageProps keys:", list(pp)[:25])
    except Exception as exc:  # noqa: BLE001
        print("eslite search probe failed:", type(exc).__name__, exc)


if __name__ == "__main__":
    probe_momo()
    for pid in ESLITE_PRODUCTS:
        probe_eslite_product(pid)
    probe_eslite_search()
    print("\n[probe] done")
