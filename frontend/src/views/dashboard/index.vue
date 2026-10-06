<template>
  <div class="page">
    <h2 class="page-title">数据概览</h2>
    <p class="page-desc">信丰脐橙产销核心指标一览（数据年度：{{ year }}）</p>

    <div class="metric-grid">
      <div class="metric-card">
        <div class="label">年度总产量</div>
        <div class="value">{{ wanTon(kpi?.total_production) }}<span class="unit">万吨</span></div>
        <div class="trend" :class="(kpi?.yoy_growth_rate ?? 0) >= 0 ? 'text-up' : 'text-down'">
          同比 {{ kpi?.yoy_growth_rate === null ? '-' : pct(kpi?.yoy_growth_rate) }}
        </div>
      </div>
      <div class="metric-card">
        <div class="label">年度总销量</div>
        <div class="value">{{ wanTon(kpi?.total_sales_volume) }}<span class="unit">万吨</span></div>
        <div class="trend">产销率 {{ pct(kpi?.production_sales_rate) }}</div>
      </div>
      <div class="metric-card">
        <div class="label">销售总额</div>
        <div class="value">{{ yiYuan(kpi?.total_sales_amount) }}<span class="unit">亿元</span></div>
        <div class="trend">覆盖 {{ kpi?.province_count ?? 0 }} 个省市</div>
      </div>
      <div class="metric-card">
        <div class="label">平均批发价</div>
        <div class="value">{{ num(kpi?.avg_wholesale_price, 2) }}<span class="unit">元/kg</span></div>
        <div class="trend">产地均价口径</div>
      </div>
    </div>

    <el-row :gutter="14" style="margin-top: 14px">
      <el-col :span="24">
        <div class="page-card">
          <div class="section-title">产销月度趋势</div>
          <EChart :option="trendOption" height="340px" :loading="loading" />
        </div>
      </el-col>
    </el-row>

    <el-row :gutter="14" style="margin-top: 14px">
      <el-col :span="14">
        <div class="page-card">
          <div class="section-title">核心市场销量 TOP10</div>
          <EChart :option="marketOption" height="360px" :loading="loading" />
        </div>
      </el-col>
      <el-col :span="10">
        <div class="page-card">
          <div class="section-title">价格走势与预测</div>
          <EChart :option="priceOption" height="360px" :loading="loading" />
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import type { EChartsOption } from 'echarts'
import EChart from '@/components/EChart.vue'
import { analysisApi, screenApi } from '@/api'
import type { ScreenKpi } from '@/types'
import { num, pct, wanTon, yiYuan } from '@/utils/format'

const loading = ref(true)
const year = ref(new Date().getFullYear())
const kpi = ref<ScreenKpi | null>(null)
const monthly = ref<{ month: string; production: number; sales: number }[]>([])
const top10 = ref<{ name: string; sales_volume: number }[]>([])
const history = ref<{ month: string; value: number }[]>([])
const forecast = ref<{ month: string; value: number }[]>([])

const trendOption = computed<EChartsOption>(() => ({
  tooltip: { trigger: 'axis' },
  legend: { data: ['产量', '销量'], top: 0 },
  grid: { left: 50, right: 24, top: 40, bottom: 40 },
  xAxis: {
    type: 'category',
    data: monthly.value.map((m) => m.month),
    axisLabel: { rotate: 40, fontSize: 10 },
  },
  yAxis: { type: 'value', name: '吨' },
  dataZoom: [{ type: 'inside' }, { type: 'slider', height: 16, bottom: 8 }],
  series: [
    {
      name: '产量',
      type: 'line',
      smooth: true,
      showSymbol: false,
      areaStyle: { opacity: 0.12 },
      itemStyle: { color: '#2c8b4c' },
      data: monthly.value.map((m) => m.production),
    },
    {
      name: '销量',
      type: 'line',
      smooth: true,
      showSymbol: false,
      areaStyle: { opacity: 0.12 },
      itemStyle: { color: '#ff8c32' },
      data: monthly.value.map((m) => m.sales),
    },
  ],
}))

const marketOption = computed<EChartsOption>(() => {
  const rows = [...top10.value].reverse()
  return {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: 78, right: 30, top: 16, bottom: 20 },
    xAxis: { type: 'value', name: '吨' },
    yAxis: { type: 'category', data: rows.map((r) => r.name), axisLabel: { fontSize: 11 } },
    series: [
      {
        type: 'bar',
        barWidth: 14,
        itemStyle: {
          borderRadius: [0, 7, 7, 0],
          color: '#2c8b4c',
        },
        label: { show: true, position: 'right', fontSize: 10, formatter: (p: any) => num(p.value / 10000, 1) + '万吨' },
        data: rows.map((r) => r.sales_volume),
      },
    ],
  }
})

const priceOption = computed<EChartsOption>(() => {
  const histMonths = history.value.map((h) => h.month)
  const fcMonths = forecast.value.map((f) => f.month)
  return {
    tooltip: { trigger: 'axis' },
    legend: { data: ['历史批发价', '预测批发价'], top: 0, textStyle: { fontSize: 11 } },
    grid: { left: 44, right: 20, top: 40, bottom: 40 },
    xAxis: { type: 'category', data: [...histMonths, ...fcMonths], axisLabel: { fontSize: 10, rotate: 40 } },
    yAxis: { type: 'value', name: '元/kg' },
    series: [
      {
        name: '历史批发价',
        type: 'line',
        smooth: true,
        showSymbol: false,
        itemStyle: { color: '#2c8b4c' },
        data: [...history.value.map((h) => h.value), ...fcMonths.map(() => null)],
      },
      {
        name: '预测批发价',
        type: 'line',
        smooth: true,
        showSymbol: false,
        lineStyle: { type: 'dashed', color: '#ff8c32' },
        itemStyle: { color: '#ff8c32' },
        data: [...histMonths.map(() => null), ...forecast.value.map((f) => f.value)],
      },
    ],
  }
})

onMounted(async () => {
  loading.value = true
  try {
    const ov = await screenApi.overview()
    kpi.value = ov.kpi
    year.value = ov.kpi.year
    top10.value = ov.top10
    history.value = ov.price_trend.history
    forecast.value = ov.price_trend.forecast
    const ps = await analysisApi.productionSales()
    monthly.value = ps.monthly
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.trend {
  font-size: 12px;
  color: var(--text-sub);
  margin-top: 8px;
}
</style>
