<template>
  <div class="page">
    <h2 class="page-title">销量数据</h2>
    <p class="page-desc">按销售地区与月份维护脐橙销量、销售额与销售渠道</p>

    <div class="page-card">
      <div class="toolbar">
        <el-select v-model="query.region_id" placeholder="销售地区" clearable filterable style="width: 190px">
          <el-option v-for="r in provinces" :key="r.id" :label="r.name" :value="r.id" />
        </el-select>
        <el-date-picker
          v-model="range"
          type="daterange"
          value-format="YYYY-MM-DD"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          style="width: 260px"
        />
        <el-button type="primary" :icon="Search" @click="load(1)">查询</el-button>
        <el-button :icon="Refresh" @click="reset">重置</el-button>
        <span class="spacer"></span>
        <el-button type="primary" :icon="Plus" @click="openCreate">新增记录</el-button>
      </div>

      <el-table v-loading="loading" :data="rows" border stripe>
        <el-table-column type="index" label="#" width="56" />
        <el-table-column prop="region_name" label="销售地区" min-width="150" />
        <el-table-column prop="date" label="日期" width="120" />
        <el-table-column label="销量(吨)" width="130" align="right">
          <template #default="{ row }">{{ num(row.sales_volume, 2) }}</template>
        </el-table-column>
        <el-table-column label="销售额(万元)" width="140" align="right">
          <template #default="{ row }">{{ num(row.sales_amount, 2) }}</template>
        </el-table-column>
        <el-table-column label="渠道" width="100">
          <template #default="{ row }">
            <el-tag size="small" :type="row.sales_channel === '电商' ? 'success' : 'info'" effect="plain">
              {{ row.sales_channel || '-' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
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
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next"
          @current-change="load()"
          @size-change="load(1)"
        />
      </div>
    </div>

    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑销量记录' : '新增销量记录'" width="540px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="120px">
        <el-form-item label="销售地区" prop="region_id">
          <el-select v-model="form.region_id" filterable style="width: 100%">
            <el-option v-for="r in provinces" :key="r.id" :label="r.name" :value="r.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="日期" prop="date">
          <el-date-picker v-model="form.date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
        </el-form-item>
        <el-form-item label="销量(吨)" prop="sales_volume">
          <el-input-number v-model="form.sales_volume as number" :min="0" :precision="2" :controls="false" style="width: 100%" />
        </el-form-item>
        <el-form-item label="销售额(万元)">
          <el-input-number v-model="form.sales_amount as number" :min="0" :precision="2" :controls="false" style="width: 100%" />
        </el-form-item>
        <el-form-item label="销售渠道">
          <el-select v-model="form.sales_channel" style="width: 100%">
            <el-option label="批发" value="批发" />
            <el-option label="电商" value="电商" />
            <el-option label="商超" value="商超" />
            <el-option label="产地直发" value="产地直发" />
          </el-select>
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
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { Plus, Refresh, Search } from '@element-plus/icons-vue'
import { baseApi, tradeApi } from '@/api'
import type { Region, SalesData } from '@/types'
import { num } from '@/utils/format'

const loading = ref(false)
const saving = ref(false)
const rows = ref<SalesData[]>([])
const provinces = ref<Region[]>([])
const total = ref(0)
const range = ref<[string, string] | null>(null)
const query = reactive({ page: 1, page_size: 20, region_id: null as number | null })

const dialogVisible = ref(false)
const isEdit = ref(false)
const formRef = ref<FormInstance>()
const form = reactive<Partial<SalesData>>({})

const rules: FormRules = {
  region_id: [{ required: true, message: '请选择销售地区', trigger: 'change' }],
  date: [{ required: true, message: '请选择日期', trigger: 'change' }],
  sales_volume: [{ required: true, message: '请输入销量', trigger: 'blur' }],
}

async function load(page?: number) {
  if (page) query.page = page
  loading.value = true
  try {
    const res = await tradeApi.sales({
      page: query.page,
      page_size: query.page_size,
      region_id: query.region_id ?? undefined,
      start: range.value?.[0],
      end: range.value?.[1],
    })
    rows.value = res.items
    total.value = res.total
  } finally {
    loading.value = false
  }
}

function reset() {
  query.region_id = null
  range.value = null
  load(1)
}

function openCreate() {
  isEdit.value = false
  Object.keys(form).forEach((k) => delete (form as any)[k])
  dialogVisible.value = true
}

function openEdit(row: SalesData) {
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
        await tradeApi.updateSales(form.id, form)
      } else {
        await tradeApi.createSales(form)
      }
      ElMessage.success('保存成功')
      dialogVisible.value = false
      await load()
    } finally {
      saving.value = false
    }
  })
}

async function onDelete(row: SalesData) {
  await ElMessageBox.confirm('确认删除该销量记录？', '提示', { type: 'warning' })
  await tradeApi.deleteSales(row.id)
  ElMessage.success('删除成功')
  await load()
}

onMounted(async () => {
  const regions = await baseApi.regions()
  provinces.value = regions.filter((r) => r.type === 'province')
  await load()
})
</script>
