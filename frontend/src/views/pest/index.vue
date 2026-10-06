<template>
  <div class="page">
    <h2 class="page-title">病虫害管理</h2>
    <p class="page-desc">记录各产地脐橙病虫害发生情况（发生面积、严重程度、产量影响、防治成本），并统计发生规律</p>

    <el-row :gutter="14">
      <el-col :span="16">
        <div class="page-card">
          <div class="toolbar">
            <el-select v-model="query.production_area_id" placeholder="产地" clearable filterable style="width: 190px">
              <el-option v-for="a in areas" :key="a.id" :label="a.name" :value="a.id" />
            </el-select>
            <el-select v-model="query.pest_disease_type_id" placeholder="病虫害类型" clearable style="width: 170px">
              <el-option v-for="t in types" :key="t.id" :label="t.name" :value="t.id" />
            </el-select>
            <el-button type="primary" :icon="Search" @click="load(1)">查询</el-button>
            <el-button :icon="Refresh" @click="reset">重置</el-button>
            <span class="spacer"></span>
            <el-button type="primary" :icon="Plus" @click="openCreate">新增记录</el-button>
          </div>
          <el-table v-loading="loading" :data="rows" border stripe max-height="560">
            <el-table-column type="index" label="#" width="52" />
            <el-table-column prop="production_area_name" label="产地" min-width="160" />
            <el-table-column prop="pest_disease_type_name" label="病虫害" width="130" />
            <el-table-column prop="date" label="发生日期" width="115" />
            <el-table-column label="严重程度" width="100">
              <template #default="{ row }">
                <el-tag size="small" :type="severityTag(row.severity)" effect="plain">
                  {{ severityLabel[row.severity] || row.severity || '-' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="发生面积(亩)" width="125" align="right">
              <template #default="{ row }">{{ num(row.affected_area, 1) }}</template>
            </el-table-column>
            <el-table-column label="产量影响(吨)" width="125" align="right">
              <template #default="{ row }">{{ num(row.production_impact, 2) }}</template>
            </el-table-column>
            <el-table-column label="防治成本(元)" width="125" align="right">
              <template #default="{ row }">{{ num(row.prevention_cost, 2) }}</template>
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

      <el-col :span="8">
        <div class="page-card">
          <div class="section-title">病虫害发生次数 TOP</div>
          <EChart :option="typeOption" height="270px" />
          <div class="section-title" style="margin-top: 16px">月度发生趋势</div>
          <EChart :option="monthOption" height="270px" />
        </div>
      </el-col>
    </el-row>

    <div class="page-card" style="margin-top: 14px">
      <div class="section-title">病虫害类型与防治要点</div>
      <el-collapse>
        <el-collapse-item v-for="t in types" :key="t.id" :name="t.id">
          <template #title>
            <el-tag size="small" :type="t.type === 'disease' ? 'danger' : 'warning'" effect="plain" style="margin-right: 10px">
              {{ t.type === 'disease' ? '病害' : '虫害' }}
            </el-tag>
            <span style="font-weight: 600">{{ t.name }}</span>
          </template>
          <p class="pest-desc"><strong>发生特点：</strong>{{ t.description }}</p>
          <p class="pest-desc"><strong>防治措施：</strong>{{ t.prevention_method }}</p>
        </el-collapse-item>
      </el-collapse>
    </div>

    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑病虫害记录' : '新增病虫害记录'" width="560px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="120px">
        <el-form-item label="产地" prop="production_area_id">
          <el-select v-model="form.production_area_id" filterable style="width: 100%">
            <el-option v-for="a in areas" :key="a.id" :label="a.name" :value="a.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="病虫害类型" prop="pest_disease_type_id">
          <el-select v-model="form.pest_disease_type_id" filterable style="width: 100%">
            <el-option v-for="t in types" :key="t.id" :label="t.name" :value="t.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="发生日期" prop="date">
          <el-date-picker v-model="form.date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
        </el-form-item>
        <el-form-item label="严重程度" prop="severity">
          <el-radio-group v-model="form.severity">
            <el-radio-button value="mild">轻度</el-radio-button>
            <el-radio-button value="moderate">中度</el-radio-button>
            <el-radio-button value="severe">重度</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="发生面积(亩)">
          <el-input-number v-model="form.affected_area as number" :min="0" :precision="1" :controls="false" style="width: 100%" />
        </el-form-item>
        <el-form-item label="产量影响(吨)">
          <el-input-number v-model="form.production_impact as number" :min="0" :precision="2" :controls="false" style="width: 100%" />
        </el-form-item>
        <el-form-item label="防治成本(元)">
          <el-input-number v-model="form.prevention_cost as number" :min="0" :precision="2" :controls="false" style="width: 100%" />
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
import type { PestRecord, PestType, ProductionArea } from '@/types'
import { num, severityLabel } from '@/utils/format'

const loading = ref(false)
const saving = ref(false)
const rows = ref<PestRecord[]>([])
const types = ref<PestType[]>([])
const areas = ref<ProductionArea[]>([])
const total = ref(0)
const query = reactive({
  page: 1,
  page_size: 20,
  production_area_id: null as number | null,
  pest_disease_type_id: null as number | null,
})
const byType = ref<{ name: string; count: number }[]>([])
const byMonth = ref<{ month: string; count: number }[]>([])

const dialogVisible = ref(false)
const isEdit = ref(false)
const formRef = ref<FormInstance>()
const form = reactive<Partial<PestRecord>>({})

const rules: FormRules = {
  production_area_id: [{ required: true, message: '请选择产地', trigger: 'change' }],
  pest_disease_type_id: [{ required: true, message: '请选择病虫害类型', trigger: 'change' }],
  date: [{ required: true, message: '请选择发生日期', trigger: 'change' }],
  severity: [{ required: true, message: '请选择严重程度', trigger: 'change' }],
}

function severityTag(s: string | null) {
  return s === 'severe' ? 'danger' : s === 'moderate' ? 'warning' : 'info'
}

const typeOption = computed<EChartsOption>(() => {
  const rows2 = [...byType.value].reverse()
  return {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: 92, right: 40, top: 10, bottom: 20 },
    xAxis: { type: 'value' },
    yAxis: { type: 'category', data: rows2.map((r) => r.name), axisLabel: { fontSize: 10 } },
    series: [
      {
        type: 'bar',
        barWidth: 11,
        itemStyle: { borderRadius: [0, 6, 6, 0], color: '#e0603a' },
        label: { show: true, position: 'right', fontSize: 10 },
        data: rows2.map((r) => r.count),
      },
    ],
  }
})

const monthOption = computed<EChartsOption>(() => {
  const recent = byMonth.value.slice(-24)
  return {
    tooltip: { trigger: 'axis' },
    grid: { left: 40, right: 20, top: 16, bottom: 44 },
    xAxis: { type: 'category', data: recent.map((r) => r.month), axisLabel: { fontSize: 9, rotate: 45 } },
    yAxis: { type: 'value', name: '次数' },
    series: [
      {
        type: 'line',
        smooth: true,
        showSymbol: false,
        areaStyle: { opacity: 0.14 },
        itemStyle: { color: '#e0603a' },
        data: recent.map((r) => r.count),
      },
    ],
  }
})

async function load(page?: number) {
  if (page) query.page = page
  loading.value = true
  try {
    const res = await tradeApi.pestRecords({
      page: query.page,
      page_size: query.page_size,
      production_area_id: query.production_area_id ?? undefined,
      pest_disease_type_id: query.pest_disease_type_id ?? undefined,
    })
    rows.value = res.items
    total.value = res.total
    const analysis = await analysisApi.pest()
    byType.value = analysis.by_type.slice(0, 8)
    byMonth.value = analysis.by_month
  } finally {
    loading.value = false
  }
}

function reset() {
  query.production_area_id = null
  query.pest_disease_type_id = null
  load(1)
}

function openCreate() {
  isEdit.value = false
  Object.keys(form).forEach((k) => delete (form as any)[k])
  form.severity = 'mild'
  dialogVisible.value = true
}

function openEdit(row: PestRecord) {
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
        await tradeApi.updatePestRecord(form.id, form)
      } else {
        await tradeApi.createPestRecord(form)
      }
      ElMessage.success('保存成功')
      dialogVisible.value = false
      await load()
    } finally {
      saving.value = false
    }
  })
}

async function onDelete(row: PestRecord) {
  await ElMessageBox.confirm('确认删除该病虫害记录？', '提示', { type: 'warning' })
  await tradeApi.deletePestRecord(row.id)
  ElMessage.success('删除成功')
  await load()
}

onMounted(async () => {
  types.value = await tradeApi.pestTypes()
  const res = await baseApi.areas({ page: 1, page_size: 200 })
  areas.value = res.items
  await load()
})
</script>

<style scoped>
.pest-desc {
  margin: 4px 0;
  font-size: 13px;
  color: #4a5560;
  line-height: 1.7;
}
</style>
