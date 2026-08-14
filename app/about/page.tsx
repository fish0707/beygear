import type { Metadata } from 'next'
import { formatTime, getMeta } from '@/lib/data'
import { PUBLISHER, REPO_URL, SITE_URL, SOURCES } from '@/lib/site'

export const metadata: Metadata = {
  title: '資料說明',
  description:
    'Beygear 的資料怎麼來、多久更新一次、哪些數字可以信、哪些不能。包含各通路的抓取方式、已知限制與免責說明。',
  alternates: { canonical: '/about' },
}

export default function About() {
  const meta = getMeta()

  return (
    <div className="max-w-3xl space-y-10">
      <section>
        <h1 className="text-3xl font-bold tracking-tight">資料說明</h1>
        <p className="mt-3 text-muted">
          這一頁寫清楚站上的數字怎麼來的、有哪些已知的限制。看不出資料怎麼產生的網站,
          數字就不該相信 —— 包括這一個。
        </p>
      </section>

      <section>
        <h2 className="text-xl font-semibold">更新頻率</h2>
        <p className="mt-3 text-muted">
          雷達每 15 分鐘掃一次,寫進一個版本控管的資料庫。網頁本身不會每 15 分鐘重新部署,
          但頁面載入時會去抓最新的一份快照,所以你看到的庫存與售價是即時的。
          最後一次建置的資料時間是 {formatTime(meta.generated_at)}。
        </p>
      </section>

      <section>
        <h2 className="text-xl font-semibold">資料來源</h2>
        <ul className="mt-3 space-y-3 text-muted">
          {SOURCES.map((s) => (
            <li key={s.label}>
              <a
                href={s.href}
                target="_blank"
                rel="nofollow noopener"
                className="text-brand hover:underline"
              >
                {s.label}
              </a>
              <br />
              {s.detail}
            </li>
          ))}
        </ul>
        <p className="mt-3 text-muted">
          只讀取通路公開頁面上任何人都看得到的欄位:商品名稱、售價、賣場標示的定價、庫存數。
          不繞過登入,不整批複製對方的商品資料庫。
        </p>
      </section>

      <section>
        <h2 className="text-xl font-semibold">「賣場定價」不等於「原廠建議售價」</h2>
        <p className="mt-3 text-muted">
          站上顯示的「賣場定價」是通路自己在頁面上標的原價(momo 的{' '}
          <code className="rounded bg-panel px-1">goodsPriceOri</code>、誠品的{' '}
          <code className="rounded bg-panel px-1">mprice</code>)。這是真實可查證的數字,
          但賣場想標多少就標多少,所以「售價低於賣場定價」幾乎永遠成立,幾乎沒有意義。
        </p>
        <p className="mt-3 text-muted">
          真正有意義的是「有沒有用原廠建議售價買到」。那需要逐款查證原廠定價,目前
          <strong className="text-slate-100">還沒有任何一款查證完成</strong>,所以站上不會出現
          任何「以原價供應」的判定。查證一款就會補一款,而不是拿賣場定價來充數。
        </p>
      </section>

      <section>
        <h2 className="text-xl font-semibold">已知限制</h2>
        <ul className="mt-3 list-disc space-y-2 pl-5 text-muted">
          <li>
            momo 的單品即時查詢介面拒絕機房來源的請求,所以資料是從公開搜尋結果取得的。
            沒有出現在搜尋結果前幾頁的商品就不會被記錄到。
          </li>
          <li>
            目前只收錄 momo 自營商品。摩天商城賣家商品的商品頁網址規則尚未驗證,
            寧可不收,也不要給出錯誤的連結。
          </li>
          <li>
            誠品線上以書籍為主,搜尋「戰鬥陀螺」得到的多半是攻略本、漫畫與附錄雜誌,
            不是玩具本體。
          </li>
          <li>
            兩次掃描之間發生又結束的變化(例如補貨後幾分鐘內售罄)可能整段錯過。
          </li>
        </ul>
      </section>

      <section>
        <h2 className="text-xl font-semibold">誰做的</h2>
        <p className="mt-3 text-muted">
          由{' '}
          <a href={PUBLISHER.url} className="text-brand hover:underline">
            {PUBLISHER.legalName}
          </a>
          （{PUBLISHER.location}）營運,負責人 {PUBLISHER.founder}。
          原本是自己要搶貨寫的私人工具,後來因為想用的人變多才公開。
          監控程式與資料都是公開的:{' '}
          <a
            href={REPO_URL}
            target="_blank"
            rel="noopener"
            className="text-brand hover:underline"
          >
            GitHub 原始碼與資料
          </a>
          。抓取邏輯與每一次觀測都能自己回去核對。
        </p>
      </section>

      <section>
        <h2 className="text-xl font-semibold">免責</h2>
        <p className="mt-3 text-muted">
          站上的價格與庫存是觀測當下的紀錄,不保證即時準確,也不構成購買建議。
          通路隨時可能調整售價或庫存,下單前請以通路頁面顯示的為準。
          本站與 TAKARA TOMY 及各通路業者無任何隸屬關係,連往通路的連結不含分潤代碼。
        </p>
      </section>

      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify({
            '@context': 'https://schema.org',
            '@type': 'AboutPage',
            url: `${SITE_URL}/about`,
            name: '資料說明',
            isPartOf: { '@id': `${SITE_URL}/#website` },
            publisher: { '@id': `${SITE_URL}/#publisher` },
          }),
        }}
      />
    </div>
  )
}
