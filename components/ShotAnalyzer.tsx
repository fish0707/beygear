'use client'

import { useMemo, useState } from 'react'
import {
  crossTab,
  groupStats,
  mannWhitneyP,
  median,
  parseBackup,
  quantile,
  type ParseResult,
  type Shot,
} from '@/lib/shots'

/** 「1600-1614, 1620」這種輸入 → 編號集合。 */
function parseRanges(input: string): Set<number> {
  const out = new Set<number>()
  for (const part of input.split(/[,，\s]+/)) {
    if (!part) continue
    const m = part.match(/^(\d+)\s*[-–~]\s*(\d+)$/)
    if (m) {
      const lo = Math.min(+m[1], +m[2])
      const hi = Math.max(+m[1], +m[2])
      for (let i = lo; i <= hi; i++) out.add(i)
    } else if (/^\d+$/.test(part)) {
      out.add(+part)
    }
  }
  return out
}

/** 「13586 164」逐行 → SP 與加速度成對,用來貼別人的截圖數字。 */
function parsePairs(input: string): { sp: number; accel: number }[] {
  const out: { sp: number; accel: number }[] = []
  for (const line of input.split('\n')) {
    const nums = line.match(/\d+(?:\.\d+)?/g)
    if (!nums || nums.length < 2) continue
    const sp = +nums[nums.length - 2]
    const accel = +nums[nums.length - 1]
    if (sp > 1000 && accel > 1) out.push({ sp, accel })
  }
  return out
}

const fmt = (n: number, d = 0) =>
  Number.isFinite(n) ? n.toLocaleString('zh-TW', { maximumFractionDigits: d }) : '—'

function Stat({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="rounded-lg border border-line bg-panel px-4 py-3">
      <div className="text-xs text-muted">{label}</div>
      <div className="mt-1 text-2xl font-semibold tabular-nums">{value}</div>
      {hint && <div className="mt-1 text-xs text-muted">{hint}</div>}
    </div>
  )
}

export default function ShotAnalyzer() {
  const [result, setResult] = useState<ParseResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [rangeA, setRangeA] = useState('')
  const [rangeB, setRangeB] = useState('')
  const [bench, setBench] = useState('')

  async function onFile(file: File | undefined) {
    if (!file) return
    setError(null)
    try {
      const parsed = parseBackup(await file.text())
      if (parsed.shots.length === 0) {
        setError('這個檔案裡沒有可分析的發射紀錄。請確認是 BeyGear 匯出的備份 JSON。')
        setResult(null)
        return
      }
      setResult(parsed)
    } catch {
      setError('讀不到這個檔案的內容,看起來不是有效的 JSON。')
      setResult(null)
    }
  }

  // 雜訊值會把百分位和最高值整個拉歪,統計一律排除,但另外列出來讓人自己看。
  const clean = useMemo(
    () => (result ? result.shots.filter((s) => !s.glitch) : []),
    [result]
  )
  const glitches = useMemo(
    () => (result ? result.shots.filter((s) => s.glitch) : []),
    [result]
  )

  const ab = useMemo(() => {
    if (clean.length === 0) return null
    const setA = parseRanges(rangeA)
    const setB = parseRanges(rangeB)
    if (setA.size === 0 || setB.size === 0) return null
    const a = clean.filter((s) => setA.has(s.num))
    const b = clean.filter((s) => setB.has(s.num))
    if (a.length < 3 || b.length < 3) return { a, b, p: NaN, pAccel: NaN }
    return {
      a,
      b,
      p: mannWhitneyP(a.map((s) => s.sp), b.map((s) => s.sp)),
      pAccel: mannWhitneyP(a.map((s) => s.accel), b.map((s) => s.accel)),
    }
  }, [clean, rangeA, rangeB])

  const benchmark = useMemo(() => {
    const pairs = parsePairs(bench)
    if (pairs.length === 0) return null
    return {
      n: pairs.length,
      sp: median(pairs.map((p) => p.sp)),
      accel: median(pairs.map((p) => p.accel)),
      ratio: median(pairs.map((p) => p.sp / p.accel)),
    }
  }, [bench])

  return (
    <div className="space-y-10">
      <section>
        <label className="block cursor-pointer rounded-xl border border-dashed border-line bg-panel px-6 py-10 text-center hover:border-brand">
          <input
            type="file"
            accept=".json,application/json"
            className="sr-only"
            onChange={(e) => onFile(e.target.files?.[0])}
          />
          <div className="text-lg font-medium">選擇 BeyGear 備份 JSON</div>
          <div className="mt-2 text-sm text-muted">
            檔案只在你的瀏覽器裡解析,不會上傳到任何伺服器。
          </div>
        </label>
        {error && <p className="mt-3 text-sm text-bad">{error}</p>}
      </section>

      {result && clean.length > 0 && (
        <>
          <Overview result={result} clean={clean} glitches={glitches} />
          <Hidden clean={clean} />
          <CrossTable clean={clean} />

          <section>
            <h2 className="text-xl font-semibold">A/B 比較</h2>
            <p className="mt-2 text-muted">
              改一個動作,打兩組,填進來看差異是不是真的。10–15 發的樣本很容易被運氣騙,
              所以這裡用排序檢定算 p 值,而不是只比平均。
            </p>
            <div className="mt-4 grid gap-4 sm:grid-cols-2">
              <div>
                <label className="text-sm text-muted">A 組編號</label>
                <input
                  value={rangeA}
                  onChange={(e) => setRangeA(e.target.value)}
                  placeholder="例:1560-1574"
                  className="mt-1 w-full rounded-lg border border-line bg-panel px-3 py-2 tabular-nums outline-none focus:border-brand"
                />
              </div>
              <div>
                <label className="text-sm text-muted">B 組編號</label>
                <input
                  value={rangeB}
                  onChange={(e) => setRangeB(e.target.value)}
                  placeholder="例:1575-1589"
                  className="mt-1 w-full rounded-lg border border-line bg-panel px-3 py-2 tabular-nums outline-none focus:border-brand"
                />
              </div>
            </div>
            {ab && <AbResult ab={ab} />}
          </section>

          <section>
            <h2 className="text-xl font-semibold">跟別人對照</h2>
            <p className="mt-2 text-muted">
              把對方 App 列表的「SP」和「加速度」逐行貼上來(每行兩個數字)。
              SP÷加速度 約等於上升時間,所以就算只有截圖也能跟你的節奏放在同一把尺上比。
            </p>
            <textarea
              value={bench}
              onChange={(e) => setBench(e.target.value)}
              rows={5}
              placeholder={'13586 164\n14018 164\n13661 169'}
              className="mt-3 w-full rounded-lg border border-line bg-panel px-3 py-2 font-mono text-sm tabular-nums outline-none focus:border-brand"
            />
            {benchmark && <Benchmark benchmark={benchmark} clean={clean} />}
          </section>
        </>
      )}
    </div>
  )
}

function Overview({
  result,
  clean,
  glitches,
}: {
  result: ParseResult
  clean: Shot[]
  glitches: Shot[]
}) {
  const sp = clean.map((s) => s.sp)
  const first = clean[0]
  const last = clean[clean.length - 1]
  const day = (t: number) =>
    t ? new Date(t).toLocaleDateString('zh-TW', { timeZone: 'Asia/Taipei' }) : '—'

  return (
    <section>
      <h2 className="text-xl font-semibold">總覽</h2>
      <p className="mt-2 text-muted">
        可分析 {fmt(clean.length)} 發(檔案共 {fmt(result.total)} 筆),
        {day(first.createdAt)} 至 {day(last.createdAt)}。
      </p>

      {result.devices.length > 1 && (
        <p className="mt-3 rounded-lg border border-warn/40 bg-warn/10 px-4 py-3 text-sm text-warn">
          這份資料混了 {result.devices.length} 個感測器。不同陀螺的轉動慣量不同,
          SP 不能直接放在一起比 —— 下面的統計會失真。
        </p>
      )}

      <div className="mt-4 grid gap-3 sm:grid-cols-3">
        <Stat label="SP 中位數" value={fmt(quantile(sp, 0.5))} hint="比最高值誠實" />
        <Stat label="SP 第 90 百分位" value={fmt(quantile(sp, 0.9))} />
        <Stat label="SP 最高(排除雜訊)" value={fmt(Math.max(...sp))} />
      </div>

      <table className="mt-4 w-full text-sm tabular-nums">
        <thead className="text-muted">
          <tr>
            {[10, 25, 50, 75, 90, 95, 99].map((p) => (
              <th key={p} className="py-2 text-left font-normal">
                P{p}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          <tr className="border-t border-line">
            {[10, 25, 50, 75, 90, 95, 99].map((p) => (
              <td key={p} className="py-2">
                {fmt(quantile(sp, p / 100))}
              </td>
            ))}
          </tr>
        </tbody>
      </table>

      {glitches.length > 0 && (
        <div className="mt-6 rounded-lg border border-line bg-panel px-4 py-3">
          <div className="font-medium">
            排除了 {glitches.length} 發感測器雜訊
          </div>
          <p className="mt-1 text-sm text-muted">
            峰值那一步的轉速跳升遠高於整段的常態(超過中位斜率的 4 倍),
            實體陀螺做不到這種變化。這種讀數會把你的「最高 SP」灌到一個不存在的數字上。
          </p>
          <div className="mt-2 text-sm tabular-nums text-muted">
            編號 {glitches.slice(0, 8).map((g) => `${g.num}(${fmt(g.sp)})`).join('、')}
            {glitches.length > 8 && ' …'}
          </div>
        </div>
      )}
    </section>
  )
}

function Hidden({ clean }: { clean: Shot[] }) {
  const top = [...clean].sort((a, b) => b.sp - a.sp).slice(0, Math.max(20, Math.round(clean.length * 0.05)))
  const mid = [...clean].sort(
    (a, b) => Math.abs(a.sp - median(clean.map((s) => s.sp))) - Math.abs(b.sp - median(clean.map((s) => s.sp)))
  ).slice(0, Math.max(40, Math.round(clean.length * 0.1)))

  const row = (label: string, g: Shot[]) => (
    <tr className="border-t border-line">
      <td className="py-2">{label}</td>
      <td className="py-2 text-right">{fmt(median(g.map((s) => s.sp)))}</td>
      <td className="py-2 text-right">{fmt(median(g.map((s) => s.accel)))}</td>
      <td className="py-2 text-right">{fmt(median(g.map((s) => s.revs)), 1)}</td>
      <td className="py-2 text-right">{fmt(median(g.map((s) => s.riseMs)))}</td>
      <td className="py-2 text-right">{fmt(median(g.map((s) => s.msPerRev)), 1)}</td>
    </tr>
  )

  return (
    <section>
      <h2 className="text-xl font-semibold">App 看不到的三個數字</h2>
      <p className="mt-2 text-muted">
        感測器每轉一圈記一筆,所以上升期的取樣點數就是**陀螺被帶動了幾圈**,
        約當這一發實際用掉的繩長;到峰值的時間則是繩子帶動陀螺的實際時長。
        把你最強的球和一般的球放在一起,差在圈數還是時間就看得出來。
      </p>
      <table className="mt-4 w-full text-sm tabular-nums">
        <thead className="text-muted">
          <tr>
            <th className="py-2 text-left font-normal"> </th>
            <th className="py-2 text-right font-normal">SP</th>
            <th className="py-2 text-right font-normal">加速度</th>
            <th className="py-2 text-right font-normal">圈數</th>
            <th className="py-2 text-right font-normal">上升時間</th>
            <th className="py-2 text-right font-normal">每圈耗時</th>
          </tr>
        </thead>
        <tbody>
          {row('最強一批', top)}
          {row('中位一批', mid)}
          {row('全部', clean)}
        </tbody>
      </table>
    </section>
  )
}

function CrossTable({ clean }: { clean: Shot[] }) {
  const tab = crossTab(clean)
  if (tab.length === 0) return null
  return (
    <section>
      <h2 className="text-xl font-semibold">圈數 × 上升時間</h2>
      <p className="mt-2 text-muted">
        格子裡是 SP 中位數。兩個方向都會動,代表這兩件事各自獨立地影響結果 ——
        圈數多而且時間短的那一格,通常比你的整體中位數高一大截。樣本少於 10 發的格子留空。
      </p>
      <div className="mt-4 overflow-x-auto">
        <table className="w-full min-w-[28rem] text-sm tabular-nums">
          <thead className="text-muted">
            <tr>
              <th className="py-2 text-left font-normal">圈數 \ 時間</th>
              {tab[0].riseLabels.map((l) => (
                <th key={l} className="py-2 text-right font-normal">
                  {l}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {tab.map((r) => (
              <tr key={r.label} className="border-t border-line">
                <td className="py-2">{r.label}</td>
                {r.cells.map((c, i) => (
                  <td key={i} className="py-2 text-right">
                    {Number.isFinite(c.spMedian) ? (
                      <>
                        {fmt(c.spMedian)}
                        <span className="ml-1 text-xs text-muted">n={c.n}</span>
                      </>
                    ) : (
                      <span className="text-muted">—</span>
                    )}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}

function AbResult({ ab }: { ab: { a: Shot[]; b: Shot[]; p: number; pAccel: number } }) {
  const sa = groupStats(ab.a)
  const sb = groupStats(ab.b)

  if (ab.a.length < 3 || ab.b.length < 3) {
    return (
      <p className="mt-4 text-sm text-warn">
        找到 A 組 {ab.a.length} 發、B 組 {ab.b.length} 發。每組至少要 3 發才算得出來,
        建議每組 10–15 發。
      </p>
    )
  }

  const verdict = (p: number) =>
    !Number.isFinite(p)
      ? '—'
      : p < 0.05
        ? '差異看起來是真的'
        : p < 0.15
          ? '有點跡象,但還不夠'
          : '看不出差異,可能只是運氣'

  return (
    <div className="mt-4 space-y-4">
      <table className="w-full text-sm tabular-nums">
        <thead className="text-muted">
          <tr>
            <th className="py-2 text-left font-normal"> </th>
            <th className="py-2 text-right font-normal">發數</th>
            <th className="py-2 text-right font-normal">SP 中位</th>
            <th className="py-2 text-right font-normal">加速度中位</th>
            <th className="py-2 text-right font-normal">圈數</th>
            <th className="py-2 text-right font-normal">上升時間</th>
            <th className="py-2 text-right font-normal">每圈耗時</th>
          </tr>
        </thead>
        <tbody>
          {[
            ['A 組', sa],
            ['B 組', sb],
          ].map(([label, s]) => {
            const g = s as ReturnType<typeof groupStats>
            return (
              <tr key={label as string} className="border-t border-line">
                <td className="py-2">{label as string}</td>
                <td className="py-2 text-right">{g.n}</td>
                <td className="py-2 text-right">{fmt(g.spMedian)}</td>
                <td className="py-2 text-right">{fmt(g.accelMedian)}</td>
                <td className="py-2 text-right">{fmt(g.revsMedian, 1)}</td>
                <td className="py-2 text-right">{fmt(g.riseMedian)}</td>
                <td className="py-2 text-right">{fmt(g.msPerRevMedian, 1)}</td>
              </tr>
            )
          })}
        </tbody>
      </table>

      <div className="grid gap-3 sm:grid-cols-2">
        <Stat
          label="SP 差異"
          value={`p = ${Number.isFinite(ab.p) ? ab.p.toFixed(3) : '—'}`}
          hint={verdict(ab.p)}
        />
        <Stat
          label="加速度差異"
          value={`p = ${Number.isFinite(ab.pAccel) ? ab.pAccel.toFixed(3) : '—'}`}
          hint={verdict(ab.pAccel)}
        />
      </div>

      <p className="text-sm text-muted">
        加速度的 p 值通常比 SP 更早看得出變化 —— 它是輸入,SP 是結果,雜訊比較少。
        兩組之間如果隔了很久或中間換過器材,這個數字就不能算數。
      </p>
    </div>
  )
}

function Benchmark({
  benchmark,
  clean,
}: {
  benchmark: { n: number; sp: number; accel: number; ratio: number }
  clean: Shot[]
}) {
  const mySp = median(clean.map((s) => s.sp))
  const myAccel = median(clean.map((s) => s.accel))
  const myRatio = median(clean.map((s) => s.ratio))
  const myBestAccel = quantile(clean.map((s) => s.accel), 0.99)

  return (
    <div className="mt-4 space-y-4">
      <table className="w-full text-sm tabular-nums">
        <thead className="text-muted">
          <tr>
            <th className="py-2 text-left font-normal"> </th>
            <th className="py-2 text-right font-normal">SP</th>
            <th className="py-2 text-right font-normal">加速度</th>
            <th className="py-2 text-right font-normal">SP÷加速度</th>
          </tr>
        </thead>
        <tbody>
          <tr className="border-t border-line">
            <td className="py-2">對方(n={benchmark.n})</td>
            <td className="py-2 text-right">{fmt(benchmark.sp)}</td>
            <td className="py-2 text-right">{fmt(benchmark.accel)}</td>
            <td className="py-2 text-right">{fmt(benchmark.ratio)}</td>
          </tr>
          <tr className="border-t border-line">
            <td className="py-2">你的中位數</td>
            <td className="py-2 text-right">{fmt(mySp)}</td>
            <td className="py-2 text-right">{fmt(myAccel)}</td>
            <td className="py-2 text-right">{fmt(myRatio)}</td>
          </tr>
          <tr className="border-t border-line">
            <td className="py-2">你的 P99</td>
            <td className="py-2 text-right text-muted">—</td>
            <td className="py-2 text-right">{fmt(myBestAccel)}</td>
            <td className="py-2 text-right text-muted">—</td>
          </tr>
        </tbody>
      </table>
      <p className="text-sm text-muted">
        SP÷加速度 越小代表抽完的時間越短。這個數字接近而 SP 差很多,代表同樣的節奏下
        對方的陀螺被帶動得更多;這個數字差很多,那才是單純的快慢差別。
        對方只貼幾發的話結論很不穩,至少要 10 發以上再下判斷。
      </p>
    </div>
  )
}
