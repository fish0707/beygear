import type { Metadata } from 'next'
import Link from 'next/link'
import { notFound } from 'next/navigation'
import { LiveBadge } from '@/components/LiveData'
import {
  formatPrice,
  formatStock,
  formatTime,
  getMeta,
  getModelProducts,
  platformLabel,
  statusLabel,
} from '@/lib/data'
import { SITE_URL } from '@/lib/site'

export function generateStaticParams() {
  return getModelProducts().map((p) => ({ code: p.product_key }))
}

export function generateMetadata({ params }: { params: { code: string } }): Metadata {
  const p = getModelProducts().find((x) => x.product_key === params.code)
  if (!p) return {}
  const where = p.in_stock_anywhere
    ? `目前有貨,最低 ${formatPrice(p.lowest_price)}`
    : '目前各通路皆售罄'
  return {
    title: `${p.product_key} 價格與補貨紀錄`,
    description: `Beyblade X ${p.product_key}(${p.name})在台灣通路的售價、庫存與補貨歷史。${where}。`,
    alternates: { canonical: `/model/${p.product_key}` },
  }
}

export default function ModelPage({ params }: { params: { code: string } }) {
  const product = getModelProducts().find((p) => p.product_key === params.code)
  if (!product) notFound()

  const meta = getMeta()
  const history = [...product.history].sort((a, b) => b.observed_at - a.observed_at)
  const prices = product.history.map((h) => h.price).filter((p): p is number => p != null)
  const low = prices.length ? Math.min(...prices) : null
  const high = prices.length ? Math.max(...prices) : null

  return (
    <div className="space-y-10">
      <nav className="text-sm text-muted">
        <Link href="/" className="hover:text-slate-100">
          現在有貨
        </Link>
        {' / '}
        <span>{product.product_key}</span>
      </nav>

      <section>
        <h1 className="text-3xl font-bold tracking-tight">
          {product.product_key}
        </h1>
        <p className="mt-2 text-muted">{product.name}</p>
        <p className="mt-3">
          <LiveBadge builtAt={meta.generated_at} />
        </p>
      </section>

      <section className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Stat
          label="目前狀態"
          value={product.in_stock_anywhere ? '有貨' : '售罄'}
          tone={product.in_stock_anywhere ? 'good' : 'muted'}
        />
        <Stat label="目前最低價" value={formatPrice(product.lowest_price)} />
        <Stat
          label="觀測價格區間"
          value={low != null && high != null ? `${formatPrice(low)} – ${formatPrice(high)}` : '—'}
        />
        <Stat label="補貨次數" value={String(product.restock_count)} />
      </section>

      <section>
        <h2 className="text-xl font-semibold">各通路目前狀況</h2>
        <div className="mt-4 overflow-x-auto rounded-lg border border-line">
          <table className="w-full min-w-[36rem] text-sm">
            <thead className="bg-panel text-left text-muted">
              <tr>
                <th className="px-3 py-2 font-medium">通路</th>
                <th className="px-3 py-2 font-medium">商品</th>
                <th className="px-3 py-2 text-right font-medium">售價</th>
                <th className="px-3 py-2 text-right font-medium">庫存</th>
              </tr>
            </thead>
            <tbody>
              {product.listings.map((l) => (
                <tr key={`${l.platform}:${l.item_id}`} className="border-t border-line">
                  <td className="px-3 py-2 text-muted">{platformLabel(l.platform)}</td>
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
                  <td className="px-3 py-2 text-right tabular-nums">{formatPrice(l.price)}</td>
                  <td className="px-3 py-2 text-right tabular-nums">
                    {l.available ? (
                      <span className="text-good">{formatStock(l.stock)}</span>
                    ) : (
                      <span className="text-muted">售罄</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section>
        <h2 className="text-xl font-semibold">變動紀錄</h2>
        <p className="mt-1 mb-4 text-sm text-muted">
          每一筆都是雷達實際觀測到的變化。沒有變化的輪次不會留下紀錄,所以這份清單
          就是這個型號從被發現到現在的完整時間軸。
        </p>
        <ol className="space-y-2">
          {history.map((h, i) => (
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
              {h.old_price != null && h.old_price !== h.price ? (
                <span className={h.price! < h.old_price ? 'text-good' : 'text-warn'}>
                  {formatPrice(h.old_price)} → {formatPrice(h.price)}
                </span>
              ) : (
                <span className="tabular-nums text-muted">{formatPrice(h.price)}</span>
              )}
              <span className="text-muted">{platformLabel(h.platform)}</span>
            </li>
          ))}
        </ol>
      </section>

      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify({
            '@context': 'https://schema.org',
            '@graph': [
              {
                '@type': 'BreadcrumbList',
                itemListElement: [
                  { '@type': 'ListItem', position: 1, name: '現在有貨', item: SITE_URL },
                  {
                    '@type': 'ListItem',
                    position: 2,
                    name: product.product_key,
                    item: `${SITE_URL}/model/${product.product_key}`,
                  },
                ],
              },
              {
                '@type': 'Product',
                name: `Beyblade X ${product.product_key}`,
                description: product.name,
                sku: product.product_key,
                offers: product.listings
                  .filter((l) => l.price != null)
                  .map((l) => ({
                    '@type': 'Offer',
                    price: l.price,
                    priceCurrency: 'TWD',
                    url: l.url,
                    availability: l.available
                      ? 'https://schema.org/InStock'
                      : 'https://schema.org/OutOfStock',
                    seller: { '@type': 'Organization', name: platformLabel(l.platform) },
                  })),
              },
            ],
          }),
        }}
      />
    </div>
  )
}

function Stat({
  label,
  value,
  tone,
}: {
  label: string
  value: string
  tone?: 'good' | 'muted'
}) {
  return (
    <div className="rounded-lg border border-line bg-panel p-4">
      <div className="text-xs text-muted">{label}</div>
      <div
        className={`mt-1 text-xl font-semibold tabular-nums ${
          tone === 'good' ? 'text-good' : ''
        }`}
      >
        {value}
      </div>
    </div>
  )
}
