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


# 監控清單 —— 盯「已知商品碼」的目標。
#
# 目前是空的,而且 momo 不在這裡:實測 momo 的單品即時資訊 API 對機房 IP 一律
# 回「查無商品」,商品頁也被換成擋機器人頁,所以盯商品碼這條路走不通。momo 改
# 走下面的 SEARCHES —— 搜尋頁本身就內嵌完整商品資料。PChome / Funbox 之後要
# 盯單品時再往這裡加。
WATCHES: list[Watch] = []


# --- 已知建議售價 -----------------------------------------------------------

# 型號 → 台灣建議售價(NT$)。這是雷達的重點判斷依據:秒殺後的加價轉賣要能
# 一眼看出來,就得知道原價是多少。
#
# 沒列在這裡的型號會退回用平台自己標的原價(momo goodsPriceOri / 誠品
# mprice)。那是「該賣場的定價」,不等於原廠建議售價,只是備援。查證過一款
# 再往這裡加一款,不要憑印象填。
ORIGINAL_PRICES: dict[str, int] = {}


# --- 搜尋 / 發現式監控目標 --------------------------------------------------

@dataclass
class Search:
    """一筆「掃描搜尋頁抓新品」的目標。

    跟 Watch 不同:Watch 是盯「已知商品碼」;Search 是拿關鍵字去掃某商城的
    搜尋/分類頁,把「以前沒看過的 Beyblade X 商品」當新上架通知你。
    首次掃描會先建立基準線(不通知),之後才通知真正的新品。
    """

    platform: str            # "momo" | "eslite" | (之後可加 pchome、toysrus…)
    keyword: str             # 搜尋關鍵字(如 "beyblade")
    name: str = ""           # 這組掃描的人類可讀標籤


# 掃描清單 —— 這裡放「要在哪些商城、用什麼關鍵字掃新品」。
#
# momo 用中文「戰鬥陀螺」比英文 BEYBLADE 涵蓋得廣(台灣商品名多半是中文),
# 兩個都掃,重複的會依商品碼去重。誠品用「戰鬥陀螺」才掃得到東西 ——
# 用 "beyblade" 只會命中賭博默示錄那類書,因為它是模糊比對。
SEARCHES: list[Search] = [
    Search(platform="momo", keyword="戰鬥陀螺", name="momo 戰鬥陀螺掃描"),
    Search(platform="momo", keyword="BEYBLADE", name="momo BEYBLADE 掃描"),
    Search(platform="eslite", keyword="戰鬥陀螺", name="誠品戰鬥陀螺掃描"),
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
