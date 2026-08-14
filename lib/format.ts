/**
 * 純顯示與分類的小工具,不碰檔案系統。
 *
 * 這些必須跟 lib/data.ts 分開:data.ts 用 fs 在建置時讀 JSON,而 client
 * component 也需要這幾個函式。兩者放在一起的話,webpack 會試著把 fs 打包進
 * 瀏覽器端而編譯失敗。
 */

export function formatPrice(n: number | null | undefined): string {
  return n == null ? '—' : `NT$${n.toLocaleString('zh-TW')}`
}

export function formatTime(unix: number): string {
  return new Date(unix * 1000).toLocaleString('zh-TW', {
    timeZone: 'Asia/Taipei',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

/**
 * 誠品的電子書用一個哨兵值代表「不限量」(觀測到 100999997、99999998)。
 * 照著印出來會變成一個荒謬的數字,所以超過這個門檻一律當作不限量。
 */
const UNLIMITED_STOCK = 100_000

export function formatStock(n: number | null | undefined): string {
  if (n == null) return '有貨'
  return n >= UNLIMITED_STOCK ? '不限量' : n.toLocaleString('zh-TW')
}

/**
 * 陀螺本體 / 套裝,相對於誠品那邊的書與周邊。
 *
 * 首頁的「最低價」這種統計只能算陀螺 —— 誠品的電子書 NT$105 會把它拉到一個
 * 跟本站主題無關的數字上,看起來像是陀螺只要一百元。
 */
export function isGearKey(key: string): boolean {
  return !key.startsWith('eslite-')
}

/** 型號代碼(BX/UX/CX-NN)才是真正的商品;其餘是套裝或誠品的書。 */
const MODEL_KEY = /^(BX|UX|CX)-\d{2}$/

export function isModelKey(key: string): boolean {
  return MODEL_KEY.test(key)
}

export function platformLabel(platform: string): string {
  return (
    { momo: 'momo 購物網', eslite: '誠品線上', pchome: 'PChome', funbox: 'Funbox' }[
      platform
    ] ?? platform
  )
}

export function statusLabel(status: string): string {
  return (
    {
      ON_SALE: '販售中',
      SOLD_OUT: '售罄',
      RESTOCKED: '補貨',
      ANNOUNCED: '已公布',
      IMMINENT: '即將開賣',
    }[status] ?? status
  )
}
