export const SITE_URL =
  process.env.NEXT_PUBLIC_SITE_URL ?? 'https://beygear.calc-mates.com'

export const SITE_NAME = 'Beygear 陀螺捕獲情報'

export const SITE_DESCRIPTION =
  '追蹤 Beyblade X 戰鬥陀螺在台灣各通路的上架、售罄、補貨與價格變化。' +
  '每 15 分鐘更新一次,記錄每一次補貨與降價的時間點。'

/**
 * 資料是從 GitHub 直接讀的,不是從這個網站的建置產物讀的。
 *
 * 雷達每 15 分鐘寫一次資料,但網站不會每 15 分鐘重新部署（會爆掉 Vercel 的
 * 每日部署額度）。所以靜態頁面用建置當下的資料預先算好,前端再去抓 GitHub 上
 * 的最新一份覆蓋上去 —— 頁面內容對搜尋引擎是完整的,對使用者則是即時的。
 */
export const LIVE_SNAPSHOT_URL =
  'https://raw.githubusercontent.com/fish0707/beygear/main/data/snapshot.json'

export const REPO_URL = 'https://github.com/fish0707/beygear'

export const PUBLISHER = {
  name: 'Digimate',
  legalName: '數伴有限公司 (Digimate Co., Ltd.)',
  url: 'https://www.digimate.tw',
  location: '台中市',
  founder: 'Chen Chien-Yu',
  founderAlias: 'Fish Chen',
} as const

/** 資料來源,列在站上供查證。 */
export const SOURCES = [
  {
    label: 'momo 購物網 商品搜尋',
    detail: '公開搜尋結果頁,取商品名稱、售價、賣場定價與庫存數',
    href: 'https://www.momoshop.com.tw/',
  },
  {
    label: '誠品線上 商品搜尋 API',
    detail: '誠品前端自己使用的公開搜尋端點,取商品名稱、售價、定價與庫存',
    href: 'https://www.eslite.com/',
  },
] as const
