import type { Metadata } from 'next'
import ShotAnalyzer from '@/components/ShotAnalyzer'

export const metadata: Metadata = {
  title: '發射數據分析',
  description:
    '上傳 BeyGear 備份 JSON,算出 App 介面上看不到的圈數、上升時間與加速度分佈,' +
    '並用統計檢定判斷你改的動作到底有沒有效。資料只在瀏覽器裡處理。',
  alternates: { canonical: '/analyze' },
}

export default function Analyze() {
  return (
    <div className="max-w-3xl space-y-10">
      <section>
        <h1 className="text-3xl font-bold tracking-tight">發射數據分析</h1>
        <p className="mt-3 text-muted">
          這一頁不告訴你姿勢該怎麼調 —— 它給你一把尺,讓你自己驗證任何說法。
          上傳 BeyGear 的備份 JSON,算出 App 介面上看不到的數字,
          再用統計檢定判斷你改的那個動作到底有沒有效。
        </p>
      </section>

      <ShotAnalyzer />

      <section className="border-t border-line pt-10">
        <h2 className="text-xl font-semibold">為什麼不給姿勢建議</h2>
        <p className="mt-3 text-muted">
          網路上關於轉速的說法互相矛盾:有人說要轉腰帶動、有人說重點是快不是力、
          打到一萬五的人則直接說「沒有一個所謂的最好拉的方式,因為每個人身高、臂展、
          協調度都不一樣」。實測過一輪之後,真正站得住的結論比想像中少很多 ——
          光靠看影片猜出來的姿勢建議,很容易讓人花好幾個禮拜走冤枉路。
        </p>
        <p className="mt-3 text-muted">
          所以這裡只做一件事:把你自己的數據算清楚,讓你用 30 發就分辨出一個說法對你
          有沒有用。誰說的都一樣,數字說了算。
        </p>
      </section>

      <section>
        <h2 className="text-xl font-semibold">數字是怎麼算的</h2>

        <h3 className="mt-5 font-medium">每個取樣點 = 陀螺轉一圈</h3>
        <p className="mt-2 text-muted">
          備份檔裡每一發都帶一串 rpm 與時間戳。實測發現取樣間隔恰好等於 60000/rpm,
          誤差在 1 毫秒以內 —— 也就是感測器每轉一圈記一筆。因此上升期的取樣點數
          就是陀螺被帶動了幾圈,約當這一發實際用掉的繩長;到峰值的時間則是繩子
          帶動陀螺的實際時長。這兩個量 App 介面上都看不到。
        </p>

        <h3 className="mt-5 font-medium">每圈耗時,以及它為什麼不是萬用的</h3>
        <p className="mt-2 text-muted">
          「上升時間 ÷ 圈數」= 加速期間陀螺轉一圈要多久,越小代表全程轉得越快。
          它的好處是跟圈數沒有代數糾纏 —— 圈數多的球上升時間也會跟著長,兩者一起
          變動時很難分辨到底是哪一個在推 SP,每圈耗時把這層糾纏拆掉了。
        </p>
        <p className="mt-2 text-muted">
          但它跟 SP 的關係會隨動作改變方向,這點請務必留意。同一個人的資料裡,
          一段時間內每圈耗時與 SP 是負相關(轉得越快 SP 越高)、圈數則幾乎無關甚至
          反向;換了一套發力方式之後卻反過來 —— 圈數變多、每圈耗時變長,SP 反而
          創新高。所以這些指標的正確用法是<strong className="text-ink">在你自己的資料裡
          看它跟著哪一個變動</strong>,不是背一條固定的規則。
        </p>

        <h3 className="mt-5 font-medium">發力曲線:前 1/3 / 中 1/3 / 後 1/3</h3>
        <p className="mt-2 text-muted">
          把上升期按<strong className="text-ink">時間</strong>切三等份,算各段的平均角加速度,
          就看得出這一發的力是什麼時候出去的。目前 948 發裡最能分辨好壞的就是
          <strong className="text-ink">後 1/3</strong>:按它分四層,SP 中位是
          7,961 / 8,455 / 8,761 / 9,157,而且固定圈數之後依然成立,不是「圈數多所以 SP 高」。
        </p>
        <p className="mt-2 text-muted">
          最乾淨的一次驗證是單一場練習的 69 發 —— 同一顆陀螺、同一個發射器、
          同一個晚上,只按後段分層:
        </p>
        <div className="mt-3 overflow-x-auto">
          <table className="w-full min-w-[22rem] text-sm tabular-nums">
            <thead className="text-muted">
              <tr>
                <th className="py-2 text-left font-normal">後 1/3 加速度</th>
                <th className="py-2 text-right font-normal">發數</th>
                <th className="py-2 text-right font-normal">SP 中位</th>
              </tr>
            </thead>
            <tbody>
              {[
                ['< 65', 21, '8,342'],
                ['65 – 78', 19, '9,191'],
                ['78 – 88', 10, '9,804'],
                ['≥ 88', 18, '10,238'],
              ].map(([band, n, sp]) => (
                <tr key={band as string} className="border-t border-line">
                  <td className="py-2">{band as string}</td>
                  <td className="py-2 text-right">{n as number}</td>
                  <td className="py-2 text-right">{sp as string}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-3 text-muted">
          一個晚上之內拉開 1,900 SP,器材、陀螺、場地全部沒變。
        </p>

        <p className="mt-4 text-muted">
          前段幾乎不影響結果。按中位切成 2×2 看得最清楚:
        </p>
        <div className="mt-3 overflow-x-auto">
          <table className="w-full min-w-[20rem] text-sm tabular-nums">
            <thead className="text-muted">
              <tr>
                <th className="py-2 text-left font-normal"> </th>
                <th className="py-2 text-right font-normal">後段低</th>
                <th className="py-2 text-right font-normal">後段高</th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-t border-line">
                <td className="py-2">前段低</td>
                <td className="py-2 text-right">8,260</td>
                <td className="py-2 text-right text-good">9,009</td>
              </tr>
              <tr className="border-t border-line">
                <td className="py-2">前段高</td>
                <td className="py-2 text-right">8,223</td>
                <td className="py-2 text-right text-good">8,949</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p className="mt-3 text-muted">
          後段高低差 750;前段在固定後段之後只差 37–60。所以起手用不用力對 SP
          <strong className="text-ink">沒有直接影響</strong>,
          繩子快抽完的時候還有沒有在加速才有。兩場完全相反的動作可以印證:一場前段 22、
          9.5 圈、上升 124ms,另一場前段 96、9 圈、上升 93ms,SP 中位 9,102 vs 9,025
          (p = 0.72)—— 一模一樣,而它們唯一的共同點就是後段都高。
        </p>
        <p className="mt-2 text-muted">
          但前段有一條<strong className="text-ink">間接</strong>的路:它決定圈數。
          前段最低的那 25% 有 58% 的球能跑到 10 圈以上,前段高的三層則是 0–4%。
          而圈數在固定後段之後仍然加分。兩者疊起來就是四個格子:
        </p>
        <div className="mt-3 overflow-x-auto">
          <table className="w-full min-w-[22rem] text-sm tabular-nums">
            <thead className="text-muted">
              <tr>
                <th className="py-2 text-left font-normal"> </th>
                <th className="py-2 text-right font-normal">後段低</th>
                <th className="py-2 text-right font-normal">後段高</th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-t border-line">
                <td className="py-2">9 圈</td>
                <td className="py-2 text-right">8,232</td>
                <td className="py-2 text-right">9,047</td>
              </tr>
              <tr className="border-t border-line">
                <td className="py-2">10 圈以上</td>
                <td className="py-2 text-right">8,787</td>
                <td className="py-2 text-right text-good">9,339</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p className="mt-3 text-muted">
          所以會有兩套都能打到 9,000 的動作:起手鬆、換到多的圈數;或是起手硬、
          圈數少但每圈更快。上限比較高的是前者。這也是為什麼這一頁只給你三欄數字 ——
          同一個量在不同動作裡走不同的路,寫死成規則就會錯。
        </p>

        <h3 className="mt-5 font-medium">用「一場裡的最大圈數」看繩子有沒有磨損</h3>
        <p className="mt-2 text-muted">
          PE 編織線用久了會縮短,而繩長直接決定圈數的上限 —— 所以每一場的
          <strong className="text-ink">最大圈數</strong>是一個免費的器材耗損指標,
          跟你當天的狀態幾乎無關。
        </p>
        <p className="mt-2 text-muted">
          實測一條用了約 600 發的線:前半個月每一場的最大圈數都還有 11–12,
          之後連續四天 372 發全部壓在 9–10,其中一天 52 發的最大值只有 9。
          換上新發射器的第一場就回到 12。狀態會讓中位數上下跑,但
          <strong className="text-ink">不會讓最大值連續四天都上不去</strong> ——
          看到這種天花板就是該換線了。
        </p>

        <h3 className="mt-5 font-medium">加速度用的是 App 自己的公式</h3>
        <p className="mt-2 text-muted">
          反推自 App 顯示的數值:(峰值 rpm − 第二筆 rpm) ÷ (峰值時間 − 第二筆時間),
          對照畫面可以對到個位數。用同一條公式,站上算出來的才跟你在 App 裡看到的
          是同一個東西。
        </p>

        <h3 className="mt-5 font-medium">SP ÷ 加速度 ≈ 上升時間</h3>
        <p className="mt-2 text-muted">
          這讓你只憑一張截圖的兩個欄位,就能跟別人放在同一把尺上比 —— 不需要對方
          給你備份檔。以實測資料驗證,分組平均的估計值與實際上升時間相差在數毫秒內。
        </p>

        <h3 className="mt-5 font-medium">雜訊會被排除</h3>
        <p className="mt-2 text-muted">
          有些紀錄的峰值是感測器跳點,例如四毫秒內從九千跳到一萬四 —— 實體陀螺
          做不到這種變化。這種讀數會把「最高 SP」灌到一個不存在的數字上,
          所以統計時排除,但會另外列出來讓你自己看。
        </p>

        <h3 className="mt-5 font-medium">A/B 用排序檢定,不是比平均</h3>
        <p className="mt-2 text-muted">
          每組只有十幾發時,一兩發好球就能把平均拉高。這裡用 Mann-Whitney
          排序檢定算 p 值,結論比較不會被單一發帶走。p 小於 0.05 才當作差異是真的。
        </p>
      </section>

      <section>
        <h2 className="text-xl font-semibold">已知限制</h2>
        <ul className="mt-3 list-disc space-y-2 pl-5 text-muted">
          <li>
            SP 量的是陀螺的轉速,而轉速受陀螺本身的重量與轉動慣量影響。
            換過陀螺的資料不能直接放在一起比,偵測到多個感測器時頁面會提醒。
          </li>
          <li>
            換發射器也一樣不能直接比,而且它的影響不是固定的加分 ——
            實測同一個人換發射器,在後段低的球上是 −152(看不出差異),
            後段中段 +230,後段高的球 +523。<strong className="text-ink">器材放大你當下的發力,
            不會替你補上沒做出來的部分。</strong>所以比較器材的時候,要在後段相近的球之間比。
          </li>
          <li>
            圈數與上升時間加起來只能解釋一部分的 SP 變異,其餘來自這個感測器
            看不到的地方。這頁能告訴你「差在哪個量」,不能告訴你「為什麼」。
          </li>
          <li>
            A/B 兩組之間如果隔了很久、或中間換過器材與場地,p 值就不能算數。
            要比就在同一次練習裡連著打完。
          </li>
        </ul>
      </section>
    </div>
  )
}
