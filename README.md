# Beygear — Beyblade X 原價開賣雷達

跨平台監控 Beyblade X 商品的**上架、售罄、補貨與價格**，在回到**原價**時通知，
並把累積的觀測公開成情報站。

熱門陀螺秒殺後常見加價轉賣，「哪裡還買得到原價」才是真正的問題 —— 這是本專案的核心。

## 組成

| 目錄 | 內容 |
|------|------|
| `radar/` | Python 監控器（momo / PChome / Funbox / 誠品）、狀態機、Telegram 通知 |
| `data/`  | 雷達產出的資料：`radar.db`（狀態）與網站用的 JSON 快照 |
| `.github/workflows/radar.yml` | 每 15 分鐘雲端執行一輪 |

## 資料流

```
GitHub Actions（每 15 分鐘）
  → radar/run.py --once      讀寫 data/radar.db，變動時發 Telegram
  → radar/export_web.py      匯出 data/{snapshot,products,meta}.json
  → 有變動才 commit          （避免灌爆 Vercel 每日部署額度）
```

**`data/radar.db` 必須進版控。** GitHub Actions 每次執行都是全新容器，狀態不進 repo
就跨不了輪次 —— 每一輪都會像第一次看到商品，補貨永遠偵測不到。

## 為什麼歷史要另存一張表

`events` 表以 `(platform, item_id)` 為唯一鍵、每次觀測就覆寫，只保留「當下狀態」。
`history` 表則在**每次有意義的變化**（新商品、狀態轉換、降價）追加一列，
價格與補貨的時間序列才留得下來 —— 這份時間序列是本站唯一無法被複製的資產。

## 設定

Repo → Settings → Secrets and variables → Actions：

| Secret | 用途 |
|--------|------|
| `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` | Telegram 通知 |
| `DISCORD_WEBHOOK_URL` | Discord 通知（可替代 Telegram） |
| `SHOPEE_AFFILIATE_ID` | 蝦皮分潤連結（可選） |

監控清單在 `radar/config.py`。

## 本地執行

```bash
cd radar
pip install -r requirements.txt
python run.py --once                  # 跑一輪
python export_web.py --db radar.db --out ../data
python -m pytest tests/ -q            # 44 tests
```
