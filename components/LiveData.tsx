'use client'

import { useEffect, useState } from 'react'
import { LIVE_SNAPSHOT_URL } from '@/lib/site'

type LiveListing = {
  product_key: string
  platform: string
  item_id: string
  price: number | null
  stock: number | null
  available: boolean
  status: string
}

export type Live = {
  generatedAt: number
  byItem: Map<string, LiveListing>
} | null

/**
 * 抓 GitHub 上最新的一份 snapshot,用來蓋掉建置當下的數字。
 *
 * 雷達每 15 分鐘更新,但網站不會跟著重新部署。沒有這一步,使用者看到的就是
 * 上次部署當下的庫存 —— 對一個「現在還買不買得到」的站來說那等於沒用。
 * 靜態內容仍然完整,所以搜尋引擎讀到的頁面不受影響。
 */
export function useLiveSnapshot(): Live {
  const [live, setLive] = useState<Live>(null)

  useEffect(() => {
    let cancelled = false
    fetch(LIVE_SNAPSHOT_URL, { cache: 'no-store' })
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (cancelled || !data?.listings) return
        const byItem = new Map<string, LiveListing>()
        for (const l of data.listings as LiveListing[]) {
          byItem.set(`${l.platform}:${l.item_id}`, l)
        }
        setLive({ generatedAt: data.generated_at, byItem })
      })
      .catch(() => {
        // 抓不到就維持建置當下的資料,頁面照常可讀。
      })
    return () => {
      cancelled = true
    }
  }, [])

  return live
}

export function LiveBadge({ builtAt }: { builtAt: number }) {
  const live = useLiveSnapshot()
  const at = live?.generatedAt ?? builtAt
  const fresh = live != null

  return (
    <span className="inline-flex items-center gap-2 text-xs text-muted">
      <span
        className={`inline-block h-2 w-2 rounded-full ${fresh ? 'bg-good' : 'bg-muted'}`}
        aria-hidden
      />
      資料更新於{' '}
      {new Date(at * 1000).toLocaleString('zh-TW', {
        timeZone: 'Asia/Taipei',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
      })}
      {fresh ? '（即時）' : ''}
    </span>
  )
}
