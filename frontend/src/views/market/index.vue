<template>
  <div class="page">
    <h2 class="page-title">市场管理</h2>
    <p class="page-desc">全国各销售省份的销量、销售额、市场占比与市场等级，用于销售流向与市场策略分析</p>

    <el-row :gutter="14">
      <el-col :span="15">
        <div class="page-card">
          <div class="toolbar">
            <el-select v-model="query.region_id" placeholder="销售省份" clearable filterable style="width: 180px">
              <el-option v-for="r in provinces" :key="r.id" :label="r.name" :value="r.id" />
            </el-select>
            <el-input-number v-model="query.year" :min="2020" :max="2030" :controls="false" placeholder="年份" style="width: 120px" />
            <el-button type="primary" :icon="Search" @click="load(1)">查询</el-button>
            <el-button :icon="Refresh" @click="reset">重置</el-button>
            <span class="spacer"></span>
            <el-button type="primary" :icon="Plus" @click="openCreate">新增记录</el-button>
          </div>
          <el-table v-loading="loading" :data="rows" border stripe max-height="520">
            <el-table-column type="index" label="#" width="52" />
            <el-table-column prop="region_name" label="销售省份" min-width="130" />
            <el-table-column prop="date" label="统计日期" width="120" />
            <el-table-column label="销量(吨)" width="120" align="right">
              <template #default="{ row }">{{ num(row.sales_volume) }}</template>
            </el-table-column>
            <el-table-column label="销售额(万元)" width="130" align="right">
              <template #default="{ row }">{{ num(row.sales_amount) }}</template>
            </el-table-column>
            <el-table-column label="市场等级" width="100">
              <template #default="{ row }">
                <el-tag size="small" :type="levelTag(row.market_level)" effect="plain">
                  {{ marketLevelLabel[row.market_level] || row.market_level || '-' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="同比增长" width="110" align="right">
              <template #default="{ row }">
                <span :class="(row.growth_rate ?? 0) >= 0 ? 'text-up' : 'text-down'">
                  {{ row.growth_rate === null ? '-' : pct(row.growth_rate) }}
                </span>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="140" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
                <el-button link type="danger" @click="onDelete(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
          <div class="pagination-bar">
            <el-pagination
              v-model:current-page="query.page"
              v-model:page-size="query.page_size"
              :total="total"
              :page-sizes="[10, 20, 50]"
              layout="total, sizes, prev, pager, next"
              @current-change="load()"
              @size-change="load(1)"
            />
          </div>
        </div>
      </el-col>

      <el-col :span="9">
        <div class="page-card">
          <div class="section-title">市场销量 TOP10</div>
          <EChart :option="top10Option" height="300px" />
          <div class="section-title" style="margin-top: 18px">市场等级分布</div>
          <EChart :option="levelOption" height="240px" />
        </div>
      </el-col>
    </el-row>

    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑市场记录' : '新增市场记录'" width="520px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="110px">
        <el-form-item label="销售省份" prop="region_id">
          <el-select v-model="form.region_id" filterable style="width: 100%">
            <el-option v-for="r in provinces" :key="r.id" :label="r.name" :value="r.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="统计日期" prop="date">
          <el-date-picker v-model="form.date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
        </el-form-item>
        <el-form-item label="销量(吨)" prop="sales_volume">
          <el-input-number v-model="form.sales_volume as number" :min="0" :precision="2" :controls="false" style="width: 100%" />
        </el-form-item>
        <el-form-item label="销售额(万元)">
          <el-input-number v-model="form.sales_amount as number" :min="0" :precision="2" :controls="false" style="width: 100%" />
        </el-form-item>
        <el-form-item label="市场等级">
          <el-select v-model="form.market_level" style="width: 100%">
            <el-option label="核心市场" value="core" />
            <el-option label="重点市场" value="main" />
            <el-option label="潜力市场" value="potential" />
          </el-select>
        </el-form-item>
        <el-form-item label="同比增长(%)">
          <el-input-number v-model="form.growth_rate as number" :precision="2" :controls="false" style="width: 100%" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="onSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import type { EChartsOption } from 'echarts'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { Plus, Refresh, Search } from '@element-plus/icons-vue'
import EChart from '@/components/EChart.vue'
import { analysisApi, baseApi, tradeApi } from '@/api'
import type { MarketData, Region } from '@/types'
import { marketLevelLabel, num, pct } from '@/utils/format'

const loading = ref(false)
const saving = ref(false)
const rows = ref<MarketData[]>([])
const provinces = ref<Region[]>([])
const total = ref(0)
const query = reactive({ page: 1, page_size: 20, region_id: null as number | null, year: undefined as number | undefined })
const chartData = ref<{ name: string; sales_volume: number }[]>([])
const levelDist = ref<Record<string, number>>({})

const dialogVisible = ref(false)
const isEdit = ref(false)
const formRef = ref<FormInstance>()
const form = reactive<Partial<MarketData>>({})

const rules: FormRules = {
  region_id: [{ required: true, message: '请选择销售省份', trigger: 'change' }],
  date: [{ required: true, message: '请选择统计日期', trigger: 'change' }],
  sales_volume: [{ required: true, message: '请输入销量', trigger: 'blur' }],
}

function levelTag(level: string | null) {
  return level === 'core' ? 'danger' : level === 'main' ? 'warning' : 'info'
}

const top10Option = computed<EChartsOption>(() => {
  const rows2 = [...chartData.value].reverse()
  return {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: 74, right: 60, top: 10, bottom: 20 },
    xAxis: { type: 'value' },
    yAxis: { type: 'category', data: rows2.map((r) => r.name), axisLabel: { fontSize: 11 } },
    series: [
      {
        type: 'bar',
        barWidth: 12,
        itemStyle: { borderRadius: [0, 6, 6, 0], color: '#2c8b4c' },
        label: { show: true, position: 'right', fontSize: 10, formatter: (p: any) => num(p.value / 10000, 1) + '万吨' },
        data: rows2.map((r) => r.sales_volume),
      },
    ],
  }
})

const levelOption = computed<EChartsOption>(() => ({
  tooltip: { trigger: 'item' },
  legend: { bottom: 0, textStyle: { fontSize: 11 } },
  series: [
    {
      type: 'pie',
      radius: ['42%', '68%'],
      center: ['50%', '44%'],
      itemStyle: { borderColor: '#fff', borderWidth: 2 },
      label: { formatter: '{b}: {c}' },
      data: [
        { name: '核心市场', value: levelDist.value.core || 0, itemStyle: { color: '#d93025' } },
        { name: '重点市场', value: levelDist.value.main || 0, itemStyle: { color: '#ff8c32' } },
        { name: '潜力市场', value: levelDist.value.potential || 0, itemStyle: { color: '#2c8b4c' } },
      ],
    },
  ],
}))

async function load(page?: number) {
  if (page) query.page = page
  loading.value = true
  try {
    const res = await tradeApi.markets({
      page: query.page,
      page_size: query.page_size,
      region_id: query.region_id ?? undefined,
      year: query.year ?? undefined,
    })
    rows.value = res.items
    total.value = res.total
    const analysis = await analysisApi.market({ year: query.year ?? undefined })
    chartData.value = analysis.provinces.slice(0, 10)
    levelDist.value = analysis.level_distribution
  } finally {
    loading.value = false
  }
}

function reset() {
  query.region_id = null
  query.year = undefined
  load(1)
}

function openCreate() {
  isEdit.value = false
  Object.keys(form).forEach((k) => delete (form as any)[k])
  dialogVisible.value = true
}

function openEdit(row: MarketData) {
  isEdit.value = true
  Object.assign(form, row)
  dialogVisible.value = true
}

async function onSave() {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    saving.value = true
    try {
      if (isEdit.value && form.id) {
        await tradeApi.updateMarket(form.id, form)
      } else {
        await tradeApi.createMarket(form)
      }
      ElMessage.success('保存成功')
      dialogVisible.value = false
      await load()
    } finally {
      saving.value = false
    }
  })
}

async function onDelete(row: MarketData) {
  await ElMessageBox.confirm('确认删除该市场记录？', '提示', { type: 'warning' })
  await tradeApi.deleteMarket(row.id)
  ElMessage.success('删除成功')
  await load()
}

onMounted(async () => {
  const regions = await baseApi.regions({ type: 'province' })
  provinces.value = regions
  await load()
})
</script>
