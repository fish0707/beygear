"""
Probe the real retailer responses and print their structure.

The dev sandbox cannot reach Taiwanese e-commerce (its egress proxy refuses
momoshop and eslite), so this runs on a GitHub Actions runner, which can, and
prints structure to the job log to write the parsers against.

What the first two rounds established:

  momo — the product page returns 200 with title "momo購物網 -- Mobile管理訊息",
    zero ld+json and no price anywhere. That is momo's bot-guard page, not the
    product. Its API is alive (sending `i_code` instead of `goodsCode` gets
    "goodsCode is empty!!!", so it reads the field) but answers 查無商品 for a
    code taken from the owner's own product URL. Both smell like the same cause:
    we arrive with no session. Round 3 warms a cookie jar on the homepage first.

  eslite — every URL returns the identical 13,583-byte page: a Vue SPA shell
    (vue.runtime + axios + vue-router + pinia) behind Cloudflare. There is no
    server-rendered product HTML to scrape, ever, so the current parser cannot
    work by design. The content arrives over XHR, so round 3 reads the JS bundle
    to find the API base rather than guessing endpoints. The shell also links
    /llms.txt — eslite publishing a machine-readable version of itself — which
    would be the cleanest source of all if it carries product data.

It prints shapes and short samples, never whole pages.

    python tools/probe_sites.py
"""

from __future__ import annotations

import re
import sys
from urllib.parse import urljoin

import requests

sys.path.insert(0, ".")
from config import SETTINGS  # noqa: E402

UA = SETTINGS.user_agent

MOMO_ITEM = "15462752"
ESLITE_PRODUCT = "10042014802683176604005"

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


def title_of(html: str) -> str | None:
    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
    return m.group(1).strip()[:120] if m else None


# --- momo -------------------------------------------------------------------

def probe_momo_with_session() -> None:
    """Warm a cookie jar on the homepage before touching the product/API.

    A bare request has no momo session cookie; that is the most likely reason
    both the page and the API refuse us.
    """
    hr("momo — with a warmed session")
    s = requests.Session()
    s.headers.update(BROWSER_HEADERS)
    try:
        home = s.get("https://www.momoshop.com.tw/", timeout=25)
        print("homepage:", home.status_code, "| title:", title_of(home.text))
        print("cookies after homepage:", list(s.cookies.get_dict()))

        url = f"https://www.momoshop.com.tw/goods/GoodsDetail.jsp?i_code={MOMO_ITEM}"
        page = s.get(url, headers={"Referer": "https://www.momoshop.com.tw/"}, timeout=25)
        print("\nproduct page:", page.status_code, "| bytes:", len(page.text))
        print("title:", title_of(page.text))
        html = page.text
        print("blocked-page marker:", "管理訊息" in html)
        for pat, name in (
            (r'"price"\s*:\s*"?(\d[\d,]*)', '"price"'),
            (r'seoPrice[^0-9]{0,20}(\d[\d,]*)', "seoPrice"),
            (r'itemprop=["\']price["\'][^>]*content=["\']([\d.,]+)', "itemprop=price"),
            (r'og:title["\'][^>]*content=["\']([^"\']{0,80})', "og:title"),
        ):
            m = re.search(pat, html, re.I)
            print(f"   {name}: {m.group(1) if m else None}")

        api = s.post(
            "https://www.momoshop.com.tw/api/moecapp/getGoodsRealTimeInfo",
            json={"goodsCode": MOMO_ITEM},
            headers={
                "Content-Type": "application/json;charset=UTF-8",
                "Accept": "application/json, text/plain, */*",
                "Origin": "https://www.momoshop.com.tw",
                "Referer": url,
                "X-Requested-With": "XMLHttpRequest",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin",
            },
            timeout=20,
        )
        print("\nAPI with session:", api.status_code, "::", api.text[:400])
    except Exception as exc:  # noqa: BLE001
        print("momo session probe failed:", type(exc).__name__, exc)


def probe_momo_search() -> None:
    """momo's search endpoint. If it answers, discovery works even when the
    per-item API does not."""
    hr("momo — search endpoints")
    s = requests.Session()
    s.headers.update(BROWSER_HEADERS)
    try:
        s.get("https://www.momoshop.com.tw/", timeout=20)
    except Exception:  # noqa: BLE001
        pass
    for label, url in (
        ("search page", "https://www.momoshop.com.tw/search/searchShop.jsp?keyword=BEYBLADE"),
        ("mobile search", "https://m.momoshop.com.tw/search.momo?searchKeyword=BEYBLADE"),
    ):
        try:
            r = s.get(url, timeout=25)
            html = r.text
            codes = sorted(set(re.findall(r"i_code=(\d{6,})", html)))
            print(f"   [{label}] {r.status_code} | bytes {len(html)} | title "
                  f"{title_of(html)} | i_codes {len(codes)} {codes[:8]}")
        except Exception as exc:  # noqa: BLE001
            print(f"   [{label}] failed: {type(exc).__name__} {exc}")


# --- eslite -----------------------------------------------------------------

def probe_eslite_llms() -> None:
    """The shell advertises /llms.txt. If eslite publishes a machine-readable
    version of itself, that is a sanctioned source and beats reverse-engineering."""
    hr("eslite /llms.txt")
    for url in ("https://www.eslite.com/llms.txt",
                f"https://www.eslite.com/product/{ESLITE_PRODUCT}.md"):
        try:
            r = requests.get(url, headers={"User-Agent": UA,
                                           "Accept": "text/markdown,text/plain,*/*"},
                             timeout=25)
            print(f"\n{url} -> {r.status_code} | {r.headers.get('content-type')} | "
                  f"{len(r.text)} bytes")
            if r.status_code == 200:
                print(r.text[:1500])
        except Exception as exc:  # noqa: BLE001
            print(f"{url} failed:", type(exc).__name__, exc)


def probe_eslite_bundle() -> None:
    """Read the SPA's own JS to find the API base it calls.

    The page is a Vue shell, so the product data comes over XHR. The bundle
    contains the URLs; that is far more reliable than guessing endpoint names.
    """
    hr("eslite — API endpoints from the JS bundle")
    base = "https://www.eslite.com/"
    try:
        shell = requests.get(base, headers=BROWSER_HEADERS, timeout=25).text
        assets = sorted(set(re.findall(r'src="(/assets/[^"]+\.js)"', shell)))
        assets += sorted(set(re.findall(r'href="(/assets/[^"]+\.js)"', shell)))
        print("asset scripts in shell:", assets[:10])

        seen_hosts: set[str] = set()
        seen_paths: set[str] = set()
        for path in assets[:6]:
            try:
                js = requests.get(urljoin(base, path),
                                  headers={"User-Agent": UA}, timeout=30).text
            except Exception as exc:  # noqa: BLE001
                print(f"   {path}: fetch failed {exc}")
                continue
            print(f"   {path}: {len(js)} bytes")
            for host in re.findall(r'https://([a-z0-9.-]*(?:api|athena|eslite)[a-z0-9.-]*)/',
                                   js, re.I):
                seen_hosts.add(host)
            for p in re.findall(r'["\'`](/api/[a-zA-Z0-9/_\-{}$.]{3,60})["\'`]', js):
                seen_paths.add(p)
        print("\nAPI-ish hosts found:", sorted(seen_hosts)[:20])
        print("API paths found:", sorted(seen_paths)[:40])
    except Exception as exc:  # noqa: BLE001
        print("eslite bundle probe failed:", type(exc).__name__, exc)


if __name__ == "__main__":
    probe_momo_with_session()
    probe_momo_search()
    probe_eslite_llms()
    probe_eslite_bundle()
    print("\n[probe] done")
