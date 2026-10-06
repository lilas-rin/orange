<template>
  <div class="page">
    <h2 class="page-title">数据分析</h2>
    <p class="page-desc">产销对比、价格波动、产地竞争力多维度统计分析</p>

    <div class="page-card">
      <div class="toolbar">
        <el-date-picker
          v-model="range"
          type="daterange"
          value-format="YYYY-MM-DD"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          style="width: 260px"
        />
        <el-select v-model="areaId" placeholder="选择产地（可选）" clearable filterable style="width: 210px">
          <el-option v-for="a in areas" :key="a.id" :label="a.name" :value="a.id" />
        </el-select>
        <el-button type="primary" :icon="Search" @click="loadAll">分析</el-button>
        <el-button :icon="Refresh" @click="reset">重置</el-button>
      </div>

      <el-tabs v-model="tab">
        <el-tab-pane label="产销分析" name="ps">
          <div class="metric-grid" style="margin-bottom: 14px">
            <div class="metric-card">
              <div class="label">累计产量</div>
              <div class="value">{{ wanTon(ps?.summary.total_production) }}<span class="unit">万吨</span></div>
            </div>
            <div class="metric-card">
              <div class="label">累计销量</div>
              <div class="value">{{ wanTon(ps?.summary.total_sales) }}<span class="unit">万吨</span></div>
            </div>
            <div class="metric-card">
              <div class="label">综合产销率</div>
              <div class="value">{{ pct(ps?.summary.rate) }}</div>
            </div>
          </div>
          <div class="section-title">月度产量 / 销量对比</div>
          <EChart :option="psOption" height="340px" :loading="loading" />
          <el-row :gutter="14" style="margin-top: 16px">
            <el-col :span="12">
              <div class="section-title">各产地累计产量 TOP15</div>
              <EChart :option="areaBarOption" height="330px" />
            </el-col>
            <el-col :span="12">
              <div class="section-title">各县区累计产量</div>
              <EChart :option="countyBarOption" height="330px" />
            </el-col>
          </el-row>
        </el-tab-pane>

        <el-tab-pane label="价格分析" name="price">
          <div class="metric-grid" style="margin-bottom: 14px">
            <div class="metric-card">
              <div class="label">平均价</div>
              <div class="value">{{ num(price?.summary.avg_price, 2) }}<span class="unit">元/kg</span></div>
            </div>
            <div class="metric-card">
              <div class="label">最高价</div>
              <div class="value">{{ num(price?.summary.highest, 2) }}<span class="unit">元/kg</span></div>
            </div>
            <div class="metric-card">
              <div class="label">最低价</div>
              <div class="value">{{ num(price?.summary.lowest, 2) }}<span class="unit">元/kg</span></div>
            </div>
            <div class="metric-card">
              <div class="label">价格波动率（变异系数）</div>
              <div class="value">{{ pct(price?.summary.volatility) }}</div>
            </div>
          </div>
          <div class="section-title">价格走势（均价 / 最高 / 最低）</div>
          <EChart :option="priceOption" height="340px" :loading="loading" />
          <div class="section-title" style="margin-top: 16px">各产地平均价对比 TOP15</div>
          <EChart :option="priceAreaOption" height="340px" />
        </el-tab-pane>

        <el-tab-pane label="产地评价" name="eval">
          <div class="section-title">产地综合竞争力排名（五维评价）</div>
          <EChart :option="evalOption" height="420px" :loading="loading" />
          <el-table :data="evalRanking" border stripe style="margin-top: 16px" max-height="420">
            <el-table-column prop="rank" label="排名" width="70" align="center" />
            <el-table-column prop="name" label="产地名称" min-width="180" />
            <el-table-column label="价格分" width="90" align="right">
              <template #default="{ row }">{{ row.price }}</template>
            </el-table-column>
            <el-table-column label="技术分" width="90" align="right">
              <template #default="{ row }">{{ row.technology }}</template>
            </el-table-column>
            <el-table-column label="运输分" width="90" align="right">
              <template #default="{ row }">{{ row.transport }}</template>
            </el-table-column>
            <el-table-column label="供应分" width="90" align="right">
              <template #default="{ row }">{{ row.supply }}</template>
            </el-table-column>
            <el-table-column label="效益分" width="90" align="right">
              <template #default="{ row }">{{ row.benefit }}</template>
            </el-table-column>
            <el-table-column label="综合得分" width="110" align="right">
              <template #default="{ row }">
                <el-tag :type="row.total >= 85 ? 'success' : row.total >= 78 ? 'warning' : 'info'" effect="plain">
                  {{ row.total }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import type { EChartsOption } from 'echarts'
import { Refresh, Search } from '@element-plus/icons-vue'
import EChart from '@/components/EChart.vue'
import { analysisApi, baseApi } from '@/api'
import type { ProductionArea } from '@/types'
import { num, pct, wanTon } from '@/utils/format'

type PS = Awaited<ReturnType<typeof analysisApi.productionSales>>
type PR = Awaited<ReturnType<typeof analysisApi.price>>
type EV = Awaited<ReturnType<typeof analysisApi.evaluation>>

const loading = ref(false)
const tab = ref('ps')
const range = ref<[string, string] | null>(null)
const areaId = ref<number | null>(null)
const areas = ref<ProductionArea[]>([])
const ps = ref<PS | null>(null)
const price = ref<PR | null>(null)
const evalData = ref<EV | null>(null)

const evalRanking = computed(() => evalData.value?.ranking ?? [])

const psOption = computed<EChartsOption>(() => ({
  tooltip: { trigger: 'axis' },
  legend: { data: ['产量', '销量'], top: 0 },
  grid: { left: 60, right: 30, top: 40, bottom: 40 },
  xAxis: { type: 'category', data: (ps.value?.monthly ?? []).map((m) => m.month), axisLabel: { rotate: 40, fontSize: 10 } },
  yAxis: { type: 'value', name: '吨' },
  dataZoom: [{ type: 'inside' }, { type: 'slider', height: 16, bottom: 6 }],
  series: [
    { name: '产量', type: 'bar', barMaxWidth: 16, itemStyle: { color: '#2c8b4c' }, data: (ps.value?.monthly ?? []).map((m) => m.production) },
    { name: '销量', type: 'bar', barMaxWidth: 16, itemStyle: { color: '#ff8c32' }, data: (ps.value?.monthly ?? []).map((m) => m.sales) },
  ],
}))

const areaBarOption = computed<EChartsOption>(() => {
  const rows = [...(ps.value?.by_area ?? [])].slice(0, 15).reverse()
  return {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: 128, right: 44, top: 10, bottom: 20 },
    xAxis: { type: 'value' },
    yAxis: { type: 'category', data: rows.map((r) => r.name), axisLabel: { fontSize: 10 } },
    series: [{ type: 'bar', barWidth: 11, itemStyle: { borderRadius: [0, 6, 6, 0], color: '#357a5b' }, label: { show: true, position: 'right', fontSize: 9, formatter: (p: any) => num(p.value / 10000, 1) }, data: rows.map((r) => r.production) }],
  }
})

const countyBarOption = computed<EChartsOption>(() => {
  const rows = [...(ps.value?.by_county ?? [])].reverse()
  return {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: 74, right: 44, top: 10, bottom: 20 },
    xAxis: { type: 'value' },
    yAxis: { type: 'category', data: rows.map((r) => r.name), axisLabel: { fontSize: 10 } },
    series: [{ type: 'bar', barWidth: 11, itemStyle: { borderRadius: [0, 6, 6, 0], color: '#e0883a' }, label: { show: true, position: 'right', fontSize: 9, formatter: (p: any) => num(p.value / 10000, 1) }, data: rows.map((r) => r.production) }],
  }
})

const priceOption = computed<EChartsOption>(() => ({
  tooltip: { trigger: 'axis' },
  legend: { data: ['均价', '最高价', '最低价'], top: 0 },
  grid: { left: 52, right: 30, top: 40, bottom: 40 },
  xAxis: { type: 'category', data: (price.value?.monthly ?? []).map((m) => m.month), axisLabel: { rotate: 40, fontSize: 10 } },
  yAxis: { type: 'value', name: '元/kg' },
  dataZoom: [{ type: 'inside' }, { type: 'slider', height: 16, bottom: 6 }],
  series: [
    { name: '均价', type: 'line', smooth: true, showSymbol: false, itemStyle: { color: '#d93025' }, data: (price.value?.monthly ?? []).map((m) => m.avg) },
    { name: '最高价', type: 'line', smooth: true, showSymbol: false, lineStyle: { type: 'dashed' }, itemStyle: { color: '#ff8c32' }, data: (price.value?.monthly ?? []).map((m) => m.max) },
    { name: '最低价', type: 'line', smooth: true, showSymbol: false, lineStyle: { type: 'dashed' }, itemStyle: { color: '#2c8b4c' }, data: (price.value?.monthly ?? []).map((m) => m.min) },
  ],
}))

const priceAreaOption = computed<EChartsOption>(() => {
  const rows = [...(price.value?.by_area ?? [])].slice(0, 15).reverse()
  return {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: 128, right: 44, top: 10, bottom: 20 },
    xAxis: { type: 'value', name: '元/kg' },
    yAxis: { type: 'category', data: rows.map((r) => r.name), axisLabel: { fontSize: 10 } },
    series: [{ type: 'bar', barWidth: 11, itemStyle: { borderRadius: [0, 6, 6, 0], color: '#d93025' }, label: { show: true, position: 'right', fontSize: 9 }, data: rows.map((r) => r.avg) }],
  }
})

const evalOption = computed<EChartsOption>(() => {
  const top = (evalData.value?.ranking ?? []).slice(0, 20)
  return {
    tooltip: { trigger: 'axis' },
    legend: { data: ['价格', '技术', '运输', '供应', '效益', '综合'], top: 0, textStyle: { fontSize: 11 } },
    grid: { left: 44, right: 24, top: 44, bottom: 90 },
    xAxis: { type: 'category', data: top.map((t) => t.name), axisLabel: { rotate: 42, fontSize: 10, interval: 0 } },
    yAxis: { type: 'value', max: 100 },
    series: [
      { name: '价格', type: 'bar', stack: 'dim', barMaxWidth: 22, itemStyle: { color: '#d93025' }, data: top.map((t) => t.price) },
      { name: '技术', type: 'bar', stack: 'dim', itemStyle: { color: '#ff8c32' }, data: top.map((t) => t.technology) },
      { name: '运输', type: 'bar', stack: 'dim', itemStyle: { color: '#e0c33a' }, data: top.map((t) => t.transport) },
      { name: '供应', type: 'bar', stack: 'dim', itemStyle: { color: '#3aa06a' }, data: top.map((t) => t.supply) },
      { name: '效益', type: 'bar', stack: 'dim', itemStyle: { color: '#3578c0' }, data: top.map((t) => t.benefit) },
      { name: '综合', type: 'line', smooth: true, itemStyle: { color: '#1f2733' }, data: top.map((t) => t.total) },
    ],
  }
})

async function loadAll() {
  loading.value = true
  try {
    const params = {
      start: range.value?.[0],
      end: range.value?.[1],
      area_id: areaId.value ?? undefined,
    }
    ps.value = await analysisApi.productionSales(params)
    price.value = await analysisApi.price(params)
    evalData.value = await analysisApi.evaluation()
  } finally {
    loading.value = false
  }
}

function reset() {
  range.value = null
  areaId.value = null
  loadAll()
}

onMounted(async () => {
  const res = await baseApi.areas({ page: 1, page_size: 200 })
  areas.value = res.items
  await loadAll()
})
</script>
