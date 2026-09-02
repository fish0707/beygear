import type { Metadata } from 'next'
import Link from 'next/link'
import './globals.css'
import { PUBLISHER, SITE_DESCRIPTION, SITE_NAME, SITE_URL } from '@/lib/site'

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: `${SITE_NAME} — Beyblade X 台灣通路價格與補貨追蹤`,
    template: `%s | ${SITE_NAME}`,
  },
  description: SITE_DESCRIPTION,
  alternates: { canonical: '/' },
  openGraph: {
    type: 'website',
    locale: 'zh_TW',
    url: SITE_URL,
    siteName: SITE_NAME,
    title: `${SITE_NAME} — Beyblade X 台灣通路價格與補貨追蹤`,
    description: SITE_DESCRIPTION,
  },
  robots: { index: true, follow: true },
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const graph = {
    '@context': 'https://schema.org',
    '@graph': [
      {
        '@type': 'Organization',
        '@id': `${SITE_URL}/#publisher`,
        name: PUBLISHER.name,
        legalName: PUBLISHER.legalName,
        url: PUBLISHER.url,
        founder: {
          '@type': 'Person',
          name: PUBLISHER.founder,
          alternateName: PUBLISHER.founderAlias,
        },
        address: {
          '@type': 'PostalAddress',
          addressLocality: PUBLISHER.location,
          addressCountry: 'TW',
        },
        sameAs: [PUBLISHER.url, 'https://calc-mates.com'],
      },
      {
        '@type': 'WebSite',
        '@id': `${SITE_URL}/#website`,
        url: SITE_URL,
        name: SITE_NAME,
        description: SITE_DESCRIPTION,
        inLanguage: 'zh-TW',
        publisher: { '@id': `${SITE_URL}/#publisher` },
      },
    ],
  }

  return (
    <html lang="zh-TW">
      <body>
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(graph) }}
        />
        <header className="border-b border-line">
          <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-4">
            <Link href="/" className="font-bold tracking-tight">
              <span className="text-brand">Beygear</span> 陀螺捕獲情報
            </Link>
            <nav className="flex gap-4 text-sm text-muted">
              <Link href="/" className="hover:text-slate-100">現在有貨</Link>
              <Link href="/analyze" className="hover:text-slate-100">發射分析</Link>
              <Link href="/about" className="hover:text-slate-100">資料說明</Link>
            </nav>
          </div>
        </header>
        <main className="mx-auto max-w-5xl px-4 py-8">{children}</main>
        <footer className="mt-16 border-t border-line">
          <div className="mx-auto max-w-5xl px-4 py-8 text-sm text-muted">
            <p>
              {SITE_NAME} 由{' '}
              <a href={PUBLISHER.url} className="text-brand hover:underline">
                {PUBLISHER.legalName}
              </a>{' '}
              營運。價格與庫存是各通路公開資訊的觀測紀錄,可能與你點進去時的實際情況不同,
              下單前請以通路頁面為準。
            </p>
            <p className="mt-2">本站與 TAKARA TOMY 及各通路業者無任何隸屬關係。</p>
          </div>
        </footer>
      </body>
    </html>
  )
}
