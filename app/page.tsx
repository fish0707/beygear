import Link from 'next/link'
import { ListingTable } from '@/components/ListingTable'
import { LiveBadge } from '@/components/LiveData'
import {
  formatPrice,
  formatTime,
  getMeta,
  isGearKey,
  getModelProducts,
  getProducts,
  platformLabel,
  statusLabel,
} from '@/lib/data'
import { SITE_URL, SOURCES } from '@/lib/site'

export default function Home() {
  const products = getProducts()
  const models = getModelProducts()
  const meta = getMeta()
  const listings = products.flatMap((p) => p.listings)

  // 統計只算陀螺與套裝。誠品那邊多半是書,把 NT$105 的電子書算進「最低有貨價」
  // 會做出一個跟本站主題無關、而且會誤導人的頭條數字。
  const gear = listings.filter((l) => isGearKey(l.product_key))
  const gearInStock = gear.filter((l) => l.available)
  const cheapestGear = gearInStock
    .filter((l) => l.price != null)
    .sort((a, b) => (a.price ?? 0) - (b.price ?? 0))[0]

  // 最近的狀態變化。史料就是這個站唯一無法被複製的東西,所以放在首頁。
  const recent = products
    .flatMap((p) => p.history)
    .sort((a, b) => b.observed_at - a.observed_at)
    .slice(0, 12)

  return (
    <div className="space-y-12">
      <section>
        <h1 className="text-3xl font-bold tracking-tight">
          Beyblade X 現在在台灣哪裡買得到
        </h1>
        <p className="mt-3 max-w-2xl text-muted">
          每 15 分鐘掃一次 momo 與誠品線上的公開商品資料,記錄每一次上架、售罄、
          補貨與價格變動。熱門陀螺售罄後常出現加價轉賣,這個站要回答的是
          「現在還買不買得到、多少錢」。
        </p>
        <p className="mt-3">
          <LiveBadge builtAt={meta.generated_at} />
        </p>
      </section>

      <section className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Stat label="追蹤中陀螺商品" value={String(gear.length)} />
        <Stat label="目前有貨" value={String(gearInStock.length)} />
        <Stat
          label="最低有貨價"
          value={cheapestGear ? formatPrice(cheapestGear.price) : '—'}
        />
        <Stat label="累計變動紀錄" value={String(meta.history_count)} />
      </section>

      {models.length > 0 && (
        <section>
          <h2 className="text-xl font-semibold">依型號查看</h2>
          <p className="mt-1 text-sm text-muted">
            有明確型號的商品各有一頁,記錄它自己的價格與補貨歷史。
          </p>
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            {models.map((p) => (
              <Link
                key={p.product_key}
                href={`/model/${p.product_key}`}
                className="rounded-lg border border-line bg-panel p-4 hover:border-brand"
              >
                <div className="flex items-baseline justify-between">
                  <span className="font-semibold text-brand">{p.product_key}</span>
                  <span className="tabular-nums">{formatPrice(p.lowest_price)}</span>
                </div>
                <p className="mt-1 line-clamp-2 text-sm text-muted">{p.name}</p>
                <p className="mt-2 text-xs text-muted">
                  {p.in_stock_anywhere ? (
                    <span className="text-good">有貨</span>
                  ) : (
                    <span>目前售罄</span>
                  )}
                  {' · '}
                  {p.platforms.map(platformLabel).join('、')}
                </p>
              </Link>
            ))}
          </div>
        </section>
      )}

      <section>
        <h2 className="text-xl font-semibold">全部觀測到的商品</h2>
        <p className="mt-1 mb-4 text-sm text-muted">
          包含套裝組合與誠品的相關書籍。「賣場定價」是通路自己標示的原價,不是原廠建議售價
          —— 兩者的差別寫在<Link href="/about" className="text-brand hover:underline">資料說明</Link>。
        </p>
        <ListingTable listings={listings} />
      </section>

      {recent.length > 0 && (
        <section>
          <h2 className="text-xl font-semibold">最近的變動</h2>
          <p className="mt-1 mb-4 text-sm text-muted">
            只有真的發生變化(新商品、狀態轉換、價格調整)才會留下一筆紀錄。
          </p>
          <ol className="space-y-2">
            {recent.map((h, i) => (
              <li
                key={`${h.platform}:${h.item_id}:${h.observed_at}:${i}`}
                className="flex flex-wrap items-baseline gap-x-3 gap-y-1 rounded border border-line bg-panel px-3 py-2 text-sm"
              >
                <span className="text-xs tabular-nums text-muted">
                  {formatTime(h.observed_at)}
                </span>
                <span className="font-medium">
                  {h.old_status ? `${statusLabel(h.old_status)} → ` : ''}
                  {statusLabel(h.status)}
                </span>
                {h.old_price != null && h.old_price !== h.price && (
                  <span className={h.price! < h.old_price ? 'text-good' : 'text-warn'}>
                    {formatPrice(h.old_price)} → {formatPrice(h.price)}
                  </span>
                )}
                <span className="text-muted">{platformLabel(h.platform)}</span>
                <span className="min-w-0 flex-1 truncate text-muted">{h.name}</span>
              </li>
            ))}
          </ol>
        </section>
      )}

      <section className="rounded-lg border border-line bg-panel p-5 text-sm">
        <h2 className="text-base font-semibold">資料來源</h2>
        <ul className="mt-3 space-y-2 text-muted">
          {SOURCES.map((s) => (
            <li key={s.label}>
              <a href={s.href} target="_blank" rel="nofollow noopener" className="text-brand hover:underline">
                {s.label}
              </a>
              {' — '}
              {s.detail}
            </li>
          ))}
        </ul>
      </section>

      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify({
            '@context': 'https://schema.org',
            '@type': 'CollectionPage',
            '@id': `${SITE_URL}/#webpage`,
            url: SITE_URL,
            name: 'Beyblade X 現在在台灣哪裡買得到',
            isPartOf: { '@id': `${SITE_URL}/#website` },
            publisher: { '@id': `${SITE_URL}/#publisher` },
            dateModified: new Date(meta.generated_at * 1000).toISOString(),
          }),
        }}
      />
    </div>
  )
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-line bg-panel p-4">
      <div className="text-xs text-muted">{label}</div>
      <div className="mt-1 text-xl font-semibold tabular-nums">{value}</div>
    </div>
  )
}
