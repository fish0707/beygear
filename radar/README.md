# Beyblade X 原價開賣情報・個人雷達

自動盯各購物平台,在 **Beyblade X「原價」商品**開賣 / 上架 / **補貨**時**通知你自己**(Telegram / Discord),
並生成帶**蝦皮分潤連結**的貼文草稿,由你審核後手動貼到 Threads / IG / FB。

> **個人雷達,不公開帳號、不自動發文**。系統只通知你、發文你自己貼。
> 不做社群自動發文 API(省掉審核最嚴的部分)。

## 為什麼這樣設計(關鍵結論)

- **分潤只押蝦皮**:momo 分潤(點點賺)已於 **2026/01/31 停止**,個人分潤主力只剩
  [蝦皮分潤計畫](https://affiliate.shopee.tw)(商城約 2–5%,需先申請:約 300 追蹤、審核約 5 工作天、滿 NT$500 提領)。
  momo / PChome / Funbox 只能純導流。過審前草稿放純導流連結即可。
- **最好自動監控(有 API/JSON)**:momo(`getGoodsRealTimeInfo`)、PChome(公開 JSON)、Funbox 官網(SHOPLINE)。
- **難抓**(超商限量、誠品、粉專公告)→ 用 `feed_manual.py` 人工餵進同一行事曆,不硬爬。
- **LINE Notify 已停用** → 通知走 **Telegram bot** 或 **Discord webhook**。

## 架構

```
監控層(自動)          統一行事曆(核心)        通知 + 草稿(給你)
monitors/momo.py  ─┐                          ┌─ notify.py   (Telegram/Discord)
monitors/pchome.py ─┼─▶ calendar_db.py (SQLite) ─┤
monitors/funbox.py ─┘   去重/跨平台合併/狀態機   └─ draft.py    (貼文草稿+蝦皮連結)
feed_manual.py ─────────▶ (人工餵料走同一路徑)
run.py = 排程主迴圈(常駐 or --once 給 cron/GitHub Actions)
```

**狀態機**:`預告(ANNOUNCED) → 即將開賣(IMMINENT) → 已上架/開賣(ON_SALE) → 售罄(SOLD_OUT) → 回補(RESTOCKED)`。
最想被通知的訊號是 **RESTOCKED 且為原價**(秒殺後常見加價轉賣,回到原價才值得搶)。

**兩種監控方式**:
- **盯已知商品碼**(`WATCHES`):Watch 指定商品碼,追它的價格/庫存/開賣時間變化。
- **掃搜尋頁抓新品**(`SEARCHES`,發現式):拿關鍵字掃某商城搜尋頁,「以前沒看過的
  Beyblade X 商品」就當**新商品上架**通知你(如誠品 eslite)。首次掃描先建立基準線
  (不通知),之後才通知真正的新品,避免第一輪洗版。**加新商城 = 加一個 adapter**
  (照 `monitors/eslite.py` 抄)。

## 檔案

| 檔案 | 狀態 | 說明 |
|------|------|------|
| `config.py` | ✅ | 監控清單(`WATCHES`)、輪詢間隔、金鑰(env) |
| `monitors/momo.py` | ✅ MVP | momo `getGoodsRealTimeInfo`,回開賣時間戳/庫存/價格 |
| `monitors/base.py` | ✅ | `ProductSnapshot` 統一格式 + monitor 介面 |
| `calendar_db.py` | ✅ MVP | SQLite 行事曆:去重、跨平台合併、狀態機、變更偵測 |
| `notify.py` | ✅ MVP | Telegram / Discord 通知 + 訊息格式化 |
| `draft.py` | ✅ | 貼文草稿(自寫摘要)+ 蝦皮分潤/導流連結 |
| `feed_manual.py` | ✅ | 人工餵料(超商/粉專公告),走同一 upsert/狀態機/通知 |
| `run.py` | ✅ | 排程主迴圈 |
| `monitors/pchome.py` | ✅ 階段二 | PChome 公開 JSON(Price P/M、Qty);市價 M 可當原價後備 |
| `monitors/funbox.py` | ✅ 階段二 | Funbox SHOPLINE:解析商品頁 JSON-LD(Offer 的 price/availability) |
| `monitors/discovery.py` | ✅ | 發現式監控基底(掃搜尋頁抓新品),一站一個 adapter |
| `monitors/eslite.py` | ✅ | 誠品線上:掃搜尋頁 → 新上架就通知(★需真實 HTML 校準) |

## 快速開始

```bash
cd beyblade-radar
pip install -r requirements.txt
cp .env.example .env          # 填 Telegram/Discord;分潤先留空
python -m unittest discover -s tests   # 跑測試(21 項,無需金鑰)

python run.py --once          # 跑一輪(cron 模式)
python run.py                 # 常駐,每 POLL_INTERVAL_SEC 一輪
```

要盯哪些商品,改 `config.py` 的 `WATCHES`(商品碼 / 平台 / 已知原價)。
同一顆陀螺在不同平台請用**相同 `product_key`**,行事曆才會跨平台合併。

**人工餵一筆情報**(例:超商限量):

```bash
python feed_manual.py --key UX-05 --platform seven --name "UX-05 超商限量" \
  --price 390 --original-price 390 --on-sale "2026-08-01 00:00" --stock 30 --available
```

## 部署(要可靠命中 00:00 開賣通知)

單機只有開機才跑,建議放**常開主機**或用**雲端排程**:

- **常開主機**(Raspberry Pi / 便宜雲主機):`cron` 每 N 分鐘跑 `python run.py --once`,
  或直接 `python run.py` 常駐。SQLite 會保存上一輪狀態,能正確偵測「售罄→回補」。
- **GitHub Actions**:已附 [`.github/workflows/beyblade-radar.yml`](../.github/workflows/beyblade-radar.yml),
  在 repo Secrets 填 `TELEGRAM_BOT_TOKEN` 等即可雲端定時跑。
  ⚠️ serverless 不跨輪保存 `radar.db`,所以「售罄→回補」這種**跨輪狀態變更**偵測不到;
  「即將開賣 / 新上架」提醒不受影響。要完整狀態機請用常開主機或自備持久化 DB。

## 來源分級(本專案原則)

不是所有「網路上看得到的情報」都能用同一種方式取得。加新來源前先分級:

| 級別 | 例子 | 可以怎麼用 |
|---|---|---|
| **第一手**:零售商自己的公開商品頁 | momo、PChome、Funbox、誠品 | 可低頻自動抓**公開事實**(價格/庫存/上架/開賣時間) |
| **彙整站**:別人整理好的情報資料庫 | beybladehub.app 之類 | **只接站方主動提供的 feed / API,或取得授權;不爬清單頁** |

彙整站的價值來自站方投入人力蒐集、正規化資料。整批複製他人彙整的資料庫,與抓第一手公開
事實**性質不同**(參 Lawsnote 判例)。沒有 feed 就走人工餵料(`feed_manual.py`),
不要寫爬蟲繞過這條線。

接新來源前,先跑探測腳本確認站方有沒有提供 feed:

```bash
python tools/probe_feed.py https://要探測的網站/
```

它會唯讀檢查 `robots.txt`、常見 feed 路徑、首頁的 feed 宣告與內嵌資料,並印出判讀提示。
(JS 動態載入的請求它看不到,需另用 DevTools → Network → Fetch/XHR 確認。)

## 校準抓取器(上線前必做)

發現式 adapter(如 `monitors/eslite.py`)的選擇器需要用**真實 HTML** 對準,因為各站
結構會改版,且開發環境無法連外。步驟:

1. 用瀏覽器開誠品搜尋頁(如 `https://www.eslite.com/search?keyword=beyblade`),F12 開
   DevTools。
2. 看資料從哪來:多半是 `__NEXT_DATA__` 內嵌 JSON,或某個 `/api/...` 搜尋 API 回 JSON,
   或商品頁 JSON-LD。`eslite.py` 三種都試(`extract_products`),但欄位名稱可能要微調。
3. 把一份真實搜尋結果存成 HTML,丟進 `EsliteMonitor.parse_search()` 跑一次,確認有正確
   撈到商品 id / 名稱 / 價格。對不到就改 `_walk_product_like` 的候選欄位名。

> 加其他商城(ToysRUs / 博客來 / 蝦皮…):複製 `eslite.py` 換 `SEARCH_URL` 與抽取邏輯即可。
> 蝦皮反爬強,建議低頻或改人工。

## 關鍵約束與風險

- **法律 / 合規**:只抓公開「事實資料」(價格 / 上架 / 庫存 / 時間)、**低頻**、遵守 robots.txt、
  不繞登入牆、不整批複製他人資料庫(參 Lawsnote 判例)。貼文用**自寫摘要 + 自拍/官方素材**,
  勿轉原圖原文。分潤連結**明示「內含推廣」**(`draft.py` 已內建揭露句)。
- **蝦皮反爬強** → 只做人工 + 分潤連結,別硬爬。
- **momo 會改版**:`getGoodsRealTimeInfo` 端點/欄位可能變動。`monitors/momo.py` 已做防呆解析
  (欄位缺漏不炸整輪),但上線前請用 DevTools Network 再確認一次端點/參數。
- **金鑰不硬編碼**:全走環境變數 / `.env`(見 `.env.example`);`.env` 與 `*.db` 已在 `.gitignore`。

## 分階段

- **MVP(已完成)**:momo monitor + calendar_db + notify + draft + feed_manual + run。
- **階段二(已完成)**:`monitors/pchome.py`(公開 JSON)、`monitors/funbox.py`(JSON-LD)。
  三平台同款用相同 `product_key` 自動合併,`by_product_key()` 可查各平台現況。
- **階段三**:蝦皮分潤過審後,把 `draft.py` 的 `shopee_link` 換成分潤後台產生的正式連結。

共 33 項單元測試(momo / pchome / funbox 解析 + 行事曆狀態機 + 通知 + 草稿),
全部不需金鑰、不打真實網路。

## 測試

```bash
python -m unittest discover -s tests -v
```

涵蓋:momo 回應解析(含缺欄防呆)、狀態機五態轉換、去重、跨平台合併、原價判斷、
價格下跌偵測、通知訊息格式、草稿含推廣揭露。全部不需金鑰、不打真實網路。
