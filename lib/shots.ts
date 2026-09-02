/**
 * BeyGear 備份檔的發射數據分析。
 *
 * 純函式、不碰 fs —— 整份分析在使用者的瀏覽器裡跑,備份檔不會離開他的裝置。
 *
 * ## 這裡的數字是怎麼來的
 *
 * 備份檔的每一發都帶 `rpms[]` 與 `times[]` 兩個等長陣列。實測發現**取樣間隔
 * 恰好等於 60000/rpm**(誤差 <1ms),也就是**感測器每轉一圈記一筆**。這件事
 * 讓兩個 App 介面上看不到的量變得可以計算:
 *
 *   - 上升期的取樣點數 = 陀螺在被加速期間轉了幾圈
 *   - 到達峰值的時間   = 繩子帶動陀螺的實際時長
 *
 * App 顯示的「加速度」也反推出來了:`(峰值rpm − rpms[1]) / (峰值時間 − times[1])`,
 * 對照實際畫面的數值可以對到個位數。留著同一條公式,站上算出來的才跟他 App 裡
 * 看到的是同一個東西。
 */

export type RawRecord = {
  id?: string
  deviceMac?: string
  rpms?: number[]
  times?: number[]
  maxRpm?: number
  evalSp?: number
  numShoot?: number
  voltage?: number
  createdAt?: number
}

export type Shot = {
  /** App 裡的「編號」,使用者唯一認得的識別。 */
  num: number
  createdAt: number
  sp: number
  /** 上升期轉了幾圈 ≈ 這一發實際用掉的繩長。 */
  revs: number
  /** 從第一筆取樣到峰值的毫秒數。 */
  riseMs: number
  /** 跟 App「加速度」欄同一條公式。 */
  accel: number
  /** sp/accel,約等於上升時間;只有 SP 與加速度兩欄時可以用它跟別人對照。 */
  ratio: number
  /** 峰值那一步的斜率遠高於整段中位數 = 感測器跳點,不是真的打出來的。 */
  glitch: boolean
}

/**
 * 雜訊判準:某一圈的轉速增幅同時超過這兩個門檻。
 *
 * 每個取樣點是一圈,所以「一圈之內轉速漲了多少」是有物理上限的。實測 1,600
 * 發的分佈:第 4 圈之後的每圈增幅中位數是 7.7%,P99 是 24.7%。
 *
 * 門檻不能訂在 P99 附近 —— 有大約 5% 的紀錄會在**上升期的最後一圈**出現
 * 25–37% 的增幅,而且集中在第 11–13 圈、橫跨整段使用期間。那是繩子抽完前
 * 最後一段不完整的圈被當成整圈計時造成的,是這個感測器的系統性特性,不是故障。
 *
 * 真正的跳點跟這群分得很開:一圈漲 50% 以上,最誇張的一圈漲了 3.3 倍,
 * 而且下一筆又掉回三成。整份資料裡這種只有 0.5%。
 */
const GLITCH_MIN_EXCESS = 0.5
const GLITCH_TREND_RATIO = 5

/** 前幾圈本來就會大幅加速,從這一圈之後才檢查。 */
const GLITCH_FROM_REV = 4

/** 少於這麼多取樣點的紀錄資訊量不足,直接跳過。 */
const MIN_SAMPLES = 5

function median(xs: number[]): number {
  if (xs.length === 0) return NaN
  const s = [...xs].sort((a, b) => a - b)
  const m = s.length >> 1
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2
}

export function quantile(xs: number[], p: number): number {
  if (xs.length === 0) return NaN
  const s = [...xs].sort((a, b) => a - b)
  const i = (s.length - 1) * p
  const lo = Math.floor(i)
  const hi = Math.ceil(i)
  return lo === hi ? s[lo] : s[lo] + (s[hi] - s[lo]) * (i - lo)
}

export function mean(xs: number[]): number {
  return xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : NaN
}

export { median }

/**
 * 把一發原始紀錄換算成指標,資料不足或形狀不對就回 null。
 *
 * 峰值出現在第 0 或第 1 筆的紀錄要丟掉:加速度的公式要用 rpms[1] 當起點,
 * 峰值就在起點上的話算出來的是 0 或負值,不是真的發射。
 */
export function toShot(r: RawRecord): Shot | null {
  const rpms = r.rpms
  const times = r.times
  if (!rpms || !times || rpms.length < MIN_SAMPLES || times.length !== rpms.length) {
    return null
  }

  let peak = 0
  for (let i = 1; i < rpms.length; i++) if (rpms[i] > rpms[peak]) peak = i
  if (peak < 2) return null

  const riseMs = times[peak] - times[0]
  const accelSpan = times[peak] - times[1]
  if (riseMs <= 0 || accelSpan <= 0) return null

  const sp = r.evalSp ?? r.maxRpm ?? rpms[peak]
  const accel = (rpms[peak] - rpms[1]) / accelSpan

  // 上升期裡有沒有哪一圈的增幅同時遠高於門檻與當下的趨勢。
  let glitch = false
  for (let i = GLITCH_FROM_REV; i <= peak && !glitch; i++) {
    if (rpms[i - 1] <= 0) continue
    const excess = rpms[i] / rpms[i - 1] - 1
    if (excess <= GLITCH_MIN_EXCESS) continue

    const recent: number[] = []
    for (let k = Math.max(1, i - 3); k < i; k++) {
      if (rpms[k - 1] > 0) recent.push(rpms[k] / rpms[k - 1] - 1)
    }
    // 下限避免趨勢趨近於零時把任何一點起伏都放大成雜訊。
    const trend = Math.max(median(recent), 0.01)
    glitch = excess > trend * GLITCH_TREND_RATIO
  }

  return {
    num: r.numShoot ?? 0,
    createdAt: r.createdAt ?? 0,
    sp,
    revs: peak,
    riseMs,
    accel,
    ratio: accel > 0 ? sp / accel : NaN,
    glitch,
  }
}

export type ParseResult = {
  shots: Shot[]
  /** 檔案裡總共有幾筆,含被跳過的。 */
  total: number
  /** 感測器數量;超過一個代表這份資料混了不同陀螺,不能直接比。 */
  devices: string[]
}

export function parseBackup(text: string): ParseResult {
  const data = JSON.parse(text) as { records?: RawRecord[] }
  const records = Array.isArray(data.records) ? data.records : []
  const shots: Shot[] = []
  const devices = new Set<string>()

  for (const r of records) {
    if (r.deviceMac) devices.add(r.deviceMac)
    const s = toShot(r)
    if (s) shots.push(s)
  }
  shots.sort((a, b) => a.createdAt - b.createdAt || a.num - b.num)

  return { shots, total: records.length, devices: [...devices] }
}

/**
 * Mann-Whitney U(常態近似 + 連續性校正)。
 *
 * A/B 每組只有 10–15 發,而 SP 的分佈有長尾 —— t 檢定在這種樣本上容易把
 * 一兩發好球當成「有效果」。改用排序檢定,結論比較不會被單一發帶走。
 */
export function mannWhitneyP(a: number[], b: number[]): number {
  const n1 = a.length
  const n2 = b.length
  if (n1 < 3 || n2 < 3) return NaN

  const all = [...a.map((v) => ({ v, g: 0 })), ...b.map((v) => ({ v, g: 1 }))]
  all.sort((x, y) => x.v - y.v)

  // 同分要給平均排名,否則 U 值會偏掉。
  const ranks = new Array<number>(all.length)
  let i = 0
  const tieGroups: number[] = []
  while (i < all.length) {
    let j = i
    while (j + 1 < all.length && all[j + 1].v === all[i].v) j++
    const avg = (i + j) / 2 + 1
    for (let k = i; k <= j; k++) ranks[k] = avg
    if (j > i) tieGroups.push(j - i + 1)
    i = j + 1
  }

  let r1 = 0
  for (let k = 0; k < all.length; k++) if (all[k].g === 0) r1 += ranks[k]

  const u1 = r1 - (n1 * (n1 + 1)) / 2
  const u = Math.min(u1, n1 * n2 - u1)
  const mu = (n1 * n2) / 2
  const n = n1 + n2
  const tieCorr = tieGroups.reduce((acc, t) => acc + (t * t * t - t), 0)
  const sigma = Math.sqrt(
    ((n1 * n2) / 12) * (n + 1 - tieCorr / (n * (n - 1)))
  )
  if (!(sigma > 0)) return NaN

  // 連續性校正在兩組幾乎沒差時會讓 z 變負,算出來的機率就會超過 1。
  const z = Math.max((Math.abs(u - mu) - 0.5) / sigma, 0)
  return Math.min(2 * (1 - normalCdf(z)), 1)
}

function normalCdf(z: number): number {
  // Abramowitz & Stegun 26.2.17,精度對「顯著/不顯著」的判斷綽綽有餘。
  const t = 1 / (1 + 0.2316419 * Math.abs(z))
  const d = 0.3989422804014327 * Math.exp(-(z * z) / 2)
  const p =
    d * t * (0.319381530 + t * (-0.356563782 + t * (1.781477937 + t * (-1.821255978 + t * 1.330274429))))
  return z > 0 ? 1 - p : p
}

export type GroupStats = {
  n: number
  spMedian: number
  spMean: number
  accelMedian: number
  revsMedian: number
  riseMedian: number
}

export function groupStats(shots: Shot[]): GroupStats {
  return {
    n: shots.length,
    spMedian: median(shots.map((s) => s.sp)),
    spMean: mean(shots.map((s) => s.sp)),
    accelMedian: median(shots.map((s) => s.accel)),
    revsMedian: median(shots.map((s) => s.revs)),
    riseMedian: median(shots.map((s) => s.riseMs)),
  }
}

/** 圈數 × 上升時間的 SP 中位數交叉表,格子太少就留空。 */
export function crossTab(shots: Shot[]) {
  const revBands = [
    { label: '少 (<10 圈)', lo: 0, hi: 10 },
    { label: '中 (10–11 圈)', lo: 10, hi: 12 },
    { label: '多 (≥12 圈)', lo: 12, hi: Infinity },
  ]
  const riseBands = [
    { label: '快 (<105ms)', lo: 0, hi: 105 },
    { label: '中 (105–125ms)', lo: 105, hi: 125 },
    { label: '慢 (>125ms)', lo: 125, hi: Infinity },
  ]
  return revBands.map((rb) => ({
    label: rb.label,
    cells: riseBands.map((tb) => {
      const g = shots.filter(
        (s) => s.revs >= rb.lo && s.revs < rb.hi && s.riseMs >= tb.lo && s.riseMs < tb.hi
      )
      return { n: g.length, spMedian: g.length >= 10 ? median(g.map((s) => s.sp)) : NaN }
    }),
    riseLabels: riseBands.map((b) => b.label),
  }))
}
