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

        <h3 className="mt-5 font-medium">每圈耗時比圈數更值得看</h3>
        <p className="mt-2 text-muted">
          「上升時間 ÷ 圈數」= 加速期間陀螺轉一圈要多久,越小代表全程轉得越快。
          以每一天為樣本時,這是唯一真正預測當天 SP 的量(r = −0.724);
          圈數反而是 −0.249,方向是反的 —— 圈數中位數最低的那一天 SP 最高。
        </p>
        <p className="mt-2 text-muted">
          圈數看起來跟 SP 正相關是代數糾纏:圈數多的球上升時間也長,每圈耗時
          幾乎沒變(9 圈 10.9ms、10 圈 11.4ms、11 圈 12.0ms)。多轉的那幾圈是
          多花時間換來的,不是轉更快。所以追圈數沒有用,要追的是每圈耗時。
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
