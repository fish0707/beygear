// Notify IndexNow (Bing, DuckDuckGo, Seznam, Yandex) of the site's URLs.
// Runs automatically after `next build` via the "postbuild" script.
// Only submits on Vercel production builds; otherwise it prints a dry run.
//
// The URL list is read from the live production sitemap.xml. On a fresh
// deploy this reflects the previous deploy, so brand-new URLs (a newly
// discovered model, a new page) are picked up on the next build — an
// acceptable lag, and Google still gets them via the sitemap directly.
// This keeps the script free of TS/build-time imports.
//
// Same pattern as calc-mates.com's scripts/indexnow.mjs, with its own key —
// IndexNow verifies per-host, so each host needs its own key file at its own
// root; beygear.calc-mates.com is a distinct host from calc-mates.com.

const KEY = '2b28b7c77cca005fbc13a6e6b01d000c'
const HOST = 'beygear.calc-mates.com'
const BASE = `https://${HOST}`

async function fetchSitemapUrls() {
  try {
    const res = await fetch(`${BASE}/sitemap.xml`, { headers: { 'User-Agent': 'Beygear-IndexNow' } })
    if (!res.ok) return []
    const xml = await res.text()
    return [...xml.matchAll(/<loc>([^<]+)<\/loc>/g)].map(m => m[1].trim())
  } catch {
    return []
  }
}

async function main() {
  const isProd = process.env.VERCEL_ENV === 'production'
  const urlList = await fetchSitemapUrls()

  if (!isProd) {
    console.log(`[indexnow] dry run — found ${urlList.length} URLs in sitemap (skipped: not a Vercel production build).`)
    return
  }
  if (urlList.length === 0) {
    console.warn('[indexnow] no URLs found in sitemap — skipping submission.')
    return
  }

  try {
    const res = await fetch('https://api.indexnow.org/indexnow', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json; charset=utf-8' },
      body: JSON.stringify({ host: HOST, key: KEY, keyLocation: `${BASE}/${KEY}.txt`, urlList }),
    })
    console.log(`[indexnow] submitted ${urlList.length} URLs — HTTP ${res.status}`)
  } catch (err) {
    // Never fail the build over a ping.
    console.warn('[indexnow] submission failed (non-fatal):', err?.message || err)
  }
}

main()
