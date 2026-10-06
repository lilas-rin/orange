<template>
  <div class="screen-wrap" ref="wrapRef">
    <div class="screen" :style="scaleStyle">
      <!-- 顶部标题栏 -->
      <header class="sc-header">
        <div class="sc-header-left">
          <span class="dot" :class="{ pulse: refreshing }"></span>
          <span class="sc-sub">{{ seasonLabel }} · 智能决策</span>
        </div>
        <h1 class="sc-title">脐橙产销数据分析与智能决策平台</h1>
        <div class="sc-header-right">
          <span class="live"><i :class="{ pulse: refreshing }"></i>实时</span>
          <span class="sc-date">{{ nowText }}</span>
          <span class="sc-updated">更新 {{ updatedText }}</span>
          <button class="sc-btn" @click="goAdmin">后台管理</button>
        </div>
      </header>

      <div class="sc-body">
        <!-- 左列：市场与风险 -->
        <aside class="sc-col sc-col-left">
          <section class="panel">
            <div class="panel-title"><i></i>核心市场预测 TOP10</div>
            <div class="mkt-head">
              <span class="c-rank">#</span>
              <span class="c-name">市场</span>
              <span class="c-vol">销量</span>
              <span class="c-fc">30天预测</span>
              <span class="c-yoy">同比</span>
            </div>
            <div class="mkt-list">
              <div
                v-for="(r, i) in top10Rows"
                :key="r.name"
                class="mkt-row"
                :class="'dl-' + r.demandLevel"
                :style="{ '--w': r.barPct + '%' }"
              >
                <span class="c-rank" :class="{ top3: i < 3 }">{{ i + 1 }}</span>
                <span class="c-name">{{ r.short }}</span>
                <span class="c-vol"><RollingNumber :text="r.volText" /></span>
                <span class="c-fc"><RollingNumber :text="r.fcText" fallback="—" /></span>
                <span class="c-yoy" :class="toneUp(r.demandGrowth)">
                  {{ arrow(r.demandGrowth) }}<RollingNumber :text="r.growthPct" />
                </span>
              </div>
              <div v-if="!top10Rows.length" class="empty">暂无市场数据</div>
            </div>
            <div class="foot-note">
              单位万吨 · 30天预测＝模型预测新产季首月(11月)销量 · 左侧色条＝需求等级
            </div>
          </section>

          <section class="panel">
            <div class="panel-title"><i></i>市场需求预测（新产季首月）</div>
            <div class="grow-list">
              <div
                v-for="(r, i) in demandRows"
                :key="r.name"
                class="grow-row"
                :class="'dl-' + r.level"
              >
                <span class="grank" :class="{ top3: i < 3 }">{{ i + 1 }}</span>
                <span class="gname">{{ r.short }}</span>
                <span class="gfc"><RollingNumber :text="r.fcText" /><em>万吨</em></span>
                <span class="gyoy" :class="toneUp(r.growth)">
                  {{ arrow(r.growth) }}<RollingNumber :text="r.growthPct" />
                </span>
              </div>
              <div v-if="!demandRows.length" class="empty">暂无需求预测数据</div>
            </div>
            <div class="foot-note">预测值＝新产季首月需求 · 同比＝较上产季首月实际</div>
          </section>

          <section class="panel">
            <div class="panel-title"><i></i>病虫害风险预测</div>            <div class="pest-list">
              <div
                v-for="c in pestRows"
                :key="c.region_id"
                class="pest-row"
                :class="'lv-' + c.forecast"
              >
                <span class="pname">{{ c.name }}</span>
                <span class="pchip" :class="'risk-' + c.current">{{ shortRisk(c.current) }}</span>
                <span class="pchip" :class="'risk-' + c.forecast">{{ shortRisk(c.forecast) }}</span>
                <span class="ptrend" :class="'tr-' + c.trend">{{ trendGlyph(c.trend) }}</span>
                <span class="pcnt">{{ c.recent_count }} 次</span>
              </div>
              <div v-if="!pestRows.length" class="empty">暂无病虫害数据</div>
            </div>
            <div class="foot-note">
              当前＝近12个月实况 · 未来＝预测 {{ pestWindow }} · 高风险区 {{ pest?.high_count ?? 0 }} 个
            </div>
          </section>
        </aside>

        <!-- 中列：地图 + 价格 -->
        <main class="sc-col sc-col-center">
          <div class="map-bar">
            <div class="map-bar-l">
              <span class="map-title">{{ layerTitle }}</span>
              <div class="layer-tabs">
                <button
                  v-for="t in LAYER_TABS"
                  :key="t.key"
                  :class="{ active: layerKey === t.key }"
                  @click="switchLayer(t.key)"
                >
                  {{ t.label }}
                </button>
              </div>
            </div>
            <button v-if="mapLevel === 'ganzhou'" class="map-back" @click="backToChina">
              ← 返回全国
            </button>
            <div class="map-legend">
              <span v-for="(l, i) in mapLegend" :key="i">
                <i v-if="!l.gradient" :style="{ background: l.color }"></i>
                <i v-else :style="{ background: `linear-gradient(90deg, ${l.color}, ${l.color2})` }"></i>
                {{ l.label }}
              </span>
            </div>
          </div>

          <div ref="mapBoxRef" class="map-box" @mousemove="onMapMove">
            <EChart
              class="map-chart"
              :option="mapOption"
              @click="onMapClick"
              @mouseover="onMapOver"
              @mouseout="onMapOut"
              @globalout="onMapOut"
            />
            <div v-if="hoverCounty" class="county-radar" :style="radarStyle">
              <header class="cr-head">
                <span class="cr-name">{{ hoverCounty.name }}</span>
                <span class="cr-tag" :class="`risk-${hoverCounty.risk_level}`">
                  {{ riskLevelLabel[hoverCounty.risk_level] ?? '-' }}
                </span>
              </header>
              <div class="cr-rows">
                <!-- 图层取值放首行；供应压力图层的取值就是产量本身，重复展示反而像数据出错，故跳过 -->
                <div v-if="hoverLayerItem && layerKey !== 'supply'" class="cr-row">
                  <span class="cr-k">{{ layerTitle }}</span>
                  <span class="cr-v cr-hi">{{ hoverLayerItem.label ?? hoverLayerItem.value }}</span>
                </div>
                <div class="cr-row">
                  <span class="cr-k">产量</span>
                  <span class="cr-v">{{ wanTon(hoverCounty.production) }}<i>万吨</i></span>
                </div>
                <div class="cr-row">
                  <span class="cr-k">库内均价</span>
                  <span class="cr-v">{{ hoverCounty.avg_price }}<i>元/kg</i></span>
                </div>
                <div v-if="hoverCounty.real_price_per_kg" class="cr-row">
                  <span class="cr-k">真实产地价</span>
                  <span class="cr-v">{{ hoverCounty.real_price_per_kg }}<i>元/kg</i></span>
                </div>
                <div v-if="hoverCounty.pest_control" class="cr-row">
                  <span class="cr-k">官方防控</span>
                  <span class="cr-v">{{ hoverCounty.pest_control.control_area }}<i>万亩次</i></span>
                </div>
              </div>
              <div class="cr-sub">五维评价</div>
              <EChart class="county-radar-chart" :option="hoverRadarOption" height="234px" />
            </div>
          </div>

          <section class="panel price-panel">
            <div class="panel-title"><i></i>价格趋势 · 异常监测 · 预测区间</div>
            <div class="price-stats">
              <div class="ps">
                <span class="ps-l">当前价格</span>
                <b class="ps-v"><RollingNumber :text="liveNum('px-cur', priceOut?.current, 2, 0.008)" /><em>元/kg</em></b>
              </div>
              <div class="ps">
                <span class="ps-l">未来 7 天</span>
                <b class="ps-v" :class="toneUp(priceOut?.chg7)">
                  {{ arrow(priceOut?.chg7) }}{{ pctAbs(priceOut?.chg7) }}
                </b>
              </div>
              <div class="ps">
                <span class="ps-l">未来 30 天</span>
                <b class="ps-v" :class="toneUp(priceOut?.chg30)">
                  {{ arrow(priceOut?.chg30) }}{{ pctAbs(priceOut?.chg30) }}
                </b>
              </div>
              <div class="ps">
                <span class="ps-l">异常概率</span>
                <b class="ps-v" :class="anomalyTone">{{ priceOut?.anomaly_label ?? '-' }}</b>
              </div>
              <div class="ps">
                <span class="ps-l">置信区间</span>
                <b class="ps-v small">
                  {{ num(priceOut?.ci_low, 1) }}~{{ num(priceOut?.ci_high, 1) }}
                  <em>{{ priceOut?.confidence ?? '-' }}%</em>
                </b>
              </div>
            </div>
            <EChart class="fill-chart" :option="priceOption" />
          </section>
        </main>

        <!-- 右列：核心指标 + 智能产销排产 -->
        <aside class="sc-col sc-col-right">
          <section class="panel kpi-panel">
            <div class="panel-title"><i></i>核心经营指标（{{ kpi?.year || '-' }} 产季）</div>
            <div class="kpi-grid" :class="{ flash: flashOn }">
              <div v-for="k in kpiCards" :key="k.label" class="kpi">
                <div class="kpi-label">{{ k.label }}</div>
                <div class="kpi-val"><RollingNumber :text="k.value" /><em>{{ k.unit }}</em></div>
                <div class="kpi-foot" :class="k.footTone">
                  <RollingNumber :text="k.footText" />
                </div>
              </div>
            </div>
          </section>

          <section class="panel plan-panel">
            <div class="panel-title"><i></i>智能产销排产</div>

            <div class="plan-hero">
              <div class="ph-label">未来 7 天建议排产</div>
              <div class="ph-val">
                <RollingNumber :text="liveWanTon('plan-7d', plan?.plan_7d, 0.005)" /><em>万吨</em>
              </div>
              <div class="ph-sub" :class="toneUp(plan?.change)">
                {{ arrow(plan?.change) }}<RollingNumber :text="livePct('plan-chg', plan?.change, 1, 0.5)" />
                <span class="ph-note">较上产季首月同期</span>
                <span class="ph-state" :class="'st-' + (stock?.risk ?? 'low')">
                  {{ stock?.label ?? '-' }}
                </span>
              </div>
              <div v-if="stock?.advice" class="ph-advice">{{ stock.advice }}</div>
            </div>

            <div class="plan-block">
              <div class="pb-title">市场供应建议</div>
              <div class="pb-rows">
                <div v-for="m in planMarkets" :key="m.name" class="pb-row">
                  <span class="pb-name">{{ shortProvince(m.name) }}</span>
                  <span class="pb-amt" :class="toneUp(m.delta_wan)">
                    {{ m.delta_wan >= 0 ? '+' : '−' }}<RollingNumber :text="m.deltaText" /> 万吨
                  </span>
                  <span class="pb-yoy" :class="toneUp(m.growth)">
                    {{ arrow(m.growth) }}<RollingNumber :text="m.growthPct" />
                  </span>
                  <span class="pb-tag" :class="'tg-' + demandTone(m.growth)">{{ demandTag(m.growth) }}</span>
                </div>
                <div v-if="!planMarkets.length" class="empty">暂无建议</div>
              </div>
            </div>

            <div class="plan-block">
              <div class="pb-title">区域排产</div>
              <div class="pb-rows">
                <div v-for="r in planRegions" :key="r.region_id" class="pb-row">
                  <span class="pb-name">{{ r.name }}</span>
                  <span class="pb-amt plain"><RollingNumber :text="r.planText" /> 万吨</span>
                  <span class="pb-yoy" :class="toneUp(r.delta)">
                    {{ arrow(r.delta) }}<RollingNumber :text="r.deltaPct" />
                  </span>
                  <span class="pb-tag" :class="'risk-' + r.risk">{{ shortRisk(r.risk) }}</span>
                </div>
                <div v-if="!planRegions.length" class="empty">暂无排产数据</div>
              </div>
            </div>

            <div class="foot-note">
              排产＝首月需求 × 安全余量，按产量份额与病虫害风险分配 ·
              期初库存 <RollingNumber :text="liveWanTon('plan-stock', stock?.opening_stock)" /> 万吨 ·
              保障系数 <RollingNumber :text="liveNum('plan-cov', stock?.coverage, 2, 0.004)" />
            </div>
          </section>
        </aside>
      </div>

      <!-- 县区详情抽屉 -->
      <transition name="slide">
        <div v-if="county" class="drawer">
          <div class="drawer-head">
            <h3>{{ county.name }} · 产销联动</h3>
            <div class="drawer-meta">
              <span>
                当前病虫害风险：
                <b :class="`risk-${county.current_risk}`">{{ riskLevelLabel[county.current_risk] }}</b>
              </span>
              <button class="close" @click="closeCounty">×</button>
            </div>
          </div>
          <div class="drawer-body">
            <div class="drawer-grid">
              <div class="chart-card">
                <div class="chart-title">产量趋势（吨）</div>
                <EChart :option="countyProdOption" height="200px" />
              </div>
              <div class="chart-card">
                <div class="chart-title">价格趋势（元/kg）</div>
                <EChart :option="countyPriceOption" height="200px" />
              </div>
              <div class="chart-card">
                <div class="chart-title">病害风险预测</div>
                <EChart :option="countyRiskOption" height="200px" />
              </div>
              <div class="chart-card">
                <div class="chart-title">产地综合评分</div>
                <EChart :option="countyAreaOption" height="200px" />
              </div>
            </div>

            <div class="area-table">
              <div class="chart-title">产地列表（点击查看五维评价与价格预测）</div>
              <div class="area-rows">
                <div
                  v-for="a in county.areas"
                  :key="a.id"
                  class="area-row"
                  :class="{ active: area?.id === a.id }"
                  @click="loadArea(a.id)"
                >
                  <span class="ar-name">{{ a.name }}</span>
                  <span class="ar-variety">{{ a.main_variety || '-' }}</span>
                  <span class="ar-area">{{ num(a.planting_area) }} 亩</span>
                  <span class="ar-score">{{ a.score ?? '-' }}</span>
                </div>
              </div>
            </div>

            <div v-if="area" class="area-detail">
              <div class="chart-title">{{ area.name }} · 五维评价雷达</div>
              <div class="area-detail-grid">
                <EChart :option="radarOption" height="240px" />
                <EChart :option="areaPriceOption" height="240px" />
              </div>
            </div>
          </div>
        </div>
      </transition>

      <div v-if="error" class="global-empty">
        <div class="ge-title">数据加载失败：{{ error }}</div>
        <div v-if="retryLeft > 0" class="ge-sub">正在自动重试（剩余 {{ retryLeft }} 次）…</div>
        <div v-else class="ge-sub">已停止自动重试，请确认后端服务已启动后再试</div>
        <button class="ge-btn" type="button" @click="manualRetry">立即重试</button>
      </div>
      <div v-else-if="!loading && !overview" class="global-empty">
        暂无数据，请先在后台导入或生成演示数据
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import dayjs from 'dayjs'
import { echarts } from '@/utils/echarts'
import type { EChartsOption } from '@/utils/echarts'
import EChart from '@/components/EChart.vue'
import RollingNumber from '@/components/RollingNumber.vue'
import { screenApi } from '@/api'
import type {
  AreaDetail,
  ChinaMapData,
  CountyDetail,
  CountyItem,
  GanzhouData,
  MapLayer,
  MapLayerItem,
  ScreenIntelligence,
  ScreenOverview,
} from '@/types'
import { num, pct, riskLevelLabel, wanTon } from '@/utils/format'
import { registerMaps, GANZHOU_CENTER } from '@/utils/map'

// 地图必须在 EChart 子组件挂载前注册，否则地图系列初始化失败。
registerMaps()

const wrapRef = ref<HTMLElement | null>(null)
const scaleStyle = ref<Record<string, string>>({})
const scaleFactor = ref(1)
let fitRO: ResizeObserver | null = null
let fitRaf = 0
let fitTimers: number[] = []
let fittedW = 0
let fittedH = 0
const nowText = ref('')
const updatedText = ref('--:--:--')

const loading = ref(true)
const refreshing = ref(false)
const error = ref<string | null>(null)
const overview = ref<ScreenOverview | null>(null)
const gzData = ref<GanzhouData | null>(null)
const chinaData = ref<ChinaMapData | null>(null)
const intel = ref<ScreenIntelligence | null>(null)
const layers = ref<Record<string, MapLayer> | null>(null)
const county = ref<CountyDetail | null>(null)
const area = ref<AreaDetail | null>(null)

/** 地图 hover 的县区（赣州下钻视图）与其雷达图定位。 */
const mapBoxRef = ref<HTMLElement | null>(null)
const hoverCounty = ref<CountyItem | null>(null)
const hoverPos = ref({ x: 0, y: 0 })

/** 地图层级：全国（默认） ↔ 赣州市县区。 */
const mapLevel = ref<'china' | 'ganzhou'>('china')

const kpi = computed(() => overview.value?.kpi)
const top10 = computed(() => overview.value?.top10 ?? [])
const counties = computed(() => gzData.value?.counties ?? [])
const chinaProvinces = computed(() => chinaData.value?.provinces ?? [])
const chinaFlows = computed(() => chinaData.value?.flows ?? [])
const demand = computed(() => intel.value?.demand)
const plan = computed(() => intel.value?.plan)
const stock = computed(() => intel.value?.stock)
const prodFc = computed(() => intel.value?.production)
const priceOut = computed(() => intel.value?.price)
const pest = computed(() => intel.value?.pest)
const seasonLabel = computed(() => `${kpi.value?.year ?? '-'} 产季`)
const pestWindow = computed(() => pest.value?.target_month?.slice(0, 7) ?? '未来 7 天')

// ---------------- 通用格式化 ----------------

function shortProvince(name: string) {
  return name.replace(/(壮族自治区|回族自治区|维吾尔自治区|特别行政区|自治区|省|市|县|区)$/, '')
}

/** 正向指标：数值上升为「良好」→ 绿；下降为「负面」→ 红。 */
function toneUp(v: number | null | undefined): string {
  if (v === null || v === undefined || Number.isNaN(v)) return 'flat'
  return v >= 0 ? 'good' : 'bad'
}

/** 反向指标：数值上升为「负面」→ 红；下降为「良好」→ 绿（库存积压、风险上升等）。 */
function toneDown(v: number | null | undefined): string {
  if (v === null || v === undefined || Number.isNaN(v)) return 'flat'
  return v >= 0 ? 'bad' : 'good'
}

function arrow(v: number | null | undefined): string {
  if (v === null || v === undefined || Number.isNaN(v)) return ''
  return v >= 0 ? '↑ ' : '↓ '
}

function pctAbs(v: number | null | undefined, digits = 1): string {
  if (v === null || v === undefined || Number.isNaN(v)) return '-'
  return `${Math.abs(v).toFixed(digits)}%`
}

const RISK_SHORT: Record<string, string> = { low: '低', medium: '中', high: '高' }
function shortRisk(level: string | null | undefined): string {
  return RISK_SHORT[level ?? ''] ?? '-'
}

const TREND_GLYPH: Record<string, string> = { up: '↑', down: '↓', flat: '→' }
function trendGlyph(t: string) {
  return TREND_GLYPH[t] ?? '→'
}

function demandTone(g: number | null | undefined): string {
  if (g === null || g === undefined) return 'flat'
  if (g >= 8) return 'high'
  if (g >= 2) return 'steady'
  if (g >= 0) return 'flat'
  return 'down'
}

function demandTag(g: number | null | undefined): string {
  if (g === null || g === undefined) return '—'
  if (g >= 8) return '高需求'
  if (g >= 2) return '需求平稳'
  if (g >= 0) return '微增'
  return '需求下降'
}

function toWan(v: number | null | undefined, digits = 2): string {
  if (v === null || v === undefined || Number.isNaN(v)) return '—'
  return (v / 10000).toFixed(digits)
}

// ---------------- 实时跳动引擎 ----------------
// 纯展示层效果：**不改变任何真实数据**，只在渲染时叠加一个有界、均值回归的偏移，
// 让读数看起来像在持续刷新（后端数据本身每 60s 才刷新一次）。
//
// 幅度策略（滚轮显示下重新定标）：
//   量值 —— 统一收敛到 3~5 个「最小显示单位」。上一版按比例放大（0.2% × 164 ≈
//           0.33，即 33 个刻度），配合文本直接替换看着还行，但换成滚轮后末位会以
//           每秒十几格的速度疯转，比阶梯跳变更难看。pct 现在只用于在 3~5 格之间微调。
//   比率 —— 幅度压到 |基准| × 25% 以内并保留原符号，杜绝「颜色是绿、数字是负」的矛盾。
//
// 关键机制：**JS 只负责把目标值改掉，滚动过程完全交给组件的 CSS 过渡**。
// 上一版是 JS 每 180ms 把显示值往目标「缓动」一小步，换成滚轮后每步只移动 0.2 格，
// 数字于是永远卡在两格之间（看起来是重影而不是滚动）。现在每个读数有自己的滚动
// 周期（约 0.55~0.9s，随机错峰），到点后直接把显示值跳到新的游走位置，由 CSS 在
// 0.28s 内滚过去 —— 剩下的时间数字是静止、清晰可读的。
//
// 刻意不参与的部分：地图与所有 ECharts 图表（否则每帧都会触发图表重绘）、
// 病虫害「N 次」这类整数计数（出现小数不合常理）、风险等级与日期。

const LIVE_TICK_MS = 200 // 引擎巡检节拍（到点才推进，不是每拍都动）
const LIVE_STEP_MS = 620 // 单个读数的滚动周期基准，实际值会加 45% 随机抖动来错峰

interface LiveState {
  base: number // 真实值（游走中心）
  cur: number // 当前显示值（直接喂给组件，由 CSS 滚动到位）
  target: number // 相对 base 的偏移量
  amp: number // 最大偏移幅度
  nextAt: number // 下一次滚动的时刻
  stepMs: number // 该读数的滚动周期
}

const liveStates = new Map<string, LiveState>()
const liveVersion = ref(0)

let liveTicker: number | undefined
/**
 * 抖动幅度。
 *
 * 换成滚轮显示后不再按比例放大：0.2% × 164 ≈ 0.33，相当于 33 个最小刻度，
 * 末位数字会以每秒十几格的速度疯转。现在统一收敛到「3~5 个最小显示单位」，
 * 单步滚动跨度约 2~4 格，看起来像滚轮在转，而不是老虎机在狂转。
 * pct 只在 3~5 格之间做微调；基准本身很小时再压一档，避免抖动盖过数值本身。
 */
function ampFor(base: number, pct: number, digits: number): number {
  const quantum = Math.pow(10, -digits)
  const steps = 3 + Math.min(pct * 400, 2)
  return Math.min(quantum * steps, Math.abs(base) * 0.25)
}

/**
 * 取某读数的跳动显示值。
 * @param key  稳定且唯一的键；不同指标必须不同，否则会互相污染
 * @param base 真实值（不参与缓动，仅作为缓动中心）
 * @param amp  最大偏移幅度（正负对称）
 */
function live(key: string, base: number | null | undefined, amp: number): number | null {
  void liveVersion.value // 建立响应式依赖：引擎推进时触发重算
  if (base === null || base === undefined || !Number.isFinite(base)) return null
  const st = liveStates.get(key)
  if (!st) {
    const stepMs = LIVE_STEP_MS * (0.75 + Math.random() * 0.5)
    liveStates.set(key, {
      base,
      cur: base,
      target: 0,
      amp,
      // 先停在真实值上，随机延迟后才开始第一个滚动周期，让各读数错峰滚动
      nextAt: performance.now() + Math.random() * stepMs,
      stepMs,
    })
    return base
  }
  if (st.base !== base || st.amp !== amp) {
    // 真实数据刷新（或口径变化）：重新居中，避免沿用旧基准
    st.base = base
    st.amp = amp
    st.target = 0
    st.cur = base
  }
  return st.cur
}

function liveValue(
  key: string,
  base: number | null | undefined,
  pct: number,
  digits: number,
): number | null {
  if (base === null || base === undefined || !Number.isFinite(base)) return null
  return live(key, base, ampFor(base, pct, digits))
}

/** 比率（%）：保留原符号，幅度不超过基准的 25%。 */
function liveRate(
  key: string,
  base: number | null | undefined,
  amp = 0.35,
  digits = 1,
): number | null {
  if (base === null || base === undefined || !Number.isFinite(base)) return null
  const quantum = Math.pow(10, -digits)
  const cap = Math.min(amp, Math.abs(base) * 0.25)
  return live(key, base, Math.min(quantum * 3, cap))
}

/** 吨 → 万吨，带跳动。 */
function liveWanTon(key: string, base: number | null | undefined, pct = 0.002): string {
  if (base === null || base === undefined) return '-'
  const v = liveValue(key, base / 10000, pct, 2)
  return v === null ? '-' : num(v, 2)
}

/** 按显示位数跳动的数字。 */
function liveNum(
  key: string,
  base: number | null | undefined,
  digits = 2,
  pct = 0.0012,
): string {
  const v = liveValue(key, base, pct, digits)
  return v === null ? '-' : num(v, digits)
}

/** 跳动的百分比文案。符号与真实值一致，颜色请继续用真实值判定。 */
function livePct(
  key: string,
  base: number | null | undefined,
  digits = 1,
  amp = 0.35,
): string {
  const v = liveRate(key, base, amp, digits)
  return v === null ? '-' : `${Math.abs(v).toFixed(digits)}%`
}

function liveTick() {
  if (document.hidden) return // 页面不可见时停摆，避免无意义的重算
  const now = performance.now()

  let dirty = false
  liveStates.forEach((st) => {
    if (now < st.nextAt) return // 未到自己的滚动时刻，保持静止（这段静止才是「看得清」的关键）
    st.nextAt = now + st.stepMs

    // 均值回归的随机游走：带惯性、有边界，比纯随机更像真实读数。
    // pull 给回归力，kick 决定单步跨度 —— 典型跨度约为 amp 的 0.5~1.0 倍。
    const pull = -st.target * 0.3
    const kick = (Math.random() * 2 - 1) * st.amp
    let next = st.target + pull + kick
    if (next > st.amp) next = st.amp
    else if (next < -st.amp) next = -st.amp
    st.target = next
    // 直接把显示值跳到新位置，滚动过程完全交给 CSS 过渡
    st.cur = st.base + next
    dirty = true
  })
  if (dirty) liveVersion.value++
}

// ---------------- 核心经营指标（ML 预测融入） ----------------

/** 「同比 ↑x.x%」文案：数字跳动，箭头与颜色仍取自真实值。 */
function yoyText(key: string, v: number | null | undefined, digits = 1): string {
  if (v === null || v === undefined || Number.isNaN(v)) return '同比 -'
  return `同比 ${arrow(v)}${livePct(key, v, digits)}`
}

const kpiCards = computed(() => {
  const k = kpi.value
  const pf = prodFc.value
  const st = stock.value
  const po = priceOut.value
  return [
    {
      label: '总产量',
      value: liveWanTon('kpi-prod', k?.total_production),
      unit: '万吨',
      footText: yoyText('kpi-prod-yoy', k?.yoy_growth_rate),
      footTone: toneUp(k?.yoy_growth_rate),
    },
    {
      label: '总销量',
      value: liveWanTon('kpi-sales', k?.total_sales_volume),
      unit: '万吨',
      footText: yoyText('kpi-sales-yoy', k?.total_sales_volume_yoy),
      footTone: toneUp(k?.total_sales_volume_yoy),
    },
    {
      label: '产销率',
      value: liveNum('kpi-rate', k?.production_sales_rate, 1, 0.0022),
      unit: '%',
      footText: yoyText('kpi-rate-yoy', k?.production_sales_rate_yoy),
      footTone: toneUp(k?.production_sales_rate_yoy),
    },
    {
      label: '平均批发价',
      value: liveNum('kpi-price', k?.avg_wholesale_price, 2, 0.008),
      unit: '元/kg',
      footText: `30天预测 ${arrow(po?.chg30)}${livePct('kpi-price30', po?.chg30)}`,
      footTone: toneUp(po?.chg30),
    },
    {
      label: '期初库存',
      value: liveWanTon('kpi-stock', st?.opening_stock),
      unit: '万吨',
      footText: yoyText('kpi-stock-yoy', st?.stock_yoy),
      // 库存上升＝积压，属负面信息 → 红
      footTone: toneDown(st?.stock_yoy),
    },
    {
      label: `${pf?.year ?? '下产季'} 预测产量`,
      value: liveWanTon('kpi-pf', pf?.value),
      unit: '万吨',
      footText: yoyText('kpi-pf-yoy', pf?.yoy),
      footTone: toneUp(pf?.yoy),
    },
  ]
})

// ---------------- 市场排名（叠加 30 天需求预测） ----------------

const demandByName = computed(() => {
  const map = new Map<string, { forecast: number; growth: number | null; level: string }>()
  ;(demand.value?.all ?? []).forEach((d) => {
    map.set(d.name, { forecast: d.forecast, growth: d.growth, level: d.level })
  })
  return map
})

const top10Rows = computed(() => {
  const rows = top10.value
  const max = Math.max(...rows.map((r) => r.sales_volume), 1)
  return rows.map((r) => {
    const d = demandByName.value.get(r.name)
    const growth = d?.growth ?? r.growth_rate
    return {
      ...r,
      short: shortProvince(r.name),
      barPct: Math.max((r.sales_volume / max) * 100, 2),
      volText: liveWanTon(`t10-vol-${r.name}`, r.sales_volume, 0.003),
      fcText: d ? liveWanTon(`t10-fc-${r.name}`, d.forecast, 0.004) : null,
      growthPct: livePct(`t10-yoy-${r.name}`, growth),
      demandGrowth: growth,
      demandLevel: d?.level ?? 'unknown',
    }
  })
})

const demandRows = computed(() =>
  (demand.value?.markets ?? []).slice(0, 5).map((r) => ({
    ...r,
    short: shortProvince(r.name),
    fcText: liveWanTon(`dm-fc-${r.name}`, r.forecast, 0.004),
    growthPct: livePct(`dm-yoy-${r.name}`, r.growth),
  })),
)

// ---------------- 病虫害风险预测 ----------------

const pestRows = computed(() => (pest.value?.items ?? []).slice(0, 6))

// ---------------- 智能产销排产 ----------------

const planRegions = computed(() =>
  (plan.value?.regions ?? []).slice(0, 6).map((r) => ({
    ...r,
    planText: liveWanTon(`pr-${r.region_id}`, r.plan, 0.003),
    deltaPct: livePct(`prd-${r.region_id}`, r.delta, 1, 0.4),
  })),
)
const planMarkets = computed(() =>
  (plan.value?.markets ?? []).map((m) => ({
    ...m,
    // 先取绝对值再抖动，符号由真实值决定，不会出现「加号配负数」
    deltaText: liveNum(`pm-${m.name}`, Math.abs(m.delta_wan), 2, 0.01),
    growthPct: livePct(`pmg-${m.name}`, m.growth, 1, 0.4),
  })),
)

// ---------------- 地图图层 ----------------

const LAYER_TABS = [
  { key: 'flow', label: '销售流向', scope: 'china' },
  { key: 'demand', label: '市场需求', scope: 'china' },
  { key: 'price', label: '销地价格', scope: 'china' },
  { key: 'supply', label: '供应压力', scope: 'ganzhou' },
  { key: 'risk', label: '病虫害风险', scope: 'ganzhou' },
  { key: 'plan', label: '智能排产', scope: 'ganzhou' },
] as const

const layerKey = ref<string>('flow')
const currentLayer = computed(() => layers.value?.[layerKey.value] ?? null)
const layerItems = computed<MapLayerItem[]>(() => currentLayer.value?.items ?? [])
const layerTitle = computed(() => currentLayer.value?.title ?? '全国脐橙产销地图')

const layerItemsByName = computed(() => {
  const map = new Map<string, MapLayerItem>()
  layerItems.value.forEach((i) => map.set(i.name, i))
  return map
})

function switchLayer(key: string) {
  layerKey.value = key
  const tab = LAYER_TABS.find((t) => t.key === key)
  if (!tab) return
  hoverCounty.value = null
  if (tab.scope === 'ganzhou') {
    mapLevel.value = 'ganzhou'
    closeCounty()
  } else {
    mapLevel.value = 'china'
  }
}

/** 返回全国视图；若当前图层是赣州维度，自动切回销售流向。 */
function backToChina() {
  mapLevel.value = 'china'
  hoverCounty.value = null
  const tab = LAYER_TABS.find((t) => t.key === layerKey.value)
  if (tab && tab.scope === 'ganzhou') layerKey.value = 'flow'
  closeCounty()
}

interface LegendItem {
  label: string
  color: string
  color2?: string
  gradient?: boolean
}

const mapLegend = computed<LegendItem[]>(() => {
  if (mapLevel.value === 'ganzhou' && layerKey.value === 'risk') {
    return [
      { label: '高风险', color: '#ff5b5b' },
      { label: '中风险', color: '#ffc53d' },
      { label: '低风险', color: '#4ade80' },
    ]
  }
  if (layerKey.value === 'demand') {
    return [
      { label: '需求下降', color: '#ff5b5b' },
      { label: '需求平稳', color: '#2b4a63' },
      { label: '需求上升', color: '#4ade80' },
    ]
  }
  if (layerKey.value === 'price') {
    return [{ label: '价格 低→高', color: '#1f5fa8', color2: '#4ade80', gradient: true }]
  }
  if (layerKey.value === 'supply' || layerKey.value === 'plan') {
    return [{ label: '数值 低→高', color: '#1f5fa8', color2: '#9fe0ff', gradient: true }]
  }
  return [
    { label: '销售流向（线宽＝销量）', color: '#ffbe4d' },
    { label: '产地：赣州市', color: '#ff9a4d' },
  ]
})

const mapHint = computed(() => {
  if (mapLevel.value === 'china') {
    return '滚轮缩放、拖拽平移；悬停查看各省数据，点击「江西省」或「赣州市」下钻'
  }
  return '滚轮缩放、拖拽平移；悬停县区查看五维评价与真实产地价，点击「信丰县」进入后台'
})

// ---------------- 图表基色 ----------------

const CHART_TEXT = '#bcd8ef'
const CHART_AXIS = 'rgba(120,200,255,.28)'
const CHART_SPLIT = 'rgba(120,200,255,.13)'
const TOOLTIP = {
  backgroundColor: 'rgba(6,26,44,.94)',
  borderColor: 'rgba(79,195,247,.45)',
  textStyle: { color: '#e6f4ff', fontSize: 15 },
}

const DESIGN_W = 1920
const DESIGN_H = 1080

/**
 * 自适应：始终等比缩放铺满视口；宽屏时横向扩展画布，避免两侧留白。
 *
 * 尺寸来源以 documentElement 的**布局视口**为准（F11、跨显示器拖动、系统缩放比
 * 变化时它是唯一权威真值），并把它回写到 .screen-wrap 上：
 * `position: fixed; inset: 0` 在祖先出现 transform / filter / contain 时会退化成
 * 「相对该祖先定位」，容器就不再等于视口，画面会被裁掉一半。显式钉住容器尺寸后，
 * 即使这种极端情况发生，缩放比例也仍然是按真实视口算出来的。
 */
function applyFit() {
  const box = wrapRef.value
  const de = document.documentElement
  const w = Math.round(de?.clientWidth || window.innerWidth || box?.clientWidth || DESIGN_W)
  const h = Math.round(de?.clientHeight || window.innerHeight || box?.clientHeight || DESIGN_H)
  if (w <= 0 || h <= 0) return
  if (box && (Math.abs(box.clientWidth - w) > 1 || Math.abs(box.clientHeight - h) > 1)) {
    box.style.width = `${w}px`
    box.style.height = `${h}px`
  }
  const scale = Math.min(w / DESIGN_W, h / DESIGN_H)
  const canvasW = Math.max(DESIGN_W, Math.round(w / scale))
  scaleFactor.value = scale
  fittedW = w
  fittedH = h
  scaleStyle.value = {
    width: `${canvasW}px`,
    transform: `scale(${scale})`,
    transformOrigin: 'left top',
    marginLeft: `${(w - canvasW * scale) / 2}px`,
    marginTop: `${(h - DESIGN_H * scale) / 2}px`,
  }
}

/**
 * 兜底自愈：与「已适配尺寸」比对，不一致就重算。
 * 全屏切换（F11）、投屏、笔记本外接显示器切换这类场景，事件偶尔会漏，
 * 漏一次画面就会停在旧比例上；每秒比对一次几乎零成本，能保证 1 秒内自愈。
 */
function guardFit() {
  const de = document.documentElement
  const w = Math.round(de?.clientWidth || window.innerWidth || 0)
  const h = Math.round(de?.clientHeight || window.innerHeight || 0)
  if (Math.abs(w - fittedW) > 1 || Math.abs(h - fittedH) > 1) applyFit()
}

/**
 * 全屏切换后视口尺寸要晚一两帧才稳定（Chrome 的 F11 有一段约 300ms 的过渡，
 * 期间 resize 只报中间态），所以立即算一次，再按递增间隔连补几次校准。
 */
function resize() {
  if (fitRaf) cancelAnimationFrame(fitRaf)
  fitRaf = requestAnimationFrame(() => {
    fitRaf = 0
    applyFit()
  })
  fitTimers.forEach((t) => window.clearTimeout(t))
  fitTimers = [60, 160, 320, 600, 1000, 1800].map((d) => window.setTimeout(applyFit, d))
}

// ---------------- 价格图表 ----------------

function round1(v: number) {
  return Math.round(v * 10) / 10
}

/** 月度环比波动超过 ±10% 视为异常点。 */
const priceAnomalies = computed(() => {
  const hist = overview.value?.price_trend.history ?? []
  const marks: { month: string; value: number; pct: number }[] = []
  for (let i = 1; i < hist.length; i += 1) {
    const a = hist[i - 1].value
    const b = hist[i].value
    if (!a) continue
    const pctChange = ((b - a) / a) * 100
    if (Math.abs(pctChange) >= 10) {
      marks.push({ month: hist[i].month, value: b, pct: round1(pctChange) })
    }
  }
  return marks
})

const anomalyTone = computed(() => {
  const r = priceOut.value?.anomaly_risk
  return r === 'high' ? 'bad' : r === 'medium' ? 'warn' : 'good'
})

const priceOption = computed<EChartsOption>(() => {
  const hist = overview.value?.price_trend.history ?? []
  const fc = overview.value?.price_trend.forecast ?? []
  const hm = hist.map((h) => h.month)
  const fm = fc.map((f) => f.month)
  const anomalies = priceAnomalies.value
  const nulls = fm.map(() => null)
  return {
    tooltip: { trigger: 'axis', ...TOOLTIP },
    legend: {
      data: ['历史价', '预测价', '价格异常'],
      textStyle: { color: CHART_TEXT, fontSize: 15 },
      top: 2,
      right: 12,
      itemWidth: 20,
      itemHeight: 12,
    },
    grid: { left: 62, right: 26, top: 40, bottom: 34 },
    xAxis: {
      type: 'category',
      data: [...hm, ...fm],
      axisLabel: { color: CHART_TEXT, fontSize: 14, rotate: 28, interval: 2 },
      axisLine: { lineStyle: { color: CHART_AXIS } },
    },
    yAxis: {
      type: 'value',
      name: '元/kg',
      nameTextStyle: { color: CHART_TEXT, fontSize: 15 },
      axisLabel: { color: CHART_TEXT, fontSize: 14 },
      splitLine: { lineStyle: { color: CHART_SPLIT } },
    },
    series: [
      {
        name: '历史价',
        type: 'line',
        smooth: true,
        showSymbol: false,
        z: 3,
        lineStyle: { color: '#4fc3f7', width: 3 },
        itemStyle: { color: '#4fc3f7' },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(79,195,247,.4)' },
            { offset: 1, color: 'rgba(79,195,247,0)' },
          ]),
        },
        data: [...hist.map((h) => h.value), ...nulls],
      },
      // 预测置信区间：借堆叠把 lower / upper 之间的带状区域填色
      {
        name: '区间下界',
        type: 'line',
        stack: 'ci',
        symbol: 'none',
        silent: true,
        z: 1,
        lineStyle: { opacity: 0 },
        areaStyle: { opacity: 0 },
        tooltip: { show: false },
        data: [...hm.map(() => null), ...fc.map((f) => f.lower)],
      },
      {
        name: '预测区间',
        type: 'line',
        stack: 'ci',
        symbol: 'none',
        silent: true,
        z: 1,
        lineStyle: { opacity: 0 },
        areaStyle: { color: 'rgba(255,197,61,.18)' },
        tooltip: { show: false },
        data: [...hm.map(() => null), ...fc.map((f) => Math.max(0, f.upper - f.lower))],
      },
      {
        name: '预测价',
        type: 'line',
        smooth: true,
        showSymbol: false,
        z: 3,
        lineStyle: { type: 'dashed', color: '#ffc53d', width: 3 },
        itemStyle: { color: '#ffc53d' },
        data: [...hm.map(() => null), ...fc.map((f) => f.value)],
      },
      {
        name: '价格异常',
        type: 'scatter',
        symbol: 'pin',
        symbolSize: 22,
        z: 10,
        itemStyle: {
          color: (p: any) => (p.data.pct >= 0 ? '#4ade80' : '#ff5b5b'),
        },
        label: {
          show: true,
          position: 'top',
          color: '#e6f4ff',
          fontSize: 13,
          formatter: (p: any) => `${p.data.pct >= 0 ? '↑' : '↓'}${Math.abs(p.data.pct)}%`,
        },
        data: anomalies.map((a) => ({ value: [a.month, a.value], pct: a.pct })),
      },
    ],
  }
})

// ---------------- 地图 ----------------

const XINFENG_NAME = '信丰县'
const JIANGXI_NAME = '江西省'
const GANZHOU_NAME = '赣州市'

const BLUE_SCALE = ['rgba(16,58,96,.85)', '#1f5fa8', '#2f8fd0', '#4fc3f7']

/**
 * 全国地图上的省级名称压成简称。
 * 「新疆维吾尔自治区」「内蒙古自治区」这类长名在 1920 宽的画布上一定会互相压字，
 * 压成两三个字后密度立刻降下来，观感也统一。
 */
const REGION_SHORT: Record<string, string> = {
  新疆维吾尔自治区: '新疆',
  西藏自治区: '西藏',
  内蒙古自治区: '内蒙古',
  广西壮族自治区: '广西',
  宁夏回族自治区: '宁夏',
  香港特别行政区: '香港',
  澳门特别行政区: '澳门',
}

function shortRegionName(name: string): string {
  if (REGION_SHORT[name]) return REGION_SHORT[name]
  return name.replace(/(省|市)$/, '')
}

/**
 * 面积太小的行政区：标签一定会溢到相邻省份头上，永久显示只会制造「撞字」。
 * 默认隐藏，鼠标悬停时用 emphasis.label 单独放大显示。
 */
const TINY_REGIONS = ['北京市', '天津市', '上海市', '香港特别行政区', '澳门特别行政区']

function hexLerp(a: string, b: string, t: number): string {
  const pa = [1, 3, 5].map((i) => parseInt(a.slice(i, i + 2), 16))
  const pb = [1, 3, 5].map((i) => parseInt(b.slice(i, i + 2), 16))
  return `rgb(${pa.map((v, i) => Math.round(v + (pb[i] - v) * t)).join(',')})`
}

/** 销量占比 → 流向线色：量小偏青蓝、量大偏金橙，形成冷→暖的规模层级。 */
function flowColor(t: number): string {
  return t < 0.5
    ? hexLerp('#2f7fb8', '#6ad0ff', t / 0.5)
    : hexLerp('#6ad0ff', '#ffbe4d', (t - 0.5) / 0.5)
}

const mapOption = computed<EChartsOption>(() =>
  mapLevel.value === 'china' ? chinaMapOption() : ganzhouMapOption(),
)

/** 全国视图：销售流向 / 市场需求 / 销地价格 三类数据图层。 */
const chinaMapOption = (): EChartsOption => {
  const ps = chinaProvinces.value
  const items = layerItemsByName.value
  const isFlow = layerKey.value === 'flow'
  const maxVol = Math.max(...ps.map((p) => p.sales_volume), 1)

  const coordOf = (name: string) => {
    const p = ps.find((x) => x.name === name)
    return p && p.longitude !== null && p.latitude !== null ? [p.longitude, p.latitude] : null
  }

  // 全部流向：不再只取 TOP5，21 个销地省份全部绘出；线宽/亮度按销量占比分档，
  // 这样即使线条变多，也能一眼读出「哪儿量大、哪儿量小」的层级。
  const flowRaw = [...chinaFlows.value].sort((a, b) => b.value - a.value)
  const maxFlow = Math.max(...flowRaw.map((f) => f.value), 1)
  const flows = flowRaw
    .map((f) => {
      const to = coordOf(f.to_name)
      if (!to) return null
      return {
        coords: [GANZHOU_CENTER, to] as [number, number][],
        dest: to,
        value: f.value,
        name: f.to_name,
        t: Math.min(f.value / maxFlow, 1),
      }
    })
    .filter(Boolean) as {
    coords: [number, number][]
    dest: [number, number]
    value: number
    name: string
    t: number
  }[]

  const valueOf = (name: string): number | undefined => {
    if (isFlow) {
      const p = ps.find((x) => x.name === name)
      return p ? p.sales_volume : undefined
    }
    return items.get(name)?.value
  }

  // 需求图层以 0 为中轴做红绿双向映射（下降红 / 上升绿）
  const demandAbs = Math.max(...[...items.values()].map((i) => Math.abs(i.value)), 1)

  const visualMap: Record<string, unknown> = isFlow
    ? {
        min: 0,
        max: maxVol,
        text: ['销量高', '销量低'],
        inRange: { color: BLUE_SCALE },
      }
    : layerKey.value === 'demand'
      ? {
          min: -demandAbs,
          max: demandAbs,
          text: ['需求上升', '需求下降'],
          inRange: { color: ['#ff5b5b', '#2b4a63', '#4ade80'] },
        }
      : {
          min: currentLayer.value?.min ?? 0,
          max: currentLayer.value?.max ?? 1,
          text: ['价格高', '价格低'],
          inRange: { color: ['rgba(16,58,96,.85)', '#1f5fa8', '#2f8fd0', '#4ade80'] },
        }

  return {
    tooltip: {
      ...TOOLTIP,
      trigger: 'item',
      formatter: (p: any) => {
        const name = p.name as string
        const c = ps.find((x) => x.name === name)
        const it = items.get(name)
        const head = `<b style="font-size:16px">${name}</b>`
        if (!c) return head
        const lines = [
          `销量：${wanTon(c.sales_volume)} 万吨`,
          `销售额：${wanTon(c.sales_amount)} 万元`,
          `市场等级：${c.market_level || '-'}`,
          `销量同比：${pct(c.growth_rate)}`,
        ]
        if (layerKey.value === 'demand' && it) {
          lines.push(`未来首月需求预测：${toWan(it.value)} 万吨`)
          lines.push(`需求同比：${pct(it.value)}`)
        }
        if (layerKey.value === 'price' && it) {
          lines.push(`销地批发价：${it.value} 元/kg（${realReferenceNote.value}）`)
        }
        return `${head}<br/>${lines.join('<br/>')}`
      },
    },
    geo: {
      map: 'china',
      roam: true,
      scaleLimit: { min: 0.9, max: 8 },
      // 放大到 1.28：一是把地图填满画框（原先下方大片空白），
      // 二是把华东一带的省名拉开，产地标记「赣州市」才不会和湖南/福建贴在一起。
      zoom: 1.28,
      layoutCenter: ['50%', '50%'],
      layoutSize: '100%',
      aspectScale: 0.88,
      // 省份名称常驻，但要解决「两个行政区名字挤在一起」：
      // 长名先压成简称（新疆/内蒙古/广西/宁夏/港澳），再把北京、天津、上海这类
      // 「面积很小、标签必然溢到邻居身上」的直辖市/特区默认隐藏（悬停仍可读到全名），
      // 剩下的省份彼此就基本不会撞字了。
      label: {
        show: true,
        formatter: (p: any) => shortRegionName(String(p?.name ?? '')),
        color: '#b6d4ee',
        fontSize: 12,
        fontWeight: 600,
        textBorderColor: 'rgba(4,18,31,.95)',
        textBorderWidth: 3,
      },
      labelLayout: { moveOverlap: 'shiftY' },
      regions: [
        ...TINY_REGIONS.map((name) => ({ name, label: { show: false } })),
        // 两个需要手工让位的标签：江西的省名往北推（给产地「赣州市」腾地方），
        // 福建的省名往东推（福建本身够小，往海边让一点视觉上完全说得通）。
        { name: JIANGXI_NAME, label: { offset: [0, -36] } },
        { name: '福建省', label: { offset: [16, 8] } },
      ],
      itemStyle: {
        areaColor: 'rgba(16,58,96,.85)',
        borderColor: 'rgba(120,196,255,.55)',
        borderWidth: 1,
      },
      emphasis: {
        itemStyle: { areaColor: 'rgba(52,136,200,.98)' },
        label: {
          show: true,
          color: '#fff',
          fontSize: 17,
          fontWeight: 800,
          textBorderColor: 'rgba(4,18,31,.95)',
          textBorderWidth: 3,
        },
      },
    } as any,
    series: [
      {
        type: 'map',
        map: 'china',
        geoIndex: 0,
        selectedMode: false,
        // geoIndex 模式下区域由 geo 组件渲染，此处 label 不生效，保留为语义标注
        data: ps.map((p) => ({ name: p.name, value: valueOf(p.name) })),
      },
      // 销售流向：全部流向汇聚成「产地辐射网」。
      // 动效从「箭头浮标」换成**流光点**：ECharts 的 trailLength 会画出前粗后细的
      // 锥形拖尾，给长了就是箭头观感，所以只留 0.16 一小截；速度用 constantSpeed，
      // 让长短线速度一致（用 period 的话长线飞快、短线龟速）。
      // zlevel 必须与地图同为 0，否则 effect 会被画到独立画布上，平移/缩放后留下残影。
      ...(isFlow
        ? ([
            {
              type: 'lines' as const,
              coordinateSystem: 'geo' as const,
              zlevel: 0,
              z: 2,
              silent: true,
              effect: {
                show: true,
                constantSpeed: 26,
                // trailLength 会画出前粗后细的锥形拖尾，给长了就是「箭头浮标」观感，
                // 因此归零：只留一个发光小圆点沿线流动，主视觉交给线本身。
                trailLength: 0,
                symbol: 'circle',
                symbolSize: 6,
                color: '#fff0c0',
              },
              lineStyle: { curveness: 0.12 },
              data: flows.map((f) => ({
                coords: f.coords,
                value: f.value,
                name: f.name,
                lineStyle: {
                  color: flowColor(f.t),
                  width: 1.4 + f.t * 4.6,
                  opacity: 0.38 + f.t * 0.5,
                  shadowBlur: 8,
                  shadowColor: flowColor(f.t),
                },
              })),
            },
            // 销地节点：大小/呼吸速度随销量，让「流到哪、多大」直接可见
            {
              type: 'effectScatter' as const,
              coordinateSystem: 'geo' as const,
              zlevel: 0,
              z: 3,
              silent: true,
              symbolSize: (v: any) => 4 + (v?.[2] ?? 0) * 9,
              rippleEffect: { brushType: 'stroke', scale: 2.6, period: 4.5 },
              itemStyle: {
                color: '#9fe4ff',
                opacity: 0.9,
                shadowBlur: 14,
                shadowColor: '#4fc3f7',
              },
              data: flows.map((f) => ({
                name: f.name,
                value: [f.dest[0], f.dest[1], f.t],
              })),
            },
          ] as any[])
        : []),
      // 产地标记：全图唯一常驻文字「赣州市」
      {
        type: 'effectScatter',
        coordinateSystem: 'geo',
        zlevel: 0,
        z: 4,
        symbolSize: 13,
        // 光晕收小：原来的 scale:5 会形成半径 40px 的波纹，把「江西省」的字压得看不清
        rippleEffect: { brushType: 'stroke', scale: 3 },
        itemStyle: { color: '#ff9a4d', shadowBlur: 20, shadowColor: '#ff7a45' },
        label: {
          show: true,
          // 点在江西南部，四周（湖南/广东/福建）都挤满了省名，
          // 只有压在点上是唯一不会撞字的位置
          position: 'inside',
          // 只保留默认地名，不加 ★ 之类符号
          formatter: '赣州市',
          color: '#ffd8c2',
          fontSize: 15,
          fontWeight: 800,
          textBorderColor: 'rgba(4,18,31,.95)',
          textBorderWidth: 3,
        },
        data: [{ name: '赣州市', value: [...GANZHOU_CENTER] }],
      },
    ],
    visualMap: {
      ...(visualMap as Record<string, unknown>),
      left: 8,
      bottom: 8,
      calculable: false,
      textStyle: { color: CHART_TEXT, fontSize: 14 },
      itemWidth: 14,
      itemHeight: 120,
    } as any,
  }
}

/** 赣州视图：供应压力 / 病虫害风险 / 智能排产 三类图层。 */
const ganzhouMapOption = (): EChartsOption => {
  const cs = counties.value
  const items = layerItemsByName.value
  const isRisk = layerKey.value === 'risk'
  const values = [...items.values()].map((i) => i.value)

  // geoIndex 模式下县区名由 geo 组件渲染，因此标签样式必须写在 geo.label 上（此前写在 series 上导致不显示）。
  const geoLabel = {
    show: true,
    color: '#e6f4ff',
    fontSize: 15,
    fontWeight: 700,
    textBorderColor: 'rgba(4,18,31,.95)',
    textBorderWidth: 3,
  }

  const visualMap: Record<string, unknown> = isRisk
    ? {
        type: 'piecewise',
        pieces: [
          { value: 3, label: '高风险', color: '#ff5b5b' },
          { value: 2, label: '中风险', color: '#ffc53d' },
          { value: 1, label: '低风险', color: '#4ade80' },
        ],
        itemWidth: 16,
        itemHeight: 14,
      }
    : {
        min: Math.min(...values, 0),
        max: Math.max(...values, 1),
        text: ['高', '低'],
        inRange: { color: BLUE_SCALE },
        itemWidth: 16,
        itemHeight: 120,
      }

  return {
    // 县区视图已有「五维评价卡片」承载全部信息，再叠加一个跟随鼠标的原生 tooltip
    // 会正好压在卡片上，两层浮层互相打架，所以这里关掉。
    tooltip: { show: false },
    geo: {
      map: 'ganzhou',
      roam: true,
      scaleLimit: { min: 0.9, max: 10 },
      zoom: 1.12,
      label: { ...geoLabel },
      // geo.labelLayout 在 ECharts 5 中可用，但类型定义未收录，这里放宽类型
      labelLayout: { moveOverlap: 'shiftY' },
      itemStyle: {
        areaColor: 'rgba(16,58,96,.85)',
        borderColor: 'rgba(120,196,255,.65)',
        borderWidth: 1.6,
      },
      emphasis: {
        itemStyle: { areaColor: 'rgba(52,136,200,.98)' },
        label: {
          ...geoLabel,
          fontSize: 18,
        },
      },
    } as any,
    series: [
      {
        type: 'map',
        map: 'ganzhou',
        geoIndex: 0,
        selectedMode: false,
        data: cs.map((c) => ({ name: c.name, value: items.get(c.name)?.value ?? undefined })),
      },
      // 信丰县入口标记：只放一个脉冲光点，地名交给 geo 默认标签渲染，
      // 不再叠加「★ 后台入口」之类文字。
      {
        type: 'effectScatter',
        coordinateSystem: 'geo',
        zlevel: 0,
        z: 4,
        symbolSize: 16,
        rippleEffect: { brushType: 'stroke', scale: 4.5 },
        itemStyle: { color: '#ff9a4d', shadowBlur: 22, shadowColor: '#ff7a45' },
        data: [{ name: XINFENG_NAME, value: [114.9309, 25.3802] }],
      },
    ],
    visualMap: {
      ...visualMap,
      left: 16,
      bottom: 20,
      textStyle: { color: CHART_TEXT, fontSize: 15 },
    },
  }
}

const realReferenceNote = computed(() => overview.value?.reference?.collected_at ?? '')

// ---------------- 县区抽屉图表 ----------------

const countyProdOption = computed<EChartsOption>(() => ({
  tooltip: { trigger: 'axis', ...TOOLTIP },
  grid: { left: 58, right: 18, top: 24, bottom: 34 },
  xAxis: {
    type: 'category',
    data: (county.value?.production_trend ?? []).map((t) => t.month),
    axisLabel: { color: CHART_TEXT, fontSize: 13, rotate: 40 },
    axisLine: { lineStyle: { color: CHART_AXIS } },
  },
  yAxis: {
    type: 'value',
    axisLabel: { color: CHART_TEXT, fontSize: 14 },
    splitLine: { lineStyle: { color: CHART_SPLIT } },
  },
  series: [
    {
      type: 'line',
      smooth: true,
      showSymbol: false,
      lineStyle: { color: '#4fc3f7', width: 2.8 },
      itemStyle: { color: '#4fc3f7' },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(79,195,247,.35)' },
          { offset: 1, color: 'rgba(79,195,247,0)' },
        ]),
      },
      data: (county.value?.production_trend ?? []).map((t) => t.value),
    },
  ],
}))

const countyPriceOption = computed<EChartsOption>(() => {
  const hist = county.value?.price_trend ?? []
  return {
    tooltip: { trigger: 'axis', ...TOOLTIP },
    grid: { left: 54, right: 18, top: 24, bottom: 34 },
    xAxis: {
      type: 'category',
      data: hist.map((t) => t.month),
      axisLabel: { color: CHART_TEXT, fontSize: 13, rotate: 40 },
      axisLine: { lineStyle: { color: CHART_AXIS } },
    },
    yAxis: {
      type: 'value',
      axisLabel: { color: CHART_TEXT, fontSize: 14 },
      splitLine: { lineStyle: { color: CHART_SPLIT } },
    },
    series: [
      {
        type: 'line',
        smooth: true,
        showSymbol: false,
        lineStyle: { color: '#ffc53d', width: 2.8 },
        itemStyle: { color: '#ffc53d' },
        data: hist.map((t) => t.value),
      },
    ],
  }
})

const countyRiskOption = computed<EChartsOption>(() => {
  const rows = (county.value?.risk_predictions ?? []).slice().reverse()
  return {
    tooltip: { trigger: 'axis', ...TOOLTIP },
    grid: { left: 78, right: 20, top: 24, bottom: 34 },
    xAxis: {
      type: 'category',
      data: rows.map((r) => r.target_date),
      axisLabel: { color: CHART_TEXT, fontSize: 13 },
      axisLine: { lineStyle: { color: CHART_AXIS } },
    },
    yAxis: {
      type: 'category',
      data: ['low', 'medium', 'high'],
      axisLabel: {
        color: CHART_TEXT,
        fontSize: 14,
        formatter: (v: string) => riskLevelLabel[v] || v,
      },
      axisLine: { lineStyle: { color: CHART_AXIS } },
    },
    series: [
      {
        type: 'bar',
        barWidth: 20,
        itemStyle: {
          borderRadius: [4, 4, 0, 0],
          color: (p: any) => {
            const lv = rows[p.dataIndex]?.risk_level
            return lv === 'high' ? '#ff5b5b' : lv === 'medium' ? '#ffc53d' : '#4ade80'
          },
        },
        data: rows.map((r) => ({
          value: r.risk_level === 'high' ? 3 : r.risk_level === 'medium' ? 2 : 1,
          risk_level: r.risk_level,
        })),
      },
    ],
  }
})

const countyAreaOption = computed<EChartsOption>(() => {
  const rows = (county.value?.areas ?? []).slice(0, 12)
  return {
    tooltip: { trigger: 'axis', ...TOOLTIP },
    grid: { left: 54, right: 20, top: 24, bottom: 56 },
    xAxis: {
      type: 'category',
      data: rows.map((r) => r.name.replace('脐橙基地', '')),
      axisLabel: { color: CHART_TEXT, fontSize: 13, rotate: 42, interval: 0 },
      axisLine: { lineStyle: { color: CHART_AXIS } },
    },
    yAxis: {
      type: 'value',
      max: 100,
      axisLabel: { color: CHART_TEXT, fontSize: 14 },
      splitLine: { lineStyle: { color: CHART_SPLIT } },
    },
    series: [
      {
        type: 'bar',
        barWidth: 20,
        itemStyle: { borderRadius: [4, 4, 0, 0], color: '#2f8fd0' },
        data: rows.map((r) => r.score ?? 0),
      },
    ],
  }
})

const radarOption = computed<EChartsOption>(() => {
  const s = area.value?.scores
  return {
    tooltip: {},
    radar: {
      indicator: [
        { name: '生产技术', max: 100 },
        { name: '交通运输', max: 100 },
        { name: '供应能力', max: 100 },
        { name: '效益水平', max: 100 },
        { name: '价格水平', max: 100 },
      ],
      axisName: { color: CHART_TEXT, fontSize: 15 },
      splitLine: { lineStyle: { color: 'rgba(120,200,255,.2)' } },
      splitArea: { areaStyle: { color: ['rgba(20,60,100,.25)', 'rgba(12,40,70,.25)'] } },
      axisLine: { lineStyle: { color: 'rgba(120,200,255,.25)' } },
    },
    series: [
      {
        type: 'radar',
        areaStyle: { color: 'rgba(79,195,247,.28)' },
        lineStyle: { color: '#4fc3f7', width: 2.4 },
        itemStyle: { color: '#4fc3f7' },
        data: [
          {
            value: [
              s?.technology ?? 0,
              s?.transport ?? 0,
              s?.supply ?? 0,
              s?.benefit ?? 0,
              area.value?.evaluation?.price ?? 0,
            ],
          },
        ],
      },
    ],
  }
})

const areaPriceOption = computed<EChartsOption>(() => {
  const hist = area.value?.price_trend ?? []
  const pred = area.value?.price_predictions ?? []
  const hm = hist.map((h) => h.month)
  const pm = pred.map((p) => p.target_date.slice(0, 7))
  return {
    tooltip: { trigger: 'axis', ...TOOLTIP },
    legend: { data: ['历史价', '预测价'], textStyle: { color: CHART_TEXT, fontSize: 15 }, top: 2 },
    grid: { left: 54, right: 20, top: 44, bottom: 34 },
    xAxis: {
      type: 'category',
      data: [...hm, ...pm],
      axisLabel: { color: CHART_TEXT, fontSize: 13, rotate: 45 },
      axisLine: { lineStyle: { color: CHART_AXIS } },
    },
    yAxis: {
      type: 'value',
      axisLabel: { color: CHART_TEXT, fontSize: 14 },
      splitLine: { lineStyle: { color: CHART_SPLIT } },
    },
    series: [
      {
        name: '历史价',
        type: 'line',
        smooth: true,
        showSymbol: false,
        lineStyle: { color: '#4fc3f7', width: 2.6 },
        itemStyle: { color: '#4fc3f7' },
        data: [...hist.map((h) => h.value), ...pm.map(() => null)],
      },
      {
        name: '预测价',
        type: 'line',
        smooth: true,
        showSymbol: false,
        lineStyle: { type: 'dashed', color: '#ffc53d', width: 2.6 },
        itemStyle: { color: '#ffc53d' },
        data: [...hm.map(() => null), ...pred.map((p) => p.value)],
      },
    ],
  }
})

// ---------------- 地图交互 ----------------

const RADAR_INDICATORS = [
  { name: '价格', max: 100 },
  { name: '生产技术', max: 100 },
  { name: '运输能力', max: 100 },
  { name: '供应能力', max: 100 },
  { name: '效益', max: 100 },
]

const hoverRadarOption = computed<EChartsOption>(() => {
  const r = hoverCounty.value?.radar
  return {
    tooltip: {},
    radar: {
      indicator: RADAR_INDICATORS,
      // 半径再大就会把顶部的「价格」轴名挤出画布（可见区域只有 234px 高）
      radius: '76%',
      center: ['50%', '50%'],
      axisName: { color: '#a9cbe6', fontSize: 14, fontWeight: 600 },
      splitLine: { lineStyle: { color: 'rgba(120,190,240,.30)' } },
      splitArea: { areaStyle: { color: ['rgba(24,70,116,.30)', 'rgba(10,34,58,.30)'] } },
      axisLine: { lineStyle: { color: 'rgba(120,190,240,.30)' } },
    },
    series: [
      {
        type: 'radar',
        symbolSize: 4,
        areaStyle: { color: 'rgba(79,195,247,.32)' },
        lineStyle: { color: '#4fc3f7', width: 2.4 },
        itemStyle: { color: '#9fe0ff' },
        data: [
          {
            value: [
              r?.price ?? 0,
              r?.technology ?? 0,
              r?.transport ?? 0,
              r?.supply ?? 0,
              r?.benefit ?? 0,
            ],
          },
        ],
      },
    ],
  }
})

const RADAR_W = 352
// 最多 4 行指标时卡片实测高度约 410，留一点余量给边界钳位用
const RADAR_H = 424

/** 当前悬停县区在「当前图层」下的取值，用于卡片首行。 */
const hoverLayerItem = computed(() =>
  hoverCounty.value ? layerItemsByName.value.get(hoverCounty.value.name) ?? null : null,
)

/** 雷达卡片跟随鼠标，并限制在地图容器内。 */
const radarStyle = computed(() => {
  const box = mapBoxRef.value
  const bw = box?.clientWidth ?? 1200
  const bh = box?.clientHeight ?? 700
  const x = hoverPos.value.x
  const y = hoverPos.value.y
  let left = x + 24
  let top = y + 12
  if (left + RADAR_W > bw - 8) left = x - RADAR_W - 24
  if (left < 8) left = 8
  if (top + RADAR_H > bh - 8) top = Math.max(8, bh - RADAR_H - 8)
  return { left: `${left}px`, top: `${top}px` }
})

/** 记录鼠标在地图容器内的位置（换算回 1920 设计稿坐标系）。 */
function onMapMove(e: MouseEvent) {
  const box = mapBoxRef.value
  if (!box) return
  const rect = box.getBoundingClientRect()
  hoverPos.value = {
    x: (e.clientX - rect.left) / scaleFactor.value,
    y: (e.clientY - rect.top) / scaleFactor.value,
  }
}

function onMapOver(params: any) {
  if (mapLevel.value !== 'ganzhou') return
  const c = counties.value.find((x) => x.name === params?.name)
  hoverCounty.value = c ?? null
}

function onMapOut() {
  hoverCounty.value = null
}

function onMapClick(params: any) {
  const name = params?.name as string
  if (!name) return
  if (mapLevel.value === 'china') {
    if (name === JIANGXI_NAME || name === GANZHOU_NAME) {
      mapLevel.value = 'ganzhou'
      // 全国维度图层在赣州视图下没有数据，自动切到供应压力图层
      const tab = LAYER_TABS.find((t) => t.key === layerKey.value)
      if (tab && tab.scope === 'china') layerKey.value = 'supply'
      county.value = null
      area.value = null
      hoverCounty.value = null
    }
    return
  }
  const c = counties.value.find((x) => x.name === name)
  if (c) onCountyClick(c)
}

function onCountyClick(c: CountyItem) {
  if (c.name === XINFENG_NAME) {
    goAdmin()
    return
  }
  loadCounty(c.region_id)
}

async function loadCounty(regionId: number) {
  area.value = null
  county.value = await screenApi.countyDetail(regionId)
}

function closeCounty() {
  county.value = null
  area.value = null
}

async function loadArea(areaId: number) {
  area.value = await screenApi.areaDetail(areaId)
}

function goAdmin() {
  location.hash = '#/dashboard'
}

// ---------------- 生命周期与实时刷新 ----------------

let clockTimer: number | undefined
let pollTimer: number | undefined
let retryTimer: number | undefined
const REFRESH_MS = 60_000
const RETRY_MS = 2_500
const RETRY_MAX = 8

const retryLeft = ref(0)

/**
 * 真实数据刷新（每 60s）时给核心指标一次高亮脉冲 —— 与「跳动」区分开：
 * 跳动是连续微动，脉冲只在数据真正更新时闪一次，说明「刚拉到新值」。
 */
const flashOn = ref(false)
let flashTimer: number | undefined

function flashOnce() {
  flashOn.value = true
  if (flashTimer !== undefined) window.clearTimeout(flashTimer)
  flashTimer = window.setTimeout(() => {
    flashOn.value = false
  }, 900)
}

/** 核心数据（轻接口）：决定大屏能否渲染出内容。 */
async function fetchCore() {
  const [ov, gz, cm] = await Promise.all([
    screenApi.overview(),
    screenApi.ganzhou(),
    screenApi.chinaMap(),
  ])
  overview.value = ov
  gzData.value = gz
  chinaData.value = cm
}

/**
 * 重计算数据（预测 + 地图图层）：单次约 6s，进程刚启动时更慢。
 * 用 allSettled 隔离 —— 任何一个失败或超时都不应拖垮已经渲染出来的大屏。
 */
async function fetchHeavy() {
  const [it, ly] = await Promise.allSettled([
    screenApi.intelligence(),
    screenApi.layers(),
  ])
  if (it.status === 'fulfilled') intel.value = it.value
  if (ly.status === 'fulfilled') layers.value = ly.value
  return it.status === 'fulfilled' && ly.status === 'fulfilled'
}

function scheduleRetry() {
  if (retryTimer !== undefined || retryLeft.value <= 0) return
  retryLeft.value -= 1
  retryTimer = window.setTimeout(() => {
    retryTimer = undefined
    void bootstrap()
  }, RETRY_MS)
}

/**
 * 首屏加载，刻意分两步：
 * 1) 先取核心数据，到手立刻渲染 —— 不再让「预测/图层」把整屏卡成空白；
 * 2) 再取重计算数据，晚到或失败只表现为缺一块面板。
 * 失败自动重试，覆盖「后端刚重启、模型尚未就绪」这一最常见场景。
 */
async function bootstrap() {
  loading.value = true
  error.value = null
  try {
    await fetchCore()
    loading.value = false
    retryLeft.value = RETRY_MAX
    updatedText.value = dayjs().format('HH:mm:ss')
    flashOnce()
    await fetchHeavy()
    updatedText.value = dayjs().format('HH:mm:ss')
  } catch (e: any) {
    loading.value = false
    error.value = e?.message || String(e)
    scheduleRetry()
  }
}

/** 错误横幅上的手动重试。 */
function manualRetry() {
  if (retryTimer !== undefined) {
    clearTimeout(retryTimer)
    retryTimer = undefined
  }
  retryLeft.value = RETRY_MAX
  void bootstrap()
}

/** 定时静默刷新，保持大屏数据「实时」感；不打断当前下钻与悬浮状态。 */
async function silentRefresh() {
  if (document.hidden) return
  refreshing.value = true
  try {
    const [ov, gz, cm] = await Promise.allSettled([
      screenApi.overview(),
      screenApi.ganzhou(),
      screenApi.chinaMap(),
    ])
    if (ov.status === 'fulfilled') overview.value = ov.value
    if (gz.status === 'fulfilled') gzData.value = gz.value
    if (cm.status === 'fulfilled') chinaData.value = cm.value
    // 一旦恢复就清掉错误横幅并重置重试额度，下次故障才能再次自愈
    if (ov.status === 'fulfilled') {
      error.value = null
      retryLeft.value = RETRY_MAX
    }
    await fetchHeavy()
    updatedText.value = dayjs().format('HH:mm:ss')
    if (ov.status === 'fulfilled') flashOnce()
  } catch {
    /* 静默刷新失败不打断展示，等待下一次轮询 */
  } finally {
    refreshing.value = false
  }
}

function onVisibility() {
  if (!document.hidden) silentRefresh()
}

onMounted(() => {
  registerMaps()
  resize()

  // 尺寸监听三保险：window.resize 在 F11 全屏 / 跨屏移动 / 系统缩放变化时
  // 不一定及时触发，ResizeObserver 盯住**根元素**（＝布局视口）兜底，
  // fullscreenchange 再兜一层。
  // 注意不能改成观察 .screen-wrap —— applyFit 会把它的宽高写成 inline 值，
  // 钉住之后它自己就不再随视口变化，ResizeObserver 会彻底失效。
  if (typeof ResizeObserver !== 'undefined') {
    fitRO = new ResizeObserver(() => resize())
    fitRO.observe(document.documentElement)
  }
  window.addEventListener('resize', resize)
  window.addEventListener('orientationchange', resize)
  window.visualViewport?.addEventListener('resize', resize)
  document.addEventListener('fullscreenchange', resize)
  document.addEventListener('webkitfullscreenchange', resize as EventListener)
  document.addEventListener('visibilitychange', onVisibility)
  nowText.value = dayjs().format('YYYY-MM-DD HH:mm:ss')
  clockTimer = window.setInterval(() => {
    nowText.value = dayjs().format('YYYY-MM-DD HH:mm:ss')
    guardFit()
  }, 1000)
  pollTimer = window.setInterval(silentRefresh, REFRESH_MS)
  liveTicker = window.setInterval(liveTick, LIVE_TICK_MS)
  retryLeft.value = RETRY_MAX
  bootstrap()
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resize)
  window.removeEventListener('orientationchange', resize)
  window.visualViewport?.removeEventListener('resize', resize)
  document.removeEventListener('fullscreenchange', resize)
  document.removeEventListener('webkitfullscreenchange', resize as EventListener)
  document.removeEventListener('visibilitychange', onVisibility)
  fitRO?.disconnect()
  fitRO = null
  if (fitRaf) cancelAnimationFrame(fitRaf)
  fitTimers.forEach((t) => window.clearTimeout(t))
  fitTimers = []
  if (clockTimer) window.clearInterval(clockTimer)
  if (pollTimer) window.clearInterval(pollTimer)
  if (retryTimer !== undefined) window.clearTimeout(retryTimer)
  if (liveTicker !== undefined) window.clearInterval(liveTicker)
  if (flashTimer !== undefined) window.clearTimeout(flashTimer)
})

defineExpose({})
</script>

<style scoped>
.screen-wrap {
  /* 固定铺满视口：用 fixed+inset 而不是 100vw/100vh —— 后者在出现滚动条时
     会大于可视区，导致比例算偏、画面被挤出屏幕外。 */
  position: fixed;
  inset: 0;
  overflow: hidden;
  background: #04121f;
}

.screen {
  width: 1920px;
  height: 1080px;
  background:
    radial-gradient(circle at 20% 0%, rgba(31, 95, 168, 0.35), transparent 45%),
    radial-gradient(circle at 88% 100%, rgba(79, 195, 247, 0.18), transparent 42%),
    linear-gradient(160deg, #04121f 0%, #061a2c 55%, #04121f 100%);
  color: #d8ecff;
  padding: 4px 12px 10px;
  position: relative;
}

.sc-header {
  height: 58px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  position: relative;
}

.sc-title {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
  font-size: 46px;
  letter-spacing: 6px;
  margin: 0;
  font-weight: 800;
  background: linear-gradient(180deg, #ffffff 20%, #7ad3ff 100%);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  text-shadow: 0 0 28px rgba(79, 195, 247, 0.45);
  white-space: nowrap;
}

.sc-header-left {
  display: flex;
  align-items: center;
  gap: 9px;
  color: #8fb4d0;
  font-size: 17px;
}

.dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: #4ade80;
  box-shadow: 0 0 12px #4ade80;
}

.sc-header-right {
  display: flex;
  align-items: center;
  gap: 14px;
  font-size: 17px;
  color: #a9c7e0;
}

.live {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  color: #4ade80;
  font-size: 15px;
}

.live i {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #4ade80;
  box-shadow: 0 0 8px #4ade80;
}

.sc-updated {
  font-size: 15px;
  color: #7fa0bb;
}

.pulse {
  animation: pulse 1.1s ease-in-out infinite;
}

@keyframes pulse {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.25;
  }
}

.sc-btn {
  background: rgba(79, 195, 247, 0.12);
  border: 1px solid rgba(79, 195, 247, 0.45);
  color: #a9dcff;
  padding: 6px 18px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 16px;
}

.sc-btn:hover {
  background: rgba(79, 195, 247, 0.25);
}

/* 主体：三栏，中间为地图 + 价格趋势 */
.sc-body {
  display: grid;
  /*
   * 中列必须写 minmax(0, 1fr)，不能写 1fr。
   * 1fr 的隐含最小值是 min-content：ECharts 会给自己的 DOM 留下「上一次尺寸」的
   * 内联 px 宽度，于是中列的 min-content 被钉在「历史最大宽度」上，
   * 网格轨道就再也缩不回去 —— 表现为窗口一旦变小（最典型的就是按 F11 从
   * 非 16:9 的窗口切到 16:9 全屏，画布宽度由 2100+ 收敛回 1920），
   * 右列会被整体挤出屏幕，「屏幕只显示一半」。minmax(0, 1fr) 把最小值显式归零，
   * 轨道就可以自由收缩。
   */
  grid-template-columns: 348px minmax(0, 1fr) 396px;
  gap: 10px;
  height: 1010px;
}

.sc-col {
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-height: 0;
  min-width: 0;
}

.panel {
  background: linear-gradient(180deg, rgba(13, 45, 78, 0.75), rgba(8, 28, 50, 0.75));
  border: 1px solid rgba(79, 195, 247, 0.22);
  border-radius: 10px;
  padding: 8px 10px 8px;
  position: relative;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.panel::before,
.panel::after {
  content: '';
  position: absolute;
  width: 12px;
  height: 12px;
  border-color: #4fc3f7;
  border-style: solid;
}

.panel::before {
  left: -1px;
  top: -1px;
  border-width: 2px 0 0 2px;
}

.panel::after {
  right: -1px;
  bottom: -1px;
  border-width: 0 2px 2px 0;
}

.panel-title {
  flex: none;
  font-size: 21px;
  color: #e3f2ff;
  margin-bottom: 7px;
  display: flex;
  align-items: center;
  gap: 9px;
  letter-spacing: 1px;
  font-weight: 700;
}

.panel-title i {
  width: 6px;
  height: 20px;
  background: linear-gradient(180deg, #4fc3f7, #1f5fa8);
  border-radius: 2px;
}

.fill-chart {
  flex: 1 1 0;
  min-height: 0;
}

.foot-note {
  flex: none;
  margin-top: 5px;
  font-size: 12px;
  line-height: 1.4;
  color: #5f7d96;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* 左列配比：TOP10 占大头 */
.sc-col-left > .panel:nth-child(1) {
  flex: 1.5 1 0;
}
.sc-col-left > .panel:nth-child(2) {
  flex: 1.05 1 0;
}
.sc-col-left > .panel:nth-child(3) {
  flex: 1.15 1 0;
}

/* ---- 核心市场预测 TOP10 ---- */
.mkt-head {
  flex: none;
  display: grid;
  grid-template-columns: 22px 1fr 62px 62px 52px;
  gap: 4px;
  padding: 0 6px 4px;
  font-size: 13px;
  color: #6f92ad;
}

.mkt-head .c-vol,
.mkt-head .c-fc,
.mkt-head .c-yoy {
  text-align: right;
}

.mkt-list {
  flex: 1 1 0;
  min-height: 0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.mkt-row {
  position: relative;
  flex: 1 1 0;
  min-height: 27px;
  display: grid;
  grid-template-columns: 22px 1fr 62px 62px 52px;
  gap: 4px;
  align-items: center;
  padding: 0 6px;
  border-radius: 6px;
  font-size: 15px;
  overflow: hidden;
  border-left: 3px solid rgba(79, 195, 247, 0.35);
}

/* 行内数据条：以宽度表达销量规模 */
.mkt-row::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: var(--w);
  background: linear-gradient(90deg, rgba(79, 195, 247, 0.26), rgba(79, 195, 247, 0.04));
  border-radius: 6px;
  pointer-events: none;
}

.mkt-row > span {
  position: relative;
}

/* 需求等级：上升绿 / 平稳蓝 / 下降红 */
.mkt-row.dl-high {
  border-left-color: #4ade80;
}
.mkt-row.dl-steady,
.mkt-row.dl-flat {
  border-left-color: #4fc3f7;
}
.mkt-row.dl-down {
  border-left-color: #ff5b5b;
}

.c-rank {
  color: #6f92ad;
  font-size: 14px;
  font-weight: 700;
  text-align: center;
}

.c-rank.top3 {
  color: #ffd666;
}

.c-name {
  color: #e6f4ff;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.c-vol {
  text-align: right;
  color: #bcd8ef;
  font-family: 'DIN Alternate', Arial, sans-serif;
}

.c-fc {
  text-align: right;
  color: #ffd666;
  font-family: 'DIN Alternate', Arial, sans-serif;
}

.c-yoy {
  text-align: right;
  font-size: 14px;
}

/* ---- 市场需求预测 ---- */
.grow-list {
  flex: 1 1 0;
  min-height: 0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.grow-row {
  flex: 1 1 0;
  min-height: 30px;
  display: grid;
  grid-template-columns: 24px 1fr auto auto;
  gap: 8px;
  align-items: center;
  padding: 0 8px;
  border-radius: 6px;
  background: rgba(12, 48, 82, 0.42);
  border-left: 3px solid rgba(79, 195, 247, 0.35);
  font-size: 15px;
}

.grow-row.dl-high {
  border-left-color: #4ade80;
}
.grow-row.dl-steady,
.grow-row.dl-flat {
  border-left-color: #4fc3f7;
}
.grow-row.dl-down {
  border-left-color: #ff5b5b;
}

.grank {
  color: #6f92ad;
  font-weight: 700;
  font-size: 14px;
  text-align: center;
}

.grank.top3 {
  color: #ffd666;
}

.gname {
  color: #e6f4ff;
  font-weight: 600;
}

.gfc {
  color: #ffd666;
  font-size: 15px;
  font-family: 'DIN Alternate', Arial, sans-serif;
}

.gfc em {
  font-style: normal;
  font-size: 11px;
  color: #8fb4d0;
  margin-left: 2px;
}

.gyoy {
  font-size: 16px;
  font-weight: 700;
  min-width: 60px;
  text-align: right;
}

/* ---- 病虫害风险预测 ---- */
.pest-list {
  flex: 1 1 0;
  min-height: 0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.pest-row {
  flex: 1 1 0;
  min-height: 30px;
  display: grid;
  grid-template-columns: 1fr 34px 34px 22px 44px;
  gap: 6px;
  align-items: center;
  padding: 0 8px;
  border-radius: 6px;
  background: rgba(12, 48, 82, 0.42);
  border-left: 3px solid rgba(79, 195, 247, 0.4);
  font-size: 15px;
}

.pest-row.lv-high {
  border-left-color: #ff5b5b;
}

.pest-row.lv-medium {
  border-left-color: #ffc53d;
}

.pest-row.lv-low {
  border-left-color: #4ade80;
}

.pname {
  color: #e6f4ff;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.pchip {
  text-align: center;
  font-size: 13px;
  border-radius: 4px;
  padding: 1px 0;
  color: #9dbcd6;
  background: rgba(120, 200, 255, 0.1);
}

.ptrend {
  text-align: center;
  font-size: 16px;
  font-weight: 800;
}

.ptrend.tr-up {
  color: #ff5b5b;
}
.ptrend.tr-down {
  color: #4ade80;
}
.ptrend.tr-flat {
  color: #8fb4d0;
}

.pcnt {
  text-align: right;
  color: #9dbcd6;
  font-size: 13px;
}

/* ---- 地图区 ---- */
.sc-col-center {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-height: 0;
  min-width: 0;
}

.map-bar {
  flex: none;
  height: 44px;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 4px;
}

.map-bar-l {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
  min-width: 0;
}

.map-title {
  flex: none;
  font-size: 21px
;
  font-weight: 800;
  letter-spacing: 1px;
  color: #7ad3ff;
}

.layer-tabs {
  display: flex;
  align-items: center;
  gap: 5px;
}

.layer-tabs button {
  background: rgba(79, 195, 247, 0.09);
  border: 1px solid rgba(79, 195, 247, 0.28);
  color: #9dbcd6;
  padding: 3px 10px;
  border-radius: 20px;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.16s;
}

.layer-tabs button:hover {
  color: #cfe9ff;
  border-color: rgba(79, 195, 247, 0.6);
}

.layer-tabs button.active {
  background: linear-gradient(180deg, rgba(79, 195, 247, 0.42), rgba(31, 95, 168, 0.42));
  border-color: #4fc3f7;
  color: #ffffff;
  font-weight: 700;
}

.map-legend {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 14px;
  color: #a9c7e0;
  flex: none;
}

.map-back {
  flex: none;
  background: rgba(79, 195, 247, 0.12);
  border: 1px solid rgba(79, 195, 247, 0.45);
  color: #a9dcff;
  padding: 3px 10px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
}

.map-back:hover {
  background: rgba(79, 195, 247, 0.28);
}
.map-legend span {
  display: flex;
  align-items: center;
  gap: 5px;
}
.map-legend i {
  width: 13px;
  height: 13px;
  border-radius: 2px;
  display: inline-block;
}

.map-box {
  position: relative;
  flex: 1 1 0;
  min-height: 0;
  border: 1px solid rgba(79, 195, 247, 0.2);
  border-radius: 10px;
  background:
    radial-gradient(circle at 46% 46%, rgba(22, 78, 132, 0.45), rgba(6, 22, 38, 0.55)),
    linear-gradient(180deg, rgba(9, 34, 58, 0.6), rgba(5, 18, 32, 0.6));
  overflow: hidden;
}

.map-chart {
  width: 100%;
  height: 100%;
}

/* hover 县区五维雷达卡片：实底玻璃面板。
 * 早先做成「透明底 + 描边」是错的 —— 地图上的县名、流向线会透上来，
 * 和卡片里的文字互相穿插，看上去很脏。这里改成几乎不透明的深色面板 + 内侧高光，
 * 让信息层级一次读清：标题 / 指标 / 图形。 */
.county-radar {
  position: absolute;
  width: 352px;
  z-index: 20;
  pointer-events: none;
  padding: 11px 14px 10px;
  border-radius: 12px;
  border: 1px solid rgba(79, 195, 247, 0.34);
  /* 不透明：卡片浮在地图上，半透明会让县名和流向线透上来跟卡片文字混在一起 */
  background: linear-gradient(180deg, #0e2c4a, #051221);
  box-shadow:
    0 18px 44px rgba(0, 0, 0, 0.66),
    0 0 26px rgba(31, 95, 168, 0.35),
    inset 0 1px 0 rgba(150, 215, 255, 0.16);
}

.cr-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding-bottom: 9px;
  border-bottom: 1px solid rgba(79, 195, 247, 0.2);
}

.cr-name {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 21px;
  font-weight: 800;
  color: #eaf6ff;
  letter-spacing: 2px;
}

.cr-name::before {
  content: '';
  width: 4px;
  height: 19px;
  border-radius: 2px;
  background: linear-gradient(180deg, #9fe0ff, #2f8fd0);
  box-shadow: 0 0 10px rgba(79, 195, 247, 0.75);
}

.cr-tag {
  flex: none;
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 1px;
  padding: 3px 10px;
  border-radius: 999px;
  color: #cfe6f7;
  background: rgba(79, 195, 247, 0.14);
}

.cr-tag.risk-high {
  color: #ffb3b0;
  background: rgba(255, 91, 91, 0.2);
}
.cr-tag.risk-medium {
  color: #ffd666;
  background: rgba(255, 197, 61, 0.18);
}
.cr-tag.risk-low,
.cr-tag.risk-opportunity {
  color: #86efac;
  background: rgba(74, 222, 128, 0.16);
}

.cr-rows {
  padding: 3px 0 2px;
}

.cr-row {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  height: 25px;
  border-bottom: 1px dashed rgba(79, 195, 247, 0.14);
}

.cr-row:last-child {
  border-bottom: 0;
}

.cr-k {
  font-size: 14px;
  color: #8fb4d0;
  letter-spacing: 0.5px;
}

.cr-v {
  font-variant-numeric: tabular-nums;
  font-size: 19px;
  font-weight: 700;
  color: #e6f4ff;
}

.cr-v i {
  font-style: normal;
  font-size: 12px;
  font-weight: 500;
  color: #7fa0bb;
  margin-left: 4px;
}

.cr-v.cr-hi {
  color: #ffd666;
}

.cr-sub {
  margin-top: 3px;
  font-size: 12px;
  letter-spacing: 3px;
  color: #6f92ad;
  border-top: 1px solid rgba(79, 195, 247, 0.16);
  padding-top: 5px;
}

.county-radar-chart {
  width: 100%;
}

.price-panel {
  flex: none;
  height: 296px;
}

/* 价格关键指标条 */
.price-stats {
  flex: none;
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 8px;
  margin-bottom: 4px;
}

.ps {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 4px 9px;
  background: rgba(12, 48, 82, 0.42);
  border-radius: 6px;
  border-left: 3px solid rgba(79, 195, 247, 0.5);
}

.ps-l {
  font-size: 13px;
  color: #7fa0bb;
  white-space: nowrap;
}

.ps-v {
  font-size: 20px;
  font-weight: 800;
  color: #e6f4ff;
  font-family: 'DIN Alternate', Arial, sans-serif;
  white-space: nowrap;
}

.ps-v.small {
  font-size: 17px;
}

.ps-v em {
  font-size: 12px;
  font-style: normal;
  color: #8fb4d0;
  margin-left: 3px;
  font-weight: 400;
}

/* ---- 右上角核心指标 ---- */
.kpi-panel {
  flex: none;
  height: 330px;
}

.kpi-grid {
  flex: 1 1 0;
  min-height: 0;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-content: stretch;
}

/* 真实数据刷新（每 60s）时的一次高亮脉冲，区别于逐帧微动：
   用 filter 而非 background，避免覆盖卡片原有背景。 */
.kpi-grid.flash .kpi {
  animation: kpi-flash 900ms ease-out;
}

@keyframes kpi-flash {
  0% {
    filter: brightness(1);
  }
  30% {
    filter: brightness(1.4) saturate(1.25);
  }
  100% {
    filter: brightness(1);
  }
}

.kpi {
  box-sizing: border-box;
  flex: 1 1 calc(50% - 4px);
  min-width: calc(50% - 4px);
  max-width: calc(50% - 4px);
  background: rgba(12, 48, 82, 0.6);
  border: 1px solid rgba(79, 195, 247, 0.2);
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  gap: 3px;
  overflow: hidden;
  padding: 4px 6px;
}

.kpi-label {
  font-size: 14px;
  color: #9dbcd6;
  white-space: nowrap;
}

.kpi-val {
  font-size: 26px;
  font-weight: 800;
  color: #7ad3ff;
  font-family: 'DIN Alternate', Arial, sans-serif;
  line-height: 1.08;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
}

.kpi-val em {
  font-size: 12px;
  font-style: normal;
  color: #8fb4d0;
  margin-left: 3px;
  font-weight: 400;
}

.kpi-foot {
  font-size: 13px;
  color: #8fb4d0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
}

/* ---- 智能产销排产 ---- */
.plan-panel {
  flex: 1 1 0;
}

.plan-hero {
  flex: none;
  background: rgba(12, 48, 82, 0.55);
  border: 1px solid rgba(79, 195, 247, 0.24);
  border-radius: 8px;
  padding: 8px 12px 9px;
  text-align: center;
}

.ph-label {
  font-size: 14px;
  color: #7fa0bb;
}

.ph-val {
  font-size: 44px;
  font-weight: 800;
  line-height: 1.06;
  color: #ffe08a;
  font-family: 'DIN Alternate', Arial, sans-serif;
  text-shadow: 0 0 22px rgba(255, 197, 61, 0.35);
}

.ph-val em {
  font-size: 15px;
  font-style: normal;
  color: #c8a86a;
  margin-left: 5px;
  font-weight: 400;
}

.ph-sub {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 700;
  margin-top: 2px;
}

.ph-note {
  font-size: 12px;
  font-weight: 400;
  color: #7fa0bb;
}

.ph-state {
  font-size: 12px;
  font-weight: 600;
  padding: 1px 7px;
  border-radius: 4px;
  background: rgba(120, 200, 255, 0.12);
  color: #9dbcd6;
}

.ph-state.st-low {
  background: rgba(74, 222, 128, 0.16);
  color: #86efac;
}
.ph-state.st-medium {
  background: rgba(255, 197, 61, 0.16);
  color: #ffd666;
}
.ph-state.st-high {
  background: rgba(255, 91, 91, 0.18);
  color: #ffb3b0;
}

.ph-advice {
  margin-top: 6px;
  font-size: 12px;
  line-height: 1.35;
  color: #7fa0bb;
  text-align: center;
}

.plan-block {
  flex: 1 1 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
  margin-top: 8px;
}

.pb-title {
  flex: none;
  font-size: 15px;
  color: #a9dcff;
  font-weight: 600;
  margin-bottom: 5px;
  padding-left: 8px;
  border-left: 3px solid rgba(79, 195, 247, 0.7);
}

.pb-rows {
  flex: 1 1 0;
  min-height: 0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.pb-row {
  flex: 1 1 0;
  min-height: 28px;
  display: grid;
  grid-template-columns: 1fr 88px 54px 56px;
  gap: 6px;
  align-items: center;
  padding: 0 8px;
  border-radius: 6px;
  background: rgba(12, 48, 82, 0.42);
  font-size: 14px;
}

.pb-name {
  color: #e6f4ff;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.pb-amt {
  text-align: right;
  font-weight: 700;
  font-family: 'DIN Alternate', Arial, sans-serif;
}

.pb-amt.plain {
  color: #ffd666;
  font-weight: 600;
}

.pb-yoy {
  text-align: right;
  font-size: 13px;
}

.pb-tag {
  text-align: center;
  font-size: 12px;
  border-radius: 4px;
  padding: 1px 0;
  background: rgba(120, 200, 255, 0.1);
  color: #9dbcd6;
}

.pb-tag.tg-high {
  background: rgba(74, 222, 128, 0.16);
  color: #86efac;
}
.pb-tag.tg-steady,
.pb-tag.tg-flat {
  background: rgba(79, 195, 247, 0.16);
  color: #9fe0ff;
}
.pb-tag.tg-down {
  background: rgba(255, 91, 91, 0.16);
  color: #ffb3b0;
}

.empty {
  color: #5f7d96;
  font-size: 16px;
  text-align: center;
  padding: 16px 0;
}

/* 风险色：良好=绿 / 负面=红 */
.risk-high {
  color: #ff5b5b;
}
.risk-medium {
  color: #ffc53d;
}
.risk-low {
  color: #4ade80;
}
.risk-opportunity {
  color: #4ade80;
}

.pchip.risk-high {
  color: #ffb3b0;
  background: rgba(255, 91, 91, 0.2);
}
.pchip.risk-medium {
  color: #ffd666;
  background: rgba(255, 197, 61, 0.18);
}
.pchip.risk-low {
  color: #86efac;
  background: rgba(74, 222, 128, 0.16);
}
.pb-tag.risk-high {
  color: #ffb3b0;
  background: rgba(255, 91, 91, 0.18);
}
.pb-tag.risk-medium {
  color: #ffd666;
  background: rgba(255, 197, 61, 0.18);
}
.pb-tag.risk-low {
  color: #86efac;
  background: rgba(74, 222, 128, 0.16);
}

/* 抽屉 */
.drawer {
  position: absolute;
  top: 66px;
  right: 14px;
  width: 820px;
  height: calc(1080px - 80px);
  background: linear-gradient(180deg, rgba(8, 32, 56, 0.98), rgba(5, 20, 34, 0.98));
  border: 1px solid rgba(79, 195, 247, 0.35);
  border-radius: 12px;
  box-shadow: -12px 0 40px rgba(0, 0, 0, 0.5);
  display: flex;
  flex-direction: column;
  z-index: 30;
}

.drawer-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid rgba(79, 195, 247, 0.25);
}

.drawer-head h3 {
  margin: 0;
  font-size: 21px;
  color: #7ad3ff;
  letter-spacing: 1px;
}

.drawer-meta {
  display: flex;
  align-items: center;
  gap: 14px;
  font-size: 15px;
  color: #a9c7e0;
}

.close {
  background: transparent;
  border: none;
  color: #8fb4d0;
  font-size: 26px;
  line-height: 1;
  cursor: pointer;
}

.close:hover {
  color: #ff5b5b;
}

.drawer-body {
  flex: 1;
  overflow-y: auto;
  padding: 12px 16px 18px;
}

.drawer-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.chart-card {
  background: rgba(12, 48, 82, 0.4);
  border: 1px solid rgba(79, 195, 247, 0.16);
  border-radius: 8px;
  padding: 8px 10px;
}

.chart-title {
  font-size: 15px;
  color: #a9dcff;
  margin-bottom: 6px;
  font-weight: 600;
}

.area-table {
  margin-top: 12px;
  background: rgba(12, 48, 82, 0.4);
  border: 1px solid rgba(79, 195, 247, 0.16);
  border-radius: 8px;
  padding: 8px 10px;
}

.area-rows {
  max-height: 180px;
  overflow-y: auto;
  margin-top: 6px;
}

.area-row {
  display: grid;
  grid-template-columns: 2fr 1fr 1fr 0.7fr;
  gap: 8px;
  padding: 6px 8px;
  font-size: 14px;
  color: #b8d4e8;
  border-radius: 6px;
  cursor: pointer;
}

.area-row:hover,
.area-row.active {
  background: rgba(31, 95, 168, 0.55);
  color: #fff;
}

.ar-score {
  color: #7ad3ff;
  font-weight: 700;
}

.area-detail {
  margin-top: 12px;
  background: rgba(12, 48, 82, 0.4);
  border: 1px solid rgba(79, 195, 247, 0.16);
  border-radius: 8px;
  padding: 8px 10px;
}

.area-detail-grid {
  display: grid;
  grid-template-columns: 1fr 1.2fr;
  gap: 10px;
}

.slide-enter-active,
.slide-leave-active {
  transition:
    transform 0.28s ease,
    opacity 0.28s ease;
}

.slide-enter-from,
.slide-leave-to {
  transform: translateX(40px);
  opacity: 0;
}

.global-empty {
  position: absolute;
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  color: #6d8ba5;
  font-size: 17px;
  text-align: center;
}

.ge-title {
  color: #ffb3b0;
}

.ge-sub {
  font-size: 14px;
  color: #7d9ab4;
}

.ge-btn {
  margin-top: 4px;
  padding: 7px 24px;
  border: 1px solid rgba(120, 196, 255, 0.55);
  border-radius: 4px;
  background: rgba(31, 95, 168, 0.35);
  color: #cfe6ff;
  font-size: 14px;
  cursor: pointer;
}

.ge-btn:hover {
  background: rgba(52, 136, 200, 0.55);
}

::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}
::-webkit-scrollbar-thumb {
  background: rgba(79, 195, 247, 0.35);
  border-radius: 3px;
}
::-webkit-scrollbar-track {
  background: transparent;
}

/* ---- 语义色（放在最后，确保覆盖各区域的基础文字色）----
   约定：良好信息 = 绿；负面信息 = 红。不按数值正负号，而按业务含义判定。 */
.good {
  color: #4ade80;
}
.bad {
  color: #ff5b5b;
}
.warn {
  color: #ffc53d;
}
.flat {
  color: #9dbcd6;
}
</style>
