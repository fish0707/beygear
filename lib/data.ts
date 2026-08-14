import { readFileSync } from 'fs'
import path from 'path'
import { isModelKey } from './format'

export * from './format'

export type Listing = {
  product_key: string
  platform: string
  item_id: string
  name: string
  url: string
  price: number | null
  original_price: number | null
  stock: number | null
  status: string
  available: boolean
  is_original_price: boolean | null
  markup_pct: number | null
  first_seen_at: number
  last_updated_at: number
  on_sale_ts: number | null
}

export type HistoryRow = {
  product_key: string
  platform: string
  item_id: string
  name: string
  url: string
  status: string
  old_status: string | null
  price: number | null
  old_price: number | null
  stock: number | null
  observed_at: number
}

export type Product = {
  product_key: string
  name: string
  platforms: string[]
  listings: Listing[]
  history: HistoryRow[]
  restock_count: number
  in_stock_anywhere: boolean
  at_or_below_list_price: boolean
  available_at_msrp: boolean | null
  lowest_price: number | null
  list_price: number | null
  msrp: number | null
  last_updated_at: number
}

export type Meta = {
  generated_at: number
  product_count: number
  listing_count: number
  history_count: number
  in_stock_count: number
  at_msrp_count: number
  msrp_known_count: number
}

function read<T>(file: string): T {
  return JSON.parse(
    readFileSync(path.join(process.cwd(), 'data', file), 'utf8')
  ) as T
}

export function getProducts(): Product[] {
  return read<{ products: Product[] }>('products.json').products
}

export function getMeta(): Meta {
  return read<Meta>('meta.json')
}

/**
 * 只有「有型號」的商品會有自己的頁面。
 *
 * 套裝與誠品的書留在首頁的總表裡就好 —— 它們每一筆能講的內容就是一行價格,
 * 硬拆成獨立頁面只會做出一堆沒有內容的頁,對讀者和搜尋引擎都沒有意義。
 */
export function getModelProducts(): Product[] {
  return getProducts()
    .filter((p) => isModelKey(p.product_key))
    .sort((a, b) => a.product_key.localeCompare(b.product_key))
}
