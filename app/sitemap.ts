import type { MetadataRoute } from 'next'
import { getMeta, getModelProducts } from '@/lib/data'
import { SITE_URL } from '@/lib/site'

export default function sitemap(): MetadataRoute.Sitemap {
  const meta = getMeta()
  const updated = new Date(meta.generated_at * 1000)

  return [
    { url: SITE_URL, lastModified: updated, changeFrequency: 'hourly', priority: 1 },
    { url: `${SITE_URL}/about`, lastModified: updated, changeFrequency: 'monthly', priority: 0.5 },
    ...getModelProducts().map((p) => ({
      url: `${SITE_URL}/model/${p.product_key}`,
      lastModified: new Date(p.last_updated_at * 1000),
      changeFrequency: 'daily' as const,
      priority: 0.8,
    })),
  ]
}
