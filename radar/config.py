"""
Beyblade X 原價開賣雷達 — 設定檔

- 監控清單:要盯哪些商品(商品碼 / 關鍵字 / 平台 / 已知原價)。
- 執行參數:輪詢間隔、「即將開賣」提前提醒的分鐘數。
- 金鑰一律走環境變數 / .env,不硬編碼(見 .env.example)。

原則:此檔只放「設定資料」,不放邏輯。上線前用 DevTools 再確認 momo 端點/參數,
別把易變的 API 細節寫死在這裡。
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional

# --- .env 載入(可選,沒裝 python-dotenv 也能跑,直接讀 os.environ) --------
try:
    from dotenv import load_dotenv  # type: ignore

    load_dotenv()
except Exception:  # pragma: no cover - dotenv 為選配
    pass


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default).strip()


def _env_int(key: str, default: int) -> int:
    raw = _env(key)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


# --- 監控目標 ---------------------------------------------------------------

@dataclass
class Watch:
    """一筆監控目標。

    product_key: 跨平台同款合併用的正規化鍵(例如 "UX-04")。同一顆陀螺在
                 momo / PChome / Funbox 上請用「相同」的 product_key,行事曆
                 才能把它們併成一個事件。
    platform:    "momo" | "pchome" | "funbox"
    item_id:     平台商品識別碼。momo 為 goodsCode;PChome 為 prod id
                 (如 "DGAJ8T-A900AVFV7");funbox 直接填「商品頁完整網址」。
    keyword:     搜尋用關鍵字(給搜尋型 monitor 抓新品用,單品監控可留空)。
    original_price: 已知「原價 / 建議售價」(NT$)。用來判斷觀測到的售價是否為原價。
                    不填則 is_original_price 會是 None(未知)。
    name:        人類可讀名稱(通知/草稿顯示用)。
    """

    product_key: str
    platform: str
    item_id: str = ""
    keyword: str = ""
    original_price: Optional[int] = None
    name: str = ""


# 監控清單 —— 這裡放你要盯的 Beyblade X 商品。
# 範例:UX-04(計畫書驗證用;商品碼與開賣時間以上線前實測為準)。
WATCHES: list[Watch] = [
    # momo 商品碼取自商品頁網址 /product/<code>。原價待確認 —— 先留空，
    # is_original_price 會是 None（未知），等 probe 讀到建議售價再補。
    Watch(
        product_key="UX-03",
        platform="momo",
        item_id="15462752",
        name="BEYBLADE X 戰鬥陀螺（momo 15462752）",
    ),
]


# --- 搜尋 / 發現式監控目標 --------------------------------------------------

@dataclass
class Search:
    """一筆「掃描搜尋頁抓新品」的目標。

    跟 Watch 不同:Watch 是盯「已知商品碼」;Search 是拿關鍵字去掃某商城的
    搜尋/分類頁,把「以前沒看過的 Beyblade X 商品」當新上架通知你。
    首次掃描會先建立基準線(不通知),之後才通知真正的新品。
    """

    platform: str            # "eslite" | (之後可加 momo/pchome 搜尋、toysrus…)
    keyword: str             # 搜尋關鍵字(如 "beyblade")
    name: str = ""           # 這組掃描的人類可讀標籤


# 掃描清單 —— 這裡放「要在哪些商城、用什麼關鍵字掃新品」。
SEARCHES: list[Search] = [
    Search(platform="eslite", keyword="beyblade", name="誠品 Beyblade X 掃描"),
]


# --- 執行參數 ---------------------------------------------------------------

@dataclass
class Settings:
    # 輪詢間隔(秒)。低頻,尊重對方站台;預設 5 分鐘。
    poll_interval_sec: int = field(default_factory=lambda: _env_int("POLL_INTERVAL_SEC", 300))
    # 「即將開賣」提前多少分鐘提醒(進 IMMINENT 狀態)。
    imminent_lead_min: int = field(default_factory=lambda: _env_int("IMMINENT_LEAD_MIN", 30))
    # SQLite 檔路徑。
    db_path: str = field(default_factory=lambda: _env("RADAR_DB_PATH", "radar.db"))
    # HTTP 請求逾時(秒)。
    http_timeout_sec: int = field(default_factory=lambda: _env_int("HTTP_TIMEOUT_SEC", 15))
    # 送出的 User-Agent(擬一般瀏覽器,低頻使用)。
    user_agent: str = field(
        default_factory=lambda: _env(
            "RADAR_USER_AGENT",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
        )
    )

    # --- 通知管道(擇一或都填) ---
    telegram_bot_token: str = field(default_factory=lambda: _env("TELEGRAM_BOT_TOKEN"))
    telegram_chat_id: str = field(default_factory=lambda: _env("TELEGRAM_CHAT_ID"))
    discord_webhook_url: str = field(default_factory=lambda: _env("DISCORD_WEBHOOK_URL"))

    # --- 分潤 ---
    # 蝦皮分潤 ID(過審後填);未填時 draft 只放純導流連結。
    shopee_affiliate_id: str = field(default_factory=lambda: _env("SHOPEE_AFFILIATE_ID"))

    @property
    def has_telegram(self) -> bool:
        return bool(self.telegram_bot_token and self.telegram_chat_id)

    @property
    def has_discord(self) -> bool:
        return bool(self.discord_webhook_url)


SETTINGS = Settings()
