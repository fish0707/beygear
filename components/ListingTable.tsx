'use client'

import { useMemo, useState } from 'react'
import type { Listing } from '@/lib/data'
import { formatStock, isGearKey } from '@/lib/format'
import { useLiveSnapshot } from './LiveData'

function price(n: number | null | undefined) {
  return n == null ? '—' : `NT$${n.toLocaleString('zh-TW')}`
}

const PLATFORMS: Record<string, string> = {
  momo: 'momo',
  eslite: '誠品',
  pchome: 'PChome',
  funbox: 'Funbox',
}

/**
 * 全部觀測到的架上商品。
 *
 * 排序預設「陀螺排在書前面,有貨的排前面,再依價格由低到高」—— 這個站要回答
 * 的問題是「現在最便宜買得到哪一顆陀螺」。純照價格排會讓誠品的百元電子書佔滿
 * 前幾行,把真正要找的東西壓到看不見的地方。
 */
export function ListingTable({ listings }: { listings: Listing[] }) {
  const live = useLiveSnapshot()
  const [onlyInStock, setOnlyInStock] = useState(false)
  const [platform, setPlatform] = useState<string>('all')

  const rows = useMemo(() => {
    const merged = listings.map((l) => {
      const fresh = live?.byItem.get(`${l.platform}:${l.item_id}`)
      return fresh ? { ...l, ...fresh } : l
    })
    const filtered = merged.filter(
      (l) =>
        (!onlyInStock || l.available) &&
        (platform === 'all' || l.platform === platform)
    )
    return filtered.sort((a, b) => {
      const gearA = isGearKey(a.product_key)
      const gearB = isGearKey(b.product_key)
      if (gearA !== gearB) return gearA ? -1 : 1
      if (a.available !== b.available) return a.available ? -1 : 1
      return (a.price ?? Infinity) - (b.price ?? Infinity)
    })
  }, [listings, live, onlyInStock, platform])

  const platforms = Array.from(new Set(listings.map((l) => l.platform))).sort()

  return (
    <div>
      <div className="mb-3 flex flex-wrap items-center gap-3 text-sm">
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={onlyInStock}
            onChange={(e) => setOnlyInStock(e.target.checked)}
            className="accent-brand"
          />
          只看有貨
        </label>
        <label className="flex items-center gap-2">
          通路
          <select
            value={platform}
            onChange={(e) => setPlatform(e.target.value)}
            className="rounded border border-line bg-panel px-2 py-1"
          >
            <option value="all">全部</option>
            {platforms.map((p) => (
              <option key={p} value={p}>
                {PLATFORMS[p] ?? p}
              </option>
            ))}
          </select>
        </label>
        <span className="text-muted">{rows.length} 筆</span>
      </div>

      <div className="overflow-x-auto rounded-lg border border-line">
        <table className="w-full min-w-[42rem] text-sm">
          <thead className="bg-panel text-left text-muted">
            <tr>
              <th className="px-3 py-2 font-medium">商品</th>
              <th className="px-3 py-2 font-medium">通路</th>
              <th className="px-3 py-2 text-right font-medium">售價</th>
              <th className="px-3 py-2 text-right font-medium">賣場定價</th>
              <th className="px-3 py-2 text-right font-medium">庫存</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((l) => (
              <tr key={`${l.platform}:${l.item_id}`} className="border-t border-line">
                <td className="px-3 py-2">
                  <a
                    href={l.url}
                    target="_blank"
                    rel="nofollow noopener"
                    className="text-brand hover:underline"
                  >
                    {l.name}
                  </a>
                </td>
                <td className="px-3 py-2 text-muted">{PLATFORMS[l.platform] ?? l.platform}</td>
                <td className="px-3 py-2 text-right tabular-nums">{price(l.price)}</td>
                <td className="px-3 py-2 text-right tabular-nums text-muted">
                  {price(l.original_price)}
                </td>
                <td className="px-3 py-2 text-right tabular-nums">
                  {l.available ? (
                    <span className="text-good">{formatStock(l.stock)}</span>
                  ) : (
                    <span className="text-muted">售罄</span>
                  )}
                </td>
              </tr>
            ))}
            {rows.length === 0 && (
              <tr>
                <td colSpan={5} className="px-3 py-6 text-center text-muted">
                  這個條件下目前沒有紀錄。
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
