"""探測某網站是否「主動提供」feed / API —— 在接入新情報來源前先跑這支。

用途:彙整站(例如 beybladehub.app)的資料是站方投入人力整理的,整批爬取有法律風險
(參 Lawsnote 判例)。本專案的原則是:**彙整站只接站方主動提供的 feed / API**。
這支腳本就是用來回答「它到底有沒有提供」。

它只做唯讀探測:抓 robots.txt、試常見 feed 路徑、看首頁有沒有 feed 宣告 / 內嵌 JSON,
然後印出摘要。低頻、單執行緒、送可辨識的 User-Agent,不繞任何登入牆。

用法:
    python tools/probe_feed.py https://beybladehub.app/

把輸出貼回來,就能判斷要走「接 feed」還是「人工餵料」。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from urllib.parse import urljoin, urlparse

import requests

# 誠實標示身分,而非偽裝瀏覽器 —— 消費他人 feed 的基本禮節。
UA = "beyblade-radar-feed-probe/1.0 (checking for a public feed before any integration)"
TIMEOUT = 15
PAUSE_SEC = 1.0  # 每個請求間隔,低頻

COMMON_PATHS = [
    "robots.txt", "sitemap.xml", "sitemap_index.xml",
    "rss", "rss.xml", "feed", "feed.xml", "atom.xml", "index.xml",
    "manifest.json", "api", "api/releases", "api/products", "api/items",
]

FEEDISH = ("xml", "rss", "atom", "json")


def get(url: str) -> tuple[int, str, str]:
    """回 (status, content_type, body 前段)。失敗回 (0, 錯誤訊息, '')。"""
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=TIMEOUT)
        return r.status_code, r.headers.get("Content-Type", ""), r.text[:4000]
    except requests.RequestException as exc:
        return 0, f"ERROR: {exc}", ""


def probe_paths(base: str) -> list[tuple[str, int, str, str]]:
    found = []
    for p in COMMON_PATHS:
        url = urljoin(base, p)
        status, ctype, body = get(url)
        found.append((url, status, ctype, body))
        time.sleep(PAUSE_SEC)
    return found


def inspect_home(base: str) -> dict:
    status, ctype, body = get(base)
    info: dict = {"status": status, "content_type": ctype, "len": len(body)}
    if status != 200:
        info["error"] = ctype
        return info

    # 1) <link rel="alternate"> feed 宣告
    info["alternate_links"] = re.findall(
        r'<link[^>]+rel=["\']alternate["\'][^>]*>', body, re.I
    )[:10]
    # 2) Next.js 內嵌資料
    info["has_next_data"] = bool(
        re.search(r'id=["\']__NEXT_DATA__["\']', body, re.I)
    )
    m = re.search(r'"buildId"\s*:\s*"([^"]+)"', body)
    info["next_build_id"] = m.group(1) if m else None
    # 3) JSON-LD
    info["jsonld_blocks"] = len(
        re.findall(r'type=["\']application/ld\+json["\']', body, re.I)
    )
    # 4) 內文出現的 API 端點線索
    info["api_hints"] = sorted(set(re.findall(r'["\'](/api/[a-z0-9\-_/]+)["\']', body, re.I)))[:12]
    # 5) 第三方後端(私有,不算公開 feed)
    info["backends"] = sorted(set(re.findall(
        r'([a-z0-9\-]+\.(?:supabase\.co|firebaseio\.com|firebaseapp\.com|algolia\.net))', body, re.I
    )))[:6]
    return info


def summarize(url: str, status: int, ctype: str, body: str) -> str:
    if status == 0:
        return f"  ✗ {url}\n      {ctype}"
    tag = "✓" if status == 200 else "·"
    line = f"  {tag} [{status}] {url}  ({ctype.split(';')[0] or '?'})"
    if status == 200 and body.strip():
        looks_feed = any(k in ctype.lower() for k in FEEDISH) or body.lstrip()[:1] in "<{["
        if looks_feed:
            preview = " ".join(body.strip()[:220].split())
            line += f"\n      ↳ {preview}"
    return line


def main() -> int:
    ap = argparse.ArgumentParser(description="探測網站是否提供公開 feed / API")
    ap.add_argument("url", help="站台首頁,例如 https://beybladehub.app/")
    args = ap.parse_args()

    base = args.url if args.url.endswith("/") else args.url + "/"
    host = urlparse(base).netloc
    print(f"=== 探測 {host} ===\n(唯讀、低頻、UA 已標示身分)\n")

    print("--- 1) 首頁分析 ---")
    home = inspect_home(base)
    print(json.dumps(home, ensure_ascii=False, indent=2))
    print()

    print("--- 2) 常見 feed / API 路徑 ---")
    for url, status, ctype, body in probe_paths(base):
        print(summarize(url, status, ctype, body))
    print()

    print("--- 3) 判讀提示 ---")
    print("  • robots.txt 有 Sitemap: → 照那個網址再抓一次看內容")
    print("  • 出現 rss/atom/feed 且回 200 XML → 站方有提供 feed,可以接")
    print("  • 只有 __NEXT_DATA__ / supabase 等私有後端 → 不算公開 feed,走人工餵料")
    print("  • robots.txt 明文 Disallow 相關路徑 → 不要抓,走人工餵料")
    print("\n  DevTools 補充(腳本看不到 JS 載入的請求):")
    print("  F12 → Network → 篩 Fetch/XHR → 重整,看清單資料來自哪個 JSON 請求。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
